"""Telemetry routes: ingest, activity history, stats, and export."""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from .. import database, models, auth
from ..services.activity import (
    classify_activity_ai,
    estimate_batch_calories,
    estimate_session_soreness_delta,
    haversine_distance,
)
from ..services.readiness import calculate_readiness_score

router = APIRouter()


@router.post("/ingest", response_model=models.IngestResponse)
def ingest(
    sample: models.TelemetrySample,
    db: Session = Depends(database.get_db),
    current_user: database.User = Depends(auth.get_current_user),
):
                                                                              
    five_min_ago = datetime.utcnow() - timedelta(minutes=5)
    active_session = (
        db.query(database.WorkoutSession)
        .filter(
            database.WorkoutSession.user_id == current_user.id,
            database.WorkoutSession.updated_at >= five_min_ago,
        )
        .order_by(database.WorkoutSession.updated_at.desc())
        .first()
    )

    if active_session:
        session = active_session
    else:
        session = database.WorkoutSession(user_id=current_user.id)
        db.add(session)
        db.commit()
        db.refresh(session)

                                                     
    dominant_label, _confidence = classify_activity_ai(sample)

    resolved_ts = datetime.utcnow()
    telemetry = database.TelemetryData(
        session_id=session.id,
        timestamp=resolved_ts,
        speed_mps=sample.speed_mps,
        heart_bpm=sample.heart_bpm,
        accel_rms=sample.accel_rms,
        accel_variance=sample.accel_variance,
        accel_magnitude_mean=sample.accel_magnitude_mean,
        gyro_rms=sample.gyro_rms,
        mcr=sample.mcr,
        iqr=sample.iqr,
        spo2=sample.spo2,
        gps_lat=sample.gps_lat,
        gps_lon=sample.gps_lon,
        label=dominant_label,
    )
    db.add(telemetry)

                               
    session.activity_type = dominant_label
    session.max_speed = max(session.max_speed or 0, sample.speed_mps)
    session.updated_at = datetime.utcnow()
    if session.start_time is None or resolved_ts < session.start_time:
        session.start_time = resolved_ts
    if session.end_time is None or resolved_ts > session.end_time:
        session.end_time = resolved_ts
    db.commit()
                                             
    avg_hr_val = sample.heart_bpm or 100.0
    soreness_delta = estimate_session_soreness_delta(avg_hr_val, 1, dominant_label)

    today_str = datetime.utcnow().date().isoformat()
    today_recovery = db.query(database.DailyRecovery)\
        .filter(database.DailyRecovery.user_id == current_user.id,
                database.DailyRecovery.date == today_str).first()

    if today_recovery:
        new_soreness = min((today_recovery.muscle_soreness or 0) + soreness_delta, 10.0)
        today_recovery.muscle_soreness = round(new_soreness, 1)
        today_recovery.readiness_score = calculate_readiness_score(
            sleep_hours=today_recovery.sleep_hours,
            resting_hr=today_recovery.resting_heart_rate,
            muscle_soreness=today_recovery.muscle_soreness
        )
        db.commit()

    return {
        "inserted": 1,
        "session_id": session.id,
        "activity_type": dominant_label,
        "message": f"Recorded {dominant_label}",
    }


