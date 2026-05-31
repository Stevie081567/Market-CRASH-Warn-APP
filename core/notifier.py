"""
notifier.py — Pushover Integration
Sendet Notifications an iPhone/iPad des Benutzers.
Prioritäten und Sounds basieren auf dem Ampelstatus.
"""

import logging
import requests
import config

logger = logging.getLogger(__name__)

# Pushover Prioritäten
PRIORITY_LOW    = -1   # Kein Sound, kein Vibration
PRIORITY_NORMAL =  0   # Normaler Sound
PRIORITY_HIGH   =  1   # Hoher Sound, Vibration
PRIORITY_EMERG  =  2   # Wiederholt bis bestätigt (erfordert retry + expire)

# Pushover Sounds
SOUND_PUSHOVER    = "pushover"       # Standard
SOUND_SIREN       = "siren"          # Alarm
SOUND_SPACEALARM  = "spacealarm"     # Für rote Alerts
SOUND_NONE        = "none"

# Status → Pushover-Konfiguration
STATUS_CONFIG = {
    "green": {
        "priority": PRIORITY_LOW,
        "sound":    SOUND_NONE,
        "title_prefix": "🟢",
    },
    "yellow": {
        "priority": PRIORITY_NORMAL,
        "sound":    SOUND_PUSHOVER,
        "title_prefix": "🟡",
    },
    "red": {
        "priority": PRIORITY_HIGH,
        "sound":    SOUND_SPACEALARM,
        "title_prefix": "🔴",
    },
}


def send_notification(
    title:   str,
    message: str,
    status:  str = "green",
    url:     str = "",
    url_title: str = "",
) -> bool:
    """
    Sendet eine Pushover-Notification.
    Gibt True bei Erfolg zurück, False bei Fehler.
    """
    if not config.PUSHOVER_APP_TOKEN or not config.PUSHOVER_USER_KEY:
        logger.error("Pushover Credentials nicht gesetzt (.env prüfen)")
        return False

    conf = STATUS_CONFIG.get(status, STATUS_CONFIG["green"])

    payload = {
        "token":    config.PUSHOVER_APP_TOKEN,
        "user":     config.PUSHOVER_USER_KEY,
        "title":    f"{conf['title_prefix']} {title}",
        "message":  message,
        "priority": conf["priority"],
        "sound":    conf["sound"],
        "html":     0,
    }

    if url:
        payload["url"]       = url
        payload["url_title"] = url_title or "Details"

    # Emergency-Priorität benötigt retry + expire
    if conf["priority"] == PRIORITY_EMERG:
        payload["retry"]  = 60   # alle 60 Sekunden wiederholen
        payload["expire"] = 3600 # max 1 Stunde

    try:
        resp = requests.post(
            config.PUSHOVER_API_URL,
            data=payload,
            timeout=10
        )
        resp.raise_for_status()
        result = resp.json()

        if result.get("status") == 1:
            logger.info(f"Pushover gesendet: [{status.upper()}] {title}")
            return True
        else:
            logger.error(f"Pushover Fehler: {result.get('errors', 'Unbekannt')}")
            return False

    except Exception as e:
        logger.error(f"Pushover Ausnahme: {e}")
        return False


def send_alert(alert_result) -> bool:
    """Convenience-Wrapper: sendet AlertResult als Pushover-Notification."""
    return send_notification(
        title=alert_result.to_pushover_title(),
        message=alert_result.to_pushover_message(),
        status=alert_result.status,
    )


def send_test_notification() -> bool:
    """Sendet eine Test-Notification zum Überprüfen der Konfiguration."""
    return send_notification(
        title="StockCrash WarnApp — Test",
        message="✅ Verbindung erfolgreich!\nApp läuft und überwacht die Märkte.",
        status="green",
    )
