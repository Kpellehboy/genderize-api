import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Genderize Proxy API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Explicit OPTIONS handler to guarantee CORS preflight works
@app.options("/api/classify")
async def options_classify():
    return JSONResponse(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
        content={}
    )

GENDERIZE_URL = os.getenv("GENDERIZE_API_URL", "https://api.genderize.io")

def utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

@app.get("/api/classify")
async def classify_name(name: Optional[str] = Query(None)):
    # Manual validation
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

    gender = data.get("gender")
    count = data.get("count", 0)
    
    if gender is None or count == 0:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "No prediction available for the provided name"}
        )

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

@app.get("/health")
async def health():
    return {"status": "ok"}