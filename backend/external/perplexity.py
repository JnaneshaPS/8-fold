from perplexity import Perplexity
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("PERPLEXITY_API_KEY")
if not api_key:
    raise RuntimeError("PERPLEXITY_API_KEY is not set in environment/.env")

_client = Perplexity(api_key=api_key)

def ask_structured_perplexity(prompt: str, response_model: type[BaseModel]) -> BaseModel:
    completion = _client.chat.completions.create(
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
