"""
put_call_ratio.py — CBOE Total Put/Call Ratio
Quelle: CBOE öffentliche Daten
Hoher Wert = mehr Puts = Absicherung/Panik im Markt
"""

import logging
import requests
import config
from indicators.base import IndicatorResult

logger = logging.getLogger(__name__)

# CBOE stellt tägliche Put/Call Ratio Daten als CSV bereit
CBOE_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/PC_TOTAL.csv"
HEADERS  = {"User-Agent": "Mozilla/5.0 (compatible; StockCrashWarn/1.0)"}


def get_signal() -> IndicatorResult:
    """Liest die aktuelle CBOE Put/Call Ratio."""
    try:
        resp = requests.get(CBOE_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        lines  = resp.text.strip().splitlines()
        # Format: DATE,PC_RATIO
        # Letzte Zeile = neuester Wert
        valid_lines = [l for l in lines[1:] if l.strip() and "," in l]
        if not valid_lines:
            raise ValueError("Keine gültigen P/C Ratio Daten")

        last_line = valid_lines[-1]
        date_str, ratio_str = last_line.split(",")[:2]
        ratio = float(ratio_str.strip())

        if ratio >= config.PUT_CALL_RED:
            return IndicatorResult(
                name="Put/Call Ratio",
                value=ratio,
                status="red",
                score=config.SCORE_PER_RED,
                message=f"P/C={ratio:.2f} 🔴 — starke Absicherung (Stand: {date_str.strip()})"
            )
        elif ratio >= config.PUT_CALL_YELLOW:
            return IndicatorResult(
                name="Put/Call Ratio",
                value=ratio,
                status="yellow",
                score=config.SCORE_PER_YELLOW,
                message=f"P/C={ratio:.2f} 🟡 — erhöhte Absicherung (Stand: {date_str.strip()})"
            )
        else:
            return IndicatorResult(
                name="Put/Call Ratio",
                value=ratio,
                status="green",
                score=0,
                message=f"P/C={ratio:.2f} — normal (Stand: {date_str.strip()})"
            )

    except Exception as e:
        logger.error(f"Put/Call Ratio Fehler: {e}")
        return IndicatorResult(
            name="Put/Call Ratio",
            value=None,
            status="error",
            score=0,
            message=f"Datenfehler: {e}"
        )
