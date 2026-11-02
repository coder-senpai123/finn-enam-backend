import asyncio
import json
from datetime import datetime, timedelta
from app.core.database import async_session_maker, init_db
from app.models.models import Company, PriceHistory, Announcement, AlertTriggered, AlertRule

MOCK_COMPANIES = [
    {"ticker": "RELIANCE", "name": "Reliance Industries Ltd", "sector": "Energy & Retail", "market_cap_category": "Large"},
    {"ticker": "TCS", "name": "Tata Consultancy Services", "sector": "Information Technology", "market_cap_category": "Large"},
    {"ticker": "HDFCBANK", "name": "HDFC Bank Ltd", "sector": "Banking & Finance", "market_cap_category": "Large"},
    {"ticker": "INFY", "name": "Infosys Ltd", "sector": "Information Technology", "market_cap_category": "Large"},
    {"ticker": "ICICIBANK", "name": "ICICI Bank Ltd", "sector": "Banking & Finance", "market_cap_category": "Large"},
    {"ticker": "TATAMOTORS", "name": "Tata Motors Ltd", "sector": "Automotive", "market_cap_category": "Large"},
    {"ticker": "SUNPHARMA", "name": "Sun Pharmaceutical Inds", "sector": "Pharma & Healthcare", "market_cap_category": "Large"},
    {"ticker": "ITC", "name": "ITC Ltd", "sector": "FMCG", "market_cap_category": "Large"},
    {"ticker": "TATASTEEL", "name": "Tata Steel Ltd", "sector": "Metals & Mining", "market_cap_category": "Mid"},
    {"ticker": "ZOMATO", "name": "Zomato Ltd (Eternal)", "sector": "Consumer Internet", "market_cap_category": "Mid"},
    {"ticker": "TITAN", "name": "Titan Company Ltd", "sector": "Consumer Discretionary", "market_cap_category": "Large"},
    {"ticker": "KOTAKBANK", "name": "Kotak Mahindra Bank", "sector": "Banking & Finance", "market_cap_category": "Large"},
    {"ticker": "BAJFINANCE", "name": "Bajaj Finance Ltd", "sector": "NBFC", "market_cap_category": "Large"},
    {"ticker": "HAL", "name": "Hindustan Aeronautics Ltd", "sector": "Defence & Aerospace", "market_cap_category": "Mid"},
    {"ticker": "PERSISTENT", "name": "Persistent Systems Ltd", "sector": "Information Technology", "market_cap_category": "Mid"},
]

MOCK_ANNOUNCEMENTS = [
    {
        "ticker": "INFY",
        "category": "management_change",
        "headline": "Resignation of Chief Financial Officer and appointment of successor",
        "materiality_score": 0.95,
        "ai_summary": "CFO Nilanjan Roy stepped down. Successor Jayesh Sanghrajka appointed effective next month.",
        "enrichment_json": json.dumps({
            "type": "management_change",
            "name": "Jayesh Sanghrajka",
            "role": "Chief Financial Officer",
            "bio": "22+ years at Infosys in treasury, tax and M&A. Previously Deputy CFO and interim leadership."
        }),
        "hours_ago": 2
    },
    {
        "ticker": "TCS",
        "category": "results",
        "headline": "Financial Results for the Quarter and Half Year ended September 30",
        "materiality_score": 0.92,
        "ai_summary": "Q2 revenue up 2.6% QoQ with margin stability at 24.1%. Net profit reported at ₹11,909 Cr.",
        "enrichment_json": json.dumps({
            "type": "results",
            "quarter": "Q2 FY27",
            "metrics": [
                {"name": "Revenue", "val": "₹64,259 Cr", "qoq": "+2.6%", "yoy": "+7.6%"},
                {"name": "EBITDA", "val": "₹16,707 Cr", "qoq": "+1.9%", "yoy": "+6.4%"},
                {"name": "PBT", "val": "₹15,820 Cr", "qoq": "+2.1%", "yoy": "+5.8%"},
                {"name": "PAT", "val": "₹11,909 Cr", "qoq": "+2.0%", "yoy": "+5.0%"}
            ]
        }),
        "hours_ago": 5
    },
    {
        "ticker": "RELIANCE",
        "category": "M&A",
        "headline": "Strategic Joint Venture binding agreement executed for clean tech expansion",
        "materiality_score": 0.88,
        "ai_summary": "RIL signs 51:49 JV agreement for green hydrogen electrolysis manufacturing in Gujarat.",
        "hours_ago": 8
    },
    {
        "ticker": "TATAMOTORS",
        "category": "capex",
        "headline": "Board approves ₹9,000 Cr capacity expansion for EV platform facility",
        "materiality_score": 0.72,
        "ai_summary": "Capex tranche approved to establish dedicated gigafactory battery assembly lines.",
        "hours_ago": 14
    },
    {
        "ticker": "HDFCBANK",
        "category": "credit_rating",
        "headline": "CRISIL reaffirms AAA credit rating with stable outlook",
        "materiality_score": 0.55,
        "ai_summary": "CRISIL reiterates highest safety rating on Tier-II bonds and certificate of deposits.",
        "hours_ago": 20
    },
    {
        "ticker": "ITC",
        "category": "unclassified",
        "headline": "Submission of certificate under Regulation 74(5) of SEBI regulations",
        "materiality_score": 0.12,
        "ai_summary": "Routine quarterly depository confirmation received from registrar.",
        "hours_ago": 22
    },
    {
        "ticker": "SUNPHARMA",
        "category": "postal_ballot",
        "headline": "Notice of Postal Ballot and Electronic Voting Schedule",
        "materiality_score": 0.18,
        "ai_summary": "Routine voting notice for amendment in articles of association.",
        "hours_ago": 26
    }
]

