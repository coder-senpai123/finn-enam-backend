from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime
from app.core.database import get_db
from app.models.models import Company, PriceHistory, Announcement, AlertTriggered
from app.schemas.schemas import SyncResponse, CompanyOut, PriceHistoryOut, AnnouncementOut, AlertTriggeredOut

router = APIRouter(prefix="/sync", tags=["sync"])

@router.get("", response_model=SyncResponse)
async def get_sync_data(
    since: str = Query(None, description="ISO timestamp of last sync"),
    db: AsyncSession = Depends(get_db)
):
    """
    Delta sync endpoint for mobile SQLite database caching.
    """
    comp_res = await db.execute(select(Company))
    companies = comp_res.scalars().all()

    price_res = await db.execute(select(PriceHistory).order_by(desc(PriceHistory.date)))
    prices = price_res.scalars().all()

    ann_res = await db.execute(select(Announcement).order_by(desc(Announcement.filed_at)).limit(50))
    announcements = ann_res.scalars().all()

    alerts_res = await db.execute(select(AlertTriggered).order_by(desc(AlertTriggered.triggered_at)).limit(20))
    alerts = alerts_res.scalars().all()

    return SyncResponse(
        companies=[CompanyOut.from_orm(c) for c in companies],
        latest_prices=[PriceHistoryOut.from_orm(p) for p in prices[:len(companies)]],
        recent_announcements=[AnnouncementOut.from_orm(a) for a in announcements],
        triggered_alerts=[AlertTriggeredOut.from_orm(al) for al in alerts],
        last_sync_timestamp=datetime.utcnow().isoformat()
    )

