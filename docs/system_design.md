# PulseOps AI — System Design Document

> **Version:** 1.0 &nbsp;·&nbsp; **Stack:** FastAPI · Celery · Redis · Python · HTML · CSS · JavaScript · SSE &nbsp;·&nbsp; **Status:** Active Development

---

## Table of Contents

1. [Overview](#1-overview)
2. [Objectives](#2-objectives)
3. [High-Level Architecture](#3-high-level-architecture)
4. [Core Request Flow](#4-core-request-flow)
5. [Component Breakdown](#5-component-breakdown)
6. [Agent Pipeline](#6-agent-pipeline)
7. [Queue & Worker Layer](#7-queue--worker-layer)
8. [Streaming Layer](#8-streaming-layer)
9. [Failure Handling](#9-failure-handling)
10. [Manual Batching Logic](#10-manual-batching-logic)
11. [Scalability Design](#11-scalability-design)
12. [Trade-Offs & Design Decisions](#12-trade-offs--design-decisions)
13. [Security Considerations](#13-security-considerations)
14. [Conclusion](#14-conclusion)

---

## 1. Overview

PulseOps AI is a **multi-agent asynchronous task execution platform** designed to handle complex, long-running natural-language tasks that are impractical to resolve in a single synchronous API call.

When a user submits a task — such as *"Research the competitive landscape for AI coding assistants and write a structured report"* — PulseOps does not attempt to resolve it in one step. Instead, it decomposes the task into a directed graph of subtasks, routes each subtask to a purpose-built AI agent, executes the full pipeline asynchronously via a distributed worker queue, and streams granular progress updates back to the frontend in real time.

**Four design principles drive the system:**

**Multi-agent architecture.** Complex tasks are broken down by a Planner Agent into discrete, well-scoped subtasks. Each subtask is handled by a specialized agent — Retriever, Analyzer, Writer, or Critic — chosen for the nature of the work. Specialization produces higher-quality outputs than a single generalist prompt and enables parallel execution where task dependencies allow.

**Async task execution.** All heavy work runs outside the HTTP request cycle. FastAPI accepts the task, enqueues it, and returns a task ID immediately. Celery workers pick up jobs from the Redis broker and execute them independently. The API never blocks waiting for an agent to finish.

**Live streaming updates.** Rather than polling or waiting for a final response, the frontend subscribes to a Server-Sent Events (SSE) stream keyed by task ID. As each agent completes a step, the backend pushes a structured progress event. Users see the pipeline advance in real time — which agent is running, what it produced, and whether any step failed.

**Scalable design.** The API layer is stateless and horizontally scalable. Workers are stateless processes that can be replicated across machines. The Redis broker decouples producers from consumers, smoothing out traffic spikes without dropping work.

---

## 2. Objectives

| # | Objective | Rationale |
|---|-----------|-----------|
| 1 | **Non-blocking execution of long-running tasks** | LLM inference chains can take 15–120 seconds. Blocking a web server thread for that duration is not viable at any meaningful scale. |
| 2 | **Higher output quality through agent specialization** | A single prompt cannot reliably plan, retrieve, analyze, write, and critique simultaneously. Dedicated agents with narrowly scoped responsibilities produce more accurate, coherent outputs. |
| 3 | **Real-time transparency for users** | Waiting with no feedback degrades UX severely on long tasks. SSE streams give users live visibility into which stage is running and what partial output has been produced. |
| 4 | **Retry and failure tolerance** | Network calls to LLM providers are unreliable. Any step in a multi-agent pipeline can fail. The system must detect failures, retry with backoff, and route unrecoverable tasks to a Dead Letter Queue without losing state. |
| 5 | **Horizontal scalability** | The system should handle increased task volume by adding workers, not by vertically scaling a monolith. The queue-based architecture enables this without architectural changes. |

---

## 3. High-Level Architecture

The system is organized into six discrete layers, each with a single well-defined responsibility:

![PulseOps Architecture](pulseops_architecture.png)

| Layer | Responsibility |
|-------|---------------|
| **Client** | Browser UI and PulseOps Dashboard — submits tasks, renders SSE stream |
| **Application** | FastAPI gateway, Orchestrator, State Manager, Streaming Service |
| **Deployment** | Frontend on Vercel; Backend on Render / Railway |
| **Queue** | Redis Broker + Celery Worker Queue with Retry Policy / Dead Letter Queue |
| **Data** | Upstash Redis (production) / Local Redis (development) for task state |
| **LLM Providers** | Groq, Gemini, OpenAI — called by agents via provider-agnostic abstraction |

---

## 4. Core Request Flow

```
User Input
    │
    ▼
Frontend Dashboard
    │  POST /api/v1/task
    ▼
FastAPI API Gateway          ← validates input, returns task_id immediately
    │
    ▼
Orchestrator / Task Manager  ← creates task record, sets status = QUEUED
    │
    ▼
Planner Agent                ← decomposes natural-language task into subtask graph
    │
    ▼
Task Batching Window         ← collects subtasks arriving within time window,
    │                           groups them into an efficient batch before enqueue
    ▼
Redis Broker                 ← subtasks pushed as serialized messages
    │
    ▼
Celery Worker Queue          ← workers dequeue and dispatch to correct agent
    │
    ├──► Retriever Agent      ← fetches relevant context / external data
    │
    ├──► Analyzer Agent       ← extracts patterns, structures findings
    │
    ├──► Writer Agent         ← synthesizes structured output
    │
    └──► Critic Agent         ← reviews output, flags issues, triggers revision
              │
              ▼
         Retry Policy         ← on failure: exponential backoff, up to N retries
              │
              ▼ (unrecoverable)
         Dead Letter Queue    ← persists failed tasks for inspection / replay
              │
              ▼ (success)
         State Manager        ← writes agent output + status to Redis
              │
              ▼
         SSE Streaming Service ← pushes progress event to open client stream
              │
              ▼
         Frontend Dashboard   ← renders live agent progress and final output
```

The HTTP request path (`POST /api/v1/task`) returns in under 100ms. All subsequent work is fully async. The frontend subscribes to `GET /api/v1/stream/{task_id}` via EventSource and receives push events as each pipeline stage completes.

---

## 5. Component Breakdown

### 5.1 Frontend Dashboard

The client application provides two surfaces: a task submission form and a live results panel. On submission, the frontend fires a `POST` request, receives a `task_id`, then immediately opens an SSE connection to `/api/v1/stream/{task_id}`. The results panel updates incrementally as events arrive — showing which agent is running, intermediate outputs, and completion status. No polling. No full-page refreshes.

**Key responsibilities:** task submission, SSE subscription management, rendering streaming output, surfacing error states from failed agents.

---

### 5.2 FastAPI API Gateway

The API layer is the single entry point for all external traffic. It handles request validation via Pydantic schemas, serializes the task payload, writes an initial task record to Redis, and enqueues the root job for the Orchestrator.

The gateway is intentionally thin — it does no LLM work and holds no session state. This makes it straightforward to scale horizontally behind a load balancer.

**Key endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/task` | Submit a new task; returns `task_id` |
| `GET` | `/api/v1/stream/{task_id}` | SSE stream for live task progress |
| `GET` | `/api/v1/task/{task_id}` | Poll task status and result |

---

### 5.3 Orchestrator (Task Manager)

The Orchestrator manages the lifecycle of a submitted task. It owns task creation, state transitions (`QUEUED → RUNNING → COMPLETE / FAILED`), and the routing of subtasks produced by the Planner Agent into the correct worker queues.

It does not execute agent logic directly. Its role is coordination: knowing what needs to run next, what has finished, and what has failed. State is persisted in Redis so the Orchestrator can reconstruct task context after a worker restart.

---

### 5.4 State Manager

A lightweight Redis-backed store that tracks per-task state: current status, which agents have completed, partial outputs, retry counts, and timestamps. Both the API layer and the SSE streaming service read from this store.

Using Redis for task state (rather than a relational database) keeps reads and writes sub-millisecond and avoids coupling the hot path to a heavier persistence layer. A migration path to PostgreSQL for durable long-term storage is noted in the Scalability section.

---

### 5.5 Streaming Service

Manages open SSE connections, keyed by `task_id`. When an agent completes a step, it publishes a structured event to a Redis key. The Streaming Service reads that key and pushes the event down the corresponding open HTTP response stream.

Events are structured JSON with a consistent schema:

```json
{
  "task_id": "abc123",
  "agent": "writer",
  "status": "complete",
  "output": "...",
  "timestamp": "2025-04-19T10:30:00Z"
}
```

---

## 6. Agent Pipeline

The agent pipeline is the core of PulseOps. Each agent is a self-contained module that receives a typed input, calls an LLM provider, and returns a typed output. Agents share no mutable state with each other; all coordination is through the task state in Redis.

### 6.1 Planner Agent

**Input:** Raw natural-language task string.
**Output:** Ordered list of subtasks with declared dependencies.

The Planner is the first agent to run. Its sole job is decomposition: given a complex request, produce a task graph with clearly scoped subtasks and enough context for downstream agents to execute independently. The quality of the Planner's output directly determines the quality of the final result.

### 6.2 Retriever Agent

**Input:** A subtask requiring external context (facts, data, examples).
**Output:** Structured context block passed to the Analyzer.

The Retriever gathers the information that other agents need. It may call external APIs, perform lookup operations, or construct targeted prompts to extract specific facts from an LLM. It does not synthesize or draw conclusions — that is the Analyzer's domain.

### 6.3 Analyzer Agent

**Input:** Retriever output + original subtask specification.
**Output:** Structured findings, extracted patterns, key insights.

The Analyzer processes raw retrieved context into structured findings. It is responsible for removing noise, identifying patterns, and producing the organized material that the Writer will use to generate output. Keeping retrieval and analysis separate prevents conflation of "what was found" with "what it means."

### 6.4 Writer Agent

**Input:** Analyzer output + original subtask specification.
**Output:** Fully composed text, report section, or structured artifact.

The Writer synthesizes findings into the final user-facing output for its subtask. It receives clean, structured input from the Analyzer and focuses purely on generation quality — coherence, clarity, formatting, and completeness.

### 6.5 Critic Agent

**Input:** Writer output + original subtask specification.
**Output:** Structured review — pass, revision request, or failure signal.

The Critic is a quality gate. It reviews Writer output against the original subtask requirements and flags issues: logical inconsistencies, missing coverage, factual gaps, or format violations. If the Critic returns a revision request, the Orchestrator loops the subtask back through the Writer with the Critic's feedback as additional context. A maximum revision depth prevents infinite loops.

---

## 7. Queue & Worker Layer

### Redis Broker

Redis serves as the message broker for Celery. Subtasks are serialized and pushed to named queues. Redis was chosen over heavier alternatives because the task payloads are small (JSON, sub-10KB), durability requirements are satisfied by retry logic at the application layer, and Redis is already in the stack for task state — adding a separate broker would increase operational complexity without meaningful benefit at the current scale.

### Celery Workers

Celery workers are stateless Python processes that dequeue jobs, deserialize the task payload, invoke the appropriate agent module, and write results back to the State Manager. Workers can be scaled horizontally — adding more worker processes increases throughput linearly because the queue is the only shared resource.

Workers are registered to named queues that correspond to agent types. This allows independent scaling: if Retriever tasks are the bottleneck, only Retriever workers need to be scaled up.

```bash
celery -A pulseops.worker worker \
  --queues=retriever,analyzer,writer,critic \
  --concurrency=4
```

### Task Serialization

All task payloads are serialized as JSON. Celery's default pickle serializer is explicitly disabled to avoid deserialization vulnerabilities. Task payloads carry a `task_id`, `agent_type`, `input_payload`, `retry_count`, and `created_at` timestamp.

---

## 8. Streaming Layer

PulseOps uses **Server-Sent Events (SSE)** rather than WebSockets for streaming. This is a deliberate trade-off: SSE is unidirectional (server → client), which is exactly the shape of progress updates. It runs over plain HTTP/1.1, works through all standard proxies and load balancers without configuration, and does not require a stateful handshake or persistent bidirectional connection.

**Streaming flow:**

1. Frontend opens `GET /api/v1/stream/{task_id}` using the browser's native `EventSource` API.
2. FastAPI holds the response open and yields events as they are written to Redis by workers.
3. Each agent completion pushes a structured event to the open stream.
4. On task completion or failure, the server sends a terminal event and closes the connection.

Clients that disconnect and reconnect receive only new events — partial replay from a cursor is a planned enhancement noted in the Scalability section.

---

## 9. Failure Handling

Reliability in a multi-agent pipeline requires failure handling at every layer. PulseOps treats failure as an expected condition, not an edge case.

### Retries with Exponential Backoff

Every Celery task is configured with automatic retries. On any exception — LLM provider timeout, rate limit response, transient network error — the worker retries with exponential backoff and jitter:

```python
@celery_app.task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,         # doubles delay on each retry
    retry_backoff_max=60,       # caps at 60 seconds
    retry_jitter=True,          # adds random jitter to prevent thundering herd
)
def run_agent_task(self, payload: dict) -> dict:
    ...
```

### Dead Letter Queue

Tasks that exhaust all retry attempts are routed to a dedicated Dead Letter Queue (DLQ). The DLQ persists failed task payloads with full metadata: original input, retry history, final exception, and timestamps. This enables:

- Manual inspection of failure patterns without log trawling.
- Replay of failed tasks after a root cause is resolved.
- Alerting on DLQ depth as an operational health signal.

### Timeouts

Each agent invocation carries a hard timeout. If an LLM call does not return within the configured window, the worker raises a timeout exception and the retry policy takes over. Timeouts prevent workers from being permanently blocked by a hung provider call.

### Graceful UI Errors

When a task fails after all retries, the State Manager writes a `FAILED` status with a structured error summary. The SSE stream delivers a terminal error event to the frontend, which renders a clear failure state — identifying which agent failed and surfacing an actionable message — rather than silently hanging or displaying a generic error.

---

## 10. Manual Batching Logic

PulseOps implements a **task batching window** at the Orchestrator level. When the Planner Agent decomposes a task into subtasks, those subtasks do not enqueue individually and immediately. Instead, the Orchestrator holds them in a short-lived buffer (configurable window, default 200ms) and groups them into a single batch before enqueuing.

**Why this matters:**

Subtasks from the same parent task frequently share context. Batching allows the Orchestrator to deduplicate shared retrieval work before jobs hit the queue — a Retriever task fetching the same source for two subtasks becomes one task instead of two. Batch enqueue also reduces Redis round-trips: one `lpush` with N items versus N individual calls. It also provides a natural point to apply priority sorting before enqueue, ensuring earlier pipeline stages (Retriever) queue ahead of later ones (Writer) even when the Planner emits all subtasks simultaneously.

```python
class TaskBatchingWindow:
    def __init__(self, window_ms: int = 200):
        self.window_ms = window_ms
        self.buffer: list[SubTask] = []

    async def add(self, subtask: SubTask) -> None:
        self.buffer.append(subtask)

    async def flush(self) -> list[SubTask]:
        await asyncio.sleep(self.window_ms / 1000)
        batch = self._deduplicate(self.buffer)
        self.buffer.clear()
        return batch

    def _deduplicate(self, tasks: list[SubTask]) -> list[SubTask]:
        seen: dict[str, SubTask] = {}
        for t in tasks:
            key = t.dedup_key()
            if key not in seen:
                seen[key] = t
        return list(seen.values())
```

The batching window is a lightweight optimization that costs 200ms of latency on the enqueue path in exchange for meaningful reductions in redundant LLM calls and queue pressure under load.

---

## 11. Scalability Design

### Current Architecture

The current design is intentionally simple and operationally lean while remaining genuinely scalable:

**Stateless API layer.** FastAPI instances hold no per-request state. Any instance can handle any request. Scaling horizontally behind a load balancer requires no configuration changes.

**Horizontally scalable workers.** Celery workers are stateless processes. Increasing throughput means running more worker processes — on the same machine or across multiple hosts. The Redis queue is the only shared resource.

**Redis as shared state.** Task state written to Redis is immediately visible to all API instances and all worker processes without any inter-process communication. No sticky sessions. No shared memory.

**Provider-agnostic LLM layer.** Agents call LLM providers through an abstraction layer. Switching providers or adding fallback routing on rate limits requires no changes to agent logic.

### Future Enhancements

| Enhancement | Motivation |
|-------------|-----------|
| **PostgreSQL for task persistence** | Redis is in-memory. Long-term task history, audit trails, and analytical queries require a durable relational store. |
| **Redis Streams for event log** | Replace direct Redis key writes with an append-only event stream per task. Enables SSE replay from a cursor and decouples the streaming service from workers. |
| **Kafka for high-volume ingestion** | At tens of thousands of tasks per minute, Kafka's partitioned log model provides stronger durability and consumer group semantics than Redis lists. |
| **Worker autoscaling** | Attach worker process count to queue depth metrics. Scale up when queues deepen; scale down during idle periods. |
| **Multi-region deployment** | Deploy API and worker layers to multiple regions with a globally replicated Redis for task state. Route users to their nearest endpoint. |

---

## 12. Trade-Offs & Design Decisions

### Redis + Celery over Kafka

Kafka is the standard recommendation for high-throughput event streaming. PulseOps uses Redis + Celery instead, for deliberate reasons.

**Operational simplicity.** Kafka requires managing brokers, topic partitions, consumer groups, and offset management. Redis + Celery is a fraction of the operational surface area. At PulseOps' current scale, Kafka's complexity would be pure overhead with no throughput benefit.

**Redis is already in the stack.** Redis serves as the task state store. Using it as the broker eliminates a dependency. A second message-passing system would add cost and operational complexity without solving a real problem.

**Celery provides all required primitives.** Retries, timeouts, task routing, priority queues, dead letter handling, and result backends are all first-class Celery features. Building equivalent behaviour on raw Kafka would require significantly more custom code.

**Migration path is defined.** Kafka becomes the right choice if task volume grows to a scale where Redis list operations bottleneck, or if durable ordered event logs become a hard requirement. The abstraction layer around queue interactions is intentionally narrow to keep this migration feasible.

### SSE over WebSockets

Progress updates are strictly server-to-client. SSE matches this shape exactly. WebSockets add bidirectional capability that is not needed here, introduce more complex connection management, and require careful proxy and load balancer configuration. SSE works over plain HTTP/1.1 with no special infrastructure requirements.

### In-Memory Redis State over a Database

Using Redis for task state keeps the hot path fast (sub-millisecond reads and writes) and avoids coupling task execution to a relational database. The accepted trade-off is that task history is not durably persisted across a full Redis restart. This is acceptable in the current phase; PostgreSQL persistence is a planned addition.

---

## 13. Security Considerations

**Secrets management.** All API keys (LLM providers), Redis connection strings, and service credentials are injected via environment variables. No credentials appear in source code or version control. `.env` files are excluded via `.gitignore`.

**Input validation.** All incoming task payloads are validated through Pydantic models before any processing occurs. Unexpected fields are rejected. Input length is bounded to prevent prompt injection vectors from generating unbounded LLM calls.

**CORS policy.** FastAPI's CORS middleware is configured with an explicit allowlist of trusted origins. Wildcard origins (`*`) are not used in production.

**Authentication-ready design.** The API gateway is structured to accept an `Authorization` header with bearer token validation as a middleware layer. User identity is not required for the current deployment scope, but the integration point exists and can be activated without structural changes.

**No sensitive data in task payloads.** Task payloads stored in Redis contain the user's task text and processing metadata only. LLM provider responses are written to Redis temporarily and are not logged at the API layer.

---

## 14. Conclusion

PulseOps AI is designed around a single core insight: complex tasks are best handled by a pipeline of specialized components, not by a single monolithic call. The multi-agent architecture enforces separation of concerns at the AI layer. The Redis + Celery queue enforces separation between task acceptance and task execution. SSE enforces a clean, unidirectional contract between the backend and the frontend.

The current system is production-capable, operationally simple, and horizontally scalable within its existing stack. The architecture is not over-engineered for current requirements, but each component has a clear upgrade path — Redis Streams for event replay, PostgreSQL for persistence, Kafka for high-volume scenarios — that can be activated as requirements evolve without structural rewrites.

Every design decision in PulseOps prioritises correctness, failure tolerance, and operational clarity over premature complexity.

---

*Document maintained in `docs/system_design.md`. Architecture diagram at `pulseops_architecture.png`.*
