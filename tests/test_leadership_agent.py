import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from perplexity import Perplexity
from pydantic import BaseModel, Field
from typing import List, Optional

load_dotenv()


class Leader(BaseModel):
    name: str = Field(description="Full name of the person")
    title: str = Field(description="Current role/title at the company")
    linkedin_url: Optional[str] = Field(default=None)
    image_url: Optional[str] = Field(default=None)
    location: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)


class LeadershipSummary(BaseModel):
    company_name: str = Field(description="Canonical company name")
    leaders: List[Leader] = Field(default_factory=list)
    notes: Optional[str] = Field(default=None)


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


def fetch_leadership(company_name: str) -> LeadershipSummary:
    ctx = f"Company: {company_name}"
    
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


def test_leadership():
    print("Testing Leadership Agent...")
    
    test_companies = ["Stripe", "Razorpay"]
    
    for company in test_companies:
        print(f"\n  Testing with: {company}")
        try:
            result = fetch_leadership(company)
            print(f"    ✓ Found {len(result.leaders)} leaders")
            for i, leader in enumerate(result.leaders[:3], 1):
                print(f"    {i}. {leader.name} - {leader.title}")
                if leader.linkedin_url:
                    print(f"       LinkedIn: {leader.linkedin_url}")
        except Exception as e:
            print(f"    ✗ Failed: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    print("\n✓ Leadership Agent test PASSED!")


if __name__ == "__main__":
    test_leadership()

