from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from agents import Agent, Runner, function_tool, ModelSettings, RunContextWrapper
from pydantic import BaseModel, Field

from backend.agents.fundamentals import (
    fundamentals_tool,
    fetch_company_fundamentals,
    CompanyFundamentals,
)
from backend.agents.leadership import (
    leadership_tool,
    fetch_leadership,
    LeadershipSummary,
)
from backend.agents.market_news import (
    market_news_tool,
    fetch_market_news,
    MarketNewsSummary,
)
from backend.agents.tech_services import (
    tech_services_tool,
    fetch_tech_and_services,
    TechServicesSummary,
)
from backend.agents.persona_strategy import (
    persona_strategy_tool,
    build_persona_strategy,
    PersonaContext,
    PersonaStrategyOutput,
)
from backend.agents.visualization import (
    stock_visualization_tool,
    get_stock_series,
    StockSeries,
)
from backend.db.client import get_session
from backend.db.cruds import (
    create_report,
    get_latest_report_for_persona_company,
    get_persona,
)
from backend.db.models import PersonaRead, ReportCreate
from backend.memory.mem0_client import add_memory, search_memory


@dataclass
class SessionContext:
    user_id: str
    persona_id: Optional[uuid.UUID] = None
    persona: Optional[PersonaRead] = None


@function_tool(name_override="memory_lookup")
def memory_lookup_tool(
    ctx: RunContextWrapper[SessionContext],
    query: str,
    limit: int = 5,
    persona_only: bool = True,
) -> str:
    """
    Search the Mem0 store for past research, comparisons, or chats.

    Args:
        query: Natural language description of what to retrieve.
        limit: Maximum number of results to return.
        persona_only: Restrict results to the active persona when available.
    """

    user_id = ctx.context.user_id
    persona_id = (
        str(ctx.context.persona_id) if ctx.context.persona_id is not None else None
    )

    try:
        results = search_memory(query=query, user_id=user_id, limit=limit)
    except Exception as exc:  # pragma: no cover - best effort
        return f"Unable to read memory: {exc}"

    entries = results.get("results", []) if isinstance(results, dict) else []
    lines: list[str] = []
    for entry in entries:
        memory_text = entry.get("memory") or entry.get("text") or ""
        metadata = entry.get("metadata") or {}

        if persona_only and persona_id:
            if str(metadata.get("persona_id")) != persona_id:
                continue

        meta_bits: list[str] = []
        if metadata.get("company_name"):
            meta_bits.append(f"company={metadata['company_name']}")
        if metadata.get("mode"):
            meta_bits.append(f"mode={metadata['mode']}")
        if metadata.get("research_type"):
            meta_bits.append(f"research={metadata['research_type']}")
        if metadata.get("comparison_pair"):
            meta_bits.append(f"compare={metadata['comparison_pair']}")

        summary = memory_text.strip()
        if meta_bits:
            summary = f"{summary} [{' | '.join(meta_bits)}]"

        if summary:
            lines.append(summary)

    if not lines:
        return "No relevant memories found."

    return "\n".join(lines[:limit])


class FullResearchReport(BaseModel):
    fundamentals: CompanyFundamentals
    leadership: LeadershipSummary
    news: MarketNewsSummary
    tech_services: TechServicesSummary
    strategy: PersonaStrategyOutput
    stock: Optional[StockSeries] = None


class ResearchOrchestrator:
    def __init__(self, context: SessionContext):
        self.context = context
        self.agent = self._build_research_agent()

    def _build_research_agent(self) -> Agent[SessionContext]:
        instructions = """
You are the Research Orchestrator for deep company research.

Your job is to coordinate specialized tools to build a comprehensive research report:
1. Call fundamentals_tool with the company name first
2. Call leadership_tool, market_news_tool, and tech_services_tool 
3. Call persona_strategy_tool with all gathered data to generate personalized insights
4. If the company is public with a stock ticker, call stock_visualization_tool

Return all results in the FullResearchReport format with all required fields populated.
"""

        return Agent(
            name="Research Orchestrator",
            instructions=instructions,
            model="gpt-5.1",
            output_type=FullResearchReport,
            tools=[
                fundamentals_tool,
                leadership_tool,
                market_news_tool,
                tech_services_tool,
                persona_strategy_tool,
                stock_visualization_tool,
            ],
        )

    async def run_full_research(
        self,
        company_name: str,
        website: Optional[str] = None,
        region_hint: Optional[str] = None,
        save_to_db: bool = True,
    ) -> FullResearchReport:
        if not self.context.persona:
            raise ValueError("Persona must be set in context before running research")

        query = f"Research {company_name}"
        if website:
            query += f" (website: {website})"
        if region_hint:
            query += f" in {region_hint}"

        result = await Runner.run(self.agent, query, context=self.context)
        report = result.final_output_as(FullResearchReport)

        if save_to_db:
            await self._save_report_to_db(report)

        await self._save_to_memory(company_name, report)

        return report

    async def _save_report_to_db(self, report: FullResearchReport) -> None:
        with get_session() as db:
            report_data = ReportCreate(
                persona_id=self.context.persona.id,
                company_name=report.fundamentals.profile.company_name,
                company_website=report.fundamentals.profile.website,
                company_hq=report.fundamentals.profile.headquarters,
                report_json=report.model_dump(mode="json"),
            )
            create_report(db, report_data)

    async def _save_to_memory(
        self, company_name: str, report: FullResearchReport
    ) -> None:
        memory_messages = [
            {
                "role": "user",
                "content": f"I researched {company_name}",
            },
            {
                "role": "assistant",
                "content": f"Completed research on {company_name}. Key insights: {report.strategy.why_it_matters[:200]}",
            },
        ]

        add_memory(
            messages=memory_messages,
            user_id=self.context.user_id,
            metadata={
                "company_name": company_name,
                "persona_id": str(self.context.persona.id),
                "research_type": "full",
            },
        )


