"""
config.py — Zentrale Konfiguration für StockCRASH_WarnAPP
Alle Schwellenwerte, Zeitfenster und API-Endpunkte hier ändern.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Pushover
# ---------------------------------------------------------------------------
PUSHOVER_APP_TOKEN = os.getenv("PUSHOVER_APP_TOKEN", "")
PUSHOVER_USER_KEY  = os.getenv("PUSHOVER_USER_KEY", "")
PUSHOVER_API_URL   = "https://api.pushover.net/1/messages.json"

# ---------------------------------------------------------------------------
# FRED API
# ---------------------------------------------------------------------------
FRED_API_KEY  = os.getenv("FRED_API_KEY", "")
FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

# ---------------------------------------------------------------------------
# Zeitzone
# ---------------------------------------------------------------------------
TIMEZONE = os.getenv("TIMEZONE", "Europe/Berlin")

# ---------------------------------------------------------------------------
# Scheduler-Zeitfenster (Berlin-Zeit, 24h)
# ---------------------------------------------------------------------------
PREMARKET_START_HOUR   = 14   # 14:00 Uhr
PREMARKET_START_MINUTE = 0
PREMARKET_END_HOUR     = 15
PREMARKET_END_MINUTE   = 30

MARKET_START_HOUR   = 15
MARKET_START_MINUTE = 30
MARKET_END_HOUR     = 22
MARKET_END_MINUTE   = 0

INTRADAY_INTERVAL_MINUTES = 15  # Check alle 15 Minuten

DAILY_SUMMARY_HOUR   = 22
DAILY_SUMMARY_MINUTE = 30

WEEKEND_CHECK_HOUR   = 10
WEEKEND_CHECK_MINUTE = 0

# ---------------------------------------------------------------------------
# VIX Schwellenwerte
# ---------------------------------------------------------------------------
VIX_YELLOW = 20.0   # Erhöhte Volatilität
VIX_RED    = 30.0   # Crash-Alarm

# ---------------------------------------------------------------------------
# S&P 500 Intraday-Drawdown (in %)
# ---------------------------------------------------------------------------
SP500_INTRADAY_YELLOW = 1.5   # -1.5% heute
SP500_INTRADAY_RED    = 3.0   # -3.0% heute

# S&P 500 vom Allzeithoch (ATH) in %
SP500_ATH_YELLOW = 5.0    # -5% vom ATH
SP500_ATH_RED    = 10.0   # -10% vom ATH (offiziell: Korrektur)

# ---------------------------------------------------------------------------
# Yield Curve (10Y - 2Y) in Prozentpunkten
# ---------------------------------------------------------------------------
YIELD_CURVE_YELLOW = 0.30   # < 0.30% → flache Kurve
YIELD_CURVE_RED    = 0.0    # Invertiert → Rezessionsindikator

# ---------------------------------------------------------------------------
# Fear & Greed Index (CNN) — 0=Extreme Fear, 100=Extreme Greed
# ---------------------------------------------------------------------------
FEAR_GREED_YELLOW = 35   # < 35 = Fear
FEAR_GREED_RED    = 20   # < 20 = Extreme Fear

# ---------------------------------------------------------------------------
# Put/Call Ratio (CBOE)
# ---------------------------------------------------------------------------
PUT_CALL_YELLOW = 1.0   # > 1.0 = mehr Puts als Calls
PUT_CALL_RED    = 1.3   # > 1.3 = starke Absicherung

# ---------------------------------------------------------------------------
# E-Mini Futures Pre-Market (%-Veränderung zum Vortag)
# ---------------------------------------------------------------------------
FUTURES_YELLOW = -0.5   # < -0.5%
FUTURES_RED    = -1.5   # < -1.5%

# Zu überwachende Futures-Symbole
FUTURES_SYMBOLS = {
    "ES=F": "S&P 500 E-Mini",
    "NQ=F": "Nasdaq E-Mini",
    "YM=F": "Dow Jones E-Mini",
}

# ---------------------------------------------------------------------------
# Buffett Indicator (Gesamtmarkt / BIP in %)
# ---------------------------------------------------------------------------
BUFFETT_YELLOW = 150.0   # > 150% = überbewertet
BUFFETT_RED    = 180.0   # > 180% = stark überbewertet

# ---------------------------------------------------------------------------
# Globale Märkte — durchschnittliche Tagesperformance in %
# ---------------------------------------------------------------------------
GLOBAL_MARKETS_YELLOW = -1.0   # ∅ > -1%
GLOBAL_MARKETS_RED    = -2.0   # ∅ > -2%

# Asiatische Indizes
ASIAN_INDICES = {
    "^N225":  "Nikkei 225 (Japan)",
    "^HSI":   "Hang Seng (Hongkong)",
    "^AXJO":  "ASX 200 (Australien)",
}

# Europäische Indizes
EUROPEAN_INDICES = {
    "^GDAXI": "DAX (Deutschland)",
    "^FCHI":  "CAC 40 (Frankreich)",
    "^FTSE":  "FTSE 100 (UK)",
    "^STOXX50E": "Euro Stoxx 50",
}

# ---------------------------------------------------------------------------
# Ampel-Scoring
# ---------------------------------------------------------------------------
# Punkte pro roter Indikator
SCORE_PER_RED    = 2
# Punkte pro gelber Indikator
SCORE_PER_YELLOW = 1

# Gesamtpunktzahl-Grenzen
STATUS_YELLOW_THRESHOLD = 3   # ab 3 Punkten → GELB
STATUS_RED_THRESHOLD    = 6   # ab 6 Punkten → ROT

# ---------------------------------------------------------------------------
# State-Datei (nicht in Git)
# ---------------------------------------------------------------------------
STATE_FILE = "state.json"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_FILE       = "logs/crashwarn.log"
LOG_MAX_BYTES  = 5 * 1024 * 1024   # 5 MB
LOG_BACKUP_COUNT = 7               # 7 Tage aufbewahren
