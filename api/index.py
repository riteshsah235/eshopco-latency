
import json
import math
from pathlib import Path
from http.server import BaseHTTPRequestHandler

DATA_FILE = Path(__file__).resolve().parent.parent / "q-vercel-latency.json"


class handler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        super().end_headers()

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(length) or b"{}")
            regions = request.get("regions", [])
            threshold = float(request.get("threshold_ms", 180))

            if not isinstance(regions, list):
                return self.send_json(400, {"error": "regions must be a list"})

            with open(DATA_FILE, encoding="utf-8") as file:
                records = json.load(file)

            results = []
            for region in regions:
                rows = [r for r in records if r["region"] == region]
                if not rows:
                    continue

                latencies = sorted(float(r["latency_ms"]) for r in rows)
                uptimes = [float(r["uptime_pct"]) for r in rows]

                pos = (len(latencies) - 1) * 0.95
                lo, hi = math.floor(pos), math.ceil(pos)
                p95 = latencies[lo] + (latencies[hi] - latencies[lo]) * (pos - lo)

                results.append({
                    "region": region,
                    "avg_latency": sum(latencies) / len(latencies),
                    "p95_latency": p95,
                    "avg_uptime": sum(uptimes) / len(uptimes),
                    "breaches": sum(x > threshold for x in latencies)
                })

            self.send_json(200, {"regions": results})

        except Exception:
            self.send_json(500, {"error": "Unable to process telemetry"})

