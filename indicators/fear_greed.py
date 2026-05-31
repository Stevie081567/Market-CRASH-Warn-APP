"""
fear_greed.py — CNN Fear & Greed Index
Quelle: CNN inoffizieller API-Endpunkt
0 = Extreme Fear, 100 = Extreme Greed
"""

import logging
import requests
from indicators.base import IndicatorResult
import config

logger = logging.getLogger(__name__)

CNN_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; StockCrashWarn/1.0)",
    "Referer": "https://edition.cnn.com/markets/fear-and-greed",
}


def get_signal() -> IndicatorResult:
    """Ruft den aktuellen CNN Fear & Greed Index ab."""
    try:
        resp = requests.get(CNN_URL, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data  = resp.json()
        score_data = data.get("fear_and_greed", {})
        value = float(score_data.get("score", -1))
        label = score_data.get("rating", "Unknown")

        if value < 0:
            raise ValueError("Ungültiger Fear & Greed Wert")

        if value <= config.FEAR_GREED_RED:
            return IndicatorResult(
                name="Fear & Greed Index",
                value=value,
                status="red",
                score=config.SCORE_PER_RED,
                message=f"F&G={value:.0f} ({label}) — EXTREME FEAR 🔴"
            )
        elif value <= config.FEAR_GREED_YELLOW:
            return IndicatorResult(
                name="Fear & Greed Index",
                value=value,
                status="yellow",
                score=config.SCORE_PER_YELLOW,
                message=f"F&G={value:.0f} ({label}) — Angst im Markt 🟡"
            )
        else:
            return IndicatorResult(
                name="Fear & Greed Index",
                value=value,
                status="green",
                score=0,
                message=f"F&G={value:.0f} ({label})"
            )

    except Exception as e:
        logger.error(f"Fear & Greed Fehler: {e}")
        return IndicatorResult(
            name="Fear & Greed Index",
            value=None,
            status="error",
            score=0,
            message=f"Datenfehler: {e}"
        )
