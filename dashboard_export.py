"""
dashboard_export.py — Erweitert state.json für das Web-Dashboard

Schreibt nach jedem Check eine dashboard-kompatible state.json:
{
  "status":       "yellow",
  "score":        4,
  "red_count":    1,
  "yellow_count": 2,
  "error_count":  0,
  "last_updated": "18:45",
  "indicators":   [...],
  "history":      [...]   ← letzte 20 Checks
}

Integration in alert_engine.py / main.py:
    from dashboard_export import update_dashboard
    update_dashboard(alert_result)
"""

import json
import logging
import os
from datetime import datetime
import config

logger = logging.getLogger(__name__)

DASHBOARD_STATE_FILE = "state.json"
MAX_HISTORY = 20   # letzte N Checks im Verlauf behalten


def _load_state() -> dict:
    if not os.path.exists(DASHBOARD_STATE_FILE):
        return {}
    try:
        with open(DASHBOARD_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def update_dashboard(alert_result) -> None:
    """
    Schreibt den aktuellen AlertResult in state.json
    (kompatibel mit dashboard.html).

    Aufruf in main.py nach jedem Check:
        from dashboard_export import update_dashboard
        update_dashboard(alert)
    """
    try:
        state = _load_state()
        now   = datetime.now()

        # Indikatoren serialisieren
        indicators = []
        for r in alert_result.results:
            indicators.append({
                "name":    r.name,
                "value":   r.value,
                "status":  r.status,
                "score":   r.score,
                "message": r.message,
            })

        # History anhängen (Ring-Buffer)
        history = state.get("history", [])
        history.append({
            "time":   now.strftime("%H:%M"),
            "score":  alert_result.total_score,
            "status": alert_result.status,
        })
        if len(history) > MAX_HISTORY:
            history = history[-MAX_HISTORY:]

        new_state = {
            "status":        alert_result.status,
            "score":         alert_result.total_score,
            "red_count":     alert_result.red_count,
            "yellow_count":  alert_result.yellow_count,
            "error_count":   alert_result.error_count,
            "last_updated":  now.strftime("%H:%M"),
            "last_updated_full": now.isoformat(),
            "indicators":    indicators,
            "history":       history,
        }

        with open(DASHBOARD_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(new_state, f, indent=2, ensure_ascii=False)

        logger.debug(f"Dashboard state.json aktualisiert: {alert_result.status.upper()} Score={alert_result.total_score}")

    except Exception as e:
        logger.error(f"Dashboard Export fehlgeschlagen: {e}")
