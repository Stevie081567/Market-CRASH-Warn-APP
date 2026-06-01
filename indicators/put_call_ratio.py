"""
put_call_ratio.py — CBOE Total Put/Call Ratio
Primär: yfinance (^PCCE oder ^CPC)
Fallback: CBOE CSV (kann 403 liefern)
Hoher Wert = mehr Puts = Absicherung/Panik im Markt
"""

import logging
import requests
import yfinance as yf
import config
from indicators.base import IndicatorResult

logger = logging.getLogger(__name__)

CBOE_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/PC_TOTAL.csv"
HEADERS  = {"User-Agent": "Mozilla/5.0 (compatible; StockCrashWarn/1.0)"}


def _get_via_yfinance() -> float:
    """
    Holt Put/Call Ratio via yfinance.
    ^PCCE = CBOE Equity Put/Call Ratio
    ^CPC  = CBOE Total Put/Call Ratio
    """
    for symbol in ("^PCCE", "^CPC"):
        try:
            ticker = yf.Ticker(symbol)
            data   = ticker.history(period="5d")
            if not data.empty:
                ratio = float(data["Close"].iloc[-1])
                if 0.3 < ratio < 3.0:   # Plausibilitäts-Check
                    logger.debug(f"Put/Call Ratio via yfinance ({symbol}): {ratio}")
                    return ratio
        except Exception as e:
            logger.debug(f"yfinance {symbol} fehlgeschlagen: {e}")
    raise ValueError("Keine Put/Call Ratio Daten via yfinance")


def _get_via_cboe_csv() -> tuple[float, str]:
    """Holt Put/Call Ratio direkt vom CBOE CSV-Endpunkt."""
    resp = requests.get(CBOE_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    lines = resp.text.strip().splitlines()
    valid_lines = [l for l in lines[1:] if l.strip() and "," in l]
    if not valid_lines:
        raise ValueError("Keine gültigen P/C Ratio Daten")

    last_line = valid_lines[-1]
    date_str, ratio_str = last_line.split(",")[:2]
    return float(ratio_str.strip()), date_str.strip()


def get_signal() -> IndicatorResult:
    """Liest die aktuelle CBOE Put/Call Ratio."""
    ratio    = None
    date_str = "aktuell"

    # Primär: yfinance
    try:
        ratio = _get_via_yfinance()
    except Exception as e:
        logger.warning(f"Put/Call yfinance fehlgeschlagen: {e} — versuche CBOE CSV")

    # Fallback: CBOE CSV
    if ratio is None:
        try:
            ratio, date_str = _get_via_cboe_csv()
        except Exception as e:
            logger.error(f"Put/Call Ratio Fehler (beide Quellen): {e}")
            return IndicatorResult(
                name="Put/Call Ratio",
                value=None,
                status="error",
                score=0,
                message=f"Datenfehler: CBOE & yfinance nicht erreichbar"
            )

    try:
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

    except Exception as e:
        logger.error(f"Put/Call Ratio Bewertung fehlgeschlagen: {e}")
        return IndicatorResult(
            name="Put/Call Ratio",
            value=None,
            status="error",
            score=0,
            message=f"Datenfehler: {e}"
        )
