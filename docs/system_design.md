# PulseOps AI — System Design

---

# Overview

PulseOps AI is a multi-agent asynchronous task execution platform designed for complex user requests.

The system accepts a natural-language task, decomposes it into smaller subtasks, routes them to specialized AI agents, and streams live progress updates to the frontend.

---

# Core Flow

```text
User Request
   ↓
FastAPI API
   ↓
Planner Agent
   ↓
Task Graph / Steps
   ↓
Redis Queue
   ↓
Celery Worker
   ↓
Retriever → Analyzer → Writer → Critic
   ↓
Live SSE Updates
   ↓
Frontend UI