"""
main.py — StockCRASH_WarnAPP Einstiegspunkt
Startet den APScheduler mit allen Markt-Überwachungs-Jobs.

Zeitfenster (Europe/Berlin):
  Pre-Market:     Mo-Fr 14:00–15:30 (Futures + Global)
  Intraday:       Mo-Fr 15:30–22:00 (alle 15 Min, nur bei Statuswechsel)
  Daily Summary:  Mo-Fr 22:30 (immer senden)
  Weekend Check:  Sa 10:00 (Wochenzusammenfassung)
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime

import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

import config
from core import alert_engine, notifier, state_manager

# ---------------------------------------------------------------------------
# Logging einrichten
# ---------------------------------------------------------------------------
os.makedirs("logs", exist_ok=True)

log_handler = logging.handlers.RotatingFileHandler(
    config.LOG_FILE,
    maxBytes=config.LOG_MAX_BYTES,
    backupCount=config.LOG_BACKUP_COUNT,
    encoding="utf-8",
)
log_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
))

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
))

logging.basicConfig(level=logging.INFO, handlers=[log_handler, console_handler])
logger = logging.getLogger("main")


# ---------------------------------------------------------------------------
# Konfiguration validieren
# ---------------------------------------------------------------------------
def validate_config() -> bool:
    missing = []
    if not config.PUSHOVER_APP_TOKEN:
        missing.append("PUSHOVER_APP_TOKEN")
    if not config.PUSHOVER_USER_KEY:
        missing.append("PUSHOVER_USER_KEY")
    if not config.FRED_API_KEY:
        logger.warning("FRED_API_KEY fehlt — Yield Curve & Buffett Indicator deaktiviert")

    if missing:
        logger.error(f"Fehlende .env-Variablen: {', '.join(missing)}")
        return False
    return True


# ---------------------------------------------------------------------------
# Job-Funktionen
# ---------------------------------------------------------------------------
def job_premarket_check():
    """Pre-Market: Futures + globale Märkte vor US-Öffnung."""
    logger.info("=== PRE-MARKET CHECK gestartet ===")
    alert = alert_engine.run_all_checks(include_futures=True)

    logger.info(f"Status: {alert.status.upper()} | Score: {alert.total_score}")

    # Immer senden wenn gelb oder rot, sonst nur bei Statuswechsel
    if alert.status in ("yellow", "red") or state_manager.status_changed(alert.status):
        notifier.send_alert(alert)
        state_manager.set_status(alert.status)
    else:
        logger.info("Status unverändert GRÜN — keine Notification")


def job_intraday_check():
    """Intraday: alle 15 Minuten — nur bei Statuswechsel Notification."""
    now = datetime.now(pytz.timezone(config.TIMEZONE))
    logger.info(f"=== INTRADAY CHECK {now.strftime('%H:%M')} ===")

    alert = alert_engine.run_all_checks(include_futures=True)
    logger.info(f"Status: {alert.status.upper()} | Score: {alert.total_score}")

    if state_manager.status_changed(alert.status):
        old_status = state_manager.get_last_status()
        logger.info(f"Statuswechsel: {old_status.upper()} → {alert.status.upper()}")
        notifier.send_alert(alert)
        state_manager.set_status(alert.status)
    else:
        logger.info(f"Status unverändert: {alert.status.upper()} — keine Notification")


def job_daily_summary():
    """Tägliche Zusammenfassung um 22:30 — wird IMMER gesendet."""
    logger.info("=== DAILY SUMMARY ===")
    alert = alert_engine.run_all_checks(include_futures=False)

    # Titel anpassen
    title   = f"📊 Tages-Report: {alert.status_emoji()} {alert.status.upper()}"
    message = f"Tagesabschluss — {datetime.now().strftime('%d.%m.%Y')}\n\n"
    message += alert.to_pushover_message()

    notifier.send_notification(
        title=title,
        message=message,
        status=alert.status,
    )
    state_manager.set_status(alert.status)
    logger.info("Daily Summary gesendet")


def job_weekend_check():
    """Samstags: Wochenzusammenfassung."""
    logger.info("=== WEEKEND CHECK ===")
    alert = alert_engine.run_all_checks(include_futures=False)

    title   = f"📅 Wochen-Report: {alert.status_emoji()} {alert.status.upper()}"
    message = f"Wochenabschluss — {datetime.now().strftime('%d.%m.%Y')}\n\n"
    message += alert.to_pushover_message()

    notifier.send_notification(
        title=title,
        message=message,
        status=alert.status,
    )
    logger.info("Weekend Summary gesendet")


# ---------------------------------------------------------------------------
# Scheduler einrichten
# ---------------------------------------------------------------------------
def setup_scheduler() -> BlockingScheduler:
    tz = pytz.timezone(config.TIMEZONE)
    scheduler = BlockingScheduler(timezone=tz)

    # Pre-Market: 14:00 und 15:00 Mo-Fr
    scheduler.add_job(
        job_premarket_check,
        CronTrigger(day_of_week="mon-fri", hour=14, minute=0, timezone=tz),
        id="premarket_1400",
        name="Pre-Market 14:00",
    )
    scheduler.add_job(
        job_premarket_check,
        CronTrigger(day_of_week="mon-fri", hour=15, minute=0, timezone=tz),
        id="premarket_1500",
        name="Pre-Market 15:00",
    )

    # Intraday: alle 15 Minuten Mo-Fr 15:30–21:45
    scheduler.add_job(
        job_intraday_check,
        CronTrigger(
            day_of_week="mon-fri",
            hour="15-21",
            minute="30,45",
            timezone=tz,
        ),
        id="intraday_half",
        name="Intraday :30/:45",
    )
    scheduler.add_job(
        job_intraday_check,
        CronTrigger(
            day_of_week="mon-fri",
            hour="16-21",
            minute="0,15",
            timezone=tz,
        ),
        id="intraday_full",
        name="Intraday :00/:15",
    )

    # Daily Summary: 22:30 Mo-Fr
    scheduler.add_job(
        job_daily_summary,
        CronTrigger(
            day_of_week="mon-fri",
            hour=config.DAILY_SUMMARY_HOUR,
            minute=config.DAILY_SUMMARY_MINUTE,
            timezone=tz,
        ),
        id="daily_summary",
        name="Daily Summary",
    )

    # Weekend Check: Sa 10:00
    scheduler.add_job(
        job_weekend_check,
        CronTrigger(
            day_of_week="sat",
            hour=config.WEEKEND_CHECK_HOUR,
            minute=config.WEEKEND_CHECK_MINUTE,
            timezone=tz,
        ),
        id="weekend_check",
        name="Weekend Check",
    )

    return scheduler


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    logger.info("=" * 50)
    logger.info("StockCRASH_WarnAPP gestartet")
    logger.info(f"Zeitzone: {config.TIMEZONE}")
    logger.info("=" * 50)

    if not validate_config():
        logger.error("Konfiguration unvollständig — App beendet. Bitte .env befüllen.")
        sys.exit(1)

    # Startup-Test
    logger.info("Sende Test-Notification...")
    if notifier.send_test_notification():
        logger.info("✅ Pushover Verbindung OK")
    else:
        logger.error("❌ Pushover Verbindung fehlgeschlagen — prüfe PUSHOVER_APP_TOKEN und PUSHOVER_USER_KEY")

    scheduler = setup_scheduler()
    logger.info("Scheduler Jobs:")
    for job in scheduler.get_jobs():
        logger.info(f"  • {job.name}: {job.trigger}")

    logger.info("Scheduler läuft — warte auf nächsten Job... (Ctrl+C zum Beenden)")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("App manuell gestoppt")
    except Exception as e:
        logger.error(f"Unerwarteter Fehler: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Kommandozeilen-Argumente
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "--test":
            # Sofortiger Test-Check ohne Scheduler
            logging.basicConfig(level=logging.INFO, handlers=[console_handler])
            logger.info("=== MANUELLER TEST-CHECK ===")
            alert = alert_engine.run_all_checks(include_futures=True)
            for line in alert.summary_lines():
                print(line)
            print(f"\nGesamtpunktzahl: {alert.total_score}")
        elif cmd == "--notify-test":
            logging.basicConfig(level=logging.INFO, handlers=[console_handler])
            validate_config()
            success = notifier.send_test_notification()
            print("✅ Test-Notification gesendet!" if success else "❌ Fehler beim Senden")
        else:
            print(f"Unbekanntes Argument: {cmd}")
            print("Verwendung: python main.py [--test | --notify-test]")
    else:
        main()
