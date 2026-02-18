from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from simulation import DEFAULT_ARRIVAL_PROFILE, SimulationConfig, evaluate_capacities, recommend_capacity

ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"


class AppHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path: Path, content_type: str = "text/html; charset=utf-8") -> None:
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        normalized = parsed.path.rstrip("/") or "/"

        if normalized == "/api/defaults":
            payload = {
                "arrival_profile": DEFAULT_ARRIVAL_PROFILE,
                "hours": 12,
                "max_queue": 12,
                "mean_service_minutes": 22,
                "price_per_service": 18,
                "server_cost_per_hour": 11.5,
                "capacity_min": 2,
                "capacity_max": 12,
            }
            self._send_json(payload)
            return

        # Fallback: en algunos previews la URL llega con prefijos o rutas adicionales.
        # Si no es /api, servimos la UI para evitar "Not Found".
        if normalized.startswith("/api"):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self._serve_file(WEB_DIR / "index.html")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/simulate":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length)

        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json({"error": "JSON inválido"}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            arrival_profile = payload.get("arrival_profile", DEFAULT_ARRIVAL_PROFILE)
            if len(arrival_profile) != 12:
                raise ValueError("El perfil de llegadas debe tener 12 valores (uno por hora).")

            config = SimulationConfig(
                hours=int(payload.get("hours", 12)),
                max_queue=int(payload.get("max_queue", 12)),
                mean_service_minutes=float(payload.get("mean_service_minutes", 22)),
                price_per_service=float(payload.get("price_per_service", 18)),
                server_cost_per_hour=float(payload.get("server_cost_per_hour", 11.5)),
                seed=int(payload.get("seed", 42)),
            )

            capacity_min = int(payload.get("capacity_min", 2))
            capacity_max = int(payload.get("capacity_max", 12))
            if capacity_min > capacity_max:
                raise ValueError("capacity_min no puede ser mayor que capacity_max")

            capacities = range(capacity_min, capacity_max + 1)

            results = evaluate_capacities(capacities, arrival_profile, config)
            best = recommend_capacity(
                results,
                max_avg_wait=float(payload.get("max_avg_wait", 10)),
                max_rejection_rate=float(payload.get("max_rejection_rate", 0.05)),
            )
        except (ValueError, TypeError) as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        self._send_json({"results": results, "best": best})


def run(host: str = "0.0.0.0", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"Servidor web en http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
