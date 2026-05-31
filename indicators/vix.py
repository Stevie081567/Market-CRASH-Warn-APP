"""
vix.py — CBOE VIX Fear Index
Quelle: Yahoo Finance (^VIX), 15-Min-Delay
"""

import logging
import yfinance as yf
import config
from indicators.base import IndicatorResult

logger = logging.getLogger(__name__)


def get_signal() -> IndicatorResult:
    """Liest den aktuellen VIX-Stand und bewertet ihn."""
    try:
        ticker = yf.Ticker("^VIX")
        data   = ticker.history(period="1d", interval="5m")

        if data.empty:
            raise ValueError("Keine VIX-Daten erhalten")

        vix = float(data["Close"].iloc[-1])

        if vix >= config.VIX_RED:
            return IndicatorResult(
                name="VIX Fear Index",
                value=vix,
                status="red",
                score=config.SCORE_PER_RED,
                message=f"VIX={vix:.1f} — CRASH-ALARM (Schwelle: {config.VIX_RED})"
            )
        elif vix >= config.VIX_YELLOW:
            return IndicatorResult(
                name="VIX Fear Index",
                value=vix,
                status="yellow",
                score=config.SCORE_PER_YELLOW,
                message=f"VIX={vix:.1f} — erhöhte Volatilität (Schwelle: {config.VIX_YELLOW})"
            )
        else:
            return IndicatorResult(
                name="VIX Fear Index",
                value=vix,
                status="green",
                score=0,
                message=f"VIX={vix:.1f} — normal"
            )

    except Exception as e:
        logger.error(f"VIX Fehler: {e}")
        return IndicatorResult(
            name="VIX Fear Index",
            value=None,
            status="error",
            score=0,
            message=f"Datenfehler: {e}"
        )
