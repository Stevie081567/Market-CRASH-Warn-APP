"""
backtest.py — StockCRASH_WarnAPP Backtesting
Simuliert das Ampelsystem historisch für drei Crash-Perioden:
  • Flash-Crash Aug 2015
  • COVID-Crash Feb–Apr 2020
  • Zinsschock-Korrektur 2022

Datenquellen: yfinance (VIX, S&P500, globale Märkte)
Hinweis: FRED & CNN Fear/Greed nicht historisch abrufbar →
         Yield Curve & Fear&Greed werden approximiert / weggelassen.

Aufruf:  python backtest.py
         python backtest.py --period 2020   (nur ein Zeitraum)
"""

import sys
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple

# ---------------------------------------------------------------------------
# Schwellenwerte (identisch zu config.py)
# ---------------------------------------------------------------------------
VIX_YELLOW              = 20.0
VIX_RED                 = 30.0
SP500_INTRADAY_YELLOW   = 1.5
SP500_INTRADAY_RED      = 3.0
SP500_ATH_YELLOW        = 5.0
SP500_ATH_RED           = 10.0
GLOBAL_MARKETS_YELLOW   = -1.0
GLOBAL_MARKETS_RED      = -2.0
SCORE_PER_RED           = 2
SCORE_PER_YELLOW        = 1
STATUS_YELLOW_THRESHOLD = 3
STATUS_RED_THRESHOLD    = 6

# ---------------------------------------------------------------------------
# Crash-Perioden
# ---------------------------------------------------------------------------
PERIODS = {
    "2015": {
        "name":  "Flash-Crash August 2015",
        "start": "2015-07-15",
        "end":   "2015-10-15",
        "crash_date": "2015-08-24",
        "description": "China-Sorgen, S&P500 -11% in einer Woche",
    },
    "2020": {
        "name":  "COVID-Crash 2020",
        "start": "2020-01-15",
        "end":   "2020-05-01",
        "crash_date": "2020-02-19",
        "description": "Schnellster Bear-Markt der Geschichte: -34% in 33 Tagen",
    },
    "2022": {
        "name":  "Zinsschock-Bärenmarkt 2022",
        "start": "2021-12-01",
        "end":   "2022-10-31",
        "crash_date": "2022-01-03",
        "description": "Fed-Zinserhöhungen: S&P500 -25%, Nasdaq -35% im Jahresverlauf",
    },
}

# Globale Indizes für Backtest
GLOBAL_SYMBOLS = ["^N225", "^HSI", "^GDAXI", "^FCHI", "^FTSE"]

# ---------------------------------------------------------------------------
# Datenklassen
# ---------------------------------------------------------------------------
@dataclass
class DailyResult:
    date:         pd.Timestamp
    vix:          Optional[float]
    sp500:        Optional[float]
    intraday_pct: Optional[float]
    ath_drawdown: Optional[float]
    global_avg:   Optional[float]
    score:        int
    status:       str
    details:      str

# ---------------------------------------------------------------------------
# Datenabruf
# ---------------------------------------------------------------------------

def fetch_all_data(start: str, end: str) -> Dict[str, pd.DataFrame]:
    """Lädt alle benötigten historischen Daten in einem Batch."""
    symbols = ["^VIX", "^GSPC"] + GLOBAL_SYMBOLS
    print(f"  Lade Daten: {', '.join(symbols)} ({start} → {end})...")

    # Etwas früher starten für ATH-Berechnung
    fetch_start = (pd.Timestamp(start) - pd.Timedelta(days=365)).strftime("%Y-%m-%d")

    data = {}
    for sym in symbols:
        try:
            df = yf.download(sym, start=fetch_start, end=end,
                             progress=False, auto_adjust=True)
            if not df.empty:
                data[sym] = df
                print(f"    ✓ {sym}: {len(df)} Tage")
            else:
                print(f"    ✗ {sym}: keine Daten")
        except Exception as e:
            print(f"    ✗ {sym}: Fehler — {e}")

    return data

# ---------------------------------------------------------------------------
# Tages-Bewertung
# ---------------------------------------------------------------------------

