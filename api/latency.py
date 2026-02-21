from http.server import BaseHTTPRequestHandler
import json
import os
import statistics

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
}

# Load telemetry data — robust path resolution
_here = os.path.dirname(os.path.abspath(__file__))
_data_path = os.path.join(_here, "..", "q-vercel-latency.json")
with open(_data_path, "r") as _f:
    TELEMETRY = json.load(_f)


def _percentile(data, pct):
    """Compute the p-th percentile of a sorted list."""
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * pct / 100
    lo, hi = int(k), min(int(k) + 1, len(sorted_data) - 1)
    return sorted_data[lo] + (sorted_data[hi] - sorted_data[lo]) * (k - lo)


def compute_metrics(regions, threshold_ms):
    result = {}
    for region in regions:
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
            "avg_latency": round(statistics.mean(latencies), 4),
            "p95_latency": round(_percentile(latencies, 95), 4),
            "avg_uptime": round(statistics.mean(uptimes), 4),
            "breaches": sum(1 for l in latencies if l > threshold_ms),
        }
    return result


class handler(BaseHTTPRequestHandler):

    def _send_cors_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        self.end_headers()

    def do_OPTIONS(self):
        self._send_cors_headers(200)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            regions = body.get("regions", [])
            threshold_ms = float(body.get("threshold_ms", 180))
            result = compute_metrics(regions, threshold_ms)
            payload = json.dumps(result).encode()
            self._send_cors_headers(200)
            self.wfile.write(payload)
        except Exception as e:
            err = json.dumps({"error": str(e)}).encode()
            self._send_cors_headers(500)
            self.wfile.write(err)

    def log_message(self, format, *args):
        pass  # suppress default stderr logging
