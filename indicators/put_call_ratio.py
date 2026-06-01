"""
put_call_ratio.py — CBOE Total Put/Call Ratio
Quellen (in Reihenfolge):
  1. Stooq.com  (^cpc)
  2. CBOE CSV   (manchmal 403)
  3. Wallstreetmojo / Wisesheets via yfinance Ticker "^PCALL"
Hoher Wert = mehr Puts = Absicherung/Panik im Markt
"""

import logging
import requests
import yfinance as yf
import config
from indicators.base import IndicatorResult

logger = logging.getLogger(__name__)

CBOE_URL  = "https://cdn.cboe.com/api/global/us_indices/daily_prices/PC_TOTAL.csv"
STOOQ_URL = "https://stooq.com/q/d/l/?s=^cpc&i=d"
HEADERS   = {"User-Agent": "Mozilla/5.0 (compatible; StockCrashWarn/1.0)"}


def _get_via_stooq() -> float:
    """Holt Put/Call Ratio von stooq.com."""
    resp = requests.get(STOOQ_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    lines = resp.text.strip().splitlines()
    if len(lines) < 2:
        raise ValueError(f"Stooq: zu wenig Zeilen ({len(lines)})")

    # Überspringe Header, finde letzte gültige Zeile
    valid = []
    for line in lines[1:]:
        parts = line.strip().split(",")
        if len(parts) >= 5 and "N/D" not in line and parts[4].strip():
            try:
                val = float(parts[4])
                if 0.3 < val < 3.0:
                    valid.append(val)
            except ValueError:
                continue

    if not valid:
        raise ValueError("Stooq: keine gültigen Werte gefunden")

    return valid[-1]


def _get_via_cboe_csv() -> tuple:
    """Holt Put/Call Ratio direkt vom CBOE CSV-Endpunkt."""
    resp = requests.get(CBOE_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    lines = resp.text.strip().splitlines()
    valid = [l for l in lines[1:] if l.strip() and "," in l]
    if not valid:
        raise ValueError("CBOE CSV: keine gültigen Daten")

    parts    = valid[-1].split(",")
    date_str = parts[0].strip()
    ratio    = float(parts[1].strip())
    return ratio, date_str


def _get_via_yfinance() -> float:
    """Versucht Put/Call Ratio über verschiedene yfinance Symbole."""
    for symbol in ("^PCALL", "^PCEALL", "PCALL"):
        try:
            ticker = yf.Ticker(symbol)
            data   = ticker.history(period="5d")
            if not data.empty:
                val = float(data["Close"].iloc[-1])
                if 0.3 < val < 3.0:
                    logger.debug(f"Put/Call via yfinance {symbol}: {val}")
                    return val
        except Exception:
            continue
    raise ValueError("yfinance: kein gültiges Put/Call Symbol gefunden")


def get_signal() -> IndicatorResult:
    """Liest die aktuelle CBOE Put/Call Ratio."""
    ratio    = None
    date_str = "aktuell"
    source   = ""

    # 1. Stooq
    try:
        ratio  = _get_via_stooq()
        source = "Stooq"
    except Exception as e:
        logger.warning(f"Put/Call Stooq fehlgeschlagen: {e}")

    # 2. CBOE CSV
    if ratio is None:
        try:
            ratio, date_str = _get_via_cboe_csv()
            source = "CBOE"
        except Exception as e:
            logger.warning(f"Put/Call CBOE CSV fehlgeschlagen: {e}")

    # 3. yfinance
    if ratio is None:
        try:
            ratio  = _get_via_yfinance()
            source = "yfinance"
        except Exception as e:
            logger.error(f"Put/Call alle Quellen fehlgeschlagen: {e}")
            return IndicatorResult(
                name="Put/Call Ratio",
                value=None,
                status="error",
                score=0,
                message="Datenfehler: alle Quellen nicht erreichbar"
            )

    logger.debug(f"Put/Call Ratio={ratio:.2f} via {source}")

    if ratio >= config.PUT_CALL_RED:
        return IndicatorResult(
            name="Put/Call Ratio",
            value=ratio,
            status="red",
            score=config.SCORE_PER_RED,
            message=f"P/C={ratio:.2f} 🔴 — starke Absicherung (Stand: {date_str})"
        )
    elif ratio >= config.PUT_CALL_YELLOW:
        return IndicatorResult(
            name="Put/Call Ratio",
            value=ratio,
            status="yellow",
            score=config.SCORE_PER_YELLOW,
            message=f"P/C={ratio:.2f} 🟡 — erhöhte Absicherung (Stand: {date_str})"
        )
    else:
        return IndicatorResult(
            name="Put/Call Ratio",
            value=ratio,
            status="green",
            score=0,
            message=f"P/C={ratio:.2f} — normal (Stand: {date_str})"
        )