@router.get("/activities")
def activities(
    limit: int = 50,
    session_id: int = None,
    db: Session = Depends(database.get_db),
    current_user: database.User = Depends(auth.get_current_user),
):
    query = (
        db.query(database.TelemetryData, database.WorkoutSession.activity_type)
        .join(database.WorkoutSession)
        .filter(database.WorkoutSession.user_id == current_user.id)
    )
    if session_id is not None:
        query = query.filter(database.TelemetryData.session_id == session_id)
    if session_id is not None:
        order_expr = database.TelemetryData.timestamp.asc()
    else:
        order_expr = database.TelemetryData.id.desc()
    results = (
        query.order_by(order_expr)
        .limit(limit)
        .all()
    )

    print("\n========== ACTIVITIES DEBUG ==========")
    for r in results[:5]:
        print(
            "ID=", r[0].id,
            " TIMESTAMP=", r[0].timestamp,
            " LABEL=", r[0].label,
            " HR=", r[0].heart_bpm
        )
    print("======================================\n")

    formatted_data = []
    for t, lbl in results:
        if t.heart_bpm and t.accel_rms:
            denominator = t.heart_bpm * t.accel_rms
            efficiency = round((t.speed_mps / denominator) * 1000, 2)
        else:
            efficiency = None
        formatted_data.append({
            "timestamp": t.timestamp.isoformat(),
            "speed_mps": t.speed_mps,
            "heart_bpm": t.heart_bpm,
            "accel_rms": t.accel_rms,
            "accel_variance": t.accel_variance,
            "accel_magnitude_mean": t.accel_magnitude_mean,
            "gyro_rms": t.gyro_rms,
            "mcr": t.mcr,
            "iqr": t.iqr,
            "spo2": t.spo2,
            "efficiency": efficiency,
            "label": lbl or "unknown",
            "gps_lat": t.gps_lat,
            "gps_lon": t.gps_lon,
        })

    return formatted_data


@router.get("/sessions")
def sessions(
    db: Session = Depends(database.get_db),
    current_user: database.User = Depends(auth.get_current_user),
):
    sessions = (
        db.query(database.WorkoutSession)
        .filter(database.WorkoutSession.user_id == current_user.id)
        .order_by(database.WorkoutSession.start_time.desc())
        .all()
    )

    session_list = []
    for s in sessions:
        points = (
            db.query(database.TelemetryData)
            .filter(database.TelemetryData.session_id == s.id)
            .order_by(database.TelemetryData.timestamp.asc())
            .all()
        )

        total_distance = 0.0
        valid_hr = [p.heart_bpm for p in points if p.heart_bpm is not None and 30 <= p.heart_bpm <= 220]
        avg_hr = round(sum(valid_hr) / len(valid_hr), 1) if valid_hr else None
        for i in range(1, len(points)):
            total_distance += haversine_distance(
                points[i - 1].gps_lat,
                points[i - 1].gps_lon,
                points[i].gps_lat,
                points[i].gps_lon,
            )

        duration_min = None
        if s.start_time and s.end_time:
            duration_min = round((s.end_time - s.start_time).total_seconds() / 60, 1)

        valid_labels = [p.label for p in points if p.label in ("WALKING", "RUNNING", "RESTING", "TYPING")]
        if valid_labels:
            most_common = max(set(valid_labels), key=valid_labels.count)
        else:
            most_common = s.activity_type

        session_list.append({
            "session_id": s.id,
            "activity_type": most_common,
            "start_time": s.start_time.isoformat() if s.start_time else None,
            "end_time": s.end_time.isoformat() if s.end_time else None,
            "duration_min": duration_min,
            "avg_heart_rate": avg_hr,
            "max_speed": s.max_speed,
            "sample_count": len(points),
            "distance_km": round(total_distance, 3),
        })

    return session_list


