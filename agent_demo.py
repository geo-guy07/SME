"""
Agent Demo — SME Compliance & Registration Automation Assistant
Upgraded to Agentic Compliance Automation System

Features:
- Fixed Regulatory RAG (hybrid Chroma vector + BM25 search)
- Structured compliance check: check_requirements(business_id)
- Reusable compliance workflow engine with state transitions
- Udyam MSME registration automation with Playwright & dry-run mode
- Human-in-the-loop pause for Aadhaar/OTP authorization
- Honest status tracking (no false completion claims)
"""

import os
import json
from rag.regulations import REGULATIONS
from rag.vector_store import VectorStore
from core.business_profile import get_business, SAMPLE_BUSINESSES
from core.rules_engine import check_requirements, evaluate_business
from core.workflow import (
    start_udyam_workflow,
    resume_udyam_workflow,
    ACTIVE_WORKFLOWS,
    WorkflowStatus,
    mask_value,
)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Default active business for demo (ABC Traders, Rahul Sharma, Indore MP)
ACTIVE_BUSINESS_ID = "B005"


# ---- Tools the agent can call ----
def search_regulations(keyword: str):
    """Search official regulatory provisions and thresholds using hybrid retrieval."""
    store = VectorStore()
    results = store.search(query=keyword, top_k=3)
    # Return serializable summary for agent
    return [
        {
            "id": r["id"],
            "title": r["title"],
            "category": r["category"],
            "source": r["source"],
            "text": r["text"],
            "relevance_score": r["score"],
        }
        for r in results
    ]


def query_business_data(business_id: str = ACTIVE_BUSINESS_ID):
    """Look up a business profile by ID from the business database."""
    biz = get_business(business_id)
    return biz.as_dict() if biz else {"error": f"No business found for id {business_id}"}


def check_requirements_tool(business_id: str = ACTIVE_BUSINESS_ID):
    """
    Evaluate all statutory compliance requirements for a business profile.
    Returns structured findings including GST, Udyam MSME classification, Shops & Establishments, PF, ESI.
    """
    return check_requirements(business_id)


def start_udyam_registration(business_id: str = ACTIVE_BUSINESS_ID, dry_run: bool = True):
    """
    Initiate the Udyam MSME registration automation workflow for a business.
    Pre-fills business data, verifies portal structure, and pauses at Aadhaar/OTP authentication.
    """
    biz = get_business(business_id)
    if not biz:
        return {"error": f"No business found for id {business_id}"}

    workflow_id = f"WF-UDYAM-{business_id}"
    result = start_udyam_workflow(
        workflow_id=workflow_id,
        business_data=biz.as_dict(),
        dry_run=dry_run,
        headless=True,
    )
    return result


def resume_udyam_registration(workflow_id: str, otp: str = None, missing_data: dict = None):
    """
    Resume an existing paused Udyam registration workflow with user-provided action (e.g. OTP or missing data).
    """
    if missing_data:
        action = {"data": missing_data}
    elif otp:
        action = {"otp": otp}
    else:
        return {"error": "Must provide either 'otp' or 'missing_data' to resume workflow."}

    return resume_udyam_workflow(workflow_id=workflow_id, user_action=action)


from core.doc_extractor import ingest_document_photo


def upload_and_extract_document(image_path: str, business_id: str = None):
    """
    Ingest a document photo (GST certificate, PAN card, utility bill, tax invoice)
    using Gemini Vision OCR, extract structured compliance details, and persist them
    directly into PostgreSQL.
    """
    return ingest_document_photo(image_path=image_path, business_id=business_id)


TOOLS = {
    "search_regulations": search_regulations,
    "query_business_data": query_business_data,
    "check_requirements": check_requirements_tool,
    "start_udyam_registration": start_udyam_registration,
    "resume_udyam_registration": resume_udyam_registration,
    "upload_and_extract_document": upload_and_extract_document,
}


