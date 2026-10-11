
import json
import math
from pathlib import Path
from http.server import BaseHTTPRequestHandler

DATA_FILE = Path(__file__).resolve().parent.parent / "q-vercel-latency.json"


def percentile95(values):
    values = sorted(values)
    if len(values) == 1:
        return values[0]

    position = (len(values) - 1) * 0.95
    lower = math.floor(position)
    upper = math.ceil(position)

    return values[lower] + (values[upper] - values[lower]) * (
        position - lower
    )


class handler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_json(200, {"ok": True})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(length))

            regions = request.get("regions", [])
            threshold = float(request.get("threshold_ms", 180))

            if not isinstance(regions, list):
                return self.send_json(
                    400, {"error": "regions must be a list"}
                )

            with open(DATA_FILE, encoding="utf-8") as file:
                records = json.load(file)

            results = []

            for region in regions:
                rows = [
                    row for row in records
                    if row["region"] == region
                ]

                if not rows:
                    continue

                latencies = [float(row["latency_ms"]) for row in rows]
                uptimes = [float(row["uptime_pct"]) for row in rows]

                results.append({
                    "region": region,
                    "avg_latency": sum(latencies) / len(latencies),
                    "p95_latency": percentile95(latencies),
                    "avg_uptime": sum(uptimes) / len(uptimes),
                    "breaches": sum(
                        latency > threshold for latency in latencies
                    )
                })

            self.send_json(200, {"regions": results})

        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            self.send_json(400, {"error": str(exc)})
        except Exception:
            self.send_json(500, {"error": "Internal server error"})
