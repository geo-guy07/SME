"""
FastAPI Server — SME Compliance & Audit Assistant
Unified backend providing REST APIs for:
- Statutory Compliance Audits
- AI Compliance Agent Chat
- Human-in-the-Loop Registration Automation (Udyam)
- Multimodal Document & Invoice Ingestion
- Official PDF Report Generation
- Regulatory Knowledge Base Browser
"""

import os
import json
import shutil
from typing import Optional, Dict, Any, List
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.business_profile import SAMPLE_BUSINESSES, get_business, BusinessProfile
from core.rules_engine import check_requirements, evaluate_business
from core.workflow import start_udyam_workflow, resume_udyam_workflow, ACTIVE_WORKFLOWS, WorkflowStatus
from core.doc_extractor import extract_document
from core.report_generator import generate_pdf_report
from core.database import (
    init_db,
    SessionLocal,
    Business,
    FindingRecord,
    QuerySession,
    ToolCallLog,
    DocumentUpload,
    WorkflowRecord,
    persist_findings,
    log_tool_call,
)
from rag.regulations import REGULATIONS
from rag.vector_store import VectorStore

app = FastAPI(
    title="SME Compliance & Audit Assistant",
    description="Agentic AI Compliance, Statutory Audit & Registration Automation for Indian SMEs",
    version="2.0.0",
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent
WEB_DIR = BASE_DIR / "web"
UPLOADS_DIR = BASE_DIR / "uploads"
REPORTS_DIR = BASE_DIR / "reports"
UPLOADS_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

# Shared VectorStore instance
_vector_store: Optional[VectorStore] = None

def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


# ---- Pydantic Schemas ----
class CustomAuditRequest(BaseModel):
    name: str = "Custom SME"
    business_type: str = "goods"  # "goods" or "services"
    turnover_lakh: float = 45.0
    employee_count: int = 4
    state: str = "Madhya Pradesh"
    special_category_state: bool = False
    activity: Optional[str] = "Trading"
    owner: Optional[str] = "Proprietor"
    pan: Optional[str] = "ABCDE1234F"
    aadhaar: Optional[str] = "987654321098"
    mobile: Optional[str] = "9876543210"
    email: Optional[str] = "owner@example.com"
    address: Optional[str] = "Indore, MP"


class ChatMessageRequest(BaseModel):
    message: str
    business_id: Optional[str] = "B005"
    session_id: Optional[str] = "web-session-default"


class WorkflowStartRequest(BaseModel):
    business_id: str
    dry_run: bool = True


class WorkflowResumeRequest(BaseModel):
    workflow_id: str
    otp: Optional[str] = None
    missing_data: Optional[Dict[str, Any]] = None


# ---- Endpoints ----

@app.get("/")
def serve_index():
    """Serve the single-page application dashboard."""
    index_file = WEB_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse("<h1>Web UI is building...</h1>")
    return FileResponse(str(index_file))


@app.get("/api/businesses")
def list_businesses():
    """Retrieve all available registered and sample businesses."""
    db = SessionLocal()
    try:
        db_businesses = db.query(Business).all()
        if db_businesses:
            return [b.as_dict() for b in db_businesses]
    except Exception:
        pass
    finally:
        db.close()
    return [b.as_dict() for b in SAMPLE_BUSINESSES]


@app.get("/api/business/{business_id}")
def get_business_details(business_id: str):
    """Retrieve details for a specific business."""
    biz = get_business(business_id)
    if not biz:
        raise HTTPException(status_code=404, detail=f"Business '{business_id}' not found.")
    return biz.as_dict()


@app.get("/api/audit/{business_id}")
def audit_business(business_id: str):
    """Run complete statutory compliance audit against a business ID."""
    findings = check_requirements(business_id)
    if not findings or findings.get("error"):
        raise HTTPException(status_code=404, detail=findings.get("error", "Audit failed."))
    return findings


@app.post("/api/audit/custom")
def audit_custom(req: CustomAuditRequest):
    """Evaluate compliance rules for custom user input on the fly."""
    temp_biz = BusinessProfile(
        business_id="CUSTOM",
        name=req.name,
        turnover_lakh=req.turnover_lakh,
        employee_count=req.employee_count,
        state=req.state,
        business_type=req.business_type,
        special_category_state=req.special_category_state,
        owner=req.owner,
        activity=req.activity,
        pan=req.pan,
        aadhaar=req.aadhaar,
        mobile=req.mobile,
        email=req.email,
        address=req.address,
    )
    raw_findings = evaluate_business(temp_biz)
    findings = []
    for f in raw_findings:
        entry = {
            "requirement": f.requirement,
            "applies": f.applies,
            "reason": f.reason,
            "evidence_id": f.evidence_id,
            "severity": f.severity,
        }
        if "udyam" in f.requirement.lower() and f.applies:
            entry["workflow_available"] = "udyam_registration"
        findings.append(entry)

    return {
        "business_id": "CUSTOM",
        "business_name": req.name,
        "applicable_count": sum(1 for f in findings if f["applies"]),
        "findings": findings,
    }


@app.post("/api/chat")
def chat_with_agent(req: ChatMessageRequest):
    """
    Conversational Agent Endpoint:
    Processes user query, executes relevant tool calls, retrieves statutory grounding,
    and returns response with citation badges and reasoning steps.
    """
    biz_id = req.business_id or "B005"
    biz = get_business(biz_id)
    query = req.message.strip()

    # Track session in DB
    db = SessionLocal()
    try:
        session = db.query(QuerySession).filter(QuerySession.session_id == req.session_id).first()
        if not session:
            session = QuerySession(session_id=req.session_id, business_id=biz_id, summary="Web Chat Session")
            db.add(session)
            db.commit()
    except Exception:
        pass
    finally:
        db.close()

    # 1. Check if GEMINI_API_KEY is active for live agentic reasoning
    gemini_key = os.environ.get("GEMINI_API_KEY")
    tools_invoked = []
    retrieved_citations = []

    # Run hybrid vector search for relevant regulations
    try:
        vstore = get_vector_store()
        rag_hits = vstore.search(query=query, top_k=3)
        retrieved_citations = [
            {"id": h["id"], "title": h["title"], "category": h["category"], "source": h["source"], "text": h["text"][:160] + "..."}
            for h in rag_hits
        ]
    except Exception as e:
        print(f"  [ChatAPI] RAG search note: {e}")

    if gemini_key:
        try:
            from agent_demo import run_agent_with_gemini
            prompt = f"User is asking about Business ID '{biz_id}' ({biz.name if biz else 'SME'}). Question: {query}"
            answer = run_agent_with_gemini(prompt)
            tools_invoked.append({"tool": "gemini_function_calling", "query": query})
            return {
                "response": answer,
                "citations": retrieved_citations,
                "tools_invoked": tools_invoked,
                "business_id": biz_id,
            }
        except Exception as e:
            print(f"  [ChatAPI] Live Gemini call error: {e}. Falling back to structured response.")

    # 2. Intelligent Structured Fallback
    lower = query.lower()
    answer_parts = []

    if any(k in lower for k in ["audit", "requirement", "need", "eligible", "compliance", "register"]):
        audit_res = check_requirements(biz_id)
        tools_invoked.append({"tool": "check_requirements", "business_id": biz_id})
        log_tool_call(req.session_id, "check_requirements", {"business_id": biz_id}, audit_res)
        
        applicable = [f for f in audit_res["findings"] if f["applies"]]
        exempt = [f for f in audit_res["findings"] if not f["applies"]]
        
        answer_parts.append(
            f"Based on **{biz.name}** (Turnover: ₹{biz.turnover_lakh}L, Employees: {biz.employee_count}, State: {biz.state}), "
            f"we identified **{len(applicable)} mandatory compliance obligations**:"
        )
        for f in applicable:
            answer_parts.append(f"• **{f['requirement']}** ({f['severity']}): {f['reason']} *(Evidence: {f['evidence_id']})*")
        
        if exempt:
            exempt_reqs = ", ".join(f["requirement"] for f in exempt[:3])
            answer_parts.append(f"\nCurrently exempt from: {exempt_reqs}.")

    elif any(k in lower for k in ["udyam", "msme", "start registration"]):
        tools_invoked.append({"tool": "start_udyam_registration", "business_id": biz_id})
        wf_res = start_udyam_workflow(f"WF-UDYAM-{biz_id}", biz.as_dict() if biz else {}, dry_run=True)
        log_tool_call(req.session_id, "start_udyam_registration", {"business_id": biz_id}, wf_res)
        
        answer_parts.append(
            f"Initiated Udyam MSME Registration for **{biz.name}**. "
            f"The workflow is currently in state **{wf_res['status']}**."
        )
        if wf_res.get("pending_user_action"):
            p = wf_res["pending_user_action"]
            answer_parts.append(f"\n⚠️ **Action Required**: {p.get('prompt')}")
            answer_parts.append("You can switch to the **Registration Automation** tab to input your Aadhaar OTP!")

    elif any(k in lower for k in ["report", "pdf", "download"]):
        tools_invoked.append({"tool": "generate_compliance_report", "business_id": biz_id})
        pdf_path = generate_pdf_report(biz_id)
        log_tool_call(req.session_id, "generate_compliance_report", {"business_id": biz_id}, {"path": pdf_path})
        answer_parts.append(
            f"Generated official compliance audit dossier for **{biz.name}**. "
            f"You can download your PDF report in the **Audit Report Center** tab or at `/api/report/download/{biz_id}`."
        )
    else:
        # Grounded RAG Answer
        tools_invoked.append({"tool": "search_regulations", "query": query})
        log_tool_call(req.session_id, "search_regulations", {"query": query}, retrieved_citations)
        answer_parts.append(f"Here is the relevant statutory guidance based on Indian regulatory provisions:")
        for c in retrieved_citations[:2]:
            answer_parts.append(f"• **{c['title']} ({c['id']})**: {c['text']}")

    final_text = "\n\n".join(answer_parts) if answer_parts else (
        f"I have reviewed the profile for **{biz.name}**. How can I assist you with GST, Udyam MSME, labor codes, or tax compliance?"
    )

    return {
        "response": final_text,
        "citations": retrieved_citations,
        "tools_invoked": tools_invoked,
        "business_id": biz_id,
    }


@app.post("/api/workflow/start")
def api_start_workflow(req: WorkflowStartRequest):
    """Start the Udyam registration automation state machine."""
    biz = get_business(req.business_id)
    if not biz:
        raise HTTPException(status_code=404, detail=f"Business '{req.business_id}' not found.")

    workflow_id = f"WF-UDYAM-{req.business_id}"
    summary = start_udyam_workflow(
        workflow_id=workflow_id,
        business_data=biz.as_dict(),
        dry_run=req.dry_run,
        headless=True,
    )
    return summary


@app.post("/api/workflow/resume")
def api_resume_workflow(req: WorkflowResumeRequest):
    """Resume a paused workflow awaiting human action (e.g. OTP)."""
    if req.missing_data:
        action = {"data": req.missing_data}
    elif req.otp:
        action = {"otp": req.otp}
    else:
        raise HTTPException(status_code=400, detail="Must provide 'otp' or 'missing_data'.")

    summary = resume_udyam_workflow(req.workflow_id, action)
    if "error" in summary:
        raise HTTPException(status_code=400, detail=summary["error"])
    return summary


@app.get("/api/workflow/status/{workflow_id}")
def api_get_workflow_status(workflow_id: str):
    """Get latest state and history for an active workflow."""
    wf = ACTIVE_WORKFLOWS.get(workflow_id)
    if wf:
        return wf.get_summary()

    # Query database
    db = SessionLocal()
    try:
        rec = db.query(WorkflowRecord).filter(WorkflowRecord.workflow_id == workflow_id).first()
        if rec:
            return {
                "workflow_id": rec.workflow_id,
                "workflow_name": rec.workflow_name,
                "status": rec.status,
                "pending_user_action": json.loads(rec.pending_action_json) if rec.pending_action_json else None,
                "result": json.loads(rec.result_json) if rec.result_json else None,
                "steps": json.loads(rec.steps_log_json) if rec.steps_log_json else [],
            }
    finally:
        db.close()

    raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found.")


@app.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...),
    business_id: Optional[str] = Form(None)
):
    """
    Multimodal Document Ingestion:
    Upload invoice, utility bill, PAN card, or GST certificate.
    Returns structured extracted fields with confidence score.
    """
    file_path = UPLOADS_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = extract_document(
        file_path=str(file_path),
        mime_type=file.content_type,
        business_id=business_id,
    )
    return result


