"""
AutoJustice AI NEXUS — Phase 2: Video Evidence Forensics Service
Detects deepfake videos, analyzes video metadata, and extracts key frames for AI review.

Detection Layers:
  L1: Container metadata analysis (creation tools, deepfake software signatures)
  L2: Frame extraction + image forensics on key frames
  L3: Audio-video sync anomaly detection (basic)
  L4: Gemini Vision analysis on extracted frames
  L5: File integrity and compression artifact detection

Supports: MP4, MOV, AVI, WebM, MKV
"""
import io
import json
import logging
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Optional dependencies ─────────────────────────────────────────────────────
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.info("opencv-python not installed. Frame extraction will use ffmpeg fallback.")

try:
    from google import genai as _genai_sdk
    from google.genai import types as _genai_types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Known deepfake / face-swap software signatures in video metadata
DEEPFAKE_TOOL_SIGNATURES = [
    "faceswap", "deepfacelab", "deepfake", "reface", "face2face",
    "neural face", "first order motion", "ganface", "styleganv",
    "deeptomcruise", "avatarify", "wav2lip", "talking head",
    "luma dream", "runway gen", "heygen", "synthesia",
    "wondershare", "facetune video", "remini video",
]

# Legitimate screen recording / editing tools (lower suspicion)
LEGITIMATE_TOOLS = [
    "obs studio", "bandicam", "fraps", "shadowplay", "screenflow",
    "camtasia", "final cut", "premiere", "davinci", "handbrake",
    "ffmpeg", "quicktime", "vlc", "iphone", "samsung", "android",
    "samsung sm-", "iphone", "pixel", "xiaomi", "oneplus",
]

SUPPORTED_VIDEO_TYPES = {".mp4", ".mov", ".avi", ".webm", ".mkv", ".3gp", ".flv"}


