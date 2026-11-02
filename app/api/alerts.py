from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List
from app.core.database import get_db
from app.models.models import AlertTriggered, AlertRule
from app.schemas.schemas import AlertTriggeredOut, AlertRuleOut, AlertRuleCreate

router = APIRouter(prefix="/alerts", tags=["alerts"])

@router.get("/triggered", response_model=List[AlertTriggeredOut])
async def get_triggered_alerts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AlertTriggered).order_by(desc(AlertTriggered.triggered_at)))
    return result.scalars().all()

@router.get("/rules", response_model=List[AlertRuleOut])
async def get_alert_rules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AlertRule))
    return result.scalars().all()

@router.post("/rules", response_model=AlertRuleOut)
async def create_alert_rule(rule: AlertRuleCreate, db: AsyncSession = Depends(get_db)):
    new_rule = AlertRule(**rule.dict(), is_active=True)
    db.add(new_rule)
    await db.commit()
    await db.refresh(new_rule)
    return new_rule

