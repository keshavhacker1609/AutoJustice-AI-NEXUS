"""
AutoJustice AI NEXUS - OCR Service
Extracts text from evidence files (images, PDFs, screenshots).
Handles Tesseract gracefully with fallback messaging when not installed.
PDF support upgraded to use pdfplumber for proper text extraction.
"""
import os
import re
import logging
from pathlib import Path
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# ─── Tesseract Setup ──────────────────────────────────────────────────────────
try:
    import pytesseract
    from PIL import Image, ExifTags
    from config import settings
    if settings.tesseract_path and settings.tesseract_path != "tesseract":
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_path
    TESSERACT_AVAILABLE = True
except Exception:
    TESSERACT_AVAILABLE = False
    logger.warning("Tesseract/Pillow not available. OCR will return empty strings.")

# ─── PDF Extraction Setup ─────────────────────────────────────────────────────
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logger.info("pdfplumber not installed. Will try pypdf2 fallback for PDFs.")

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    try:
        from PyPDF2 import PdfReader
        PYPDF_AVAILABLE = True
    except ImportError:
        PYPDF_AVAILABLE = False

# ─── pdf2image for OCR on scanned PDFs ───────────────────────────────────────
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

# ─── Gemini Vision fallback for OCR (when Tesseract is unavailable) ──────────
# Uses google.genai (new SDK, same as used elsewhere in the project)
try:
    from google import genai as _genai_vision_sdk
    from google.genai import types as _genai_vision_types
    GEMINI_VISION_AVAILABLE = True
except ImportError:
    GEMINI_VISION_AVAILABLE = False


