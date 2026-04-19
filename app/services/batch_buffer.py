from __future__ import annotations

import json

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

BUFFER_KEY = "pulseops:task_buffer"


class BatchBuffer:
    def __init__(self, redis: aioredis.Redis) -> None:
        self.redis = redis
        self.max_batch_size: int = settings.max_batch_size
        self.flush_interval: float = settings.batch_flush_interval

    async def push(self, task_id: str, user_request: str) -> int:
        """Append one task to the right of the list. Returns new list length."""
        payload = json.dumps({"task_id": task_id, "user_request": user_request})
        size: int = await self.redis.rpush(BUFFER_KEY, payload)
        logger.info(
            "task_buffered",
            task_id=task_id,
            buffer_size=size,
            max_batch_size=self.max_batch_size,
        )
        return size

    async def pop_batch(self) -> list[dict]:
        """
        Atomically grab up to max_batch_size items from the left
        and trim them from the list so no other flusher can claim them.
        """
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.lrange(BUFFER_KEY, 0, self.max_batch_size - 1)
            pipe.ltrim(BUFFER_KEY, self.max_batch_size, -1)
            results = await pipe.execute()

        raw_items: list[bytes | str] = results[0]
        batch = [json.loads(item) for item in raw_items]

        logger.info(
            "batch_popped",
            batch_size=len(batch),
        )
        return batch

    async def size(self) -> int:
        length: int = await self.redis.llen(BUFFER_KEY)
        return length
