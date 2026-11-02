from enum import Enum
from app.ai.gemini_client import MODELS

class TaskType(str, Enum):
    CLASSIFY = "classify"
    SUMMARIZE = "summarize"
    EXTRACT = "extract"
    ENRICH = "enrich"
    BUSINESS_SNAPSHOT = "business_snapshot"
    FINANCIAL_SNAPSHOT = "financial_snapshot"
    TRAJECTORY = "trajectory"
    BALANCE_SHEET = "balance_sheet"
    CASH_QUALITY = "cash_quality"
    NARRATIVE_VS_NUMBERS = "narrative_vs_numbers"
    GUIDANCE = "guidance"
    BULL_BEAR = "bull_bear"

def route_model(task: str) -> str:
    """
    Returns the appropriate Gemini model tier for a given task.
    - Flash-Lite: Bulk classification, fast sorting
    - Flash: Extraction, summaries, business/financial snapshot
    - Pro: Deep reasoning (narrative vs numbers, trajectory, bull vs bear)
    """
    if task in [TaskType.CLASSIFY]:
        return "flash_lite"
    elif task in [TaskType.SUMMARIZE, TaskType.EXTRACT, TaskType.ENRICH, TaskType.BUSINESS_SNAPSHOT, TaskType.FINANCIAL_SNAPSHOT]:
        return "flash"
    elif task in [TaskType.NARRATIVE_VS_NUMBERS, TaskType.BULL_BEAR, TaskType.TRAJECTORY, TaskType.BALANCE_SHEET, TaskType.CASH_QUALITY, TaskType.GUIDANCE]:
        return "pro"
    return "flash"

