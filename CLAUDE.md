# StockCRASH_WarnAPP — CLAUDE.md

## Projektübersicht

**Zweck:** 24/7 laufender Markt-Frühwarnservice, der bei drohenden Börsenkorrekturen oder Crashs automatisch Push-Benachrichtigungen an iPhone/iPad des Besitzers sendet. Der Besitzer ist häufig auf Reisen (Urlaub, Geschäftsreisen) und möchte rechtzeitig gewarnt werden, bevor sein Portfolio signifikant an Wert verliert.

**Besitzer:** Stefan Schauß  
**Plattform:** Python 3.11+ auf Linux-Server (24/7) oder Raspberry Pi  
**Benachrichtigung:** Pushover → iPhone & iPad  
**Ampelsystem:** 🟢 Grün / 🟡 Gelb / 🔴 Rot  

---

## Architektur

```
StockCRASH_WarnAPP/
├── main.py                  # Einstiegspunkt, APScheduler
├── config.py                # Alle Schwellenwerte & Konfiguration
├── .env                     # API-Keys (nicht in Git!)
├── .env.example             # Template für .env
├── requirements.txt
├── indicators/              # Ein Modul pro Indikator
│   ├── vix.py               # CBOE VIX Fear Index
│   ├── sp500.py             # S&P 500 Tages-Drawdown & ATH
│   ├── yield_curve.py       # 10Y-2Y US Treasury Spread (FRED)
│   ├── fear_greed.py        # CNN Fear & Greed Index
│   ├── futures.py           # E-Mini Futures (ES, NQ, YM) Pre-Market
│   ├── global_markets.py    # Asian & European Indices (Nikkei, DAX, FTSE...)
│   ├── buffett_indicator.py # Marktkapitalisierung / BIP
│   └── put_call_ratio.py    # CBOE Put/Call Ratio
├── core/
│   ├── alert_engine.py      # Scoring, Ampel-Logik
│   ├── notifier.py          # Pushover-Integration
│   └── state_manager.py     # Verhindert Notification-Spam
├── deploy/
│   ├── install.sh           # Linux-Server Setup-Script
│   └── crashwarn.service    # systemd Service-Datei
└── logs/                    # Läuft lokal, nicht in Git
```

---

## Indikatoren & Schwellenwerte

### 🔴 Kritische Indikatoren (je 2 Punkte)

| Indikator | Gelb | Rot |
|---|---|---|
| VIX | > 20 | > 30 |
| S&P 500 Intraday-Drop | > 1,5% | > 3% |
| S&P 500 vom ATH | > 5% | > 10% |
| Fear & Greed | < 35 | < 20 |

### 🟡 Warnsignal-Indikatoren (je 1 Punkt)

| Indikator | Gelb | Rot |
|---|---|---|
| Yield Curve (10Y-2Y) | < 0,3% | Invertiert (< 0) |
| Put/Call Ratio | > 1,0 | > 1,3 |
| E-Mini Futures Pre-Market | < -0,5% | < -1,5% |
| Buffett Indicator | > 150% | > 180% |
| Global Markets (Asien/EU) | ∅ > -1% | ∅ > -2% |

### Ampel-Gesamtbewertung

```
GRÜN  = Gesamtpunktzahl 0–2   → Kein Alert
GELB  = Gesamtpunktzahl 3–5   → Warnung (Pushover Normal-Priorität)
ROT   = Gesamtpunktzahl 6+    → Alarm  (Pushover Hohe Priorität + Sound)
```

---

## Scheduler-Zeitfenster (Europe/Berlin)

| Job | Zeit | Was |
|---|---|---|
| Pre-Market Check | Mo–Fr 14:00–15:30 | Futures + Asian/EU-Märkte |
| Intraday Check | Mo–Fr 15:30–22:00 | Alle Indikatoren, alle 15 Min |
| Daily Summary | Mo–Fr 22:30 | Tagesbericht unabhängig vom Status |
| Weekend Check | Sa 10:00 | Wochenzusammenfassung |

**Wichtig:** Notifications werden nur bei Statuswechsel gesendet (Grün→Gelb, Gelb→Rot etc.), NICHT bei jedem 15-Minuten-Check. Ausnahme: Tägliche Zusammenfassung immer.

---

## Datenquellen

| Indikator | Bibliothek/API | Key nötig? |
|---|---|---|
| VIX, SP500, Futures, Global | `yfinance` | Nein |
| Yield Curve | FRED API | Ja (kostenlos) |
| Fear & Greed | CNN endpoint (requests) | Nein |
| Put/Call Ratio | CBOE endpoint (requests) | Nein |
| Buffett Indicator | FRED (GDP) + yfinance (^W5000) | Ja (FRED) |

---

## Umgebungsvariablen (.env)

```
PUSHOVER_APP_TOKEN=   # Pushover Application Token
PUSHOVER_USER_KEY=    # Pushover User Key
FRED_API_KEY=         # FRED API Key (kostenlos, fred.stlouisfed.org)
TIMEZONE=Europe/Berlin
```

---

## Installation & Deployment

### Lokaler Test (Windows)
```powershell
cd C:\Users\StefanSchauß\OneDrive\StockCRASH_WarnAPP
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # dann .env befüllen
python main.py
```

### Linux Server (24/7)
```bash
git clone https://github.com/DEIN-USERNAME/StockCRASH_WarnAPP.git
cd StockCRASH_WarnAPP
bash deploy/install.sh
# .env befüllen
sudo systemctl enable crashwarn
sudo systemctl start crashwarn
```

---

## Entwicklungshinweise für Claude

- **Niemals** `.env` in Git committen — `.gitignore` schützt es bereits
- Alle Schwellenwerte leben ausschließlich in `config.py` — nie hardcoden
- Jeder Indikator-Modul hat eine Hauptfunktion `get_signal() -> IndicatorResult`
- `IndicatorResult` ist ein `dataclass` mit: `name`, `value`, `status` (green/yellow/red), `score`, `message`
- `state_manager.py` speichert den letzten Ampelstatus in `state.json` (nicht in Git)
- Bei API-Fehlern: Indikator überspringen, im Log vermerken, keine Exception werfen
- Logging über Python `logging` Modul → `logs/crashwarn.log` (täglicher Rotation)
- Zeitzone immer aus `config.TIMEZONE` laden, nie hardcoden

---

## Git Workflow

```bash
# Feature entwickeln
git checkout -b feature/indikator-name
git add .
git commit -m "feat: beschreibung"
git push origin feature/indikator-name
# → Pull Request auf GitHub
```

Commit-Präfixe: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`
