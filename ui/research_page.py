from __future__ import annotations

import asyncio
import uuid
from typing import Optional

import pandas as pd
import streamlit as st

from backend.orchestrator import OrchestratorFactory, FullResearchReport


class ResearchPage:
    def __init__(self, user_id: str):
        self.user_id = user_id

    def render(self, persona_id: Optional[uuid.UUID]) -> None:
        if not persona_id:
            st.info("Select a persona to run research.")
            return

        state_key = f"research_report_{persona_id}"

        with st.form("research_form", clear_on_submit=False):
            company = st.text_input("Company name")
            website = st.text_input("Website", placeholder="example.com")
            region = st.text_input("Region hint", placeholder="US, EMEA, APAC")
            submitted = st.form_submit_button("Run research", disabled=not company.strip())

        if submitted and company.strip():
            with st.spinner("Running research"):
                report = self._run_research(
                    persona_id=persona_id,
                    company=company.strip(),
                    website=website.strip() or None,
                    region=region.strip() or None,
                )
            st.session_state[state_key] = report.model_dump(mode="json")
            st.success(f"Completed research for {company.strip()}")

        stored = st.session_state.get(state_key)
        if not stored:
            st.info("Run research to view the full report.")
            return

        report = FullResearchReport.model_validate(stored)
        self._render_report(report)

    def _run_research(
        self,
        *,
        persona_id: uuid.UUID,
        company: str,
        website: Optional[str],
        region: Optional[str],
    ) -> FullResearchReport:
        orchestrator = OrchestratorFactory.create_research_orchestrator(
            self.user_id,
            persona_id,
        )
        return asyncio.run(
            orchestrator.run_full_research(
                company_name=company,
                website=website,
                region_hint=region,
                save_to_db=True,
            )
        )

    def _render_report(self, report: FullResearchReport) -> None:
        self._render_profile(report)
        self._render_stock(report)
        self._render_leadership(report)
        self._render_news(report)
        self._render_products(report)
        self._render_tech(report)
        self._render_strategy(report)

    def _render_profile(self, report: FullResearchReport) -> None:
        profile = report.fundamentals.profile
        st.subheader("Profile")
        cols = st.columns(3)
        cols[0].write(f"**Company**: {profile.company_name}")
        cols[1].write(f"**HQ**: {profile.headquarters or 'Unknown'}")
        cols[2].write(f"**Website**: {profile.website or 'Unknown'}")
        cols = st.columns(3)
        cols[0].write(f"**Industry**: {profile.industry or 'Unknown'}")
        cols[1].write(f"**Public status**: {profile.public_status}")
        cols[2].write(f"**Ticker**: {profile.stock_ticker or 'N/A'}")
        key_numbers = report.fundamentals.key_numbers
        cols = st.columns(3)
        cols[0].write(f"**Revenue (B USD)**: {key_numbers.latest_revenue_usd_bil or 'N/A'}")
        cols[1].write(f"**YoY growth (%)**: {key_numbers.yoy_revenue_growth_pct or 'N/A'}")
        cols[2].write(f"**Employees**: {key_numbers.employee_count_estimate or 'N/A'}")
        st.write(report.fundamentals.business_model or "No business model summary available.")

    def _render_stock(self, report: FullResearchReport) -> None:
        stock = report.stock
        st.subheader("Market data")
        if not stock or not stock.points:
            st.write("No public market data available.")
            return
        data = pd.DataFrame(
            [
                {"date": point.date, "close": point.close}
                for point in stock.points
            ]
        )
        data = data.sort_values("date")
        st.line_chart(data, x="date", y="close")

    def _render_leadership(self, report: FullResearchReport) -> None:
        st.subheader("Leadership")
        leaders = report.leadership.leaders
        if not leaders:
            st.write("No leadership data available.")
            return
        for leader in leaders:
            block = f"**{leader.name}** — {leader.title}"
            if leader.location:
                block += f" ({leader.location})"
            st.markdown(block)
            if leader.notes:
                st.markdown(leader.notes)
            if leader.linkedin_url:
                st.markdown(f"[LinkedIn]({leader.linkedin_url})")
            st.divider()

    def _render_news(self, report: FullResearchReport) -> None:
        st.subheader("Latest news")
        items = report.news.items
        if not items:
            st.write("No recent news captured.")
            return
        for item in items:
            st.markdown(f"**{item.title}**")
            meta = []
            if item.published_at:
                meta.append(item.published_at)
            if item.sentiment:
                meta.append(f"Sentiment: {item.sentiment}")
            if meta:
                st.caption(" | ".join(meta))
            st.write(item.summary)
            st.markdown(f"[Read more]({item.url})")
            st.divider()

    def _render_products(self, report: FullResearchReport) -> None:
        st.subheader("Services and products")
        offerings = report.tech_services.products_and_services
        if not offerings:
            st.write("No products captured.")
            return
        for product in offerings:
            st.markdown(f"**{product.name}**")
            if product.category:
                st.caption(product.category)
            if product.description:
                st.write(product.description)
            if product.target_users:
                st.write(", ".join(product.target_users))
            st.divider()

    def _render_tech(self, report: FullResearchReport) -> None:
        st.subheader("Tech stack")
        stack = report.tech_services.tech_stack
        if not stack:
            st.write("No tech stack signals captured.")
            return
        for component in stack:
            st.markdown(f"**{component.area}**")
            if component.technologies:
                st.write(", ".join(component.technologies))
            if component.confidence_comment:
                st.caption(component.confidence_comment)
            st.divider()

    def _render_strategy(self, report: FullResearchReport) -> None:
        strategy = report.strategy
        st.subheader("Why it matters")
        st.write(strategy.why_it_matters)
        st.subheader("Opportunities")
        if strategy.opportunities_for_me:
            for opp in strategy.opportunities_for_me:
                st.markdown(f"**{opp.title}**")
                st.write(opp.description)
                if opp.evidence:
                    st.write("\n".join([f"- {item}" for item in opp.evidence]))
                st.divider()
        else:
            st.write("No opportunities captured.")
        st.subheader("Key unknowns")
        if strategy.key_unknowns:
            for unknown in strategy.key_unknowns:
                st.markdown(f"**{unknown.question}**")
                st.write(unknown.why_it_matters)
                if unknown.how_to_find_out:
                    st.caption(unknown.how_to_find_out)
                st.divider()
        else:
            st.write("No unknowns captured.")
        st.subheader("Risks and blockers")
        if strategy.risks_blockers:
            for risk in strategy.risks_blockers:
                st.markdown(f"**{risk.risk}**")
                st.write(risk.impact)
                if risk.mitigation:
                    st.caption(risk.mitigation)
                st.divider()
        else:
            st.write("No risks captured.")
        st.subheader("Next steps")
        if strategy.next_steps:
            for step in strategy.next_steps:
                line = step.action
                if step.owner:
                    line += f" — {step.owner}"
                if step.timeframe:
                    line += f" ({step.timeframe})"
                st.write(line)
        else:
            st.write("No next steps captured.")
        st.subheader("Suggested follow-ups")
        if strategy.suggested_followups:
            for suggestion in strategy.suggested_followups:
                st.write(f"- {suggestion}")
        else:
            st.write("No follow-up prompts available.")


