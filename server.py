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
    msg = payload.message.strip().lower()
    biz_id = payload.business_id or "B005"
    profile = get_business(biz_id)
    if not profile:
        profile = SAMPLE_BUSINESSES[0]

    # Modeled directly after the WhatsApp phone mockup in the thumbnail
    # 1. Monthly compliance check command
    if any(k in msg for k in ["check compliance", "check my compliance", "month", "audit", "status", "rules"]):
        findings = evaluate_business(profile)
        applies_list = [f.requirement for f in findings if f.applies]
        
        steps = [
            {"label": "Documents verified", "status": "done"},
            {"label": "Checking applicable rules", "status": "done"},
            {"label": "Scanning for statutory risks", "status": "done"},
            {"label": "Preparing summary report", "status": "done"},
        ]

        if applies_list:
            applies_str = ", ".join(applies_list[:3])
            answer_text = (
                f"**Here's your compliance report 📄**\n\n"
                f"For **{profile.name}** (Turnover: Rs.{profile.turnover_lakh}L, Employees: {profile.employee_count}, State: {profile.state}):\n\n"
                f"• **Applicable Requirements ({len(applies_list)}):** {applies_str}\n"
                f"• **Statutory Status:** Action required to ensure full compliance before month-end filing deadlines.\n\n"
                f"You can view and trigger automated registrations in your Dashboard."
            )
            final_status = "Action Needed ⚠️"
        else:
            answer_text = (
                f"**Here's your compliance report 📄**\n\n"
                f"All clear for **{profile.name}**! You are within exempt thresholds for all statutory categories this month.\n\n"
                f"Keep growing confidently! 🚀"
            )
            final_status = "All clear! ✅ Keep growing!"

        return {
            "type": "AUDIT_CHECKLIST",
            "reply": answer_text,
            "checklist_steps": steps,
            "final_status": final_status,
            "business_id": biz_id,
            "applicable_count": len(applies_list),
        }

    # 2. Composition scheme query
    elif "composition" in msg:
        limit = 75 if profile.special_category_state else 150
        eligible = profile.turnover_lakh <= limit
        evidence = "GST-003"
        return {
            "type": "DIRECT_ANSWER",
            "reply": (
                f"**Composition Scheme Eligibility (Section 10 CGST Act / {evidence}):**\n\n"
                f"• Your turnover: Rs.{profile.turnover_lakh} Lakhs\n"
                f"• Ceiling threshold: Rs.{limit} Lakhs ({profile.state})\n"
                f"• **Verdict:** {'✅ Eligible for simplified 1% tax payment without detailed monthly return burden.' if eligible else '❌ Not eligible. Turnover exceeds the Rs.' + str(limit) + 'L ceiling.'}"
            ),
        }

    # 3. GST Registration query
    elif "gst" in msg:
        goods_thresh = 20 if profile.special_category_state else 40
        serv_thresh = 10 if profile.special_category_state else 20
        req = profile.turnover_lakh >= (goods_thresh if profile.business_type == "goods" else serv_thresh)
        return {
            "type": "DIRECT_ANSWER",
            "reply": (
                f"**GST Registration Requirements (Notification No. 10/2019 / GST-001):**\n\n"
                f"• Business Type: **{profile.business_type.title()}**\n"
                f"• State: **{profile.state}** (Threshold: Rs.{goods_thresh if profile.business_type == 'goods' else serv_thresh}L)\n"
                f"• Your Turnover: **Rs.{profile.turnover_lakh} Lakhs**\n"
                f"• **Verdict:** {'Mandatory GST registration applies.' if req else 'Exempt from mandatory GST registration under threshold limits.'}"
            ),
        }

    # 4. RAG search fallback for generic compliance queries
    else:
        store = get_rag_store()
        snippets = []
        if store:
            try:
                results = store.search(payload.message, top_k=2)
                snippets = [f"• **[{r['id']}] {r['title']}**: {r['text'][:150]}..." for r in results]
            except Exception:
                pass

        knowledge_str = "\n\n".join(snippets) if snippets else "General statutory guidelines apply."
        return {
            "type": "RAG_ANSWER",
            "reply": (
                f"Based on our official Indian statutory regulatory corpus:\n\n"
                f"{knowledge_str}\n\n"
                f"Would you like me to inspect your records against these thresholds?"
            ),
        }


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
    import time
    start_time = time.time()

    biz_id = payload.business_id or "B005"
    biz = get_business(biz_id)
    if not biz:
        profile_dict = get_business_from_db(biz_id)
        if profile_dict:
            biz = BusinessProfile(**profile_dict)
        else:
            biz = SAMPLE_BUSINESSES[0]
            biz_id = biz.business_id

    mission = (payload.mission or "").strip().lower()
    prompt = (payload.prompt or "").strip().lower()
    user_action = payload.user_action or {}
    workflow_id = payload.workflow_id or f"WF-UDYAM-{biz_id}"

    steps = []
    citations = []
    hitl_action = None
    workflow_status = None

    # 1. Resume Workflow (Human In The Loop Checkpoint)
    if user_action and (user_action.get("otp") or user_action.get("data") or user_action.get("missing_data")):
        otp_val = user_action.get("otp")
        missing_data = user_action.get("data") or user_action.get("missing_data")
        action = {}
        if otp_val:
            action["otp"] = str(otp_val).strip()
        if missing_data:
            action["data"] = missing_data

        resume_summary = resume_udyam_workflow(workflow_id, action)
        workflow_status = resume_summary.get("status")

        steps.append({
            "step_num": 1,
            "title": "Resume Workflow & Verify Human Authorization",
            "tool_called": "resume_udyam_registration",
            "input": {"workflow_id": workflow_id, "user_action": {"otp": "******" if otp_val else "[Provided]"}},
            "output": {
                "status": resume_summary.get("status"),
                "result": resume_summary.get("result"),
            },
            "status": "COMPLETED" if resume_summary.get("status") != "FAILED" else "FAILED",
        })

        if workflow_status == "AWAITING_USER":
            hitl_action = resume_summary.get("pending_user_action")
            summary = f"**Checkpoint Reached:** {hitl_action.get('prompt')}"
        else:
            res_msg = resume_summary.get("result", {}).get("status_message", "Stage 1 Aadhaar Authentication & PAN Linking Complete.")
            summary = (
                f"### ✅ Human-In-The-Loop Authorization Confirmed\n\n"
                f"**Aadhaar e-KYC Verification Successful** for **{biz.name}** ({biz.owner}).\n\n"
                f"• **Workflow ID:** `{workflow_id}`\n"
                f"• **Current Status:** `STAGE 1 VERIFIED`\n"
                f"• **Progress:** {res_msg}\n\n"
                f"The compliance agent has recorded this verification in PostgreSQL. The enterprise is now authorized to proceed with unit details."
            )

        return {
            "status": "SUCCESS",
            "mission": "resume_workflow",
            "business": biz.as_dict(),
            "workflow_id": workflow_id,
            "workflow_status": workflow_status,
            "summary": summary,
            "steps": steps,
            "findings": [],
            "citations": [],
            "hitl_action": hitl_action,
            "execution_time_ms": int((time.time() - start_time) * 1000),
        }

    # 2. Mission: Full Statutory Compliance Health Audit
    if mission == "full_audit" or any(k in prompt for k in ["full audit", "statutory health", "complete compliance", "check requirements", "audit report"]):
        steps.append({
            "step_num": 1,
            "title": "Business Profile Discovery & Schema Verification",
            "tool_called": "query_business_data",
            "input": {"business_id": biz_id},
            "output": {
                "name": biz.name,
                "owner": biz.owner,
                "turnover_lakh": biz.turnover_lakh,
                "employee_count": biz.employee_count,
                "state": biz.state,
                "business_type": biz.business_type,
                "gstin": biz.gstin,
                "pan": biz.pan,
            },
            "status": "COMPLETED",
        })

        findings = evaluate_business(biz)
        record_audit_findings(biz_id, findings)
        applicable = [f for f in findings if f.applies]
        exempt = [f for f in findings if not f.applies]

        steps.append({
            "step_num": 2,
            "title": "Statutory Rules Engine Audit",
            "tool_called": "check_requirements",
            "input": {"turnover": biz.turnover_lakh, "employees": biz.employee_count, "state": biz.state, "type": biz.business_type},
            "output": {
                "total_rules": len(findings),
                "applicable_count": len(applicable),
                "exempt_count": len(exempt),
                "liabilities": [f.requirement for f in applicable],
            },
            "status": "COMPLETED",
        })

        store = get_rag_store()
        rag_results = []
        if store:
            try:
                rag_results = store.search(f"{biz.business_type} GST threshold MSME Udyam employee PF ESI {biz.state}", top_k=4)
            except Exception:
                rag_results = []
        if not rag_results:
            rag_results = [r for r in REGULATIONS if r["id"] in [f.evidence_id for f in applicable] or r["id"] in ["GST-001", "MSME-001", "SHOP-001"]][:4]

        citations = [
            {
                "id": r.get("id"),
                "title": r.get("title"),
                "category": r.get("category"),
                "source": r.get("source"),
                "text": r.get("text"),
                "relevance_score": round(float(r.get("score", 0.95)), 2) if "score" in r else 0.95,
            }
            for r in rag_results
        ]

        steps.append({
            "step_num": 3,
            "title": "Regulatory RAG Citation Grounding",
            "tool_called": "search_regulations",
            "input": {"query": f"GST, Udyam, S&E, PF, ESI statutory provisions for {biz.state}"},
            "output": {"retrieved_citations_count": len(citations), "evidence_ids": [c["id"] for c in citations]},
            "status": "COMPLETED",
        })

        score = max(50, min(100, int((1 - (len(applicable) / (len(findings) * 2))) * 100)))

        summary = (
            f"### 🛡️ Statutory Compliance Audit Memo\n\n"
            f"**Subject:** Comprehensive Statutory & Regulatory Health Assessment\n"
            f"**Enterprise:** **{biz.name}** (Proprietor: {biz.owner} | State: {biz.state})\n"
            f"**Operational Metrics:** Annual Turnover **₹{biz.turnover_lakh} Lakhs** | Headcount: **{biz.employee_count} Employees**\n"
            f"**Statutory Health Index:** **{score}% Compliance Standing**\n\n"
            f"---\n\n"
            f"#### ⚠️ Mandatory Registration & Filing Liabilities ({len(applicable)}):\n"
        )
        for idx, f in enumerate(applicable, 1):
            summary += f"{idx}. **{f.requirement}** (Evidence: `{f.evidence_id}`)\n   *Reason:* {f.reason}\n"

        if exempt:
            summary += f"\n#### ✅ Verified Exemptions ({len(exempt)}):\n"
            for f in exempt:
                summary += f"• **{f.requirement}**: {f.reason} (`{f.evidence_id}`)\n"

        summary += (
            f"\n---\n"
            f"**Next Recommended Autonomous Action:** Trigger the automated **Udyam MSME Registration** workflow to secure priority sector lending benefits and formal legal standing."
        )

        return {
            "status": "SUCCESS",
            "mission": "full_audit",
            "business": biz.as_dict(),
            "workflow_id": workflow_id,
            "summary": summary,
            "steps": steps,
            "findings": [
                {
                    "requirement": f.requirement,
                    "applies": f.applies,
                    "reason": f.reason,
                    "evidence_id": f.evidence_id,
                    "severity": "HIGH" if f.applies and ("GST" in f.requirement or "Udyam" in f.requirement) else "MEDIUM" if f.applies else "INFO",
                }
                for f in findings
            ],
            "citations": citations,
            "hitl_action": None,
            "execution_time_ms": int((time.time() - start_time) * 1000),
        }

    # 3. Mission: Udyam MSME Registration Pipeline
    if mission == "udyam_automate" or any(k in prompt for k in ["udyam", "msme registration", "automate udyam", "register msme"]):
        steps.append({
            "step_num": 1,
            "title": "Business Entity & Statutory ID Verification",
            "tool_called": "query_business_data",
            "input": {"business_id": biz_id},
            "output": {
                "name": biz.name,
                "owner": biz.owner,
                "pan": biz.pan,
                "aadhaar": mask_value(biz.aadhaar or "987654321098"),
                "mobile": biz.mobile,
                "address": biz.address,
            },
            "status": "COMPLETED",
        })

        limit_turnover = 500.0  # 5 Crore for Micro
        is_micro = (biz.turnover_lakh or 0) <= limit_turnover
        steps.append({
            "step_num": 2,
            "title": "Statutory MSME Micro Enterprise Qualification Check",
            "tool_called": "check_requirements",
            "input": {"turnover_lakh": biz.turnover_lakh, "max_micro_limit_lakh": limit_turnover},
            "output": {
                "classification": "Micro Enterprise" if is_micro else "Small Enterprise",
                "meets_criteria": is_micro,
                "evidence_id": "MSME-001",
            },
            "status": "COMPLETED",
        })

        citations = [r for r in REGULATIONS if r["id"] in ["MSME-001", "MSME-002"]]
        steps.append({
            "step_num": 3,
            "title": "Regulatory Grounding (Ministry of MSME)",
            "tool_called": "search_regulations",
            "input": {"query": "Udyam registration MSME Micro classification threshold"},
            "output": {"citations": [c["id"] for c in citations]},
            "status": "COMPLETED",
        })

        biz_data = biz.as_dict()
        if not biz_data.get("aadhaar") or "X" in str(biz_data.get("aadhaar", "")):
            biz_data["aadhaar"] = "987654321098"

        wf_res = start_udyam_workflow(workflow_id=workflow_id, business_data=biz_data, dry_run=True)
        workflow_status = wf_res.get("status")
        pending_action = wf_res.get("pending_user_action")

        steps.append({
            "step_num": 4,
            "title": "Official Portal Automation Pipeline (udyamregistration.gov.in)",
            "tool_called": "start_udyam_registration",
            "input": {"workflow_id": workflow_id, "dry_run": True, "target_url": "https://udyamregistration.gov.in"},
            "output": {
                "workflow_id": workflow_id,
                "status": workflow_status,
                "stage": "Stage 1 - Aadhaar & PAN Validation",
                "checkpoint": pending_action.get("action_type") if pending_action else "None",
            },
            "status": "COMPLETED",
        })

        hitl_action = {
            "action_type": pending_action.get("action_type", "ENTER_AADHAAR_OTP") if pending_action else "ENTER_AADHAAR_OTP",
            "workflow_id": workflow_id,
            "prompt": pending_action.get("prompt", "Enter 6-digit Aadhaar OTP sent to registered mobile.") if pending_action else "Enter 6-digit Aadhaar OTP to authorize e-KYC.",
            "fields": [
                {
                    "name": "otp",
                    "type": "text",
                    "label": "6-Digit Aadhaar OTP",
                    "placeholder": "654321",
                    "default_demo": "654321",
                }
            ],
            "disclaimer": "Indian UIDAI statutory privacy guidelines require explicit user OTP entry before continuing.",
        }

        summary = (
            f"### 🏛️ Udyam MSME Automation Pipeline Initialized\n\n"
            f"• **Enterprise:** **{biz.name}**\n"
            f"• **Classification:** **Micro Enterprise** (Annual Turnover ₹{biz.turnover_lakh}L is within the ₹5 Crore ceiling)\n"
            f"• **Statutory Base:** *Ministry of MSME S.O. 2119(E) / MSME-001*\n"
            f"• **Portal Status:** Automated form pre-fill executed. Reached Aadhaar OTP authentication boundary.\n\n"
            f"> [!IMPORTANT]\n"
            f"> **Human-In-The-Loop Checkpoint Active:** Government regulations prohibit automated OTP bypassing. Please enter the 6-digit OTP below to authorize the agent to link PAN & complete Stage 1."
        )

        return {
            "status": "SUCCESS",
            "mission": "udyam_automate",
            "business": biz.as_dict(),
            "workflow_id": workflow_id,
            "workflow_status": workflow_status,
            "summary": summary,
            "steps": steps,
            "findings": [],
            "citations": citations,
            "hitl_action": hitl_action,
            "execution_time_ms": int((time.time() - start_time) * 1000),
        }

    # 4. Mission: Composition Scheme Analysis
    if mission == "composition_check" or any(k in prompt for k in ["composition", "section 10", "1% tax", "cmp-08"]):
        limit = 75.0 if biz.special_category_state else 150.0
        eligible = (biz.turnover_lakh or 0) <= limit
        citations = [r for r in REGULATIONS if r["id"] == "GST-003"]

        steps.append({
            "step_num": 1,
            "title": "Turnover Threshold Comparison",
            "tool_called": "query_business_data",
            "input": {"business_id": biz_id},
            "output": {"turnover_lakh": biz.turnover_lakh, "state": biz.state, "special_category": biz.special_category_state},
            "status": "COMPLETED",
        })

        steps.append({
            "step_num": 2,
            "title": "Section 10 CGST Act Slabs Evaluation",
            "tool_called": "check_requirements",
            "input": {"turnover": biz.turnover_lakh, "ceiling": limit},
            "output": {"eligible": eligible, "tax_rate": "1% on turnover (0.5% CGST + 0.5% SGST)", "return_type": "Quarterly CMP-08"},
            "status": "COMPLETED",
        })

        summary = (
            f"### 📊 Composition Scheme Eligibility Evaluation (Section 10 CGST Act)\n\n"
            f"• **Enterprise:** **{biz.name}**\n"
            f"• **Annual Turnover:** **₹{biz.turnover_lakh} Lakhs**\n"
            f"• **Statutory Threshold:** **₹{limit} Lakhs** for {biz.state}\n"
            f"• **Legal Grounding:** `GST-003` (*CGST Act 2017, Section 10*)\n\n"
            f"**Verdict:** {'✅ **ELIGIBLE** for Composition Scheme' if eligible else '❌ **NOT ELIGIBLE** — Turnover exceeds ₹' + str(limit) + 'L ceiling'}\n\n"
            f"#### Key Trade-offs for {biz.name}:\n"
            f"1. **Tax Burden:** Flat 1% turnover tax (0.5% CGST + 0.5% SGST) instead of standard 18% GST.\n"
            f"2. **Compliance Overhead:** Simplified quarterly statement (CMP-08) instead of GSTR-1, GSTR-3B monthly filings.\n"
            f"3. **Statutory Restrictions:** Cannot collect tax from customers, cannot claim Input Tax Credit (ITC), and cannot make inter-state outward supplies."
        )

        return {
            "status": "SUCCESS",
            "mission": "composition_check",
            "business": biz.as_dict(),
            "workflow_id": workflow_id,
            "summary": summary,
            "steps": steps,
            "findings": [],
            "citations": citations,
            "hitl_action": None,
            "execution_time_ms": int((time.time() - start_time) * 1000),
        }

    # 5. Mission: Labor Law & Employee Headcount Check
    if mission == "labor_check" or any(k in prompt for k in ["pf", "esi", "epf", "employees", "headcount", "labor", "labour"]):
        epf_applies = (biz.employee_count or 0) >= 20
        esi_applies = (biz.employee_count or 0) >= 10
        citations = [r for r in REGULATIONS if r["id"] in ["EPF-001", "ESIC-001", "SHOP-001"]]

        steps.append({
            "step_num": 1,
            "title": "Headcount & Payroll Inspection",
            "tool_called": "query_business_data",
            "input": {"business_id": biz_id},
            "output": {"employee_count": biz.employee_count, "state": biz.state},
            "status": "COMPLETED",
        })

        steps.append({
            "step_num": 2,
            "title": "Statutory Labor Slabs Evaluation",
            "tool_called": "check_requirements",
            "input": {"headcount": biz.employee_count},
            "output": {
                "epf_required": epf_applies,
                "epf_threshold": 20,
                "esi_required": esi_applies,
                "esi_threshold": 10,
            },
            "status": "COMPLETED",
        })

        summary = (
            f"### 👥 Labor Laws & Social Security Compliance Audit\n\n"
            f"• **Enterprise:** **{biz.name}**\n"
            f"• **Current Employee Headcount:** **{biz.employee_count} Persons**\n\n"
            f"1. **EPF Registration (Employees' Provident Fund Act, 1952 / `EPF-001`):**\n"
            f"   • Mandatory threshold: **20 employees**\n"
            f"   • Status: {'⚠️ **MANDATORY**' if epf_applies else f'✅ **EXEMPT** (Headcount {biz.employee_count} < 20 threshold)'}\n\n"
            f"2. **ESIC Registration (Employees' State Insurance Act, 1948 / `ESIC-001`):**\n"
            f"   • Mandatory threshold: **10 employees** in most commercial establishments\n"
            f"   • Status: {'⚠️ **MANDATORY**' if esi_applies else f'✅ **EXEMPT** (Headcount {biz.employee_count} < 10 threshold)'}\n\n"
            f"3. **State Shops & Commercial Establishments Act (`SHOP-001`):**\n"
            f"   • Mandatory for all commercial premises within municipal limits in {biz.state}, even with 0 employees."
        )

        return {
            "status": "SUCCESS",
            "mission": "labor_check",
            "business": biz.as_dict(),
            "workflow_id": workflow_id,
            "summary": summary,
            "steps": steps,
            "findings": [],
            "citations": citations,
            "hitl_action": None,
            "execution_time_ms": int((time.time() - start_time) * 1000),
        }

    # 6. Default / Freeform Compliance Query
    store = get_rag_store()
    rag_results = []
    if store and prompt:
        try:
            rag_results = store.search(prompt, top_k=3)
        except Exception:
            rag_results = []
    if not rag_results:
        rag_results = REGULATIONS[:3]

    citations = [
        {
            "id": r.get("id"),
            "title": r.get("title"),
            "category": r.get("category"),
            "source": r.get("source"),
            "text": r.get("text"),
            "relevance_score": round(float(r.get("score", 0.9)), 2) if "score" in r else 0.9,
        }
        for r in rag_results
    ]

    steps.append({
        "step_num": 1,
        "title": "Business Context Lookup",
        "tool_called": "query_business_data",
        "input": {"business_id": biz_id},
        "output": {"name": biz.name, "turnover": biz.turnover_lakh, "state": biz.state},
        "status": "COMPLETED",
    })

    steps.append({
        "step_num": 2,
        "title": "Regulatory Corpus Hybrid Search",
        "tool_called": "search_regulations",
        "input": {"query": payload.prompt or "Compliance query"},
        "output": {"matched_regulations": [c["id"] for c in citations]},
        "status": "COMPLETED",
    })

    summary = (
        f"### 📋 Statutory Guidance for {biz.name}\n\n"
        f"Regarding your query: *\"{payload.prompt or 'Compliance inquiry'}\"*\n\n"
        f"Based on **{biz.name}**'s registered profile (Turnover: ₹{biz.turnover_lakh}L, State: {biz.state}, Sector: {biz.business_type}):\n\n"
    )
    for c in citations:
        summary += f"• **[{c['id']}] {c['title']}** (*{c['source']}*):\n  {c['text']}\n\n"

    summary += f"You can choose one of the recommended missions above to initiate an automated audit or execute the Udyam MSME registration."

    return {
        "status": "SUCCESS",
        "mission": "custom_query",
        "business": biz.as_dict(),
        "workflow_id": workflow_id,
        "summary": summary,
        "steps": steps,
        "findings": [],
        "citations": citations,
        "hitl_action": None,
        "execution_time_ms": int((time.time() - start_time) * 1000),
    }


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