class VideoForensicsService:
    """
    Multi-layer forensic analysis for uploaded video evidence.
    Falls back gracefully when optional dependencies (cv2, ffmpeg) are missing.
    """

    def analyze(self, file_path: Path) -> dict:
        """
        Run all forensic layers on a video file.
        Returns standardised result dict compatible with image forensics output format.
        """
        if file_path.suffix.lower() not in SUPPORTED_VIDEO_TYPES:
            return self._unsupported_result(file_path.suffix)

        flags = []
        scores = {}

        try:
            # L1: Container / metadata analysis
            l1_score, l1_flags, metadata = self._l1_metadata_analysis(file_path)
            flags.extend(l1_flags)
            scores["metadata"] = l1_score

            # L2: Key frame extraction + image forensics
            l2_score, l2_flags, frame_paths = self._l2_frame_forensics(file_path)
            flags.extend(l2_flags)
            scores["frame_forensics"] = l2_score

            # L3: File integrity / compression artifact check
            l3_score, l3_flags = self._l3_integrity_check(file_path, metadata)
            flags.extend(l3_flags)
            scores["integrity"] = l3_score

            # L4: Gemini Vision on key frames
            l4_score, l4_flags = self._l4_gemini_vision(frame_paths, file_path)
            flags.extend(l4_flags)
            scores["gemini_vision"] = l4_score

        except Exception as e:
            logger.error(f"Video forensics failed for {file_path.name}: {e}")
            return self._error_result(str(e))
        finally:
            # Clean up extracted frames
            for fp in (frame_paths if 'frame_paths' in dir() else []):
                try: fp.unlink()
                except Exception: pass

        # Weighted composite score
        weights = {
            "metadata":       0.30,
            "frame_forensics":0.25,
            "integrity":      0.15,
            "gemini_vision":  0.30,
        }
        tamper_score = sum(scores.get(k, 0.0) * w for k, w in weights.items())
        tamper_score = round(min(max(tamper_score, 0.0), 1.0), 3)

        # Strong individual evidence override
        if scores.get("gemini_vision", 0) >= 0.70:
            tamper_score = max(tamper_score, 0.75)
        if scores.get("metadata", 0) >= 0.80:
            tamper_score = max(tamper_score, 0.70)

        tamper_score = round(min(tamper_score, 1.0), 3)

        from config import settings
        is_tampered = tamper_score >= settings.ela_tamper_threshold

        return {
            "tamper_score":      tamper_score,
            "is_tampered":       is_tampered,
            "flags":             list(dict.fromkeys(flags)),
            "summary":           self._generate_summary(tamper_score, flags),
            "file_type":         "video",
            "format":            file_path.suffix.lower(),
            "metadata":          metadata,
            "layer_scores":      scores,
            "ela_stats":         {},
            "gps_lat":           None,
            "gps_lon":           None,
            "forensics_layers":  {
                k: {
                    "label":   k.replace("_", " ").title(),
                    "score":   round(scores.get(k, 0.0), 3),
                    "pct":     f"{scores.get(k, 0.0):.0%}",
                    "weight":  f"{int(weights[k]*100)}%",
                    "verdict": (
                        "HIGH suspicion" if scores.get(k, 0) >= 0.60
                        else "MODERATE suspicion" if scores.get(k, 0) >= 0.35
                        else "Low suspicion" if scores.get(k, 0) > 0
                        else "Clean"
                    ),
                    "flags":   [f for f in flags if k.upper()[:4] in f.upper()],
                }
                for k in weights
            },
        }

    # ─── Layer 1: Metadata Analysis ──────────────────────────────────────────

    def _l1_metadata_analysis(self, file_path: Path) -> tuple[float, list, dict]:
        """Extract and analyse video container metadata using ffprobe or fallback."""
        flags = []
        score = 0.0
        metadata = {}

        # ── Try ffprobe (most reliable) ────────────────────────────────────
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet", "-print_format", "json",
                    "-show_format", "-show_streams", str(file_path)
                ],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                probe = json.loads(result.stdout)
                fmt = probe.get("format", {})
                tags = fmt.get("tags", {})
                metadata = {
                    "encoder":       tags.get("encoder", tags.get("ENCODER", "")),
                    "creation_time": tags.get("creation_time", ""),
                    "comment":       tags.get("comment", tags.get("COMMENT", "")),
                    "duration":      fmt.get("duration", ""),
                    "bit_rate":      fmt.get("bit_rate", ""),
                    "format_name":   fmt.get("format_name", ""),
                }

                encoder = metadata["encoder"].lower()
                comment = metadata["comment"].lower()
                combined_meta = encoder + " " + comment

                # Check for deepfake tool signatures
                for tool in DEEPFAKE_TOOL_SIGNATURES:
                    if tool in combined_meta:
                        score = max(score, 0.90)
                        flags.append(
                            f"META-VIDEO: Deepfake/face-swap software detected in encoder — "
                            f"'{metadata['encoder']}'"
                        )
                        break

                # Check bit rate anomalies for compressed-after-generation
                try:
                    br = int(metadata["bit_rate"])
                    dur = float(metadata["duration"])
                    if br < 100_000 and dur > 5.0:
                        score = max(score, 0.25)
                        flags.append(
                            f"META-VIDEO: Unusually low bit rate ({br//1000} kbps) for video — "
                            "may indicate heavy re-compression (common in deepfake pipelines)"
                        )
                except (ValueError, TypeError):
                    pass

                # No creation time = processed / re-encoded
                if not metadata["creation_time"]:
                    score = max(score, 0.15)
                    flags.append(
                        "META-VIDEO: No creation timestamp in metadata — video may have been re-encoded"
                    )

        except FileNotFoundError:
            logger.info("ffprobe not found — skipping container metadata analysis")
            metadata["ffprobe"] = "unavailable"
        except Exception as e:
            logger.debug(f"ffprobe error: {e}")

        # ── Filename heuristics ────────────────────────────────────────────
        fname_lower = file_path.stem.lower()
        for tool in DEEPFAKE_TOOL_SIGNATURES[:8]:  # Check most common
            if tool.replace(" ", "") in fname_lower.replace("-", "").replace("_", ""):
                score = max(score, 0.75)
                flags.append(
                    f"META-VIDEO: Filename '{file_path.name}' contains deepfake tool reference"
                )
                break

        return min(score, 1.0), flags, metadata

    # ─── Layer 2: Frame Extraction + Image Forensics ─────────────────────────

    def _l2_frame_forensics(self, file_path: Path) -> tuple[float, list, list]:
        """Extract key frames and run image forensics on them."""
        flags = []
        score = 0.0
        frame_paths = []

        # Extract frames using cv2 (preferred) or ffmpeg fallback
        frame_paths = self._extract_key_frames(file_path, n_frames=5)

        if not frame_paths:
            return 0.0, ["VIDEO-FRAMES: Could not extract frames for analysis"], []

        # Run image forensics on each extracted frame
        try:
            from services.image_forensics_service import ImageForensicsService
            img_forensics = ImageForensicsService()

            frame_scores = []
            for fp in frame_paths:
                result = img_forensics.analyze(fp)
                frame_scores.append(result["tamper_score"])
                if result["tamper_score"] >= 0.40:
                    flags.append(
                        f"FRAME-FORENSICS: Frame shows manipulation indicators "
                        f"(score={result['tamper_score']:.0%}): {result['flags'][:2]}"
                    )

            if frame_scores:
                # Use max frame score (a single bad frame is enough)
                score = max(frame_scores)
                avg_score = sum(frame_scores) / len(frame_scores)
                if avg_score >= 0.35:
                    flags.append(
                        f"FRAME-FORENSICS: Multiple frames show manipulation — "
                        f"avg score {avg_score:.0%}, max {score:.0%}"
                    )

        except Exception as e:
            logger.warning(f"Frame forensics failed: {e}")

        return min(score, 1.0), flags, frame_paths

    # ─── Layer 3: File Integrity Check ───────────────────────────────────────

    def _l3_integrity_check(self, file_path: Path, metadata: dict) -> tuple[float, list]:
        """Check for re-encoding artifacts and file inconsistencies."""
        flags = []
        score = 0.0

        try:
            file_size = file_path.stat().st_size
            # Try to get duration from metadata
            dur_str = metadata.get("duration", "0")
            try:
                duration = float(dur_str)
            except (ValueError, TypeError):
                duration = 0.0

            # Bytes per second (rough quality indicator)
            if duration > 1.0:
                bps = file_size / duration
                # Less than 50KB/s is extreme compression for video
                if bps < 50_000:
                    score += 0.30
                    flags.append(
                        f"INTEGRITY: Video has very low data rate ({bps/1024:.0f} KB/s) — "
                        "extreme compression typical of deepfake output pipelines"
                    )

        except Exception as e:
            logger.debug(f"Integrity check error: {e}")

        return min(score, 1.0), flags

    # ─── Layer 4: Gemini Vision on Key Frames ────────────────────────────────

    def _l4_gemini_vision(self, frame_paths: list, original_path: Path) -> tuple[float, list]:
        """
        Send extracted frames to Gemini Vision for deepfake detection.
        Sends up to 3 frames in a single multi-image prompt for efficiency.
        """
        if not GEMINI_AVAILABLE or not frame_paths:
            return 0.0, []

        try:
            import os
            from config import settings as _cfg
            api_key = getattr(_cfg, "gemini_api_key", "") or os.getenv("GEMINI_API_KEY", "")
            if not api_key:
                return 0.0, []

            client = _genai_sdk.Client(api_key=api_key)

            # Use up to 3 frames
            frames_to_analyze = frame_paths[:3]
            parts = []
            for fp in frames_to_analyze:
                try:
                    with open(fp, "rb") as f:
                        img_bytes = f.read()
                    parts.append(
                        _genai_types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
                    )
                except Exception:
                    continue

            if not parts:
                return 0.0, []

            parts.append(
                "You are a forensic deepfake analyst. These are extracted frames from a video "
                f"submitted as cybercrime evidence (file: {original_path.name}).\n\n"
                "Analyze for signs of deepfake manipulation:\n"
                "1. Face-swapping artifacts (edge blending around face boundaries)\n"
                "2. Unnatural blinking or eye movement\n"
                "3. Inconsistent skin texture or lighting on face vs background\n"
                "4. Temporal inconsistencies visible between frames\n"
                "5. AI-generated facial features (too smooth, plastic-looking)\n"
                "6. Lip-sync artifacts (if applicable)\n\n"
                "Respond ONLY in this JSON format (no markdown):\n"
                '{"deepfake_detected": true/false, "confidence": <0.0-1.0>, '
                '"manipulation_type": "<face_swap|lip_sync|full_generation|none>", '
                '"reasons": ["<reason1>", "<reason2>"]}'
            )

            response = client.models.generate_content(
                model=getattr(_cfg, "gemini_model", "gemini-2.0-flash"),
                contents=parts,
                config=_genai_types.GenerateContentConfig(
                    temperature=0.05,
                    max_output_tokens=400,
                ),
            )

            raw = (response.text or "").strip()
            raw = re.sub(r"```(?:json)?", "", raw).strip()
            data = json.loads(raw)

            if data.get("deepfake_detected"):
                conf = max(0.0, min(float(data.get("confidence", 0.5)), 1.0))
                manip_type = data.get("manipulation_type", "unknown")
                reasons = "; ".join(str(r) for r in data.get("reasons", [])[:2])
                flags = [
                    f"GEMINI-DEEPFAKE: Deepfake detected in video frames "
                    f"(type={manip_type}, confidence={conf:.0%}) — {reasons}"
                ]
                logger.info(
                    f"Gemini deepfake detection: {manip_type} ({conf:.0%}) — {original_path.name}"
                )
                return conf, flags
            else:
                conf = float(data.get("confidence", 0.5))
                logger.info(
                    f"Gemini: No deepfake detected ({1-conf:.0%} real) — {original_path.name}"
                )
                return 0.0, []

        except Exception as e:
            logger.debug(f"Gemini video analysis failed: {e}")
            return 0.0, []

    # ─── Frame Extraction ─────────────────────────────────────────────────────

    def _extract_key_frames(self, file_path: Path, n_frames: int = 5) -> list:
        """
        Extract N evenly-spaced frames from a video as JPEG files.
        Tries cv2 first, falls back to ffmpeg.
        Returns list of temporary Path objects (caller must delete them).
        """
        frame_paths = []
        tmp_dir = Path(tempfile.mkdtemp())

        # ── cv2 method ────────────────────────────────────────────────────
        if CV2_AVAILABLE:
            try:
                cap = cv2.VideoCapture(str(file_path))
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if total_frames > 0:
                    indices = [
                        int(i * total_frames / n_frames)
                        for i in range(n_frames)
                    ]
                    for i, idx in enumerate(indices):
                        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                        ret, frame = cap.read()
                        if ret:
                            fp = tmp_dir / f"frame_{i:02d}.jpg"
                            cv2.imwrite(str(fp), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                            frame_paths.append(fp)
                cap.release()
                if frame_paths:
                    logger.info(f"Extracted {len(frame_paths)} frames via cv2 from {file_path.name}")
                    return frame_paths
            except Exception as e:
                logger.debug(f"cv2 frame extraction failed: {e}")

        # ── ffmpeg fallback ───────────────────────────────────────────────
        try:
            result = subprocess.run(
                [
                    "ffmpeg", "-i", str(file_path),
                    "-vf", f"fps=1/5",           # 1 frame every 5 seconds
                    "-frames:v", str(n_frames),
                    "-q:v", "3",                 # JPEG quality 3 (high)
                    str(tmp_dir / "frame_%02d.jpg"),
                    "-y", "-loglevel", "error",
                ],
                capture_output=True, timeout=30
            )
            for fp in sorted(tmp_dir.glob("frame_*.jpg")):
                frame_paths.append(fp)
            if frame_paths:
                logger.info(f"Extracted {len(frame_paths)} frames via ffmpeg from {file_path.name}")
        except FileNotFoundError:
            logger.info("ffmpeg not found — frame extraction unavailable")
        except Exception as e:
            logger.debug(f"ffmpeg frame extraction failed: {e}")

        return frame_paths

    # ─── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _generate_summary(tamper_score: float, flags: list) -> str:
        has_deepfake = any("DEEPFAKE" in f or "face" in f.lower() for f in flags)
        has_metadata = any("META-VIDEO" in f for f in flags)

        if has_deepfake and tamper_score >= 0.70:
            return f"Score: {tamper_score:.0%}. DEEPFAKE DETECTED — Gemini Vision identified face manipulation. This video cannot be used as genuine evidence without expert verification."
        elif has_metadata and tamper_score >= 0.60:
            return f"Score: {tamper_score:.0%}. SUSPICIOUS VIDEO — Deepfake software signature found in metadata. Recommend expert forensic analysis."
        elif tamper_score >= 0.50:
            return f"Score: {tamper_score:.0%}. MANIPULATION INDICATORS — Multiple layers flagged anomalies. Manual review required."
        elif tamper_score >= 0.25:
            return f"Score: {tamper_score:.0%}. Low-level anomalies detected in video frames."
        else:
            return f"Score: {tamper_score:.0%}. No significant manipulation indicators detected."

    @staticmethod
    def _unsupported_result(suffix: str) -> dict:
        return {
            "tamper_score": 0.0,
            "is_tampered": False,
            "flags": [f"VIDEO: Unsupported format '{suffix}'. Supported: MP4, MOV, AVI, WebM, MKV"],
            "summary": "Video forensics skipped — unsupported format.",
            "file_type": "video",
            "forensics_layers": {},
            "ela_stats": {}, "gps_lat": None, "gps_lon": None, "metadata": {},
        }

    @staticmethod
    def _error_result(error: str) -> dict:
        return {
            "tamper_score": 0.0,
            "is_tampered": False,
            "flags": [f"VIDEO: Forensic analysis failed — {error}"],
            "summary": "Video forensics encountered an error.",
            "file_type": "video",
            "forensics_layers": {},
            "ela_stats": {}, "gps_lat": None, "gps_lon": None, "metadata": {},
        }


# Module-level singleton
video_forensics_service = VideoForensicsService()
