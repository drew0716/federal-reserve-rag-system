# Local Model Migration Guide

This guide provides comprehensive instructions for replacing Claude Sonnet 4 with local open-source models. This migration eliminates API costs and provides full privacy by running everything locally.

## Table of Contents

1. [Why Use Local Models?](#why-use-local-models)
2. [Model Options & Recommendations](#model-options--recommendations)
3. [Installation & Setup](#installation--setup)
4. [Code Changes Required](#code-changes-required)
5. [Configuration](#configuration)
6. [Testing & Validation](#testing--validation)
7. [Performance Optimization](#performance-optimization)
8. [Troubleshooting](#troubleshooting)

---

## Why Use Local Models?

### Advantages
- ✅ **No API costs** - Free after initial setup
- ✅ **Complete privacy** - Data never leaves your infrastructure
- ✅ **No rate limits** - Process unlimited queries
- ✅ **Offline operation** - No internet required
- ✅ **Customizable** - Fine-tune models for your use case
- ✅ **Compliance** - Easier to meet data residency requirements

### Disadvantages
- ⚠️ **Hardware requirements** - Need GPU (8GB+ VRAM) or powerful CPU
- ⚠️ **Setup complexity** - More complex than API calls
- ⚠️ **Lower quality** - Open models may not match Claude Sonnet 4 quality
- ⚠️ **Slower response times** - Especially on CPU-only systems
- ⚠️ **Maintenance** - You manage model updates and performance

### Use Cases
- **High-volume deployments** - Thousands of queries/day where API costs add up
- **Sensitive data** - Government, healthcare, financial institutions
- **Air-gapped environments** - Systems without internet access
- **Research & experimentation** - Testing different models and prompts

---

## Model Options & Recommendations

### Option 1: Ollama (⭐ Recommended for Most Users)

**Why Ollama:**
- Easiest setup (one command)
- OpenAI-compatible API
- Supports Apple Silicon, NVIDIA GPUs, CPU
- Automatic model management
- Active community

**Recommended Models:**

| Model | Size | VRAM | Quality | Speed | Use Case |
|-------|------|------|---------|-------|----------|
| **Llama 3.1 8B** | 4.7GB | 8GB | Good | Fast | Development, testing |
| **Llama 3.1 70B** | 40GB | 48GB | Excellent | Slow | Production (high quality) |
| **Qwen 2.5 14B** | 9GB | 12GB | Very Good | Medium | Balanced production |
| **Mistral 7B** | 4.1GB | 6GB | Good | Fast | Low-resource environments |
| **Mixtral 8x7B** | 26GB | 32GB | Excellent | Medium | High-quality production |

**Quantization Levels:**
- `q4_0` - Fastest, lowest quality (4-bit)
- `q4_K_M` - Balanced (4-bit, medium quality)
- `q5_K_M` - Better quality (5-bit)
- `q8_0` - Best quality, slower (8-bit)
- `fp16` - Full precision (requires most VRAM)

**Installation:**

```bash
# macOS/Linux
curl -fsSL https://ollama.com/install.sh | sh

# Or via Homebrew (macOS)
brew install ollama

# Start Ollama service
ollama serve

# Pull a model (in another terminal)
ollama pull llama3.1:8b
# or for better quality:
ollama pull qwen2.5:14b
# or for production:
ollama pull llama3.1:70b
```

**API Endpoint:** `http://localhost:11434/v1` (OpenAI-compatible)

---

### Option 2: llama.cpp (For Advanced Users)

**Why llama.cpp:**
- Maximum performance optimization
- Runs on CPU efficiently
- Fine-grained control over inference
- Supports many quantization formats

**Installation:**

```bash
# Clone repository
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp

# Build with CPU support
make

# Or build with GPU support (NVIDIA)
make LLAMA_CUBLAS=1

# Or build with Metal support (Apple Silicon)
make LLAMA_METAL=1

# Download a model (GGUF format)
# Example: Llama 3.1 8B Q4_K_M
wget https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf

# Start server
./server -m Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf --host 0.0.0.0 --port 8080
```

**API Endpoint:** `http://localhost:8080/v1` (OpenAI-compatible)

---

### Option 3: vLLM (For Production, GPU Required)

**Why vLLM:**
- Highest throughput for production
- Optimized for serving multiple users
- Advanced batching and caching
- Best for cloud deployments

**Requirements:**
- NVIDIA GPU with 16GB+ VRAM
- CUDA 11.8+
- Linux (Ubuntu recommended)

**Installation:**

```bash
# Install vLLM
pip install vllm

# Start server
python3 -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Meta-Llama-3.1-8B-Instruct \
    --port 8000
```

**API Endpoint:** `http://localhost:8000/v1`

---

### Option 4: LocalAI (Multi-Backend Support)

**Why LocalAI:**
- Supports multiple backend engines (llama.cpp, vLLM, etc.)
- OpenAI-compatible API
- Docker support
- Good for testing different models

**Installation:**

```bash
# Using Docker
docker run -p 8080:8080 \
  -v $PWD/models:/models \
  localai/localai:latest \
  --models-path /models \
  --context-size 4096
```

---

### Recommended Configuration by Use Case

**Development/Testing (Low Resources):**
- Model: Llama 3.1 8B (Q4_K_M)
- Backend: Ollama
- VRAM: 6-8GB
- Expected speed: 5-10 tokens/sec on GPU, 1-3 on CPU

**Production (Balanced):**
- Model: Qwen 2.5 14B (Q5_K_M)
- Backend: Ollama or vLLM
- VRAM: 12-16GB
- Expected speed: 15-25 tokens/sec on GPU

**Production (High Quality):**
- Model: Llama 3.1 70B (Q4_K_M) or Mixtral 8x7B
- Backend: vLLM
- VRAM: 40-48GB
- Expected speed: 10-20 tokens/sec on high-end GPU

---

## Installation & Setup

### Step 1: Install Model Backend

Choose one option from above. For this guide, we'll use **Ollama** as it's the easiest:

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama (in one terminal)
ollama serve

# Pull model (in another terminal)
# For development:
ollama pull llama3.1:8b

# For production (better quality):
ollama pull qwen2.5:14b
```

### Step 2: Install Python Client

```bash
# Activate your virtual environment
source venv/bin/activate

# Install OpenAI client (works with Ollama)
pip install openai
```

### Step 3: Update requirements.txt

Add the OpenAI client and remove the Anthropic client:

```bash
# Edit requirements.txt
# Remove or comment out:
# anthropic>=0.18.0

# Add:
openai>=1.0.0
```

---

## Code Changes Required

You need to update three main files:

### File 1: `rag_system.py`

#### Replace Anthropic client initialization with OpenAI client:

**BEFORE:**
```python
import anthropic
from anthropic import Anthropic

class RAGSystem:
    def __init__(self):
        self.anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
```

**AFTER:**
```python
from openai import OpenAI

class RAGSystem:
    def __init__(self):
        # Initialize local model client (Ollama/llama.cpp/vLLM)
        self.llm_client = OpenAI(
            base_url=os.getenv("LOCAL_MODEL_URL", "http://localhost:11434/v1"),
            api_key="not-needed"  # Local models don't need API key
        )
        self.model_name = os.getenv("LOCAL_MODEL_NAME", "llama3.1:8b")
```

#### Update `generate_response()` method:

**BEFORE:**
```python
def generate_response(self, query: str, context_docs: List[Dict], max_tokens: int = 2000) -> str:
    """Generate response using Claude with retrieved context."""

    # Build context from documents
    context_text = "\n\n".join([
        f"Source {i+1} ({doc.get('source_type', 'unknown')}): {doc.get('url', 'N/A')}\n{doc['content']}"
        for i, doc in enumerate(context_docs)
    ])

    # Create prompt
    prompt = f"""You are a professional correspondence writer for the Federal Reserve...

Context from Federal Reserve documents:
{context_text}

Question: {query}

Please provide a professional response..."""

    # Call Claude API
    response = self.anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text
```

**AFTER:**
```python
def generate_response(self, query: str, context_docs: List[Dict], max_tokens: int = 2000) -> str:
    """Generate response using local model with retrieved context."""

    # Build context from documents
    context_text = "\n\n".join([
        f"Source {i+1} ({doc.get('source_type', 'unknown')}): {doc.get('url', 'N/A')}\n{doc['content']}"
        for i, doc in enumerate(context_docs)
    ])

    # Create system prompt
    system_prompt = """You are a professional correspondence writer for the Federal Reserve Board of Governors.

Your task is to provide accurate, professional responses to questions about Federal Reserve policies, operations, and monetary policy.

IMPORTANT GUIDELINES:
1. Base responses ONLY on the provided source documents
2. Include inline citations in the format [Source N] after each fact
3. Write in a professional, formal tone suitable for official correspondence
4. If information is not in the sources, clearly state this
5. Structure responses with clear paragraphs
6. Focus on accuracy and clarity"""

    # Create user prompt
    user_prompt = f"""Context from Federal Reserve documents:
{context_text}

Question: {query}

Please provide a professional response with inline citations [Source N]."""

    # Call local model API (OpenAI-compatible)
    response = self.llm_client.chat.completions.create(
        model=self.model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=max_tokens,
        temperature=0.3,  # Lower temperature for more factual responses
        top_p=0.9
    )

    return response.choices[0].message.content
```

#### Update `detect_query_category()` method:

**BEFORE:**
```python
def detect_query_category(self, query: str) -> Optional[str]:
    """Detect the category of the query using Claude."""

    prompt = f"""Analyze this Federal Reserve query and categorize it...

Query: {query}

Category (one word):"""

    response = self.anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=50,
        messages=[{"role": "user", "content": prompt}]
    )

    category = response.content[0].text.strip()
    return category if category else None
```

**AFTER:**
```python
def detect_query_category(self, query: str) -> Optional[str]:
    """Detect the category of the query using local model."""

    system_prompt = """You are a Federal Reserve query classifier. Analyze queries and categorize them into ONE of these categories:

- Interest Rates
- Banking Regulation
- Monetary Policy
- Currency
- Payment Systems
- Financial Stability
- Economic Data
- Consumer Protection
- Other

Respond with ONLY the category name, nothing else."""

    user_prompt = f"Query: {query}\n\nCategory:"

    try:
        response = self.llm_client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=50,
            temperature=0.1  # Very low temperature for consistent categorization
        )

        category = response.choices[0].message.content.strip()
        return category if category else None
    except Exception as e:
        print(f"Error detecting category: {e}")
        return None
```

---

### File 2: `feedback_analyzer.py`

#### Replace Anthropic client with OpenAI client:

**BEFORE:**
```python
import anthropic
from anthropic import Anthropic

class FeedbackAnalyzer:
    def __init__(self):
        self.anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
```

**AFTER:**
```python
from openai import OpenAI

class FeedbackAnalyzer:
    def __init__(self):
        # Initialize local model client
        self.llm_client = OpenAI(
            base_url=os.getenv("LOCAL_MODEL_URL", "http://localhost:11434/v1"),
            api_key="not-needed"
        )
        self.model_name = os.getenv("LOCAL_MODEL_NAME", "llama3.1:8b")
```

#### Update `analyze_comment()` method:

**BEFORE:**
```python
def analyze_comment(self, comment: str, rating: int) -> Dict:
    """Analyze feedback comment using Claude."""

    prompt = f"""Analyze this user feedback..."""

    response = self.anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    # Parse JSON response
    result = json.loads(response.content[0].text)
    return result
```

**AFTER:**
```python
def analyze_comment(self, comment: str, rating: int) -> Dict:
    """Analyze feedback comment using local model."""

    system_prompt = """You are a feedback analysis AI. Analyze user feedback and extract structured information.

Respond ONLY with valid JSON in this exact format:
{
  "sentiment": "positive" | "neutral" | "negative",
  "confidence": 0.0-1.0,
  "issues": ["outdated_info", "incorrect_info", "too_technical", "missing_citations", "irrelevant", "unclear"],
  "severity": "minor" | "moderate" | "severe",
  "summary": "Brief summary of the feedback"
}

Valid issue types:
- outdated_info: Information appears outdated
- incorrect_info: Information is factually incorrect
- too_technical: Response is too technical/complex
- missing_citations: Lacks proper citations
- irrelevant: Response doesn't address the question
- unclear: Response is confusing or unclear"""

    user_prompt = f"""Rating: {rating}/5
Comment: {comment}

Analyze this feedback and provide JSON output:"""

    try:
        response = self.llm_client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=500,
            temperature=0.2,  # Low temperature for consistent JSON output
            response_format={"type": "json_object"}  # Force JSON output (if model supports it)
        )

        result_text = response.choices[0].message.content

        # Parse JSON response
        result = json.loads(result_text)

        # Validate and set defaults
        result.setdefault("sentiment", "neutral")
        result.setdefault("confidence", 0.5)
        result.setdefault("issues", [])
        result.setdefault("severity", "minor")
        result.setdefault("summary", comment[:100])

        return result

    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from model: {e}")
        print(f"Model response: {result_text}")
        # Return safe default
        return {
            "sentiment": "neutral",
            "confidence": 0.5,
            "issues": [],
            "severity": "minor",
            "summary": comment[:100]
        }
    except Exception as e:
        print(f"Error analyzing comment: {e}")
        return {
            "sentiment": "neutral",
            "confidence": 0.5,
            "issues": [],
            "severity": "minor",
            "summary": comment[:100]
        }
```

---

### File 3: `.env` Configuration

Update your `.env` file:

**REMOVE:**
```bash
ANTHROPIC_API_KEY=sk-ant-...
```

**ADD:**
```bash
# Local Model Configuration
LOCAL_MODEL_URL=http://localhost:11434/v1  # Ollama default
LOCAL_MODEL_NAME=llama3.1:8b               # Or qwen2.5:14b, mistral:7b, etc.

# For llama.cpp:
# LOCAL_MODEL_URL=http://localhost:8080/v1

# For vLLM:
# LOCAL_MODEL_URL=http://localhost:8000/v1
# LOCAL_MODEL_NAME=meta-llama/Meta-Llama-3.1-8B-Instruct

# PII Redaction (still works with local models)
ENABLE_PII_REDACTION=true
```

---

### File 4: `streamlit_app.py` (Optional UI Updates)

Add information about the local model in the sidebar:

```python
# In the sidebar
with st.sidebar:
    st.title("Federal Reserve RAG")

    # Add model info
    model_info = os.getenv("LOCAL_MODEL_NAME", "llama3.1:8b")
    st.info(f"🤖 Model: {model_info}")

    # Rest of sidebar code...
```

---

## Configuration

### Environment Variables

Create or update `.env`:

```bash
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/fed_rag

# Local Model Configuration
LOCAL_MODEL_URL=http://localhost:11434/v1
LOCAL_MODEL_NAME=llama3.1:8b

# Model Parameters (optional)
MODEL_TEMPERATURE=0.3          # 0.0-1.0, lower = more factual
MODEL_MAX_TOKENS=2000          # Maximum response length
MODEL_TOP_P=0.9                # Nucleus sampling parameter

# PII Redaction
ENABLE_PII_REDACTION=true

# Performance Tuning (optional)
MODEL_CONTEXT_WINDOW=4096      # Model's context window size
MODEL_NUM_THREADS=4            # CPU threads (for llama.cpp)
MODEL_GPU_LAYERS=35            # GPU layers (for llama.cpp)
```

### Model-Specific Settings

**For Ollama:**
```bash
LOCAL_MODEL_URL=http://localhost:11434/v1
LOCAL_MODEL_NAME=llama3.1:8b
# Or: qwen2.5:14b, mistral:7b, mixtral:8x7b
```

**For llama.cpp:**
```bash
LOCAL_MODEL_URL=http://localhost:8080/v1
LOCAL_MODEL_NAME=llama-3.1-8b-instruct
# Model name depends on what you loaded in llama.cpp
```

**For vLLM:**
```bash
LOCAL_MODEL_URL=http://localhost:8000/v1
LOCAL_MODEL_NAME=meta-llama/Meta-Llama-3.1-8B-Instruct
# Use HuggingFace model identifier
```

---

## Testing & Validation

### Step 1: Test Model Connection

Create a test script `test_local_model.py`:

```python
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize client
client = OpenAI(
    base_url=os.getenv("LOCAL_MODEL_URL"),
    api_key="not-needed"
)

# Test simple completion
response = client.chat.completions.create(
    model=os.getenv("LOCAL_MODEL_NAME"),
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say hello!"}
    ],
    max_tokens=50
)

print(f"Model response: {response.choices[0].message.content}")
print(f"✅ Local model is working!")
```

Run test:
```bash
python3 test_local_model.py
```

### Step 2: Test RAG System

```bash
# Start Streamlit app
streamlit run streamlit_app.py

# Test a simple query
# Go to http://localhost:8501
# Ask: "What is the federal funds rate?"
```

### Step 3: Validate Response Quality

Compare responses with previous Claude Sonnet 4 responses:

**Checklist:**
- [ ] Response includes inline citations [Source N]
- [ ] Response is factually accurate based on context
- [ ] Response is professionally written
- [ ] Response addresses the query completely
- [ ] No hallucinations or unsupported claims
- [ ] Proper formatting and structure

### Step 4: Test Feedback Analysis

```bash
# Submit feedback on a response
# Check if sentiment analysis works correctly
# Verify JSON parsing doesn't fail
```

### Step 5: Performance Testing

```python
# Create performance_test.py
import time
from rag_system import RAGSystem

rag = RAGSystem()

queries = [
    "What is quantitative easing?",
    "How does the Federal Reserve control inflation?",
    "What is the federal funds rate?"
]

for query in queries:
    start = time.time()
    response = rag.process_query(query)
    elapsed = time.time() - start

    print(f"Query: {query}")
    print(f"Time: {elapsed:.2f}s")
    print(f"Response length: {len(response['response'])} chars")
    print("-" * 50)
```

**Target Performance:**
- GPU (8GB VRAM): 2-5 seconds per response
- CPU only: 10-30 seconds per response
- Production (large models): 5-15 seconds per response

---

## Performance Optimization

### 1. Choose the Right Quantization

**For Speed (Development):**
```bash
# Ollama
ollama pull llama3.1:8b-q4_0        # Fastest

# llama.cpp
wget <url-to-model>-Q4_0.gguf       # 4-bit quantization
```

**For Quality (Production):**
```bash
# Ollama
ollama pull llama3.1:8b-q8_0        # Best quality

# llama.cpp
wget <url-to-model>-Q8_0.gguf       # 8-bit quantization
```

### 2. GPU Acceleration

**Ollama (automatic):**
```bash
# Ollama automatically uses GPU if available
# Check GPU usage:
nvidia-smi  # NVIDIA
# or
top         # macOS with Metal
```

**llama.cpp:**
```bash
# For NVIDIA GPU:
make clean
make LLAMA_CUBLAS=1

# For Apple Silicon:
make clean
make LLAMA_METAL=1

# Start with GPU layers
./server -m model.gguf --n-gpu-layers 35  # Adjust based on VRAM
```

### 3. Reduce Context Window

If running into memory issues:

```python
# In rag_system.py, limit context documents
def retrieve_documents(self, query: str, limit: int = 5):  # Reduce from 10 to 5
    # ... existing code
```

### 4. Batch Processing

For high-volume scenarios, implement batching:

```python
# Process multiple queries at once
responses = []
for query_batch in batches(queries, batch_size=4):
    # Process batch
    batch_responses = process_batch(query_batch)
    responses.extend(batch_responses)
```

### 5. Caching

Cache common queries to avoid re-computation:

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def generate_response_cached(query: str, context_hash: str):
    # Generate response
    pass
```

### 6. Model Selection by Task

Use different models for different tasks:

```python
# Fast model for categorization
CATEGORIZATION_MODEL = "mistral:7b"  # Fast

# Better model for response generation
RESPONSE_MODEL = "qwen2.5:14b"       # Higher quality

# In code:
def detect_query_category(self, query: str):
    response = self.llm_client.chat.completions.create(
        model=CATEGORIZATION_MODEL,  # Use fast model
        # ...
    )

def generate_response(self, query: str, context_docs: List[Dict]):
    response = self.llm_client.chat.completions.create(
        model=RESPONSE_MODEL,  # Use better model
        # ...
    )
```

---

## Troubleshooting

### Issue: Model responses are low quality

**Solutions:**
1. Use a larger model: `qwen2.5:14b` or `llama3.1:70b`
2. Reduce temperature: Set to 0.1-0.3 for more factual responses
3. Improve prompts: Add more explicit instructions
4. Use better quantization: Q8_0 instead of Q4_0

### Issue: Responses are slow

**Solutions:**
1. Use GPU acceleration (see Performance Optimization)
2. Use smaller model: `llama3.1:8b` instead of `70b`
3. Reduce max_tokens: Set to 1000 instead of 2000
4. Use faster quantization: Q4_0 instead of Q8_0
5. Reduce context: Fewer retrieved documents

### Issue: Model not generating citations

**Solutions:**
1. Strengthen the prompt:
```python
system_prompt = """...
CRITICAL: You MUST include inline citations in the format [Source N] after EVERY fact.
Example: "The federal funds rate is set by the FOMC [Source 1]."
..."""
```

2. Add few-shot examples:
```python
user_prompt = f"""Example response format:
"The Federal Reserve uses three main tools for monetary policy [Source 1]. These include open market operations, the discount rate, and reserve requirements [Source 2]."

Now answer this question:
{query}"""
```

### Issue: JSON parsing errors in feedback analysis

**Solutions:**
1. Add better error handling (already in code above)
2. Use `response_format={"type": "json_object"}` if model supports it
3. Add JSON validation prompt:
```python
system_prompt += "\n\nIMPORTANT: Respond with ONLY valid JSON. No markdown, no explanation, just JSON."
```

### Issue: Out of memory errors

**Solutions:**
1. Use smaller model or lower quantization
2. Reduce batch size
3. Reduce context window:
```bash
# For Ollama
OLLAMA_NUM_PARALLEL=1  # Process one request at a time

# For llama.cpp
./server -m model.gguf --ctx-size 2048  # Reduce from 4096
```

### Issue: Model doesn't follow instructions well

**Solutions:**
1. Use instruction-tuned models: `llama3.1-instruct`, `qwen2.5-instruct`
2. Use chat templates correctly
3. Add examples in the prompt (few-shot learning)
4. Try different models - some follow instructions better than others

### Issue: Ollama connection errors

**Solutions:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Restart Ollama
pkill ollama
ollama serve

# Check logs
journalctl -u ollama -f  # Linux
# or
~/Library/Logs/Ollama/  # macOS
```

### Issue: Different responses each time

**Solutions:**
Set temperature to 0 for deterministic output:
```python
response = self.llm_client.chat.completions.create(
    model=self.model_name,
    temperature=0,  # Deterministic
    # ...
)
```

---

## Quality Comparison: Claude vs Local Models

### Expected Quality Levels

| Aspect | Claude Sonnet 4 | Llama 3.1 70B | Qwen 2.5 14B | Llama 3.1 8B |
|--------|----------------|---------------|--------------|--------------|
| **Factual Accuracy** | Excellent | Very Good | Good | Good |
| **Citation Quality** | Excellent | Good | Fair-Good | Fair |
| **Writing Style** | Excellent | Very Good | Good | Good |
| **Instruction Following** | Excellent | Good | Good | Fair |
| **Consistency** | Excellent | Good | Fair | Fair |
| **Hallucinations** | Rare | Occasional | Occasional | More Common |

### Recommendations by Deployment

**Personal/Development:**
- Llama 3.1 8B Q4_K_M
- Acceptable quality, fast iteration

**Small Production:**
- Qwen 2.5 14B Q5_K_M
- Good balance of quality and speed

**High-Volume Production:**
- Llama 3.1 70B Q4_K_M or Mixtral 8x7B
- Best open-source quality
- Still cheaper than API at scale

**Enterprise Production:**
- Consider keeping Claude Sonnet 4
- Or fine-tune Llama 3.1 70B on your data

---

## Advanced: Fine-Tuning for Better Results

For production deployments, consider fine-tuning a local model on Federal Reserve content:

### Step 1: Prepare Training Data

```python
# Create training_data.jsonl with examples
# Format: {"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}

# Example entry:
{
  "messages": [
    {"role": "system", "content": "You are a Federal Reserve correspondence writer..."},
    {"role": "user", "content": "What is the federal funds rate?"},
    {"role": "assistant", "content": "The federal funds rate is the target interest rate set by the Federal Open Market Committee [Source 1]..."}
  ]
}
```

### Step 2: Fine-Tune Model

```bash
# Using Ollama Modelfile
# Create Modelfile:
FROM llama3.1:8b
PARAMETER temperature 0.3
SYSTEM """You are a professional Federal Reserve correspondence writer..."""

# Build custom model
ollama create fed-reserve-assistant -f Modelfile

# Use in app
LOCAL_MODEL_NAME=fed-reserve-assistant
```

For more advanced fine-tuning, see:
- [Axolotl](https://github.com/OpenAccess-AI-Collective/axolotl) - Training framework
- [Unsloth](https://github.com/unslothai/unsloth) - Fast fine-tuning
- [PEFT/LoRA](https://github.com/huggingface/peft) - Parameter-efficient fine-tuning

---

## Migration Checklist

Use this checklist to ensure complete migration:

- [ ] Choose local model backend (Ollama/llama.cpp/vLLM)
- [ ] Install backend and pull/download model
- [ ] Test model connection with simple query
- [ ] Update `requirements.txt` (remove anthropic, add openai)
- [ ] Update `rag_system.py`:
  - [ ] Replace Anthropic client with OpenAI client
  - [ ] Update `generate_response()` method
  - [ ] Update `detect_query_category()` method
- [ ] Update `feedback_analyzer.py`:
  - [ ] Replace Anthropic client with OpenAI client
  - [ ] Update `analyze_comment()` method
  - [ ] Add JSON parsing error handling
- [ ] Update `.env` file with local model configuration
- [ ] Remove `ANTHROPIC_API_KEY` from environment
- [ ] Test complete RAG flow with sample queries
- [ ] Validate response quality
- [ ] Test feedback analysis
- [ ] Performance benchmark
- [ ] Update documentation
- [ ] Deploy to production environment

---

## Cost Analysis

### API Costs (Claude Sonnet 4)

Assuming 1000 queries/month:
- Input: ~500K tokens/month × $3/1M = $1.50
- Output: ~200K tokens/month × $15/1M = $3.00
- **Total: ~$4.50/month for 1000 queries**

At scale (10,000 queries/month):
- **~$45/month**

At high volume (100,000 queries/month):
- **~$450/month**

### Local Model Costs

**One-time hardware investment:**
- GPU (RTX 3090 24GB): ~$1,500
- Or cloud GPU: ~$0.50-2/hour

**Ongoing costs:**
- Electricity: ~$10-30/month
- Or cloud GPU (24/7): ~$360-1,440/month

**Break-even analysis:**
- Personal GPU pays for itself after ~33 months at 1000 queries/month
- But pays for itself immediately at 10,000+ queries/month or for privacy-sensitive data

---

## Conclusion

### When to Use Local Models

✅ **Use local models if:**
- You process 10,000+ queries per month
- You have sensitive data (PII, regulated industries)
- You need offline operation
- You have GPU hardware available
- API costs are a concern
- You want full control over the system

❌ **Stick with Claude if:**
- You process <5,000 queries per month
- Response quality is critical
- You don't have GPU hardware
- You want simplest deployment
- Development time is limited

### Recommended Migration Path

1. **Start small:** Test with Ollama + Llama 3.1 8B locally
2. **Evaluate quality:** Compare responses with Claude
3. **Optimize:** Try different models and prompts
4. **Scale:** Move to larger model or better hardware
5. **Fine-tune:** (Optional) Train on your specific use case

---

## Additional Resources

- [Ollama Documentation](https://ollama.com/docs)
- [llama.cpp GitHub](https://github.com/ggerganov/llama.cpp)
- [vLLM Documentation](https://docs.vllm.ai/)
- [HuggingFace Model Hub](https://huggingface.co/models)
- [Awesome LLM](https://github.com/Hannibal046/Awesome-LLM) - Curated list of LLM resources

---

**Questions?** Common issues:
- Model not responding → Check if Ollama/llama.cpp server is running
- Low quality responses → Try larger model or better quantization
- Slow performance → Enable GPU acceleration
- Out of memory → Use smaller model or reduce context window