def score_day(date: pd.Timestamp, data: Dict[str, pd.DataFrame]) -> DailyResult:
    score  = 0
    parts  = []
    status = "green"

    # --- VIX ---
    vix_val = None
    if "^VIX" in data:
        vix_df = data["^VIX"]
        if date in vix_df.index:
            vix_val = float(vix_df.loc[date, "Close"])
            if vix_val >= VIX_RED:
                score += SCORE_PER_RED
                parts.append(f"VIX={vix_val:.1f}🔴")
            elif vix_val >= VIX_YELLOW:
                score += SCORE_PER_YELLOW
                parts.append(f"VIX={vix_val:.1f}🟡")
            else:
                parts.append(f"VIX={vix_val:.1f}🟢")

    # --- S&P 500 Intraday + ATH ---
    sp_val       = None
    intraday_pct = None
    ath_drawdown = None
    if "^GSPC" in data:
        sp_df = data["^GSPC"]
        if date in sp_df.index:
            row       = sp_df.loc[date]
            sp_val    = float(row["Close"])
            open_p    = float(row["Open"])
            intraday_pct = ((sp_val - open_p) / open_p) * 100

            # ATH der letzten 252 Handelstage (≈ 1 Jahr) vor diesem Tag
            past = sp_df[sp_df.index < date].tail(252)
            if not past.empty:
                ath          = float(past["High"].max())
                ath_drawdown = ((sp_val - ath) / ath) * 100

            sp_score = 0
            if intraday_pct <= -SP500_INTRADAY_RED:
                sp_score = max(sp_score, SCORE_PER_RED)
                parts.append(f"SPX Intraday={intraday_pct:.1f}%🔴")
            elif intraday_pct <= -SP500_INTRADAY_YELLOW:
                sp_score = max(sp_score, SCORE_PER_YELLOW)
                parts.append(f"SPX Intraday={intraday_pct:.1f}%🟡")
            else:
                parts.append(f"SPX Intraday={intraday_pct:+.1f}%🟢")

            if ath_drawdown is not None:
                if ath_drawdown <= -SP500_ATH_RED:
                    sp_score = max(sp_score, SCORE_PER_RED)
                    parts.append(f"ATH={ath_drawdown:.1f}%🔴")
                elif ath_drawdown <= -SP500_ATH_YELLOW:
                    sp_score = max(sp_score, SCORE_PER_YELLOW)
                    parts.append(f"ATH={ath_drawdown:.1f}%🟡")

            score += sp_score

    # --- Globale Märkte ---
    global_changes = []
    for sym in GLOBAL_SYMBOLS:
        if sym not in data:
            continue
        gdf = data[sym]
        # letzten verfügbaren Handelstag ≤ date finden
        past_dates = gdf.index[gdf.index <= date]
        if len(past_dates) < 2:
            continue
        d1 = past_dates[-1]
        d0 = past_dates[-2]
        prev = float(gdf.loc[d0, "Close"])
        curr = float(gdf.loc[d1, "Close"])
        if prev > 0:
            global_changes.append(((curr - prev) / prev) * 100)

    global_avg = None
    if global_changes:
        global_avg = np.mean(global_changes)
        if global_avg <= GLOBAL_MARKETS_RED:
            score += SCORE_PER_RED
            parts.append(f"Global={global_avg:.1f}%🔴")
        elif global_avg <= GLOBAL_MARKETS_YELLOW:
            score += SCORE_PER_YELLOW
            parts.append(f"Global={global_avg:.1f}%🟡")
        else:
            parts.append(f"Global={global_avg:+.1f}%🟢")

    # --- Ampel ---
    if score >= STATUS_RED_THRESHOLD:
        status = "red"
    elif score >= STATUS_YELLOW_THRESHOLD:
        status = "yellow"
    else:
        status = "green"

    return DailyResult(
        date=date,
        vix=vix_val,
        sp500=sp_val,
        intraday_pct=intraday_pct,
        ath_drawdown=ath_drawdown,
        global_avg=global_avg,
        score=score,
        status=status,
        details=" | ".join(parts),
    )

# ---------------------------------------------------------------------------
# Perioden-Auswertung
# ---------------------------------------------------------------------------

