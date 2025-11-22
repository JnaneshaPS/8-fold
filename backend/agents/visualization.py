from __future__ import annotations

from datetime import date as DateType
from typing import List, Optional

from pydantic import BaseModel, Field
from agents import function_tool

from backend.external.finance_api import fetch_daily_price_series


class StockPoint(BaseModel):
    """Single point on the stock price chart."""

    date: DateType = Field(description="Trading day (UTC)")
    close: float = Field(description="Daily close price in quote currency")


class StockSeries(BaseModel):
    symbol: str = Field(description="Ticker symbol, e.g. 'AAPL'")
    company_name: Optional[str] = Field(
        default=None,
        description="Canonical company name if known",
    )
    currency: Optional[str] = Field(
        default=None,
        description="Quote currency code, e.g. 'USD'",
    )
    points: List[StockPoint] = Field(
        default_factory=list,
        description="Ordered oldest → newest, suitable for plotting",
    )


def get_stock_series(
    symbol: str,
    company_name: Optional[str] = None,
    days: int = 365,
) -> StockSeries:
    """
    Wrap the finance API into a clean Pydantic model for charting.

    The finance client is responsible for talking to AlphaVantage / Finnhub etc.
    """
    raw = fetch_daily_price_series(symbol=symbol, days=days)

    points = [
        StockPoint(
            date=DateType.fromisoformat(p["date"]),
            close=float(p["close"]),
        )
        for p in raw
    ]

    return StockSeries(
        symbol=symbol,
        company_name=company_name,
        currency=None,
        points=points,
    )


@function_tool
def stock_visualization_tool(
    symbol: str,
    company_name: Optional[str] = None,
    days: int = 365,
) -> str:
    """
    Get stock price series for visualization.

    Args:
        symbol: Ticker symbol such as 'AAPL' or 'GOOG'.
        company_name: Optional company name for labeling in UI.
        days: How many days of history to fetch (approx).

    Returns:
        JSON string matching StockSeries.
    """
    series = get_stock_series(
        symbol=symbol,
        company_name=company_name,
        days=days,
    )
    return series.model_dump_json()
