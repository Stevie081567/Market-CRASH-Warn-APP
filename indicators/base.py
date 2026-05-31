"""
base.py — Gemeinsame Datenstruktur für alle Indikatoren
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class IndicatorResult:
    """Einheitliches Ergebnis-Objekt für jeden Indikator."""
    name:    str            # Anzeigename, z.B. "VIX Fear Index"
    value:   Optional[float]  # Numerischer Wert (None bei Fehler)
    status:  str            # "green", "yellow", "red", "error"
    score:   int            # 0, 1 (yellow) oder 2 (red)
    message: str            # Kurze lesbare Beschreibung

    def is_ok(self) -> bool:
        return self.status not in ("error",)

    def emoji(self) -> str:
        return {"green": "🟢", "yellow": "🟡", "red": "🔴", "error": "⚫"}.get(self.status, "⚫")

    def __str__(self) -> str:
        return f"{self.emoji()} {self.name}: {self.message}"
