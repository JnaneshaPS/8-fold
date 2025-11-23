from __future__ import annotations

import os
from functools import lru_cache, wraps
from typing import Any, Callable, Dict, Optional

try:
    from langfuse import Langfuse, observe
except Exception:  # pragma: no cover - optional dependency
    Langfuse = None  # type: ignore

    def observe(*args, **kwargs):  # type: ignore
        def decorator(func):
            return func

        if args and callable(args[0]):
            return args[0]
        return decorator


LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_BASE_URL = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")

LANGFUSE_ENABLED = bool(
    Langfuse and LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY and LANGFUSE_BASE_URL
)


@lru_cache(maxsize=1)
def get_langfuse_client() -> Optional[Langfuse]:
    if not LANGFUSE_ENABLED:
        return None
    return Langfuse(  # type: ignore[call-arg]
        public_key=LANGFUSE_PUBLIC_KEY,
        secret_key=LANGFUSE_SECRET_KEY,
        host=LANGFUSE_BASE_URL,
    )


def render_prompt(
    name: str,
    *,
    prompt_type: str = "text",
    variables: Optional[Dict[str, Any]] = None,
    fallback: Optional[str] = None,
) -> str:
    client = get_langfuse_client()
    if client:
        try:
            prompt = client.get_prompt(name, type=prompt_type)
            if prompt_type == "chat":
                compiled = prompt.compile(**(variables or {}))
                if isinstance(compiled, list):
                    return "\n".join(
                        item.get("content", "") for item in compiled if item
                    )
                return str(compiled)
            return str(prompt.compile(**(variables or {})))
        except Exception:
            pass
    return fallback or ""


def observe_span(**kwargs):
    client = get_langfuse_client()
    if not client:
        def decorator(func: Callable[..., Any]):
            return func

        return decorator

    return observe(**kwargs)

