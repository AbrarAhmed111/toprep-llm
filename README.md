<div align="center">

<a href="https://www.abrarahmed.pro" target="_blank">
  <img src="https://www.abrarahmed.pro/assets/devAbby-fulllogo-C9-MX7QK.png" alt="Built by Abrar Ahmed" height="65" />
</a>

# 🚀 LLM Gateway Service

**A production-ready FastAPI backend** for chat completions with a multi-provider LLM gateway and automatic failover.

This service powers **[ToPrep](https://github.com/AbrarAhmed111/toprep)** — an AI-powered preparation platform for interviews, exams, and certifications.

Built by **[Abrar Ahmed](https://www.abrarahmed.pro)** | Managed with [uv](https://docs.astral.sh/uv/)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Package Manager](https://img.shields.io/badge/managed%20by-uv-DE5FE9.svg?logo=astral&logoColor=white)](https://docs.astral.sh/uv/)
[![Built By](https://img.shields.io/badge/author-Abrar%20Ahmed-black.svg)](https://www.abrarahmed.pro)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## ✨ Core Features

### 🔄 Multi-Provider LLM Gateway
- **Seamless Provider Switching** - Support for **OpenAI**, **Groq**, **DeepSeek**, **Ollama**, **OpenRouter**, **Together AI**, **vLLM**, **Google Gemini**, **Mistral**, **Cerebras**
- **Automatic Failover** - Fallback to secondary providers on failure
- **Provider Health Monitoring** - Track provider status and availability
- **Error Classification** - Intelligent error categorization and recovery
- **Cost Optimization** - Route to most cost-effective providers

### 💬 Chat & Streaming
- `POST /api/chat` - Standard JSON chat completions with automatic provider failover
  - Supports **Claude** (Anthropic), **GPT** (OpenAI), **Gemini** (Google)
  - Automatic fallback if primary provider fails
  - Streaming and non-streaming modes
- `GET /api/chat/fast-prompts` - Retrieve pre-built prompts for quick interactions
- Multi-turn conversation support with message history

### 🎬 YouTube Topic Search
- `POST /api/youtube/search` - Find videos relevant to a topic
- **Filters** - min/max duration, min/max views, published-date window (any time, past month, past 6 months, past year, or a custom range), language hint, exclude Shorts, exclude live/upcoming streams
- **Sorting** - relevance, views, newest, oldest
- **Results per topic** - capped and configurable via `max_results`

### 🧭 AI Topic Organization
- `POST /api/topics/organize` - Suggest a learning order for a preparation's topics
- Orders topics by prerequisites, dependencies, and conceptual progression
- Returns a strict permutation of the input topic IDs plus a one-sentence rationale
- Ordering only — never applied silently; the caller shows the suggestion for explicit review/accept

### 🛡️ Production Features
- ⚡ **Powered by `uv`** - Lightning-fast dependency management
- 🔐 **Type-Safe Settings** - Environment variables with pydantic-settings
- 📝 **Structured Logging** - Comprehensive application logging
- 🧪 **Unit Tests Included** - Async tests with pytest and mocking
- 📚 **Auto-Generated Docs** - Interactive Swagger at `/docs` and ReDoc at `/redoc`
- 🌐 **CORS Middleware** - Pre-configured for cross-origin requests
- 🚀 **Async/Await Throughout** - Full async Python for high concurrency

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
│   │       ├── youtube.py            # YouTube topic search endpoint
│   │       ├── topics.py             # AI topic organization endpoint
│   │       └── health.py             # Health check endpoint
│   │
│   ├── core/                         # Core Configuration
│   │   ├── config.py                 # Pydantic settings (environment vars)
│   │   └── logging.py                # Logging configuration
│   │
│   ├── services/                     # Business Logic Layer
│   │   ├── chat_service.py           # Orchestrates message normalization → LLM
│   │   ├── youtube_service.py        # YouTube search, enrichment, filtering, sorting
│   │   └── topic_organizer_service.py# Builds the ordering prompt, validates the AI's permutation
│   │
│   ├── gateway/                      # LLM Gateway & Failover
│   │   ├── gateway.py                # Multi-provider LLM client
│   │   ├── deployment.py             # Provider deployment config
│   │   ├── error_classifier.py       # Error categorization
│   │   └── status.py                 # Provider health tracking
│   │
│   └── schemas/                      # Pydantic Data Models
│       ├── chat.py                   # Chat request/response schemas
│       ├── youtube.py                # YouTube search request/response/filter schemas
│       └── topics.py                 # Topic organization request/response schemas
│
├── tests/                            # Test Suite
│   ├── conftest.py                   # Pytest configuration
│   ├── test_api.py                   # API endpoint tests
│   ├── test_gateway.py               # LLM gateway tests
│   ├── test_youtube.py               # YouTube search service & endpoint tests
│   └── test_topic_organizer.py       # AI topic organizer service & endpoint tests
│
├── run.py                            # Server entry point
├── pyproject.toml                    # Dependencies & tool config
├── .env.example                      # Environment variables template
└── requirements.txt                  # Dependencies (alternative to uv)
```

### Key Architectural Decisions

| Component | Purpose | Design |
|-----------|---------|--------|
| **LLM Gateway** | Provider abstraction | Multi-provider with failover |
| **Chat Service** | Orchestration | Normalizes messages → LLM Gateway |
| **YouTube Service** | Topic video search | search.list → videos.list enrichment → filter → sort |
| **Topic Organizer** | AI-assisted ordering | Index-based JSON prompt → strict permutation validation |

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
cd toprep-llm-youtube

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

### 2. Chat
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello, how can you help me?"}
    ],
    "temperature": 0.7
  }'
```

### 3. Fast Prompts
```bash
curl http://localhost:8000/api/chat/fast-prompts
```

Returns pre-built quick prompts for immediate use.

### 4. YouTube Topic Search
```bash
curl -X POST http://localhost:8000/api/youtube/search \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "React hooks",
    "filters": {
      "min_duration_seconds": 300,
      "max_duration_seconds": 1800,
      "min_views": 1000,
      "published_window": "past_year",
      "exclude_shorts": true,
      "exclude_livestreams": true,
      "max_results": 10,
      "sort": "views"
    }
  }'
```

`filters` is optional — omit it entirely for a relevance-sorted, unfiltered search of up to `YOUTUBE_DEFAULT_MAX_RESULTS` videos.

### 5. AI Topic Organization
```bash
curl -X POST http://localhost:8000/api/topics/organize \
  -H "Content-Type: application/json" \
  -d '{
    "preparation_title": "Full Stack Developer Interview",
    "preparation_type": "Interview",
    "topics": [
      {"id": "t1", "name": "React"},
      {"id": "t2", "name": "JavaScript"},
      {"id": "t3", "name": "Next.js"},
      {"id": "t4", "name": "TypeScript"},
      {"id": "t5", "name": "Node.js"}
    ]
  }'
```

Returns `ordered_topic_ids` (a permutation of the input IDs) plus a one-sentence `reasoning`. Requires at least two topics.

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

**Gateway Configuration:**
```env
GATEWAY_MAX_ATTEMPTS=10
GATEWAY_COOLDOWN_SECONDS=60
```

**YouTube Configuration:**
```env
YOUTUBE_API_KEY=your_youtube_data_api_key_here
YOUTUBE_API_BASE_URL=https://www.googleapis.com/youtube/v3   # Optional
YOUTUBE_REQUEST_TIMEOUT=15
YOUTUBE_DEFAULT_MAX_RESULTS=10
YOUTUBE_MAX_RESULTS_LIMIT=25
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

**PDF Ingestion Configuration:**
```env
PDF_MAX_SIZE_BYTES=15728640      # 15MB, matches the frontend's upload cap
PDF_MIN_TEXT_CHARS_PER_PAGE=20   # below this, a page falls back to OCR
PDF_OCR_ENABLED=true             # set false in environments without Tesseract installed
```

OCR fallback (for scanned/image-only PDF pages) uses PyMuPDF's built-in Tesseract
integration and requires a **system-level Tesseract-OCR install** with English
`tessdata` available — this can't be installed via `pip`/`uv` alone. If Tesseract
isn't available in your environment, set `PDF_OCR_ENABLED=false`; text-based PDFs are
unaffected, and pages that would have needed OCR are recorded as `ocr_failed` instead
of aborting the whole document. See `doc/pdf-extraction-phases.md` (in the main
`toprep` repo) for the full pipeline design.

---

## 🧪 Testing

Run all tests:
```bash
uv run pytest
```

Run specific test file:
```bash
uv run pytest tests/test_gateway.py -v
```

Run with coverage:
```bash
uv run pytest --cov=src.app tests/
```

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

**PDF Ingestion:**
- `pymupdf` - PDF validation, text extraction, and OCR fallback

**Testing:**
- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `httpx` - Async HTTP client

All dependencies managed by `uv` and defined in `pyproject.toml`.

---

## 🔗 Integration with ToPrep Frontend

This backend powers the **ToPrep** Next.js frontend with:

| Feature | Endpoint | Frontend Component |
|---------|----------|-------------------|
| **Topic Explanations** | `POST /api/chat` | TopicContainer.tsx |
| **Practice Questions** | `POST /api/chat` | TopicContainer.tsx |
| **Video Search** | `POST /api/youtube/search` | YouTube components |
| **Topic Ordering** | `POST /api/topics/organize` | SectionBoard.tsx |

### Frontend Setup
The frontend expects the backend at:
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Ensure this is configured in the frontend's `.env.local` before starting.

---

## 🛠️ Adding New Features to Your Product

When building a new AI product on top of this service:
1. **Add new schemas** in `schemas/` (e.g. `schemas/agent.py`).
2. **Add pure logic & prompt templates** in `services/`.
3. **Add route handlers** in `api/routes/`.
4. **Mount router** in `api/router.py` using `app.include_router(...)`.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author & Credits

Built with ❤️ by **[Abrar Ahmed](https://www.abrarahmed.pro)**

<a href="https://www.abrarahmed.pro" target="_blank">
  <img src="https://www.abrarahmed.pro/assets/devAbby-fulllogo-C9-MX7QK.png" alt="devAbby logo" height="50" />
</a>