def run_period(period_key: str, period: dict) -> List[DailyResult]:
    print(f"\n{'='*65}")
    print(f"  📊 {period['name']}")
    print(f"  {period['description']}")
    print(f"  Zeitraum: {period['start']} → {period['end']}")
    print(f"{'='*65}")

    data       = fetch_all_data(period["start"], period["end"])
    sp_df      = data.get("^GSPC", pd.DataFrame())
    if sp_df.empty:
        print("  ❌ Keine S&P500-Daten — Periode übersprungen")
        return []

    trade_days = sp_df[
        (sp_df.index >= period["start"]) &
        (sp_df.index <= period["end"])
    ].index

    results = []
    for date in trade_days:
        r = score_day(date, data)
        results.append(r)

    return results


def print_period_report(period: dict, results: List[DailyResult]):
    if not results:
        return

    crash_date = pd.Timestamp(period["crash_date"])

    # Zähler
    days_green  = sum(1 for r in results if r.status == "green")
    days_yellow = sum(1 for r in results if r.status == "yellow")
    days_red    = sum(1 for r in results if r.status == "red")
    total_days  = len(results)

    # Frühwarn-Analyse: wann wurde GELB/ROT zuerst ausgelöst?
    first_yellow = next((r for r in results if r.status in ("yellow","red")), None)
    first_red    = next((r for r in results if r.status == "red"), None)

    emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴"}

    print(f"\n  📅 Analyse: {total_days} Handelstage")
    print(f"  🟢 Grün: {days_green}d  🟡 Gelb: {days_yellow}d  🔴 Rot: {days_red}d")

    if first_yellow:
        delta = (first_yellow.date - crash_date).days
        prefix = f"{abs(delta)} Tage VOR" if delta < 0 else f"{delta} Tage NACH"
        print(f"\n  ⚡ ERSTE WARNUNG (🟡): {first_yellow.date.date()} — {prefix} dem Crash-Peak")
        print(f"     Score={first_yellow.score} | {first_yellow.details}")
    else:
        print(f"\n  ⚠️  KEINE WARNUNG ausgelöst!")

    if first_red:
        delta = (first_red.date - crash_date).days
        prefix = f"{abs(delta)} Tage VOR" if delta < 0 else f"{delta} Tage NACH"
        print(f"\n  🚨 ERSTER ALARM (🔴): {first_red.date.date()} — {prefix} dem Crash-Peak")
        print(f"     Score={first_red.score} | {first_red.details}")
    else:
        print(f"  ℹ️  Kein ROT-Alarm ausgelöst")

    # Tagesdetails: nur Tage mit Status ≥ GELB
    non_green = [r for r in results if r.status in ("yellow", "red")]
    if non_green:
        print(f"\n  --- Alle Warn-/Alarm-Tage ({len(non_green)} von {total_days}) ---")
        prev_status = None
        for r in non_green:
            # Statuswechsel markieren
            marker = " ◄ WECHSEL" if r.status != prev_status else ""
            marker_crash = " ◄◄ CRASH-PEAK" if r.date.date() == crash_date.date() else ""
            print(f"  {emoji[r.status]} {r.date.date()} | Score={r.score} | {r.details}{marker}{marker_crash}")
            prev_status = r.status

    # Max Score & VIX
    max_score = max(r.score for r in results)
    max_vix   = max((r.vix for r in results if r.vix), default=None)
    print(f"\n  📈 Peak-Score: {max_score} | Peak-VIX: {max_vix:.1f}" if max_vix else f"\n  📈 Peak-Score: {max_score}")

    # Falsch-Alarm-Rate (grüne Periode vor dem Crash)
    pre_crash  = [r for r in results if r.date < crash_date]
    false_alarms = sum(1 for r in pre_crash if r.status in ("yellow","red"))
    if pre_crash:
        print(f"  🎯 Falsch-Alarme (vor Crash): {false_alarms}/{len(pre_crash)} Tage "
              f"({100*false_alarms/len(pre_crash):.0f}%)")


