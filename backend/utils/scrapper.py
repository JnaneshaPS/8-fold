from __future__ import annotations

import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup


LINKEDIN_MEDIA_HOST = "media.licdn.com"


class ScraperError(RuntimeError):
    pass


async def fetch_html(
    url: str,
    *,
    timeout: float = 10.0,
) -> str:
    """
    Fetch raw HTML of a public page with a browser-like User-Agent.

    NOTE: LinkedIn may block unauthenticated or automated requests.
    This works best for public profiles and is not guaranteed.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    async with httpx.AsyncClient(
        headers=headers,
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        resp = await client.get(url)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ScraperError(f"Failed to fetch {url}: {e}") from e

        return resp.text


def extract_linkedin_profile_image_src(html: str) -> Optional[str]:
    """
    Parse LinkedIn profile HTML and extract the profile image URL.

    We look for <img> tags used in the top-card profile picture, e.g.:

        <button class="pv-top-card-profile-picture__container ...">
          <img src="https://media.licdn.com/dms/image/v2/.../profile-displayphoto-..." ...>
        </button>

    Heuristics:
      - src contains 'media.licdn.com'
      - img class or surrounding button includes common profile-picture classes
    """
    soup = BeautifulSoup(html, "html.parser")

    candidates: list[str] = []

    for button in soup.find_all("button"):
        class_str = " ".join(button.get("class") or [])
        if "pv-top-card-profile-picture__container" in class_str:
            img = button.find("img")
            if img:
                src = img.get("src")
                if src and LINKEDIN_MEDIA_HOST in src:
                    candidates.append(src)

    if not candidates:
        for img in soup.find_all("img"):
            src = img.get("src")
            if not src or LINKEDIN_MEDIA_HOST not in src:
                continue

            classes = " ".join(img.get("class") or [])
            alt = img.get("alt", "")
            title = img.get("title", "")

            if any(
                hint in classes
                for hint in [
                    "pv-top-card-profile-picture__image",
                    "EntityPhoto-circle",
                    "profile-displayphoto",
                    "evi-image",
                ]
            ):
                candidates.append(src)
                continue

            if "profile-displayphoto" in src or "displayphoto" in src:
                candidates.append(src)
                continue

            if (alt and len(alt) > 2) or (title and len(title) > 2):
                if "profile" in classes.lower() or "photo" in classes.lower():
                    candidates.append(src)

    return candidates[0] if candidates else None


async def get_linkedin_profile_image_url(
    profile_url: str,
    *,
    timeout: float = 10.0,
) -> Optional[str]:
    """
    High-level helper:

      LinkedIn profile URL -> profile image URL (if discoverable).

    Returns:
        Full image URL string or None if not found.
    """
    html = await fetch_html(profile_url, timeout=timeout)
    return extract_linkedin_profile_image_src(html)
