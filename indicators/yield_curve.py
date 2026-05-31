"""
yield_curve.py — US Treasury 10Y-2Y Spread (Yield Curve)
Quelle: FRED API (kostenloser Key erforderlich)
Inversionsindikator für Rezession.
"""

import logging
import requests
import config
from indicators.base import IndicatorResult

logger = logging.getLogger(__name__)

FRED_SERIES = {
    "10Y": "DGS10",   # 10-Year Treasury Constant Maturity Rate
    "2Y":  "DGS2",    # 2-Year Treasury Constant Maturity Rate
}


def _fetch_latest(series_id: str) -> float:
    """Holt den neuesten Wert einer FRED-Zeitreihe."""
    params = {
        "series_id":      series_id,
        "api_key":        config.FRED_API_KEY,
        "file_type":      "json",
        "sort_order":     "desc",
        "limit":          5,
        "observation_end": "9999-12-31",
    }
    resp = requests.get(config.FRED_BASE_URL, params=params, timeout=10)
    resp.raise_for_status()
    observations = resp.json().get("observations", [])

    # Überspringe "." (fehlende Werte) und nehme den neuesten gültigen
    for obs in observations:
        if obs["value"] != ".":
            return float(obs["value"])

    raise ValueError(f"Keine gültigen Daten für {series_id}")


def get_signal() -> IndicatorResult:
    """Berechnet 10Y-2Y Spread und bewertet die Yield Curve."""
    if not config.FRED_API_KEY:
        return IndicatorResult(
            name="Yield Curve (10Y-2Y)",
            value=None,
            status="error",
            score=0,
            message="FRED_API_KEY nicht gesetzt"
        )

    try:
        rate_10y = _fetch_latest(FRED_SERIES["10Y"])
        rate_2y  = _fetch_latest(FRED_SERIES["2Y"])
        spread   = rate_10y - rate_2y

        if spread <= config.YIELD_CURVE_RED:
            return IndicatorResult(
                name="Yield Curve (10Y-2Y)",
                value=spread,
                status="red",
                score=config.SCORE_PER_RED,
                message=f"Spread={spread:+.2f}% — INVERTIERT 🔴 Rezessionsindikator!"
            )
        elif spread <= config.YIELD_CURVE_YELLOW:
            return IndicatorResult(
                name="Yield Curve (10Y-2Y)",
                value=spread,
                status="yellow",
                score=config.SCORE_PER_YELLOW,
                message=f"Spread={spread:+.2f}% — flache Kurve (10Y={rate_10y:.2f}% / 2Y={rate_2y:.2f}%)"
            )
        else:
            return IndicatorResult(
                name="Yield Curve (10Y-2Y)",
                value=spread,
                status="green",
                score=0,
                message=f"Spread={spread:+.2f}% — normal (10Y={rate_10y:.2f}% / 2Y={rate_2y:.2f}%)"
            )

    except Exception as e:
        logger.error(f"Yield Curve Fehler: {e}")
        return IndicatorResult(
            name="Yield Curve (10Y-2Y)",
            value=None,
            status="error",
            score=0,
            message=f"Datenfehler: {e}"
        )
