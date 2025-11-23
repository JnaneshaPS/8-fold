import asyncio
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from perplexity import Perplexity

load_dotenv()

api_key = os.getenv("PERPLEXITY_API_KEY")
if not api_key:
    raise RuntimeError("PERPLEXITY_API_KEY is not set in environment/.env")


async def ask_structured_perplexity(prompt: str, response_model: type[BaseModel]) -> BaseModel:
    def _call():
        client = Perplexity(api_key=api_key)
        completion = client.chat.completions.create(
            model="sonar-pro",
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {"schema": response_model.model_json_schema()},
            },
        )
        return completion.choices[0].message.content

    content = await asyncio.to_thread(_call)
    return response_model.model_validate_json(content)
