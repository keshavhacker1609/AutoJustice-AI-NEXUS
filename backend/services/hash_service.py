"""
AutoJustice AI NEXUS - SHA-256 Hash Service
Section 65B Indian Evidence Act compliance: every file and FIR is hashed on creation.
Hashes are immutable — stored once, verified on every access.
"""
import hashlib
import json
from pathlib import Path
from datetime import datetime


class HashService:
    """
    Cryptographic integrity layer for all evidence and generated documents.
    Uses SHA-256 as required for Section 65B compliance.
    """

    @staticmethod
    def hash_file(file_path: str | Path) -> str:
        """Compute SHA-256 hash of a file. Used for evidence files and FIR PDFs."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def hash_bytes(data: bytes) -> str:
        """Compute SHA-256 hash of raw bytes."""
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def hash_text(text: str) -> str:
        """Compute SHA-256 hash of a text string (UTF-8 encoded)."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def hash_report_content(description: str, extracted_text: str, complainant: str) -> str:
        """
        Canonical content hash for a report submission.
        Combines key immutable fields — used to detect duplicate submissions.
        """
        canonical = json.dumps({
            "complainant": complainant.strip().lower(),
            "description": description.strip(),
            "extracted_text": extracted_text.strip() if extracted_text else "",
        }, sort_keys=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def verify_file_integrity(file_path: str | Path, expected_hash: str) -> bool:
        """Verify a file's current hash matches its recorded hash. Detects tampering."""
        current_hash = HashService.hash_file(file_path)
        return current_hash == expected_hash

    @staticmethod
    def generate_certificate(case_number: str, content_hash: str, fir_hash: str) -> dict:
        """
        Generate a Section 65B certificate payload.
        This would be signed with a digital certificate in production.
        """
        return {
            "certificate_type": "Section 65B - Indian Evidence Act",
            "case_number": case_number,
            "content_hash_sha256": content_hash,
            "fir_hash_sha256": fir_hash,
            "certified_at": datetime.utcnow().isoformat() + "Z",
            "algorithm": "SHA-256",
            "statement": (
                "I certify that this electronic record was produced by an automated system "
                "and the hash values recorded herein represent the exact state of the digital "
                "evidence at the time of submission, in compliance with Section 65B of the "
                "Indian Evidence Act, 1872."
            ),
        }
