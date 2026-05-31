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
            "green":  "GRÜN — Kein erhöhtes Risiko",
            "yellow": "GELB — Vorsicht: Erhöhtes Risiko",
            "red":    "ROT — ALARM: Crash-Risiko hoch!",
        }.get(self.status, "Unbekannt")

    def summary_lines(self) -> List[str]:
        """Formatiert den Bericht als Liste von Zeilen."""
        lines = [
            f"{self.status_emoji()} {self.status_label()}",
            f"Score: {self.total_score} | 🔴 {self.red_count} | 🟡 {self.yellow_count}",
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
    include_futures=False beim Daily Summary (Markt ist zu).
    """
    from indicators import vix, sp500, yield_curve, fear_greed
    from indicators import futures, global_markets, buffett_indicator, put_call_ratio

    checks = [
        vix.get_signal,
        sp500.get_signal,
        yield_curve.get_signal,
        fear_greed.get_signal,
        global_markets.get_signal,
        buffett_indicator.get_signal,
        put_call_ratio.get_signal,
    ]

    if include_futures:
        checks.insert(4, futures.get_signal)

    results = []
    for check_fn in checks:
        try:
            result = check_fn()
            results.append(result)
            logger.debug(f"  {result}")
        except Exception as e:
            name = check_fn.__module__.split(".")[-1]
            logger.error(f"Unerwarteter Fehler in {name}: {e}")

    return AlertResult(results)
