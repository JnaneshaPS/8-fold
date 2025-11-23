from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Mapping, Sequence

from mem0 import MemoryClient

MEM0_API_KEY = os.getenv("MEM0_API_KEY")
MEM0_ENABLED = bool(MEM0_API_KEY)


@lru_cache(maxsize=1)
def get_mem0_client() -> MemoryClient | None:
    if not MEM0_ENABLED:
        return None
    return MemoryClient(api_key=MEM0_API_KEY)


def add_memory(
    messages: Sequence[Mapping[str, str]],
    *,
    user_id: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    client = get_mem0_client()
    if not client:
        return {}
    try:
        return client.add(messages, user_id=user_id, metadata=metadata or {})
    except Exception:
        return {}


def search_memory(
    query: str,
    *,
    user_id: str,
    limit: int = 5,
) -> dict[str, Any]:
    client = get_mem0_client()
    if not client:
        return {}
    try:
        return client.search(query, filters={"user_id": user_id}, limit=limit)
    except Exception:
        return {}
