"""
vvix.py — CBOE VVIX Index (Volatility of VIX)
Misst die Volatilität des VIX selbst — "Fear of Fear".
Quelle: Yahoo Finance (^VVIX)

Schwellenwerte:
  Gelb: > 100  (erhöhte Unsicherheit)
  Rot:  > 120  (Panik / Crash-Umfeld)
"""

import logging
import yfinance as yf
import config
from indicators.base import IndicatorResult

logger = logging.getLogger(__name__)


def get_signal() -> IndicatorResult:
    """Liest den aktuellen VVIX-Stand und bewertet ihn."""
    try:
        ticker = yf.Ticker("^VVIX")
        data   = ticker.history(period="1d", interval="5m")

        if data.empty:
            # Fallback: Tagesdaten
            data = ticker.history(period="5d")
            if data.empty:
                raise ValueError("Keine VVIX-Daten erhalten")

        vvix = float(data["Close"].iloc[-1])

        if vvix >= config.VVIX_RED:
            return IndicatorResult(
                name="VVIX (Vol of VIX)",
                value=vvix,
                status="red",
                score=config.SCORE_PER_RED,
                message=f"VVIX={vvix:.1f} 🔴 — Panic regime (threshold: {config.VVIX_RED})"
            )
        elif vvix >= config.VVIX_YELLOW:
            return IndicatorResult(
                name="VVIX (Vol of VIX)",
                value=vvix,
                status="yellow",
                score=config.SCORE_PER_YELLOW,
                message=f"VVIX={vvix:.1f} 🟡 — Elevated uncertainty (threshold: {config.VVIX_YELLOW})"
            )
        else:
            return IndicatorResult(
                name="VVIX (Vol of VIX)",
                value=vvix,
                status="green",
                score=0,
                message=f"VVIX={vvix:.1f} — Normal vol regime"
            )

    except Exception as e:
        logger.error(f"VVIX Fehler: {e}")
        return IndicatorResult(
            name="VVIX (Vol of VIX)",
            value=None,
            status="error",
            score=0,
            message=f"Data error: {e}"
        )
