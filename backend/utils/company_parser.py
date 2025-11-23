from __future__ import annotations

import os
from typing import List

from openai import OpenAI


class _CompanyExtractor:
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for company extraction.")
        self.client = OpenAI(api_key=api_key)
        self.schema = {
            "name": "CompanyExtraction",
            "schema": {
                "type": "object",
                "properties": {
                    "companies": {
                        "type": "array",
                        "items": {"type": "string"},
                    }
                },
                "required": ["companies"],
                "additionalProperties": False,
            },
            "strict": True,
        }

    def extract(self, text: str, max_companies: int = 2) -> List[str]:
        if not text.strip():
            return []
        prompt = (
            "Identify company names mentioned in the user's text. "
            "Return only pure company names without extra words.\n\n"
            f"Text: {text}\n"
            f"Limit to {max_companies} companies ordered as they appear."
        )
        try:
            response = self.client.responses.create(
                model="gpt-4o-mini",
                input=prompt,
                response_format={"type": "json_schema", "json_schema": self.schema},
            )
            content = response.output[0].content[0].text
        except Exception:
            return []

        try:
            import json

            data = json.loads(content)
            companies = [
                name.strip()
                for name in data.get("companies", [])[:max_companies]
                if name.strip()
            ]
            return companies
        except Exception:
            return []


_extractor: _CompanyExtractor | None = None


def extract_companies(text: str, max_companies: int = 2) -> List[str]:
    global _extractor
    if _extractor is None:
        try:
            _extractor = _CompanyExtractor()
        except Exception:
            return []
    return _extractor.extract(text, max_companies=max_companies)

