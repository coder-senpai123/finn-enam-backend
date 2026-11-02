import httpx
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional
import re
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

def clean_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()

async def fetch_screener_company_data(ticker: str) -> Dict[str, Any]:
    """
    Fetches real primary data for any NSE/BSE company from screener.in:
    - Company fundamentals summary (Market Cap, PE, ROCE, ROE, Debt/Eq)
    - Corporate announcements filed with BSE/NSE
    - Concall / Earnings-call transcripts
    - Annual Report PDF links
    """
    clean_ticker = ticker.upper().replace(".NS", "").replace(".BO", "")
    url = f"https://www.screener.in/company/{clean_ticker}/"

    async with httpx.AsyncClient(headers=HEADERS, timeout=12.0, follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                return {"error": f"Company '{clean_ticker}' not found on screener.in (status {resp.status_code})"}

            soup = BeautifulSoup(resp.text, "html.parser")
            
            # 1. Company Name & About
            name_tag = soup.find("h1")
            company_name = clean_text(name_tag.text) if name_tag else clean_ticker
            about_tag = soup.find("div", {"class": "about"})
            description = clean_text(about_tag.text) if about_tag else ""

            # 2. Key Ratios / Fundamentals
            ratios = {}
            top_ratios = soup.find("ul", {"id": "top-ratios"})
            if top_ratios:
                for li in top_ratios.find_all("li"):
                    name = clean_text(li.find("span", {"class": "name"}).text) if li.find("span", {"class": "name"}) else ""
                    val = clean_text(li.find("span", {"class": "nowrap value"}).text) if li.find("span", {"class": "nowrap value"}) else ""
                    if name and val:
                        ratios[name] = val

            # 3. Documents section (Announcements, Concalls, Annual Reports)
            announcements = []
            annual_reports = []
            concalls = []

            docs_sec = soup.find("section", {"id": "documents"})
            if docs_sec:
                for li in docs_sec.find_all("li"):
                    a = li.find("a")
                    if not a:
                        continue
                    title = clean_text(li.text)
                    href = a.get("href", "")
                    if not href.startswith("http"):
                        href = f"https://www.screener.in{href}"

                    if "Annual Report" in title:
                        annual_reports.append({"title": title, "url": href})
                    elif "Transcript" in title or "concall" in href.lower() or "Earnings Call" in title:
                        concalls.append({"title": title, "url": href})
                    elif "bseindia.com" in href or "announcements" in href.lower():
                        announcements.append({"headline": title, "url": href, "filed_at": datetime.utcnow().strftime("%Y-%m-%d")})

            return {
                "ticker": clean_ticker,
                "name": company_name,
                "description": description,
                "ratios": ratios,
                "announcements": announcements[:10],
                "concalls": concalls[:6],
                "annual_reports": annual_reports[:5],
                "source": "screener.in + bse/nse primary disclosures"
            }

        except Exception as e:
            print(f"Error fetching from screener for {clean_ticker}: {e}")
            return {"error": str(e)}

