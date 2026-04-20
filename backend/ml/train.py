"""
AutoJustice AI NEXUS — ML Model Training
Run: python train.py  (from backend/ml/ directory)
Trains and saves 3 models to backend/ml/models/
"""
import sys
import os
import json
import logging
from datetime import datetime
from pathlib import Path

# ── Ensure this module can import features.py and dataset.py ──────────────────
_HERE = Path(__file__).parent.resolve()
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import LinearSVC
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

from features import FEATURE_NAMES
from dataset import (
    generate_fake_detection_dataset,
    generate_crime_dataset,
    generate_risk_dataset,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

MODELS_DIR = _HERE / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

CRIME_CATEGORIES = [
    "Financial Crime",
    "Online Harassment",
    "Identity Theft",
    "Extortion",
    "Child Safety",
    "Data Breach",
    "Cyber Fraud",
    "Impersonation",
    "Other Cybercrime",
]


def train_fake_detector() -> dict:
    """
    Train RandomForestClassifier on 18-feature vectors.
    Labels: 0=fake, 1=genuine, 2=review
    """
    logger.info("=" * 60)
    logger.info("Training Fake Detection Classifier (RandomForest)")
    logger.info("=" * 60)

    logger.info("  Generating dataset...")
    X_raw, y_raw = generate_fake_detection_dataset()
    X = np.array(X_raw, dtype=np.float32)
    y = np.array(y_raw, dtype=np.int32)

    logger.info(f"  Dataset: {len(X)} samples | "
                f"Genuine={sum(y==1)}, Fake={sum(y==0)}, Review={sum(y==2)}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=12,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    logger.info("  Fitting model...")
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)

    logger.info(f"  Test accuracy: {acc:.4f}")
    logger.info("\n" + classification_report(
        y_test, y_pred,
        target_names=["Fake(0)", "Genuine(1)", "Review(2)"],
        zero_division=0,
    ))

    out_path = MODELS_DIR / "fake_detector.pkl"
    joblib.dump(clf, out_path)
    logger.info(f"  Saved → {out_path}")

    return {
        "accuracy": round(float(acc), 4),
        "training_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
    }


def train_crime_classifier() -> dict:
    """
    Train TF-IDF + LinearSVC pipeline for 9-class crime categorisation.
    """
    logger.info("=" * 60)
    logger.info("Training Crime Category Classifier (TF-IDF + LinearSVC)")
    logger.info("=" * 60)

    logger.info("  Generating dataset...")
    descriptions, labels = generate_crime_dataset()
    logger.info(f"  Dataset: {len(descriptions)} samples across {len(set(labels))} categories")

    X_train, X_test, y_train, y_test = train_test_split(
        descriptions, labels, test_size=0.2, random_state=42, stratify=labels
    )

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            max_features=3000,
            ngram_range=(1, 2),
            sublinear_tf=True,
        )),
        ("clf", LinearSVC(
            C=1.0,
            random_state=42,
            max_iter=2000,
        )),
    ])

    logger.info("  Fitting pipeline...")
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)

    logger.info(f"  Test accuracy: {acc:.4f}")
    logger.info("\n" + classification_report(
        y_test, y_pred,
        target_names=sorted(set(labels)),
        zero_division=0,
    ))

    out_path = MODELS_DIR / "crime_classifier.pkl"
    joblib.dump(pipeline, out_path)
    logger.info(f"  Saved → {out_path}")

    return {
        "accuracy": round(float(acc), 4),
        "training_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
    }


def train_risk_classifier() -> dict:
    """
    Train GradientBoostingClassifier on 18-feature vectors for risk levels.
    Labels: HIGH / MEDIUM / LOW
    """
    logger.info("=" * 60)
    logger.info("Training Risk Level Classifier (GradientBoosting)")
    logger.info("=" * 60)

    logger.info("  Generating dataset...")
    X_raw, y_raw = generate_risk_dataset()
    X = np.array(X_raw, dtype=np.float32)
    y = np.array(y_raw)

    unique, counts = np.unique(y, return_counts=True)
    for lbl, cnt in zip(unique, counts):
        logger.info(f"    {lbl}: {cnt}")
    logger.info(f"  Total: {len(X)} samples")

    # Ensure all classes are represented in train and test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    clf = GradientBoostingClassifier(
        n_estimators=150,
        max_depth=5,
        learning_rate=0.1,
        random_state=42,
    )
    logger.info("  Fitting model...")
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)

    logger.info(f"  Test accuracy: {acc:.4f}")
    logger.info("\n" + classification_report(
        y_test, y_pred,
        target_names=sorted(set(y_raw)),
        zero_division=0,
    ))

    out_path = MODELS_DIR / "risk_classifier.pkl"
    joblib.dump(clf, out_path)
    logger.info(f"  Saved → {out_path}")

    return {
        "accuracy": round(float(acc), 4),
        "training_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
    }


def save_metadata(fake_meta: dict, crime_meta: dict, risk_meta: dict) -> None:
    """Persist training metadata to JSON for the predictor and UI to consume."""
    metadata = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "model_versions": {
            "fake_detector": "1.0.0",
            "crime_classifier": "1.0.0",
            "risk_classifier": "1.0.0",
        },
        "feature_names": FEATURE_NAMES,
        "crime_categories": CRIME_CATEGORIES,
        "fake_detector": fake_meta,
        "crime_classifier": crime_meta,
        "risk_classifier": risk_meta,
    }
    out_path = MODELS_DIR / "training_metadata.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"  Metadata saved → {out_path}")


def main():
    logger.info("")
    logger.info("AutoJustice AI NEXUS — ML Training Pipeline")
    logger.info(f"Output directory: {MODELS_DIR}")
    logger.info("")

    fake_meta  = train_fake_detector()
    logger.info("")
    crime_meta = train_crime_classifier()
    logger.info("")
    risk_meta  = train_risk_classifier()
    logger.info("")

    logger.info("=" * 60)
    logger.info("Saving training metadata...")
    save_metadata(fake_meta, crime_meta, risk_meta)

    logger.info("")
    logger.info("=" * 60)
    logger.info("Training complete. Summary:")
    logger.info(f"  Fake detector accuracy  : {fake_meta['accuracy']:.2%}")
    logger.info(f"  Crime classifier accuracy: {crime_meta['accuracy']:.2%}")
    logger.info(f"  Risk classifier accuracy : {risk_meta['accuracy']:.2%}")
    logger.info("=" * 60)
    logger.info("")


if __name__ == "__main__":
    main()
