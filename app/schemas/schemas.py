from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime

class CompanyBase(BaseModel):
    ticker: str
    name: str
    sector: str
    market_cap_category: str
    description: Optional[str] = None
    screener_slug: Optional[str] = None

class CompanyOut(CompanyBase):
    class Config:
        from_attributes = True

class PriceHistoryOut(BaseModel):
    id: int
    ticker: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    change_pct: float
    avg_volume_20d: float

    class Config:
        from_attributes = True

class AnnouncementOut(BaseModel):
    id: int
    ticker: str
    category: str
    headline: str
    raw_text: Optional[str] = None
    ai_summary: Optional[str] = None
    materiality_score: float
    enrichment_json: Optional[str] = None
    source_url: Optional[str] = None
    filed_at: datetime

    class Config:
        from_attributes = True

class FeedItemOut(BaseModel):
    announcement: AnnouncementOut
    priority_level: str # 'must-see', 'worth-knowing', 'routine'

class AlertRuleCreate(BaseModel):
    ticker: str
    rule_type: str
    threshold: Optional[float] = None
    category_filter: Optional[str] = None

class AlertRuleOut(AlertRuleCreate):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

class AlertTriggeredOut(BaseModel):
    id: int
    ticker: str
    rule_type: str
    message: str
    payload_json: Optional[str] = None
    triggered_at: datetime
    is_read: bool

    class Config:
        from_attributes = True

class ResearchRequest(BaseModel):
    ticker: str
    module: str # 'business_snapshot', 'financial_snapshot', 'trajectory', 'balance_sheet', 'cash_quality', 'narrative_vs_numbers', 'guidance', 'bull_bear'
    query: Optional[str] = None

class ResearchResponse(BaseModel):
    ticker: str
    module: str
    model_used: str
    title: str
    summary: str
    structured_data: Optional[Dict[str, Any]] = None
    sources: List[str] = []
    generated_at: str

class SyncResponse(BaseModel):
    companies: List[CompanyOut]
    latest_prices: List[PriceHistoryOut]
    recent_announcements: List[AnnouncementOut]
    triggered_alerts: List[AlertTriggeredOut]
    last_sync_timestamp: str

