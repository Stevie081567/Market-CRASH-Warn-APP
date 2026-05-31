"""
buffett_indicator.py — Buffett Indicator (Marktkapitalisierung / BIP)
Formel: Wilshire 5000 Total Market Cap / US GDP * 100
Quelle: Yahoo Finance (^W5000) + FRED API (GDP)
"""

import logging
import requests
import yfinance as yf
import config
from indicators.base import IndicatorResult

logger = logging.getLogger(__name__)


def _get_us_gdp_billions() -> float:
    """Holt das nominale US-BIP von FRED (in Milliarden USD)."""
    params = {
        "series_id":  "GDP",       # Nominal GDP, Quarterly, Seasonally Adjusted Annual Rate
        "api_key":    config.FRED_API_KEY,
        "file_type":  "json",
        "sort_order": "desc",
        "limit":      4,
    }
    resp = requests.get(config.FRED_BASE_URL, params=params, timeout=10)
    resp.raise_for_status()
    observations = resp.json().get("observations", [])

    for obs in observations:
        if obs["value"] != ".":
            return float(obs["value"])

    raise ValueError("Keine gültigen GDP-Daten von FRED")


def _get_wilshire5000_billions() -> float:
    """
    Holt den Wilshire 5000 Index und konvertiert in Marktkapitalisierung.
    Der Index-Punkt entspricht ca. 1 Mrd USD (historische Näherung).
    """
    ticker = yf.Ticker("^W5000")
    data   = ticker.history(period="5d")

    if data.empty:
        raise ValueError("Keine Wilshire 5000 Daten")

    # Letzter verfügbarer Schlusskurs
    index_value = float(data["Close"].iloc[-1])
    # Näherung: 1 Indexpunkt ≈ 1 Mrd USD Marktkapitalisierung
    return index_value * 1.0


def get_signal() -> IndicatorResult:
    """Berechnet den Buffett Indicator und bewertet die Marktbewertung."""
    if not config.FRED_API_KEY:
        return IndicatorResult(
            name="Buffett Indicator",
            value=None,
            status="error",
            score=0,
            message="FRED_API_KEY nicht gesetzt"
        )

    try:
        gdp_billions      = _get_us_gdp_billions()
        market_cap_billions = _get_wilshire5000_billions()
        buffett_ratio     = (market_cap_billions / gdp_billions) * 100

        if buffett_ratio >= config.BUFFETT_RED:
            return IndicatorResult(
                name="Buffett Indicator",
                value=buffett_ratio,
                status="red",
                score=config.SCORE_PER_RED,
                message=f"{buffett_ratio:.0f}% 🔴 — stark überbewertet (Schwelle: {config.BUFFETT_RED}%)"
            )
        elif buffett_ratio >= config.BUFFETT_YELLOW:
            return IndicatorResult(
                name="Buffett Indicator",
                value=buffett_ratio,
                status="yellow",
                score=config.SCORE_PER_YELLOW,
                message=f"{buffett_ratio:.0f}% 🟡 — überbewertet (Schwelle: {config.BUFFETT_YELLOW}%)"
            )
        else:
            return IndicatorResult(
                name="Buffett Indicator",
                value=buffett_ratio,
                status="green",
                score=0,
                message=f"{buffett_ratio:.0f}% — faire Bewertung"
            )

    except Exception as e:
        logger.error(f"Buffett Indicator Fehler: {e}")
        return IndicatorResult(
            name="Buffett Indicator",
            value=None,
            status="error",
            score=0,
            message=f"Datenfehler: {e}"
        )
