from fastapi import APIRouter, HTTPException
from app.schemas.schemas import ResearchRequest, ResearchResponse
from app.ai.analyzer import run_analysis

router = APIRouter(prefix="/research", tags=["research"])

@router.post("", response_model=ResearchResponse)
async def perform_research(req: ResearchRequest):
    """
    On-demand analysis grounded in primary documents (ARs + concall transcripts).
    Routes query through Gemini Flash / Pro depending on depth.
    """
    try:
        result = await run_analysis(
            ticker=req.ticker.upper(),
            module=req.module,
            custom_query=req.query
        )
        return ResearchResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

