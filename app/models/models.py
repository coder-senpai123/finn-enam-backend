from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Company(Base):
    __tablename__ = "companies"

    ticker = Column(String(20), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    sector = Column(String(50), nullable=False)
    market_cap_category = Column(String(20), nullable=False)  # Large, Mid, Small
    description = Column(Text, nullable=True)
    screener_slug = Column(String(50), nullable=True)

    prices = relationship("PriceHistory", back_populates="company", cascade="all, delete-orphan")
    announcements = relationship("Announcement", back_populates="company", cascade="all, delete-orphan")

class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), ForeignKey("companies.ticker"), index=True, nullable=False)
    date = Column(String(20), nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    change_pct = Column(Float, default=0.0)
    avg_volume_20d = Column(Float, default=0.0)

    company = relationship("Company", back_populates="prices")

class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), ForeignKey("companies.ticker"), index=True, nullable=False)
    category = Column(String(50), nullable=False, index=True) # results, M&A, management_change, etc.
    headline = Column(String(255), nullable=False)
    raw_text = Column(Text, nullable=True)
    ai_summary = Column(Text, nullable=True)
    materiality_score = Column(Float, default=0.5) # 0.0 to 1.0
    enrichment_json = Column(Text, nullable=True) # JSON details e.g. quarterly figures or person bio
    source_url = Column(String(255), nullable=True)
    filed_at = Column(DateTime, default=datetime.utcnow, index=True)

    company = relationship("Company", back_populates="announcements")

class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False, index=True)
    rule_type = Column(String(50), nullable=False) # volume_spike, price_move, announcement_type, materiality
    threshold = Column(Float, nullable=True) # e.g. 2.0 (2x volume), 5.0 (5% price move)
    category_filter = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)

class AlertTriggered(Base):
    __tablename__ = "alerts_triggered"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False, index=True)
    rule_type = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    payload_json = Column(Text, nullable=True)
    triggered_at = Column(DateTime, default=datetime.utcnow, index=True)
    is_read = Column(Boolean, default=False)

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False, index=True)
    doc_type = Column(String(50), nullable=False) # annual_report, concall, presentation
    title = Column(String(200), nullable=False)
    period = Column(String(50), nullable=True) # e.g. Q2 FY27, FY26
    chunk_text = Column(Text, nullable=False)

