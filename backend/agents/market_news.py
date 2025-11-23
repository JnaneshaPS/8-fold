from __future__ import annotations

from typing import List, Optional, Literal

from pydantic import BaseModel, Field
from agents import function_tool

from backend.external.perplexity import ask_structured_perplexity
from backend.observability import render_prompt


class NewsItem(BaseModel):
    """Single news item we might show in the 'Latest news' section."""

    title: str = Field(description="Headline/title of the article")
    summary: str = Field(
        description="2–4 sentence summary of what this article says",
    )
    url: str = Field(description="Link to the original article/blog/press release")
    published_at: Optional[str] = Field(
        default=None,
        description="Publication date as ISO string if available",
    )
    sentiment: Optional[Literal["positive", "negative", "neutral", "mixed"]] = Field(
        default=None,
        description="Sentiment of the news for the company",
    )
    topics: List[str] = Field(
        default_factory=list,
        description="Short topic tags, e.g. ['product launch', 'security incident']",
    )


class MarketNewsSummary(BaseModel):
    company_name: str = Field(description="Canonical company name")
    overall_sentiment: Optional[Literal["positive", "negative", "neutral", "mixed"]] = (
        Field(
            default=None,
            description="Overall sentiment across the listed news items",
        )
    )
    key_themes: List[str] = Field(
        default_factory=list,
        description="Key themes / storylines from the recent news",
    )
    items: List[NewsItem] = Field(
        default_factory=list,
        description="Chronologically recent, de-duplicated news items",
    )


async def fetch_market_news(
    company_name: str,
    website: Optional[str] = None,
    max_items: int = 6,
) -> MarketNewsSummary:
    ctx = f"Company: {company_name}"
    if website:
        ctx += f"\nWebsite: {website}"

    prompt = render_prompt(
        "market_news_agent_prompt",
        variables={
            "company_context": ctx,
            "max_items": str(max_items),
        }
    )

    summary = await ask_structured_perplexity(prompt, MarketNewsSummary)

    if len(summary.items) > max_items:
        summary.items = summary.items[:max_items]

    return summary


@function_tool
async def market_news_tool(
    company_name: str,
    website: Optional[str] = None,
    max_items: int = 6,
) -> str:
    result = await fetch_market_news(
        company_name=company_name,
        website=website,
        max_items=max_items,
    )
    return result.model_dump_json()