class ChatOrchestrator:
    def __init__(self, context: SessionContext):
        self.context = context
        self.conversation_history: List[Dict[str, str]] = []
        self.agent = self._build_chat_agent()

    def _build_chat_agent(self) -> Agent[SessionContext]:
        def dynamic_instructions(ctx, agent):
            persona_info = ""
            if ctx.context.persona:
                persona_info = f"""
Current Persona: {ctx.context.persona.name}
Role: {ctx.context.persona.role}
Company: {ctx.context.persona.company}
"""

            memory_context = ""
            try:
                recent_memories = search_memory(
                    query="recent conversations and research",
                    user_id=ctx.context.user_id,
                    limit=5,
                )
                if recent_memories and "results" in recent_memories:
                    memories = recent_memories["results"]
                    if memories:
                        memory_context = "\n".join(
                            [f"- {m.get('memory', '')}" for m in memories[:3]]
                        )
            except Exception:
                pass

            return f"""
You are a helpful B2B research assistant in Chat Mode.

{persona_info}

Recent context:
{memory_context}

You can:
- Answer questions about companies, industries, and market trends
- Provide quick summaries and insights
- Help users understand their research targets
- Suggest when to run a full Research Mode report
- Call the memory_lookup tool whenever you need details from past research,
  comparisons, or previous conversations for this persona.

Be conversational, helpful, and concise. If the user asks for deep research on a company,
suggest they use Research Mode for a complete structured report.
"""

        return Agent(
            name="Chat Assistant",
            instructions=dynamic_instructions,
            model="gpt-5.1",
            tools=[memory_lookup_tool],
        )

    async def chat(self, message: str) -> str:
        self.conversation_history.append({"role": "user", "content": message})
        
        input_for_agent = self.conversation_history if len(self.conversation_history) > 1 else message
        
        result = await Runner.run(
            self.agent,
            input_for_agent,
            context=self.context,
        )

        assistant_response = result.final_output
        self.conversation_history.append({"role": "assistant", "content": assistant_response})
        
        await self._save_chat_to_memory(message, assistant_response)

        return assistant_response

    async def _save_chat_to_memory(self, user_message: str, assistant_response: str):
        metadata: dict[str, Any] = {"mode": "chat"}
        if self.context.persona_id:
            metadata["persona_id"] = str(self.context.persona_id)

        add_memory(
            messages=[
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_response},
            ],
            user_id=self.context.user_id,
            metadata=metadata,
        )


class CompareResult(BaseModel):
    company_a_name: str
    company_b_name: str
    company_a: Dict[str, Any]
    company_b: Dict[str, Any]
    comparison_summary: str
    recommendation: str
    opportunities_comparison: List[str]
    risks_comparison: List[str]


