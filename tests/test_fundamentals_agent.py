import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from perplexity import Perplexity
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

load_dotenv()


class CompanyProfile(BaseModel):
    company_name: str = Field(description="Canonical company name")
    website: Optional[str] = Field(default=None, description="Primary website URL if known")
    headquarters: Optional[str] = Field(default=None, description="City + country of HQ")
    industry: Optional[str] = Field(default=None, description="High-level industry")
    public_status: Literal["public", "private", "subsidiary", "unknown"] = Field(default="unknown")
    stock_ticker: Optional[str] = Field(default=None)
    employee_count_bucket: Optional[str] = Field(default=None)
    primary_regions: List[str] = Field(default_factory=list)
    short_description: Optional[str] = Field(default=None)


class KeyNumbers(BaseModel):
    latest_revenue_usd_bil: Optional[float] = Field(default=None)
    yoy_revenue_growth_pct: Optional[float] = Field(default=None)
    employee_count_estimate: Optional[int] = Field(default=None)
    founded_year: Optional[int] = Field(default=None)


class CompanyFundamentals(BaseModel):
    profile: CompanyProfile
    key_numbers: KeyNumbers
    business_model: Optional[str] = Field(default=None)
    ideal_customer_profile: Optional[str] = Field(default=None)
    key_segments: List[str] = Field(default_factory=list)
    notable_notes: List[str] = Field(default_factory=list)


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


def fetch_company_fundamentals(company_name: str) -> CompanyFundamentals:
    ctx = f"Company name: {company_name}"
    
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


def test_fundamentals():
    print("Testing Fundamentals Agent...")
    
    test_companies = ["Stripe", "Razorpay"]
    
    for company in test_companies:
        print(f"\n  Testing with: {company}")
        try:
            result = fetch_company_fundamentals(company)
            print(f"    ✓ Company: {result.profile.company_name}")
            print(f"    ✓ HQ: {result.profile.headquarters}")
            print(f"    ✓ Industry: {result.profile.industry}")
            print(f"    ✓ Status: {result.profile.public_status}")
            print(f"    ✓ Founded: {result.key_numbers.founded_year}")
            print(f"    ✓ Business Model: {result.business_model[:80] if result.business_model else 'N/A'}...")
        except Exception as e:
            print(f"    ✗ Failed: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    print("\n✓ Fundamentals Agent test PASSED!")


if __name__ == "__main__":
    test_fundamentals()

