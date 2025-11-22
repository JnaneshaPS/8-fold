import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from perplexity import Perplexity
from pydantic import BaseModel, Field
from typing import List, Optional

load_dotenv()


class ProductOrService(BaseModel):
    name: str = Field(description="Name of the product / service")
    category: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    target_users: List[str] = Field(default_factory=list)


class TechComponent(BaseModel):
    area: str = Field(description="Area of the stack")
    technologies: List[str] = Field(default_factory=list)
    confidence_comment: Optional[str] = Field(default=None)


class TechServicesSummary(BaseModel):
    company_name: str = Field(description="Canonical company name")
    products_and_services: List[ProductOrService] = Field(default_factory=list)
    tech_stack: List[TechComponent] = Field(default_factory=list)
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


def fetch_tech_and_services(company_name: str) -> TechServicesSummary:
    ctx = f"Company: {company_name}"
    
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
    
    return ask_structured_perplexity(prompt, TechServicesSummary)


def test_tech_services():
    print("Testing Tech Services Agent...")
    
    test_companies = ["Stripe", "Vercel"]
    
    for company in test_companies:
        print(f"\n  Testing with: {company}")
        try:
            result = fetch_tech_and_services(company)
            print(f"    ✓ Found {len(result.products_and_services)} products/services")
            for i, product in enumerate(result.products_and_services[:3], 1):
                print(f"    {i}. {product.name} ({product.category})")
            
            print(f"\n    ✓ Tech stack ({len(result.tech_stack)} areas):")
            for component in result.tech_stack[:4]:
                techs = ", ".join(component.technologies[:3])
                print(f"       {component.area}: {techs}")
        except Exception as e:
            print(f"    ✗ Failed: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    print("\n✓ Tech Services Agent test PASSED!")


if __name__ == "__main__":
    test_tech_services()

