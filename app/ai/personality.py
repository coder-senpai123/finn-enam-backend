import json
import re
from typing import Dict, Any, List
from app.ai.gemini_client import generate_gemini

def clean_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def build_fallback_personality(age: int, investor_type: str, portfolio_stocks: List[str]) -> Dict[str, Any]:
    inv = investor_type.lower()
    stocks_str = ", ".join(portfolio_stocks[:4]) if portfolio_stocks else "large-cap Indian leaders"

    if "long" in inv or "compound" in inv:
        return {
            "archetype": "The Disciplined Compounder",
            "tagline": "Patient capital focused on balance sheet safety and return on capital moats.",
            "description": f"At {age} years of age, you approach Indian equities with a multi-year horizon, prioritizing businesses like {stocks_str} with consistent ROCE/ROE (>15%), prudent leverage, and enduring competitive moats.",
            "key_traits": ["Balance Sheet Solvency", "Cash Quality & Free Cash Flow", "Low Turnover Compounding"],
            "feed_focus": "Annual reports, capital expenditure disclosures, and long-term earnings durability.",
            "risk_profile": "Moderate Conservative",
            "priority_categories": ["results", "capex", "dividend", "balance_sheet"]
        }
    elif "short" in inv or "risk" in inv:
        return {
            "archetype": "The Tactical Momentum Hunter",
            "tagline": "Agile participant seeking asymmetric risk-reward on breakout catalysts and volume shifts.",
            "description": f"At {age} years of age, you seek high-beta alpha in dynamic stocks like {stocks_str}, prioritizing immediate price catalysts, institutional volume spikes, and breaking material filings.",
            "key_traits": ["Catalyst Sensitivity", "Volume Breakout Tracking", "High Risk-Reward Asymmetry"],
            "feed_focus": "Breaking exchange disclosures, volume spikes > 2x average, and earnings surprises.",
            "risk_profile": "High Risk / Aggressive",
            "priority_categories": ["M&A", "management_change", "results", "press_release"]
        }
    else:
        return {
            "archetype": "The Strategic Growth Allocator",
            "tagline": "Balanced wealth builder evaluating operational trajectory against fair valuations.",
            "description": f"At {age} years of age, you maintain a balanced portfolio anchored by {stocks_str}, analyzing quarterly revenue/margin trends and PEG multiples to capture steady Indian market growth.",
            "key_traits": ["Quarterly Momentum", "Fair Valuation Multiple", "Segmental Growth"],
            "feed_focus": "Quarterly financial results, management concalls, and strategic expansion filings.",
            "risk_profile": "Moderate",
            "priority_categories": ["results", "earnings_call", "capex", "M&A"]
        }

async def generate_investor_personality(
    age: int,
    investor_type: str,
    portfolio_stocks: List[str]
) -> Dict[str, Any]:
    """
    Synthesizes a tailored Indian public market investor personality profile
    using Gemini LLM grounded in the user's age, trading profile, and chosen portfolio.
    """
    stocks_str = ", ".join(portfolio_stocks) if portfolio_stocks else "Diversified NSE/BSE stocks"

    prompt = f"""You are FINN, an institutional-grade investment profiling engine for Indian equity investors.
Generate a distinctive, institutional Investor Personality Profile based on these investor attributes:

- Age: {age} (Legally verified adult trading Indian markets under SEBI guidelines)
- Self-declared Investment Style: {investor_type} (Options: Long-Term Investor / Regular Investor / Short-Term Risk-Taker)
- Seed Portfolio / Watchlist: {stocks_str}

TASK:
Craft a tailored investor persona answering how this specific investor should filter information, what behavioral traps they must avoid, and what filing triggers they care most about.

Return strictly valid JSON with this exact schema (no markdown formatting, no code fences):
{{
  "archetype": "Title (e.g. 'The Disciplined Compounder' or 'The Tactical Momentum Alpha' or 'The Pragmatic Growth Allocator')",
  "tagline": "1-sentence memorable motto summarizing their approach to Indian equities.",
  "description": "2-3 dense sentences explaining their analytical strengths, risk tolerance, and decision-making framework.",
  "key_traits": ["Trait 1", "Trait 2", "Trait 3"],
  "feed_focus": "1-2 sentences on what exchange filings (e.g. capex, results, M&A, volume spikes) FINN will highlight for them.",
  "risk_profile": "Conservative" or "Moderate" or "Aggressive",
  "priority_categories": ["results", "capex", "M&A", "dividend", "management_change"]
}}"""

    system_instruction = (
        "You are an institutional investment psychologist and portfolio architect. "
        "Respond with ONLY a single valid JSON object."
    )

    try:
        raw = await generate_gemini(model_tier="pro", prompt=prompt, system_instruction=system_instruction)
        cleaned = clean_json(raw)
        data = json.loads(cleaned)
        if "archetype" in data and "description" in data:
            return data
    except Exception as e:
        print(f"Personality generation fallback: {e}")

    return build_fallback_personality(age, investor_type, portfolio_stocks)

