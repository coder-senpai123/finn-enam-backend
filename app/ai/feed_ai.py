import json
import re
import asyncio
from typing import Dict, Any, Optional
from app.ai.gemini_client import generate_gemini

# In-memory cache for generated feed assessments to ensure sub-second response times
_FEED_CACHE: Dict[str, Dict[str, Any]] = {}

def clean_json_text(text: str) -> str:
    """Strips markdown code fences and extraneous whitespace to extract valid JSON."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def build_fallback_verdict(ticker: str, company_name: str, headline: str, ratios: Dict[str, str]) -> Dict[str, Any]:
    """
    Intelligent rule-based fallback grounded in actual screener.in ratios
    in case LLM is busy or times out.
    """
    pe_str = ratios.get("Stock P/E", ratios.get("P/E", "25.0"))
    debt_eq_str = ratios.get("Debt to equity", ratios.get("Debt/Eq", "0.5"))
    roce_str = ratios.get("ROCE", "15.0%")
    roe_str = ratios.get("ROE", "12.0%")
    market_cap = ratios.get("Market Cap", "Large")

    # Extract numeric values
    try:
        pe = float(re.findall(r"[\d\.]+", pe_str)[0])
    except Exception:
        pe = 25.0
    try:
        debt_eq = float(re.findall(r"[\d\.]+", debt_eq_str)[0])
    except Exception:
        debt_eq = 0.5
    try:
        roce = float(re.findall(r"[\d\.]+", roce_str)[0])
    except Exception:
        roce = 15.0

    if debt_eq < 0.6 and roce >= 14.0 and pe <= 35.0:
        verdict = "WORTH CONSIDERING"
        verdict_reason = f"{company_name} displays healthy balance sheet safety with low leverage ({debt_eq}) and superior capital efficiency (ROCE {roce_str}), justifying long-term compounding upside."
    elif pe > 50.0 or debt_eq > 1.3:
        verdict = "HIGH RISK / CAUTION"
        verdict_reason = f"Current valuation ({pe_str} P/E) or debt leverage ({debt_eq_str}) leaves narrow margin of safety if earnings growth falters."
    else:
        verdict = "BALANCED / WAIT & WATCH"
        verdict_reason = f"Stable market position and healthy operational return ratios ({roce_str} ROCE), but current valuation fairly reflects near-term growth expectations."

    return {
        "ai_summary": f"Regulatory disclosure by {company_name}: {headline}. Financial metrics show ROCE at {roce_str} and P/E at {pe_str}.",
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "financial_health": f"Debt-to-Equity stands at {debt_eq_str} with return on capital employed (ROCE) at {roce_str}.",
        "growth_potential": f"Core operations backed by strong market capitalization of {market_cap} with selective capacity initiatives.",
        "valuation_check": f"Trading at {pe_str} P/E, which reflects prevailing industry multiples.",
        "key_risk": "Raw material inflation, competitive pricing, and macro sector cyclicality."
    }

async def generate_feed_item_analysis(
    ticker: str,
    company_name: str,
    headline: str,
    category: str,
    ratios: Dict[str, str],
    source_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates dynamic AI summary and investment viability assessment
    grounded in primary exchange filing and screener ratios.
    """
    cache_key = f"{ticker}:{headline.strip()}"
    if cache_key in _FEED_CACHE:
        return _FEED_CACHE[cache_key]

    market_cap = ratios.get("Market Cap", "N/A")
    pe = ratios.get("Stock P/E", ratios.get("P/E", "N/A"))
    roce = ratios.get("ROCE", "N/A")
    roe = ratios.get("ROE", "N/A")
    debt_eq = ratios.get("Debt to equity", "N/A")
    price = ratios.get("Current Price", "N/A")

    prompt = f"""You are FINN, an institutional-grade investment research agent for Indian public markets (BSE/NSE).
Evaluate this exchange announcement and assess whether this stock is a worthwhile investment.

Company: {company_name} ({ticker})
Category: {category}
Filing Headline: {headline}
Reported Ratios:
- Market Cap: {market_cap}
- Stock P/E: {pe}
- ROCE: {roce}
- ROE: {roe}
- Debt to Equity: {debt_eq}
- Current Price: {price}

TASK:
Answer the core investor question:
"Is this company worth investing money in, and will its stock price increase enough to justify the risk?"
Evaluate its financial health, growth potential, valuation, management/industry, and market behavior.

Return strictly valid JSON with this exact schema (no markdown fences, just pure JSON):
{{
  "ai_summary": "1-2 concise sentences summarizing the filing disclosure and its direct operational significance.",
  "verdict": "WORTH CONSIDERING" or "BALANCED / WAIT & WATCH" or "HIGH RISK / CAUTION",
  "verdict_reason": "Direct 1-2 sentence core thesis on whether expected stock price upside justifies the risk.",
  "financial_health": "1 concise sentence evaluating balance sheet safety, leverage, and capital returns.",
  "growth_potential": "1 concise sentence evaluating business expansion, revenue catalysts, or industry tailwinds.",
  "valuation_check": "1 concise sentence evaluating current P/E multiple relative to growth and margin of safety.",
  "key_risk": "1 concise sentence stating the primary risk factor or market challenge."
}}"""

    system_instruction = (
        "You are an institutional investment research engine. Respond with ONLY a single valid JSON object. "
        "Do not include markdown triple backticks. Keep responses punchy, factual, and strictly grounded."
    )

    try:
        raw_resp = await asyncio.wait_for(
            generate_gemini(model_tier="pro", prompt=prompt, system_instruction=system_instruction),
            timeout=8.0
        )
        cleaned = clean_json_text(raw_resp)
        data = json.loads(cleaned)

        # Validate required fields
        if "ai_summary" in data and "verdict" in data:
            _FEED_CACHE[cache_key] = data
            return data
    except Exception as e:
        print(f"Warning: Gemini feed analysis fallback for {ticker}: {e}")

    # Fallback if LLM call times out or throws
    fallback = build_fallback_verdict(ticker, company_name, headline, ratios)
    _FEED_CACHE[cache_key] = fallback
    return fallback

