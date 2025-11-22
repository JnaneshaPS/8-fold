import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
import httpx

load_dotenv()


async def test_finance_api():
    print("Testing Alpha Vantage Finance API...")
    
    api_key = os.getenv("ALPHAVANTAGE_API_KEY")
    if not api_key:
        print("✗ Failed: ALPHAVANTAGE_API_KEY not set in environment")
        return
    
    try:
        print(f"  Testing with symbol: AAPL")
        
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": "AAPL",
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
            print(f"  ✗ API Error: {data['Error Message']}")
            return
        
        if "Note" in data:
            print(f"  ⚠ Rate limit: {data['Note']}")
            print("  API key is valid but rate limited (expected for free tier)")
            return
        
        time_series_key = next(
            (k for k in data.keys() if "Time Series" in k),
            None
        )
        
        if time_series_key:
            series = data[time_series_key]
            dates = list(series.keys())[:5]
            print(f"  ✓ Got {len(series)} data points")
            print(f"  ✓ Latest dates: {dates}")
            print("\n✓ Finance API test PASSED!")
        else:
            print(f"  ⚠ Unexpected response structure: {list(data.keys())}")
            if "Information" in data:
                print(f"  ℹ Info: {data['Information']}")
            print(f"  Full response: {data}")
        
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(test_finance_api())

