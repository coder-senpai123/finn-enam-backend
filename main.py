from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.router import api_router
from app.api.auth import router as auth_router
from app.api.feed import router as feed_router
from app.api.portfolio import router as portfolio_router
from app.api.research import router as research_router
from app.api.alerts import router as alerts_router
from app.api.sync import router as sync_router
from app.core.database import init_db
from app.core.mongodb import init_mongodb

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schemas on launch
    await init_db()
    # Initialize MongoDB connection
    await init_mongodb()
    yield

app = FastAPI(
    title="FINN - Financial Investment Agent API",
    description="Mobile-first investment intelligence engine powered by Gemini",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Mount under /api prefix (e.g. /api/feed, /api/auth/google)
app.include_router(api_router)

# 2. Mount directly at root as well (e.g. /feed, /auth/google) so clients calling without /api never 404
app.include_router(auth_router)
app.include_router(feed_router)
app.include_router(portfolio_router)
app.include_router(research_router)
app.include_router(alerts_router)
app.include_router(sync_router)

@app.get("/")
def health_check():
    return {
        "status": "healthy",
        "agent": "FINN Financial Investment Agent",
        "version": "1.0.0",
        "modes": ["push_digest", "triggered_alerts", "on_demand_pull"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
