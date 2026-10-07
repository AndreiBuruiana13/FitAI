"""Synthetic Data Generation for Demo and Testing."""

import numpy as np
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from .. import database
from .readiness import calculate_readiness_score

                        
_GPS_LAT = 44.4268
_GPS_LON = 26.1025

                                                         
_WEEKLY = {
    0: dict(sleep_mu=6.8, sleep_sd=0.5, soreness_mu=5.0, soreness_sd=0.8),              
    1: dict(sleep_mu=6.5, sleep_sd=0.5, soreness_mu=5.8, soreness_sd=0.8),              
    2: dict(sleep_mu=6.6, sleep_sd=0.5, soreness_mu=6.2, soreness_sd=0.8),              
    3: dict(sleep_mu=8.2, sleep_sd=0.4, soreness_mu=2.5, soreness_sd=0.7),                  
    4: dict(sleep_mu=6.7, sleep_sd=0.5, soreness_mu=6.5, soreness_sd=0.9),              
    5: dict(sleep_mu=7.0, sleep_sd=0.6, soreness_mu=7.0, soreness_sd=0.9),              
    6: dict(sleep_mu=9.0, sleep_sd=0.4, soreness_mu=1.5, soreness_sd=0.6),              
}

                                                         
_ACTIVITY_PARAMS = {
    "walk": dict(speed_lo=0.8, speed_hi=1.4, heart_mu=90,  heart_sd=10, accel_mu=1.1, accel_sd=0.2),
    "run":  dict(speed_lo=2.5, speed_hi=4.5, heart_mu=150, heart_sd=15, accel_mu=2.5, accel_sd=0.5),
    "bike": dict(speed_lo=5.0, speed_hi=10.0, heart_mu=125, heart_sd=12, accel_mu=1.4, accel_sd=0.3),
}

N_DAYS = 90


def seed_recovery_data(user_id: int, db: Session) -> dict:
    existing = (
        db.query(database.DailyRecovery)
        .filter(database.DailyRecovery.user_id == user_id)
        .count()
    )
    if existing > 0:
        return {"message": "Recovery data already seeded", "count": existing}

    rng = np.random.default_rng(42)
    today = datetime.now(timezone.utc).date()

                                                                             
    recovery_entries = []
    for i in range(N_DAYS):
        record_date = today - timedelta(days=N_DAYS - 1 - i)
        weekday = record_date.weekday()
        p = _WEEKLY[weekday]

                                                                                
        rhr_trend = -0.1 * i
        soreness_trend = -0.03 * i

        sleep_hours = float(np.clip(rng.normal(p["sleep_mu"], p["sleep_sd"]), 5.0, 10.0))
        resting_hr = int(np.clip(rng.normal(62.0 + rhr_trend, 3.0), 50, 75))
        muscle_soreness = float(np.clip(
            rng.normal(p["soreness_mu"] + soreness_trend, p["soreness_sd"]), 0.0, 10.0
        ))

        rec = database.DailyRecovery(
            user_id=user_id,
            date=record_date.isoformat(),
            sleep_hours=round(sleep_hours, 1),
            resting_heart_rate=resting_hr,
            muscle_soreness=round(muscle_soreness, 1),
        )
        rec.readiness_score = calculate_readiness_score(
            sleep_hours=rec.sleep_hours,
            resting_hr=rec.resting_heart_rate,
            muscle_soreness=rec.muscle_soreness,
        )
        recovery_entries.append(rec)

    db.bulk_save_objects(recovery_entries)

                                                                             
    n_sessions = int(rng.integers(15, 21))
    session_day_indices = sorted(rng.choice(N_DAYS, size=n_sessions, replace=False).tolist())
    activity_cycle = ["walk", "run", "bike"]

    for order, day_idx in enumerate(session_day_indices):
        record_date = today - timedelta(days=N_DAYS - 1 - day_idx)
        activity = activity_cycle[order % 3]
        duration_min = int(rng.integers(5, 31))             
        n_samples = duration_min * 60

        start_hour = int(rng.integers(6, 20))
        session_start = datetime(
            record_date.year, record_date.month, record_date.day,
            start_hour, 0, 0, tzinfo=timezone.utc,
        )

        session = database.WorkoutSession(
            user_id=user_id,
            start_time=session_start,
            end_time=session_start + timedelta(minutes=duration_min),
            activity_type=activity,
        )
        db.add(session)
        db.flush()                                                     

        ap = _ACTIVITY_PARAMS[activity]
                                                                 
        lat = _GPS_LAT + float(rng.uniform(-0.005, 0.005))
        lon = _GPS_LON + float(rng.uniform(-0.005, 0.005))

        telemetry = []
        for s in range(n_samples):
            speed = float(np.clip(rng.uniform(ap["speed_lo"], ap["speed_hi"]), 0.0, 50.0))
            heart = int(np.clip(rng.normal(ap["heart_mu"], ap["heart_sd"]), 30, 250))
            accel = float(np.clip(rng.normal(ap["accel_mu"], ap["accel_sd"]), 0.0, 20.0))
                                                                             
            lat += float(rng.uniform(-0.00003, 0.00003))
            lon += float(rng.uniform(-0.00003, 0.00003))

            telemetry.append(database.TelemetryData(
                session_id=session.id,
                timestamp=session_start + timedelta(seconds=s),
                speed_mps=round(speed, 3),
                heart_bpm=heart,
                accel_rms=round(accel, 3),
                gps_lat=round(lat, 6),
                gps_lon=round(lon, 6),
            ))

        db.bulk_save_objects(telemetry)

    db.commit()
    return {
        "message": f"Seeded {N_DAYS} days of recovery data and {n_sessions} workout sessions",
        "count": N_DAYS,
        "sessions": n_sessions,
    }
