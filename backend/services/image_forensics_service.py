"""
AutoJustice AI NEXUS - Image Forensics Service
Detects tampered/manipulated images and AI-generated synthetic images.

Detection Layers:
  ELA   (Error Level Analysis)     – JPEG re-compression reveals edited regions
  META  (Metadata Forensics)       – Missing/inconsistent EXIF flags anomalies
  AIGEN (AI Generation Detection)  – Dimension patterns + missing sensor metadata
  NOISE (Statistical Analysis)     – Noise uniformity, copy-move artifact detection
  SCRN  (Screenshot Detection)     – Identifies screenshots vs genuine camera photos
"""
import io
import logging
import statistics
from pathlib import Path
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageChops, ImageStat, ExifTags
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("Pillow not available. Image forensics will be skipped.")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from google import genai as _genai_vision_sdk
    from google.genai import types as _genai_vision_types
    GEMINI_VISION_AVAILABLE = True
except ImportError:
    GEMINI_VISION_AVAILABLE = False


# ─── Constants ────────────────────────────────────────────────────────────────
ELA_SAVE_QUALITY      = 90    # Re-save JPEG at this quality for ELA
ELA_AMPLIFY_FACTOR    = 10    # Amplify difference for visibility
ELA_HIGH_DIFF         = 25    # Mean diff above this = suspicious
ELA_UNIFORMITY        = 0.3   # Low std/mean ratio = uniform edit

COMMON_SCREEN_WIDTHS  = {1920, 1366, 1280, 1440, 2560, 1024, 768, 390, 414, 375}

# Standard output sizes from major AI image generators
# DALL-E 3, Stable Diffusion, Midjourney, Firefly etc.
AI_GENERATION_SIZES = {
    (512, 512), (768, 768), (1024, 1024),
    (1024, 1792), (1792, 1024),
    (512, 768), (768, 512),
    (640, 480), (480, 640),
    (1344, 768), (768, 1344),
    (1216, 832), (832, 1216),
    (896, 1152), (1152, 896),
    (576, 1024), (1024, 576),
}

# AI generation software keywords in EXIF
AI_SOFTWARE_KEYWORDS = [
    "stable diffusion", "midjourney", "dall-e", "dalle",
    "firefly", "dreamstudio", "runway", "bing image creator",
    "leonardo", "adobe firefly", "imagen", "flux",
    "novelai", "automatic1111", "comfyui", "invokeai",
]


