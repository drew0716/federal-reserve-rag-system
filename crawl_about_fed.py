import asyncio
import aiohttp
import ssl
import certifi
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import time
import re
from datetime import datetime

BASE_URL = "https://www.federalreserve.gov"
START_URL = f"{BASE_URL}/aboutthefed.htm"
SAVE_DIR = "about_the_fed_pages"
MAX_PAGES = 1500
CONCURRENCY = 10
SEEN = set()

FAQ_MAIN_URL = f"{BASE_URL}/faqs.htm"
FAQ_PREFIX = "/faqs/"
FAQ_SAVE_DIR = "faq_pages"
os.makedirs(FAQ_SAVE_DIR, exist_ok=True)
FAQ_SEEN = set()


os.makedirs(SAVE_DIR, exist_ok=True)

def is_valid_link(href):
    if not href:
        return False
    p = urlparse(href).path.lower()

    # Skip these types of pages - be aggressive to filter non-educational content
    skip_patterns = [
        "boardmeetings",  # Board meeting archives
        "meetings/",      # Meeting archives
        "/foia",          # FOIA pages
        "/default.htm",   # Default/index pages
        "/aboutthefed/files/",  # PDF file listings
        "quarterly",      # Quarterly reports (financial data)
        "financial-report",  # Financial reports
        "financialstatements",  # Financial statements
        "audited-annual",  # Audited annual reports
        "annual-report",  # Annual reports
        "auditors-report",  # Auditor reports
        "/bios/",         # Biography pages
        "sunshine",       # Sunshine act notices
        "appendix-",      # Technical appendices
        "annualreports",  # Annual report listings
        "/careers",       # Career pages
        "/offices",       # Office listings
        "archive",        # Archives
        "centennial",     # Historical centennial content
    ]

    if any(pattern in p for pattern in skip_patterns):
        return False

    return (
        (p.startswith("/aboutthefed") or p.startswith(FAQ_PREFIX))
        and not p.endswith(".pdf")
    )

def is_faq_url(href):
    if not href:
        return False
    p = urlparse(href).path.lower()
    return p.startswith(FAQ_PREFIX) and p.endswith((".htm", ".html"))


def clean_soup(soup):
    """Remove all non-content elements from the soup."""
    # Remove common non-content elements
    for tag in soup([
        "header", "nav", "footer", "script", "style", "noscript",
        "aside", "iframe", "form", "button"
    ]):
        tag.decompose()

    # Remove by class/id patterns (common navigation/UI elements)
    remove_selectors = [
        ".skip-link", ".skipnav", ".skip-to-content",
        ".breadcrumb", ".breadcrumbs",
        ".sidebar", ".side-nav", ".sidenav",
        ".menu", ".navigation", ".nav",
        ".footer", ".page-footer",
        ".header", ".page-header",
        ".tool-menu", ".utility-nav",
        ".social-media", ".share-buttons",
        ".related-links", ".see-also",
        "#breadcrumb", "#navigation", "#sidebar",
        "[role='navigation']", "[role='banner']", "[role='contentinfo']",
        ".usa-banner", ".usa-identifier"  # Federal Reserve specific
    ]

    for selector in remove_selectors:
        for tag in soup.select(selector):
            tag.decompose()

    # Remove lists that are likely navigation (ul/ol with many links)
    for list_tag in soup.find_all(['ul', 'ol']):
        links = list_tag.find_all('a')
        # If more than 5 links in a list, it's likely navigation
        if len(links) > 5:
            list_tag.decompose()

    return soup.get_text(separator="\n", strip=True)

def extract_main_content(html):
    """Extract main content from HTML, focusing on article text."""
    soup = BeautifulSoup(html, "html.parser")

    # Try to find the main content container in order of preference
    container = (
        soup.select_one("article") or
        soup.select_one("main") or
        soup.select_one("div#content") or
        soup.select_one("div.content") or
        soup.select_one("[role='main']") or
        soup.select_one("body")
    )

    if not container:
        return None, None

    # Clean the container
    text = clean_soup(container)

    # Additional filtering: remove very short lines (likely nav remnants)
    lines = text.split('\n')
    filtered_lines = []
    for line in lines:
        line = line.strip()
        # Keep lines that are substantial (>20 chars) or are part of a paragraph
        if len(line) > 20 or (line and len(filtered_lines) > 0 and len(filtered_lines[-1]) > 20):
            filtered_lines.append(line)

    text = '\n'.join(filtered_lines)

    # Content validation: reject if mostly dates or navigation
    if is_mostly_navigation_or_dates(text):
        return None, None

    # Get title
    title = soup.title.string.strip() if soup.title else "Untitled"

    return title, text

