"""
put_call_ratio.py — CBOE Total Put/Call Ratio
Quellen (in Reihenfolge):
  1. Stooq.com CSV  (zuverlässig, kostenlos)
  2. CBOE CSV       (manchmal 403)
Hoher Wert = mehr Puts = Absicherung/Panik im Markt
"""

import logging
import requests
import config
from indicators.base import IndicatorResult

logger = logging.getLogger(__name__)

CBOE_URL  = "https://cdn.cboe.com/api/global/us_indices/daily_prices/PC_TOTAL.csv"
STOOQ_URL = "https://stooq.com/q/d/l/?s=^cpc&i=d"
HEADERS   = {"User-Agent": "Mozilla/5.0 (compatible; StockCrashWarn/1.0)"}


def _get_via_stooq() -> float:
    """Holt Put/Call Ratio von stooq.com (^CPC = CBOE Total Put/Call)."""
    resp = requests.get(STOOQ_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    lines = resp.text.strip().splitlines()
    # Format: Date,Open,High,Low,Close,Volume
    valid = [l for l in lines[1:] if l.strip() and "," in l and "N/D" not in l]
    if not valid:
        raise ValueError("Keine gültigen Stooq-Daten")

    last  = valid[-1].split(",")
    ratio = float(last[4])   # Close
    if not (0.3 < ratio < 3.0):
        raise ValueError(f"Stooq-Wert außerhalb Plausibilitätsbereich: {ratio}")
    return ratio


def _get_via_cboe_csv() -> tuple:
    """Holt Put/Call Ratio direkt vom CBOE CSV-Endpunkt."""
    resp = requests.get(CBOE_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    lines = resp.text.strip().splitlines()
    valid = [l for l in lines[1:] if l.strip() and "," in l]
    if not valid:
        raise ValueError("Keine gültigen CBOE CSV-Daten")

    last_line            = valid[-1]
    date_str, ratio_str  = last_line.split(",")[:2]
    return float(ratio_str.strip()), date_str.strip()


def get_signal() -> IndicatorResult:
    """Liest die aktuelle CBOE Put/Call Ratio."""
    ratio    = None
    date_str = "aktuell"

    # Primär: Stooq
    try:
        ratio = _get_via_stooq()
        logger.debug(f"Put/Call Ratio via Stooq: {ratio}")
    except Exception as e:
        logger.warning(f"Put/Call Stooq fehlgeschlagen: {e} — versuche CBOE CSV")

    # Fallback: CBOE CSV
    if ratio is None:
        try:
            ratio, date_str = _get_via_cboe_csv()
            logger.debug(f"Put/Call Ratio via CBOE CSV: {ratio}")
        except Exception as e:
            logger.error(f"Put/Call Ratio Fehler (beide Quellen): {e}")
            return IndicatorResult(
                name="Put/Call Ratio",
                value=None,
                status="error",
                score=0,
                message="Datenfehler: Stooq & CBOE nicht erreichbar"
            )

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
