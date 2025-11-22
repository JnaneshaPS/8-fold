import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from datetime import date as DateType
from pydantic import BaseModel, Field
from typing import List, Optional
import httpx

load_dotenv()


class StockPoint(BaseModel):
    date: DateType = Field(description="Trading day (UTC)")
    close: float = Field(description="Daily close price in quote currency")


class StockSeries(BaseModel):
    symbol: str = Field(description="Ticker symbol, e.g. 'AAPL'")
    company_name: Optional[str] = Field(default=None)
    currency: Optional[str] = Field(default=None)
    points: List[StockPoint] = Field(default_factory=list)


async def fetch_daily_price_series(symbol: str, days: int = 365):
    api_key = os.getenv("ALPHAVANTAGE_API_KEY")
    if not api_key:
        raise RuntimeError("ALPHAVANTAGE_API_KEY not set")
    
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "apikey": api_key,
        "outputsize": "compact",
    }
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            "https://www.alphavantage.co/query",
            params=params
        )
        resp.raise_for_status()
        data = resp.json()
    
    if "Error Message" in data:
        raise RuntimeError(f"API Error: {data['Error Message']}")
    if "Note" in data:
        raise RuntimeError(f"Rate limit: {data['Note']}")
    if "Information" in data:
        raise RuntimeError(f"Info: {data['Information']}")
    
    time_series_key = next(
        (k for k in data.keys() if "Time Series" in k),
        None
    )
    
    if not time_series_key:
        raise RuntimeError("Could not find time series in response")
    
    series = data[time_series_key]
    points = []
    
    for date_str, ohlc in series.items():
        close_str = ohlc.get("4. close")
        if close_str:
            points.append({"date": date_str, "close": float(close_str)})
    
    points.sort(key=lambda x: x["date"])
    
    if days and days > 0:
        points = points[-days:]
    
    return points


def get_stock_series(symbol: str, company_name: Optional[str] = None, days: int = 365):
    raw = asyncio.run(fetch_daily_price_series(symbol=symbol, days=days))
    
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
        currency="USD",
        points=points,
    )


def test_visualization():
    print("Testing Visualization Agent...")
    
    test_symbols = [
        ("AAPL", "Apple Inc."),
        ("MSFT", "Microsoft Corporation"),
    ]
    
    for symbol, company in test_symbols:
        print(f"\n  Testing with: {symbol} ({company})")
        try:
            series = get_stock_series(
                symbol=symbol,
                company_name=company,
                days=90
            )
            
            print(f"    ✓ Symbol: {series.symbol}")
            print(f"    ✓ Company: {series.company_name}")
            print(f"    ✓ Data points: {len(series.points)}")
            print(f"    ✓ Date range: {series.points[0].date} to {series.points[-1].date}")
            print(f"    ✓ Latest close: ${series.points[-1].close:.2f}")
            
            price_change = series.points[-1].close - series.points[0].close
            pct_change = (price_change / series.points[0].close) * 100
            print(f"    ✓ 90-day change: ${price_change:.2f} ({pct_change:+.2f}%)")
            
        except Exception as e:
            print(f"    ✗ Failed: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    print("\n✓ Visualization Agent test PASSED!")


if __name__ == "__main__":
    test_visualization()

