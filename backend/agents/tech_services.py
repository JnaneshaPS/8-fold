from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field
from agents import function_tool

from backend.external.perplexity import ask_structured_perplexity


class ProductOrService(BaseModel):
    """Core offerings that matter to our persona."""

    name: str = Field(description="Name of the product / service")
    category: Optional[str] = Field(
        default=None,
        description="Short category label, e.g. 'cloud database', 'HR SaaS'",
    )
    description: Optional[str] = Field(
        default=None,
        description="1–2 sentence explanation of what this offering does",
    )
    target_users: List[str] = Field(
        default_factory=list,
        description="Roles / teams that typically use this offering",
    )


class TechComponent(BaseModel):
    """High-level tech stack components (no guessing deep internals)."""

    area: str = Field(
        description="Area of the stack, e.g. 'cloud provider', 'database', 'frontend'",
    )
    technologies: List[str] = Field(
        default_factory=list,
        description="Technologies that appear to be in use, e.g. 'AWS', 'PostgreSQL'",
    )
    confidence_comment: Optional[str] = Field(
        default=None,
        description="Short note indicating how confident we are in this tech inference",
    )


class TechServicesSummary(BaseModel):
    company_name: str = Field(description="Canonical company name")
    products_and_services: List[ProductOrService] = Field(
        default_factory=list,
        description="Short list of core offerings",
    )
    tech_stack: List[TechComponent] = Field(
        default_factory=list,
        description="Simplified view of tech stack, focused on what matters to our persona",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Any relevant notes, e.g. 'heavily multi-cloud', 'on-premise focus'",
    )


async def fetch_tech_and_services(
    company_name: str,
    website: Optional[str] = None,
) -> TechServicesSummary:
    ctx = f"Company: {company_name}"
    if website:
        ctx += f"\nWebsite: {website}"

    prompt = f"""
You are preparing the 'Services / products' and 'Tech stack' sections
for a B2B account plan.

Given:

{ctx}

1. Identify the main products/services that are most relevant to a B2B conversation.
2. Identify the visible tech stack only from reliable public signals:
   docs, careers pages, engineering blogs, case studies, etc.
3. Do NOT guess deep internal architecture. Keep it high-level and honest.

Return ONLY a JSON object that matches the TechServicesSummary schema.
"""

    return await ask_structured_perplexity(prompt, TechServicesSummary)


@function_tool
async def tech_services_tool(
    company_name: str,
    website: Optional[str] = None,
) -> str:
    result = await fetch_tech_and_services(
        company_name=company_name,
        website=website,
    )
    return result.model_dump_json()
