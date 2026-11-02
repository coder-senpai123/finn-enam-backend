import asyncio
import json
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.core.database import get_db
from app.core.mongodb import find_user_by_email
from app.ingestion.screener import fetch_screener_company_data
from app.ai.analyzer import classify_announcement_category
from app.ai.feed_ai import generate_feed_item_analysis

router = APIRouter(prefix="/feed", tags=["feed"])

DEFAULT_TICKERS = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "TATAMOTORS", "ITC", "SUNPHARMA"]

@router.get("", response_model=List[Dict[str, Any]])
async def get_live_feed(
    window_hours: int = Query(24, description="Time window in hours"),
    email: Optional[str] = Query(None, description="User email for profile personalization"),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetches real primary exchange announcements for portfolio stocks via screener.in & BSE links,
    classifies them, scores materiality, dynamically synthesizes AI summaries and an Investment
    Viability Assessment, and personalizes ranking and commentary based on the user's AI Investor Personality.
    """
    user = None
    priority_categories = []
    investor_type = "Regular Investor"
    archetype = "General Investor"

    if email:
        user = await find_user_by_email(email)
        if user:
            personality = user.get("personality", {})
            priority_categories = personality.get("priority_categories", [])
            investor_type = user.get("investor_type", "Regular Investor")
            archetype = personality.get("archetype", "Active Investor")

    # Use user's saved portfolio stocks if available, otherwise DEFAULT_TICKERS
    if user and user.get("portfolio_stocks"):
        active_tickers = user["portfolio_stocks"][:7]
    else:
        active_tickers = DEFAULT_TICKERS[:6]

    # Fetch screener data concurrently
    screener_results = await asyncio.gather(
        *(fetch_screener_company_data(t) for t in active_tickers),
        return_exceptions=True
    )

    feed_items = []
    item_id = 1
    tasks_to_generate = []
    announcement_meta = []

    for idx, ticker in enumerate(active_tickers):
        if idx >= len(screener_results):
            continue
        data = screener_results[idx]
        if isinstance(data, Exception) or not data or "error" in data:
            continue

        company_name = data.get("name", ticker)
        ratios = data.get("ratios", {})
        anns = data.get("announcements", [])

        # Process top 2 real filings per company
        for ann in anns[:2]:
            headline = ann.get("headline", "")
            classification = classify_announcement_category(headline)
            cat = classification["category"]
            materiality = classification["materiality"]

            # Personalize materiality based on user's investment persona
            if cat in priority_categories:
                materiality = min(1.0, materiality + 0.15)

            if "short" in investor_type.lower() and cat in ["M&A", "management_change", "results"]:
                materiality = min(1.0, materiality + 0.2)
            elif "long" in investor_type.lower() and cat in ["dividend", "capex", "balance_sheet"]:
                materiality = min(1.0, materiality + 0.15)

            if materiality >= 0.75:
                priority = "must-see"
            elif materiality >= 0.45:
                priority = "worth-knowing"
            else:
                priority = "routine"

            source_url = ann.get("url")
            filed_at = ann.get("filed_at", datetime.utcnow().strftime("%Y-%m-%d"))

            announcement_meta.append({
                "id": item_id,
                "ticker": ticker,
                "company_name": company_name,
                "headline": headline,
                "category": cat,
                "materiality": materiality,
                "priority": priority,
                "ratios": ratios,
                "source_url": source_url,
                "filed_at": filed_at,
            })
            item_id += 1

            tasks_to_generate.append(
                generate_feed_item_analysis(
                    ticker=ticker,
                    company_name=company_name,
                    headline=headline,
                    category=cat,
                    ratios=ratios,
                    source_url=source_url
                )
            )

    # Concurrently generate AI summaries and viability assessments
    if tasks_to_generate:
        ai_assessments = await asyncio.gather(*tasks_to_generate, return_exceptions=True)
    else:
        ai_assessments = []

    for i, meta in enumerate(announcement_meta):
        assessment = ai_assessments[i] if i < len(ai_assessments) and not isinstance(ai_assessments[i], Exception) else None

        if not assessment:
            assessment = {
                "ai_summary": f"Filing by {meta['company_name']} regarding {meta['headline']}.",
                "verdict": "BALANCED / WAIT & WATCH",
                "verdict_reason": "Stable operational profile, evaluating risk-adjusted upside vs market cycle.",
                "financial_health": "Evaluating leverage and operational capital efficiency.",
                "growth_potential": "Tracking business order flows and segmental margins.",
                "valuation_check": "Trading in line with historical peer multiples.",
                "key_risk": "Broad market cyclicality and input price pressure."
            }

        # Personalized lens commentary
        if "long" in investor_type.lower():
            personalized_lens = f"Tailored for {archetype}: Prioritizing balance sheet safety, ROCE moats, and capital compounding."
        elif "short" in investor_type.lower():
            personalized_lens = f"Tailored for {archetype}: Prioritizing immediate price action catalysts, volume breakouts, and headline momentum."
        else:
            personalized_lens = f"Tailored for {archetype}: Balanced evaluation of quarterly trajectory and margin durability."

        enrichment_payload = {
            "type": "investment_viability",
            "verdict": assessment.get("verdict", "BALANCED / WAIT & WATCH"),
            "verdict_reason": assessment.get("verdict_reason", ""),
            "financial_health": assessment.get("financial_health", ""),
            "growth_potential": assessment.get("growth_potential", ""),
            "valuation_check": assessment.get("valuation_check", ""),
            "key_risk": assessment.get("key_risk", ""),
            "personalized_lens": personalized_lens,
            "ratios": {
                "P/E": meta["ratios"].get("Stock P/E", meta["ratios"].get("P/E", "N/A")),
                "ROCE": meta["ratios"].get("ROCE", "N/A"),
                "ROE": meta["ratios"].get("ROE", "N/A"),
                "Debt/Eq": meta["ratios"].get("Debt to equity", "N/A"),
                "Price": meta["ratios"].get("Current Price", "N/A"),
                "Market Cap": meta["ratios"].get("Market Cap", "N/A")
            },
            "source_url": meta["source_url"],
            "disclaimer": "AI is prone to mistakes; trust your judgement first."
        }

        feed_items.append({
            "announcement": {
                "id": meta["id"],
                "ticker": meta["ticker"],
                "category": meta["category"],
                "headline": meta["headline"],
                "raw_text": meta["headline"],
                "ai_summary": assessment.get("ai_summary", f"Filing by {meta['ticker']} with stock exchanges."),
                "materiality_score": meta["materiality"],
                "enrichment_json": json.dumps(enrichment_payload),
                "source_url": meta["source_url"],
                "filed_at": meta["filed_at"]
            },
            "priority_level": meta["priority"]
        })

    # Sort prioritised: must-see first, then worth-knowing, then routine
    priority_order = {"must-see": 0, "worth-knowing": 1, "routine": 2}
    feed_items.sort(key=lambda x: (priority_order.get(x["priority_level"], 3), -x["announcement"]["materiality_score"]))

    return feed_items
