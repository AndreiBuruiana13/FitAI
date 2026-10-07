from app.services.readiness import calculate_readiness_score


def test_all_none_returns_default():
    assert calculate_readiness_score() == 50.0


def test_perfect_inputs():
    score = calculate_readiness_score(sleep_hours=8.0, resting_hr=60, muscle_soreness=0.0)
    assert score > 95.0


def test_low_rhr_capped():
    score = calculate_readiness_score(resting_hr=50)
    assert score <= 100.0
    assert score >= 90.0


def test_single_metric_sleep():
    score = calculate_readiness_score(sleep_hours=8.0)
    assert score > 95.0


def test_single_metric_soreness():
    score = calculate_readiness_score(muscle_soreness=10.0)
    assert score < 5.0


def test_seven_day_avg_contributes():
    base = calculate_readiness_score(sleep_hours=7.0, resting_hr=65, muscle_soreness=3.0)
    with_avg = calculate_readiness_score(sleep_hours=7.0, resting_hr=65, muscle_soreness=3.0, seven_day_avg=80.0)
    assert base != with_avg
