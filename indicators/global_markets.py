"""
global_markets.py — Asiatische & Europäische Indizes
Früherkennung durch Marktbewegungen vor US-Öffnung.
Quelle: Yahoo Finance
"""

import logging
import yfinance as yf
import config
from indicators.base import IndicatorResult

logger = logging.getLogger(__name__)


def _get_daily_change(symbol: str) -> float | None:
    """Berechnet die prozentuale Tagesveränderung eines Index."""
    try:
        ticker = yf.Ticker(symbol)
        data   = ticker.history(period="2d")

        if len(data) < 2:
            return None

        prev_close = float(data["Close"].iloc[-2])
        last_close = float(data["Close"].iloc[-1])
        return ((last_close - prev_close) / prev_close) * 100

    except Exception as e:
        logger.warning(f"Global Markets {symbol} Fehler: {e}")
        return None


def get_signal() -> IndicatorResult:
    """Bewertet globale Märkte anhand des Durchschnitts aller verfügbaren Indizes."""
    changes    = {}
    all_symbols = {**config.ASIAN_INDICES, **config.EUROPEAN_INDICES}

    for symbol, name in all_symbols.items():
        change = _get_daily_change(symbol)
        if change is not None:
            changes[name] = change

    if not changes:
        return IndicatorResult(
            name="Globale Märkte",
            value=None,
            status="error",
            score=0,
            message="Keine globalen Marktdaten verfügbar"
        )

    avg_change = sum(changes.values()) / len(changes)

    # Top-Verlierer für Details
    sorted_changes = sorted(changes.items(), key=lambda x: x[1])
    worst = sorted_changes[:3]
    details = " | ".join(f"{n.split('(')[0].strip()}: {v:+.1f}%" for n, v in worst)

    if avg_change <= config.GLOBAL_MARKETS_RED:
        return IndicatorResult(
            name="Globale Märkte",
            value=avg_change,
            status="red",
            score=config.SCORE_PER_RED,
            message=f"Ø {avg_change:+.1f}% 🔴 | Schlimmste: {details}"
        )
    elif avg_change <= config.GLOBAL_MARKETS_YELLOW:
        return IndicatorResult(
            name="Globale Märkte",
            value=avg_change,
            status="yellow",
            score=config.SCORE_PER_YELLOW,
            message=f"Ø {avg_change:+.1f}% 🟡 | Schlimmste: {details}"
        )
    else:
        return IndicatorResult(
            name="Globale Märkte",
            value=avg_change,
            status="green",
            score=0,
            message=f"Ø {avg_change:+.1f}% — {details}"
        )
