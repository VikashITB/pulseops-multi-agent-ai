from __future__ import annotations

import json
import asyncio
from asyncio import Queue

from app.models.schemas import SSEEvent


async def event_generator(queue: Queue[SSEEvent]):
    yield "event: connected\n"
    yield 'data: {"status":"connected"}\n\n'

    while True:
        try:
            event = await asyncio.wait_for(queue.get(), timeout=15)

            data = event.model_dump(mode="json")

            yield f"event: {event.event.value}\n"
            yield f"data: {json.dumps(data)}\n\n"

            if event.message == "__STREAM_END__":
                break

        except asyncio.TimeoutError:
            yield "event: heartbeat\n"
            yield 'data: {"status":"alive"}\n\n'