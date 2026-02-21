from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
from mangum import Mangum
import json
import os
import numpy as np

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "q-vercel-latency.json")

with open(DATA_PATH, "r") as f:
    TELEMETRY = json.load(f)


class LatencyRequest(BaseModel):
    regions: List[str]
    threshold_ms: float


@app.options("/api/latency")
async def options_latency():
    return JSONResponse(
        content={},
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
    )


@app.post("/api/latency")
def latency_metrics(req: LatencyRequest):
    result = {}
    for region in req.regions:
        records = [r for r in TELEMETRY if r["region"] == region]
        if not records:
            result[region] = {
                "avg_latency": None,
                "p95_latency": None,
                "avg_uptime": None,
                "breaches": 0,
            }
            continue

        latencies = [r["latency_ms"] for r in records]
        uptimes = [r["uptime_pct"] for r in records]

        result[region] = {
            "avg_latency": round(float(np.mean(latencies)), 4),
            "p95_latency": round(float(np.percentile(latencies, 95)), 4),
            "avg_uptime": round(float(np.mean(uptimes)), 4),
            "breaches": int(sum(1 for l in latencies if l > req.threshold_ms)),
        }

    return JSONResponse(
        content=result,
        headers={"Access-Control-Allow-Origin": "*"},
    )


# Mangum adapter — required for Vercel's Python serverless runtime
handler = Mangum(app, lifespan="off")
