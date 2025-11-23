from __future__ import annotations

import re
import uuid
from typing import Dict, List, Optional

import asyncio
import threading

import streamlit as st

from backend.orchestrator import (
    OrchestratorFactory,
    ChatOrchestrator,
    FullResearchReport,
    CompareResult,
)
from backend.utils.company_parser import extract_companies as llm_extract_companies


class ChatPage:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self._loop_key = "chat_async_loop"

    def render(self, persona_id: Optional[uuid.UUID]) -> None:
        if not persona_id:
            st.info("Select a persona to start chatting.")
            return

        mode = self._mode_selector(persona_id)
        history_key = self._history_key(persona_id)
        if history_key not in st.session_state:
            st.session_state[history_key] = []

        for entry in st.session_state[history_key]:
            if isinstance(entry, dict):
                st.chat_message(entry["role"]).write(entry["content"])
            else:
                role, content = entry
            st.chat_message(role).write(content)

        prompt = st.chat_input("Type your message")
        if not prompt:
            return

        orchestrator = self._get_chat_orchestrator(persona_id)
        self._append_history(history_key, "user", prompt)
        st.chat_message("user").write(prompt)

        try:
            assistant_message = st.chat_message("assistant")
            assistant_message.write("...")
            if mode == "Chat":
                response = self._run(orchestrator.chat(prompt))
            elif mode == "Research":
                response = self._handle_research(persona_id, prompt)
            else:
                response = self._handle_compare(persona_id, prompt)
            assistant_message.empty()
            assistant_message.write(response)
            self._append_history(history_key, "assistant", response)
        except Exception as exc:  # pragma: no cover - UI feedback
            error_text = f"Sorry, something went wrong: {exc}"
            assistant_message.write(error_text)
            self._append_history(history_key, "assistant", error_text)

    def _mode_selector(self, persona_id: uuid.UUID) -> str:
        key = f"chat_mode_{persona_id}"
        if key not in st.session_state:
            st.session_state[key] = "Chat"
        st.sidebar.subheader("Mode")
        st.session_state[key] = st.sidebar.radio(
            "Conversation mode",
            options=["Chat", "Research", "Compare"],
            index=["Chat", "Research", "Compare"].index(st.session_state[key]),
            key=f"mode_radio_{persona_id}",
        )
        return st.session_state[key]

    def _handle_research(self, persona_id: uuid.UUID, request: str) -> str:
        orchestrator = OrchestratorFactory.create_research_orchestrator(
            self.user_id,
            persona_id,
        )
        with st.spinner("Running research"):
            report = self._run(
                orchestrator.run_full_research(
                    request=request.strip(),
                    save_to_db=True,
                )
            )
        return self._format_research_report(report)

    def _handle_compare(self, persona_id: uuid.UUID, request: str) -> str:
        pending_key = f"compare_pending_{persona_id}"
        companies = [
            self._clean_company_name(name)
            for name in llm_extract_companies(request, max_companies=2)
        ]
        companies = [name for name in companies if name]
        if not companies:
            companies = self._extract_companies(request)
        pending = st.session_state.get(pending_key)

        if len(companies) >= 2:
            company_a, company_b = companies[:2]
        elif len(companies) == 1:
            if pending:
                company_a, company_b = pending, companies[0]
                st.session_state.pop(pending_key, None)
            else:
                st.session_state[pending_key] = companies[0]
                return f"Noted {companies[0]}. Please provide another company to compare."
        else:
            return (
                "I couldn't identify any company names. "
                "Try phrasing it like 'Compare Stripe vs Snowflake'."
            )

        orch = OrchestratorFactory.create_compare_orchestrator(
            self.user_id,
            persona_id,
        )
        result = self._run(
            orch.compare_companies(
                company_a=company_a,
                company_b=company_b,
                use_cached=True,
            )
        )
        return self._format_compare_result(result)

    def _format_research_report(self, report: FullResearchReport) -> str:
        profile = report.fundamentals.profile
        lines = [
            f"## {profile.company_name} — {profile.industry or 'Unknown industry'}",
            f"- HQ: {profile.headquarters or 'Unknown'}",
            f"- Status: {profile.public_status}",
            f"- Website: {profile.website or 'N/A'}",
            "",
            f"### Why it matters\n{report.strategy.why_it_matters}",
        ]

        leaders = report.leadership.leaders[:5]
        if leaders:
            lines.append("\n### Leadership")
            for leader in leaders:
                block = f"- **{leader.name}**, {leader.title}"
                if leader.location:
                    block += f" ({leader.location})"
                lines.append(block)

        if report.strategy.opportunities_for_me:
            lines.append("\n### Opportunities")
            for opp in report.strategy.opportunities_for_me[:6]:
                evidence = ""
                if opp.evidence:
                    evidence = "\n    " + "\n    ".join(f"- {ev}" for ev in opp.evidence[:3])
                lines.append(f"- **{opp.title}**: {opp.description}{evidence}")

        if report.strategy.key_unknowns:
            lines.append("\n### Key unknowns")
            for unknown in report.strategy.key_unknowns[:6]:
                block = f"- **{unknown.question}**: {unknown.why_it_matters}"
                if unknown.how_to_find_out:
                    block += f" _(How to find out: {unknown.how_to_find_out})_"
                lines.append(block)

        if report.strategy.risks_blockers:
            lines.append("\n### Risks & blockers")
            for risk in report.strategy.risks_blockers[:6]:
                block = f"- **{risk.risk}**: {risk.impact}"
                if risk.mitigation:
                    block += f" _(Mitigation: {risk.mitigation})_"
                lines.append(block)

        if report.strategy.next_steps:
            lines.append("\n### Next steps")
            for step in report.strategy.next_steps[:6]:
                line = f"- {step.action}"
                if step.owner:
                    line += f" (Owner: {step.owner})"
                if step.timeframe:
                    line += f" [{step.timeframe}]"
                lines.append(line)

        if report.strategy.suggested_followups:
            lines.append("\n### Suggested follow-ups")
            for suggestion in report.strategy.suggested_followups[:6]:
                lines.append(f"- {suggestion}")

        if report.news.items:
            lines.append("\n### Latest news")
            for item in report.news.items[:5]:
                meta_bits = []
                if item.published_at:
                    meta_bits.append(item.published_at)
                if item.sentiment:
                    meta_bits.append(item.sentiment)
                meta = f" ({' | '.join(meta_bits)})" if meta_bits else ""
                lines.append(f"- **{item.title}**{meta}\n  {item.summary}")

        if report.tech_services.products_and_services:
            lines.append("\n### Key products / services")
            for product in report.tech_services.products_and_services[:6]:
                desc = product.description or "No description"
                lines.append(f"- **{product.name}** ({product.category or 'N/A'}): {desc}")

        if report.tech_services.tech_stack:
            lines.append("\n### Tech stack highlights")
            for component in report.tech_services.tech_stack[:6]:
                techs = ", ".join(component.technologies[:6]) or "Unknown"
                lines.append(f"- **{component.area}**: {techs}")

        return "\n".join(lines)

    def _format_compare_result(self, result: CompareResult) -> str:
        lines = [
            f"## Recommendation\n{result.recommendation}",
            "\n## Summary",
            result.comparison_summary.strip(),
                ]

        lines.append("\n## Company snapshots")
        lines.append(self._format_company_block(result.company_a))
        lines.append(self._format_company_block(result.company_b))

        if result.opportunities_comparison:
            lines.append("\n## Opportunities")
            lines.extend([f"- {entry}" for entry in result.opportunities_comparison])

        if result.risks_comparison:
            lines.append("\n## Risks")
            lines.extend([f"- {entry}" for entry in result.risks_comparison])

        return "\n".join(lines)

    def _format_company_block(self, data: Dict[str, any]) -> str:
        profile = data.get("profile", {})
        lines = [
            f"### {data.get('name', 'Company')}",
            f"- HQ: {profile.get('headquarters', 'Unknown')}",
            f"- Industry: {profile.get('industry', 'Unknown')}",
            f"- Status: {profile.get('public_status', 'Unknown')}",
            f"- Website: {profile.get('website', 'Unknown')}",
        ]
        if data.get("opportunities"):
            lines.append("  - Opportunities:")
            lines.extend([f"    • {opp}" for opp in data["opportunities"][:4]])
        if data.get("risks"):
            lines.append("  - Risks:")
            lines.extend([f"    • {risk}" for risk in data["risks"][:4]])
        return "\n".join(lines)

    def _clean_company_name(self, text: str) -> str:
        name = text.strip()
        name = re.sub(
            r"^(please|kindly|would you|could you|can you)\s+",
            "",
            name,
            flags=re.IGNORECASE,
        )
        name = re.sub(r"^(compare|tell me about|versus|vs)\s+", "", name, flags=re.IGNORECASE)
        name = re.sub(r"\s*(please|thanks|thank you)$", "", name, flags=re.IGNORECASE)
        name = re.sub(r"[^\w\s&\-.]", "", name)
        return re.sub(r"\s+", " ", name).strip()

    def _extract_companies(self, request: str) -> List[str]:
        text = request.strip()
        if not text:
            return []
        parts = re.split(
            r"\s+vs\.?\s+|\s+versus\s+|\s+and\s+",
            text,
            flags=re.IGNORECASE,
        )
        cleaned = [self._clean_company_name(chunk) for chunk in parts if chunk.strip()]
        if len(cleaned) >= 2:
            return cleaned[:2]
        if "," in text:
            chunks = [
                self._clean_company_name(chunk)
                for chunk in text.split(",")
                if chunk.strip()
            ]
            chunks = [c for c in chunks if c]
            if chunks:
                return chunks[:2]
        single = self._clean_company_name(text)
        return [single] if single else []

    def _get_chat_orchestrator(self, persona_id: uuid.UUID) -> ChatOrchestrator:
        key = f"chat_orchestrator_{persona_id}"
        if key not in st.session_state:
            st.session_state[key] = OrchestratorFactory.create_chat_orchestrator(
                self.user_id,
                persona_id,
            )
        return st.session_state[key]

    def _history_key(self, persona_id: uuid.UUID) -> str:
        return f"chat_history_{persona_id}"

    def _append_history(self, key: str, role: str, content: str) -> None:
        st.session_state[key].append({"role": role, "content": content})

    def _run(self, coro):
        loop = self._get_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop_key in st.session_state:
            loop = st.session_state[self._loop_key]
            if loop.is_closed():
                st.session_state.pop(self._loop_key, None)
            else:
                return loop

        loop = asyncio.new_event_loop()

        def _run_loop():
            asyncio.set_event_loop(loop)
            loop.run_forever()

        thread = threading.Thread(target=_run_loop, daemon=True)
        thread.start()
        st.session_state[self._loop_key] = loop
        return loop
