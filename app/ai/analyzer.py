from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from app.ai.router import route_model
from app.ai.gemini_client import generate_gemini, MODELS
from app.ingestion.screener import fetch_screener_company_data
from app.ingestion.price_volume import fetch_live_eod

def classify_announcement_category(headline: str) -> Dict[str, Any]:
    h_lower = headline.lower()
    if any(k in h_lower for k in ["financial result", "quarterly result", "half year", "unaudited financial"]):
        return {"category": "results", "materiality": 0.95}
    elif any(k in h_lower for k in ["resignation", "appointment", "cfo", "ceo", "managing director", "director"]):
        return {"category": "management_change", "materiality": 0.92}
    elif any(k in h_lower for k in ["acquisition", "merger", "demerger", "joint venture", "amalgamation"]):
        return {"category": "M&A", "materiality": 0.90}
    elif any(k in h_lower for k in ["capacity expansion", "capex", "new plant", "facility"]):
        return {"category": "capex", "materiality": 0.75}
    elif any(k in h_lower for k in ["rating", "crisil", "care", "icra"]):
        return {"category": "credit_rating", "materiality": 0.55}
    elif any(k in h_lower for k in ["dividend", "record date"]):
        return {"category": "dividend", "materiality": 0.60}
    elif any(k in h_lower for k in ["bonus", "stock split"]):
        return {"category": "bonus_split", "materiality": 0.65}
    elif any(k in h_lower for k in ["concall", "transcript", "earnings call"]):
        return {"category": "earnings_call", "materiality": 0.70}
    elif any(k in h_lower for k in ["press release", "expansion", "partnership", "order win"]):
        return {"category": "press_release", "materiality": 0.50}
    elif any(k in h_lower for k in ["postal ballot", "voting"]):
        return {"category": "postal_ballot", "materiality": 0.20}
    elif any(k in h_lower for k in ["regulation 74", "certificate", "compliance", "esop"]):
        return {"category": "unclassified", "materiality": 0.10}
    return {"category": "press_release", "materiality": 0.40}

MODULE_PROMPTS = {
    "narrative_vs_numbers": """Focus strictly on Narrative vs. Numbers (Guidance vs. Delivered Reality):
1. Extract and analyze what management committed to or guided in recent concalls/transcripts regarding top-line growth, operating margins, capacity capex, and segmental traction.
2. Cross-reference this narrative directly against the actual delivered financial ratios (ROCE, ROE, Debt/Equity, Operating Margins).
3. Identify any specific divergences (e.g. over-promising on growth, margin compression vs guided stability, or capex deferrals).
4. Provide a definitive management credibility verdict (Delivered / Partial Divergence / Aggressive Guidance).""",

    "financial_snapshot": """Provide an institutional-grade financial snapshot:
1. Current market pricing context, 1-day momentum, and volume activity (flag if trading above 20-day average volume).
2. Profitability and return profile: analyze reported ROCE, ROE, and margin realization.
3. Balance sheet risk and capital structure: evaluate Debt-to-Equity and funding stability.
4. Valuation perspective based on current P/E and Book Value.""",

    "bull_bear": """Synthesize an institutional Bull vs. Bear case:
- BULL CASE: 3 concise, high-conviction points grounded strictly in operational numbers, return metrics, order book/expansion announcements, and cash generation.
- BEAR CASE: 3 distinct, specific risk factors grounded in margin sensitivity, valuation multiple pressure, working capital demands, or regulatory disclosures.""",

    "trajectory": """Analyze the multi-year trajectory and operational direction:
1. What is expanding: key business drivers, operational scale, returns on capital employed.
2. What is compressing or facing headwinds: margin pressure, debt/leverage, or extended debtor cycles.
3. Medium-term strategic alignment based on recent exchange filings and capex disclosures.""",

    "balance_sheet": """Conduct a balance sheet, solvency, and working-capital assessment:
1. Analyze Debt-to-Equity and leverage profile.
2. Evaluate capital structure sustainability and interest-servicing safety.
3. Working capital cycle trends and cash tied up in receivables vs inventory.""",

    "cash_quality": """Assess cash quality and earnings conversion:
1. Cash conversion efficiency: do accounting headline profits translate into real operational cash?
2. Free Cash Flow (FCF) generation ability after required capex.
3. Dividend consistency and shareholder payout sustainability.""",

    "guidance": """Analyze management guidance and forecast track record:
1. Specific quantitative guidance given across recent quarters (revenue growth targets, margin bands, capex plans).
2. Historical delivery track record: how accurately does management deliver against stated targets?
3. Tone and conservative vs promotional tendencies in earnings call transcripts.""",

    "business_snapshot": """Provide a comprehensive business overview:
1. Core business activities, segments, and revenue mix.
2. Competitive moat and positioning within its sector in Indian public markets.
3. Recent material corporate actions and strategic announcements."""
}

