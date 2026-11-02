from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.router import api_router
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

app.include_router(api_router)

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
