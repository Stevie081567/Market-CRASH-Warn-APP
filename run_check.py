"""
run_check.py — GitHub Actions Entry Point
Führt einen vollständigen Markt-Check durch:
  1. Alle Indikatoren abrufen
  2. state.json aktualisieren (→ GitHub Pages Dashboard)
  3. Pushover senden wenn Statuswechsel

Aufruf: python run_check.py
"""

import logging
import os
import sys
from datetime import datetime

# Logs-Ordner anlegen (GitHub Actions hat kein persistentes Filesystem)
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("run_check")


def main():
    import pytz
    import config
    from core.alert_engine  import run_all_checks
    from core               import state_manager, notifier
    from dashboard_export   import update_dashboard

    tz  = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tz)
    logger.info("=" * 50)
    logger.info(f"StockCRASH Check — {now.strftime('%Y-%m-%d %H:%M ET')}")
    logger.info("=" * 50)

    # Markt-Check
    alert = run_all_checks(include_futures=True)

    # Dashboard state.json aktualisieren
    update_dashboard(alert)

    # Ergebnis loggen
    logger.info(f"Gesamtstatus: {alert.status.upper()} | Score: {alert.total_score} | "
                f"🔴 {alert.red_count} | 🟡 {alert.yellow_count} | ⚫ {alert.error_count}")
    for r in alert.results:
        logger.info(f"  {r}")

    # Pushover nur bei Statuswechsel
    old_status = state_manager.get_last_status()
    if state_manager.status_changed(alert.status):
        logger.info(f"Statuswechsel: {old_status.upper()} → {alert.status.upper()} — sende Pushover")
        success = notifier.send_alert(alert)
        if success:
            logger.info("✅ Pushover gesendet")
        else:
            logger.warning("❌ Pushover fehlgeschlagen")
    else:
        logger.info(f"Status unverändert ({alert.status.upper()}) — keine Notification")

    state_manager.set_status(alert.status)

    logger.info("Check abgeschlossen ✓")
    sys.exit(0)


if __name__ == "__main__":
    main()
