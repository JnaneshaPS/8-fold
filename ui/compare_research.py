from __future__ import annotations

import asyncio
import uuid
from typing import Optional

import streamlit as st

from backend.orchestrator import OrchestratorFactory, CompareResult


class ComparePage:
    def __init__(self, user_id: str):
        self.user_id = user_id

    def render(self, persona_id: Optional[uuid.UUID]) -> None:
        if not persona_id:
            st.info("Select a persona to compare accounts.")
            return

        state_key = f"compare_result_{persona_id}"

        with st.form("compare_form", clear_on_submit=False):
            company_a = st.text_input("Company A")
            company_b = st.text_input("Company B")
            use_cached = st.checkbox("Reuse cached research when possible", value=True)
            submitted = st.form_submit_button(
                "Compare",
                disabled=not company_a.strip() or not company_b.strip(),
            )

        if submitted and company_a.strip() and company_b.strip():
            with st.spinner("Comparing accounts"):
                result = self._run_compare(
                    persona_id=persona_id,
                    company_a=company_a.strip(),
                    company_b=company_b.strip(),
                    use_cached=use_cached,
                )
            st.session_state[state_key] = result.model_dump(mode="json")
            st.success(f"Completed comparison: {company_a.strip()} vs {company_b.strip()}")

        stored = st.session_state.get(state_key)
        if not stored:
            st.info("Run a comparison to view insights.")
            return

        result = CompareResult.model_validate(stored)
        self._render_result(result)

    def _run_compare(
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
        return asyncio.run(
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


