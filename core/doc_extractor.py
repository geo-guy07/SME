"""
Multimodal Document & Invoice Ingestion — SME Compliance Assistant
Extracts business profiles, identity credentials, turnover figures, and addresses
from invoices, utility bills, PAN cards, and GST registration certificates.
Supports Gemini Multimodal Vision when GEMINI_API_KEY is configured,
with an intelligent offline heuristic parser (PyPDF + Regex) as fallback.
"""

import os
import re
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Delhi", "Jammu and Kashmir", "Ladakh"
]


def extract_with_gemini(file_path: str, mime_type: str) -> Optional[Dict[str, Any]]:
    """Use Gemini Multimodal Vision API to parse document."""
    if not GEMINI_API_KEY:
        return None

    supported_mimes = ["application/pdf", "image/jpeg", "image/png", "image/webp"]
    if mime_type not in supported_mimes:
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_API_KEY)
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        prompt = (
            "You are an expert Indian SME compliance auditor. Extract structured business details "
            "from this document (e.g. invoice, utility bill, GST certificate, PAN card). "
            "Return a clean JSON object ONLY (no markdown code fence) with the following fields: "
            "document_type (e.g., 'Tax Invoice', 'Electricity Bill', 'GST Certificate', 'PAN Card', 'Receipt'), "
            "business_name (string or null), "
            "owner (string or null), "
            "pan (string 10-char or null), "
            "aadhaar (string 12-digit or null), "
            "mobile (string 10-digit or null), "
            "email (string or null), "
            "address (string or null), "
            "state (Indian State name or null), "
            "turnover_lakh (float estimate from invoice/total or null), "
            "activity (business activity or null), "
            "confidence (float between 0.0 and 1.0)."
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                prompt,
            ],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )

        if response.text:
            cleaned = response.text.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\n|\n```$", "", cleaned)
            return json.loads(cleaned)
    except Exception as e:
        print(f"  [DocExtractor] Gemini vision error ({e}). Falling back to heuristic extractor.")
    return None


def extract_offline_heuristics(file_path: str) -> Dict[str, Any]:
    """Parse text using PyPDF or plain-text regex inspection."""
    path = Path(file_path)
    text = ""

    if path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += "\n" + extracted
        except Exception as e:
            print(f"  [DocExtractor] PyPDF read error: {e}")
    else:
        # Try reading file content directly for text or mock files
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read(15000)
        except Exception:
            text = ""
        text += "\n" + path.name

    extracted = {
        "document_type": "Commercial Document",
        "business_name": None,
        "owner": None,
        "pan": None,
        "aadhaar": None,
        "mobile": None,
        "email": None,
        "address": None,
        "state": None,
        "turnover_lakh": None,
        "activity": None,
        "confidence": 0.75 if text.strip() else 0.5,
    }

    # PAN pattern: 5 uppercase letters, 4 digits, 1 letter
    pan_match = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", text.upper())
    if pan_match:
        extracted["pan"] = pan_match.group(1)

    # Aadhaar pattern: 12 digits
    aadhaar_match = re.search(r"\b(\d{4}\s?\d{4}\s?\d{4})\b", text)
    if aadhaar_match:
        extracted["aadhaar"] = re.sub(r"\s+", "", aadhaar_match.group(1))

    # Mobile pattern: 10 digits starting with 6-9
    mobile_match = re.search(r"(?:(?:\+|0{0,2})91[\s-]?)?([6-9]\d{9})\b", text)
    if mobile_match:
        extracted["mobile"] = mobile_match.group(1)

    # Email pattern
    email_match = re.search(r"\b([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b", text)
    if email_match:
        extracted["email"] = email_match.group(1)

    # State search
    for st in INDIAN_STATES:
        if re.search(r"\b" + re.escape(st) + r"\b", text, re.IGNORECASE):
            extracted["state"] = st
            break

    # Financial amount / Invoice total
    amount_match = re.search(r"(?:Total|Invoice Value|Amount|Grand Total|Turnover)[:\s]*(?:Rs\.?|INR)?\s*([\d,]+(?:\.\d{2})?)", text, re.IGNORECASE)
    if amount_match:
        try:
            amt_str = amount_match.group(1).replace(",", "")
            amt = float(amt_str)
            # If large amount, convert to Lakhs
            extracted["turnover_lakh"] = round(amt / 100000.0, 2) if amt > 1000 else amt
        except Exception:
            pass

    # Heuristic business name if "M/s" or "Company" found
    name_match = re.search(r"(?:M/s\.?|Enterprise:|Business:|Firm:|Company:)\s*([A-Za-z0-9\s&]+?)(?:\n|,|\.|$)", text, re.IGNORECASE)
    if name_match:
        extracted["business_name"] = name_match.group(1).strip()
    else:
        # Fallback to sanitized filename
        clean_name = re.sub(r"[_\-]+", " ", path.stem).title()
        if any(w in clean_name.lower() for w in ["invoice", "bill", "doc", "scan"]):
            extracted["business_name"] = "Extracted Enterprise"
        else:
            extracted["business_name"] = clean_name

    # Document type inference
    lower_text = (text + " " + path.name).lower()
    if "tax invoice" in lower_text or "invoice" in lower_text:
        extracted["document_type"] = "Tax Invoice"
    elif "electricity" in lower_text or "power" in lower_text or "utility" in lower_text:
        extracted["document_type"] = "Electricity Utility Bill"
    elif "gst" in lower_text or "registration certificate" in lower_text:
        extracted["document_type"] = "GST Registration Certificate"
    elif "pan" in lower_text:
        extracted["document_type"] = "Permanent Account Number (PAN) Card"

    return extracted


def extract_document(file_path: str, mime_type: Optional[str] = None, business_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Main extraction interface. Tries Gemini Vision first, falls back to offline heuristics.
    Persists document record in SQLite.
    """
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File '{file_path}' does not exist."}

    ext = path.suffix.lower()
    if not mime_type:
        mime_map = {
            ".pdf": "application/pdf",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }
        mime_type = mime_map.get(ext, "application/octet-stream")

    # 1. Try Gemini Vision if online
    data = extract_with_gemini(str(path), mime_type)

    # 2. Fall back to offline heuristics
    if not data:
        data = extract_offline_heuristics(str(path))

    # Persist in SQLite
    try:
        from core.database import SessionLocal, DocumentUpload
        db = SessionLocal()
        record = DocumentUpload(
            business_id=business_id,
            filename=path.name,
            file_type=mime_type,
            file_size_bytes=path.stat().st_size,
            extracted_metadata_json=json.dumps(data, default=str),
            uploaded_at=datetime.utcnow(),
        )
        db.add(record)
        db.commit()
        data["document_id"] = record.id
        db.close()
    except Exception as e:
        print(f"  [DocExtractor] Database logging note: {e}")

    return {
        "filename": path.name,
        "mime_type": mime_type,
        "extracted_data": data,
        "timestamp": datetime.utcnow().isoformat(),
    }
