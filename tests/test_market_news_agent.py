import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from perplexity import Perplexity
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

load_dotenv()


class NewsItem(BaseModel):
    title: str = Field(description="Headline/title of the article")
    summary: str = Field(description="2–4 sentence summary")
    url: str = Field(description="Link to the original article")
    published_at: Optional[str] = Field(default=None)
    sentiment: Optional[Literal["positive", "negative", "neutral", "mixed"]] = Field(default=None)
    topics: List[str] = Field(default_factory=list)


class MarketNewsSummary(BaseModel):
    company_name: str = Field(description="Canonical company name")
    overall_sentiment: Optional[Literal["positive", "negative", "neutral", "mixed"]] = Field(default=None)
    key_themes: List[str] = Field(default_factory=list)
    items: List[NewsItem] = Field(default_factory=list)


def ask_structured_perplexity(prompt: str, response_model: type[BaseModel]) -> BaseModel:
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        raise RuntimeError("PERPLEXITY_API_KEY is not set")
    
    client = Perplexity(api_key=api_key)
    
    completion = client.chat.completions.create(
        model="sonar-pro",
        messages=[{"role": "user", "content": prompt}],
        response_format={
            "type": "json_schema",
            "json_schema": {"schema": response_model.model_json_schema()},
        },
    )
    return response_model.model_validate_json(
        completion.choices[0].message.content
    )


def fetch_market_news(company_name: str, max_items: int = 6) -> MarketNewsSummary:
    ctx = f"Company: {company_name}"
    
    prompt = f"""
You are generating a 'Latest news' section for an account plan.

Given:

{ctx}

1. Look at the most relevant, recent news items (last 6–12 months if possible).
2. Prefer news that matters to a sales / partnerships / security conversation:
   product launches, funding, big customers, security incidents, layoffs, pivots, etc.
3. Avoid trivial news or SEO spam.

Return ONLY a JSON object conforming to the MarketNewsSummary schema.
Make sure you include at most {max_items} high-signal items.
"""
    
    return ask_structured_perplexity(prompt, MarketNewsSummary)


def test_market_news():
    print("Testing Market News Agent...")
    
    test_companies = ["Stripe", "OpenAI"]
    
    for company in test_companies:
        print(f"\n  Testing with: {company}")
        try:
            result = fetch_market_news(company, max_items=4)
            print(f"    ✓ Found {len(result.items)} news items")
            print(f"    ✓ Overall sentiment: {result.overall_sentiment}")
            print(f"    ✓ Key themes: {', '.join(result.key_themes[:3])}")
            print(f"\n    Recent news:")
            for i, item in enumerate(result.items[:3], 1):
                print(f"    {i}. {item.title[:60]}...")
                print(f"       Sentiment: {item.sentiment}")
        except Exception as e:
            print(f"    ✗ Failed: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    print("\n✓ Market News Agent test PASSED!")


if __name__ == "__main__":
    test_market_news()