async def seed():
    await init_db()
    async with async_session_maker() as session:
        # Seed companies
        for c in MOCK_COMPANIES:
            comp = Company(
                ticker=c["ticker"],
                name=c["name"],
                sector=c["sector"],
                market_cap_category=c["market_cap_category"]
            )
            session.add(comp)
        await session.commit()

        # Seed price history
        base_prices = {
            "RELIANCE": 2740.0, "TCS": 3980.0, "HDFCBANK": 1720.0, "INFY": 1840.0,
            "ICICIBANK": 1260.0, "TATAMOTORS": 940.0, "SUNPHARMA": 1780.0, "ITC": 490.0,
            "TATASTEEL": 155.0, "ZOMATO": 275.0, "TITAN": 3480.0, "KOTAKBANK": 1820.0,
            "BAJFINANCE": 7120.0, "HAL": 4350.0, "PERSISTENT": 5420.0
        }

        now = datetime.utcnow()
        for ticker, price in base_prices.items():
            for day_offset in range(15, -1, -1):
                p_date = (now - timedelta(days=day_offset)).strftime("%Y-%m-%d")
                change = 0.5 if day_offset % 2 == 0 else -0.3
                close_p = round(price * (1 + (change * (day_offset / 100.0))), 2)
                vol = 1400000.0 if ticker != "RELIANCE" else 4200000.0
                if day_offset == 0 and ticker == "TATAMOTORS":
                    vol = vol * 2.4 # volume spike
                    change = 3.6

                ph = PriceHistory(
                    ticker=ticker,
                    date=p_date,
                    open=close_p * 0.995,
                    high=close_p * 1.01,
                    low=close_p * 0.99,
                    close=close_p,
                    volume=vol,
                    change_pct=change,
                    avg_volume_20d=vol * 0.8
                )
                session.add(ph)
        await session.commit()

        # Seed announcements
        for a in MOCK_ANNOUNCEMENTS:
            ann = Announcement(
                ticker=a["ticker"],
                category=a["category"],
                headline=a["headline"],
                materiality_score=a["materiality_score"],
                ai_summary=a.get("ai_summary"),
                enrichment_json=a.get("enrichment_json"),
                filed_at=now - timedelta(hours=a["hours_ago"])
            )
            session.add(ann)
        await session.commit()

        # Seed triggered alerts
        alert1 = AlertTriggered(
            ticker="TATAMOTORS",
            rule_type="volume_spike",
            message="Unusual EOD Volume: Traded at 2.4x its 20-day moving average alongside +3.6% price move.",
            triggered_at=now - timedelta(hours=1)
        )
        alert2 = AlertTriggered(
            ticker="INFY",
            rule_type="material_announcement",
            message="Material Change at Helm: CFO resignation announced. Succession profile surfaced.",
            triggered_at=now - timedelta(hours=2)
        )
        session.add(alert1)
        session.add(alert2)
        await session.commit()

    print("Successfully seeded realistic investment database.")

if __name__ == "__main__":
    asyncio.run(seed())

