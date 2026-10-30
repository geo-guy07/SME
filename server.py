"""
SME Audit AI — Backend API & Web Application Server
FastAPI backend providing REST endpoints for authentication, PostgreSQL business profile
management, statutory rules engine audits, Gemini Vision OCR document ingestion,
and the conversational compliance assistant.
"""

import os
import json
import uuid
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from core.database import (
    get_session,
    User,
    Business,
    DocumentUpload,
    AuditFinding,
    WorkflowRecord,
)
from core.db_service import (
    init_db,
    seed_default_data,
    create_user,
    get_user_by_email,
    get_user_by_id,
    list_users,
    save_business_to_db,
    get_business_from_db,
    list_businesses_from_db,
    record_audit_findings,
    get_findings_from_db,
    record_workflow_state,
)
from core.business_profile import get_business, BusinessProfile, SAMPLE_BUSINESSES
from core.rules_engine import evaluate_business, check_requirements
from core.doc_extractor import ingest_document_photo, extract_document_data
from core.workflow import (
    start_udyam_workflow,
    resume_udyam_workflow,
    ACTIVE_WORKFLOWS,
    WorkflowStatus,
    mask_value,
)
from rag.vector_store import VectorStore
from rag.regulations import REGULATIONS
from core.agent_engine import run_compliance_agent, run_compliance_chat

# Initialize database schema and default sample data
init_db()
seed_default_data()

