import asyncio
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.ingestion.price_volume import fetch_live_eod
from app.core.mongodb import find_user_by_email, upsert_user

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

# Default fallback tickers only for unauthenticated / guest demo
DEFAULT_GUEST_TICKERS = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "TATAMOTORS"]

# Global cache for company names and sectors
STOCK_METADATA: Dict[str, Dict[str, str]] = {
    "RELIANCE": {"name": "Reliance Industries Ltd", "sector": "Energy & Retail", "market_cap_category": "Large"},
    "TCS": {"name": "Tata Consultancy Services", "sector": "Information Technology", "market_cap_category": "Large"},
    "HDFCBANK": {"name": "HDFC Bank Ltd", "sector": "Banking & Finance", "market_cap_category": "Large"},
    "INFY": {"name": "Infosys Ltd", "sector": "Information Technology", "market_cap_category": "Large"},
    "ICICIBANK": {"name": "ICICI Bank Ltd", "sector": "Banking & Finance", "market_cap_category": "Large"},
    "TATAMOTORS": {"name": "Tata Motors Ltd", "sector": "Automotive", "market_cap_category": "Large"},
    "SUNPHARMA": {"name": "Sun Pharmaceutical Inds", "sector": "Pharma & Healthcare", "market_cap_category": "Large"},
    "ITC": {"name": "ITC Ltd", "sector": "FMCG", "market_cap_category": "Large"},
    "TATASTEEL": {"name": "Tata Steel Ltd", "sector": "Metals & Mining", "market_cap_category": "Mid"},
    "TITAN": {"name": "Titan Company Ltd", "sector": "Consumer Discretionary", "market_cap_category": "Large"},
    "HAL": {"name": "Hindustan Aeronautics Ltd", "sector": "Defence & Aerospace", "market_cap_category": "Mid"},
    "PERSISTENT": {"name": "Persistent Systems Ltd", "sector": "Information Technology", "market_cap_category": "Mid"},
    "ZOMATO": {"name": "Zomato Ltd", "sector": "Consumer Internet", "market_cap_category": "Mid"},
    "KOTAKBANK": {"name": "Kotak Mahindra Bank", "sector": "Banking & Finance", "market_cap_category": "Large"},
    "BAJFINANCE": {"name": "Bajaj Finance Ltd", "sector": "NBFC", "market_cap_category": "Large"},
}

class AddStockRequest(BaseModel):
    ticker: str
    name: str = ""
    sector: str = "Equities"
    email: Optional[str] = None

@router.get("", response_model=List[Dict[str, Any]])
async def get_live_portfolio(email: Optional[str] = Query(None, description="User email to load their specific watchlist")):
    """
    Returns the investor's exact watchlist with live prices and volume from Yahoo Finance.
    If email is provided, loads strictly the companies in that user's MongoDB profile.
    """
    tickers_to_load: List[str] = []

    if email:
        user = await find_user_by_email(email.lower().strip())
        if user and user.get("portfolio_stocks") is not None:
            tickers_to_load = user.get("portfolio_stocks", [])
        else:
            tickers_to_load = DEFAULT_GUEST_TICKERS
    else:
        tickers_to_load = DEFAULT_GUEST_TICKERS

    # Deduplicate while preserving order
    seen = set()
    unique_tickers = [t for t in tickers_to_load if not (t in seen or seen.add(t))]

    portfolio_items = []
    for ticker in unique_tickers:
        clean_ticker = ticker.upper().strip().replace(".NS", "").replace(".BO", "")
        meta = STOCK_METADATA.get(clean_ticker, {
            "name": f"{clean_ticker} Ltd",
            "sector": "Equities",
            "market_cap_category": "Mid"
        })
        live = fetch_live_eod(clean_ticker)
        portfolio_items.append({
            "ticker": clean_ticker,
            "name": meta.get("name") or f"{clean_ticker} Ltd",
            "sector": meta.get("sector") or "Equities",
            "market_cap_category": meta.get("market_cap_category") or ("Large" if live["close"] > 2000 else "Mid"),
            "price": live["close"],
            "change_pct": live["change_pct"],
            "volume": live["volume"],
            "avg_volume_20d": live["avg_volume_20d"],
            "is_volume_spike": live["is_volume_spike"]
        })

    return portfolio_items

@router.post("", response_model=Dict[str, Any])
async def add_stock_to_portfolio(req: AddStockRequest):
    """
    Adds a new stock to the user's personal watchlist in MongoDB.
    """
    clean_ticker = req.ticker.upper().strip().replace(".NS", "").replace(".BO", "")
    
    # Cache metadata
    if clean_ticker not in STOCK_METADATA:
        STOCK_METADATA[clean_ticker] = {
            "name": req.name.strip() or f"{clean_ticker} Ltd",
            "sector": req.sector or "Equities",
            "market_cap_category": "Mid"
        }

    live = fetch_live_eod(clean_ticker)

    if req.email:
        clean_email = req.email.lower().strip()
        user = await find_user_by_email(clean_email)
        if user:
            current_stocks = user.get("portfolio_stocks", [])
            if clean_ticker in current_stocks:
                raise HTTPException(status_code=400, detail=f"Stock {clean_ticker} is already in your watchlist")
            updated_stocks = [clean_ticker] + current_stocks
            await upsert_user(clean_email, {"portfolio_stocks": updated_stocks})
            return {"message": f"Added {clean_ticker} to your watchlist", "stocks": updated_stocks}

    return {"message": f"Added {clean_ticker} to watchlist"}

@router.delete("/{ticker}", response_model=Dict[str, Any])
async def remove_stock_from_portfolio(
    ticker: str,
    email: Optional[str] = Query(None, description="User email to remove stock from their specific watchlist")
):
    """
    Removes a stock from the user's personal watchlist in MongoDB.
    """
    clean_ticker = ticker.upper().strip().replace(".NS", "").replace(".BO", "")

    if email:
        clean_email = email.lower().strip()
        user = await find_user_by_email(clean_email)
        if user:
            current_stocks = user.get("portfolio_stocks", [])
            if clean_ticker not in current_stocks:
                raise HTTPException(status_code=404, detail=f"Stock {clean_ticker} not found in your watchlist")
            updated_stocks = [t for t in current_stocks if t != clean_ticker]
            await upsert_user(clean_email, {"portfolio_stocks": updated_stocks})
            return {"message": f"Removed {clean_ticker} from your watchlist", "stocks": updated_stocks}

    return {"message": f"Removed {clean_ticker} from watchlist"}