@router.get("/stats")
def get_stats(
    db: Session = Depends(database.get_db),
    current_user: database.User = Depends(auth.get_current_user),
):
    max_speed = (
        db.query(database.TelemetryData.speed_mps)
        .join(database.WorkoutSession)
        .filter(database.WorkoutSession.user_id == current_user.id)
        .order_by(database.TelemetryData.speed_mps.desc())
        .first()
    )
    max_speed_value = max_speed[0] if max_speed and max_speed[0] is not None else 0.0

    total_sessions = (
        db.query(database.WorkoutSession)
        .filter(database.WorkoutSession.user_id == current_user.id)
        .count()
    )

    latest_session = (
        db.query(database.WorkoutSession)
        .filter(database.WorkoutSession.user_id == current_user.id)
        .order_by(database.WorkoutSession.id.desc())
        .first()
    )

    session_dist_km = 0.0
    if latest_session:
        points = (
            db.query(database.TelemetryData)
            .filter(database.TelemetryData.session_id == latest_session.id)
            .order_by(database.TelemetryData.timestamp.asc())
            .all()
        )
        for i in range(1, len(points)):
            session_dist_km += haversine_distance(
                points[i - 1].gps_lat,
                points[i - 1].gps_lon,
                points[i].gps_lat,
                points[i].gps_lon,
            )

    week_start = datetime.utcnow() - timedelta(days=7)
    weekly_points = (
        db.query(database.TelemetryData, database.WorkoutSession.activity_type)
        .join(database.WorkoutSession)
        .filter(
            database.WorkoutSession.user_id == current_user.id,
            database.TelemetryData.timestamp >= week_start,
        )
        .order_by(database.TelemetryData.timestamp.asc())
        .all()
    )

    week_days = set()
    week_heart_rates = []
    weight_kg = current_user.weight_kg or 75.0
    MET_VALUES = {"WALKING": 3.5, "RUNNING": 8.0, "RESTING": 1.0, "TYPING": 1.5, "UNKNOWN": 4.0}
    weekly_calories = 0.0

    for telemetry, label in weekly_points:
        if telemetry.timestamp:
            week_days.add(telemetry.timestamp.date())
        if telemetry.heart_bpm is not None:
            week_heart_rates.append(telemetry.heart_bpm)

        met = MET_VALUES.get(label or "UNKNOWN", 4.0)
        weekly_calories += met * 3.5 * weight_kg / 200 / 60

    average_week_hr = round(sum(week_heart_rates) / len(week_heart_rates), 0) if week_heart_rates else None

    week_sessions = (
        db.query(database.WorkoutSession)
        .filter(
            database.WorkoutSession.user_id == current_user.id,
            database.WorkoutSession.end_time >= week_start,
        )
        .all()
    )
    week_active_minutes = 0
    for s in week_sessions:
        if s.start_time and s.end_time:
            week_active_minutes += (s.end_time - s.start_time).total_seconds() / 60
    week_active_minutes = round(week_active_minutes)

    return {
        "max_speed": round(max_speed_value, 2),
        "total_sessions": total_sessions,
        "session_distance_km": round(session_dist_km, 3),
        "week_active_days": len(week_days),
        "week_avg_hr": average_week_hr,
        "week_calories": round(weekly_calories),
        "week_active_minutes": week_active_minutes,
    }


@router.get("/export")
def export_data(
    db: Session = Depends(database.get_db),
    current_user: database.User = Depends(auth.get_current_user),
):
    def generate():
        yield "ID,Session_ID,Timestamp,Speed_mps,Heart_BPM,Accel_RMS\n"
        query = (
            db.query(database.TelemetryData)
            .join(database.WorkoutSession)
            .filter(database.WorkoutSession.user_id == current_user.id)
            .order_by(database.TelemetryData.id)
            .yield_per(500)
        )
        for row in query:
            yield f"{row.id},{row.session_id},{row.timestamp},{row.speed_mps},{row.heart_bpm},{row.accel_rms}\n"

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=fitai_export.csv"},
    )


@router.get("/latest")
def get_latest(
    db: Session = Depends(database.get_db),
    current_user: database.User = Depends(auth.get_current_user),
):
    row = (
        db.query(database.TelemetryData, database.WorkoutSession.activity_type)
        .join(database.WorkoutSession)
        .filter(database.WorkoutSession.user_id == current_user.id)
        .order_by(database.TelemetryData.id.desc())
        .first()
    )
    if not row:
        return {"status": "no_data"}
    telemetry_row, ai_label = row
    return {
        "status":                "ok",
        "timestamp":             telemetry_row.timestamp.isoformat() if telemetry_row.timestamp else None,
        "label":                 ai_label or "UNKNOWN",
        "heart_bpm":             telemetry_row.heart_bpm,
        "spo2":                  telemetry_row.spo2,
        "accel_rms":             telemetry_row.accel_rms,
        "accel_variance":        telemetry_row.accel_variance,
        "accel_magnitude_mean":  telemetry_row.accel_magnitude_mean,
        "gyro_rms":              telemetry_row.gyro_rms,
        "mcr":                   telemetry_row.mcr,
        "iqr":                   telemetry_row.iqr,
    }
