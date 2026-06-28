"""
skew.py — CBOE SKEW Index (Tail Risk / Black Swan Indicator)
Misst die wahrgenommene Wahrscheinlichkeit von Tail-Risk-Ereignissen
(2-3 Standardabweichungen unter dem Markt).
Normale Range: 100–150. Werte > 150 signalisieren erhöhtes Black-Swan-Risiko.
Quelle: Yahoo Finance (^SKEW)

Schwellenwerte:
  Gelb: > 140  (erhöhtes Tail-Risk)
  Rot:  > 150  (stark erhöhtes Black-Swan-Risiko)
"""

import logging
import yfinance as yf
import config
from indicators.base import IndicatorResult

logger = logging.getLogger(__name__)


def get_signal() -> IndicatorResult:
    """Liest den aktuellen CBOE SKEW Index."""
    try:
        ticker = yf.Ticker("^SKEW")
        data   = ticker.history(period="5d")

        if data.empty:
            raise ValueError("Keine SKEW-Daten erhalten")

        skew = float(data["Close"].iloc[-1])

        # SKEW-Besonderheit: sehr hohe Werte = erhöhtes Risiko
        # aber auch sehr niedrige Werte (< 110) können Sorglosigkeit signalisieren
        if skew >= config.SKEW_RED:
            return IndicatorResult(
                name="SKEW Index (Tail Risk)",
                value=skew,
                status="red",
                score=config.SCORE_PER_RED,
                message=f"SKEW={skew:.1f} 🔴 — High black swan risk (threshold: {config.SKEW_RED})"
            )
        elif skew >= config.SKEW_YELLOW:
            return IndicatorResult(
                name="SKEW Index (Tail Risk)",
                value=skew,
                status="yellow",
                score=config.SCORE_PER_YELLOW,
                message=f"SKEW={skew:.1f} 🟡 — Elevated tail risk (threshold: {config.SKEW_YELLOW})"
            )
        else:
            return IndicatorResult(
                name="SKEW Index (Tail Risk)",
                value=skew,
                status="green",
                score=0,
                message=f"SKEW={skew:.1f} — Normal tail risk distribution"
            )

    except Exception as e:
        logger.error(f"SKEW Fehler: {e}")
        return IndicatorResult(
            name="SKEW Index (Tail Risk)",
            value=None,
            status="error",
            score=0,
            message=f"Data error: {e}"
        )
