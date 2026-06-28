"""
config.py — Zentrale Konfiguration für StockCRASH_WarnAPP
Alle Schwellenwerte, Zeitfenster und API-Endpunkte hier ändern.

Zeitzone: America/New_York (ET) — fix, da alle Checks an NYSE-Zeiten
          gebunden sind. Läuft korrekt auf jedem Server weltweit.
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
# Alpaca API (Paper Trading)
# ---------------------------------------------------------------------------
ALPACA_API_KEY    = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_BASE_URL   = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

# ---------------------------------------------------------------------------
# Zeitzone — IMMER America/New_York (ET)
# Alle Scheduler-Jobs orientieren sich an NYSE-Öffnungszeiten.
# Kein Override via .env — die App ist NYSE-zentriert by design.
# ---------------------------------------------------------------------------
TIMEZONE = "America/New_York"

# ---------------------------------------------------------------------------
# Scheduler-Zeitfenster (Eastern Time, NYSE)
# ---------------------------------------------------------------------------
PREMARKET_START_HOUR   = 8    # 08:00 ET (Pre-Market beginnt)
PREMARKET_START_MINUTE = 0
PREMARKET_END_HOUR     = 9
PREMARKET_END_MINUTE   = 30

MARKET_START_HOUR   = 9    # 09:30 ET NYSE öffnet
MARKET_START_MINUTE = 30
MARKET_END_HOUR     = 16   # 16:00 ET NYSE schließt
MARKET_END_MINUTE   = 0

INTRADAY_INTERVAL_MINUTES = 15  # Check alle 15 Minuten

DAILY_SUMMARY_HOUR   = 16   # 16:30 ET — nach Börsenschluss
DAILY_SUMMARY_MINUTE = 30

WEEKEND_CHECK_HOUR   = 10   # 10:00 ET Samstag
WEEKEND_CHECK_MINUTE = 0

# ---------------------------------------------------------------------------
# VIX Schwellenwerte
# ---------------------------------------------------------------------------
VIX_YELLOW = 20.0
VIX_RED    = 30.0

# ---------------------------------------------------------------------------
# S&P 500 Intraday-Drawdown (in %)
# ---------------------------------------------------------------------------
SP500_INTRADAY_YELLOW = 1.5
SP500_INTRADAY_RED    = 3.0

SP500_ATH_YELLOW = 5.0
SP500_ATH_RED    = 10.0

# ---------------------------------------------------------------------------
# Yield Curve (10Y - 2Y) in Prozentpunkten
# ---------------------------------------------------------------------------
YIELD_CURVE_YELLOW = 0.30
YIELD_CURVE_RED    = 0.0

# ---------------------------------------------------------------------------
# Fear & Greed Index (CNN) — 0=Extreme Fear, 100=Extreme Greed
# Hinweis: CNN liefert 7-Tage-Durchschnitt
# ---------------------------------------------------------------------------
FEAR_GREED_YELLOW = 35
FEAR_GREED_RED    = 20

# ---------------------------------------------------------------------------
# Put/Call Ratio (CBOE via Stooq)
# ---------------------------------------------------------------------------
PUT_CALL_YELLOW = 1.0
PUT_CALL_RED    = 1.3

# ---------------------------------------------------------------------------
# E-Mini Futures Pre-Market (%-Veränderung zum Vortag)
# ---------------------------------------------------------------------------
FUTURES_YELLOW = -0.5
FUTURES_RED    = -1.5

FUTURES_SYMBOLS = {
    "ES=F": "S&P 500 E-Mini",
    "NQ=F": "Nasdaq E-Mini",
    "YM=F": "Dow Jones E-Mini",
}

# ---------------------------------------------------------------------------
# Buffett Indicator (Gesamtmarkt / BIP in %)
# ---------------------------------------------------------------------------
BUFFETT_YELLOW = 150.0
BUFFETT_RED    = 180.0

# ---------------------------------------------------------------------------
# Globale Märkte — durchschnittliche Tagesperformance in %
# ---------------------------------------------------------------------------
GLOBAL_MARKETS_YELLOW = -1.0
GLOBAL_MARKETS_RED    = -2.0

ASIAN_INDICES = {
    "^N225":  "Nikkei 225 (Japan)",
    "^HSI":   "Hang Seng (Hongkong)",
    "^AXJO":  "ASX 200 (Australien)",
}

EUROPEAN_INDICES = {
    "^GDAXI":    "DAX (Deutschland)",
    "^FCHI":     "CAC 40 (Frankreich)",
    "^FTSE":     "FTSE 100 (UK)",
    "^STOXX50E": "Euro Stoxx 50",
}

# ---------------------------------------------------------------------------
# Ampel-Scoring
# ---------------------------------------------------------------------------
SCORE_PER_RED    = 2
SCORE_PER_YELLOW = 1

STATUS_YELLOW_THRESHOLD = 3
STATUS_RED_THRESHOLD    = 6

# ---------------------------------------------------------------------------
# State-Datei (nicht in Git)
# ---------------------------------------------------------------------------
STATE_FILE = "state.json"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_FILE         = "logs/crashwarn.log"
LOG_MAX_BYTES    = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 7

# ---------------------------------------------------------------------------
# VVIX (Volatility of VIX)
# ---------------------------------------------------------------------------
VVIX_YELLOW = 100.0   # > 100 = erhöhte Unsicherheit
VVIX_RED    = 120.0   # > 120 = Panik-Regime

# ---------------------------------------------------------------------------
# MOVE Index (Bond Market Volatility)
# ---------------------------------------------------------------------------
MOVE_YELLOW = 100.0   # > 100 = erhöhter Bond-Stress
MOVE_RED    = 130.0   # > 130 = Bond-Markt unter starkem Druck

# ---------------------------------------------------------------------------
# SKEW Index (Tail Risk / Black Swan)
# ---------------------------------------------------------------------------
SKEW_YELLOW = 140.0   # > 140 = erhöhtes Tail-Risk
SKEW_RED    = 150.0   # > 150 = stark erhöhtes Black-Swan-Risiko

# ---------------------------------------------------------------------------
# SQQQ Volume Spike (vs. 20-Tage-Durchschnitt)
# ---------------------------------------------------------------------------
SQQQ_VOL_YELLOW = 2.0   # > 2.0x Durchschnitt = erhöhte Absicherung
SQQQ_VOL_RED    = 3.5   # > 3.5x Durchschnitt = institutionelle Absicherung
