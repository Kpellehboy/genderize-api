import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse  # <-- ADD THIS
from pydantic import BaseModel, Field
import httpx
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Genderize Proxy API")

# ---------- CORS FIX ----------
# Allow all methods including OPTIONS (preflight)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],  # <-- CHANGE: "*" includes GET, OPTIONS, etc.
    allow_headers=["*"],
)

GENDERIZE_URL = os.getenv("GENDERIZE_API_URL", "https://api.genderize.io")

# ---------- Response Models (unchanged) ----------
class SuccessData(BaseModel):
    name: str
    gender: str
    probability: float
    sample_size: int = Field(alias="sample_size")
    is_confident: bool
    processed_at: str

    class Config:
        populate_by_name = True

class SuccessResponse(BaseModel):
    status: str = "success"
    data: SuccessData

# ---------- Helper Functions (unchanged) ----------
def compute_confidence(probability: float, sample_size: int) -> bool:
    return probability >= 0.7 and sample_size >= 100

def utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

# ---------- The Fixed Endpoint ----------
@app.get("/api/classify")
async def classify_name(name: Optional[str] = Query(None, min_length=1)):
    # 1. Validation - return JSONResponse directly (not HTTPException)
    if name is None or name.strip() == "":
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Missing or empty name parameter"}
        )
    
    if not isinstance(name, str):
        return JSONResponse(
            status_code=422,
            content={"status": "error", "message": "Name must be a string"}
        )

    # 2. Call Genderize API
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(GENDERIZE_URL, params={"name": name})
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException:
        return JSONResponse(
            status_code=504,
            content={"status": "error", "message": "Genderize API timeout"}
        )
    except httpx.HTTPStatusError as e:
        print(f"Genderize error: {e}")
        return JSONResponse(
            status_code=502,
            content={"status": "error", "message": "Upstream API error"}
        )
    except Exception as e:
        print(f"Unexpected: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Internal server error"}
        )

    # 3. Edge case: no prediction
    gender = data.get("gender")
    count = data.get("count", 0)
    
    if gender is None or count == 0:
        return JSONResponse(
            status_code=404,  # or 400, but 404 makes sense
            content={"status": "error", "message": "No prediction available for the provided name"}
        )

    # 4. Transform and return success
    probability = data.get("probability", 0.0)
    sample_size = count
    is_confident = compute_confidence(probability, sample_size)

    result_data = SuccessData(
        name=name,
        gender=gender,
        probability=probability,
        sample_size=sample_size,
        is_confident=is_confident,
        processed_at=utc_iso_now()
    )

    return JSONResponse(
        status_code=200,
        content={"status": "success", "data": result_data.dict(by_alias=True)}
    )

# Optional health check
@app.get("/health")
async def health():
    return {"status": "ok"}