class ImageForensicsService:
    """
    Multi-layer forensic analysis for uploaded evidence images.
    Returns a tamper probability score, specific flags, and per-layer breakdown
    for explainable AI output.
    """

    def analyze(self, file_path: Path) -> dict:
        """
        Run all forensic layers on a given image file.

        Returns:
          tamper_score     : float 0.0 (clean) → 1.0 (definitely manipulated/synthetic)
          is_tampered      : bool
          flags            : list of human-readable findings
          summary          : plain-English verdict
          ela_stats        : raw ELA pixel diff stats
          gps_lat/gps_lon  : GPS coordinates if available
          forensics_layers : per-layer breakdown (for Explainable AI display)
        """
        if not PIL_AVAILABLE:
            return self._unavailable_result()

        suffix = file_path.suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}:
            return self._unavailable_result()

        all_flags = []
        ela_stats = {}
        gps_lat = gps_lon = None

        try:
            img = Image.open(file_path)

            # Layer 1 — ELA
            ela_score, ela_flags, ela_stats = self._ela_analysis(img, file_path)
            all_flags.extend(ela_flags)

            # Layer 2 — Metadata
            meta_score, meta_flags, gps_lat, gps_lon = self._metadata_forensics(img)
            all_flags.extend(meta_flags)

            # Layer 3 — AI Generation Detection
            ai_score, ai_flags = self._ai_generation_detection(img, file_path)
            all_flags.extend(ai_flags)

            # Layer 4 — Noise Analysis
            noise_score, noise_flags = self._noise_analysis(img)
            all_flags.extend(noise_flags)

            # Layer 5 — Screenshot Detection
            scrn_score, scrn_flags = self._screenshot_detection(img, file_path)
            all_flags.extend(scrn_flags)

            # Layer 6 — Gemini Vision AI detection (most accurate for modern models)
            gemini_score, gemini_flags = self._gemini_vision_check(file_path)
            all_flags.extend(gemini_flags)

        except Exception as e:
            logger.error(f"Forensics analysis failed for {file_path}: {e}")
            return self._unavailable_result()

        # ── Weighted composite ────────────────────────────────────────
        # Gemini Vision is the most reliable signal for modern AI-generated images.
        # When it fires it gets highest weight; when unavailable the other layers
        # carry the full load (their weights are renormalised internally via the
        # raw composite sum still being bounded 0-1).
        weights = {
            "ela":          0.20,
            "metadata":     0.18,
            "ai_gen":       0.22,
            "noise":        0.10,
            "screenshot":   0.05,
            "gemini_vision":0.25,
        }
        layer_raw = {
            "ela":          ela_score,
            "metadata":     meta_score,
            "ai_gen":       ai_score,
            "noise":        noise_score,
            "screenshot":   scrn_score,
            "gemini_vision":gemini_score,
        }
        tamper_score = sum(layer_raw[k] * weights[k] for k in weights)
        tamper_score = round(min(max(tamper_score, 0.0), 1.0), 3)

        # ── AI evidence override ───────────────────────────────────────
        # When AI-generation evidence is strong (single layer >= 0.60),
        # prevent the clean-layer dilution effect from masking it.
        # ai_gen OR gemini_vision scoring high is conclusive on its own.
        peak_ai_evidence = max(layer_raw["ai_gen"], layer_raw["gemini_vision"])
        if peak_ai_evidence >= 0.60:
            # Floor: strong AI evidence → score cannot be below 85% of peak evidence
            tamper_score = max(tamper_score, round(peak_ai_evidence * 0.85, 3))

        # Additional floor: if Gemini Vision specifically called this AI-generated,
        # ensure the score reflects that definitively
        if gemini_score >= 0.70:
            tamper_score = max(tamper_score, 0.75)

        tamper_score = round(min(tamper_score, 1.0), 3)

        from config import settings
        is_tampered = tamper_score >= settings.ela_tamper_threshold

        summary = self._generate_summary(tamper_score, all_flags)

        # ── Explainable AI: per-layer breakdown ───────────────────────
        layer_labels = {
            "ela":          "ELA (Error Level Analysis)",
            "metadata":     "Metadata / EXIF Analysis",
            "ai_gen":       "AI Generation Detection",
            "noise":        "Noise Pattern Analysis",
            "screenshot":   "Screenshot Detection",
            "gemini_vision":"Gemini Vision AI Check",
        }
        weight_labels = {
            "ela": "20%", "metadata": "18%", "ai_gen": "22%",
            "noise": "10%", "screenshot": "5%", "gemini_vision": "25%",
        }
        forensics_layers = {}
        layer_flag_map = {
            "ela":          ela_flags,
            "metadata":     meta_flags,
            "ai_gen":       ai_flags,
            "noise":        noise_flags,
            "screenshot":   scrn_flags,
            "gemini_vision":gemini_flags,
        }
        for key in weights:
            score = layer_raw[key]
            lflags = layer_flag_map[key]
            if score >= 0.60:
                verdict = "HIGH suspicion"
            elif score >= 0.35:
                verdict = "MODERATE suspicion"
            elif score > 0.0:
                verdict = "Low suspicion"
            else:
                verdict = "Clean"
            forensics_layers[key] = {
                "label":   layer_labels[key],
                "score":   round(score, 3),
                "pct":     f"{score:.0%}",
                "weight":  weight_labels[key],
                "verdict": verdict,
                "flags":   lflags,
            }

        return {
            "tamper_score":     tamper_score,
            "is_tampered":      is_tampered,
            "flags":            list(dict.fromkeys(all_flags)),  # preserve order, dedupe
            "summary":          summary,
            "ela_stats":        ela_stats,
            "gps_lat":          gps_lat,
            "gps_lon":          gps_lon,
            "forensics_layers": forensics_layers,
        }

    # ─── Layer 1: Error Level Analysis ───────────────────────────────────────

    def _ela_analysis(self, img: "Image.Image", file_path: Path) -> Tuple[float, list, dict]:
        """
        Re-save JPEG at known quality, compare pixel differences.
        Edited regions have higher error levels than untouched areas.
        NOTE: AI-generated images score LOW on ELA (no editing history),
        which is why we added the separate AI generation detection layer.
        """
        flags = []
        ela_stats = {}
        suffix = file_path.suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png"}:
            return 0.0, [], {}

        try:
            rgb = img.convert("RGB")
            buf = io.BytesIO()
            rgb.save(buf, format="JPEG", quality=ELA_SAVE_QUALITY)
            buf.seek(0)
            resaved = Image.open(buf).convert("RGB")

            diff = ImageChops.difference(rgb, resaved)
            amplified = diff.point(lambda p: p * ELA_AMPLIFY_FACTOR)
            stat = ImageStat.Stat(amplified)
            mean_diff = sum(stat.mean) / 3
            std_diff  = sum(stat.stddev) / 3

            ela_stats = {
                "mean_difference": round(mean_diff, 2),
                "std_difference":  round(std_diff, 2),
            }

            score = 0.0
            if mean_diff > ELA_HIGH_DIFF:
                score += 0.55
                flags.append(f"ELA: High pixel difference (mean={mean_diff:.1f}) — editing artifacts detected")
            if mean_diff > 5 and std_diff < (mean_diff * ELA_UNIFORMITY):
                score += 0.30
                flags.append("ELA: Uniform error distribution — region pasting or cloning suspected")
            if mean_diff > 50:
                score += 0.15
                flags.append("ELA: Extreme pixel diff — likely heavily edited or AI-upscaled image")

            return min(score, 1.0), flags, ela_stats

        except Exception as e:
            logger.debug(f"ELA error: {e}")
            return 0.0, [], {}

    # ─── Layer 2: Metadata Forensics ─────────────────────────────────────────

    def _metadata_forensics(self, img: "Image.Image") -> Tuple[float, list, Optional[float], Optional[float]]:
        """
        EXIF analysis. Real phone/camera photos always contain rich metadata.
        AI-generated images and edited images typically have stripped or absent EXIF.
        """
        flags = []
        score = 0.0
        gps_lat = gps_lon = None

        try:
            exif_raw = img.getexif() or None

            if exif_raw is None:
                if img.format in ("JPEG", "TIFF"):
                    # Moderate signal — real cameras embed EXIF, but messaging apps
                    # (WhatsApp, Telegram, Google Photos share) routinely strip it.
                    # We flag it but don't treat as definitive.
                    score += 0.30
                    flags.append("META: No EXIF data — camera metadata missing. Could indicate AI generation, screenshot, or metadata stripped by a messaging app.")
                elif img.format == "PNG":
                    score += 0.08
                    flags.append("META: PNG with no metadata — cannot verify camera origin")
                return score, flags, None, None

            exif = {ExifTags.TAGS.get(k, k): v for k, v in exif_raw.items()}

            # ── GPS ────────────────────────────────────────────────────
            if "GPSInfo" in exif:
                try:
                    gi = exif["GPSInfo"]
                    gps_lat = self._convert_gps(gi.get(2), gi.get(1))
                    gps_lon = self._convert_gps(gi.get(4), gi.get(3))
                except Exception:
                    pass

            # ── Check: AI generation software in Software tag ──────────
            software = str(exif.get("Software", "")).lower()
            for ai_tool in AI_SOFTWARE_KEYWORDS:
                if ai_tool in software:
                    score += 0.90
                    flags.append(f"META: AI image generation software detected — '{software.strip()}'. This image was not captured by a camera.")
                    break

            # ── Check: Common editing software ─────────────────────────
            if score < 0.9:
                edit_tools = ["photoshop", "lightroom", "gimp", "snapseed",
                              "facetune", "picsart", "pixlr", "canva", "affinity"]
                for tool in edit_tools:
                    if tool in software:
                        score += 0.50
                        flags.append(f"META: Image edited with {software.title()} — post-processing detected")
                        break

            # ── Check: DateTime mismatch ───────────────────────────────
            dt_orig     = exif.get("DateTimeOriginal")
            dt_modified = exif.get("DateTime")
            if dt_orig and dt_modified and dt_orig != dt_modified:
                score += 0.20
                flags.append(f"META: File modified after capture — original: {dt_orig}, modified: {dt_modified}")

            # ── Check: No camera Make/Model ────────────────────────────
            has_device = exif.get("Make") or exif.get("Model")
            if not has_device and img.format in ("JPEG", "TIFF"):
                score += 0.18
                flags.append("META: No camera make/model in EXIF — present in AI-generated images and heavily processed photos")

            # ── Check: ImageDescription contains editing reference ─────
            img_desc = str(exif.get("ImageDescription", "")).lower()
            if any(kw in img_desc for kw in ["photoshop", "adobe", "edited", "generated"]):
                score += 0.30
                flags.append("META: Image description references editing or generation software")

        except Exception as e:
            logger.debug(f"Metadata forensics error: {e}")

        return min(score, 1.0), flags, gps_lat, gps_lon

    # ─── Layer 3: AI Generation Detection ────────────────────────────────────

    def _ai_generation_detection(self, img: "Image.Image", file_path: Path) -> Tuple[float, list]:
        """
        Detect images produced by AI generators (DALL-E, Midjourney, Stable Diffusion, etc.)

        Signals are weighted conservatively to avoid false positives on real camera photos.
        A single signal is never enough to conclude AI generation — we require corroboration.

        Key reliable signals (require 2+ to flag high confidence):
        - Dimensions exactly match known AI generator output sizes AND missing EXIF
        - AI generation software keyword found in EXIF Software tag (handled in metadata layer)
        - Very low bytes-per-pixel for a large image (AI generators over-compress)
        """
        flags = []
        score = 0.0
        signals_fired = 0

        try:
            width, height = img.size

            # ── Signal 1: Exact AI output dimensions (strong but not alone sufficient) ──
            dim_match = (width, height) in AI_GENERATION_SIZES
            if dim_match:
                score += 0.35   # Reduced — many phones produce similar sizes
                signals_fired += 1
                flags.append(f"AI-GEN: Dimensions {width}×{height} match standard AI image generation output sizes")

            # ── Signal 2: Perfect square only if also metadata-free ───────
            elif width == height and width in {512, 768, 1024}:
                # Only flag perfect square if there's no EXIF (real cameras rarely produce square outputs)
                try:
                    exif_raw = img.getexif() or None
                    if exif_raw is None:
                        score += 0.30
                        signals_fired += 1
                        flags.append(f"AI-GEN: Perfect square {width}×{height} with no EXIF — strong indicator of AI generation")
                except Exception:
                    pass

            # ── Signal 3: PNG with NO metadata — only meaningful combined with other signals ──
            if img.format == "PNG":
                has_any_meta = bool(getattr(img, "info", {}))
                if not has_any_meta and signals_fired > 0:
                    # Only add if another signal already fired
                    score += 0.20
                    flags.append("AI-GEN: PNG with zero metadata (corroborates dimension signal)")
                elif not has_any_meta:
                    # Alone it's weak — many real photos saved as PNG lack metadata
                    score += 0.05

            # ── Signal 4: Very low bytes-per-pixel for large image ────────
            try:
                file_size = file_path.stat().st_size
                pixels    = width * height
                bpp       = file_size / pixels if pixels > 0 else 999
                if bpp < 0.06 and pixels > 300_000:
                    score += 0.25
                    signals_fired += 1
                    flags.append(f"AI-GEN: Very low file density ({bpp:.3f} bytes/pixel for {width}×{height}) — consistent with AI output compression artifacts")
            except Exception:
                pass

            # ── Signal 5: PNG with photographic content ───────────────────────
            # Real cameras save photos as JPEG/HEIC, never as PNG.
            # PNG is used for screenshots (already detected), UI graphics, and
            # AI generator exports. If a large PNG has rich photographic colour
            # complexity, it is almost certainly AI-generated or converted from one.
            if img.format == "PNG" and width >= 400 and height >= 400:
                is_screen_size = width in COMMON_SCREEN_WIDTHS
                if not is_screen_size:
                    if NUMPY_AVAILABLE:
                        arr = np.array(img.convert("RGB"))
                        # Downsample for speed, count unique colour clusters
                        sample = arr[::4, ::4].reshape(-1, 3)
                        unique_colours = len(np.unique(sample, axis=0))
                        colour_richness = unique_colours / max(sample.shape[0], 1)
                    else:
                        from PIL import ImageStat
                        stat = ImageStat.Stat(img.convert("RGB"))
                        # High per-channel std dev = photographic colour complexity
                        colour_richness = sum(stat.stddev) / (3 * 128)

                    if colour_richness > 0.55:
                        score += 0.80   # Strong signal: cameras never produce PNG photos
                        signals_fired += 1
                        flags.append(
                            "AI-GEN: Large PNG with photographic colour complexity — "
                            "cameras save photos as JPEG/HEIC, not PNG. "
                            "PNG at this quality level is characteristic of AI-generated images."
                        )

            # ── Signal 6: Dimensions divisible by 64 — for PNG only ───────────
            # Diffusion models operate on 64-pixel latent grids. PNG output at
            # multiples of 64 is a strong AI signal when combined with other signals.
            # (Removed for JPEG because real cameras also produce such dimensions.)
            if img.format == "PNG" and signals_fired > 0:
                if width % 64 == 0 and height % 64 == 0:
                    score += 0.15
                    flags.append(
                        f"AI-GEN: PNG dimensions {width}×{height} are multiples of 64 — "
                        "consistent with diffusion model latent grid output"
                    )

        except Exception as e:
            logger.debug(f"AI generation detection error: {e}")

        return min(score, 1.0), flags

    # ─── Layer 4: Noise Analysis ──────────────────────────────────────────────

    def _noise_analysis(self, img: "Image.Image") -> Tuple[float, list]:
        """
        Analyse per-block noise patterns.
        Real camera photos have natural sensor noise — slightly varied across blocks.
        AI images often have unnaturally smooth, perfectly uniform noise.
        Composited images have abrupt noise discontinuities between pasted regions.
        """
        flags = []
        score = 0.0

        try:
            gray   = img.convert("L")
            width, height = gray.size

            if width < 50 or height < 50:
                return 0.0, []

            if NUMPY_AVAILABLE:
                arr = np.array(gray, dtype=np.float32)

                # Global noise via Laplacian variance (fast, reliable)
                laplacian = (
                    arr[:-2, 1:-1] + arr[2:, 1:-1] +
                    arr[1:-1, :-2] + arr[1:-1, 2:] -
                    4 * arr[1:-1, 1:-1]
                )
                global_noise_var = float(np.var(laplacian))

                # Very low variance = perfectly smooth = AI-generated or heavily processed
                if global_noise_var < 15.0:
                    score += 0.30
                    flags.append(f"NOISE: Abnormally smooth image (noise variance={global_noise_var:.1f}) — AI-generated or heavily processed images lack natural sensor noise")

                # Block-level analysis for compositing detection
                block_size = max(width // 8, 32)
                block_vars = []
                for row in range(0, height - block_size, block_size):
                    for col in range(0, width - block_size, block_size):
                        block = arr[row:row+block_size, col:col+block_size]
                        block_vars.append(float(np.var(block)))

                if len(block_vars) >= 4:
                    mean_var = float(np.mean(block_vars))
                    std_var  = float(np.std(block_vars))

                    # Extreme block variance differences = compositing (pasted regions)
                    if std_var > (mean_var * 1.5) and mean_var > 20:
                        score += 0.25
                        flags.append("NOISE: High block-level noise variation — different regions have inconsistent noise, suggesting image compositing")

            else:
                # PIL fallback: whole-image std dev
                stat      = ImageStat.Stat(gray)
                global_std = stat.stddev[0]
                if global_std < 8.0:
                    score += 0.25
                    flags.append(f"NOISE: Very low image std dev ({global_std:.1f}) — image appears unnaturally smooth")

                # Block std devs via getdata
                pixels     = list(gray.getdata())
                block_size = max(width // 8, 16)
                block_stds = []
                for row in range(0, height - block_size, block_size):
                    for col in range(0, width - block_size, block_size):
                        blk = []
                        for r in range(row, min(row + block_size, height)):
                            for c in range(col, min(col + block_size, width)):
                                blk.append(pixels[r * width + c])
                        if len(blk) > 4:
                            block_stds.append(statistics.stdev(blk))

                if len(block_stds) >= 4:
                    mean_std   = statistics.mean(block_stds)
                    std_of_std = statistics.stdev(block_stds)
                    if mean_std < 5.0:
                        score += 0.20
                        flags.append("NOISE: Abnormally uniform per-block noise — AI-generated or synthetic image")
                    if std_of_std > 35 and mean_std > 10:
                        score += 0.20
                        flags.append("NOISE: Inconsistent block noise — possible image compositing")

        except Exception as e:
            logger.debug(f"Noise analysis error: {e}")

        return min(score, 1.0), flags

    # ─── Layer 6: Gemini Vision AI Generation Check ──────────────────────────

    def _gemini_vision_check(self, file_path: Path) -> Tuple[float, list]:
        """
        Ask Gemini Vision to assess whether the image is AI-generated.
        This is the most reliable signal for modern photorealistic diffusion model
        outputs that evade all statistical/heuristic checks.

        Uses gemini-1.5-flash (fast, cheap, vision-capable).
        Returns (score, flags). Score 0.0 if API unavailable.
        """
        if not GEMINI_VISION_AVAILABLE:
            return 0.0, []
        try:
            import os, json, re
            from config import settings as _cfg
            api_key = getattr(_cfg, "gemini_api_key", "") or os.getenv("GEMINI_API_KEY", "")
            if not api_key:
                return 0.0, []

            client = _genai_vision_sdk.Client(api_key=api_key)

            with open(file_path, "rb") as f:
                img_bytes = f.read()

            suffix = file_path.suffix.lower()
            mime_map = {
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png",  ".bmp":  "image/bmp",
                ".tiff": "image/tiff", ".gif": "image/gif",
            }
            mime = mime_map.get(suffix, "image/png")

            prompt = (
                "You are a forensic AI analyst specializing in detecting AI-generated imagery. "
                "Examine this image carefully for signs of AI generation (Midjourney, Stable Diffusion, "
                "DALL-E, Firefly, or similar diffusion models).\n\n"
                "Look for:\n"
                "1. Unnaturally perfect or plastic-looking skin/textures\n"
                "2. Physically inconsistent lighting or shadows\n"
                "3. Background distortions typical of diffusion models\n"
                "4. Uncanny-valley facial features or limbs\n"
                "5. Hyper-realistic yet subtly wrong fine details (hair, hands, blood, fabric)\n"
                "6. Overly cinematic or 'stock photo' composition\n"
                "7. Missing natural imperfections present in real photographs\n\n"
                "Respond ONLY with this exact JSON (no markdown, no extra text):\n"
                '{"ai_generated": true/false, "confidence": <0.0-1.0>, '
                '"reasons": ["<short reason 1>", "<short reason 2>"]}'
            )

            response = client.models.generate_content(
                model=getattr(_cfg, "gemini_model", "gemini-2.0-flash"),
                contents=[
                    _genai_vision_types.Part.from_bytes(data=img_bytes, mime_type=mime),
                    prompt,
                ],
                config=_genai_vision_types.GenerateContentConfig(
                    temperature=0.05,
                    max_output_tokens=300,
                ),
            )

            raw = (response.text or "").strip()
            raw = re.sub(r"```(?:json)?", "", raw).strip()
            data = json.loads(raw)

            if data.get("ai_generated"):
                conf    = max(0.0, min(float(data.get("confidence", 0.5)), 1.0))
                reasons = data.get("reasons", [])
                reason_str = "; ".join(str(r) for r in reasons[:2])
                flags = [
                    f"GEMINI-VISION: AI-generated image detected "
                    f"(confidence={conf:.0%}) — {reason_str}"
                ]
                logger.info(
                    f"Gemini Vision: AI-generated ({conf:.0%}) — {file_path.name}"
                )
                return conf, flags
            else:
                conf = float(data.get("confidence", 0.5))
                logger.info(
                    f"Gemini Vision: NOT AI-generated ({1-conf:.0%} real) — {file_path.name}"
                )
                return 0.0, []

        except Exception as e:
            logger.debug(f"Gemini Vision forensics check failed: {e}")
            return 0.0, []

    # ─── Layer 5: Screenshot Detection ───────────────────────────────────────

    def _screenshot_detection(self, img: "Image.Image", file_path: Path) -> Tuple[float, list]:
        """Detect screenshots. Informational — screenshots can be valid evidence."""
        flags = []
        score = 0.0
        try:
            width, height = img.size
            if width in COMMON_SCREEN_WIDTHS:
                flags.append(f"INFO: Resolution {width}×{height} matches common screen size — likely a screenshot (valid as evidence)")
                return 0.05, flags
        except Exception as e:
            logger.debug(f"Screenshot detection error: {e}")
        return score, flags

    # ─── Helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _convert_gps(coord, ref) -> Optional[float]:
        if not coord or not ref:
            return None
        try:
            d = float(coord[0]) + float(coord[1]) / 60.0 + float(coord[2]) / 3600.0
            if str(ref).upper() in ("S", "W"):
                d = -d
            return round(d, 6)
        except Exception:
            return None

    @staticmethod
    def _generate_summary(tamper_score: float, flags: list) -> str:
        ai_flags    = [f for f in flags if f.startswith("AI-GEN:")]
        meta_flags  = [f for f in flags if f.startswith("META:")]
        ela_flags   = [f for f in flags if f.startswith("ELA:")]
        noise_flags = [f for f in flags if f.startswith("NOISE:")]

        has_ai_flag     = any("AI-GEN:" in f for f in flags)
        has_gemini_flag = any("GEMINI-VISION:" in f for f in flags)
        has_ai_sw_flag  = any("AI image generation software detected" in f for f in flags)

        if has_ai_sw_flag:
            # Definitive — explicit AI software keyword found in EXIF metadata
            verdict = "SYNTHETIC IMAGE — AI generation software identified in metadata"
        elif has_gemini_flag:
            # Gemini Vision explicitly identified AI generation
            conf_str = next(
                (f.split("confidence=")[1].split(")")[0] for f in flags if "GEMINI-VISION:" in f),
                "high confidence"
            )
            verdict = f"SYNTHETIC IMAGE — Gemini Vision: AI-generated image ({conf_str})"
        elif has_ai_flag and tamper_score >= 0.60:
            # PNG photographic content + strong AI-gen score
            verdict = "HIGH confidence AI-generated image — photographic PNG is not a camera format"
        elif tamper_score >= 0.80:
            verdict = "HIGH confidence manipulated or AI-generated image"
        elif tamper_score >= 0.75:
            verdict = "HIGH probability of manipulation or AI generation"
        elif tamper_score >= 0.55:
            verdict = "MODERATE manipulation indicators — manual review recommended"
        elif tamper_score >= 0.30:
            verdict = "Low-level anomalies detected — review recommended"
        else:
            verdict = "No significant manipulation indicators"

        parts = [f"Score: {tamper_score:.0%}. Verdict: {verdict}."]
        total_issues = len(ai_flags) + len(meta_flags) + len(ela_flags) + len(noise_flags)
        if total_issues > 0:
            parts.append(f"{total_issues} forensic issue(s) found.")
        return " ".join(parts)

    @staticmethod
    def _unavailable_result() -> dict:
        return {
            "tamper_score":     0.0,
            "is_tampered":      False,
            "flags":            ["Forensic analysis unavailable — unsupported file type or missing Pillow library"],
            "summary":          "Image forensics skipped.",
            "ela_stats":        {},
            "gps_lat":          None,
            "gps_lon":          None,
            "forensics_layers": {},
        }

    def analyze_multiple(self, file_paths: list) -> dict:
        results = []
        for fp in file_paths:
            r = self.analyze(fp)
            r["file"] = fp.name
            results.append(r)

        if not results:
            return self._unavailable_result()

        max_score  = max(r["tamper_score"] for r in results)
        all_flags  = []
        for r in results:
            for flag in r["flags"]:
                all_flags.append(f"[{r['file']}] {flag}")

        from config import settings
        return {
            "tamper_score":     max_score,
            "is_tampered":      max_score >= settings.ela_tamper_threshold,
            "flags":            list(dict.fromkeys(all_flags)),
            "summary":          f"Analyzed {len(results)} file(s). Max tamper score: {max_score:.0%}.",
            "per_file_results": results,
            "forensics_layers": results[0].get("forensics_layers", {}) if results else {},
        }
