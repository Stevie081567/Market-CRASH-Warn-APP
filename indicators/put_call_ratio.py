"""
put_call_ratio.py — CBOE Total Put/Call Ratio
Quellen (in Reihenfolge):
  1. CBOE JSON API  (zuverlässigste Quelle)
  2. CBOE CSV       (manchmal 403)
  3. Stooq.com      (^cpc, URL-encoded)
Hoher Wert = mehr Puts = Absicherung/Panik im Markt
"""

import logging
import requests
import yfinance as yf
import config
from indicators.base import IndicatorResult

logger = logging.getLogger(__name__)

# CBOE öffentliche Endpunkte
CBOE_JSON_URL = "https://cdn.cboe.com/api/global/delayed_quotes/options/PC_TOTAL.json"
CBOE_CSV_URL  = "https://cdn.cboe.com/api/global/us_indices/daily_prices/PC_TOTAL.csv"
# Stooq: ^ muss URL-encoded sein
STOOQ_URL     = "https://stooq.com/q/d/l/?s=%5Ecpc&i=d"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept":     "application/json, text/plain, */*",
    "Referer":    "https://www.cboe.com/",
}


def _get_via_cboe_json() -> tuple[float, str]:
    """Holt Put/Call Ratio vom CBOE JSON-Endpunkt (zuverlässigste Quelle)."""
    resp = requests.get(CBOE_JSON_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    # Struktur: {"data": {"pcRatio": 0.87, "date": "2026-06-01", ...}}
    inner = data.get("data", data)
    ratio = float(inner.get("pcRatio") or inner.get("pc_ratio") or inner.get("ratio", 0))
    date  = str(inner.get("date", "aktuell"))[:10]

    if not (0.3 < ratio < 3.0):
        raise ValueError(f"CBOE JSON: ungültiger Wert {ratio}")

    return ratio, date


def _get_via_cboe_csv() -> tuple[float, str]:
    """Holt Put/Call Ratio direkt vom CBOE CSV-Endpunkt."""
    resp = requests.get(CBOE_CSV_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    lines = resp.text.strip().splitlines()
    valid = [l for l in lines[1:] if l.strip() and "," in l]
    if not valid:
        raise ValueError("CBOE CSV: keine gültigen Daten")

    parts    = valid[-1].split(",")
    date_str = parts[0].strip()
    ratio    = float(parts[1].strip())

    if not (0.3 < ratio < 3.0):
        raise ValueError(f"CBOE CSV: ungültiger Wert {ratio}")

    return ratio, date_str


def _get_via_stooq() -> float:
    """Holt Put/Call Ratio von stooq.com (^ URL-encoded als %5E)."""
    resp = requests.get(STOOQ_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    lines = resp.text.strip().splitlines()
    if len(lines) < 2:
        raise ValueError(f"Stooq: zu wenig Zeilen ({len(lines)})")

    # Format: Date,Open,High,Low,Close  → Close = index 4
    valid = []
    for line in lines[1:]:
        parts = line.strip().split(",")
        if len(parts) >= 5 and "N/D" not in line:
            for idx in (4, 1):   # Close zuerst, dann Open als Fallback
                try:
                    val = float(parts[idx])
                    if 0.3 < val < 3.0:
                        valid.append(val)
                        break
                except (ValueError, IndexError):
                    continue

    if not valid:
        raise ValueError("Stooq: keine gültigen Werte gefunden")

    return valid[-1]


def get_signal() -> IndicatorResult:
    """Liest die aktuelle CBOE Put/Call Ratio — 3 Fallback-Quellen."""
    ratio    = None
    date_str = "aktuell"
    source   = ""

    # 1. CBOE JSON (bevorzugt)
    try:
        ratio, date_str = _get_via_cboe_json()
        source = "CBOE JSON"
    except Exception as e:
        logger.warning(f"Put/Call CBOE JSON fehlgeschlagen: {e}")

    # 2. CBOE CSV
    if ratio is None:
        try:
            ratio, date_str = _get_via_cboe_csv()
            source = "CBOE CSV"
        except Exception as e:
            logger.warning(f"Put/Call CBOE CSV fehlgeschlagen: {e}")

    # 3. Stooq
    if ratio is None:
        try:
            ratio  = _get_via_stooq()
            source = "Stooq"
        except Exception as e:
            logger.error(f"Put/Call alle Quellen fehlgeschlagen: {e}")
            return IndicatorResult(
                name="Put/Call Ratio",
                value=None,
                status="error",
                score=0,
                message="Datenfehler: alle Quellen nicht erreichbar"
            )

    logger.info(f"Put/Call Ratio={ratio:.2f} via {source} (Stand: {date_str})")

    if ratio >= config.PUT_CALL_RED:
        return IndicatorResult(
            name="Put/Call Ratio",
            value=ratio,
            status="red",
            score=config.SCORE_PER_RED,
            message=f"P/C={ratio:.2f} 🔴 starke Absicherung [{source}, {date_str}]"
        )
    elif ratio >= config.PUT_CALL_YELLOW:
        return IndicatorResult(
            name="Put/Call Ratio",
            value=ratio,
            status="yellow",
            score=config.SCORE_PER_YELLOW,
            message=f"P/C={ratio:.2f} 🟡 erhöhte Absicherung [{source}, {date_str}]"
        )
    else:
        return IndicatorResult(
            name="Put/Call Ratio",
            value=ratio,
            status="green",
            score=0,
            message=f"P/C={ratio:.2f} normal [{source}, {date_str}]"
        )
