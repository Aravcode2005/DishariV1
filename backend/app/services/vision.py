from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Protocol

import httpx

from app.core.config import Settings
from app.services.gemini import AIProviderError

# ExtractedFields forbids unknown keys, so only these may ever be emitted.
ALLOWED_FIELDS = ("full_name", "date_of_birth", "address_district_pin", "aadhaar_number")

# The model is told these names; aliases cover it answering in its own words.
FIELD_ALIASES = {
    "name": "full_name", "owner_name": "full_name", "account_holder_name": "full_name",
    "dob": "date_of_birth", "birth_date": "date_of_birth",
    "address": "address_district_pin",
    "aadhaar_no": "aadhaar_number", "uid": "aadhaar_number",
}

DOC_ALIASES = {"khatian": "land_record_khatian", "voter_id": "epic"}

MIME_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".pdf": "application/pdf"}

PROMPT = (
    "Transcribe the printed fields from this synthetic specimen document image.\n"
    "Return ONLY a JSON object with exactly these keys:\n"
    '  "full_name", "date_of_birth", "address_district_pin", "aadhaar_number"\n'
    "Rules:\n"
    "- Copy characters exactly as printed. Do not correct, expand or translate names.\n"
    "- date_of_birth must be YYYY-MM-DD. If only a year is printed, give YYYY.\n"
    "- Use null for any field not visible on this document. Never guess a value.\n"
    "- Do not infer eligibility, identity, or whether documents agree.\n"
    "- No explanation, no markdown fences, JSON only."
)


class VisionProvider(Protocol):
    def extract(self, image: bytes, mime_type: str, doc_type: str) -> dict: ...


# --------------------------------------------------------------------------
# Pure helpers
# --------------------------------------------------------------------------


def digest(image: bytes) -> str:
    return hashlib.sha256(image).hexdigest()[:16]


def mime_for(path: str | Path) -> str:
    suffix = Path(path).suffix.lower()
    if suffix not in MIME_TYPES:
        raise AIProviderError(f"Unsupported document type: {suffix or 'no extension'}")
    return MIME_TYPES[suffix]


def mask_aadhaar(value: object) -> str | None:
    """ExtractedFields enforces ^XXXX-XXXX-\\d{4}$, so an unmasked number cannot leave here."""
    digits = re.sub(r"\D", "", str(value or ""))
    return f"XXXX-XXXX-{digits[-4:]}" if len(digits) >= 4 else None


def clean_text(value: object) -> str | None:
    if value is None:
        return None
    text = " ".join(unicodedata.normalize("NFKC", str(value)).split())
    return text or None


def normalize_date(value: object) -> tuple[str | None, str]:
    """-> (value, date_precision). Unparseable input is dropped, never repaired."""
    text = clean_text(value)
    if not text:
        return None, "unspecified"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text, "exact"
    for pattern, order in ((r"(\d{2})[-/](\d{2})[-/](\d{4})", "dmy"), (r"(\d{4})[-/](\d{2})[-/](\d{2})", "ymd")):
        match = re.fullmatch(pattern, text)
        if match:
            a, b, c = match.groups()
            return (f"{c}-{b}-{a}" if order == "dmy" else f"{a}-{b}-{c}"), "exact"
    if re.fullmatch(r"\d{4}", text):
        return text, "year"
    return None, "unknown"


def parse_model_json(raw: str) -> dict:
    """Tolerate fenced or prefixed output; refuse to invent structure."""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", text).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise AIProviderError("Vision provider did not return JSON") from None
        try:
            parsed = json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            raise AIProviderError("Vision provider did not return JSON") from None
    if not isinstance(parsed, dict):
        raise AIProviderError("Vision provider did not return a JSON object")
    return parsed


def to_document(raw: dict, doc_type: str) -> dict:
    """Model output -> ExtractedDocument shape. Unknown keys are dropped, not passed through."""
    renamed = {FIELD_ALIASES.get(k.lower(), k.lower()): v for k, v in raw.items()}
    fields: dict[str, object] = {}

    name = clean_text(renamed.get("full_name"))
    if name:
        fields["full_name"] = name

    dob, precision = normalize_date(renamed.get("date_of_birth"))
    if dob:
        fields["date_of_birth"] = dob

    address = clean_text(renamed.get("address_district_pin"))
    if address:
        fields["address_district_pin"] = address

    masked = mask_aadhaar(renamed.get("aadhaar_number"))
    if masked:
        fields["aadhaar_number"] = masked

    return {
        "doc_type": DOC_ALIASES.get(doc_type, doc_type),
        "fields": fields,
        # An unreadable scan is routed to the operator, never silently treated as empty.
        "usable": bool(fields),
        "date_precision": precision if "date_of_birth" in fields else "unspecified",
    }


