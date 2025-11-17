"""
Feedback Comment Analysis Module
Analyzes user feedback comments to extract quality signals and enhance document ranking.
"""

import os
import json
from typing import Dict, Optional, List
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()


class FeedbackAnalyzer:
    """Analyzes textual feedback comments using Claude to extract quality signals."""

    def __init__(self):
        """Initialize the feedback analyzer."""
        self.client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.model = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-20250514')

    def analyze_comment(self, comment: str, rating: int, query_text: str, response_text: str) -> Dict:
        """
        Analyze a feedback comment to extract quality signals.

        Args:
            comment: User's textual feedback
            rating: Numeric rating (1-5)
            query_text: Original query that was asked
            response_text: Response that was rated

        Returns:
            Dictionary containing:
            - sentiment_score: Float from -1.0 (very negative) to +1.0 (very positive)
            - issue_types: List of identified issues
            - severity: 'none', 'minor', 'moderate', 'severe'
            - needs_review: Boolean indicating if document needs manual review
            - confidence: How confident the analysis is (0.0-1.0)
            - summary: Brief summary of the feedback
        """
        if not comment or not comment.strip():
            return {
                'sentiment_score': 0.0,
                'issue_types': [],
                'severity': 'none',
                'needs_review': False,
                'confidence': 1.0,
                'summary': 'No comment provided'
            }

        prompt = f"""You are analyzing user feedback for a Federal Reserve information retrieval system.

USER QUERY: {query_text}

RESPONSE PROVIDED: {response_text[:500]}...

USER RATING: {rating}/5 stars

USER COMMENT: {comment}

Analyze this feedback and extract quality signals. Return a JSON object with:

1. "sentiment_score": A number from -1.0 (very negative) to +1.0 (very positive) representing the overall sentiment
2. "issue_types": An array of issue types found. Use ONLY these categories:
   - "outdated" - Content is out of date or references old information
   - "incorrect" - Factual errors or wrong information
   - "too_technical" - Too complex or jargon-heavy for general audience
   - "too_simple" - Not detailed enough, lacks depth
   - "missing_info" - Important information is missing
   - "poor_citation" - Citations are unclear, broken, or missing
   - "off_topic" - Response doesn't address the question
   - "formatting" - Poor formatting or structure
   - "none" - No specific issues identified
3. "severity": One of "none", "minor", "moderate", "severe"
4. "needs_review": true if this feedback suggests the source document needs manual review
5. "confidence": Your confidence in this analysis (0.0 to 1.0)
6. "summary": A one-sentence summary of the feedback (max 100 characters)

Important:
- Be conservative with severity ratings
- If the rating is 4-5 stars, severity should usually be "none" or "minor"
- If the rating is 1-2 stars, look for specific issues
- "needs_review" should only be true for serious issues (incorrect info, outdated, off-topic)
- Return ONLY valid JSON, no other text

Example response:
{{
  "sentiment_score": -0.6,
  "issue_types": ["outdated", "missing_info"],
  "severity": "moderate",
  "needs_review": true,
  "confidence": 0.85,
  "summary": "User reports outdated interest rate information"
}}
"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.0,  # Deterministic for analysis
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Parse Claude's response
            analysis_text = response.content[0].text.strip()

            # Extract JSON if wrapped in markdown code blocks
            if '```json' in analysis_text:
                analysis_text = analysis_text.split('```json')[1].split('```')[0].strip()
            elif '```' in analysis_text:
                analysis_text = analysis_text.split('```')[1].split('```')[0].strip()

            analysis = json.loads(analysis_text)

            # Validate and normalize
            analysis['sentiment_score'] = max(-1.0, min(1.0, float(analysis.get('sentiment_score', 0.0))))
            analysis['issue_types'] = analysis.get('issue_types', [])
            analysis['severity'] = analysis.get('severity', 'none')
            analysis['needs_review'] = bool(analysis.get('needs_review', False))
            analysis['confidence'] = max(0.0, min(1.0, float(analysis.get('confidence', 0.5))))
            analysis['summary'] = analysis.get('summary', 'Feedback analyzed')[:100]

            return analysis

        except Exception as e:
            print(f"Error analyzing comment: {e}")
            # Return default analysis if Claude fails
            return {
                'sentiment_score': (rating - 3.0) / 2.0,  # Fallback to rating-based sentiment
                'issue_types': ['none'],
                'severity': 'none',
                'needs_review': False,
                'confidence': 0.3,
                'summary': f'Analysis failed: {str(e)[:50]}'
            }

    def calculate_enhanced_feedback_score(self, rating: int, comment_analysis: Optional[Dict] = None) -> float:
        """
        Calculate an enhanced feedback score combining rating and comment analysis.

        Args:
            rating: Numeric rating (1-5)
            comment_analysis: Optional analysis from analyze_comment()

        Returns:
            Enhanced feedback score from -1.0 to +1.0
        """
        # Base score from rating
        base_score = (rating - 3.0) / 2.0  # Maps 1→-1.0, 3→0.0, 5→+1.0

        if not comment_analysis or comment_analysis.get('confidence', 0) < 0.3:
            return base_score

        # Weight sentiment analysis based on confidence
        sentiment_score = comment_analysis.get('sentiment_score', 0.0)
        confidence = comment_analysis.get('confidence', 0.5)

        # Severity penalty
        severity_penalty = {
            'none': 0.0,
            'minor': -0.1,
            'moderate': -0.3,
            'severe': -0.5
        }.get(comment_analysis.get('severity', 'none'), 0.0)

        # Issue type penalties
        issue_penalties = {
            'incorrect': -0.4,
            'outdated': -0.3,
            'off_topic': -0.3,
            'missing_info': -0.2,
            'poor_citation': -0.15,
            'too_technical': -0.1,
            'too_simple': -0.1,
            'formatting': -0.05
        }

        issue_penalty = sum(
            issue_penalties.get(issue, 0.0)
            for issue in comment_analysis.get('issue_types', [])
        )
        issue_penalty = max(-0.5, issue_penalty)  # Cap at -0.5

        # Combine scores
        # 70% rating-based, 30% comment analysis
        enhanced_score = (
            0.7 * base_score +
            0.3 * sentiment_score * confidence +
            severity_penalty +
            issue_penalty
        )

        # Clamp to [-1.0, 1.0]
        return max(-1.0, min(1.0, enhanced_score))

    def analyze_document_feedback_patterns(self, feedbacks: List[Dict]) -> Dict:
        """
        Analyze patterns across multiple feedback comments for a document.

        Args:
            feedbacks: List of feedback dicts with 'comment', 'rating', 'analysis'

        Returns:
            Summary of patterns found
        """
        if not feedbacks:
            return {
                'total_feedbacks': 0,
                'common_issues': [],
                'needs_review': False,
                'review_reason': None
            }

        total = len(feedbacks)
        all_issues = []
        needs_review_count = 0
        severities = {'none': 0, 'minor': 0, 'moderate': 0, 'severe': 0}

        for fb in feedbacks:
            analysis = fb.get('analysis', {})
            if analysis:
                all_issues.extend(analysis.get('issue_types', []))
                if analysis.get('needs_review'):
                    needs_review_count += 1
                severity = analysis.get('severity', 'none')
                severities[severity] = severities.get(severity, 0) + 1

        # Count issue frequencies
        issue_counts = {}
        for issue in all_issues:
            if issue != 'none':
                issue_counts[issue] = issue_counts.get(issue, 0) + 1

        # Sort by frequency
        common_issues = sorted(
            [(issue, count) for issue, count in issue_counts.items()],
            key=lambda x: x[1],
            reverse=True
        )

        # Determine if document needs review
        needs_review = False
        review_reason = None

        if needs_review_count >= 2:
            needs_review = True
            review_reason = f"{needs_review_count} users flagged for review"
        elif severities['severe'] >= 1:
            needs_review = True
            review_reason = "Severe issues reported"
        elif severities['moderate'] >= 3:
            needs_review = True
            review_reason = "Multiple moderate issues"
        elif common_issues and common_issues[0][1] >= max(3, total * 0.5):
            needs_review = True
            review_reason = f"Recurring issue: {common_issues[0][0]}"

        return {
            'total_feedbacks': total,
            'common_issues': common_issues[:5],  # Top 5
            'needs_review': needs_review,
            'review_reason': review_reason,
            'severity_distribution': severities
        }


if __name__ == "__main__":
    # Test the analyzer
    analyzer = FeedbackAnalyzer()

    test_comment = "This information about interest rates seems outdated. The current rates are different from what's shown here."
    test_rating = 2
    test_query = "What is the current federal funds rate?"
    test_response = "The federal funds rate is currently 2.5%..."

    print("Analyzing test comment...")
    analysis = analyzer.analyze_comment(test_comment, test_rating, test_query, test_response)
    print(json.dumps(analysis, indent=2))

    enhanced_score = analyzer.calculate_enhanced_feedback_score(test_rating, analysis)
    print(f"\nEnhanced feedback score: {enhanced_score:.2f}")
