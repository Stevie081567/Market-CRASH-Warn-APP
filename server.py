"""
server.py — StockCRASH_WarnAPP Web-Server
Ersetzt 'python -m http.server' mit echtem Refresh-Endpunkt.

Endpunkte:
  GET  /                       → MktCRASH_Dashboard.html
  GET  /state.json             → Aktueller Status (gecacht)
  POST /api/refresh            → Sofortiger Markt-Check (aktualisiert state.json)
  GET  /api/status             → Schnell-Status als JSON
  GET  /<datei>                → Statische Dateien

Start:
  python server.py             → Port 8080
  python server.py 9090        → Anderer Port
"""

import json
import logging
import os
import sys
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# Arbeitsverzeichnis = Projektordner (damit Imports funktionieren)
BASE_DIR = Path(__file__).parent
os.chdir(BASE_DIR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("server")

# Globale Sperre: verhindert mehrere gleichzeitige Checks
_refresh_lock = threading.Lock()
_last_refresh: datetime | None = None


def _run_check() -> dict:
    """Führt einen vollständigen Markt-Check durch und aktualisiert state.json."""
    global _last_refresh
    try:
        # Imports hier (damit server.py standalone lauffähig bleibt)
        from core.alert_engine import run_all_checks
        from dashboard_export import update_dashboard

        logger.info("Manual refresh gestartet...")
        alert = run_all_checks(include_futures=True)
        update_dashboard(alert)
        _last_refresh = datetime.now()

        logger.info(f"Refresh abgeschlossen: {alert.status.upper()} Score={alert.total_score}")
        return {
            "ok":      True,
            "status":  alert.status,
            "score":   alert.total_score,
            "updated": _last_refresh.strftime("%H:%M:%S"),
        }
    except Exception as e:
        logger.error(f"Refresh fehlgeschlagen: {e}")
        return {"ok": False, "error": str(e)}


def _load_state() -> dict:
    state_file = BASE_DIR / "state.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".css":  "text/css",
    ".js":   "application/javascript",
    ".ico":  "image/x-icon",
    ".png":  "image/png",
    ".svg":  "image/svg+xml",
}


class CrashHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        # Nur 4xx/5xx loggen — kein Rauschen für jeden 200-Request
        code = str(args[1]) if len(args) > 1 else ""
        if not code.startswith("2") and not code.startswith("3"):
            logger.warning(f"{self.address_string()} {fmt % args}")

    def _send_json(self, data: dict, code: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path):
        suffix = path.suffix.lower()
        mime   = MIME_TYPES.get(suffix, "application/octet-stream")
        data   = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]   # Query-String abschneiden

        # Root → Dashboard
        if path in ("/", "/index.html"):
            self._send_file(BASE_DIR / "MktCRASH_Dashboard.html")
            return

        # API: Schnell-Status
        if path == "/api/status":
            state = _load_state()
            self._send_json({
                "status":       state.get("status", "unknown"),
                "score":        state.get("score", 0),
                "last_updated": state.get("last_updated_full", ""),
                "server_time":  datetime.now().isoformat(),
            })
            return

        # Statische Dateien
        file_path = BASE_DIR / path.lstrip("/")
        if file_path.exists() and file_path.is_file():
            self._send_file(file_path)
            return

        # 404
        self._send_json({"error": "Not found", "path": path}, 404)

    def do_POST(self):
        path = self.path.split("?")[0]

        if path == "/api/refresh":
            if not _refresh_lock.acquire(blocking=False):
                self._send_json({
                    "ok":    False,
                    "error": "Refresh läuft bereits — bitte warten"
                }, 429)
                return
            try:
                result = _run_check()
                self._send_json(result, 200 if result["ok"] else 500)
            finally:
                _refresh_lock.release()
            return

        self._send_json({"error": "Not found"}, 404)

    def do_OPTIONS(self):
        # CORS preflight
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

    server = HTTPServer(("", port), CrashHandler)
    logger.info("=" * 50)
    logger.info(f"StockCRASH Dashboard läuft auf http://localhost:{port}")
    logger.info(f"Dashboard:  http://localhost:{port}/MktCRASH_Dashboard.html")
    logger.info(f"Refresh:    POST http://localhost:{port}/api/refresh")
    logger.info(f"Status API: GET  http://localhost:{port}/api/status")
    logger.info("=" * 50)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server gestoppt")


if __name__ == "__main__":
    main()