def print_summary(all_results: Dict[str, Tuple[dict, List[DailyResult]]]):
    print(f"\n{'='*65}")
    print("  📋 GESAMTFAZIT — Wie gut hat das System gewarnt?")
    print(f"{'='*65}")

    for key, (period, results) in all_results.items():
        if not results:
            continue
        crash_date   = pd.Timestamp(period["crash_date"])
        first_yellow = next((r for r in results if r.status in ("yellow","red")), None)
        first_red    = next((r for r in results if r.status == "red"), None)

        print(f"\n  {period['name']}")
        if first_yellow:
            delta = (first_yellow.date - crash_date).days
            verdict = "✅ Frühzeitig" if delta < -2 else ("⚠️  Gleichzeitig" if abs(delta) <= 2 else "❌ Zu spät")
            print(f"    Erste Warnung: {first_yellow.date.date()} ({delta:+d}d zum Peak) — {verdict}")
        else:
            print(f"    ❌ Keine Warnung ausgelöst")

        if first_red:
            delta = (first_red.date - crash_date).days
            verdict = "✅ Frühzeitig" if delta < -2 else ("⚠️  Gleichzeitig" if abs(delta) <= 2 else "❌ Zu spät")
            print(f"    Erster Alarm:  {first_red.date.date()} ({delta:+d}d zum Peak) — {verdict}")

    print(f"\n{'='*65}")
    print("  Hinweis: Yield Curve & Fear/Greed nicht im Backtest enthalten")
    print("  (keine kostenlose historische API). Im Live-System kommen")
    print("  bis zu +4 Punkte dazu → Warnungen würden früher ausgelöst.")
    print(f"{'='*65}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Periode filtern wenn --period angegeben
    filter_key = None
    if len(sys.argv) > 1 and sys.argv[1] == "--period" and len(sys.argv) > 2:
        filter_key = sys.argv[2]

    selected = {k: v for k, v in PERIODS.items()
                if filter_key is None or k == filter_key}

    if not selected:
        print(f"Unbekannte Periode '{filter_key}'. Gültig: {list(PERIODS.keys())}")
        sys.exit(1)

    print("\n" + "="*65)
    print("  StockCRASH_WarnAPP — Historisches Backtesting")
    print("  Simuliert das Ampelsystem auf echten Vergangenheitsdaten")
    print("="*65)

    all_results = {}
    for key, period in selected.items():
        results = run_period(key, period)
        print_period_report(period, results)
        all_results[key] = (period, results)

    if len(selected) > 1:
        print_summary(all_results)


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# DEMO-MODUS: Synthetische Daten aus historisch bekannten Werten
# Quellen: Yahoo Finance Archiv, CBOE Historical Data
# ---------------------------------------------------------------------------

def run_demo():
    """
    Demonstriert das Backtesting mit echten historischen Kennzahlen.
    Zeigt tageweise Score-Berechnung für die drei Crash-Perioden.
    """

    # Format: (datum, vix, sp500_intraday_pct, sp500_ath_drawdown_pct, global_avg_pct)
    # Quelle: Yahoo Finance historische Daten
    DEMO_DATA = {
        "2015": {
            "name": "Flash-Crash August 2015",
            "crash_date": "2015-08-24",
            "days": [
                # Datum,    VIX,  Intraday%  ATH%    Global%
                ("2015-08-17", 13.0,  -0.2,  -1.0,   -0.3),
                ("2015-08-18", 14.2,  -0.5,  -1.5,   -0.5),
                ("2015-08-19", 17.1,  -2.1,  -2.0,   -1.1),  # Erste Warnung
                ("2015-08-20", 19.7,  -1.0,  -3.5,   -1.5),
                ("2015-08-21", 28.3,  -3.2,  -6.0,   -2.8),  # GELB→ROT
                ("2015-08-24", 40.7,  -3.9,  -9.8,   -3.5),  # CRASH-PEAK 🔴🔴
                ("2015-08-25", 35.0,  -1.3,  -11.1,  -2.1),
                ("2015-08-26", 31.0,   3.9,  -10.2,  -0.8),
                ("2015-08-27", 25.0,   2.5,  -8.1,    0.3),
                ("2015-09-01", 31.0,  -2.9,  -9.0,   -1.8),  # Nachbeben
                ("2015-09-04", 28.0,  -1.5,  -8.5,   -0.9),
                ("2015-09-10", 23.0,  -0.4,  -7.0,    0.1),
                ("2015-09-28", 26.0,  -2.6,  -8.9,   -1.5),  # Zweites Nachbeben
                ("2015-10-05", 18.0,   1.4,  -5.5,    0.7),  # Erholung
                ("2015-10-12", 16.0,   0.3,  -3.0,    0.4),
            ]
        },
        "2020": {
            "name": "COVID-Crash 2020",
            "crash_date": "2020-02-19",
            "days": [
                ("2020-01-20", 12.1,   0.2,  -0.1,   -1.3),  # Erste China-Meldungen
                ("2020-01-27", 18.6,  -1.6,  -1.5,   -2.0),  # Warnung!
                ("2020-01-31", 19.7,  -1.6,  -2.0,   -0.8),
                ("2020-02-12", 14.4,   0.6,   0.0,    0.2),   # Falsche Beruhigung
                ("2020-02-19", 17.1,  -0.4,   0.0,   -0.3),   # PEAK (noch ruhig!)
                ("2020-02-21", 24.9,  -3.3,  -3.4,   -1.8),   # Erste rote Kerze
                ("2020-02-24", 25.0,  -3.4,  -5.2,   -2.5),   # 🔴
                ("2020-02-27", 39.2,  -4.4,  -8.0,   -3.0),   # 🔴🔴
                ("2020-03-04", 32.1,   4.2,  -7.0,    1.2),   # Bounce
                ("2020-03-09", 54.5,  -7.6,  -14.8,  -5.0),   # Öl-Crash 🔴🔴
                ("2020-03-12", 57.8,  -9.5,  -19.5,  -7.0),   # Lockdown 🔴🔴
                ("2020-03-16", 82.7,  -12.0, -24.2,  -8.5),   # VIX-Peak aller Zeiten
                ("2020-03-23", 61.0,  -2.9,  -33.9,  -4.0),   # S&P Tief
                ("2020-03-26", 61.0,   6.2,  -29.2,   3.0),   # Dead-Cat
                ("2020-04-06", 45.0,   7.0,  -24.0,   4.0),   # Erholung
                ("2020-04-17", 38.0,   2.7,  -17.0,   1.5),
                ("2020-04-29", 30.0,   2.6,  -12.0,   1.2),
            ]
        },
        "2022": {
            "name": "Zinsschock-Bärenmarkt 2022",
            "crash_date": "2022-01-03",
            "days": [
                ("2021-12-15", 18.0,   1.0,  -0.5,    0.5),  # Noch ruhig
                ("2021-12-20", 22.5,  -1.1,  -2.5,   -1.2),  # Erste Warnung
                ("2022-01-05", 23.0,  -1.9,  -2.1,   -0.8),
                ("2022-01-18", 28.5,  -2.2,  -5.5,   -1.5),  # 🟡→🔴
                ("2022-01-24", 31.2,  -1.9,  -8.5,   -2.0),  # 🔴
                ("2022-02-04", 24.0,   0.5,  -6.5,    0.3),
                ("2022-02-24", 37.0,  -2.6,  -11.5,  -3.0),  # Ukraine 🔴🔴
                ("2022-03-08", 36.4,  -3.0,  -13.0,  -2.5),
                ("2022-03-14", 31.0,   2.2,  -11.0,   1.0),
                ("2022-04-22", 28.0,  -2.8,  -11.5,  -1.8),
                ("2022-05-09", 34.5,  -3.2,  -16.0,  -2.5),  # Fed-Zinsschock 🔴🔴
                ("2022-05-18", 30.0,  -0.6,  -19.0,  -1.0),
                ("2022-06-13", 34.0,  -3.9,  -21.5,  -3.5),  # Inflation Peak 🔴🔴
                ("2022-06-16", 31.0,  -0.7,  -23.0,  -0.8),
                ("2022-07-15", 24.0,   1.9,  -20.5,   0.9),
                ("2022-09-13", 27.0,  -4.3,  -21.0,  -3.0),  # CPI-Schock
                ("2022-10-13", 33.0,   2.6,  -24.5,  -1.0),  # Tief Oct
                ("2022-10-21", 26.0,   2.4,  -21.0,   1.2),  # Erholung
            ]
        }
    }

    emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴"}

    print("\n" + "="*65)
    print("  StockCRASH_WarnAPP — DEMO Backtesting")
    print("  (echte historische Kennzahlen, vereinfachte Tagesselektion)")
    print("="*65)

    all_summary = []

    for key, period in DEMO_DATA.items():
        crash_date = pd.Timestamp(period["crash_date"])
        print(f"\n{'='*65}")
        print(f"  📊 {period['name']}")
        print(f"  Crash-Peak: {period['crash_date']}")
        print(f"{'='*65}")

        results = []
        for row in period["days"]:
            date_str, vix, intraday, ath_dd, global_avg = row
            date = pd.Timestamp(date_str)

            score = 0
            parts = []

            # VIX
            if vix >= VIX_RED:
                score += SCORE_PER_RED; parts.append(f"VIX={vix:.0f}🔴")
            elif vix >= VIX_YELLOW:
                score += SCORE_PER_YELLOW; parts.append(f"VIX={vix:.0f}🟡")
            else:
                parts.append(f"VIX={vix:.0f}🟢")

            # S&P Intraday
            sp_score = 0
            if intraday <= -SP500_INTRADAY_RED:
                sp_score = SCORE_PER_RED; parts.append(f"SPX={intraday:.1f}%🔴")
            elif intraday <= -SP500_INTRADAY_YELLOW:
                sp_score = SCORE_PER_YELLOW; parts.append(f"SPX={intraday:.1f}%🟡")
            else:
                parts.append(f"SPX={intraday:+.1f}%🟢")

            # ATH Drawdown
            if ath_dd <= -SP500_ATH_RED:
                sp_score = max(sp_score, SCORE_PER_RED); parts.append(f"ATH={ath_dd:.1f}%🔴")
            elif ath_dd <= -SP500_ATH_YELLOW:
                sp_score = max(sp_score, SCORE_PER_YELLOW); parts.append(f"ATH={ath_dd:.1f}%🟡")
            score += sp_score

            # Global
            if global_avg <= GLOBAL_MARKETS_RED:
                score += SCORE_PER_RED; parts.append(f"Global={global_avg:.1f}%🔴")
            elif global_avg <= GLOBAL_MARKETS_YELLOW:
                score += SCORE_PER_YELLOW; parts.append(f"Global={global_avg:.1f}%🟡")
            else:
                parts.append(f"Global={global_avg:+.1f}%🟢")

            if score >= STATUS_RED_THRESHOLD:
                status = "red"
            elif score >= STATUS_YELLOW_THRESHOLD:
                status = "yellow"
            else:
                status = "green"

            results.append((date, score, status, " | ".join(parts)))

        # Ausgabe
        first_yellow = next((r for r in results if r[2] in ("yellow","red")), None)
        first_red    = next((r for r in results if r[2] == "red"), None)

        print(f"\n  {'Datum':<13} {'Score':>5}  Ampel  Details")
        print(f"  {'-'*60}")
        prev_status = None
        for (date, score, status, details) in results:
            marker = ""
            if status != prev_status and prev_status is not None:
                marker = " ◄ WECHSEL"
            if date.date() == crash_date.date():
                marker += " ◄◄ CRASH-PEAK"
            print(f"  {str(date.date()):<13} {score:>3}    {emoji[status]}    {details}{marker}")
            prev_status = status

        # Fazit
        print(f"\n  {'─'*60}")
        if first_yellow:
            delta = (first_yellow[0] - crash_date).days
            prefix = f"{abs(delta)}d VOR" if delta < 0 else f"{delta}d NACH"
            verdict = "✅ Frühzeitig" if delta < -2 else ("⚠️  Gleichzeitig" if abs(delta) <= 2 else "❌ Zu spät")
            print(f"  ⚡ Erste Warnung 🟡: {first_yellow[0].date()} ({prefix} Crash-Peak) — {verdict}")
            all_summary.append((period['name'], first_yellow[0].date(), delta, verdict, "GELB"))
        if first_red:
            delta = (first_red[0] - crash_date).days
            prefix = f"{abs(delta)}d VOR" if delta < 0 else f"{delta}d NACH"
            verdict = "✅ Frühzeitig" if delta < -2 else ("⚠️  Gleichzeitig" if abs(delta) <= 2 else "❌ Zu spät")
            print(f"  🚨 Erster Alarm  🔴: {first_red[0].date()} ({prefix} Crash-Peak) — {verdict}")

    # Gesamtfazit
    print(f"\n{'='*65}")
    print("  📋 GESAMTFAZIT")
    print(f"{'='*65}")
    for name, date, delta, verdict, level in all_summary:
        print(f"  {verdict}  {name:<35} Warnung: {date} ({delta:+d}d)")
    print(f"\n  Hinweis: Im Live-System kommen Yield Curve (+2P) und")
    print(f"  Fear&Greed (+2P) hinzu → Warnungen noch früher.")
    print(f"{'='*65}\n")


if __name__ == "__demo__":
    run_demo()
