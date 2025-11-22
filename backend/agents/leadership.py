from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field
from agents import function_tool

from backend.external.perplexity import ask_structured_perplexity


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




@function_tool
def leadership_tool(
    company_name: str,
    website: Optional[str] = None,
) -> str:
    """
    Fetch leadership information for a company.

    Args:
        company_name: Name of the company.
        website: Optional website URL for disambiguation.

    Returns:
        JSON string matching LeadershipSummary.
    """
    result = fetch_leadership(company_name=company_name, website=website)
    return result.model_dump_json()
