"""
Retrain activity classifier from collected telemetry data in the database.

Training labels: WALKING, RESTING, RUNNING, TYPING
Feature vector:   accel_rms, accel_variance, accel_magnitude_mean, gyro_rms, mcr, iqr
Excluded:         heart_bpm, speed_mps

Usage:
    python scripts/retrain_from_collected.py [--db-path DB] [--model-out MODEL] [--meta-out META]
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import sqlite3
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    confusion_matrix,
    classification_report,
)

                                                                                
TRAINING_LABELS = ["WALKING", "RESTING", "RUNNING", "TYPING"]

FEATURE_COLUMNS = [
    "accel_rms",
    "accel_variance",
    "accel_magnitude_mean",
    "gyro_rms",
    "mcr",
    "iqr",
]

MIN_SAMPLES_PER_CLASS = 50

                       
MIN_ACCURACY = 0.80
MIN_MACRO_F1 = 0.75
MIN_TYPING_F1 = 0.70


def load_from_db(db_path: str) -> pd.DataFrame:
    """Load labelled telemetry rows from the database."""
    if not os.path.exists(db_path):
        print(f"ERROR: Database not found at '{db_path}'")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    query = f"""
        SELECT {', '.join(FEATURE_COLUMNS)}, label
        FROM telemetry_data
        WHERE label IN ({','.join('?' for _ in TRAINING_LABELS)})
    """
    df = pd.read_sql_query(query, conn, params=TRAINING_LABELS)
    conn.close()

    print(f"Loaded {len(df)} rows from database")
    return df


def validate_data(df: pd.DataFrame) -> pd.DataFrame:
    """Run NaN/Inf checks and class-count validation. Return cleaned DataFrame."""
    X = df[FEATURE_COLUMNS].copy()
    y = df["label"].copy()

                         
    nan_mask = X.isna().any(axis=1)
    if nan_mask.any():
        print(f"[VALIDATION] Dropping {nan_mask.sum()} row(s) with NaN values")
        X = X[~nan_mask]
        y = y[~nan_mask]

                         
    inf_mask = np.isinf(X.select_dtypes(include=[np.number])).any(axis=1)
    if inf_mask.any():
        print(f"[VALIDATION] Dropping {inf_mask.sum()} row(s) with Inf values")
        X = X[~inf_mask]
        y = y[~inf_mask]

    df_clean = X.copy()
    df_clean["label"] = y

                                  
    counts = df_clean["label"].value_counts()
    print("\nClass distribution:")
    for lbl in TRAINING_LABELS:
        cnt = counts.get(lbl, 0)
        print(f"  {lbl:10s}: {cnt:6d}  {'✓' if cnt >= MIN_SAMPLES_PER_CLASS else '✗ BELOW MINIMUM'}")

                                   
    if len(counts) > 0:
        max_cnt = counts.max()
        min_cnt = counts.min()
        if max_cnt > 0 and min_cnt > 0:
            ratio = max_cnt / min_cnt
            if ratio > 3:
                print(f"\n[WARNING] Class imbalance ratio {ratio:.1f}:1 (max={max_cnt}, min={min_cnt})")
            else:
                print(f"\nClass imbalance ratio {ratio:.1f}:1 — acceptable")

                               
    below = [lbl for lbl in TRAINING_LABELS if counts.get(lbl, 0) < MIN_SAMPLES_PER_CLASS]
    if below:
        print(
            f"\nABORTED: {len(below)} class(es) below {MIN_SAMPLES_PER_CLASS}-sample minimum: "
            f"{', '.join(below)}"
        )
        sys.exit(0)                                                              

    return df_clean


def train_and_evaluate(df: pd.DataFrame, model_out: str, meta_out: str) -> None:
    """Train Random Forest, evaluate, and save model + metadata."""
    X = df[FEATURE_COLUMNS].values
    y = df["label"].values
    classes = sorted(df["label"].unique().tolist())

    print(f"\nFeature matrix: {X.shape[0]} samples × {X.shape[1]} features")
    print(f"Classes: {classes}")

                                              
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Train: {len(X_train)}  |  Holdout: {len(X_test)}")

                 
    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

                                              
    cv_scores = cross_val_score(
        model, X_train, y_train, cv=5, scoring="f1_macro", n_jobs=-1
    )
    cv_macro_f1 = np.mean(cv_scores)
    print(f"\n5-fold CV macro F1: {cv_macro_f1:.4f} (±{np.std(cv_scores):.4f})")

                              
    y_pred = model.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    macro_f1 = f1_score(y_test, y_pred, average="macro")
    per_class = {
        lbl: round(f1_score(y_test, y_pred, labels=[lbl], average=None)[0], 4)
        for lbl in classes
    }
    cm = confusion_matrix(y_test, y_pred, labels=classes)

    print(f"\nHoldout evaluation ({len(X_test)} samples):")
    print(f"  Accuracy : {acc:.4f}  (threshold ≥ {MIN_ACCURACY})")
    print(f"  Macro F1 : {macro_f1:.4f}  (threshold ≥ {MIN_MACRO_F1})")
    print(f"  Per-class F1:")
    for lbl, f1 in per_class.items():
        threshold = MIN_TYPING_F1 if lbl == "TYPING" else None
        marker = f" (threshold ≥ {threshold})" if threshold else ""
        ok = " ✓" if (threshold is None or f1 >= threshold) else " ✗ FAIL"
        print(f"    {lbl:10s}: {f1:.4f}{marker}{ok}")

    print(f"\nConfusion Matrix ({' | '.join(classes)}):")
    header = " " * 12 + "".join(f"{c:>10s}" for c in classes)
    print(header)
    for i, lbl in enumerate(classes):
        row_vals = "".join(f"{val:10d}" for val in cm[i])
        print(f"  {lbl:10s}{row_vals}")

    print(f"\nFull classification report:")
    print(classification_report(y_test, y_pred, target_names=classes, zero_division=0))

                           
    fail = False
    if acc < MIN_ACCURACY:
        print(f"ACCURACY FAIL: {acc:.4f} < {MIN_ACCURACY}")
        fail = True
    if macro_f1 < MIN_MACRO_F1:
        print(f"MACRO F1 FAIL: {macro_f1:.4f} < {MIN_MACRO_F1}")
        fail = True
    if "TYPING" in per_class and per_class["TYPING"] < MIN_TYPING_F1:
        print(f"TYPING F1 FAIL: {per_class['TYPING']:.4f} < {MIN_TYPING_F1}")
        fail = True

    if fail:
        print("\nABORTED: Acceptance thresholds not met — model NOT saved.")
        sys.exit(1)

                      
    os.makedirs(os.path.dirname(model_out), exist_ok=True)
    model.feature_names_in_ = np.array([
        "accel_rms", "accel_variance", "accel_magnitude_mean",
        "gyro_rms", "mcr", "iqr"
    ])
    joblib.dump(model, model_out)
    print(f"\nModel saved to {model_out}")

                         
    sample_counts = {lbl: int((y == lbl).sum()) for lbl in classes}
    metadata = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "feature_list": FEATURE_COLUMNS,
        "class_list": classes,
        "sample_counts": sample_counts,
        "total_samples": int(len(y)),
        "cv_macro_f1_5fold": round(float(cv_macro_f1), 4),
        "holdout_accuracy": round(float(acc), 4),
        "holdout_macro_f1": round(float(macro_f1), 4),
        "per_class_f1": per_class,
        "model_type": "RandomForestClassifier",
        "hyperparameters": {
            "n_estimators": 100,
            "random_state": 42,
            "class_weight": "balanced",
            "n_jobs": -1,
        },
    }

    os.makedirs(os.path.dirname(meta_out), exist_ok=True)
    with open(meta_out, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Metadata saved to {meta_out}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Retrain activity classifier from collected telemetry"
    )
    parser.add_argument(
        "--db-path",
        default=os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "fitai_professional.db",
        ),
        help="Path to the SQLite database (default: fitai/fitai_professional.db)",
    )
    parser.add_argument(
        "--model-out",
        default=os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "app", "ai", "activity_model.joblib",
        ),
        help="Output path for trained model (default: app/ai/activity_model.joblib)",
    )
    parser.add_argument(
        "--meta-out",
        default=os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "app", "ai", "model_metadata.json",
        ),
        help="Output path for metadata JSON (default: app/ai/model_metadata.json)",
    )
    args = parser.parse_args()

             
    df = load_from_db(args.db_path)

    if len(df) == 0:
        print("\nABORTED: No labelled samples found in database.")
        print("This is a PASS condition — retrain is not possible without collected data.")
        sys.exit(0)

                 
    df_clean = validate_data(df)

                                
    train_and_evaluate(df_clean, args.model_out, args.meta_out)


if __name__ == "__main__":
    main()