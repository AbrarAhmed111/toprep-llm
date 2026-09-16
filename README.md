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
- **Seamless Provider Switching** - Support for **Google Gemini** (up to 4 rotated keys + a quality-fallback model), **Groq**, **OpenAI**, **Mistral**, **Cerebras**
- **Automatic Failover** - Tries deployments in order (Gemini → Groq → OpenAI → Mistral → Cerebras), skipping any that aren't configured
- **Provider Health Monitoring** - Cooldown tracking so a recently-failed deployment isn't retried immediately
- **Error Classification** - Distinguishes retryable (rate limit, 5xx, timeout) from non-retryable (bad request, invalid key) failures

### 💬 Chat
- `POST /api/chat` - Non-streaming JSON chat completions with automatic failover across whichever of the 5 providers above are configured
- `GET /api/chat/fast-prompts` - Retrieve pre-built prompts for quick interactions
- Multi-turn conversation support with message history
- Not currently wired into the ToPrep frontend — a standalone capability available for a future chat UI

### 🧠 AI Explanations & Practice Questions
- `POST /api/ai/explain` - A brief 2-3 line explanation of a topic, given its name and preparation context
- `POST /api/ai/questions` - 3-5 expected interview/exam questions for a topic
- Both go through the same multi-provider gateway and return which `provider`/`model` answered
- Powers `TopicContainer.tsx` in the ToPrep frontend (via `src/lib/api/aiService.ts`)

### 🧭 AI Topic Organization
- `POST /api/topics/organize` - Suggest a learning order for a preparation's topics
- Orders topics by prerequisites, dependencies, and conceptual progression
- Returns a strict permutation of the input topic IDs plus a one-sentence rationale
- Ordering only — never applied silently; the caller shows the suggestion for explicit review/accept

### 📄 PDF Topic Extraction
- `POST /api/topics/extract-pdf` - Upload a PDF, get back a flat list of learning topics
- **Pipeline**: validate → extract text (PyMuPDF, page-level, TOC-aware) → OCR fallback for scanned pages → clean (strip repeated headers/footers/page numbers) → chunk (TOC-aligned or windowed) → LLM topic extraction per chunk → LLM normalization/dedup across chunks
- Every LLM call goes through the same multi-provider gateway as chat/topic-organization — automatic failover applies here too
- Naming variants of the same concept (e.g. "React Hooks" / "Hooks in React") are merged into one canonical topic; related-but-distinct concepts (e.g. "React State" vs "Redux") are kept separate
- User-readable error responses for bad/corrupt/encrypted PDFs and pipeline timeouts — never a raw 500/stack trace
- See `doc/pdf-extraction-phases.md` (in the main `toprep` repo) for the full phase-by-phase design

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
│   │       ├── ai.py                 # AI topic explanation + practice question endpoints
│   │       ├── topics.py             # AI topic organization + PDF topic extraction endpoints
│   │       └── health.py             # Health check endpoint
│   │
│   ├── core/                         # Core Configuration
│   │   ├── config.py                 # Pydantic settings (environment vars)
│   │   └── logging.py                # Logging configuration
│   │
│   ├── services/                     # Business Logic Layer
│   │   ├── chat_service.py           # Orchestrates message normalization → LLM
│   │   ├── ai_service.py             # Topic explanation + practice question prompts → LLM
│   │   ├── topic_organizer_service.py# Builds the ordering prompt, validates the AI's permutation
│   │   ├── llm_json.py               # Shared "extract a JSON object from an LLM reply" helper
│   │   ├── pdf_extraction_service.py # Orchestrates the PDF -> topics pipeline (below)
│   │   ├── pdf/                      # PDF ingestion stages
│   │   │   ├── extractor.py          #   Validate + extract text (PyMuPDF) + OCR fallback
│   │   │   ├── cleaner.py            #   Strip repeated headers/footers/page numbers
│   │   │   └── chunker.py            #   TOC-aligned or windowed chunking
│   │   └── topic_extraction/         # LLM stages over PDF chunks
│   │       ├── extractor.py          #   Per-chunk topic extraction via the LLM gateway
│   │       ├── normalizer.py         #   Cross-chunk normalization & deduplication
│   │       └── prompts.py            #   System/user prompts for both stages
│   │
│   ├── gateway/                      # LLM Gateway & Failover
│   │   ├── gateway.py                # Multi-provider LLM client
│   │   ├── deployment.py             # Provider deployment config
│   │   ├── error_classifier.py       # Error categorization
│   │   └── status.py                 # Provider health tracking
│   │
│   └── schemas/                      # Pydantic Data Models
│       ├── chat.py                   # Chat request/response schemas
│       ├── ai.py                     # Explanation/questions request/response schemas
│       ├── topics.py                 # Topic organization request/response schemas
│       └── pdf.py                    # PDF document/chunk/topic + extract-pdf response schemas
│
├── tests/                            # Test Suite
│   ├── conftest.py                   # Pytest configuration
│   ├── test_api.py                   # API endpoint tests
│   ├── test_gateway.py               # LLM gateway tests
│   ├── test_topic_organizer.py       # AI topic organizer service & endpoint tests
│   ├── test_pdf_extractor.py         # PDF validation, text extraction, OCR fallback
│   ├── test_pdf_cleaner.py           # Header/footer/page-number cleaning
│   ├── test_pdf_chunker.py           # TOC-aligned & windowed chunking
│   ├── test_pdf_topic_extractor.py   # LLM topic extraction per chunk
│   ├── test_pdf_topic_normalizer.py  # LLM normalization & deduplication
│   └── test_pdf_topics_endpoint.py   # POST /api/topics/extract-pdf, end to end
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
| **AI Service** | Explanations & practice questions | Topic + preparation context → LLM Gateway |
| **Topic Organizer** | AI-assisted ordering | Index-based JSON prompt → strict permutation validation |
| **PDF Extraction Pipeline** | PDF → learning topics | Validate/extract (PyMuPDF + OCR) → clean → chunk → LLM extract → LLM normalize/dedup |

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

