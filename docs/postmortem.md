# PulseOps AI — Postmortem

---

# 1. Scaling Issue Encountered

## Problem

When multiple users opened live task streams simultaneously, API performance degraded.

Each connected client required continuous progress updates, which increased Redis reads and async event-loop load.

At higher concurrency:

- slower stream updates
- delayed progress logs
- occasional dropped SSE connections

## Root Cause

Initial design used periodic polling of Redis for every active stream.

With many clients:

```text
Many Streams × Frequent Polling = Heavy Load