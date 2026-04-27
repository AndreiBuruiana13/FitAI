# FitAI — Sistem Inteligent IoT pentru Monitorizarea Activității Fizice

[![License: MIT](https://img.shields.io/badge/License-MIT-teal.svg)](LICENSE)
[![Platform: ESP32-C3](https://img.shields.io/badge/Platform-ESP32--C3-blue.svg)](https://www.espressif.com/en/products/socs/esp32-c3)
[![Backend: FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com)
[![ML: scikit-learn](https://img.shields.io/badge/ML-scikit--learn-orange.svg)](https://scikit-learn.org)
[![Status: Proiect Licență](https://img.shields.io/badge/Status-Proiect%20Licen%C8%9B%C4%83-green.svg)]()

> **Proiect de Licență** — Universitatea Tehnică de Construcții București  
> Facultatea de Instalații · Automatică și Informatică Aplicată  
> Sesiunea Științifică Mai 2025 · Andrei Buruiană

---

## 📋 Conținutul Repository-ului

| Document | Descriere | Link |
|----------|-----------|------|
| `docs/SRS.pdf` | Software Requirements Specification v1.0 | [↗ docs/SRS.pdf](docs/SRS.pdf) |
| `docs/SDS.pdf` | Software Design Specification v1.0 | [↗ docs/SDS.pdf](docs/SDS.pdf) |
| `docs/Backlog.pdf` | Product Backlog Jira Export v1.0 | [↗ docs/Backlog.pdf](docs/Backlog.pdf) |
| `docs/Prezentare.pptx` | Prezentare PowerPoint proiect licență | [↗ docs/Prezentare.pptx](docs/Prezentare.pptx) |
| `backend/` | Server FastAPI + SQLite + ML Engine | [↗ backend/](backend/) |
| `firmware/` | PlatformIO ESP32-C3 firmware | [↗ firmware/](firmware/) |
| `frontend/` | Dashboard PWA (HTML/JS/Chart.js) | [↗ frontend/](frontend/) |

---

## 🎯 Jira — Product Backlog Scrum

> **Link proiect Jira:**  https://buru2003.atlassian.net/jira/software/projects/FITAI/boards/35/backlog

Proiectul Jira **FITAI** este configurat ca **Scrum Board** cu:
- **5 Epice:** Autentificare, Firmware ESP32, Backend API, ML Engine, Frontend PWA
- **30 User Stories** (FITAI-01 – FITAI-30)
- **116 Story Points** distribuite în **4 Sprinturi** de 2 săptămâni
- Corelat cu cerințele RF-XXX din SRS v1.0

| Epic | Stories | SP | Sprint |
|------|---------|-----|--------|
| Autentificare & Securitate | 5 | 19 | S1–S2 |
| Firmware ESP32 & Senzori | 6 | 28 | S1–S2 |
| Backend API & Bază de Date | 6 | 24 | S1–S3 |
| ML Engine & Analiză | 5 | 24 | S2–S3 |
| Frontend Dashboard & PWA | 8 | 21 | S3–S4 |
| **TOTAL** | **30** | **116** | S1–S4 |

---

## 🏗️ Arhitectura Sistemului

```
┌─────────────────────────────────────────────────────────────┐
│              Stratul de Prezentare — Frontend PWA           │
│                  HTML / JS / Chart.js / Service Worker      │
├─────────────────────────────────────────────────────────────┤
│           Stratul Aplicație — Backend REST API              │
│                   Python FastAPI / JWT Auth                 │
├─────────────────────────────────────────────────────────────┤
│          Stratul Domeniu — ML Engine (MotorFitAI)           │
│            Random Forest · Scor CNS · Trend HR              │
├─────────────────────────────────────────────────────────────┤
│           Stratul Date — SQLite + SQLAlchemy ORM            │
├─────────────────────────────────────────────────────────────┤
│         Stratul Hardware — Firmware ESP32-C3                │
│    MAX30102 · MPU6050 · NEO-6M GPS · WiFi · PlatformIO      │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Stack Tehnologic

### Hardware (Wearable IoT)
- **ESP32-C3 Supermini** — microcontroller WiFi 2.4 GHz
- **MAX30102** — senzor HR + SpO₂ (I²C)
- **MPU6050** — accelerometru + giroscop 3-ax (I²C)
- **NEO-6M** — modul GPS UART
- **Li-Po 500mAh** — alimentare (~4.5h autonomie)

### Backend
- **Python 3.11** + **FastAPI** (ASGI/uvicorn)
- **SQLite** + **SQLAlchemy ORM** + **Alembic** migrations
- **JWT** (python-jose, HS256) + **bcrypt** passwords
- **scikit-learn** RandomForestClassifier (PAMAP2 dataset)

### Frontend
- **Vanilla JS** (ES6 modules) + **Chart.js 4.x**
- **PWA** — Service Worker + Web App Manifest
- Fără framework SPA; bundle < 80 KB

---

## 🚀 Setup Rapid

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # configurează SECRET_KEY și DATABASE_URL
alembic upgrade head          # aplică schema DB
uvicorn app.main:app --reload --port 8000
# Swagger UI: http://localhost:8000/docs
```

### Firmware ESP32
```bash
cd firmware
# Editează include/config.h: WIFI_SSID, WIFI_PASSWORD, SERVER_URL, AUTH_TOKEN
pio run --target upload
pio device monitor            # serial monitor 115200 baud
```

### Frontend
```bash
# Servire statică simplă
cd frontend
python -m http.server 3000
# Accesează http://localhost:3000
```

---

## 📊 Funcționalități

| Funcționalitate | Stare |
|-----------------|-------|
| Înregistrare/Login utilizator (JWT) | ✅ Done |
| Colectare date HR + SpO₂ (MAX30102) | ✅ Done |
| Colectare IMU accelerometru (MPU6050) | ✅ Done |
| Tracking GPS (NEO-6M) | ✅ Done |
| Transmisie WiFi REST POST (1 Hz) | ✅ Done |
| Sesiuni antrenament start/stop | ✅ Done |
| Clasificare activitate ML (Random Forest) | ✅ Done |
| Scor recuperare CNS zilnic | ✅ Done |
| Dashboard live (HR zones, pie chart) | ✅ Done |
| Istoricul sesiunilor cu modal detalii | ✅ Done |
| Calendar heatmap recuperare CNS | ✅ Done |
| PWA instalabil + funcționare offline | ✅ Done |

---

## 📁 Structura Proiect

```
fitai/
├── backend/
│   ├── app/
│   │   ├── auth/          # JWT, bcrypt, rate limiting
│   │   ├── sessions/      # CRUD sesiuni antrenament
│   │   ├── telemetry/     # Ingestie date ESP32
│   │   ├── ml/            # Random Forest classifier + CNS
│   │   ├── recovery/      # Calcul scor recuperare
│   │   └── main.py        # FastAPI app entry point
│   ├── alembic/           # Migrații schema DB
│   ├── tests/             # pytest unit + integration
│   └── requirements.txt
├── firmware/
│   ├── src/
│   │   ├── sensors.cpp    # MAX30102 + MPU6050
│   │   ├── gps.cpp        # NEO-6M NMEA parser
│   │   ├── wifi_client.cpp # HTTP POST + retry
│   │   └── main.cpp       # FreeRTOS tasks
│   ├── include/config.h   # WiFi, server URL, token
│   └── platformio.ini
├── frontend/
│   ├── js/
│   │   ├── api.js         # Fetch wrapper + JWT interceptor
│   │   ├── dashboard.js   # Live charts
│   │   ├── history.js     # Session list + modal
│   │   ├── recovery.js    # CNS heatmap
│   │   └── auth.js        # Login/register
│   ├── sw.js              # Service Worker
│   └── manifest.webmanifest
├── docs/
│   ├── SRS.pdf            # Software Requirements Specification
│   ├── SDS.pdf            # Software Design Specification
│   ├── Backlog.pdf        # Jira Product Backlog export
│   └── Prezentare.pptx    # Prezentare licență
└── README.md
```

---

## 📚 Documentație

- **SRS v1.0** — Specificarea cerințelor funcționale (30+ cerințe RF-XXX)
- **SDS v1.0** — Arhitectura, ERD, API spec, scenarii UC-01–05, pseudocod ML
- **Jira** — Product Backlog: [fitai-scrum.atlassian.net](https://fitai-scrum.atlassian.net/jira/software/projects/FITAI/boards)

---

## 👤 Autor

**Andrei Buruiană**  
UTCB — Automatică și Informatică Aplicată  
GitHub: [@AndreiBuruiana13](https://github.com/AndreiBuruiana13)

---

## 📄 Licență

MIT License — vezi [LICENSE](LICENSE)
