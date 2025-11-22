from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field
from agents import function_tool

from backend.external.perplexity import ask_structured_perplexity
from backend.utils.scrapper import get_linkedin_profile_image_url


class Leader(BaseModel):
    """Single executive / key stakeholder at the target company."""

    name: str = Field(description="Full name of the person")
    title: str = Field(description="Current role/title at the company")
    linkedin_url: Optional[str] = Field(
        default=None,
        description="LinkedIn profile URL if available",
    )
    image_url: Optional[str] = Field(
        default=None,
        description=(
            "Profile image URL derived from LinkedIn HTML. "
            "This is not filled by the LLM; we enrich it via scraping."
        ),
    )
    location: Optional[str] = Field(
        default=None,
        description="Location if known, e.g. 'Bangalore, India'",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Short note on why they matter for the account (e.g. 'Head of Security, decision maker')",
    )


class LeadershipSummary(BaseModel):
    company_name: str = Field(description="Canonical company name")
    leaders: List[Leader] = Field(
        default_factory=list,
        description="Top 3–7 relevant leaders for this account",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Any overall notes or warnings about leadership",
    )


def fetch_leadership(
    company_name: str,
    website: Optional[str] = None,
) -> LeadershipSummary:
    """
    Use Perplexity to find the most relevant leaders for sales/account planning.
    (This step does NOT yet populate image_url.)
    """

    ctx = f"Company: {company_name}"
    if website:
        ctx += f"\nWebsite: {website}"

    prompt = f"""
You are identifying key people for an account plan.

Given:

{ctx}

1. Focus on executive and senior leaders relevant to sales / partnerships /
   security / IT decisions (e.g. CEO, CTO, CISO, VP Engineering, VP Security).
2. Whenever possible, include their LinkedIn profile URL.
3. Do NOT fabricate people. If uncertain, leave them out instead of guessing.

Return ONLY a JSON object matching the LeadershipSummary schema. No extra text.
"""

    return ask_structured_perplexity(prompt, LeadershipSummary)


async def enrich_leadership_with_images(
    summary: LeadershipSummary,
    *,
    timeout: float = 10.0,
    max_leaders: int = 3,
) -> LeadershipSummary:
    """
    Given a LeadershipSummary (with linkedin_url fields), fetch LinkedIn HTML
    and fill image_url for the first few leaders that have a LinkedIn URL.

    This is an async helper that you should call from your orchestrator.
    """

    # Work on a copy so we don't mutate original unintendedly
    updated = summary.model_copy(deep=True)

    # Only try for first N leaders to avoid hammering LinkedIn
    for leader in updated.leaders[:max_leaders]:
        if not leader.linkedin_url:
            continue

        try:
            img = await get_linkedin_profile_image_url(
                leader.linkedin_url,
                timeout=timeout,
            )
        except Exception:
            img = None

        leader.image_url = img

    return updated


@function_tool
def leadership_tool(
    company_name: str,
    website: Optional[str] = None,
) -> str:
    """
    Tool wrapper for the LLM / orchestrator.

    NOTE: This tool only calls Perplexity and does NOT perform HTML scraping,
    so image_url will generally be null. To enrich image_url, call
    `enrich_leadership_with_images` from Python after this tool returns.

    Args:
        company_name: Name of the company.
        website: Optional website URL for disambiguation.

    Returns:
        JSON string matching LeadershipSummary.
    """
    result = fetch_leadership(company_name=company_name, website=website)
    return result.model_dump_json()
