<div align="center">

<a href="https://www.abrarahmed.pro" target="_blank">
  <img src="https://www.abrarahmed.pro/assets/devAbby-fulllogo-C9-MX7QK.png" alt="Built by Abrar Ahmed" height="65" />
</a>

# 🚀 LLM FastAPI RAG Starter Template

**A production-ready, domain-agnostic RAG (Retrieval-Augmented Generation) backend template** for building intelligent LLM applications with grounded retrieval, multi-provider failover, and intent-based routing.

Built by **[Abrar Ahmed](https://www.abrarahmed.pro)** | Managed with [uv](https://docs.astral.sh/uv/)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Package Manager](https://img.shields.io/badge/managed%20by-uv-DE5FE9.svg?logo=astral&logoColor=white)](https://docs.astral.sh/uv/)
[![Built By](https://img.shields.io/badge/author-Abrar%20Ahmed-black.svg)](https://www.abrarahmed.pro)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

Designed to be your production-ready foundation for **RAG-powered AI applications**: intelligent chatbots, knowledge base systems, document Q&A engines, semantic search platforms, and grounded generative APIs.

---

## ✨ Core Features

### 🔍 RAG Pipeline (Retrieval-Augmented Generation)
- **Document Ingestion** - Load and process various document formats (Markdown, PDFs, etc.)
- **Intelligent Chunking** - Smart text splitting with configurable chunk sizes and overlap
- **Vector Embeddings** - Generate semantic embeddings for documents (OpenAI, local models)
- **Hybrid Vector Store** - In-memory vector database with semantic + BM25 hybrid search
- **Context Retrieval** - Efficient similarity search with relevance scoring
- **Grounded Response Assembly** - Automatically inject retrieved context into LLM prompts

### 🎯 Intent Detection & Routing
- **Rule-Based Intent Detection** - Zero-LLM offline intent classification
- **Intent Normalization** - Normalize user queries for consistent routing
- **Canned Responses** - Quick dispatch for common intents (zero tokens consumed)
- **Fallback to RAG** - Intelligent fallback when no intent match found
- **Conversational Shortcuts** - Reduce token usage with predefined shortcuts

### 🔄 Multi-Provider LLM Gateway
- **Seamless Provider Switching** - Support for **OpenAI**, **Groq**, **DeepSeek**, **Ollama**, **OpenRouter**, **Together AI**, **vLLM**
- **Automatic Failover** - Fallback to secondary providers on failure
- **Provider Health Monitoring** - Track provider status and availability
- **Error Classification** - Intelligent error categorization and recovery
- **Cost Optimization** - Route to most cost-effective providers

### 💬 Chat & Streaming
- `POST /api/chat` - Standard JSON chat completions
- `POST /api/chat/stream` - Real-time **Server-Sent Events (SSE)** token streaming
- `GET /api/chat/fast-prompts` - Retrieve pre-built prompts for quick interactions
- Multi-turn conversation support with message history

### 🛡️ Production Features
- ⚡ **Powered by `uv`** - Lightning-fast dependency management
- 🔐 **Type-Safe Settings** - Environment variables with pydantic-settings
- 📝 **Structured Logging** - Comprehensive application logging
- 🧪 **Unit Tests Included** - Async tests with pytest and mocking
- 📚 **Auto-Generated Docs** - Interactive Swagger at `/docs` and ReDoc at `/redoc`
- 🌐 **CORS Middleware** - Pre-configured for cross-origin requests
- 🚀 **Async/Await Throughout** - Full async Python for high concurrency

---

## 📊 RAG Concepts Explained

### What is RAG?
**Retrieval-Augmented Generation** augments LLM prompts with relevant context from a knowledge base, enabling:
- ✅ Grounded responses backed by actual documents
- ✅ Reduced hallucinations
- ✅ Up-to-date information (not limited by training data)
- ✅ Custom domain knowledge integration

### RAG Pipeline Flow
```
User Query
    ↓
[Intent Detection] → Matches intent? → Return canned response
    ↓ No
[Vector Store Retrieval] → Search for similar documents
    ↓
[Context Assembly] → Rank and format retrieved chunks
    ↓
[Prompt Injection] → "Given this context: {...}, answer: {query}"
    ↓
[LLM Gateway] → Get response from best available provider
    ↓
Response to User
```

---

## 📁 Project Structure (src/ Folder Convention)

```
src/
├── app/
│   ├── __init__.py
│   ├── main.py                       # FastAPI app initialization & lifecycle
│   │
│   ├── api/                          # HTTP API Layer
│   │   ├── router.py                 # Main API router
│   │   └── routes/
│   │       ├── chat.py               # Chat endpoints
│   │       └── health.py             # Health check endpoint
│   │
│   ├── core/                         # Core Configuration
│   │   ├── config.py                 # Pydantic settings (environment vars)
│   │   └── logging.py                # Logging configuration
│   │
│   ├── services/                     # Business Logic Layer
│   │   └── chat_service.py           # Orchestrates intent → RAG → LLM
│   │
│   ├── rag/                          # RAG Pipeline Components
│   │   ├── pipeline.py               # Main RAG orchestration
│   │   ├── ingestion/
│   │   │   └── loader.py             # Document loading
│   │   ├── chunking/
│   │   │   └── text_splitter.py      # Smart text chunking
│   │   ├── retrieval/
│   │   │   └── vector_store.py       # Vector DB & hybrid search
│   │   └── context/
│   │       └── builder.py            # Context formatting for LLM
│   │
│   ├── gateway/                      # LLM Gateway & Failover
│   │   ├── gateway.py                # Multi-provider LLM client
│   │   ├── deployment.py             # Provider deployment config
│   │   ├── error_classifier.py       # Error categorization
│   │   └── status.py                 # Provider health tracking
│   │
│   ├── intent/                       # Intent Detection & Routing
│   │   ├── detector.py               # Rule-based intent classifier
│   │   ├── normalizer.py             # Query normalization
│   │   ├── responses.py              # Canned responses
│   │   └── types.py                  # Intent type definitions
│   │
│   └── schemas/                      # Pydantic Data Models
│       ├── chat.py                   # Chat request/response schemas
│       └── rag.py                    # RAG-related schemas
│
├── tests/                            # Test Suite
│   ├── conftest.py                   # Pytest configuration
│   ├── test_api.py                   # API endpoint tests
│   ├── test_gateway.py               # LLM gateway tests
│   ├── test_intent_detector.py       # Intent detection tests
│   └── test_rag.py                   # RAG pipeline tests
│
├── knowledge/                        # Knowledge Base
│   └── documents/                    # Sample documents for RAG
│       └── sample_guide.md
│
├── run.py                            # Server entry point
├── pyproject.toml                    # Dependencies & tool config
├── .env.example                      # Environment variables template
└── requirements.txt                  # Dependencies (alternative to uv)
```

### Key Architectural Decisions

| Component | Purpose | Design |
|-----------|---------|--------|
| **RAG Pipeline** | End-to-end retrieval + generation | Modular, chainable stages |
| **Intent Detector** | Route before RAG | Zero-LLM, offline rule-based |
| **LLM Gateway** | Provider abstraction | Multi-provider with failover |
| **Vector Store** | Efficient retrieval | Hybrid (semantic + BM25) |
| **Chat Service** | Orchestration | Combines intent → RAG → LLM |

---

## ⚡ Quickstart

### 1. Prerequisites
Ensure you have [uv](https://docs.astral.sh/uv/) installed:

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Setup Environment
```bash
# Clone or enter your project
cd llm-fastapi-template

# Copy environment file
cp .env.example .env

# Install dependencies with uv
uv sync
```

### 3. Configure Your LLM Provider
Edit `.env` and choose your provider:

**Option A: OpenAI (Default)**
```env
LLM_API_KEY=sk-proj-...
LLM_DEFAULT_MODEL=gpt-4o-mini
```

**Option B: Groq (Fast & Cheap)**
```env
LLM_API_KEY=gsk_...
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_DEFAULT_MODEL=llama-3.3-70b-versatile
```

**Option C: DeepSeek**
```env
LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_DEFAULT_MODEL=deepseek-chat
```

**Option D: Ollama (Free & Local)**
```env
LLM_API_KEY=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_DEFAULT_MODEL=llama3.2
```

**Option E: OpenRouter (200+ Models)**
```env
LLM_API_KEY=sk-or-v1-...
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_DEFAULT_MODEL=anthropic/claude-3.5-sonnet
```

### 4. Add Knowledge Base Documents
Place your markdown documents in `knowledge/documents/`:
```
knowledge/documents/
├── sample_guide.md
├── faq.md
├── documentation.md
└── ...
```

---

## 🏃 Running the Server

Run with uv:
```bash
uv run python run.py
```

Or start directly with uvicorn:
```bash
uv run uvicorn src.app.main:app --reload
```

**Access Points:**
- 🌐 **API Root**: [http://localhost:8000/](http://localhost:8000/)
- 📖 **Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- 📋 **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- ✅ **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 📡 API Endpoints & Examples

### 1. Health Check
```bash
curl http://localhost:8000/health
```

### 2. Chat with RAG
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What does the documentation say about RAG?"}
    ],
    "temperature": 0.7
  }'
```

**Response Flow:**
1. Intent detection (matches or not)
2. If no intent match → Vector store search
3. Relevant documents retrieved
4. Context injected into LLM prompt
5. LLM response grounded in your documents

### 3. Streaming Chat
```bash
curl -N -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Explain vector embeddings"}
    ]
  }'
```

### 4. Fast Prompts
```bash
curl http://localhost:8000/api/chat/fast-prompts
```

Returns pre-built quick prompts for immediate use.

---

## 🔧 Configuration

### Environment Variables (`.env`)

**LLM Configuration:**
```env
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.openai.com/v1           # Optional
LLM_DEFAULT_MODEL=gpt-4o-mini
LLM_TIMEOUT=60
```

**RAG Configuration:**
```env
RAG_CHUNK_SIZE=1000
RAG_CHUNK_OVERLAP=100
RAG_RETRIEVAL_TOP_K=5
RAG_MIN_SIMILARITY_SCORE=0.5
```

**Server Configuration:**
```env
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=development
LOG_LEVEL=INFO
```

**CORS Configuration:**
```env
ALLOWED_ORIGINS=http://localhost:3000,https://example.com
```

---

## 🧪 Testing

Run all tests:
```bash
uv run pytest
```

Run specific test file:
```bash
uv run pytest tests/test_rag.py -v
```

Run with coverage:
```bash
uv run pytest --cov=src.app tests/
```

---

## 📚 How RAG Works in This Template

### 1. **Document Ingestion**
```python
from src.app.rag.ingestion.loader import DocumentLoader

loader = DocumentLoader()
documents = loader.load_documents("knowledge/documents/")
```

### 2. **Chunking**
```python
from src.app.rag.chunking.text_splitter import MarkdownTextSplitter

splitter = MarkdownTextSplitter(chunk_size=1000, overlap=100)
chunks = splitter.split_documents(documents)
```

### 3. **Vector Storage**
```python
from src.app.rag.retrieval.vector_store import InMemoryHybridVectorStore

vector_store = InMemoryHybridVectorStore()
vector_store.add_documents(chunks)
```

### 4. **Retrieval**
```python
results = vector_store.search(
    query="What is RAG?",
    top_k=5,
    min_similarity=0.5
)
```

### 5. **Context Building**
```python
from src.app.rag.context.builder import ContextBuilder

builder = ContextBuilder()
context = builder.build_context(results)
```

### 6. **LLM Invocation**
```python
prompt = f"Given this context: {context}\n\nQuestion: {user_query}"
response = await llm_gateway.generate(prompt)
```

---

## 🛣️ Common Use Cases

### Chatbot with Knowledge Base
- Load company documentation
- User asks question
- System retrieves relevant docs
- LLM grounds response in documentation

### Document Q&A System
- Ingest PDFs/docs
- Allow users to ask questions
- Retrieve most relevant sections
- Generate answers backed by source

### Semantic Search Engine
- Index documents with embeddings
- Search using natural language
- Return ranked results with context

### Customer Support Bot
- Knowledge base of support articles
- Detect customer intent
- Retrieve relevant solutions
- Generate personalized responses

---

## 🔐 Security Considerations

- ✅ API keys stored in `.env` (never committed)
- ✅ Type validation with Pydantic
- ✅ CORS configured for allowed origins
- ✅ Async processing prevents blocking
- ✅ Error handling doesn't leak sensitive info

**Production Deployment:**
- Use environment variables from secrets management
- Enable HTTPS/TLS
- Implement rate limiting
- Add authentication/authorization layer
- Monitor API usage and costs

---

## 📦 Dependencies

**Core:**
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `pydantic` - Data validation

**LLM & AI:**
- `openai` - OpenAI API
- `langchain-core` - LLM abstractions
- `langchain-openai` - OpenAI integration

**Testing:**
- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `httpx` - Async HTTP client

All dependencies managed by `uv` and defined in `pyproject.toml`.

---

## 🚀 Next Steps

1. **Customize Intent Detector** - Add your domain-specific intents in `src/app/intent/detector.py`
2. **Add Domain Documents** - Place your knowledge base in `knowledge/documents/`
3. **Tune RAG Parameters** - Adjust chunk size, similarity thresholds, and retrieval strategies
4. **Extend Chat Service** - Add custom business logic in `src/app/services/chat_service.py`
5. **Monitor & Optimize** - Track provider performance and tune failover strategies

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details

---

## 👨‍💻 Built By

**[Abrar Ahmed](https://www.abrarahmed.pro)** - AI Engineer & Full-Stack Developer

---

## 📝 Contributing

Contributions welcome! Please feel free to submit pull requests or open issues.

---

**Made with ❤️ for the AI community**
```bash
curl -X POST http://localhost:8000/api/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "input": ["Artificial Intelligence", "FastAPI backend template"]
  }'
```

---

## 🧪 Testing

Run the test suite with `uv`:
```bash
uv run pytest
```

---

## 🛠️ Adding New Features to Your Product

When building a new AI product on top of this template:
1. **Add new schemas** in `schemas/` (e.g. `schemas/agent.py` or `schemas/rag.py`).
2. **Add pure logic & prompt templates** in `services/` (e.g. `services/rag.py` or `services/prompts.py`).
3. **Add route handlers** in `api/routers/` (e.g. `api/routers/rag.py`).
4. **Mount router** in `api/main.py` using `app.include_router(...)`.

---

## 👨‍💻 Author & Credits

Built with ❤️ by **[Abrar Ahmed](https://www.abrarahmed.pro)**

<a href="https://www.abrarahmed.pro" target="_blank">
  <img src="https://www.abrarahmed.pro/assets/devAbby-fulllogo-C9-MX7QK.png" alt="devAbby logo" height="50" />
</a>

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.


