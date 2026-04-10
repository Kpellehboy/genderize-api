import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Genderize Proxy API")

# CORS - allow all methods including OPTIONS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GENDERIZE_URL = os.getenv("GENDERIZE_API_URL", "https://api.genderize.io")

def utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

@app.get("/api/classify")
async def classify_name(name: Optional[str] = Query(None)):
    # ----- MANUAL VALIDATION (no min_length in Query) -----
    # Missing or empty name -> 400
    if name is None or name.strip() == "":
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Missing or empty name parameter"}
        )
    
    # Non-string check (though query params are always strings)
    if not isinstance(name, str):
        return JSONResponse(
            status_code=422,
            content={"status": "error", "message": "Name must be a string"}
        )

    # ----- CALL GENDERIZE API -----
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
    except httpx.HTTPStatusError:
        return JSONResponse(
            status_code=502,
            content={"status": "error", "message": "Upstream API error"}
        )
    except Exception:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Internal server error"}
        )

    # ----- EDGE CASE: No prediction -----
    gender = data.get("gender")
    count = data.get("count", 0)
    
    if gender is None or count == 0:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "No prediction available for the provided name"}
        )

    # ----- SUCCESS: Transform and return -----
    probability = data.get("probability", 0.0)
    sample_size = count
    is_confident = (probability >= 0.7 and sample_size >= 100)

    result = {
        "status": "success",
        "data": {
            "name": name,
            "gender": gender,
            "probability": probability,
            "sample_size": sample_size,
            "is_confident": is_confident,
            "processed_at": utc_iso_now()
        }
    }
    
    return JSONResponse(status_code=200, content=result)

# Health check (optional)
@app.get("/health")
async def health():
    return {"status": "ok"}