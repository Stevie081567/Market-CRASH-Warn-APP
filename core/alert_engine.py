"""
alert_engine.py — Ampel-Logik & Scoring
Sammelt alle Indikator-Ergebnisse und berechnet den Gesamtstatus.
"""

import logging
from typing import List
from indicators.base import IndicatorResult
import config

logger = logging.getLogger(__name__)


class AlertResult:
    """Gesamtergebnis eines vollständigen Markt-Checks."""

    def __init__(self, results: List[IndicatorResult]):
        self.results      = results
        self.total_score  = sum(r.score for r in results)
        self.status       = self._calc_status()
        self.red_count    = sum(1 for r in results if r.status == "red")
        self.yellow_count = sum(1 for r in results if r.status == "yellow")
        self.green_count  = sum(1 for r in results if r.status == "green")
        self.error_count  = sum(1 for r in results if r.status == "error")

    def _calc_status(self) -> str:
        if self.total_score >= config.STATUS_RED_THRESHOLD:
            return "red"
        elif self.total_score >= config.STATUS_YELLOW_THRESHOLD:
            return "yellow"
        else:
            return "green"

    def status_emoji(self) -> str:
        return {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(self.status, "⚫")

    def status_label(self) -> str:
        return {
            "green":  "GREEN — No elevated risk",
            "yellow": "YELLOW — Caution: Elevated risk",
            "red":    "RED — ALERT: High crash risk!",
        }.get(self.status, "Unknown")

    def summary_lines(self) -> List[str]:
        lines = [
            f"{self.status_emoji()} {self.status_label()}",
            f"Score: {self.total_score} | 🔴 {self.red_count} | 🟡 {self.yellow_count} | 🟢 {self.green_count}",
            "─" * 30,
        ]
        for r in self.results:
            lines.append(str(r))
        return lines

    def to_pushover_message(self) -> str:
        return "\n".join(self.summary_lines())

    def to_pushover_title(self) -> str:
        return f"StockCrash {self.status_emoji()} {self.status_label().split('—')[0].strip()}"


def run_all_checks(include_futures: bool = True) -> AlertResult:
    """
    Führt alle Indikatoren aus und gibt ein AlertResult zurück.

    Indikatoren (12 gesamt):
      Kritisch (2 Punkte): VIX, S&P500, Fear&Greed, VVIX
      Standard (1 Punkt):  Yield Curve, Put/Call, Futures, Buffett,
                           Global Markets, MOVE, SKEW, SQQQ Volume
    """
    from indicators import (
        vix, sp500, yield_curve, fear_greed,
        futures, global_markets, buffett_indicator, put_call_ratio,
        vvix, move_index, skew, sqqq_volume,
    )

    # Kritische Indikatoren (2 Punkte bei Rot)
    critical_checks = [
        vix.get_signal,
        sp500.get_signal,
        fear_greed.get_signal,
        vvix.get_signal,        # NEU
    ]

    # Standard-Indikatoren (1 Punkt bei Rot)
    standard_checks = [
        yield_curve.get_signal,
        put_call_ratio.get_signal,
        global_markets.get_signal,
        buffett_indicator.get_signal,
        move_index.get_signal,  # NEU
        skew.get_signal,        # NEU
        sqqq_volume.get_signal, # NEU
    ]

    if include_futures:
        standard_checks.insert(2, futures.get_signal)

    all_checks = critical_checks + standard_checks
    results    = []

    for check_fn in all_checks:
        try:
            result = check_fn()
            results.append(result)
            logger.debug(f"  {result}")
        except Exception as e:
            name = check_fn.__module__.split(".")[-1]
            logger.error(f"Unerwarteter Fehler in {name}: {e}")

    return AlertResult(results)