def is_mostly_navigation_or_dates(text):
    """Check if content is mostly navigation links or date listings."""
    if not text or len(text) < 100:
        return True

    # Count date-like patterns (e.g., "January 2020", "2020-01-01", etc.)
    date_patterns = re.findall(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b|\b\d{4}\b', text)

    # If more than 30% of words are dates, likely a calendar/archive page
    words = text.split()
    if len(words) > 0 and len(date_patterns) / len(words) > 0.3:
        return True

    # Check for repetitive short lines (navigation menus)
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if len(lines) > 10:
        short_lines = [l for l in lines if len(l) < 30]
        if len(short_lines) / len(lines) > 0.7:  # >70% short lines = likely navigation
            return True

    # Check for common navigation phrases
    nav_phrases = ['back to top', 'share', 'print', 'page not found', 'home page']
    nav_count = sum(1 for phrase in nav_phrases if phrase in text.lower())
    if nav_count >= 3:  # Multiple nav phrases = likely navigation page
        return True

    return False

async def fetch(session, url):
    try:
        async with session.get(url, timeout=20) as response:
            if response.content_type != "text/html":
                return None
            return await response.text()
    except Exception as e:
        print(f"[ERROR] Fetching {url}: {e}")
        return None

async def crawl_page(session, url, queue):
    if url in SEEN or len(SEEN) >= MAX_PAGES:
        return
    SEEN.add(url)

    html = await fetch(session, url)
    if not html:
        return

    title, content = extract_main_content(html)
    if not content or len(content.strip()) < 20:
        print(f"[SKIP] {url} (too short or empty)")
        return

    filename = url.replace(BASE_URL, "").strip("/").replace("/", "_") + ".txt"
    filepath = os.path.join(SAVE_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"<!-- source_url: {url} -->\n")
        f.write(f"<!-- title: {title} -->\n")
        f.write(f"<!-- date_fetched: {datetime.utcnow().isoformat()}Z -->\n\n")
        f.write(content)

    print(f"[✓] Saved: {filename}")

    # Enqueue new links
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_url = urljoin(BASE_URL, href)
        if is_valid_link(href) and full_url not in SEEN:
            await queue.put(full_url)

async def worker(queue, session):
    while True:
        url = await queue.get()
        await crawl_page(session, url, queue)
        queue.task_done()

async def crawl_faq_page(session, url, queue):
    if url in FAQ_SEEN or len(FAQ_SEEN) >= MAX_PAGES:
        return
    FAQ_SEEN.add(url)

    html = await fetch(session, url)
    if not html:
        return

    title, content = extract_main_content(html)
    if not content or len(content.strip()) < 10:
        print(f"[SKIP] {url} (too short or empty)")
        return

    filename = url.replace(BASE_URL, "").strip("/").replace("/", "_") + ".txt"
    filepath = os.path.join(FAQ_SAVE_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"<!-- source_url: {url} -->\n")
        f.write(f"<!-- title: {title} -->\n")
        f.write(f"<!-- date_fetched: {datetime.utcnow().isoformat()}Z -->\n\n")
        f.write(content)

    print(f"[✓] FAQ Saved: {filename}")

    # Enqueue new FAQ links
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_url = urljoin(BASE_URL, href)
        if is_faq_url(href) and full_url not in FAQ_SEEN:
            await queue.put(full_url)

async def faq_worker(queue, session):
    while True:
        url = await queue.get()
        await crawl_faq_page(session, url, queue)
        queue.task_done()

async def main():
    # Create SSL context with certifi certificates
    ssl_context = ssl.create_default_context(cafile=certifi.where())

    queue = asyncio.Queue()
    await queue.put(START_URL)

    # Create connector with SSL context
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [asyncio.create_task(worker(queue, session)) for _ in range(CONCURRENCY)]
        await queue.join()
        for task in tasks:
            task.cancel()

    # FAQ crawl (separate run)
    faq_queue = asyncio.Queue()
    await faq_queue.put(FAQ_MAIN_URL)
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        faq_tasks = [asyncio.create_task(faq_worker(faq_queue, session)) for _ in range(CONCURRENCY)]
        await faq_queue.join()
        for task in faq_tasks:
            task.cancel()

if __name__ == "__main__":
    asyncio.run(main())
