"""
state_manager.py — Speichert den letzten Ampelstatus.
Verhindert Notification-Spam: Alert nur bei Statuswechsel.
"""

import json
import logging
import os
from datetime import datetime
import config

logger = logging.getLogger(__name__)


def _load() -> dict:
    if not os.path.exists(config.STATE_FILE):
        return {}
    try:
        with open(config.STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(state: dict) -> None:
    try:
        with open(config.STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"State speichern fehlgeschlagen: {e}")


def get_last_status() -> str:
    """Gibt den zuletzt gesendeten Ampelstatus zurück ('green', 'yellow', 'red')."""
    return _load().get("last_status", "green")


def set_status(status: str) -> None:
    """Aktualisiert den Status und Zeitstempel."""
    state = _load()
    state["last_status"]   = status
    state["last_updated"]  = datetime.now().isoformat()
    _save(state)


def status_changed(new_status: str) -> bool:
    """Gibt True zurück, wenn sich der Status geändert hat."""
    return get_last_status() != new_status


def get_last_updated() -> str | None:
    return _load().get("last_updated")
