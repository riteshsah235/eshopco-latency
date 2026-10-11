import json
import math
from pathlib import Path
from http.server import BaseHTTPRequestHandler

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "telemetry.json"


def percentile(values, p=95):
    """Linear interpolation percentile at position (n - 1) * p / 100."""
    if not values:
        return None
    xs = sorted(float(v) for v in values)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * p / 100.0
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return xs[lo]
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def load_records():
    with DATA_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Telemetry file must contain a JSON array.")
    return data


class handler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload, allow_nan=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Vary", "Origin")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Vary", "Origin")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        self.send_json(200, {
            "status": "ok",
            "message": "Latency API is running. Send a POST request with regions and threshold_ms."
        })

    def do_POST(self):
        try:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                return self.send_json(400, {"error": "Invalid Content-Length."})

            if length <= 0:
                return self.send_json(400, {"error": "A JSON request body is required."})

            try:
                request = json.loads(self.rfile.read(length).decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return self.send_json(400, {"error": "Malformed JSON request body."})

            if not isinstance(request, dict):
                return self.send_json(400, {"error": "Request body must be a JSON object."})

            regions = request.get("regions")
            threshold = request.get("threshold_ms", 180)

            if not isinstance(regions, list) or not all(isinstance(r, str) for r in regions):
                return self.send_json(400, {"error": "'regions' must be an array of strings."})

            if (isinstance(threshold, bool)
                    or not isinstance(threshold, (int, float))
                    or not math.isfinite(threshold)):
                return self.send_json(400, {"error": "'threshold_ms' must be a finite number."})

            records = load_records()
            response = {}

            for region in regions:
                rows = []
                for row in records:
                    if row.get("region") != region:
                        continue
                    latency = row.get("latency_ms")
                    uptime = row.get("uptime_pct")
                    if (isinstance(latency, bool) or not isinstance(latency, (int, float))
                            or not math.isfinite(latency)
                            or isinstance(uptime, bool) or not isinstance(uptime, (int, float))
                            or not math.isfinite(uptime)):
                        continue
                    rows.append(row)

                if not rows:
                    response[region] = {
                        "avg_latency": None,
                        "p95_latency": None,
                        "avg_uptime": None,
                        "breaches": 0
                    }
                    continue

                latencies = [float(row["latency_ms"]) for row in rows]
                uptimes = [float(row["uptime_pct"]) for row in rows]
                response[region] = {
                    "avg_latency": sum(latencies) / len(latencies),
                    "p95_latency": percentile(latencies, 95),
                    "avg_uptime": sum(uptimes) / len(uptimes),
                    "breaches": sum(value > threshold for value in latencies)
                }

            return self.send_json(200, response)

        except Exception:
            return self.send_json(500, {"error": "Unable to process telemetry data."})
