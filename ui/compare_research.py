from __future__ import annotations

import uuid
from typing import Optional

import streamlit as st

import re

import asyncio
import threading

from backend.orchestrator import OrchestratorFactory, CompareResult


class ComparePage:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self._loop_key = "compare_async_loop"

    def render(self, persona_id: Optional[uuid.UUID]) -> None:
        if not persona_id:
            st.info("Select a persona to compare accounts.")
            return

        state_key = f"compare_result_{persona_id}"
        pending_key = f"compare_pending_{persona_id}"

        request = st.text_input(
            "What comparison do you need?",
            placeholder="Example: Compare Stripe vs Razorpay for enterprise security.",
        )
        use_cached = st.checkbox("Reuse cached research when possible", value=True)
        if st.button("Run comparison", disabled=not request.strip()):
            request_text = request.strip()
            companies = self._extract_companies(request_text)
            pending = st.session_state.get(pending_key)

            if len(companies) >= 2:
                company_a, company_b = companies[0], companies[1]
                result = self._execute_compare(
                    persona_id=persona_id,
                    company_a=company_a,
                    company_b=company_b,
                    use_cached=use_cached,
                )
                st.session_state[state_key] = result.model_dump(mode="json")
                st.session_state.pop(pending_key, None)
                st.success(f"Completed comparison: {company_a} vs {company_b}")
            elif len(companies) == 1:
                if pending:
                    company_a = pending
                    company_b = companies[0]
                    result = self._execute_compare(
                        persona_id=persona_id,
                        company_a=company_a,
                        company_b=company_b,
                        use_cached=use_cached,
                    )
                    st.session_state[state_key] = result.model_dump(mode="json")
                    st.session_state.pop(pending_key, None)
                    st.success(f"Completed comparison: {company_a} vs {company_b}")
                else:
                    st.session_state[pending_key] = companies[0]
                    st.info(
                        f"Noted {companies[0]}. Please provide another company to compare.",
                    )
            else:
                st.warning(
                    "Couldn't identify any company names. "
                    "Try phrasing it like 'Compare CompanyA vs CompanyB'.",
                )

        stored = st.session_state.get(state_key)
        if not stored:
            st.info("Run a comparison to view insights.")
            return

        result = CompareResult.model_validate(stored)
        self._render_result(result)

    def _execute_compare(
        self,
        *,
        persona_id: uuid.UUID,
        company_a: str,
        company_b: str,
        use_cached: bool,
    ) -> CompareResult:
        orchestrator = OrchestratorFactory.create_compare_orchestrator(
            self.user_id,
            persona_id,
        )
        return self._run_async(
            orchestrator.compare_companies(
                company_a=company_a,
                company_b=company_b,
                use_cached=use_cached,
            )
        )

    def _render_result(self, result: CompareResult) -> None:
        st.subheader("Recommendation")
        st.success(result.recommendation)

        st.subheader("Summary")
        st.write(result.comparison_summary.strip())

        cols = st.columns(2)
        self._render_company_card(
            cols[0],
            label=result.company_a_name,
            data=result.company_a,
        )
        self._render_company_card(
            cols[1],
            label=result.company_b_name,
            data=result.company_b,
        )

        st.subheader("Opportunities")
        if result.opportunities_comparison:
            for line in result.opportunities_comparison:
                st.write(f"- {line}")
        else:
            st.write("No opportunities captured.")

        st.subheader("Risks and blockers")
        if result.risks_comparison:
            for line in result.risks_comparison:
                st.write(f"- {line}")
        else:
            st.write("No risks captured.")

    def _render_company_card(
        self,
        column,
        *,
        label: str,
        data: dict,
    ) -> None:
        column.markdown(f"### {label}")
        profile = data.get("profile", {})
        column.write(profile.get("short_description") or "No overview available.")
        column.write(f"Headquarters: {profile.get('headquarters') or 'Unknown'}")
        column.write(f"Industry: {profile.get('industry') or 'Unknown'}")
        column.write(f"Status: {profile.get('public_status') or 'Unknown'}")
        column.write(f"Website: {profile.get('website') or 'Unknown'}")
        if data.get("opportunities"):
            column.markdown("**Opportunities**")
            for opp in data["opportunities"]:
                column.write(f"- {opp}")
        if data.get("risks"):
            column.markdown("**Risks**")
            for risk in data["risks"]:
                column.write(f"- {risk}")

    def _extract_companies(self, request: str) -> list[str]:
        text = request.strip()
        if not text:
            return []

        parts = re.split(r"\s+vs\.?\s+|\s+versus\s+", text, flags=re.IGNORECASE)
        if len(parts) >= 2:
            return [parts[0].strip(" ,.;") or "", parts[1].strip(" ,.;") or ""]

        if "," in text:
            chunks = [chunk.strip(" ,.;") for chunk in text.split(",") if chunk.strip()]
            return chunks[:2]

        return [text]

    def _run_async(self, coro):
        loop = self._get_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop_key in st.session_state:
            loop = st.session_state[self._loop_key]
            if not loop.is_closed():
                return loop
            st.session_state.pop(self._loop_key, None)

        loop = asyncio.new_event_loop()

        def _run_loop():
            asyncio.set_event_loop(loop)
            loop.run_forever()

        threading.Thread(target=_run_loop, daemon=True).start()
        st.session_state[self._loop_key] = loop
        return loop

