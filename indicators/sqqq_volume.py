"""
sqqq_volume.py — SQQQ Volume Spike Indicator
SQQQ = ProShares UltraPro Short QQQ (3x inverse Nasdaq)
Hohes Volumen signalisiert institutionelle Absicherung gegen Nasdaq-Crash.

Methode: aktuelles Volumen vs. 20-Tage-Durchschnitt (Volume Ratio)
  Ratio > 2.0 = doppeltes Durchschnittsvolumen → Warnung
  Ratio > 3.5 = 3.5x Durchschnittsvolumen → Alarm

Zusätzlich: Preisveränderung % als Kontext-Info.
Quelle: Yahoo Finance (SQQQ)

Schwellenwerte (Volume Ratio):
  Gelb: > 2.0x
  Rot:  > 3.5x
"""

import logging
import numpy as np
import yfinance as yf
import config
from indicators.base import IndicatorResult

logger = logging.getLogger(__name__)

SQQQ_LOOKBACK_DAYS = 30   # Für 20-Tage-Durchschnitt + etwas Puffer


def get_signal() -> IndicatorResult:
    """
    Berechnet SQQQ Volume Ratio vs. 20-Tage-Durchschnitt.
    Hohes Ratio = institutionelle Absicherung gegen Nasdaq-Crash.
    """
    try:
        ticker = yf.Ticker("SQQQ")
        data   = ticker.history(period=f"{SQQQ_LOOKBACK_DAYS}d")

        if len(data) < 5:
            raise ValueError("Zu wenig SQQQ-Daten")

        # Aktuelles Volumen (letzter Handelstag)
        current_vol = float(data["Volume"].iloc[-1])

        # 20-Tage-Durchschnitt (ohne heutigen Tag)
        avg_vol_20d = float(data["Volume"].iloc[:-1].tail(20).mean())

        if avg_vol_20d == 0:
            raise ValueError("20-Tage-Durchschnitt ist 0")

        vol_ratio = current_vol / avg_vol_20d

        # Preisveränderung für Kontext
        if len(data) >= 2:
            prev_close   = float(data["Close"].iloc[-2])
            curr_close   = float(data["Close"].iloc[-1])
            price_change = ((curr_close - prev_close) / prev_close) * 100
            price_str    = f" | SQQQ {price_change:+.1f}%"
        else:
            price_str = ""

        vol_m = current_vol / 1_000_000   # in Millionen

        if vol_ratio >= config.SQQQ_VOL_RED:
            return IndicatorResult(
                name="SQQQ Volume Spike",
                value=vol_ratio,
                status="red",
                score=config.SCORE_PER_RED,
                message=f"Vol={vol_m:.0f}M ({vol_ratio:.1f}x avg) 🔴 — Institutional hedging{price_str}"
            )
        elif vol_ratio >= config.SQQQ_VOL_YELLOW:
            return IndicatorResult(
                name="SQQQ Volume Spike",
                value=vol_ratio,
                status="yellow",
                score=config.SCORE_PER_YELLOW,
                message=f"Vol={vol_m:.0f}M ({vol_ratio:.1f}x avg) 🟡 — Elevated hedging{price_str}"
            )
        else:
            return IndicatorResult(
                name="SQQQ Volume Spike",
                value=vol_ratio,
                status="green",
                score=0,
                message=f"Vol={vol_m:.0f}M ({vol_ratio:.1f}x avg) — Normal{price_str}"
            )

    except Exception as e:
        logger.error(f"SQQQ Volume Fehler: {e}")
        return IndicatorResult(
            name="SQQQ Volume Spike",
            value=None,
            status="error",
            score=0,
            message=f"Data error: {e}"
        )
