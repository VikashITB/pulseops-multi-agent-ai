# 🤖 Multi-Agent AI Pipeline

A production-grade FastAPI application that orchestrates a chain of specialised AI agents (Planner → Retriever → Analyzer → Writer → Critic) with async task execution, in-memory state management, Server-Sent Event streaming, and automatic retry handling.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
5. [API Reference](#api-reference)
6. [Agent Pipeline](#agent-pipeline)
7. [Project Structure](#project-structure)
8. [Development](#development)
9. [Testing](#testing)
10. [Deployment](#deployment)
11. [Documentation](#documentation)

---

## Architecture

```
┌─────────────┐  POST /task   ┌──────────────┐   enqueue   ┌──────────────┐
│   Frontend  │ ────────────▶ │   FastAPI    │ ──────────▶ │    Celery    │
│  index.html │               │   (routes)   │             │   Worker     │
│             │ ◀──────────── │              │             │              │
│             │  GET /stream  │  SSE stream  │ ◀─────────  │  Pipeline    │
│             │  (EventSource)│  (asyncio    │  events     │  Execution   │
└─────────────┘               │   Queue)     │             └──────────────┘
                              └──────────────┘                     │
                                      │                            │
                                      ▼                            ▼
                               ┌─────────────┐          ┌──────────────────┐
                               │    Redis    │          │  LLM Provider    │
                               │  (broker +  │          │  (OpenAI / etc.) │
                               │   backend)  │          └──────────────────┘
                               └─────────────┘
```

### Agent Pipeline

```
TaskRequest
    │
    ▼
PlannerAgent    → produces a structured execution plan (JSON steps)
    │
    ▼
RetrieverAgent  → fetches relevant documents / context (streaming)
    │
    ▼
AnalyzerAgent   → extracts key findings from retrieved data (streaming)
    │
    ▼
WriterAgent     → synthesises a polished response / report (streaming)
    │
    ▼
CriticAgent     → reviews and improves the final output (streaming)
    │
    ▼
TaskSummary
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| Docker | ≥ 24 |
| Docker Compose | ≥ 2.20 |
| Python | ≥ 3.11 (local dev only) |

---

## Quick Start

### With Docker Compose (recommended)

```bash
# 1. Clone and enter the project
git clone <repo-url> && cd multi-agent-pipeline

# 2. Copy and edit environment variables
cp .env.example .env
# → Set OPENAI_API_KEY (or your LLM provider key)

# 3. Start everything
docker compose up --build

# Services:
#   API:     http://localhost:8000
#   Docs:    http://localhost:8000/docs
#   Frontend: http://localhost:8000 (serves index.html)
#   Redis:   localhost:6379
```

### Local Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Requires a running Redis instance
docker run -d -p 6379:6379 redis:7-alpine

# Terminal 1 – API
uvicorn app.main:app --reload --port 8000

# Terminal 2 – Celery worker
celery -A app.queue.celery_app worker \
  --loglevel=info --concurrency=4
```

---

## Configuration

All settings live in `app/core/config.py` and are read from environment variables (`.env` file supported via `python-dotenv`).

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Application environment |
| `APP_HOST` | `0.0.0.0` | Application host |
| `APP_PORT` | `8000` | Application port |
| `LLM_PROVIDER` | `openai` | LLM provider (openai, groq, gemini) |
| `OPENAI_API_KEY` | – | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model |
| `GROQ_API_KEY` | – | Groq API key |
| `GROQ_MODEL` | `llama3-70b-8192` | Groq model |
| `GEMINI_API_KEY` | – | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Gemini model |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `CELERY_BROKER_URL` | `redis://localhost:6379/1` | Celery broker URL |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/2` | Celery result backend |
| `AGENT_MAX_RETRIES` | `3` | Maximum agent retry attempts |
| `AGENT_RETRY_BASE_DELAY` | `1.0` | Initial retry delay (seconds) |
| `AGENT_TIMEOUT` | `60` | Agent timeout (seconds) |
| `MAX_BATCH_SIZE` | `10` | Maximum batch size |
| `BATCH_FLUSH_INTERVAL` | `5.0` | Batch flush interval (seconds) |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:8000` | CORS allowed origins (comma-separated) |

---

## API Reference

### `POST /api/v1/task`

Submit a new pipeline task. Returns immediately with a `task_id` and stream URL.

**Request body**

```json
{
  "request": "Explain the impact of transformer architecture on NLP"
}
```

**Response `200 OK`**

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Task submitted successfully",
  "stream_url": "/api/v1/stream/550e8400-e29b-41d4-a716-446655440000"
}
```

---

### `GET /api/v1/task/{task_id}`

Poll the current task status and result.

**Response `200 OK`**

```json
{
  "task_id": "550e8400-...",
  "status": "completed",
  "original_request": "Explain the impact of transformer architecture on NLP",
  "final_output": "The transformer architecture revolutionized NLP...",
  "total_duration_ms": 15000
}
```

Status values: `pending` | `running` | `completed` | `partial` | `failed`

---

### `GET /api/v1/tasks`

List all tasks.

**Response `200 OK`**

```json
[
  {
    "task_id": "550e8400-...",
    "status": "completed",
    "created_at": "2026-04-18T00:00:00"
  }
]
```

---

### `GET /api/v1/stream/{task_id}`

Open an SSE connection for live event streaming.

**Event types**

| Event | Payload | Description |
|-------|---------|-------------|
| `task_started` | `{task_id, message}` | Task started |
| `plan_ready` | `{data, message}` | Plan created |
| `step_started` | `{step_id, agent, message}` | Agent step started |
| `step_progress` | `{step_id, data}` | Token streaming |
| `step_completed` | `{step_id, agent, data}` | Step completed |
| `step_failed` | `{step_id, agent, data}` | Step failed |
| `task_completed` | `{data, message}` | Task completed |
| `task_failed` | `{task_id, message}` | Task failed |

**JavaScript example**

```javascript
const es = new EventSource(`/api/v1/stream/${taskId}`);
es.onmessage = (event) => {
  const payload = JSON.parse(event.data);
  console.log(payload.event, payload.data);
  if (payload.event === "task_completed") {
    es.close();
  }
};
```

---

## Project Structure

```
.
├── app/
│   ├── main.py                  # FastAPI app factory + lifespan
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py            # API endpoints
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py        # Base agent interface
│   │   ├── planner_agent.py     # Plan generation
│   │   ├── retriever_agent.py   # Information retrieval
│   │   ├── analyzer_agent.py    # Analysis
│   │   ├── writer_agent.py      # Content generation
│   │   └── critic_agent.py      # Quality review
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # Pydantic settings
│   │   ├── logger.py            # Structured logging
│   │   ├── llm_provider.py      # LLM abstraction (OpenAI, Groq, Gemini)
│   │   ├── pipeline.py          # Async pipeline execution
│   │   └── orchestrator.py      # In-memory task orchestration
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py           # Pydantic models
│   ├── queue/
│   │   ├── __init__.py
│   │   ├── celery_app.py        # Celery configuration
│   │   └── tasks.py             # Celery task definitions
│   ├── services/
│   │   ├── __init__.py
│   │   └── streaming.py         # SSE event generator
│   └── utils/
│       ├── __init__.py
│       ├── retry.py             # Retry decorators (tenacity)
│       └── helpers.py           # Utility functions
├── frontend/
│   ├── index.html               # Single-page UI
│   ├── style.css                # Styling
│   └── script.js                # JavaScript logic
├── docs/
│   ├── system_design.md
│   └── postmortem.md
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Development

### Code style

```bash
ruff check . && ruff format .
mypy app/
```

### Adding a new agent

1. Create `app/agents/my_agent.py` inheriting from `BaseAgent`.
2. Implement the `agent_type` property and `_run()` method.
3. Register in `app/agents/__init__.py` `AGENT_REGISTRY`.
4. Add to `AgentType` enum in `app/models/schemas.py`.

---

## Testing

```bash
pytest tests/ -v --cov=app --cov-report=term-missing

# Integration tests (requires Docker)
docker compose -f docker-compose.test.yml up --abort-on-container-exit
```

---

## Deployment

### Frontend Deployment (Vercel)

1. Push your code to GitHub
2. Import project in Vercel
3. Set root directory to `frontend`
4. Deploy

The `vercel.json` config handles static file serving.

### Backend Deployment (Render)

1. Push your code to GitHub
2. Create new Web Service on Render
3. Connect your GitHub repository
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Add environment variables:
   - `APP_ENV=production`
   - `REDIS_URL` (use Upstash Redis for production)
   - `LLM_PROVIDER` (openai/groq/gemini)
   - `OPENAI_API_KEY` or `GROQ_API_KEY` or `GEMINI_API_KEY`
   - `CORS_ORIGINS=https://your-frontend.vercel.app`

### Backend Deployment (Railway)

Alternative to Render using `railway.toml`:

```bash
railway login
railway init
railway up
```

### Redis (Upstash)

For production, use Upstash Redis:

1. Create free Redis database on Upstash
2. Copy connection URL (format: `rediss://default:password@host:port`)
3. Set `REDIS_URL` environment variable

### Docker Production

```bash
# Build and run with production config
docker compose -f docker-compose.prod.yml up --build -d
```

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Required
LLM_PROVIDER=groq
GROQ_API_KEY=your_key_here
REDIS_URL=rediss://default:password@host:port

# Production CORS
CORS_ORIGINS=https://your-frontend.vercel.app,https://your-backend.render.com

# Security
APP_SECRET_KEY=generate-secure-random-string
```

### Production Checklist

- [ ] Set `CORS_ORIGINS` to your actual frontend domain
- [ ] Set `APP_SECRET_KEY` to a secure random value
- [ ] Use Upstash Redis for production
- [ ] Configure monitoring and logging
- [ ] Set up health checks
- [ ] Configure rate limiting
- [ ] Enable HTTPS/TLS

---

## Documentation

- [System Design](docs/pulseops-architecture.png)
- [Post-Mortem](docs/postmortem.md)