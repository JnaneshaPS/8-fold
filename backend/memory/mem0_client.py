from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Mapping, Sequence

from mem0 import MemoryClient

@lru_cache(maxsize=1)
def get_mem0_client() -> MemoryClient:
    api_key = os.getenv("MEM0_API_KEY")
    if not api_key:
        raise RuntimeError("MEM0_API_KEY is not set in environment/.env")
    return MemoryClient(api_key=api_key)


def add_memory(
    messages: Sequence[Mapping[str, str]],
    *,
    user_id: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    client = get_mem0_client()
    return client.add(messages, user_id=user_id, metadata=metadata or {})


def search_memory(
    query: str,
    *,
    user_id: str,
    limit: int = 5,
) -> dict[str, Any]:
    client = get_mem0_client()
    return client.search(query, filters={"user_id": user_id}, limit=limit)
