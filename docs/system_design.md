# PulseOps AI System Design

## Overview

PulseOps is a multi-agent async task platform for complex natural-language tasks. When a user submits a task like "Research AI coding assistants and write a report", PulseOps breaks it into subtasks, routes each to specialized agents (Retriever, Analyzer, Writer, Critic), executes them asynchronously via Celery workers, and streams progress via SSE.

## Architecture

**Stack:** FastAPI, Celery, Redis, Python, HTML/CSS/JS, SSE

**Layers:**
- Client: Browser UI with SSE streaming
- Application: FastAPI gateway, Orchestrator, State Manager
- Queue: Redis broker + Celery workers with retry/DLQ
- Data: Redis for task state (Upstash prod, local dev)
- LLM: Groq, Gemini, OpenAI via abstraction layer

## Request Flow

```
User → Frontend POST /api/v1/task → FastAPI → Orchestrator
→ Planner Agent → Subtask graph → Redis → Celery workers
→ Agents (Retriever → Analyzer → Writer → Critic)
→ State Manager → SSE → Frontend
```

API returns task_id in <100ms. Frontend opens SSE stream to `/api/v1/stream/{task_id}` for live updates.

## Components

**Frontend:** Task submission form, SSE streaming, live progress panel. No polling.

**API Gateway:** FastAPI with Pydantic validation. Thin layer — no LLM work, no session state.

**Orchestrator:** Task lifecycle management. Creates tasks, transitions state, routes subtasks. State in Redis.

**State Manager:** Redis-backed store for task status, outputs, retry counts.

**Streaming Service:** SSE connections keyed by task_id. Pushes events from Redis to open streams.

## Agent Pipeline

**Planner:** Decomposes user request into subtask graph with dependencies.

**Retriever:** Fetches external context/data. Does not synthesize.

**Analyzer:** Processes retrieved context into structured findings/patterns.

**Writer:** Synthesizes findings into final output.

**Critic:** Quality gate. Reviews output, flags issues, triggers revision if needed.

## Queue & Workers

**Redis Broker:** Celery message broker. JSON serialization (pickle disabled). Small payloads (<10KB).

**Celery Workers:** Stateless Python processes. Horizontal scaling. Named queues per agent type.

**Task Serialization:** JSON with task_id, agent_type, input_payload, retry_count, created_at.

## Streaming

SSE (not WebSockets) — unidirectional server→client matches progress updates. Works over HTTP/1.1, no special infrastructure.

**Flow:**
1. Frontend opens `GET /api/v1/stream/{task_id}` via EventSource
2. FastAPI holds connection open, yields events from Redis
3. Each agent completion pushes structured event
4. Terminal event closes connection

## Failure Handling

**Retries:** Celery tasks auto-retry with exponential backoff + jitter (max 3).

**Dead Letter Queue:** Failed tasks persisted with metadata for inspection/replay.

**Timeouts:** Hard timeout per agent invocation prevents hanging.

**UI Errors:** Structured error events to frontend, clear failure states shown.

## Trade-offs

**Redis + Celery vs Kafka:** Simpler ops, Redis already in stack, Celery has built-in primitives. Kafka for high-volume future.

**SSE vs WebSockets:** SSE matches unidirectional shape, simpler, works through proxies.

**Redis state vs DB:** Fast hot path, acceptable trade-off for current phase. PostgreSQL planned for persistence.

## Security

- Secrets via environment variables
- Pydantic input validation, length bounds
- CORS allowlist (no wildcards)
- Authentication-ready design (Authorization header middleware)
- No sensitive data in task payloads

## Future

- PostgreSQL for durable task history
- Redis Streams for event replay
- Kafka for high-volume ingestion
- Worker autoscaling based on queue depth
- Multi-region deployment
