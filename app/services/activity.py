"""Activity Classification and Metrics."""

import logging
import math
import os
import pandas as pd
import joblib
from typing import Optional

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.35

_activity_model = None

MODEL_EXPECTED_FEATURES = [
    "accel_rms",
    "accel_variance",
    "accel_magnitude_mean",
    "gyro_rms",
    "mcr",
    "iqr"
]

MODEL_EXPECTED_CLASSES = [
    "WALKING",
    "RESTING",
    "RUNNING",
    "TYPING"
]


def get_activity_model():
    global _activity_model
    if _activity_model is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = os.path.join(base_dir, "ai", "activity_model.joblib")
        try:
            _activity_model = joblib.load(model_path)
            logger.info("ML activity model loaded")

            try:
                loaded_features = list(_activity_model.feature_names_in_)
                loaded_classes = list(_activity_model.classes_)

                features_ok = (
                    set(loaded_features)
                    == set(MODEL_EXPECTED_FEATURES)
                )

                classes_ok = (
                    set(loaded_classes)
                    == set(MODEL_EXPECTED_CLASSES)
                )

                if not features_ok or not classes_ok:
                    _activity_model = None
                    print(
                        "[ML] Model schema mismatch — heuristic fallback active"
                    )
            except AttributeError:
                _activity_model = None
                print(
                    "[ML] Model missing feature_names_in_ — heuristic fallback active"
                )
        except Exception as e:
            logger.warning("ML model not found: %s", e)
            _activity_model = False
    return _activity_model if _activity_model is not False else None


def classify_activity_ai(sample) -> tuple:
    """
    Classify activity from a TelemetrySample object.
    Uses 6 IMU-derived features (no speed, no heart rate).
    Returns (label, confidence) where label is one of:
    WALKING, RESTING, RUNNING, TYPING, UNKNOWN
    """
    model = get_activity_model()
    if model is not None:
        try:
            features = pd.DataFrame([[
                sample.accel_rms,
                sample.accel_variance,
                sample.accel_magnitude_mean,
                sample.gyro_rms,
                sample.mcr,
                sample.iqr
            ]], columns=[
                "accel_rms",
                "accel_variance",
                "accel_magnitude_mean",
                "gyro_rms",
                "mcr",
                "iqr"
            ])
            probas = model.predict_proba(features)[0]
            max_proba = float(probas.max())
            predicted = str(model.classes_[probas.argmax()])

            if max_proba < CONFIDENCE_THRESHOLD:
                logger.info(
                    "ML confidence %.2f below threshold — using heuristic fallback",
                    max_proba,
                )
                                           
            else:
                return (predicted, max_proba)
        except Exception as e:
            logger.warning("ML prediction failed: %s", e)

                                                                  
    accel_rms = sample.accel_rms or 0
    mcr = sample.mcr or 0

    if accel_rms < 0.15 and mcr < 5:
        return ("RESTING", None)

    elif accel_rms < 0.15 and mcr >= 5:
        return ("TYPING", None)

    elif accel_rms < 0.5:
        return ("WALKING", None)

    else:
        return ("RUNNING", None)


def estimate_batch_calories(label: str, count: int, weight_kg: float = 75.0) -> float:
    met = {"WALKING": 3.5, "RUNNING": 8.0, "RESTING": 1.0, "TYPING": 1.5}.get(label, 1.0)
    return round((met * 3.5 * weight_kg / 200) * (count / 60), 2)


def estimate_session_soreness_delta(avg_hr: float, duration_samples: int,
                                    activity: str) -> float:
    """
    Estimates soreness increase after a workout session.
    Based on HR intensity zone × duration. Returns a delta (0.0–3.0).
    High-intensity run for 30+ min → +2.5 soreness. Easy walk → +0.2.
    """
    duration_min = duration_samples / 60.0
    intensity = {"WALKING": 0.3, "RUNNING": 1.0, "RESTING": 0.1, "TYPING": 0.2}.get(activity, 0.5)

                                               
    hr_factor = min((avg_hr or 100) / 150.0, 1.5)

    delta = intensity * hr_factor * (duration_min / 20.0)
    return round(min(delta, 3.0), 1)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    if None in (lat1, lon1, lat2, lon2):
        return 0.0
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c