# --------------------------------------------------------------------------
# Providers
# --------------------------------------------------------------------------


class MockVisionProvider:
    """Offline demo path. Replays the cache; never reaches the network."""

    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = Path(cache_dir)

    def extract(self, image: bytes, mime_type: str, doc_type: str) -> dict:
        cached = self.cache_dir / f"{digest(image)}.json"
        if not cached.is_file():
            raise AIProviderError(
                "Offline mode: no cached extraction for this document. "
                "Run once online to populate the cache before demonstrating."
            )
        return to_document(json.loads(cached.read_text(encoding="utf-8")), doc_type)


class GeminiVisionProvider:
    def __init__(self, api_key: str, model: str, timeout: float,
                 transport: httpx.BaseTransport | None = None) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._transport = transport

    def extract(self, image: bytes, mime_type: str, doc_type: str) -> dict:
        payload = {
            "contents": [{"role": "user", "parts": [
                {"text": PROMPT},
                {"inline_data": {"mime_type": mime_type, "data": base64.b64encode(image).decode("ascii")}},
            ]}],
            "generationConfig": {"maxOutputTokens": 512, "temperature": 0,
                                 "responseMimeType": "application/json"},
        }
        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport,
                              trust_env=False, follow_redirects=False) as client:
                response = client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent",
                    headers={"x-goog-api-key": self._api_key}, json=payload)
                response.raise_for_status()
                candidate = response.json()["candidates"][0]
                if candidate.get("finishReason") not in {"STOP", "MAX_TOKENS"}:
                    raise AIProviderError("Vision provider did not return usable text")
                text = "\n".join(part["text"] for part in candidate["content"]["parts"]
                                 if isinstance(part.get("text"), str) and not part.get("thought"))
        except httpx.TimeoutException:
            raise AIProviderError("Vision provider timed out") from None
        except AIProviderError:
            raise
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError, AttributeError):
            raise AIProviderError("Vision provider request failed") from None
        if not text.strip():
            raise AIProviderError("Vision provider did not return usable text")
        return parse_model_json(text)   # raw dict; caching happens in the service


# --------------------------------------------------------------------------
# Service
# --------------------------------------------------------------------------


class ExtractionService:
    """Cache-first extraction. One network call per distinct image, ever."""

    def __init__(self, provider: VisionProvider, cache_dir: Path, offline: bool = False) -> None:
        self.provider = provider
        self.cache_dir = Path(cache_dir)
        self.offline = offline
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def extract_document(self, image: bytes, doc_type: str, mime_type: str | None = None,
                         filename: str | None = None) -> dict:
        cached = self.cache_dir / f"{digest(image)}.json"
        if cached.is_file():
            return to_document(json.loads(cached.read_text(encoding="utf-8")), doc_type)
        if self.offline:
            raise AIProviderError(
                "Offline mode: no cached extraction for this document. "
                "Run once online to populate the cache before demonstrating."
            )
        raw = self.provider.extract(image, mime_type or mime_for(filename or ""), doc_type)
        if isinstance(raw, dict) and "fields" in raw:   # a replaying provider
            return raw
        cached.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        return to_document(raw, doc_type)

    def extract_path(self, path: str | Path, doc_type: str) -> dict:
        path = Path(path)
        return self.extract_document(path.read_bytes(), doc_type,
                                     mime_type=mime_for(path), filename=str(path))


def create_vision_provider(settings: Settings, cache_dir: Path) -> VisionProvider:
    """Mirrors create_ai_provider: mock unless Gemini is fully configured."""
    if settings.ai_provider == "mock":
        return MockVisionProvider(cache_dir)
    assert settings.gemini_api_key is not None
    return GeminiVisionProvider(settings.gemini_api_key.get_secret_value(),
                                settings.gemini_model, settings.gemini_timeout_seconds)


def create_extraction_service(settings: Settings) -> ExtractionService:
    cache_dir = Path(os.getenv("DISHARI_CACHE_DIR", "cache"))
    offline = os.getenv("DISHARI_OFFLINE", "0") == "1"
    return ExtractionService(create_vision_provider(settings, cache_dir), cache_dir, offline)
