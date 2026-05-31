"""
sp500.py — S&P 500 Intraday-Drawdown & Abstand vom ATH
Quelle: Yahoo Finance (^GSPC)
"""

import logging
import yfinance as yf
import config
from indicators.base import IndicatorResult

logger = logging.getLogger(__name__)


def get_signal() -> IndicatorResult:
    """Bewertet S&P 500 nach Intraday-Drop und ATH-Abstand."""
    try:
        ticker = yf.Ticker("^GSPC")

        # Intraday-Daten (heute)
        intraday = ticker.history(period="1d", interval="5m")
        if intraday.empty:
            raise ValueError("Keine S&P 500 Intraday-Daten")

        open_price  = float(intraday["Open"].iloc[0])
        last_price  = float(intraday["Close"].iloc[-1])
        intraday_pct = ((last_price - open_price) / open_price) * 100

        # ATH der letzten 52 Wochen als Proxy
        hist = ticker.history(period="1y")
        if hist.empty:
            raise ValueError("Keine S&P 500 Jahres-Daten")

        ath = float(hist["High"].max())
        ath_drawdown_pct = ((last_price - ath) / ath) * 100  # negativ wenn unter ATH

        # Bewertung — worst case entscheidet
        score  = 0
        status = "green"
        parts  = []

        # Intraday
        if intraday_pct <= -config.SP500_INTRADAY_RED:
            score  = max(score, config.SCORE_PER_RED)
            status = "red"
            parts.append(f"Intraday {intraday_pct:.1f}% 🔴")
        elif intraday_pct <= -config.SP500_INTRADAY_YELLOW:
            score  = max(score, config.SCORE_PER_YELLOW)
            if status == "green":
                status = "yellow"
            parts.append(f"Intraday {intraday_pct:.1f}% 🟡")
        else:
            parts.append(f"Intraday {intraday_pct:+.1f}%")

        # ATH-Abstand
        if ath_drawdown_pct <= -config.SP500_ATH_RED:
            score  = max(score, config.SCORE_PER_RED)
            status = "red"
            parts.append(f"ATH-Abstand {ath_drawdown_pct:.1f}% 🔴")
        elif ath_drawdown_pct <= -config.SP500_ATH_YELLOW:
            score  = max(score, config.SCORE_PER_YELLOW)
            if status == "green":
                status = "yellow"
            parts.append(f"ATH-Abstand {ath_drawdown_pct:.1f}% 🟡")
        else:
            parts.append(f"ATH-Abstand {ath_drawdown_pct:.1f}%")

        return IndicatorResult(
            name="S&P 500",
            value=last_price,
            status=status,
            score=score,
            message=f"SPX={last_price:.0f} | " + " | ".join(parts)
        )

    except Exception as e:
        logger.error(f"S&P 500 Fehler: {e}")
        return IndicatorResult(
            name="S&P 500",
            value=None,
            status="error",
            score=0,
            message=f"Datenfehler: {e}"
        )
