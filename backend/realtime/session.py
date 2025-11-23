from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx

from backend.db.models import PersonaRead
from backend.memory.mem0_client import search_memory, MEM0_ENABLED

REALTIME_SESSION_ENDPOINT = os.getenv(
    "OPENAI_REALTIME_SESSION_URL",
    "https://api.openai.com/v1/realtime/sessions",
)
REALTIME_MODEL = os.getenv(
    "OPENAI_REALTIME_MODEL",
    "gpt-4o-realtime-preview",
)
REALTIME_VOICE = os.getenv("OPENAI_REALTIME_VOICE", "alloy")


class RealtimeSessionError(RuntimeError):
    pass


def build_persona_prompt(persona: Optional[PersonaRead], user_id: str) -> str:
    if not persona:
        return (
            "You are a realtime B2B research assistant. "
            "Keep responses short, professional, and focused on actionable account planning."
        )

    memory_context = ""
    if MEM0_ENABLED:
        try:
            mem_response = search_memory(
                query="recent conversations and insights",
                user_id=user_id,
                limit=3,
            )
            if mem_response and "results" in mem_response:
                memories = mem_response["results"]
                trimmed = [m.get("memory", "").strip() for m in memories if m.get("memory")]
                if trimmed:
                    memory_context = "\nRecent notes:\n- " + "\n- ".join(trimmed)
        except Exception:
            memory_context = ""

    pieces = [
        f"User persona: {persona.name}",
        f"Role: {persona.role or 'Unknown'}",
        f"Company: {persona.company or 'Unknown'}",
    ]
    if persona.goal:
        pieces.append(f"Goal: {persona.goal}")
    if persona.notes:
        pieces.append(f"Notes: {persona.notes}")

    persona_blob = "\n".join(pieces)
    return (
        "You are a realtime voice assistant for B2B account research. "
        "Speak like a pragmatic sales strategist, surface opportunities, risks, and next steps.\n"
        f"{persona_blob}\n"
        f"{memory_context}\n"
        "Keep responses brief, natural, and offer to run deeper research if helpful."
    )


def create_realtime_session_config(
    *,
    persona: Optional[PersonaRead],
    user_id: str,
) -> Dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RealtimeSessionError("OPENAI_API_KEY is required for realtime sessions.")

    instructions = build_persona_prompt(persona, user_id)
    payload: Dict[str, Any] = {
      "model": REALTIME_MODEL,
      "voice": REALTIME_VOICE,
      "modalities": ["audio", "text"],
      "instructions": instructions,
      "input_audio_format": "pcm16",
      "output_audio_format": "pcm16",
      "turn_detection": {"type": "server_vad"},
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "realtime=v1",
    }

    try:
        response = httpx.post(
            REALTIME_SESSION_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text if exc.response is not None else ""
        raise RealtimeSessionError(
            f"Failed to create realtime session ({exc.response.status_code}): {detail}"
        ) from exc
    except httpx.HTTPError as exc:
        raise RealtimeSessionError(f"Failed to create realtime session: {exc}") from exc

    data = response.json()
    client_secret = data.get("client_secret", {})
    token = client_secret.get("value")
    if not token:
        raise RealtimeSessionError(
            "Realtime session did not return a client_secret token."
        )

    return {
        "session_id": data.get("id"),
        "token": token,
        "expires_at": client_secret.get("expires_at"),
        "model": REALTIME_MODEL,
        "voice": REALTIME_VOICE,
    }