class OCRService:
    """
    Extracts and cleans text from uploaded evidence files.
    Supports: JPG, PNG, BMP, TIFF, GIF images; PDF documents; TXT files.
    """

    SUPPORTED_IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".gif"}
    SUPPORTED_TEXT_TYPES = {".txt"}

    def extract_text(self, file_path: str | Path) -> Tuple[str, float]:
        """
        Extract text from a file. Returns (text, confidence_score).
        confidence_score: 0.0 (none) → 1.0 (perfect)
        """
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()

        if suffix in self.SUPPORTED_TEXT_TYPES:
            return self._extract_from_text_file(file_path)
        elif suffix in self.SUPPORTED_IMAGE_TYPES:
            return self._extract_from_image(file_path)
        elif suffix == ".pdf":
            return self._extract_from_pdf(file_path)
        else:
            return "", 0.0

    # ── Language packs available on this machine (detected once at startup) ──────
    _AVAILABLE_LANGS: Optional[str] = None   # populated lazily

    @classmethod
    def _get_lang(cls) -> str:
        """
        Return the best available Tesseract language string.
        Prefers 'eng+hin' (both English + Hindi); gracefully degrades to 'eng'
        if the Hindi data-pack is not installed — avoids crashing OCR entirely.
        """
        if cls._AVAILABLE_LANGS is not None:
            return cls._AVAILABLE_LANGS
        try:
            langs = pytesseract.get_languages(config="")
            cls._AVAILABLE_LANGS = "eng+hin" if "hin" in langs else "eng"
        except Exception:
            cls._AVAILABLE_LANGS = "eng"
        logger.info(f"OCR language pack selected: {cls._AVAILABLE_LANGS}")
        return cls._AVAILABLE_LANGS

    @staticmethod
    def _preprocess_for_ocr(img: "Image.Image") -> "Image.Image":
        """
        Pre-process an image to maximise Tesseract accuracy on screenshots.

        Steps:
          1. Upscale small images — Tesseract needs ≥300 DPI equivalent to read
             small UI text. Screenshots are typically 72–96 DPI, so we scale up
             2× if either dimension is under 1000 px.
          2. Convert to greyscale.
          3. Auto-contrast / histogram equalisation to handle coloured backgrounds
             (e.g. WhatsApp green, banking app blue) that reduce character contrast.
        """
        try:
            from PIL import ImageEnhance, ImageOps

            # Step 1 — upscale tiny images
            w, h = img.size
            if min(w, h) < 1000:
                scale = max(2.0, 1500 / min(w, h))
                new_size = (int(w * scale), int(h * scale))
                img = img.resize(new_size, Image.LANCZOS)

            # Step 2 — greyscale
            img = img.convert("L")

            # Step 3 — auto-contrast (stretches histogram to full 0-255 range)
            img = ImageOps.autocontrast(img, cutoff=2)

            # Step 4 — slight sharpness boost to recover anti-aliased edges
            img = ImageEnhance.Sharpness(img).enhance(1.5)

        except Exception as e:
            logger.debug(f"Image pre-processing skipped: {e}")
            img = img.convert("L")   # minimal fallback

        return img

    def _extract_from_image(self, file_path: Path) -> Tuple[str, float]:
        """
        Use Tesseract OCR to extract text from an image file.

        Tries three OCR passes with different page-segmentation modes so that
        screenshots (mixed layout), single-block documents, and sparse labels
        are all handled well:
          • PSM 3  — fully automatic layout detection  (best for screenshots)
          • PSM 6  — single uniform block of text       (best for plain docs)
          • PSM 11 — sparse text, no layout assumptions (best for labels/UI)
        The pass that yields the most words wins.
        """
        if not TESSERACT_AVAILABLE:
            # ── Gemini Vision fallback when Tesseract is not installed ────
            if GEMINI_VISION_AVAILABLE:
                return self._extract_via_gemini_vision(file_path)
            return "[OCR unavailable - Tesseract not installed]", 0.0

        try:
            img = Image.open(file_path)
            img = self._preprocess_for_ocr(img)
            lang = self._get_lang()

            best_words: list = []
            best_confs: list = []

            for psm in (3, 6, 11):
                try:
                    data = pytesseract.image_to_data(
                        img,
                        lang=lang,
                        output_type=pytesseract.Output.DICT,
                        config=f"--oem 3 --psm {psm}",
                    )
                    words, confs = [], []
                    for i, word in enumerate(data["text"]):
                        conf = int(data["conf"][i])
                        if conf > 15 and word.strip():   # 15 is permissive — clean screenshots
                            words.append(word)           # score very high anyway
                            confs.append(conf)
                    if len(words) > len(best_words):
                        best_words = words
                        best_confs = confs
                except Exception as psm_err:
                    logger.debug(f"PSM {psm} failed for {file_path.name}: {psm_err}")
                    continue

            raw_text = " ".join(best_words)
            avg_confidence = (
                sum(best_confs) / len(best_confs) / 100.0 if best_confs else 0.0
            )

            cleaned = self._clean_text(raw_text)
            if cleaned:
                logger.info(
                    f"Tesseract OCR: {len(cleaned)} chars from {file_path.name} "
                    f"(conf={avg_confidence:.2f}, lang={lang})"
                )
            elif GEMINI_VISION_AVAILABLE:
                # Tesseract found nothing — try Gemini Vision as a second opinion
                logger.info(f"Tesseract returned empty — trying Gemini Vision for {file_path.name}")
                return self._extract_via_gemini_vision(file_path)
            return cleaned, round(avg_confidence, 3)

        except Exception as e:
            logger.error(f"OCR extraction failed for {file_path}: {e}")
            if GEMINI_VISION_AVAILABLE:
                logger.info("Falling back to Gemini Vision after Tesseract error")
                return self._extract_via_gemini_vision(file_path)
            return f"[OCR failed: {str(e)}]", 0.0

    def _extract_via_gemini_vision(self, file_path: Path) -> Tuple[str, float]:
        """
        Gemini Vision fallback OCR.
        Called when Tesseract is unavailable OR returns empty for a screenshot.
        Uses google.genai SDK with gemini-2.0-flash for OCR.
        Returns extracted text at 0.75 confidence (AI-assisted, not pixel-perfect).
        """
        try:
            from config import settings as _cfg
            api_key = getattr(_cfg, "gemini_api_key", "") or os.getenv("GEMINI_API_KEY", "")
            if not api_key:
                logger.warning("Gemini Vision OCR: no API key — skipping")
                return "", 0.0

            client = _genai_vision_sdk.Client(api_key=api_key)

            with open(file_path, "rb") as f:
                image_bytes = f.read()

            suffix = file_path.suffix.lower()
            mime_map = {
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png",  ".bmp": "image/bmp",
                ".gif": "image/gif",  ".tiff": "image/tiff",
                ".webp": "image/webp",
            }
            mime = mime_map.get(suffix, "image/png")

            response = client.models.generate_content(
                model=getattr(_cfg, "gemini_model", "gemini-2.0-flash"),
                contents=[
                    _genai_vision_types.Part.from_bytes(data=image_bytes, mime_type=mime),
                    (
                        "Extract ALL visible text from this image exactly as it appears. "
                        "Include transaction IDs, amounts, dates, phone numbers, UPI IDs, "
                        "bank account numbers, names, and any other text. "
                        "Return ONLY the extracted text, nothing else. "
                        "If the image contains no text, respond with: NO_TEXT"
                    ),
                ],
                config=_genai_vision_types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=800,
                ),
            )

            raw = (response.text or "").strip()
            if not raw or raw == "NO_TEXT":
                logger.info(f"Gemini Vision: no text found in {file_path.name}")
                return "", 0.0

            cleaned = self._clean_text(raw)
            logger.info(f"Gemini Vision OCR: {len(cleaned)} chars from {file_path.name}")
            return cleaned, 0.75   # AI-assisted confidence level

        except Exception as e:
            logger.error(f"Gemini Vision OCR failed for {file_path}: {e}")
            return "", 0.0

    def _extract_from_text_file(self, file_path: Path) -> Tuple[str, float]:
        """Read plain text files directly."""
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
            return self._clean_text(text), 1.0
        except Exception as e:
            logger.error(f"Text file read failed: {e}")
            return "", 0.0

    def _extract_from_pdf(self, file_path: Path) -> Tuple[str, float]:
        """
        Extract text from PDF using pdfplumber (best), then pypdf (fallback),
        then pdf2image + Tesseract for scanned PDFs (last resort).
        """
        # ── Method 1: pdfplumber (best for digital PDFs) ──────────────
        if PDFPLUMBER_AVAILABLE:
            try:
                texts = []
                with pdfplumber.open(str(file_path)) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            texts.append(page_text)

                        # Also extract tables as text
                        tables = page.extract_tables()
                        for table in tables:
                            for row in table:
                                row_text = " | ".join(
                                    str(cell) if cell else ""
                                    for cell in row
                                )
                                if row_text.strip():
                                    texts.append(row_text)

                if texts:
                    combined = "\n".join(texts)
                    cleaned = self._clean_text(combined)
                    if len(cleaned) > 20:
                        logger.info(f"pdfplumber extracted {len(cleaned)} chars from {file_path.name}")
                        return cleaned, 0.90
            except Exception as e:
                logger.warning(f"pdfplumber failed for {file_path}: {e}")

        # ── Method 2: pypdf fallback ──────────────────────────────────
        if PYPDF_AVAILABLE:
            try:
                reader = PdfReader(str(file_path))
                texts = []
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        texts.append(text)

                if texts:
                    combined = "\n".join(texts)
                    cleaned = self._clean_text(combined)
                    if len(cleaned) > 20:
                        logger.info(f"pypdf extracted {len(cleaned)} chars from {file_path.name}")
                        return cleaned, 0.80
            except Exception as e:
                logger.warning(f"pypdf failed for {file_path}: {e}")

        # ── Method 3: pdf2image + Tesseract for scanned PDFs ─────────
        if PDF2IMAGE_AVAILABLE and TESSERACT_AVAILABLE:
            try:
                images = convert_from_path(str(file_path), dpi=200, first_page=1, last_page=5)
                texts = []
                confidences = []
                lang = self._get_lang()
                for img in images:
                    gray = self._preprocess_for_ocr(img)
                    data = pytesseract.image_to_data(
                        gray,
                        lang=lang,
                        output_type=pytesseract.Output.DICT,
                        config="--oem 3 --psm 3",
                    )
                    words = []
                    for i, word in enumerate(data["text"]):
                        conf = int(data["conf"][i])
                        if conf > 15 and word.strip():
                            words.append(word)
                            confidences.append(conf)
                    texts.append(" ".join(words))

                combined = " ".join(texts)
                avg_conf = sum(confidences) / len(confidences) / 100.0 if confidences else 0.5
                cleaned = self._clean_text(combined)
                if cleaned:
                    logger.info(f"pdf2image+OCR extracted {len(cleaned)} chars from {file_path.name}")
                    return cleaned, round(avg_conf, 3)
            except Exception as e:
                logger.warning(f"pdf2image+OCR failed for {file_path}: {e}")

        # ── Final fallback ────────────────────────────────────────────
        logger.warning(f"All PDF extraction methods failed for {file_path.name}")
        return "[PDF text extraction failed — install pdfplumber for best results]", 0.1

    def _clean_text(self, text: str) -> str:
        """Normalize and clean extracted text for downstream AI processing."""
        if not text:
            return ""
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^\x20-\x7E\u0900-\u097F]", " ", text)
        return text.strip()

    def extract_exif_metadata(self, file_path: str | Path) -> dict:
        """
        Extract EXIF metadata from images for forensic analysis.
        GPS coordinates, device info, and original timestamp are forensically significant.
        """
        if not TESSERACT_AVAILABLE:
            return {}
        try:
            img = Image.open(file_path)
            exif_raw = img.getexif() or None
            if not exif_raw:
                return {}
            readable = {}
            for tag_id, value in exif_raw.items():
                tag = ExifTags.TAGS.get(tag_id, str(tag_id))
                if isinstance(value, bytes):
                    continue
                readable[tag] = str(value)[:200]
            return readable
        except Exception:
            return {}
