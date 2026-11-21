"""Dishari six-hour demo: a single FastAPI endpoint for React's multipart request."""
import os
import asyncio
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from engine import build_review
from gemini import AIError, extract_names

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_FILES = 8

app = FastAPI(title="Dishari Demo API", version="1.0")
origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[item.strip() for item in origins.split(",") if item.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "ai_mode": os.getenv("AI_MODE", "demo")}


@app.post("/api/dishari/v1/documents")
async def check_documents(
    consent: bool = Form(...),
    applicant_type: str = Form(...),
    crop_or_activity: str = Form(...),
    requested_loan_amount: int = Form(...),
    preferred_language: str = Form("en"),
    aadhaar: list[UploadFile] = File(...),
    bank_passbook: list[UploadFile] = File(...),
    khatian: list[UploadFile] = File(...),
):
    """Receive the FormData produced by frontend/src/api/caseApi.ts.

    Never persist the raw documents. Only synthetic demo inputs may be used.
    """
    if not consent:
        raise HTTPException(400, "Applicant consent is required")
    if applicant_type not in {"owner", "tenant", "joint", "other"}:
        raise HTTPException(422, "Invalid applicant_type")
    if not crop_or_activity.strip():
        raise HTTPException(422, "Crop or activity is required")
    if requested_loan_amount <= 0:
        raise HTTPException(422, "Loan amount must be positive")
    if preferred_language not in {"en", "hi", "bn"}:
        raise HTTPException(422, "Invalid preferred_language")

    uploads = {"aadhaar": aadhaar, "bank_passbook": bank_passbook, "khatian": khatian}
    if any(not files or (len(files) == 1 and not files[0].filename) for files in uploads.values()):
        raise HTTPException(422, "All three document categories are mandatory")
    if sum(len(files) for files in uploads.values()) > MAX_FILES:
        raise HTTPException(413, f"Maximum {MAX_FILES} files per request")

    # Keep bytes in RAM just long enough to send to Gemini. No DB or file storage.
    images: list[dict] = []
    for category, files in uploads.items():
        for item in files:
            data = await item.read(MAX_FILE_BYTES + 1)
            if not data or len(data) > MAX_FILE_BYTES:
                raise HTTPException(413, f"File for {category} must be 1–{MAX_FILE_BYTES} bytes")
            signature = (
                "image/png" if data.startswith(b"\x89PNG\r\n\x1a\n")
                else "image/jpeg" if data.startswith(b"\xff\xd8\xff")
                else None
            )
            if signature is None or item.content_type != signature:
                raise HTTPException(415, f"{category}: expected JPEG or PNG with correct MIME type")
            images.append({"category": category, "filename": item.filename, "mime_type": signature, "bytes": data})

    mode = os.getenv("AI_MODE", "demo").lower()
    if mode not in {"demo", "gemini"}:
        raise HTTPException(500, "AI_MODE must be demo or gemini")
    try:
        names = await asyncio.to_thread(extract_names, images, mode)
    except AIError as exc:
        # Deliberately no silent switch to fabricated data on Gemini failure.
        raise HTTPException(502, f"Gemini extraction failed: {exc}") from None

    return build_review(
        case_id=str(uuid4()),
        applicant_type=applicant_type,
        crop=crop_or_activity.strip(),
        amount=requested_loan_amount,
        names=names,
        images=images,
        origin="sample" if mode == "demo" else "live",
    )
