from __future__ import annotations

import json
from typing import List, Optional

from pydantic import BaseModel, Field
from agents import function_tool


from backend.external.perplexity import ask_structured_perplexity
from backend.agents.fundamentals import CompanyFundamentals
from backend.agents.market_news import MarketNewsSummary
from backend.agents.tech_services import TechServicesSummary


class PersonaContext(BaseModel):
    """
    Lightweight view of the persona for strategy reasoning.

    You can build this from your DB Persona model before calling the agent.
    """

    id: str = Field(description="Persona ID as string (UUID in your DB)")
    name: str = Field(description="Name or label for this persona, e.g. 'Prajwal – SE at Armor1'")
    role: str = Field(description="Job title / role, e.g. 'Security engineer', 'AE', 'CISO'")
    company: str = Field(description="Persona's own company name")
    region: Optional[str] = Field(
        default=None,
        description="Region/country, e.g. 'India', 'US West'",
    )
    focus_notes: Optional[str] = Field(
        default=None,
        description="Free-form notes about what they care about (entered by user)",
    )


class OpportunityItem(BaseModel):
    title: str = Field(description="Short title of the opportunity")
    description: str = Field(
        description="2–4 sentences explaining why this is a real opportunity",
    )
    evidence: List[str] = Field(
        default_factory=list,
        description="Bullets tying this opportunity back to fundamentals/news/tech/persona",
    )


class UnknownItem(BaseModel):
    question: str = Field(description="What do we NOT know yet?")
    why_it_matters: str = Field(
        description="Why this unknown is important for closing / working the account",
    )
    how_to_find_out: Optional[str] = Field(
        default=None,
        description="How we might answer this (e.g. 'ask customer', 'internal CRM')",
    )


class RiskItem(BaseModel):
    risk: str = Field(description="Risk or blocker title")
    impact: str = Field(description="Short explanation of impact if this risk is real")
    mitigation: Optional[str] = Field(
        default=None,
        description="Concrete mitigation ideas, if any",
    )


class NextStepItem(BaseModel):
    action: str = Field(description="Specific next action, e.g. 'Email X', 'Research Y'")
    owner: Optional[str] = Field(
        default=None,
        description="Who should own this (persona, teammate, etc.)",
    )
    timeframe: Optional[str] = Field(
        default=None,
        description="Rough timeframe, e.g. 'this week', 'next 2 weeks'",
    )


class PersonaStrategyOutput(BaseModel):
    """
    Full payload for the 'Why it matters / Opportunities / Risks / Next steps' area.
    """

    why_it_matters: str = Field(
        description="Short narrative linking persona → target company",
    )
    opportunities_for_me: List[OpportunityItem] = Field(
        default_factory=list,
        description="Concrete opportunities for this persona with this account",
    )
    key_unknowns: List[UnknownItem] = Field(
        default_factory=list,
        description="Important open questions we still need to answer",
    )
    risks_blockers: List[RiskItem] = Field(
        default_factory=list,
        description="Risks that might stop progress or make this account unattractive",
    )
    next_steps: List[NextStepItem] = Field(
        default_factory=list,
        description="Tactical next actions to progress this account",
    )
    suggested_followups: List[str] = Field(
        default_factory=list,
        description="Natural-language follow up questions we can show in the UI",
    )


async def build_persona_strategy(
    persona: PersonaContext,
    fundamentals: CompanyFundamentals,
    news: MarketNewsSummary,
    tech: TechServicesSummary,
) -> PersonaStrategyOutput:
    context_blob = json.dumps(
        {
            "persona": persona.model_dump(),
            "fundamentals": fundamentals.model_dump(),
            "news": news.model_dump(),
            "tech_services": tech.model_dump(),
        },
        indent=2,
    )

    prompt = f"""
You are an expert B2B account strategist.

You will be given a JSON blob containing:
- persona: who the user is and what they care about
- fundamentals: company profile + numbers
- news: latest news summary
- tech_services: products and tech stack

JSON INPUT:
{context_blob}

Your job is to reason carefully and then output a single JSON object that:

1. Explains WHY THIS ACCOUNT MATTERS for this specific persona (why_it_matters).
2. Lists specific, concrete OPPORTUNITIES FOR ME (opportunities_for_me).
3. Lists KEY UNKNOWNS / OPEN QUESTIONS (key_unknowns).
4. Lists major RISKS / BLOCKERS (risks_blockers).
5. Proposes practical NEXT STEPS (next_steps).
6. Suggests follow-up QUESTIONS the user can click in the UI (suggested_followups).

Be realistic and honest. If something is speculative, say so in the description.
Return ONLY JSON matching the PersonaStrategyOutput schema. No extra commentary.
"""

    return await ask_structured_perplexity(prompt, PersonaStrategyOutput)


@function_tool
async def persona_strategy_tool(
    persona: PersonaContext,
    fundamentals_json: str,
    news_json: str,
    tech_json: str,
) -> str:
    fundamentals = CompanyFundamentals.model_validate_json(fundamentals_json)
    news = MarketNewsSummary.model_validate_json(news_json)
    tech = TechServicesSummary.model_validate_json(tech_json)

    result = await build_persona_strategy(
        persona=persona,
        fundamentals=fundamentals,
        news=news,
        tech=tech,
    )
    return result.model_dump_json()
