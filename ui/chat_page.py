from __future__ import annotations

import asyncio
import uuid
from typing import Optional

import streamlit as st

from backend.orchestrator import OrchestratorFactory, ChatOrchestrator


class ChatPage:
    def __init__(self, user_id: str):
        self.user_id = user_id

    def render(self, persona_id: Optional[uuid.UUID]) -> None:
        if not persona_id:
            st.info("Select a persona to start chatting.")
            return
        orchestrator = self._get_orchestrator(persona_id)
        history_key = self._history_key(persona_id)
        if history_key not in st.session_state:
            st.session_state[history_key] = []
        for role, content in st.session_state[history_key]:
            st.chat_message(role).write(content)
        prompt = st.chat_input("Ask anything about your accounts.")
        if prompt:
            response = self._run(orchestrator.chat(prompt))
            st.session_state[history_key].extend(
                [
                    ("user", prompt),
                    ("assistant", response),
                ]
            )
            st.rerun()

    def _get_orchestrator(self, persona_id: uuid.UUID) -> ChatOrchestrator:
        key = f"chat_orchestrator_{persona_id}"
        if key not in st.session_state:
            st.session_state[key] = OrchestratorFactory.create_chat_orchestrator(
                self.user_id,
                persona_id,
            )
        return st.session_state[key]

    def _history_key(self, persona_id: uuid.UUID) -> str:
        return f"chat_history_{persona_id}"

    def _run(self, coro):
        return asyncio.run(coro)

