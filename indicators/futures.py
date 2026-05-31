"""
futures.py — E-Mini Futures Pre-Market Check
Symbole: ES=F (S&P), NQ=F (Nasdaq), YM=F (Dow)
Quelle: Yahoo Finance
"""

import logging
import yfinance as yf
import config
from indicators.base import IndicatorResult

logger = logging.getLogger(__name__)


def get_signal() -> IndicatorResult:
    """
    Prüft E-Mini Futures auf Pre-Market-Bewegungen.
    Bewertet den Durchschnitt der prozentualen Veränderung.
    """
    try:
        results = {}

        for symbol, name in config.FUTURES_SYMBOLS.items():
            try:
                ticker = yf.Ticker(symbol)
                data   = ticker.history(period="2d", interval="5m")

                if len(data) < 2:
                    logger.warning(f"Zu wenig Daten für {symbol}")
                    continue

                prev_close = float(data["Close"].iloc[-288] if len(data) > 288 else data["Close"].iloc[0])
                last_price = float(data["Close"].iloc[-1])
                pct_change = ((last_price - prev_close) / prev_close) * 100
                results[name] = pct_change

            except Exception as e:
                logger.warning(f"Futures {symbol} Fehler: {e}")

        if not results:
            raise ValueError("Keine Futures-Daten verfügbar")

        avg_change = sum(results.values()) / len(results)

        # Detail-String
        details = " | ".join(f"{n.split()[0]}: {v:+.1f}%" for n, v in results.items())

        if avg_change <= config.FUTURES_RED:
            return IndicatorResult(
                name="E-Mini Futures",
                value=avg_change,
                status="red",
                score=config.SCORE_PER_RED,
                message=f"Ø {avg_change:+.1f}% 🔴 — {details}"
            )
        elif avg_change <= config.FUTURES_YELLOW:
            return IndicatorResult(
                name="E-Mini Futures",
                value=avg_change,
                status="yellow",
                score=config.SCORE_PER_YELLOW,
                message=f"Ø {avg_change:+.1f}% 🟡 — {details}"
            )
        else:
            return IndicatorResult(
                name="E-Mini Futures",
                value=avg_change,
                status="green",
                score=0,
                message=f"Ø {avg_change:+.1f}% — {details}"
            )

    except Exception as e:
        logger.error(f"Futures Fehler: {e}")
        return IndicatorResult(
            name="E-Mini Futures",
            value=None,
            status="error",
            score=0,
            message=f"Datenfehler: {e}"
        )
