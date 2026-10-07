"""Recovery routes: seed, trend, log, and readiness forecast."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import numpy as np
from .. import database, models, auth
from ..services.readiness import calculate_readiness_score, interpret_readiness
from ..services.seeding import seed_recovery_data

router = APIRouter(prefix="/recovery", tags=["recovery"])


def _get_seven_day_avg(user_id: int, before_date: str, db: Session):
    """Query mean readiness score from the 7 days before the given date."""
    recent = (
        db.query(database.DailyRecovery.readiness_score)
        .filter(
            database.DailyRecovery.user_id == user_id,
            database.DailyRecovery.date < before_date,
        )
        .order_by(database.DailyRecovery.date.desc())
        .limit(7)
        .all()
    )
    scores = [r[0] for r in recent if r[0] is not None]
    if scores:
        return sum(scores) / len(scores)
    return None


@router.post("/seed")
def seed_recovery(
    db: Session = Depends(database.get_db),
    current_user: database.User = Depends(auth.get_current_user),
):
    return seed_recovery_data(current_user.id, db)


@router.get("/trend", response_model=models.RecoveryTrendResponse)
def get_recovery_trend(
    days: int = 30,
    db: Session = Depends(database.get_db),
    current_user: database.User = Depends(auth.get_current_user),
):
    cutoff_date = (datetime.now(timezone.utc).date() - timedelta(days=days)).isoformat()
    records = (
        db.query(database.DailyRecovery)
        .filter(
            database.DailyRecovery.user_id == current_user.id,
            database.DailyRecovery.date >= cutoff_date,
        )
        .order_by(database.DailyRecovery.date.asc())
        .all()
    )
    if not records:
        return {
            "dates": [],
            "readiness_scores": [],
            "sleep_hours_list": [],
            "resting_hr_list": [],
            "soreness_list": [],
            "average_readiness": 0.0,
            "trend": "no_data",
        }

    dates = [r.date for r in records]
    readiness_scores = [r.readiness_score or 50.0 for r in records]
    sleep_hours_list = [r.sleep_hours for r in records]
    resting_hr_list = [r.resting_heart_rate for r in records]
    soreness_list = [r.muscle_soreness for r in records]

    avg_readiness = np.mean(readiness_scores) if readiness_scores else 0.0
    trend_slope = None
    if len(readiness_scores) >= 4:
        coeffs = np.polyfit(range(len(readiness_scores)), readiness_scores, 1)
        trend_slope = round(float(coeffs[0]), 3)
        if trend_slope > 0.5:
            trend = "improving"
        elif trend_slope < -0.5:
            trend = "declining"
        else:
            trend = "stable"
    else:
        trend = "insufficient_data"

    return {
        "dates": dates,
        "readiness_scores": [round(s, 1) for s in readiness_scores],
        "sleep_hours_list": sleep_hours_list,
        "resting_hr_list": resting_hr_list,
        "soreness_list": soreness_list,
        "average_readiness": round(avg_readiness, 1),
        "trend": trend,
        "trend_slope": trend_slope,
    }


@router.post("/log", response_model=models.DailyRecoveryResponse)
def log_recovery(
    data: models.DailyRecoveryData,
    db: Session = Depends(database.get_db),
    current_user: database.User = Depends(auth.get_current_user),
):
    existing = (
        db.query(database.DailyRecovery)
        .filter(
            database.DailyRecovery.user_id == current_user.id,
            database.DailyRecovery.date == data.date.isoformat(),
        )
        .first()
    )
    if existing:
        existing.sleep_hours = data.sleep_hours
        existing.resting_heart_rate = data.resting_heart_rate
        existing.muscle_soreness = data.muscle_soreness
        existing.updated_at = datetime.now(timezone.utc)
    else:
        existing = database.DailyRecovery(
            user_id=current_user.id,
            date=data.date.isoformat(),
            sleep_hours=data.sleep_hours,
            resting_heart_rate=data.resting_heart_rate,
            muscle_soreness=data.muscle_soreness,
        )
        db.add(existing)

    seven_day_avg = _get_seven_day_avg(current_user.id, data.date.isoformat(), db)

    existing.readiness_score = calculate_readiness_score(
        sleep_hours=existing.sleep_hours,
        resting_hr=existing.resting_heart_rate,
        muscle_soreness=existing.muscle_soreness,
        seven_day_avg=seven_day_avg,
    )

    db.commit()
    db.refresh(existing)
    return existing


@router.get("/readiness-forecast")
def forecast_readiness(
    db: Session = Depends(database.get_db),
    current_user: database.User = Depends(auth.get_current_user),
):
    today = datetime.now(timezone.utc).date().isoformat()
    today_record = (
        db.query(database.DailyRecovery)
        .filter(
            database.DailyRecovery.user_id == current_user.id,
            database.DailyRecovery.date == today,
        )
        .first()
    )
    if not today_record:
        week_ago = (datetime.now(timezone.utc).date() - timedelta(days=7)).isoformat()
        recent_records = (
            db.query(database.DailyRecovery)
            .filter(
                database.DailyRecovery.user_id == current_user.id,
                database.DailyRecovery.date > week_ago,
            )
            .all()
        )

        if recent_records:
            avg_sleep = np.nanmean([r.sleep_hours for r in recent_records])
            avg_rhr = int(np.nanmean([r.resting_heart_rate for r in recent_records] or [60]))
            avg_soreness = np.nanmean([r.muscle_soreness for r in recent_records])
        else:
            avg_sleep = None
            avg_rhr = None
            avg_soreness = None

        seven_day_avg = _get_seven_day_avg(current_user.id, today, db)
        readiness_score = calculate_readiness_score(avg_sleep, avg_rhr, avg_soreness, seven_day_avg)
        return {
            "date": today,
            "readiness_score": readiness_score,
            "recommendation": interpret_readiness(readiness_score),
            "is_forecast": True,
            "source": "7-day average",
        }

    score = today_record.readiness_score if today_record.readiness_score is not None else 50.0
    return {
        "date": today,
        "sleep_hours": today_record.sleep_hours,
        "resting_heart_rate": today_record.resting_heart_rate,
        "muscle_soreness": today_record.muscle_soreness,
        "readiness_score": score,
        "recommendation": interpret_readiness(score),
        "is_forecast": False,
        "source": "logged data",
    }


@router.get("/forecast-7day", response_model=models.RecoveryForecastResponse)
def forecast_7day(
    db: Session = Depends(database.get_db),
    current_user: database.User = Depends(auth.get_current_user),
):
    """
    Projects readiness for the next 7 days using linear regression on
    the last 14 days of logged data. Returns dates + predicted scores.
    """
    two_weeks_ago = (datetime.now(timezone.utc).date() - timedelta(days=14)).isoformat()
    records = db.query(database.DailyRecovery)\
        .filter(
            database.DailyRecovery.user_id == current_user.id,
            database.DailyRecovery.date >= two_weeks_ago
        )\
        .order_by(database.DailyRecovery.date.asc()).all()

    if len(records) < 4:
        return {
            "forecast": [],
            "trend_direction": "insufficient_data",
            "slope_per_day": 0.0,
            "message": "Need at least 4 days of data for forecast"
        }

    scores = [r.readiness_score or 50.0 for r in records]
    x = np.arange(len(scores))

                       
    coeffs = np.polyfit(x, scores, 1)
    slope, intercept = coeffs[0], coeffs[1]

    today = datetime.now(timezone.utc).date()
    forecast = []
    for i in range(1, 8):
        projected_x = len(scores) + i - 1
        projected_score = float(np.clip(slope * projected_x + intercept, 0, 100))
        forecast_date = (today + timedelta(days=i)).isoformat()
        forecast.append({
            "date": forecast_date,
            "predicted_score": round(projected_score, 1),
            "recommendation": interpret_readiness(projected_score)
        })

    trend_direction = "improving" if slope > 0.5 else "declining" if slope < -0.5 else "stable"

    return {
        "forecast": forecast,
        "trend_direction": trend_direction,
        "slope_per_day": round(slope, 3),
        "message": f"7-day projection based on {len(records)} historical records"
    }


@router.get("/alerts")
def get_recovery_alerts(
    db: Session = Depends(database.get_db),
    current_user: database.User = Depends(auth.get_current_user),
):
    """
    Returns alert if readiness has been below 50 for 3+ consecutive days.
    Clinically meaningful: indicates accumulated fatigue requiring intervention.
    """
    recent = db.query(database.DailyRecovery)\
        .filter(database.DailyRecovery.user_id == current_user.id)\
        .order_by(database.DailyRecovery.date.desc())\
        .limit(7).all()

    if not recent:
        return {"alert": False, "message": "No recovery data logged"}

                                                           
    consecutive_low = 0
    for r in recent:
        if (r.readiness_score or 50) < 50:
            consecutive_low += 1
        else:
            break

    if consecutive_low >= 3:
        return {
            "alert": True,
            "severity": "high" if consecutive_low >= 5 else "moderate",
            "consecutive_low_days": consecutive_low,
            "message": f"⚠️ {consecutive_low} consecutive days below 50% readiness. "
                       f"Recommend 1–2 full rest days before next training load."
        }

    return {
        "alert": False,
        "consecutive_low_days": consecutive_low,
        "message": "Recovery levels acceptable"
    }