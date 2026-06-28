"""
move_index.py — ICE BofA MOVE Index (Bond Market Volatility)
Misst die implizite Volatilität des US-Treasury-Markts.
Äquivalent zum VIX aber für Anleihen — wichtiger Stress-Indikator.
Quelle: Yahoo Finance (^MOVE)

Schwellenwerte:
  Gelb: > 100  (erhöhter Bond-Stress)
  Rot:  > 130  (Bond-Markt unter starkem Druck)
"""

import logging
import yfinance as yf
import config
from indicators.base import IndicatorResult

logger = logging.getLogger(__name__)


def get_signal() -> IndicatorResult:
    """Liest den aktuellen MOVE Index."""
    try:
        ticker = yf.Ticker("^MOVE")
        data   = ticker.history(period="5d")

        if data.empty:
            raise ValueError("Keine MOVE-Daten erhalten")

        move = float(data["Close"].iloc[-1])

        if move >= config.MOVE_RED:
            return IndicatorResult(
                name="MOVE Index (Bond Vol)",
                value=move,
                status="red",
                score=config.SCORE_PER_RED,
                message=f"MOVE={move:.1f} 🔴 — Bond market stress (threshold: {config.MOVE_RED})"
            )
        elif move >= config.MOVE_YELLOW:
            return IndicatorResult(
                name="MOVE Index (Bond Vol)",
                value=move,
                status="yellow",
                score=config.SCORE_PER_YELLOW,
                message=f"MOVE={move:.1f} 🟡 — Elevated bond volatility (threshold: {config.MOVE_YELLOW})"
            )
        else:
            return IndicatorResult(
                name="MOVE Index (Bond Vol)",
                value=move,
                status="green",
                score=0,
                message=f"MOVE={move:.1f} — Bond market calm"
            )

    except Exception as e:
        logger.error(f"MOVE Index Fehler: {e}")
        return IndicatorResult(
            name="MOVE Index (Bond Vol)",
            value=None,
            status="error",
            score=0,
            message=f"Data error: {e}"
        )
