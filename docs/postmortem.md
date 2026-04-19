# PulseOps Post-Mortem

## Overview
PulseOps is an agentic AI system that coordinates multiple specialized agents through an async pipeline to solve multi-step tasks.

## 1. Scaling Issue Encountered
A major scaling challenge was handling many concurrent SSE streaming connections. Persistent streams can increase memory usage and worker load as users grow.

### Mitigation
- Celery workers for long-running tasks
- Redis event communication
- Stateless FastAPI request handling

### Future Improvement
Move to Redis Streams or WebSocket gateway with autoscaling workers.

## 2. Design Decision I Would Change
The current version uses in-memory task state for simplicity and speed.

### What I Would Change
Replace it with:
- PostgreSQL for persistent task metadata
- Redis Streams for events
- Durable task/result storage

## 3. Trade-Offs Made During Development
Redis + Celery was chosen over Kafka.

### Benefits
- Faster development
- Easier deployment
- Lower infrastructure complexity

### Trade-Off
Kafka would offer stronger replayability and larger-scale throughput.

## Final Reflection
PulseOps demonstrates scalable multi-agent orchestration. Future priorities would be persistence, observability, autoscaling, and monitoring.