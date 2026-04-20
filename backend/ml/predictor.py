"""
AutoJustice AI NEXUS — ML Inference Engine
Singleton lazy-loading predictor for all three ML models.
Thread-safe: models are loaded once on first call.
"""
import json
import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_MODELS_DIR = Path(__file__).parent / "models"

# ─── Lazy imports — avoid hard failure if sklearn not installed ───────────────
try:
    import joblib
    import numpy as np
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn / joblib not installed — ML predictions disabled.")

try:
    from ml.features import extract_features, FEATURE_NAMES
except ImportError:
    try:
        from features import extract_features, FEATURE_NAMES
    except ImportError:
        extract_features = None
        FEATURE_NAMES = []
        logger.warning("features.py not importable — ML predictions disabled.")


class MLPredictor:
    """
    Singleton ML inference engine.
    Thread-safe lazy loading — models are loaded on first predict call.
    All predict_* methods return an 'available' key so callers can detect
    whether the ML layer is operational without raising exceptions.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._loaded = False

        self._fake_model = None
        self._crime_model = None
        self._risk_model = None
        self._metadata: dict = {}

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _load_models(self) -> None:
        """Load all three pkl files from the models directory (once)."""
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return  # double-checked locking

            if not _SKLEARN_AVAILABLE:
                logger.warning("sklearn not available — skipping model load.")
                self._loaded = True
                return

            def _try_load(filename: str):
                path = _MODELS_DIR / filename
                if path.exists():
                    try:
                        return joblib.load(path)
                    except Exception as e:
                        logger.warning(f"Failed to load {filename}: {e}")
                return None

            self._fake_model  = _try_load("fake_detector.pkl")
            self._crime_model = _try_load("crime_classifier.pkl")
            self._risk_model  = _try_load("risk_classifier.pkl")

            meta_path = _MODELS_DIR / "training_metadata.json"
            if meta_path.exists():
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        self._metadata = json.load(f)
                except Exception as e:
                    logger.warning(f"Could not load training metadata: {e}")

            loaded_names = [
                name for name, m in [
                    ("fake_detector",    self._fake_model),
                    ("crime_classifier", self._crime_model),
                    ("risk_classifier",  self._risk_model),
                ]
                if m is not None
            ]
            if loaded_names:
                logger.info(f"ML models loaded: {', '.join(loaded_names)}")
            else:
                logger.info("No ML models found — running without ML layer.")

            self._loaded = True

    def _get_features(self, description: str, evidence_text: str = "") -> Optional[List[float]]:
        """Extract 18 features; returns None if extraction not possible."""
        if extract_features is None:
            return None
        try:
            return extract_features(description, evidence_text)
        except Exception as e:
            logger.warning(f"Feature extraction failed: {e}")
            return None

    # ── Public predict methods ────────────────────────────────────────────────

    def predict_fake(self, description: str, evidence_text: str = "") -> dict:
        """
        Predict whether a report is genuine, needs review, or is fake.

        Returns
        -------
        {
          "ml_score": float,            # 0.0=fake, 1.0=genuine
          "ml_recommendation": str,     # "GENUINE" | "REVIEW" | "REJECT"
          "ml_confidence": float,       # probability of predicted class
          "top_features": list,         # top 5 feature contributions
          "available": bool
        }
        """
        self._load_models()

        if self._fake_model is None or not _SKLEARN_AVAILABLE:
            return {"available": False}

        feats = self._get_features(description, evidence_text)
        if feats is None:
            return {"available": False}

        try:
            import numpy as np
            X = np.array([feats], dtype=np.float32)
            proba = self._fake_model.predict_proba(X)[0]
            classes = self._fake_model.classes_  # typically [0, 1, 2]

            # Map class indices to score:
            #   0 = fake  → 0.0
            #   1 = genuine → 1.0
            #   2 = review → 0.5
            score_map = {0: 0.0, 1: 1.0, 2: 0.5}
            ml_score = float(sum(
                proba[i] * score_map.get(int(c), 0.5)
                for i, c in enumerate(classes)
            ))

            predicted_class = int(classes[proba.argmax()])
            ml_confidence = float(proba.max())

            if ml_score >= 0.65:
                recommendation = "GENUINE"
            elif ml_score >= 0.40:
                recommendation = "REVIEW"
            else:
                recommendation = "REJECT"

            # Build top-5 feature importance list
            top_features = []
            try:
                importances = self._fake_model.feature_importances_
                feat_arr = np.array(feats)
                scored = sorted(
                    enumerate(importances),
                    key=lambda x: x[1],
                    reverse=True,
                )[:5]
                top_features = [
                    {
                        "name": FEATURE_NAMES[idx] if idx < len(FEATURE_NAMES) else f"feat_{idx}",
                        "value": round(float(feat_arr[idx]), 4),
                        "importance": round(float(imp), 4),
                    }
                    for idx, imp in scored
                ]
            except Exception:
                pass

            return {
                "ml_score": round(ml_score, 4),
                "ml_recommendation": recommendation,
                "ml_confidence": round(ml_confidence, 4),
                "top_features": top_features,
                "available": True,
            }

        except Exception as e:
            logger.warning(f"predict_fake failed: {e}")
            return {"available": False}

    def predict_crime(self, description: str) -> dict:
        """
        Predict the crime category for a complaint description.

        Returns
        -------
        {
          "crime_category": str,
          "confidence": float,
          "available": bool
        }
        """
        self._load_models()

        if self._crime_model is None or not _SKLEARN_AVAILABLE:
            return {"available": False}

        if not description or not description.strip():
            return {"available": False}

        try:
            predicted = self._crime_model.predict([description])[0]

            # Compute confidence via decision_function softmax (LinearSVC)
            confidence = 0.0
            try:
                clf_step = self._crime_model.named_steps.get("clf")
                tfidf_step = self._crime_model.named_steps.get("tfidf")
                if clf_step is not None and tfidf_step is not None:
                    import numpy as _np
                    X_tfidf = tfidf_step.transform([description])
                    scores = _np.array(clf_step.decision_function(X_tfidf)[0], dtype=float)
                    # Softmax: stable, gives proper probability for the top class
                    scores_shifted = scores - scores.max()
                    exp_scores = _np.exp(scores_shifted)
                    probs = exp_scores / exp_scores.sum()
                    confidence = round(float(probs.max()), 4)
            except Exception:
                confidence = 0.5

            return {
                "crime_category": str(predicted),
                "confidence": max(0.0, min(confidence, 1.0)),
                "available": True,
            }

        except Exception as e:
            logger.warning(f"predict_crime failed: {e}")
            return {"available": False}

    def predict_risk(self, description: str, evidence_text: str = "") -> dict:
        """
        Predict the risk level (HIGH / MEDIUM / LOW) for a complaint.

        Returns
        -------
        {
          "risk_level": str,    # "HIGH" | "MEDIUM" | "LOW"
          "confidence": float,
          "available": bool
        }
        """
        self._load_models()

        if self._risk_model is None or not _SKLEARN_AVAILABLE:
            return {"available": False}

        feats = self._get_features(description, evidence_text)
        if feats is None:
            return {"available": False}

        try:
            import numpy as np
            X = np.array([feats], dtype=np.float32)
            proba = self._risk_model.predict_proba(X)[0]
            classes = self._risk_model.classes_

            predicted_idx = proba.argmax()
            risk_level = str(classes[predicted_idx])
            confidence = round(float(proba[predicted_idx]), 4)

            # Ensure valid label
            if risk_level not in ("HIGH", "MEDIUM", "LOW"):
                risk_level = "LOW"

            return {
                "risk_level": risk_level,
                "confidence": confidence,
                "available": True,
            }

        except Exception as e:
            logger.warning(f"predict_risk failed: {e}")
            return {"available": False}

    def get_metadata(self) -> dict:
        """Return training_metadata.json contents, or {} if unavailable."""
        self._load_models()
        return dict(self._metadata)


# ── Module-level singleton ────────────────────────────────────────────────────
ml_predictor = MLPredictor()
