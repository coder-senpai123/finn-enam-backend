from fastapi import APIRouter
from app.api.feed import router as feed_router
from app.api.portfolio import router as portfolio_router
from app.api.research import router as research_router
from app.api.alerts import router as alerts_router
from app.api.sync import router as sync_router
from app.api.auth import router as auth_router

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(feed_router)
api_router.include_router(portfolio_router)
api_router.include_router(research_router)
api_router.include_router(alerts_router)
api_router.include_router(sync_router)
