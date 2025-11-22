import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from perplexity import Perplexity
from pydantic import BaseModel, Field

load_dotenv()


class SimpleTest(BaseModel):
    company_name: str = Field(description="Name of a tech company")
    headquarters: str = Field(description="Location of headquarters")
    founded_year: int = Field(description="Year founded")


def ask_structured_perplexity(prompt: str, response_model: type[BaseModel]) -> BaseModel:
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        raise RuntimeError("PERPLEXITY_API_KEY is not set in environment/.env")
    
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


def test_perplexity():
    print("Testing Perplexity API with structured outputs...")
    
    prompt = """
    Tell me about Stripe (the payment company).
    Provide: company name, headquarters location, and year founded.
    """
    
    try:
        result = ask_structured_perplexity(prompt, SimpleTest)
        print(f"✓ Success!")
        print(f"  Company: {result.company_name}")
        print(f"  HQ: {result.headquarters}")
        print(f"  Founded: {result.founded_year}")
        print(f"\nFull result: {result.model_dump_json(indent=2)}")
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    test_perplexity()

