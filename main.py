"""
main.py — StockCRASH_WarnAPP Einstiegspunkt
Startet den APScheduler mit allen Markt-Überwachungs-Jobs.

Alle Zeiten in Eastern Time (ET) — NYSE-zentriert.
Läuft korrekt auf jedem Server weltweit (Tokyo, Frankfurt, Sydney...).

Zeitfenster (ET):
  Pre-Market:     Mo-Fr 08:00 & 09:00 ET  (Futures + Global)
  Intraday:       Mo-Fr 09:30–16:00 ET    (alle 15 Min)
  Daily Summary:  Mo-Fr 16:30 ET          (nach Börsenschluss)
  Weekend Check:  Sa 10:00 ET
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
from dashboard_export import update_dashboard

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
    """Pre-Market: Futures + globale Märkte vor NYSE-Öffnung (ET)."""
    tz  = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tz)
    logger.info(f"=== PRE-MARKET CHECK {now.strftime('%H:%M ET')} ===")
    alert = alert_engine.run_all_checks(include_futures=True)
    update_dashboard(alert)
    logger.info(f"Status: {alert.status.upper()} | Score: {alert.total_score}")

    if alert.status in ("yellow", "red") or state_manager.status_changed(alert.status):
        notifier.send_alert(alert)
        state_manager.set_status(alert.status)
    else:
        logger.info("Status unverändert GRÜN — keine Notification")


def job_intraday_check():
    """Intraday: alle 15 Minuten — nur bei Statuswechsel Notification."""
    tz  = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tz)
    logger.info(f"=== INTRADAY CHECK {now.strftime('%H:%M ET')} ===")

    alert = alert_engine.run_all_checks(include_futures=True)
    update_dashboard(alert)
    logger.info(f"Status: {alert.status.upper()} | Score: {alert.total_score}")

    if state_manager.status_changed(alert.status):
        old_status = state_manager.get_last_status()
        logger.info(f"Statuswechsel: {old_status.upper()} → {alert.status.upper()}")
        notifier.send_alert(alert)
        state_manager.set_status(alert.status)
    else:
        logger.info(f"Status unverändert: {alert.status.upper()} — keine Notification")


def job_daily_summary():
    """Tägliche Zusammenfassung 16:30 ET — wird IMMER gesendet."""
    tz  = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tz)
    logger.info("=== DAILY SUMMARY ===")
    alert = alert_engine.run_all_checks(include_futures=False)
    update_dashboard(alert)

    title   = f"📊 Tages-Report: {alert.status_emoji()} {alert.status.upper()}"
    message = f"Tagesabschluss — {now.strftime('%d.%m.%Y %H:%M ET')}\n\n"
    message += alert.to_pushover_message()

    notifier.send_notification(
        title=title,
        message=message,
        status=alert.status,
    )
    state_manager.set_status(alert.status)
    logger.info("Daily Summary gesendet")


def job_weekend_check():
    """Samstags 10:00 ET: Wochenzusammenfassung."""
    tz  = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tz)
    logger.info("=== WEEKEND CHECK ===")
    alert = alert_engine.run_all_checks(include_futures=False)
    update_dashboard(alert)

    title   = f"📅 Wochen-Report: {alert.status_emoji()} {alert.status.upper()}"
    message = f"Wochenabschluss — {now.strftime('%d.%m.%Y %H:%M ET')}\n\n"
    message += alert.to_pushover_message()

    notifier.send_notification(
        title=title,
        message=message,
        status=alert.status,
    )
    logger.info("Weekend Summary gesendet")


# ---------------------------------------------------------------------------
# Scheduler einrichten — alle Zeiten in ET
# ---------------------------------------------------------------------------
def setup_scheduler() -> BlockingScheduler:
    tz        = pytz.timezone(config.TIMEZONE)
    scheduler = BlockingScheduler(timezone=tz)

    # Pre-Market: 08:00 und 09:00 ET Mo-Fr
    scheduler.add_job(
        job_premarket_check,
        CronTrigger(day_of_week="mon-fri", hour=8, minute=0, timezone=tz),
        id="premarket_0800",
        name="Pre-Market 08:00 ET",
    )
    scheduler.add_job(
        job_premarket_check,
        CronTrigger(day_of_week="mon-fri", hour=9, minute=0, timezone=tz),
        id="premarket_0900",
        name="Pre-Market 09:00 ET",
    )

    # Intraday: alle 15 Min Mo-Fr 09:30–15:45 ET
    scheduler.add_job(
        job_intraday_check,
        CronTrigger(
            day_of_week="mon-fri",
            hour="9-15",
            minute="30,45",
            timezone=tz,
        ),
        id="intraday_half",
        name="Intraday :30/:45 ET",
    )
    scheduler.add_job(
        job_intraday_check,
        CronTrigger(
            day_of_week="mon-fri",
            hour="10-15",
            minute="0,15",
            timezone=tz,
        ),
        id="intraday_full",
        name="Intraday :00/:15 ET",
    )

    # Daily Summary: 16:30 ET Mo-Fr
    scheduler.add_job(
        job_daily_summary,
        CronTrigger(
            day_of_week="mon-fri",
            hour=config.DAILY_SUMMARY_HOUR,
            minute=config.DAILY_SUMMARY_MINUTE,
            timezone=tz,
        ),
        id="daily_summary",
        name="Daily Summary 16:30 ET",
    )

    # Weekend Check: Sa 10:00 ET
    scheduler.add_job(
        job_weekend_check,
        CronTrigger(
            day_of_week="sat",
            hour=config.WEEKEND_CHECK_HOUR,
            minute=config.WEEKEND_CHECK_MINUTE,
            timezone=tz,
        ),
        id="weekend_check",
        name="Weekend Check 10:00 ET",
    )

    return scheduler


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    tz  = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tz)
    logger.info("=" * 50)
    logger.info("StockCRASH_WarnAPP gestartet")
    logger.info(f"Serverzeit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} lokal")
    logger.info(f"NYSE-Zeit:  {now.strftime('%Y-%m-%d %H:%M:%S ET')}")
    logger.info("=" * 50)

    if not validate_config():
        logger.error("Konfiguration unvollständig — App beendet.")
        sys.exit(1)

    logger.info("Sende Test-Notification...")
    if notifier.send_test_notification():
        logger.info("✅ Pushover Verbindung OK")
    else:
        logger.error("❌ Pushover Verbindung fehlgeschlagen")

    scheduler = setup_scheduler()
    logger.info("Scheduler Jobs (alle Zeiten ET):")
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
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "--test":
            logging.basicConfig(level=logging.INFO, handlers=[console_handler])
            logger.info("=== MANUELLER TEST-CHECK ===")
            alert = alert_engine.run_all_checks(include_futures=True)
            update_dashboard(alert)
            for line in alert.summary_lines():
                print(line)
            print(f"\nGesamtpunktzahl: {alert.total_score}")
            print("✅ state.json aktualisiert — dashboard.html im Browser öffnen")
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
