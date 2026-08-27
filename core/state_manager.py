"""
state_manager.py — Speichert den letzten Ampelstatus.
Verhindert Notification-Spam durch mehrere Filter:

  1. Statuswechsel-Filter   — nur bei echtem Wechsel senden
  2. Bestätigungs-Filter    — Gelb nur nach 2x hintereinander
  3. Score-Filter           — Gelb nur ab Score >= NOTIFY_YELLOW_MIN_SCORE
  4. Cooldown-Filter        — min. NOTIFY_COOLDOWN_MINUTES zwischen Notifications
"""

import json
import logging
import os
from datetime import datetime, timedelta
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


# ---------------------------------------------------------------------------
# Basis-Getter
# ---------------------------------------------------------------------------

def get_last_status() -> str:
    return _load().get("last_status", "green")


def get_last_notified_status() -> str:
    """Status der zuletzt tatsächlich gesendeten Notification."""
    return _load().get("last_notified_status", "green")


def get_last_notification_time() -> datetime | None:
    """Zeitpunkt der letzten gesendeten Notification."""
    ts = _load().get("last_notification_time")
    if ts:
        try:
            return datetime.fromisoformat(ts)
        except Exception:
            pass
    return None


def get_yellow_streak() -> int:
    """Wie viele aufeinanderfolgende Checks war der Status Gelb."""
    return _load().get("yellow_streak", 0)


def set_status(status: str) -> None:
    """Aktualisiert den Status und Zeitstempel."""
    state = _load()
    state["last_status"]  = status
    state["last_updated"] = datetime.now().isoformat()

    # Yellow-Streak pflegen
    if status == "yellow":
        state["yellow_streak"] = state.get("yellow_streak", 0) + 1
    else:
        state["yellow_streak"] = 0

    _save(state)


def mark_notified(status: str) -> None:
    """Markiert dass eine Notification gesendet wurde."""
    state = _load()
    state["last_notified_status"]   = status
    state["last_notification_time"] = datetime.now().isoformat()
    _save(state)


def status_changed(new_status: str) -> bool:
    """Gibt True zurück wenn sich der Status geändert hat."""
    return get_last_status() != new_status


def get_last_updated() -> str | None:
    return _load().get("last_updated")


# ---------------------------------------------------------------------------
# Haupt-Entscheidungslogik
# ---------------------------------------------------------------------------

def should_notify(new_status: str, new_score: int) -> tuple[bool, str]:
    """
    Entscheidet ob eine Pushover-Notification gesendet werden soll.

    Filter (alle müssen erfüllt sein für GELB, ROT überspringt Filter 2+3):
      1. Cooldown: min. NOTIFY_COOLDOWN_MINUTES seit letzter Notification
      2. Score-Filter (nur Gelb): Score >= NOTIFY_YELLOW_MIN_SCORE
      3. Bestätigungs-Filter (nur Gelb): yellow_streak >= NOTIFY_YELLOW_CONFIRM

    Rückgabe: (senden: bool, grund: str)
    """
    # Grün → nie senden
    if new_status == "green":
        return False, "Status GREEN — no notification"

    # ── Cooldown prüfen ──────────────────────────────────────
    last_time = get_last_notification_time()
    if last_time:
        cooldown_min = config.NOTIFY_COOLDOWN_MINUTES
        elapsed_min  = (datetime.now() - last_time).total_seconds() / 60
        if elapsed_min < cooldown_min:
            remaining = int(cooldown_min - elapsed_min)
            return False, f"Cooldown aktiv — noch {remaining} Min bis nächste Notification"

    # ── ROT → sofort senden (überspringt Score + Bestätigungsfilter) ──
    if new_status == "red":
        return True, f"RED alert — Score={new_score} (immediate)"

    # ── GELB — Score-Filter ──────────────────────────────────
    if new_score < config.NOTIFY_YELLOW_MIN_SCORE:
        return False, (
            f"YELLOW suppressed — Score={new_score} < {config.NOTIFY_YELLOW_MIN_SCORE} "
            f"(min required)"
        )

    # ── GELB — Bestätigungs-Filter ───────────────────────────
    streak = get_yellow_streak()
    # +1 weil set_status noch nicht aufgerufen wurde
    next_streak = streak + 1
    if next_streak < config.NOTIFY_YELLOW_CONFIRM:
        return False, (
            f"YELLOW suppressed — confirmation {next_streak}/{config.NOTIFY_YELLOW_CONFIRM} "
            f"(Score={new_score})"
        )

    return True, (
        f"YELLOW confirmed — Score={new_score} >= {config.NOTIFY_YELLOW_MIN_SCORE}, "
        f"streak={next_streak}/{config.NOTIFY_YELLOW_CONFIRM}"
    )