async def run_analysis(ticker: str, module: str, custom_query: str = None) -> Dict[str, Any]:
    clean_ticker = ticker.upper().strip().replace(".NS", "").replace(".BO", "")
    tier = route_model(module)
    model_name = MODELS.get(tier, "gemini-3.5-flash")

    # 1. Fetch live primary source data from screener.in and Yahoo Finance
    screener_data = await fetch_screener_company_data(clean_ticker)
    
    # Check if company exists
    if not screener_data or "error" in screener_data:
        err_msg = (
            f"Could not locate ticker '{clean_ticker}' on NSE/BSE exchange records or screener.in.\n\n"
            "You might have made a typo or entered an invalid ticker symbol. "
            "Please check the spelling or search using the ticker suggestions (e.g., RELIANCE, TCS, INFY, HDFCBANK, TATAMOTORS, ITC)."
        )
        return {
            "ticker": clean_ticker,
            "module": module,
            "model_used": model_name,
            "title": f"Ticker '{clean_ticker}' Not Found",
            "summary": err_msg,
            "structured_data": {},
            "sources": [],
            "generated_at": datetime.utcnow().isoformat()
        }

    # Fetch live price data
    price_data = fetch_live_eod(clean_ticker)

    company_name = screener_data.get("name", clean_ticker)
    description = screener_data.get("description", "")
    ratios = screener_data.get("ratios", {})
    announcements = screener_data.get("announcements", [])
    concalls = screener_data.get("concalls", [])
    annual_reports = screener_data.get("annual_reports", [])

    sources = [
        f"{company_name} Live Metrics (screener.in)",
        f"{company_name} Price & Volume (Yahoo Finance)"
    ]
    for ann in announcements[:3]:
        sources.append(f"Filing: {ann.get('headline', '')[:55]}")
    for c in concalls[:2]:
        sources.append(f"Concall: {c.get('title', '')[:55]}")
    for ar in annual_reports[:2]:
        sources.append(f"Report: {ar.get('title', '')[:55]}")

    # 2. Build live primary context for the LLM
    primary_context = f"""
PRIMARY DATA CONTEXT FOR {company_name} ({clean_ticker}):
- Company Profile: {description}
- Latest EOD Trading: Close: ₹{price_data.get('close', 'N/A')} | 1-Day Change: {price_data.get('change_pct', 0)}% | Volume: {price_data.get('volume', 0)} shares | 20-Day Avg Volume: {price_data.get('avg_volume_20d', 0)}
- Reported Key Financial Ratios (from audited exchange filings):
{json.dumps(ratios, indent=2)}

- Recent Exchange Announcements & Filings (BSE/NSE):
{json.dumps([a.get('headline') for a in announcements[:6]], indent=2)}

- Earnings Call Transcripts on Record:
{json.dumps([c.get('title') for c in concalls[:4]], indent=2)}

- Audited Annual Reports on Record:
{json.dumps([ar.get('title') for ar in annual_reports[:3]], indent=2)}
"""

    module_instruction = MODULE_PROMPTS.get(module, MODULE_PROMPTS["financial_snapshot"])

    full_prompt = f"""{primary_context}

TASK:
{module_instruction}
"""
    if custom_query:
        full_prompt += f"\nADDITIONAL INVESTOR QUESTION TO ADDRESS: {custom_query}\n"

    system_instruction = (
        "You are FINN, an institutional-grade investment research agent for public-market investors. "
        "Strictly ground all assessments, ratios, figures, and commentary in the PRIMARY DATA CONTEXT provided. "
        "Do not invent facts, do not use boilerplate disclaimers, and do not repeat generic templates. "
        "Provide dense, analytical, objective insights structured for high-conviction decision making."
    )

    # 3. Call Google Gemini Live API
    try:
        ai_response = await generate_gemini(
            model_tier=tier,
            prompt=full_prompt,
            system_instruction=system_instruction
        )
    except Exception as e:
        ai_response = f"LLM Generation Error: {str(e)}"

    title_map = {
        "narrative_vs_numbers": f"{company_name}: Narrative vs. Numbers",
        "financial_snapshot": f"{company_name}: Financial Snapshot & Ratios",
        "bull_bear": f"{company_name}: Bull vs. Bear Case",
        "trajectory": f"{company_name}: Multi-Year Trajectory Analysis",
        "balance_sheet": f"{company_name}: Balance Sheet & Solvency",
        "cash_quality": f"{company_name}: Cash Quality & Earnings Conversion",
        "guidance": f"{company_name}: Guidance Track Record",
        "business_snapshot": f"{company_name}: Business Overview & Segments"
    }

    return {
        "ticker": clean_ticker,
        "module": module,
        "model_used": model_name,
        "title": title_map.get(module, f"{company_name}: {module.replace('_', ' ').title()}"),
        "summary": ai_response,
        "structured_data": ratios,
        "sources": sources[:6],
        "generated_at": datetime.utcnow().isoformat()
    }
