
import json
import math
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

DATA_FILE = Path(__file__).resolve().parent.parent / "q-vercel-latency.json"

@app.post("/api")
async def metrics(request: Request):
    body = await request.json()
    regions = body.get("regions", [])
    threshold = float(body.get("threshold_ms", 180))

    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    results = []
    for region in regions:
        rows = [r for r in data if r["region"] == region]
        if not rows:
            continue

        values = sorted(float(r["latency_ms"]) for r in rows)
        uptimes = [float(r["uptime_pct"]) for r in rows]
        p = (len(values) - 1) * 0.95
        low, high = math.floor(p), math.ceil(p)
        p95 = values[low] + (values[high] - values[low]) * (p - low)

        results.append({
            "region": region,
            "avg_latency": sum(values) / len(values),
            "p95_latency": p95,
            "avg_uptime": sum(uptimes) / len(uptimes),
            "breaches": sum(v > threshold for v in values)
        })

    return JSONResponse({"regions": results})