### 3. Configure Your LLM Provider(s)
Edit `.env` and add a key for any of the 5 supported providers — the gateway only
loads deployments whose key is set, and tries them in this order: **Gemini → Groq →
OpenAI → Mistral → Cerebras**. Configure just one, or several for real failover.

**Google Gemini** (supports up to 4 rotated keys, plus an optional quality-fallback model)
```env
GOOGLE_API_KEY1=your_key
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_FALLBACK_MODEL=gemini-2.5-flash
```

**Groq**
```env
GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-20b
GROQ_FALLBACK_MODEL=openai/gpt-oss-120b
```

**OpenAI**
```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

**Mistral**
```env
MISTRAL_API_KEY=...
MISTRAL_MODEL=mistral-small-latest
```

**Cerebras**
```env
CEREBRAS_API_KEY=...
CEREBRAS_MODEL=qwen-3.8-27b
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

### 4. AI Topic Explanation & Practice Questions
```bash
curl -X POST http://localhost:8000/api/ai/explain \
  -H "Content-Type: application/json" \
  -d '{
    "topic_name": "React Hooks",
    "preparation_type": "Interview",
    "preparation_description": "Full Stack Developer Interview"
  }'

curl -X POST http://localhost:8000/api/ai/questions \
  -H "Content-Type: application/json" \
  -d '{
    "topic_name": "React Hooks",
    "preparation_type": "Interview"
  }'
```

`/explain` returns `{"explanation": "...", "provider": "...", "model": "..."}` (a 2-3 line
explanation); `/questions` returns `{"questions": [...], "provider": "...", "model": "..."}`
(3-5 expected questions). `preparation_type`/`preparation_description` are optional context.

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

### 6. PDF Topic Extraction
```bash
curl -X POST http://localhost:8000/api/topics/extract-pdf \
  -F "file=@interview-guide.pdf;type=application/pdf"
```

Returns `{"topics": ["React Hooks", "JavaScript Promises", ...]}` — a flat, deduplicated
list ready to feed into a bulk-add-topics flow. Rejects non-PDF uploads with `400`,
unreadable/encrypted/empty PDFs with `422`, and an overly slow extraction with `504` —
all with a plain-English `detail` message, never a stack trace.

---

## 🔧 Configuration

### Environment Variables (`.env`)

**LLM Provider Configuration** (configure at least one; see [Quickstart](#3-configure-your-llm-providers) for per-provider details):
```env
GOOGLE_API_KEY1=          # up to GOOGLE_API_KEY4
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_FALLBACK_MODEL=gemini-2.5-flash

GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-20b
GROQ_FALLBACK_MODEL=openai/gpt-oss-120b

OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

MISTRAL_API_KEY=
MISTRAL_MODEL=mistral-small-latest

CEREBRAS_API_KEY=
CEREBRAS_MODEL=qwen-3.8-27b
```

**Gateway Configuration:**
```env
GATEWAY_MAX_ATTEMPTS=10
GATEWAY_COOLDOWN_SECONDS=60
```

**YouTube Configuration (reserved, currently unused):**
```env
YOUTUBE_API_KEY=your_youtube_data_api_key_here
YOUTUBE_API_BASE_URL=https://www.googleapis.com/youtube/v3   # Optional
YOUTUBE_REQUEST_TIMEOUT=15
YOUTUBE_DEFAULT_MAX_RESULTS=10
YOUTUBE_MAX_RESULTS_LIMIT=25
```
The backend's YouTube search route/service were removed in favor of a frontend-only
implementation. These `Settings` fields still exist but nothing currently reads them.

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
- `python-multipart` - Multipart form parsing (required for the PDF upload endpoint)

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
| **Topic Explanations** | `POST /api/ai/explain` | TopicContainer.tsx (via `lib/api/aiService.ts`) |
| **Practice Questions** | `POST /api/ai/questions` | TopicContainer.tsx (via `lib/api/aiService.ts`) |
| **Topic Ordering** | `POST /api/topics/organize` | AiOrganizeButton.tsx |
| **PDF Topic Extraction** | `POST /api/topics/extract-pdf` | AddTopicPanel.tsx |

`POST /api/chat` and `GET /api/chat/fast-prompts` are implemented and tested but not
currently called by the frontend — available for a future chat UI.

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
