# 📉 StockCRASH_WarnAPP

> **24/7 Markt-Frühwarnsystem** — erkennt drohende Börsencrashs und Korrekturen frühzeitig und sendet sofortige Push-Benachrichtigungen auf iPhone & iPad.

---

## 🎯 Warum dieses Projekt?

Börsenkorrekturen und Crashs passieren immer dann, wenn man gerade nicht am Schreibtisch sitzt — im Urlaub, auf Geschäftsreisen, beim Sport. Diese App läuft **rund um die Uhr auf einem Server**, überwacht 8 Marktindikatoren gleichzeitig und schlägt sofort Alarm, bevor es zu spät ist.

---

## 🚦 Das Ampelsystem

| Status | Bedeutung | Pushover |
|--------|-----------|----------|
| 🟢 **GRÜN** | Normaler Markt, kein erhöhtes Risiko | Kein Sound |
| 🟡 **GELB** | Erhöhtes Risiko — Vorsicht | Normaler Alert |
| 🔴 **ROT** | Crash-Alarm — sofort handeln! | Hohe Priorität + Siren-Sound |

Notifications werden **nur bei Statuswechsel** gesendet — kein Spam. Täglich gibt es zusätzlich einen Tagesbericht um 22:30 Uhr.

---

## 📊 Überwachte Indikatoren

### Kritische Signale (2 Punkte bei Rot)
| Indikator | 🟡 Warnung | 🔴 Alarm |
|-----------|-----------|----------|
| **VIX Fear Index** | > 20 | > 30 |
| **S&P 500 Intraday** | -1,5% | -3,0% |
| **S&P 500 vom ATH** | -5% | -10% |
| **Fear & Greed Index** | < 35 | < 20 |

### Frühindikatoren (1 Punkt bei Rot)
| Indikator | 🟡 Warnung | 🔴 Alarm |
|-----------|-----------|----------|
| **Yield Curve (10Y-2Y)** | < 0,30% | Invertiert |
| **Put/Call Ratio** | > 1,0 | > 1,3 |
| **E-Mini Futures (Pre-Market)** | < -0,5% | < -1,5% |
| **Buffett Indicator** | > 150% | > 180% |
| **Globale Märkte (Asien/EU)** | Ø -1% | Ø -2% |

**Ampel-Formel:** Score 0–2 = 🟢 / Score 3–5 = 🟡 / Score 6+ = 🔴

---

## ⏰ Überwachungs-Zeitplan (Europe/Berlin)

| Job | Zeit | Inhalt |
|-----|------|--------|
| Pre-Market Check | Mo–Fr 14:00 & 15:00 | Futures + Asien/EU-Märkte |
| Intraday Check | Mo–Fr 15:30–22:00 alle 15 Min | Alle Indikatoren |
| Tagesbericht | Mo–Fr 22:30 | Vollständige Zusammenfassung |
| Wochenbericht | Samstag 10:00 | Wochenrückblick |

---

## 🏗️ Architektur

```
StockCRASH_WarnAPP/
├── main.py                   # Scheduler (APScheduler)
├── config.py                 # Alle Schwellenwerte zentral
├── .env                      # API-Keys (nicht in Git)
│
├── indicators/               # Ein Modul pro Indikator
│   ├── base.py               # IndicatorResult Datenklasse
│   ├── vix.py
│   ├── sp500.py
│   ├── yield_curve.py        # FRED API
│   ├── fear_greed.py         # CNN
│   ├── futures.py            # E-Mini ES/NQ/YM
│   ├── global_markets.py     # Nikkei, DAX, FTSE, ...
│   ├── buffett_indicator.py  # Wilshire5000 / GDP
│   └── put_call_ratio.py     # CBOE
│
├── core/
│   ├── alert_engine.py       # Scoring & Ampel-Logik
│   ├── notifier.py           # Pushover Integration
│   └── state_manager.py      # Spam-Schutz
│
└── deploy/
    ├── install.sh            # Linux One-Click Setup
    └── crashwarn.service     # systemd Unit-Datei
```

