import os
import json
import urllib.request
import asyncio
from typing import Optional, Dict, Any
from app.config import settings

# Active verified models for your API key
MODELS = {
    "flash_lite": "gemini-3.5-flash-lite",
    "flash": "gemini-3.5-flash",
    "pro": "gemini-3.5-flash",  # Reliable fast latency
}

async def generate_gemini(model_tier: str, prompt: str, system_instruction: Optional[str] = None) -> str:
    """
    Direct asynchronous HTTP implementation with urllib running in thread pool.
    Always queries Google Gemini Live API.
    """
    model_name = MODELS.get(model_tier, "gemini-3.5-flash")
    api_key = settings.GEMINI_API_KEY

    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured in backend environment.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    payload_dict: Dict[str, Any] = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    if system_instruction:
        payload_dict["system_instruction"] = {"parts": [{"text": system_instruction}]}

    payload_data = json.dumps(payload_dict).encode("utf-8")
    req = urllib.request.Request(url, data=payload_data, headers={"Content-Type": "application/json"})

    def _sync_request():
        try:
            with urllib.request.urlopen(req, timeout=18) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if not candidates:
                    raise ValueError(f"No response candidates returned by Gemini: {data}")
                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    raise ValueError("Empty candidate content from Gemini.")
                return parts[0].get("text", "").strip()
        except urllib.error.HTTPError as he:
            err_body = he.read().decode("utf-8")
            raise ValueError(f"Gemini API HTTP {he.code}: {err_body}")

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_request)