app = FastAPI(
    title="SME Audit AI",
    description="Agentic Compliance Automation & Statutory Audit System for Indian SMEs",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
STATIC_DIR = Path("web")
STATIC_DIR.mkdir(exist_ok=True)

# Vector store cache
_vector_store = None


def get_rag_store():
    global _vector_store
    if _vector_store is None:
        try:
            _vector_store = VectorStore()
        except Exception as e:
            print(f"RAG init warning: {e}")
            _vector_store = None
    return _vector_store


# ==========================================
# Pydantic Request Models
# ==========================================

class LoginRequest(BaseModel):
    email: str
    password: Optional[str] = "password"


class RegisterRequest(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    role: Optional[str] = "owner"
    business_name: Optional[str] = None


class BusinessUpdateRequest(BaseModel):
    name: Optional[str] = None
    business_type: Optional[str] = None
    turnover_lakh: Optional[float] = None
    employee_count: Optional[int] = None
    state: Optional[str] = None
    registration_status: Optional[str] = None
    special_category_state: Optional[bool] = None
    owner: Optional[str] = None
    pan: Optional[str] = None
    gstin: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    activity: Optional[str] = None
    aadhaar: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    business_id: Optional[str] = "B005"
    user_id: Optional[int] = 1


class WorkflowStartRequest(BaseModel):
    business_id: str
    dry_run: Optional[bool] = True


class WorkflowResumeRequest(BaseModel):
    workflow_id: str
    otp: Optional[str] = None
    missing_data: Optional[Dict[str, Any]] = None


class AgentRunRequest(BaseModel):
    prompt: Optional[str] = None
    business_id: Optional[str] = "B005"
    mission: Optional[str] = None
    workflow_id: Optional[str] = None
    user_action: Optional[Dict[str, Any]] = None


# ==========================================
# Authentication & User Endpoints
# ==========================================

@app.post("/api/auth/login")
def login_user(payload: LoginRequest):
    email = payload.email.strip().lower()
    user = get_user_by_email(email)
    if not user:
        # Create user automatically for seamless demo access
        name = email.split("@")[0].replace(".", " ").title()
        user = create_user(name=name, email=email, role="owner")

    # Find associated business
    businesses = list_businesses_from_db()
    user_biz = next((b for b in businesses if b.get("user_id") == user["user_id"] or b.get("email") == email), None)
    if not user_biz and businesses:
        user_biz = businesses[0]

    return {
        "status": "SUCCESS",
        "user": user,
        "business": user_biz,
        "token": f"token-{user['user_id']}-{uuid.uuid4().hex[:8]}",
    }


@app.post("/api/auth/register")
def register_user(payload: RegisterRequest):
    existing = get_user_by_email(payload.email)
    if existing:
        return {"status": "SUCCESS", "user": existing, "message": "User already exists. Logged in."}

    user = create_user(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        role=payload.role or "owner",
    )

    # If business name provided, create an initial business profile
    biz_name = payload.business_name or f"{payload.name}'s Enterprise"
    new_biz = save_business_to_db(
        {
            "name": biz_name,
            "owner": payload.name,
            "email": payload.email,
            "mobile": payload.phone,
            "business_type": "goods",
            "turnover_lakh": 35.0,
            "employee_count": 3,
            "state": "Madhya Pradesh",
        },
        user_id=user["user_id"],
    )

    return {
        "status": "SUCCESS",
        "user": user,
        "business": new_biz,
    }


@app.get("/api/users")
def get_all_users():
    return list_users()


# ==========================================
# Business Profile Endpoints (Retrieve & Update Anything)
# ==========================================

@app.get("/api/business")
def get_all_businesses():
    return list_businesses_from_db()


@app.get("/api/business/{business_id}")
def get_single_business(business_id: str):
    biz = get_business_from_db(business_id)
    if not biz:
        profile = get_business(business_id)
        if profile:
            biz = profile.as_dict()
    if not biz:
        raise HTTPException(status_code=404, detail=f"Business '{business_id}' not found.")
    return biz


@app.put("/api/business/{business_id}")
def update_business_profile(business_id: str, payload: BusinessUpdateRequest):
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    update_data["business_id"] = business_id

    saved = save_business_to_db(update_data)

    # Immediately re-evaluate audit findings and persist
    profile = get_business(business_id)
    if profile:
        findings = evaluate_business(profile)
        record_audit_findings(business_id, findings)

    return {
        "status": "SUCCESS",
        "message": f"Business details for '{saved.get('name')}' updated and synchronized to PostgreSQL.",
        "business": saved,
    }


@app.post("/api/business")
def create_new_business(payload: BusinessUpdateRequest):
    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    saved = save_business_to_db(data)
    return {
        "status": "SUCCESS",
        "message": f"New business '{saved.get('name')}' created successfully in PostgreSQL.",
        "business": saved,
    }


# ==========================================
# Statutory Compliance Audit Endpoints
# ==========================================

@app.get("/api/audit/{business_id}")
def get_audit_scorecard(business_id: str):
    profile = get_business(business_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Business '{business_id}' not found.")

    findings = evaluate_business(profile)
    record_audit_findings(business_id, findings)

    applicable = [f for f in findings if f.applies]
    exempt = [f for f in findings if not f.applies]

    # Calculate compliance health score (percentage)
    total = len(findings)
    score = int((1 - (len(applicable) / (total * 2))) * 100) if total > 0 else 85
    score = max(50, min(100, score))

    return {
        "business_id": business_id,
        "business_name": profile.name,
        "health_score": score,
        "total_rules_evaluated": total,
        "applicable_obligations_count": len(applicable),
        "exempt_obligations_count": len(exempt),
        "findings": [
            {
                "requirement": f.requirement,
                "applies": f.applies,
                "reason": f.reason,
                "evidence_id": f.evidence_id,
                "severity": "HIGH" if f.applies and "Registration" in f.requirement else "MEDIUM" if f.applies else "INFO",
            }
            for f in findings
        ],
    }


# ==========================================
# Gemini Vision OCR Document Ingestion
# ==========================================

@app.post("/api/documents/upload")
async def upload_document_photo(
    file: UploadFile = File(...),
    business_id: Optional[str] = Form(None),
    user_id: Optional[int] = Form(None),
):
    safe_name = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    file_path = UPLOAD_DIR / safe_name
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # Run Vision OCR ingestion pipeline
        result = ingest_document_photo(
            image_path=str(file_path),
            user_id=user_id,
            business_id=business_id,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document OCR extraction failed: {str(e)}")


# ==========================================
# Conversational Compliance Assistant
# ==========================================

@app.post("/api/chat")
def compliance_chat(payload: ChatRequest):
    return run_compliance_chat(
        message=payload.message,
        business_id=payload.business_id or "B005",
    )


# ==========================================
# Udyam Workflow Endpoints
# ==========================================

@app.post("/api/workflow/udyam/start")
def start_udyam_endpoint(payload: WorkflowStartRequest):
    biz = get_business(payload.business_id)
    if not biz:
        raise HTTPException(status_code=404, detail=f"Business '{payload.business_id}' not found.")

    wf_id = f"WF-UDYAM-{payload.business_id}"
    biz_data = biz.as_dict()
    if not biz_data.get("aadhaar") or "X" in str(biz_data.get("aadhaar", "")):
        biz_data["aadhaar"] = "987654321098"

    summary = start_udyam_workflow(
        workflow_id=wf_id,
        business_data=biz_data,
        dry_run=payload.dry_run if payload.dry_run is not None else True,
    )
    return summary


@app.post("/api/workflow/udyam/resume")
def resume_udyam_endpoint(payload: WorkflowResumeRequest):
    action = {}
    if payload.otp:
        action["otp"] = payload.otp
    elif payload.missing_data:
        action["data"] = payload.missing_data
    else:
        raise HTTPException(status_code=400, detail="Must provide 'otp' or 'missing_data'.")

    summary = resume_udyam_workflow(payload.workflow_id, action)
    return summary


# ==========================================
# Agentic Compliance Automation Engine
# ==========================================

@app.post("/api/agent/run")
def run_agent_engine(payload: AgentRunRequest):
    return run_compliance_agent(
        business_id=payload.business_id,
        mission=payload.mission,
        prompt=payload.prompt,
        user_action=payload.user_action,
        workflow_id=payload.workflow_id,
    )


# ==========================================
# Static Files & SPA Fallback
# ==========================================

app.mount("/assets", StaticFiles(directory="web/assets"), name="assets")
app.mount("/static", StaticFiles(directory="web"), name="static")


@app.get("/")
def serve_index():
    index_path = Path("web/index.html")
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "SME Audit AI API running. Web files loading..."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
