from __future__ import annotations

from typing import List, Optional, Literal

from pydantic import BaseModel, Field
from agents import function_tool

from backend.external.perplexity import ask_structured_perplexity


class CompanyProfile(BaseModel):
    """Basic identity of the target company."""

    company_name: str = Field(description="Canonical company name")
    website: Optional[str] = Field(
        default=None,
        description="Primary website URL if known",
    )
    headquarters: Optional[str] = Field(
        default=None,
        description="City + country of HQ, e.g. 'San Francisco, USA'",
    )
    industry: Optional[str] = Field(
        default=None,
        description="High-level industry, e.g. 'SaaS', 'Fintech', 'Manufacturing'",
    )
    public_status: Literal["public", "private", "subsidiary", "unknown"] = Field(
        default="unknown",
        description="Whether the company is public, private, or a subsidiary",
    )
    stock_ticker: Optional[str] = Field(
        default=None,
        description="Exchange ticker symbol if publicly traded, e.g. 'NASDAQ:CRM'",
    )
    employee_count_bucket: Optional[str] = Field(
        default=None,
        description="Rough size bucket: '1-50', '51-200', '201-1000', '1000+' etc.",
    )
    primary_regions: List[str] = Field(
        default_factory=list,
        description="Key geographies where the company operates",
    )
    short_description: Optional[str] = Field(
        default=None,
        description="1–3 sentence plain-English description of what the company does",
    )


class KeyNumbers(BaseModel):
    """Lightweight numeric signals used later by strategy agent."""

    latest_revenue_usd_bil: Optional[float] = Field(
        default=None,
        description="Approximate latest annual revenue in billions USD if known",
    )
    yoy_revenue_growth_pct: Optional[float] = Field(
        default=None,
        description="Approximate year-over-year revenue growth percentage if known",
    )
    employee_count_estimate: Optional[int] = Field(
        default=None,
        description="Estimated employee count if a concrete number is available",
    )
    founded_year: Optional[int] = Field(
        default=None,
        description="Year company was founded",
    )


class CompanyFundamentals(BaseModel):
    """Top-level output for the Fundamentals agent."""

    profile: CompanyProfile
    key_numbers: KeyNumbers
    business_model: Optional[str] = Field(
        default=None,
        description="Short explanation of how the company makes money",
    )
    ideal_customer_profile: Optional[str] = Field(
        default=None,
        description="1–2 sentences describing the types of customers they target",
    )
    key_segments: List[str] = Field(
        default_factory=list,
        description="Important customer / market segments, e.g. 'enterprise banks'",
    )
    notable_notes: List[str] = Field(
        default_factory=list,
        description="Bullet points with any important contextual notes",
    )


def fetch_company_fundamentals(
    company_name: str,
    website: Optional[str] = None,
    region_hint: Optional[str] = None,
) -> CompanyFundamentals:
    """
    Call Perplexity with structured outputs to get company fundamentals.
    """

    query_ctx_parts = [f"Company name: {company_name}"]
    if website:
        query_ctx_parts.append(f"Website: {website}")
    if region_hint:
        query_ctx_parts.append(f"Region hint: {region_hint}")

    ctx = "\n".join(query_ctx_parts)

    prompt = f"""
You are a B2B account research assistant generating clean JSON for an account plan.

Given the following company context:

{ctx}

1. Identify the canonical company (avoid mixing multiple companies with similar names).
2. Use only reliable, web-verified information.
3. If you are uncertain about a numeric field, leave it null instead of guessing.

Return ONLY a JSON object that matches the provided schema. Do not add commentary.
"""

    return ask_structured_perplexity(prompt, CompanyFundamentals)


@function_tool
def fundamentals_tool(
    company_name: str,
    website: Optional[str] = None,
    region_hint: Optional[str] = None,
) -> str:
    """
    Fetch structured company fundamentals (profile + key numbers).

    Args:
        company_name: The name of the company to research.
        website: Optional official website URL if known.
        region_hint: Optional region/country hint to disambiguate the company.

    Returns:
        A JSON string matching the CompanyFundamentals schema.
    """
    result = fetch_company_fundamentals(
        company_name=company_name,
        website=website,
        region_hint=region_hint,
    )
    return result.model_dump_json()
