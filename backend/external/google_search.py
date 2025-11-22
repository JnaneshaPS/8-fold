from __future__ import annotations

import os
from typing import Any, Iterable

import httpx

GOOGLE_SEARCH_API_KEY = "GOOGLE_SEARCH_API_KEY"
GOOGLE_SEARCH_CX = "GOOGLE_SEARCH_CX"

GOOGLE_SEARCH_ENDPOINT = "https://www.googleapis.com/customsearch/v1"


class GoogleSearchError(RuntimeError):
    pass


def _get_base_params() -> dict[str, str]:
    api_key = os.getenv(GOOGLE_SEARCH_API_KEY)
    cx = os.getenv(GOOGLE_SEARCH_CX)
    if not api_key or not cx:
        raise GoogleSearchError(
            f"{GOOGLE_SEARCH_API_KEY} and {GOOGLE_SEARCH_CX} must be set in environment/.env"
        )
    return {"key": api_key, "cx": cx}


async def google_search(
    query: str,
    *,
    num: int = 5,
    link_site: str | None = None,
    site_search: str | None = None,
    exclude_terms: Iterable[str] | None = None,
    timeout: float = 10.0,
) -> list[str]:
    """
    Basic Google Custom Search JSON API wrapper.

    Returns a list of result URLs.
    """
    params: dict[str, Any] = _get_base_params()
    params["q"] = query
    params["num"] = max(1, min(num, 10))

    if link_site:
        params["linkSite"] = link_site
    if site_search:
        params["siteSearch"] = site_search
    if exclude_terms:
        params["excludeTerms"] = " ".join(exclude_terms)

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(GOOGLE_SEARCH_ENDPOINT, params=params)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise GoogleSearchError(f"Google search failed: {e}") from e

        data = resp.json()
        items = data.get("items", []) or []
        return [item.get("link", "") for item in items if item.get("link")]
