"""Central Nervous System (CNS) Recovery & Readiness Calculation.

Important:
Internally, `resting_hr` is kept as a parameter name for backend compatibility.
In the UI and interpretation, this value should be treated as "measured pulse",
not medical resting heart rate.
"""

from typing import Optional


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def normalize_sleep_score(sleep_hours: Optional[float]) -> Optional[float]:
    """
    Sleep readiness score, 0–100.

    Logic:
    - 7.5–9h is optimal.
    - 6–7.5h is acceptable.
    - under 6h is penalized.
    - over 10h is not treated as infinitely good.
    """
    if sleep_hours is None:
        return None

    try:
        h = float(sleep_hours)
    except (TypeError, ValueError):
        return None

    if h < 0 or h > 24:
        return None

    if 7.5 <= h <= 9.0:
        return 100.0

    if 6.0 <= h < 7.5:
        return 70.0 + ((h - 6.0) / 1.5) * 30.0

    if 4.0 <= h < 6.0:
        return 35.0 + ((h - 4.0) / 2.0) * 35.0

    if h < 4.0:
        return 20.0

    if 9.0 < h <= 10.0:
        return 90.0

    if 10.0 < h <= 11.0:
        return 75.0

    return 60.0


def normalize_soreness_score(muscle_soreness: Optional[float]) -> Optional[float]:
    """
    Muscle soreness readiness score, 0–100.

    0 discomfort = 100 readiness.
    10 discomfort = 0 readiness.
    """
    if muscle_soreness is None:
        return None

    try:
        soreness = float(muscle_soreness)
    except (TypeError, ValueError):
        return None

    soreness = clamp(soreness, 0.0, 10.0)
    return 100.0 - soreness * 10.0


def normalize_measured_pulse_score(resting_hr: Optional[int]) -> Optional[float]:
    """
    Measured pulse readiness score, 0–100.

    This is NOT treated as medical resting heart rate.
    It is only a secondary biometric indicator.

    The previous algorithm penalized values above 80 too aggressively.
    This version uses a softer interpretation:
    - 55–85 bpm: good / normal measured range
    - 86–100 bpm: moderate penalty
    - >100 bpm: stronger penalty
    - very low values are also treated cautiously
    """
    if resting_hr is None:
        return None

    try:
        hr = float(resting_hr)
    except (TypeError, ValueError):
        return None

    if hr < 30 or hr > 220:
        return None

    if 55 <= hr <= 85:
        return 90.0

    if 45 <= hr < 55:
        return 80.0

    if 86 <= hr <= 95:
        return 75.0

    if 96 <= hr <= 105:
        return 60.0

    if 106 <= hr <= 120:
        return 40.0

    if hr > 120:
        return 25.0

    return 60.0


def normalize_seven_day_score(seven_day_avg: Optional[float]) -> Optional[float]:
    """
    Seven-day average readiness score, 0–100.

    This is used as a small stabilizer only.
    It should not dominate the daily calculation.
    """
    if seven_day_avg is None:
        return None

    try:
        avg = float(seven_day_avg)
    except (TypeError, ValueError):
        return None

    return clamp(avg, 0.0, 100.0)


def calculate_readiness_score(
    sleep_hours: Optional[float] = None,
    resting_hr: Optional[int] = None,
    muscle_soreness: Optional[float] = None,
    seven_day_avg: Optional[float] = None,
) -> float:
    """
    CNS Readiness Score, 0–100.

    Updated weighting:
    - Sleep: 40%
    - Muscle soreness: 40%
    - Measured pulse: 15%
    - Seven-day average: 5%

    Reason:
    The glove/app cannot guarantee true resting-heart-rate conditions.
    Therefore, pulse is used as a secondary signal, not a dominant factor.
    """

    sleep = normalize_sleep_score(sleep_hours)
    soreness = normalize_soreness_score(muscle_soreness)
    pulse = normalize_measured_pulse_score(resting_hr)
    ma7 = normalize_seven_day_score(seven_day_avg)

    components = {}

    if sleep is not None:
        components["sleep"] = (sleep, 0.40)

    if soreness is not None:
        components["soreness"] = (soreness, 0.40)

    if pulse is not None:
        components["pulse"] = (pulse, 0.15)

    if ma7 is not None:
        components["ma7"] = (ma7, 0.05)

    if not components:
        return 50.0

    total_weight = sum(weight for _, weight in components.values())
    weighted_sum = sum(score * weight for score, weight in components.values())

    final_score = weighted_sum / total_weight
    return round(clamp(final_score), 2)


def interpret_readiness(score: float) -> str:
    if score is None:
        return "⏳ Fără date: înregistrează valorile de astăzi pentru a primi o recomandare."

    try:
        score = float(score)
    except (TypeError, ValueError):
        return "⏳ Fără date: înregistrează valorile de astăzi pentru a primi o recomandare."

    if score >= 90:
        return "🌟 Excelent: zi cu potențial ridicat de performanță. Potrivită pentru antrenament intens."
    elif score >= 70:
        return "✅ Bun: capacitate normală de antrenament. Poți urma antrenamentul planificat."
    elif score >= 50:
        return "⚠️ Moderat: accent pe recuperare. Se recomandă activitate ușoară."
    else:
        return "🚨 Scăzut: se recomandă o zi de pauză sau doar recuperare activă."