class CompareOrchestrator:
    def __init__(self, context: SessionContext):
        self.context = context

    async def compare_companies(
        self,
        company_a: str,
        company_b: str,
        use_cached: bool = True,
    ) -> CompareResult:
        if not self.context.persona:
            raise ValueError("Persona must be set in context before comparison")

        report_a = await self._get_or_create_report(company_a, use_cached)
        report_b = await self._get_or_create_report(company_b, use_cached)

        comparison_summary = self._build_comparison_summary(
            report_a, report_b, company_a, company_b
        )
        recommendation = self._build_recommendation(
            report_a, report_b, company_a, company_b
        )

        opps_a = [
            opp.title for opp in report_a.strategy.opportunities_for_me[:3]
        ]
        opps_b = [
            opp.title for opp in report_b.strategy.opportunities_for_me[:3]
        ]

        risks_a = [risk.risk for risk in report_a.strategy.risks_blockers[:3]]
        risks_b = [risk.risk for risk in report_b.strategy.risks_blockers[:3]]

        result = CompareResult(
            company_a_name=company_a,
            company_b_name=company_b,
            company_a={
                "name": company_a,
                "profile": report_a.fundamentals.profile.model_dump(),
                "opportunities": opps_a,
                "risks": risks_a,
            },
            company_b={
                "name": company_b,
                "profile": report_b.fundamentals.profile.model_dump(),
                "opportunities": opps_b,
                "risks": risks_b,
            },
            comparison_summary=comparison_summary,
            recommendation=recommendation,
            opportunities_comparison=[
                f"{company_a}: {', '.join(opps_a)}",
                f"{company_b}: {', '.join(opps_b)}",
            ],
            risks_comparison=[
                f"{company_a}: {', '.join(risks_a)}",
                f"{company_b}: {', '.join(risks_b)}",
            ],
        )

        await self._save_comparison_to_memory(
            company_a=company_a,
            company_b=company_b,
            summary=comparison_summary,
            recommendation=recommendation,
        )

        return result

    async def _get_or_create_report(
        self, company_name: str, use_cached: bool
    ) -> FullResearchReport:
        if use_cached:
            with get_session() as db:
                existing = get_latest_report_for_persona_company(
                    db, self.context.persona.id, company_name
                )
                if existing:
                    return FullResearchReport.model_validate(
                        existing.report_json
                    )

        orchestrator = ResearchOrchestrator(self.context)
        return await orchestrator.run_full_research(
            company_name=company_name,
            save_to_db=True,
        )

    def _build_comparison_summary(
        self,
        report_a: FullResearchReport,
        report_b: FullResearchReport,
        company_a: str,
        company_b: str,
    ) -> str:
        profile_a = report_a.fundamentals.profile
        profile_b = report_b.fundamentals.profile

        return f"""
{company_a} ({profile_a.headquarters or 'Unknown'}) vs {company_b} ({profile_b.headquarters or 'Unknown'})

{company_a}: {profile_a.short_description or 'N/A'}
{company_b}: {profile_b.short_description or 'N/A'}

Industry: {profile_a.industry or 'N/A'} vs {profile_b.industry or 'N/A'}
Status: {profile_a.public_status} vs {profile_b.public_status}
"""

    def _build_recommendation(
        self,
        report_a: FullResearchReport,
        report_b: FullResearchReport,
        company_a: str,
        company_b: str,
    ) -> str:
        opps_a_count = len(report_a.strategy.opportunities_for_me)
        opps_b_count = len(report_b.strategy.opportunities_for_me)
        risks_a_count = len(report_a.strategy.risks_blockers)
        risks_b_count = len(report_b.strategy.risks_blockers)

        if opps_a_count > opps_b_count and risks_a_count <= risks_b_count:
            priority = company_a
            reason = f"More opportunities ({opps_a_count} vs {opps_b_count}) with manageable risks"
        elif opps_b_count > opps_a_count and risks_b_count <= risks_a_count:
            priority = company_b
            reason = f"More opportunities ({opps_b_count} vs {opps_a_count}) with manageable risks"
        elif risks_a_count < risks_b_count:
            priority = company_a
            reason = f"Lower risk profile ({risks_a_count} vs {risks_b_count} blockers)"
        else:
            priority = company_b
            reason = f"Lower risk profile ({risks_b_count} vs {risks_a_count} blockers)"

        return f"Priority: {priority}. {reason}"

    async def _save_comparison_to_memory(
        self,
        *,
        company_a: str,
        company_b: str,
        summary: str,
        recommendation: str,
    ) -> None:
        metadata: dict[str, Any] = {
            "mode": "compare",
            "comparison_pair": f"{company_a} vs {company_b}",
        }
        if self.context.persona_id:
            metadata["persona_id"] = str(self.context.persona_id)

        add_memory(
            messages=[
                {
                    "role": "user",
                    "content": f"Compare {company_a} vs {company_b}",
                },
                {
                    "role": "assistant",
                    "content": f"{recommendation}\n\nSummary:\n{summary.strip()}",
                },
            ],
            user_id=self.context.user_id,
            metadata=metadata,
        )


class OrchestratorFactory:
    @staticmethod
    def create_research_orchestrator(
        user_id: str, persona_id: uuid.UUID
    ) -> ResearchOrchestrator:
        with get_session() as db:
            persona = get_persona(db, persona_id)
            if not persona:
                raise ValueError(f"Persona {persona_id} not found")

        context = SessionContext(
            user_id=user_id,
            persona_id=persona_id,
            persona=persona,
        )
        return ResearchOrchestrator(context)

    @staticmethod
    def create_chat_orchestrator(
        user_id: str, persona_id: Optional[uuid.UUID] = None
    ) -> ChatOrchestrator:
        persona = None
        if persona_id:
            with get_session() as db:
                persona = get_persona(db, persona_id)

        context = SessionContext(
            user_id=user_id,
            persona_id=persona_id,
            persona=persona,
        )
        return ChatOrchestrator(context)

    @staticmethod
    def create_compare_orchestrator(
        user_id: str, persona_id: uuid.UUID
    ) -> CompareOrchestrator:
        with get_session() as db:
            persona = get_persona(db, persona_id)
            if not persona:
                raise ValueError(f"Persona {persona_id} not found")

        context = SessionContext(
            user_id=user_id,
            persona_id=persona_id,
            persona=persona,
        )
        return CompareOrchestrator(context)

