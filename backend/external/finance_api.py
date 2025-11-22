from __future__ import annotations

import os
from typing import Any, List, Tuple

import httpx

ALPHAVANTAGE_API_KEY_ENV = "ALPHAVANTAGE_API_KEY"
ALPHAVANTAGE_ENDPOINT = "https://www.alphavantage.co/query"


class FinanceAPIError(RuntimeError):
    pass


def _get_alpha_key() -> str:
    """
    Lazy-load the Alpha Vantage API key so import doesn't explode
    if .env isn't ready yet.
    """
    key = os.getenv(ALPHAVANTAGE_API_KEY_ENV)
    if not key:
        raise FinanceAPIError(
            f"{ALPHAVANTAGE_API_KEY_ENV} is not set in environment/.env"
        )
    return key


async def fetch_daily_series(
    symbol: str,
    *,
    function: str = "TIME_SERIES_DAILY_ADJUSTED",
    timeout: float = 10.0,
) -> dict[str, Any]:
    """
    Call Alpha Vantage for daily time series. Returns raw JSON response.
    """
    params = {
        "function": function,
        "symbol": symbol,
        "apikey": _get_alpha_key(),
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(ALPHAVANTAGE_ENDPOINT, params=params)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise FinanceAPIError(f"Alpha Vantage HTTP error: {e}") from e

        data = resp.json()

        if "Error Message" in data:
            raise FinanceAPIError(f"Alpha Vantage error: {data['Error Message']}")
        if "Note" in data:
            # Usually rate limits / quota
            raise FinanceAPIError(f"Alpha Vantage note (likely rate limit): {data['Note']}")

        return data


def extract_daily_closing_prices(
    data: dict[str, Any],
) -> list[Tuple[str, float]]:
    """
    Given Alpha Vantage response, extract [(date, close_price)] sorted ascending.
    """
    time_series_key = next(
        (k for k in data.keys() if "Time Series" in k),
        None,
    )
    if not time_series_key:
        raise FinanceAPIError("Could not find time series key in response")

    series = data[time_series_key]
    rows: list[Tuple[str, float]] = []

    for date_str, ohlc in series.items():
        close_str = (
            ohlc.get("4. close")
            or ohlc.get("5. adjusted close")
            or ohlc.get("4. Close")
        )
        if close_str is None:
            continue
        try:
            close_val = float(close_str)
        except ValueError:
            continue
        rows.append((date_str, close_val))

    # Sort oldest → newest
    rows.sort(key=lambda r: r[0])
    return rows


async def fetch_daily_price_series(
    symbol: str,
    *,
    days: int = 365,
    timeout: float = 10.0,
) -> list[dict[str, Any]]:
    """
    High-level helper for the visualization agent.

    Returns a list of dicts:
        [{"date": "YYYY-MM-DD", "close": 123.45}, ...]

    Only the most recent `days` entries are kept.
    """
    raw = await fetch_daily_series(symbol=symbol, timeout=timeout)
    points = extract_daily_closing_prices(raw)

    if days is not None and days > 0:
        points = points[-days:]

    return [{"date": d, "close": v} for (d, v) in points]