def run_agent_with_gemini(user_prompt: str):
    """Agent orchestration loop using Gemini's native tool calling."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)
    config = types.GenerateContentConfig(
        tools=[
            search_regulations,
            query_business_data,
            check_requirements_tool,
            start_udyam_registration,
            resume_udyam_registration,
            upload_and_extract_document,
        ],
        temperature=0.2,
    )
    chat = client.chats.create(
        model="gemini-2.5-flash",
        config=config,
    )
    response = chat.send_message(user_prompt)
    return response.text



def run_deterministic_agent_trace(business_id: str = ACTIVE_BUSINESS_ID):
    """
    Deterministic demonstration of the agentic compliance automation lifecycle:
    1. Query business profile
    2. Run structured compliance requirements check
    3. Retrieve grounding regulatory evidence
    4. Automatically trigger and execute Udyam registration workflow
    5. Handle human-in-the-loop pause and resume
    """
    print("=" * 80)
    print("SME COMPLIANCE AGENT — AGENTIC WORKFLOW DEMONSTRATION")
    print("=" * 80)

    # 1. Query business data
    print("\n[Step 1: Business Profile Inspection]")
    biz = query_business_data(business_id)
    print(f"  Business: {biz.get('name')} ({biz.get('business_type')})")
    print(f"  Owner: {biz.get('owner')} | Location: {biz.get('address')}")
    print(f"  Turnover: Rs.{biz.get('turnover_lakh')} Lakhs | Employees: {biz.get('employee_count')}")

    # 2. Check compliance requirements
    print("\n[Step 2: Structured Compliance Audit (check_requirements)]")
    findings_report = check_requirements_tool(business_id)
    print(f"  Total Applicable Registrations: {findings_report['applicable_count']}")
    for f in findings_report["findings"]:
        status = "APPLIES" if f["applies"] else "NOT APPLICABLE"
        wf_tag = f" -> Workflow: {f['workflow_available']}" if f.get("workflow_available") else ""
        print(f"  - [{status:14}] {f['requirement']}{wf_tag}")
        print(f"       Reason: {f['reason']} (Evidence: {f['evidence_id']})")

    # 3. Regulatory RAG Evidence Retrieval
    print("\n[Step 3: Regulatory Evidence RAG (search_regulations)]")
    query = "Udyam registration MSME Micro classification threshold"
    print(f"  Querying Knowledge Base: '{query}'")
    regs = search_regulations(query)
    for r in regs[:2]:
        print(f"  * [{r['id']}] {r['title']} (Score: {r['relevance_score']})")
        print(f"    Source: {r['source']}")
        print(f"    Snippet: {r['text'][:110]}...")

    # 4. Initiate Udyam Registration Automation
    print("\n[Step 4: Executing Udyam Registration Workflow]")
    workflow_id = f"WF-UDYAM-{business_id}"
    print(f"  Starting workflow '{workflow_id}'...")
    wf_res = start_udyam_registration(business_id=business_id, dry_run=True)
    
    print(f"\n  Workflow State: {wf_res['status']}")
    if wf_res.get("pending_user_action"):
        action = wf_res["pending_user_action"]
        print(f"  [HUMAN-IN-THE-LOOP REQUIRED]")
        print(f"  Action Type: {action.get('action_type')}")
        print(f"  Prompt: {action.get('prompt')}")

        # Case A: Missing Aadhaar
        if action.get("action_type") == "PROVIDE_MISSING_DATA":
            print("\n  [User Action: Providing owner Aadhaar number...]")
            resume_res = resume_udyam_registration(workflow_id, missing_data={"aadhaar": "987654321098"})
            print(f"  Workflow State: {resume_res['status']}")
            action = resume_res.get("pending_user_action")
            print(f"  Next Prompt: {action.get('prompt') if action else 'None'}")

        # Case B: Aadhaar OTP verification
        if action and action.get("action_type") == "ENTER_AADHAAR_OTP":
            print("\n  [User Action: Entering Aadhaar OTP received on registered mobile (******3210)...]")
            otp_res = resume_udyam_registration(workflow_id, otp="654321")
            print(f"\n  Resumed Workflow State: {otp_res['status']}")
            print(f"  Progress Result:")
            print(json.dumps(otp_res.get("result"), indent=4))

    print("\n" + "=" * 80)
    print("DEMO COMPLETE — WORKFLOW TRACKED TRUTHFULLY WITHOUT FALSE COMPLETION CLAIM")
    print("=" * 80)


def main():
    question = (
        "What registrations do I need for business ID 'B005' (ABC Traders in Indore with turnover of 45 lakhs)? "
        "Please check the requirements, cite the regulatory evidence, and initiate my Udyam registration workflow."
    )

    if GEMINI_API_KEY:
        print("[Running live Gemini Agent with Function Calling]\n")
        try:
            answer = run_agent_with_gemini(question)
            print(answer)
        except Exception as e:
            print(f"Live Gemini agent error: {e}. Falling back to deterministic trace...\n")
            run_deterministic_agent_trace()
    else:
        print("[No GEMINI_API_KEY provided — Running complete deterministic agent trace]\n")
        run_deterministic_agent_trace()


if __name__ == "__main__":
    main()