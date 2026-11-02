import asyncio
from app.api.portfolio import get_live_portfolio
from app.ai.analyzer import run_analysis

async def test():
    print("--- 1. Testing Live yfinance Integration ---")
    p = await get_live_portfolio()
    for s in p[:4]:
        print(f"[{s['ticker']}] Price: INR {s['price']} | Change: {s['change_pct']}% | Volume: {s['volume']}")

    print("\n--- 2. Testing Live screener.in + Gemini Analysis ---")
    res = await run_analysis("INFY", "financial_snapshot")
    print("Title:", res["title"])
    print("Model:", res["model_used"])
    print("Primary Sources Verified:")
    for src in res["sources"][:3]:
        print("  -", src)
    print("\nAnalysis Summary:\n", res["summary"][:350])

if __name__ == "__main__":
    asyncio.run(test())