@app.get("/api/report/download/{business_id}")
def download_pdf_report(business_id: str):
    """Generate and return official branded PDF compliance audit report."""
    try:
        pdf_path = generate_pdf_report(business_id)
        return FileResponse(
            path=pdf_path,
            filename=os.path.basename(pdf_path),
            media_type="application/pdf",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation error: {str(e)}")


@app.get("/api/regulations")
def list_regulations(category: Optional[str] = None, search: Optional[str] = None):
    """Browse or search the 32 statutory regulations in the knowledge base."""
    vstore = get_vector_store()
    if search:
        return vstore.search(query=search, category_filter=category, top_k=10)
    
    results = REGULATIONS
    if category and category.lower() != "all":
        results = [r for r in results if r["category"].lower() == category.lower()]
    return results


# ---- Expanded Capabilities: GSTIN, Ledger 43B(h), CA Portfolio ----

class GSTINVerifyRequest(BaseModel):
    gstin: str

@app.post("/api/gstin/verify")
def api_verify_gstin(req: GSTINVerifyRequest):
    """Look up taxpayer details and filing track record from a 15-character GSTIN."""
    from core.gstin_checker import verify_gstin
    result = verify_gstin(req.gstin)
    if not result.get("valid"):
        raise HTTPException(status_code=400, detail=result.get("error", "Invalid GSTIN format."))
    return result


@app.post("/api/gstin/import")
def api_import_gstin(req: GSTINVerifyRequest):
    """Import taxpayer profile into the active business registry from GSTIN."""
    from core.gstin_checker import import_business_from_gstin
    result = import_business_from_gstin(req.gstin)
    if not result.get("valid") and result.get("error"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@app.post("/api/ledger/upload")
async def api_upload_ledger(file: UploadFile = File(...)):
    """Upload and analyze vendor purchase ledger CSV for Section 43B(h) disallowance & 3x RBI interest."""
    from core.ledger_analyzer import parse_csv_ledger
    content = await file.read()
    try:
        csv_text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        csv_text = content.decode("latin-1")

    analysis = parse_csv_ledger(csv_text)
    return analysis


@app.get("/api/ledger/sample")
def api_download_sample_ledger():
    """Download a realistic sample vendor ledger CSV template."""
    from core.ledger_analyzer import generate_sample_ledger_csv
    from fastapi.responses import Response
    csv_data = generate_sample_ledger_csv()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sample_vendor_ledger_43bh.csv"}
    )


@app.get("/api/ca/portfolio-summary")
def api_get_ca_portfolio():
    """Retrieve holistic compliance audit scorecard across all client businesses for CAs/Auditors."""
    from core.ca_portfolio import get_ca_portfolio_summary
    return get_ca_portfolio_summary()


if __name__ == "__main__":
    import uvicorn
    print("=" * 70)
    print("Starting SME Compliance & Audit Assistant on http://127.0.0.1:8000")
    print("=" * 70)
    uvicorn.run(app, host="127.0.0.1", port=8000)
