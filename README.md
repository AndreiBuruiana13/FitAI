# FitAI

An end-to-end wearable activity-recognition prototype developed by Andrei Stefan Buruiana for his Automation and Applied Informatics bachelor thesis at UTCB, completed in June 2026.

FitAI connects an ESP32-C3 wearable to a FastAPI backend and browser dashboard. It classifies **resting, walking, running, and typing** from motion signals and provides an illustrative recovery-readiness score.

## Features

- Arduino C++ firmware: 100 Hz motion acquisition, one-second analysis windows, six extracted features, Wi-Fi telemetry and temporary offline buffering.
- ESP32-C3, MPU6050 inertial sensor, MAX30102 optical sensor and SSD1306 OLED integration.
- FastAPI REST API, JWT authentication, SQLAlchemy and SQLite persistence.
- Random Forest inference with confidence checking and heuristic fallback.
- Dashboard with live telemetry, activity predictions, session history and recovery trends.

## Recorded evaluation

The included `app/ai/model_metadata.json` records **5,441 labelled sensor windows**:

| Metric | Recorded value |
| --- | ---: |
| Holdout accuracy | 90.17% |
| Holdout macro-F1 | 89.54% |
| Five-fold cross-validation macro-F1 | 90.71% |

Features: `accel_rms`, `accel_variance`, `accel_magnitude_mean`, `gyro_rms`, `mcr`, and `iqr`. Heart rate, GPS and speed are not classifier inputs. These are development results, not an independent replication. Nearby windows can be temporally correlated; evaluation separated by session or participant would provide stronger evidence of generalization.

## Run locally

Use Python 3.12 and a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy `.env.example` to `.env`. Generate a unique signing key with this command and put its output in the local `SECRET_KEY` setting. Never commit `.env` or reuse an old key.

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` for the dashboard and `/docs` for the API. Register a local account. The database is created on startup and excluded from Git.

The serialized model and raw personal measurements are not distributed in this source-only release. Until you train a local model, the application uses motion heuristics. `scripts/retrain_from_collected.py` supports retraining from a locally collected database.

## Wearable

Install PlatformIO. Edit the placeholder settings in `fitai_glove/platformio.ini` locally: Wi-Fi name/password, reachable backend LAN address, and a local account email/password. Loopback is a safe placeholder, not the address to use from a physical ESP32. Adjust the upload port for your computer. Keep local credentials out of commits.

```bash
cd fitai_glove
pio run
pio run --target upload
pio device monitor
```

## Tests

```bash
python -m pytest -q
```

## Layout

| Path | Purpose |
| --- | --- |
| `app/` | API, database, authentication, classification and readiness services |
| `app/ai/` | Trained classifier and aggregate evaluation metadata |
| `frontend/` | Dashboard and PWA assets |
| `fitai_glove/` | PlatformIO firmware |
| `scripts/` | Local model retraining |
| `tests/` | Existing backend tests |
| `alembic/` | Historical schema migration scaffolding |

## Scope and privacy

This is a student prototype for local demonstrations, not a production service or medical device. Optical measurements and recovery estimates are illustrative, not validated diagnostic measurements. GPS speed is a placeholder in the final firmware. Recovery scoring is separate from the classifier. External frontend libraries require internet access.

The source excludes local databases, raw telemetry, device logs, backups, IDE files, local environment files and personal documents. Network/account settings are placeholders; test account values are synthetic. The backend requires a locally supplied signing key. Do not expose the development server directly to the internet.

Earlier commits contain planning documents from an earlier stage and should not be treated as evidence of the final implementation.
