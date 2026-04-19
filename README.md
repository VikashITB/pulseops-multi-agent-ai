<div align="center">

<br/>

# ⚡ PulseOps

### Multi-Agent AI Orchestration Platform

**Coordinate chains of specialised AI agents to plan, retrieve, analyse, write, and critique — in real-time.**

<br/>

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Redis](https://img.shields.io/badge/Redis-7.0-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)
[![Celery](https://img.shields.io/badge/Celery-5.x-37814A?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![Groq](https://img.shields.io/badge/Groq-llama--3.1--8b-F55036?style=for-the-badge&logo=groq&logoColor=white)](https://groq.com)

<br/>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](CONTRIBUTING.md)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000?style=flat-square)](https://github.com/astral-sh/ruff)

<br/>

[**🚀 Live Demo**](https://pulseops-multi-agent-ai.vercel.app/) · [**Architecture**](#architecture) · [**API Docs**](#api-reference) · [**Quick Start**](#quick-start) · [**Deployment**](#deployment)

<br/>

</div>

---

## What is PulseOps?

PulseOps is a **production-grade AI task orchestration platform** that chains five specialised agents — Planner, Retriever, Analyzer, Writer, and Critic — into a fully automated pipeline. Each agent streams its progress in real time via Server-Sent Events, giving users live visibility into every step of a complex AI workflow.

Built for teams and developers who need AI pipelines that are **observable, retryable, and scalable** — not black-box API calls.

---

## Why PulseOps?

| Problem | How PulseOps solves it |
|---------|------------------------|
| LLM outputs are opaque and hard to debug | SSE streaming exposes every token and agent step in real time |
| Single-prompt AI produces shallow results | A five-stage pipeline with specialised agents produces structured, reviewed output |
| Long AI tasks block the user | Async Celery workers decouple execution from the HTTP request cycle |
| Flaky LLM APIs cause silent failures | Built-in retry logic with exponential back-off across all agents |
| Hard to swap LLM providers | Unified `LLMProvider` abstraction supports OpenAI, Groq, and Gemini behind one interface |
| Difficult to deploy and scale | Docker Compose for development; Render, Railway, and Upstash Redis for production |

---

## Features

- 🤖 **Five-stage agent pipeline** — Planner → Retriever → Analyzer → Writer → Critic
- ⚡ **Real-time SSE streaming** — token-level progress updates pushed to the browser
- 🔄 **Async task queue** — Celery + Redis decouples long-running jobs from the API
- 🛡️ **Automatic retry handling** — tenacity-powered exponential back-off per agent
- 🔌 **Multi-provider LLM support** — OpenAI, Groq, and Gemini behind a single interface
- 🐳 **One-command startup** — full stack via `docker compose up --build`
- 📡 **REST + SSE API** — clean endpoints for submission, polling, and live streaming
- 🧩 **Extensible agent registry** — add new agents with a single class + two lines of config
- 📊 **In-memory orchestration** — lightweight task state without a heavy database
- 🚀 **Production-ready** — Render, Railway, and Vercel deployment guides included

---

## Screenshots

**Dashboard** — live metrics, FAST / FULL mode selector, task input, and output panel side-by-side.

![Dashboard](screenshots/dashboard.png)

<br/>

| Task Execution | Live Streaming |
|:--------------:|:--------------:|
| ![Task Execution](screenshots/task-execution.png) | ![Live Streaming](screenshots/live-streaming.png) |

<br/>

**Analytics** — per-session stats, agent success rates, and response-time tracking.

![Analytics](screenshots/analytics.png)

---

## Tech Stack

**Backend**
- [FastAPI](https://fastapi.tiangolo.com) — async API framework with automatic OpenAPI docs
- [Celery](https://docs.celeryq.dev) — distributed task queue with Redis as broker and backend
- [Redis](https://redis.io) — in-memory broker, result store, and SSE event bus
- [Pydantic v2](https://docs.pydantic.dev) — data validation and settings management
- [Tenacity](https://tenacity.readthedocs.io) — retry logic with exponential back-off
- [Python-dotenv](https://pypi.org/project/python-dotenv/) — environment configuration

**AI / LLM**
- Supports Groq, OpenAI, and Gemini through a unified `LLMProvider` abstraction — swap providers with a single env-var change
- **Production provider:** [Groq](https://groq.com) running `llama-3.1-8b-instant` — chosen for its sub-second inference latency
- [OpenAI GPT-4o-mini](https://openai.com) — drop-in alternative for highest reasoning quality
- [Google Gemini 1.5 Flash](https://deepmind.google/gemini) — multimodal option with long context support

**Frontend**
- Vanilla HTML / CSS / JavaScript — zero-dependency, SSE-native
- Server-Sent Events — native browser streaming without WebSocket complexity

**Infrastructure**
- [Docker](https://docker.com) + [Docker Compose](https://docs.docker.com/compose/) — local and production containerisation
- [Render](https://render.com) / [Railway](https://railway.app) — backend hosting
- [Vercel](https://vercel.com) — frontend hosting
- [Upstash Redis](https://upstash.com) — serverless Redis for production

---

## Architecture

![PulseOps System Architecture](docs/pulseops_architecture.png)

The system is split into five layers — Client, Application, Queue, Data, and AI Agents — with three interchangeable LLM providers at the base. The FastAPI gateway accepts tasks synchronously and immediately returns a `task_id`; all heavy execution is handed off to Celery workers over Redis, keeping the API response time under 50 ms regardless of pipeline length.

### Agent Pipeline

Each agent is independently retryable and streams its output token-by-token via SSE.

```
TaskRequest
    │
    ├─▶ PlannerAgent    — generates a structured JSON execution plan
    │
    ├─▶ RetrieverAgent  — fetches relevant documents and context  [streaming]
    │
    ├─▶ AnalyzerAgent   — extracts key findings from retrieved data  [streaming]
    │
    ├─▶ WriterAgent     — synthesises a polished response or report  [streaming]
    │
    └─▶ CriticAgent     — reviews and improves the final output  [streaming]
            │
            ▼
        TaskSummary  →  { final_output, total_duration_ms, status }
```

---

## Prerequisites

| Tool | Minimum version |
|------|----------------|
| Docker | 24+ |
| Docker Compose | 2.20+ |
| Python | 3.11+ *(local dev only)* |

---

## Quick Start

### Docker Compose *(recommended)*

```bash
# 1. Clone the repository
git clone https://github.com/VikashITB/pulseops-multi-agent-ai.git
cd pulseops-multi-agent-ai

# 2. Configure environment variables
cp .env.example .env
# Edit .env and set your LLM API key:
#   OPENAI_API_KEY=sk-...
#   (or GROQ_API_KEY / GEMINI_API_KEY)

# 3. Start the full stack
docker compose up --build
```

| Service | URL |
|---------|-----|
| API + Frontend | http://localhost:8000 |
| Interactive API docs | http://localhost:8000/docs |
| Redis | localhost:6379 |

### Local Development

```bash
# Create and activate virtual environment
python -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start Redis (Docker)
docker run -d -p 6379:6379 redis:7-alpine

# Terminal 1 — API server
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Celery worker
celery -A app.queue.celery_app worker --loglevel=info --concurrency=4
```

---

## Configuration

Settings are managed by `app/core/config.py` using Pydantic and loaded from a `.env` file.

### Core

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Runtime environment |
| `APP_HOST` | `0.0.0.0` | Server bind host |
| `APP_PORT` | `8000` | Server bind port |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:8000` | Allowed CORS origins (comma-separated) |

### LLM Providers

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `groq` | Active provider — `groq`, `openai`, or `gemini` |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model name |
| `GROQ_API_KEY` | — | Groq API key |
| `GROQ_MODEL` | `llama-3.1-8b-instant` | Groq model name *(production default)* |
| `GEMINI_API_KEY` | — | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Gemini model name |

### Infrastructure

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `CELERY_BROKER_URL` | `redis://localhost:6379/1` | Celery broker URL |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/2` | Celery result backend |

### Agent Behaviour

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_MAX_RETRIES` | `3` | Maximum retry attempts per agent |
| `AGENT_RETRY_BASE_DELAY` | `1.0` | Initial retry delay in seconds |
| `AGENT_TIMEOUT` | `60` | Per-agent timeout in seconds |
| `MAX_BATCH_SIZE` | `10` | Maximum concurrent batch size |
| `BATCH_FLUSH_INTERVAL` | `5.0` | Batch flush interval in seconds |

---

## API Reference

### Submit a task

```
POST /api/v1/task
```

**Request**

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

### Poll task status

```
GET /api/v1/task/{task_id}
```

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

Status values: `pending` · `running` · `completed` · `partial` · `failed`

---

### List all tasks

```
GET /api/v1/tasks
```

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

### Stream live events

```
GET /api/v1/stream/{task_id}
```

Opens an SSE connection. Events are pushed as each agent starts, streams, and completes.

**Event types**

| Event | Payload fields | Description |
|-------|---------------|-------------|
| `task_started` | `task_id`, `message` | Pipeline has begun |
| `plan_ready` | `data`, `message` | Planner produced a structured plan |
| `step_started` | `step_id`, `agent`, `message` | An agent step is starting |
| `step_progress` | `step_id`, `data.token` | Streaming token from agent output |
| `step_completed` | `step_id`, `agent`, `data` | Agent step finished successfully |
| `step_failed` | `step_id`, `agent`, `data` | Agent step failed (will retry) |
| `task_completed` | `data.result`, `message` | Full pipeline completed |
| `task_failed` | `task_id`, `message` | Pipeline failed after retries |

**JavaScript example**

```javascript
const es = new EventSource(`/api/v1/stream/${taskId}`);

es.addEventListener('step_progress', (e) => {
  const { data } = JSON.parse(e.data);
  process.stdout.write(data.token);          // stream tokens as they arrive
});

es.addEventListener('task_completed', (e) => {
  const { data } = JSON.parse(e.data);
  console.log('Final output:', data.result);
  es.close();
});
```

---

## Project Structure

```
.
├── app/
│   ├── main.py                  # FastAPI app factory + lifespan hooks
│   ├── api/
│   │   └── routes.py            # All API endpoints
│   ├── agents/
│   │   ├── base_agent.py        # Abstract base — all agents inherit from here
│   │   ├── planner_agent.py     # Produces a structured JSON execution plan
│   │   ├── retriever_agent.py   # Fetches relevant documents and context
│   │   ├── analyzer_agent.py    # Extracts key findings from retrieved data
│   │   ├── writer_agent.py      # Synthesises a polished final response
│   │   └── critic_agent.py      # Reviews and improves the writer output
│   ├── core/
│   │   ├── config.py            # Pydantic settings (env-var driven)
│   │   ├── logger.py            # Structured JSON logging
│   │   ├── llm_provider.py      # OpenAI / Groq / Gemini abstraction
│   │   ├── pipeline.py          # Async sequential pipeline executor
│   │   └── orchestrator.py      # In-memory task state management
│   ├── models/
│   │   └── schemas.py           # Pydantic request / response models
│   ├── queue/
│   │   ├── celery_app.py        # Celery configuration and app instance
│   │   └── tasks.py             # Celery task definitions
│   ├── services/
│   │   └── streaming.py         # SSE event generator and queue bridge
│   └── utils/
│       ├── retry.py             # Tenacity retry decorators
│       └── helpers.py           # Shared utility functions
├── frontend/
│   ├── index.html               # Single-page application shell
│   ├── style.css                # Premium dark-theme styles
│   └── script.js                # SSE client and UI logic
├── screenshots/
│   ├── dashboard.png
│   ├── task-execution.png
│   ├── live-streaming.png
│   └── analytics.png
├── docs/
│   ├── pulseops-architecture.png
│   ├── system_design.md
│   └── postmortem.md
├── docker-compose.yml
├── docker-compose.prod.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## Development

### Code quality

```bash
# Lint and format
ruff check . && ruff format .

# Type checking
mypy app/
```

### Adding a new agent

1. Create `app/agents/my_agent.py` subclassing `BaseAgent`
2. Implement the `agent_type` property and `_run()` async method
3. Register it in `app/agents/__init__.py` → `AGENT_REGISTRY`
4. Add the enum value to `AgentType` in `app/models/schemas.py`
5. Insert the agent at the desired position in `app/core/pipeline.py`

---

## Testing

```bash
# Unit and integration tests with coverage report
pytest tests/ -v --cov=app --cov-report=term-missing

# Full integration tests (requires Docker)
docker compose -f docker-compose.test.yml up --abort-on-container-exit
```

---

## Deployment

### Frontend → Vercel

```bash
# Option A — Vercel CLI
vercel deploy

# Option B — GitHub integration
# 1. Push to GitHub
# 2. Import project at vercel.com/new
# 3. Set root directory to: frontend
# 4. Deploy (zero config needed)
```

### Backend → Render

1. Create a new **Web Service** on [Render](https://render.com)
2. Connect your GitHub repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables:

```env
APP_ENV=production
LLM_PROVIDER=groq                                 # or openai / gemini
GROQ_API_KEY=your_key_here
REDIS_URL=rediss://default:password@host:port      # Upstash URL
CORS_ORIGINS=https://your-frontend.vercel.app
APP_SECRET_KEY=generate-a-secure-random-string
```

### Backend → Railway

```bash
railway login
railway init
railway up
```

Configure via `railway.toml` in the project root.

### Redis → Upstash *(production)*

1. Create a free database at [upstash.com](https://upstash.com)
2. Copy the `rediss://` connection URL
3. Set it as `REDIS_URL`, `CELERY_BROKER_URL`, and `CELERY_RESULT_BACKEND`

### Docker production build

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

### Production checklist

- [ ] `CORS_ORIGINS` set to your actual frontend domain
- [ ] `APP_SECRET_KEY` set to a cryptographically random string
- [ ] Upstash Redis (or equivalent) provisioned
- [ ] Health-check endpoints configured on your host
- [ ] Rate limiting enabled
- [ ] HTTPS / TLS termination in place
- [ ] Structured logging routed to an observability platform
- [ ] Celery worker concurrency tuned for your workload

---

## Future Improvements

- 🔐 **User authentication** — JWT-based auth with per-user task history and quotas
- 📊 **Analytics dashboard** — pipeline latency charts, agent success rates, token usage
- 🧠 **Agent memory** — persistent vector memory so agents recall past context across sessions
- 🔭 **Observability** — OpenTelemetry tracing, Prometheus metrics, Grafana dashboards
- 👥 **Team collaboration** — shared workspaces, task comments, and result annotations
- 🔗 **Webhook callbacks** — push `task_completed` events to external systems
- 🗄️ **Persistent storage** — PostgreSQL backend to replace in-memory orchestration
- 🌐 **Agent marketplace** — plug-in community agents without touching core pipeline code

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

```bash
# Fork → clone → create a feature branch
git clone https://github.com/VikashITB/pulseops-multi-agent-ai.git
cd pulseops-multi-agent-ai
git checkout -b feat/my-improvement

# Make changes, then
ruff check . && pytest tests/ -v

# Open a pull request
```

---

## License

Distributed under the [MIT License](LICENSE).

---

<div align="center">

Built with ⚡ by [Vikash Gupta](https://github.com/VikashITB)

**[⬆ Back to top](#-pulseops)**

</div>
