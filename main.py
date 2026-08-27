"""
main.py — StockCRASH_WarnAPP Einstiegspunkt
Startet den APScheduler mit allen Markt-Überwachungs-Jobs.

Alle Zeiten in Eastern Time (ET) — NYSE-zentriert.

Notification-Filter (Spam-Schutz):
  ROT    → sofort, immer
  GELB   → nur wenn Score >= NOTIFY_YELLOW_MIN_SCORE (5)
             UND 2x hintereinander bestätigt
  Cooldown → min. NOTIFY_COOLDOWN_MINUTES (120) zwischen Notifications
  Daily Summary → deaktiviert (nur echte Alarme)
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
# Logging
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
# Gemeinsame Notification-Logik
# ---------------------------------------------------------------------------
def _handle_notification(alert, job_name: str) -> None:
    """
    Zentrale Entscheidung ob eine Pushover-Notification gesendet wird.
    Verwendet should_notify() aus state_manager mit allen Filtern.
    """
    # Status immer aktualisieren (für Streak + Dashboard)
    state_manager.set_status(alert.status)
    update_dashboard(alert)

    send, reason = state_manager.should_notify(alert.status, alert.total_score)

    if send:
        logger.info(f"[{job_name}] Notification senden: {reason}")
        notifier.send_alert(alert)
        state_manager.mark_notified(alert.status)
    else:
        logger.info(f"[{job_name}] Notification unterdrückt: {reason}")


# ---------------------------------------------------------------------------
# Job-Funktionen
# ---------------------------------------------------------------------------
def job_premarket_check():
    """Pre-Market: Futures + globale Märkte vor NYSE-Öffnung."""
    tz  = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tz)
    logger.info(f"=== PRE-MARKET CHECK {now.strftime('%H:%M ET')} ===")

    alert = alert_engine.run_all_checks(include_futures=True)
    logger.info(
        f"Status: {alert.status.upper()} | Score: {alert.total_score} | "
        f"🔴{alert.red_count} 🟡{alert.yellow_count} 🟢{alert.green_count}"
    )
    _handle_notification(alert, "PRE-MARKET")


def job_intraday_check():
    """Intraday: alle 15 Minuten."""
    tz  = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tz)
    logger.info(f"=== INTRADAY CHECK {now.strftime('%H:%M ET')} ===")

    alert = alert_engine.run_all_checks(include_futures=True)
    logger.info(
        f"Status: {alert.status.upper()} | Score: {alert.total_score} | "
        f"🔴{alert.red_count} 🟡{alert.yellow_count} 🟢{alert.green_count}"
    )
    _handle_notification(alert, "INTRADAY")


def job_weekend_check():
    """Samstags 10:00 ET — nur bei echtem Alarm."""
    logger.info("=== WEEKEND CHECK ===")
    alert = alert_engine.run_all_checks(include_futures=False)
    logger.info(f"Status: {alert.status.upper()} | Score: {alert.total_score}")
    _handle_notification(alert, "WEEKEND")


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------
def setup_scheduler() -> BlockingScheduler:
    tz        = pytz.timezone(config.TIMEZONE)
    scheduler = BlockingScheduler(timezone=tz)

    # Pre-Market: 08:00 und 09:00 ET Mo-Fr
    scheduler.add_job(
        job_premarket_check,
        CronTrigger(day_of_week="mon-fri", hour=8, minute=0, timezone=tz),
        id="premarket_0800", name="Pre-Market 08:00 ET",
    )
    scheduler.add_job(
        job_premarket_check,
        CronTrigger(day_of_week="mon-fri", hour=9, minute=0, timezone=tz),
        id="premarket_0900", name="Pre-Market 09:00 ET",
    )

    # Intraday: alle 15 Min Mo-Fr 09:30–15:45 ET
    scheduler.add_job(
        job_intraday_check,
        CronTrigger(day_of_week="mon-fri", hour="9-15", minute="30,45", timezone=tz),
        id="intraday_half", name="Intraday :30/:45 ET",
    )
    scheduler.add_job(
        job_intraday_check,
        CronTrigger(day_of_week="mon-fri", hour="10-15", minute="0,15", timezone=tz),
        id="intraday_full", name="Intraday :00/:15 ET",
    )

    # Weekend: Sa 10:00 ET
    scheduler.add_job(
        job_weekend_check,
        CronTrigger(day_of_week="sat", hour=config.WEEKEND_CHECK_HOUR,
                    minute=config.WEEKEND_CHECK_MINUTE, timezone=tz),
        id="weekend_check", name="Weekend Check 10:00 ET",
    )

    return scheduler


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    tz  = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tz)
    logger.info("=" * 55)
    logger.info("StockCRASH_WarnAPP gestartet")
    logger.info(f"NYSE-Zeit: {now.strftime('%Y-%m-%d %H:%M ET')}")
    logger.info(f"Notification-Filter:")
    logger.info(f"  ROT    → sofort")
    logger.info(f"  GELB   → Score >= {config.NOTIFY_YELLOW_MIN_SCORE} + {config.NOTIFY_YELLOW_CONFIRM}x bestätigt")
    logger.info(f"  Cooldown → {config.NOTIFY_COOLDOWN_MINUTES} Min")
    logger.info(f"  Daily Summary → deaktiviert")
    logger.info("=" * 55)

    if not validate_config():
        logger.error("Konfiguration unvollständig — App beendet.")
        sys.exit(1)

    logger.info("Sende Test-Notification...")
    if notifier.send_test_notification():
        logger.info("✅ Pushover OK")
    else:
        logger.error("❌ Pushover fehlgeschlagen")

    scheduler = setup_scheduler()
    logger.info("Scheduler Jobs (ET):")
    for job in scheduler.get_jobs():
        logger.info(f"  • {job.name}")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("App manuell gestoppt")
    except Exception as e:
        logger.error(f"Fehler: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "--test":
            logging.basicConfig(level=logging.INFO, handlers=[console_handler])
            logger.info("=== MANUELLER TEST-CHECK ===")
            alert = alert_engine.run_all_checks(include_futures=True)
            update_dashboard(alert)
            state_manager.set_status(alert.status)
            for line in alert.summary_lines():
                print(line)
            print(f"\nTotal Score: {alert.total_score}")

            # Notification-Entscheidung anzeigen
            send, reason = state_manager.should_notify(alert.status, alert.total_score)
            print(f"Notification: {'✅ würde senden' if send else '🔕 unterdrückt'} — {reason}")
            print("✅ state.json aktualisiert")

        elif cmd == "--notify-test":
            logging.basicConfig(level=logging.INFO, handlers=[console_handler])
            validate_config()
            success = notifier.send_test_notification()
            print("✅ Test-Notification gesendet!" if success else "❌ Fehler")

        elif cmd == "--filter-status":
            # Zeigt aktuellen Filter-Status an
            logging.basicConfig(level=logging.INFO, handlers=[console_handler])
            last_notify = state_manager.get_last_notification_time()
            streak      = state_manager.get_yellow_streak()
            print(f"Letzter Status:       {state_manager.get_last_status().upper()}")
            print(f"Letzte Notification:  {last_notify.strftime('%Y-%m-%d %H:%M') if last_notify else 'nie'}")
            print(f"Yellow Streak:        {streak}")
            if last_notify:
                elapsed = (datetime.now() - last_notify).total_seconds() / 60
                remaining = max(0, config.NOTIFY_COOLDOWN_MINUTES - elapsed)
                print(f"Cooldown verbleibend: {remaining:.0f} Min")
        else:
            print(f"Unbekanntes Argument: {cmd}")
            print("Verwendung: python main.py [--test | --notify-test | --filter-status]")
    else:
        main()