---

## 🚀 Quick Start

### Voraussetzungen
- Python 3.11+
- [Pushover Account](https://pushover.net) (einmalig ~5 USD)
- [FRED API Key](https://fred.stlouisfed.org/docs/api/api_key.html) (kostenlos)
- Linux-Server, Raspberry Pi oder Windows-PC (24/7)

### Installation (Linux Server)

```bash
git clone https://github.com/DEIN-USERNAME/StockCRASH_WarnAPP.git
cd StockCRASH_WarnAPP
bash deploy/install.sh
```

### .env befüllen

```bash
nano .env
```

```env
PUSHOVER_APP_TOKEN=dein_app_token
PUSHOVER_USER_KEY=dein_user_key
FRED_API_KEY=dein_fred_key
TIMEZONE=Europe/Berlin
```

### Testen

```bash
source venv/bin/activate

# Sofortiger Markt-Check (kein Scheduler)
python main.py --test

# Pushover Verbindungstest
python main.py --notify-test
```

### Als 24/7-Service starten

```bash
sudo systemctl start crashwarn
sudo systemctl status crashwarn

# Logs live beobachten
sudo journalctl -u crashwarn -f
```

### Windows (lokaler Test)

```powershell
cd C:\Pfad\zu\StockCRASH_WarnAPP
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # dann .env befüllen
python main.py --test
```

---

## 📱 Pushover Notification Beispiele

**🟡 Gelbe Warnung:**
```
🟡 StockCrash GELB — Vorsicht: Erhöhtes Risiko
Score: 4 | 🔴 1 | 🟡 2
──────────────────────────────
🔴 VIX Fear Index: VIX=28.4 — CRASH-ALARM
🟡 S&P 500: SPX=5180 | Intraday -1.8% 🟡
🟡 Put/Call Ratio: P/C=1.12 — erhöhte Absicherung
🟢 Fear & Greed Index: F&G=42 (Fear)
```

**🔴 Rote Alarm:**
```
🔴 StockCrash ROT — ALARM: Crash-Risiko hoch!
Score: 8 | 🔴 3 | 🟡 2
──────────────────────────────
🔴 VIX Fear Index: VIX=38.1 — CRASH-ALARM
🔴 S&P 500: SPX=4820 | Intraday -3.4% 🔴
🔴 E-Mini Futures: Ø -2.1% 🔴 | S&P: -2.3% | NQ: -1.9%
🟡 Globale Märkte: Ø -1.4% 🟡
🟢 Yield Curve: Spread=+0.45%
```

---

## ⚙️ Konfiguration anpassen

Alle Schwellenwerte sind in `config.py` zentral definiert — einfach anpassen:

```python
# Beispiel: VIX-Schwellen verschärfen
VIX_YELLOW = 18.0   # Standard: 20
VIX_RED    = 25.0   # Standard: 30
```

---

## 🔧 Datenquellen

| Indikator | Quelle | API Key? |
|-----------|--------|----------|
| VIX, S&P500, Futures, Global | Yahoo Finance (`yfinance`) | ❌ Nein |
| Yield Curve | [FRED](https://fred.stlouisfed.org) | ✅ Kostenlos |
| Fear & Greed | CNN Markets | ❌ Nein |
| Put/Call Ratio | CBOE (öffentlich) | ❌ Nein |
| Buffett Indicator | FRED + Yahoo Finance | ✅ FRED kostenlos |

---

## 📋 Roadmap

- [ ] Web-Dashboard (HTML) mit Live-Ampel
- [ ] Telegram-Bot als Alternative zu Pushover
- [ ] Historische Backtests (hat die App 2020, 2022 rechtzeitig gewarnt?)
- [ ] SMS-Fallback bei kritischem Alarm
- [ ] Docker-Image für einfacheres Deployment

---

## 📄 Lizenz

MIT License — frei verwendbar für private und kommerzielle Zwecke.

---

*Gebaut mit ❤️ und Claude Code | Daten mit 15-Min-Delay — kein Finanzberatungsersatz.*
