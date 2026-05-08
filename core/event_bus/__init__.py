"""
事件匯流排 — Redis Pub/Sub 實作

所有服務透過此機制發布/訂閱領域事件，
稽核服務監聽所有頻道並持久化至 Elasticsearch。
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Callable, Awaitable
from uuid import uuid4


@dataclass
class DomainEvent:
    event_type: str          # e.g. "tool.execute", "user.login", "job.complete"
    actor_user_id: int | None
    actor_username: str | None
    actor_ip: str | None
    resource_type: str       # "document", "tool", "user", ...
    resource_id: str | None
    action: str
    result: str              # "success" | "failure"
    detail: dict
    timestamp: str = ""
    event_id: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.event_id:
            self.event_id = str(uuid4())


CHANNEL_PREFIX = "xcloudpdf:events:"

CHANNELS = {
    "auth":     CHANNEL_PREFIX + "auth",
    "tool":     CHANNEL_PREFIX + "tool",
    "job":      CHANNEL_PREFIX + "job",
    "document": CHANNEL_PREFIX + "document",
    "user":     CHANNEL_PREFIX + "user",
    "system":   CHANNEL_PREFIX + "system",
}


async def publish(event: DomainEvent) -> None:
    """發布事件至對應 Redis 頻道"""
    import redis.asyncio as aioredis
    redis = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    channel = CHANNELS.get(event.resource_type, CHANNEL_PREFIX + "misc")
    await redis.publish(channel, json.dumps(asdict(event)))
    await redis.aclose()


async def subscribe(channels: list[str], handler: Callable[[DomainEvent], Awaitable[None]]) -> None:
    """訂閱頻道並持續處理事件（用於稽核服務）"""
    import redis.asyncio as aioredis
    redis = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    pubsub = redis.pubsub()
    await pubsub.subscribe(*channels)
    async for message in pubsub.listen():
        if message["type"] == "message":
            data = json.loads(message["data"])
            await handler(DomainEvent(**data))
