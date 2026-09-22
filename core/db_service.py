"""
Database Service Layer — SME Compliance Assistant
Encapsulates all PostgreSQL data operations for users, businesses, document uploads,
audit findings, and workflow records.
"""

import json
import logging
from typing import Optional, List, Dict, Any

from core.database import (
    get_engine,
    get_session,
    Base,
    User,
    Business,
    DocumentUpload,
    AuditFinding,
    WorkflowRecord,
    DEFAULT_DATABASE_URL,
)
from core.workflow import mask_value

logger = logging.getLogger("sme.db_service")


# ==========================================
# Schema Initialization & Seeding
# ==========================================

def init_db() -> bool:
    """Initialize all PostgreSQL tables defined in SQLAlchemy Base."""
    try:
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        print("  [PostgreSQL] Database tables initialized successfully.")
        return True
    except Exception as e:
        print(f"  [PostgreSQL] Table initialization failed: {e}")
        return False


def seed_default_data() -> bool:
    """
    Seed initial sample businesses (B001 to B005) and default user accounts
    if the database is currently empty.
    """
    from core.business_profile import SAMPLE_BUSINESSES

    session = None
    try:
        session = get_session()
        # 1. Seed default user if not exists
        admin_user = session.query(User).filter_by(email="rahul.sharma@example.com").first()
        if not admin_user:
            admin_user = User(
                name="Rahul Sharma",
                email="rahul.sharma@example.com",
                phone="9876543210",
                role="owner",
            )
            session.add(admin_user)
            session.flush()

        # 2. Seed businesses
        for sample in SAMPLE_BUSINESSES:
            existing = session.query(Business).filter_by(business_id=sample.business_id).first()
            if not existing:
                masked_aadhaar = mask_value(sample.aadhaar, "aadhaar") if sample.aadhaar else None
                b = Business(
                    business_id=sample.business_id,
                    user_id=admin_user.user_id if sample.business_id == "B005" else None,
                    name=sample.name,
                    business_type=sample.business_type,
                    turnover_lakh=sample.turnover_lakh,
                    employee_count=sample.employee_count,
                    state=sample.state,
                    registration_status=sample.registration_status,
                    special_category_state=sample.special_category_state,
                    owner=sample.owner,
                    pan=sample.pan,
                    gstin=sample.gstin,
                    mobile=sample.mobile,
                    email=sample.email,
                    address=sample.address,
                    activity=sample.activity,
                    aadhaar_masked=masked_aadhaar,
                )
                session.add(b)
        session.commit()
        print(f"  [PostgreSQL] Seeded default businesses and users successfully.")
        return True
    except Exception as e:
        if session:
            session.rollback()
        print(f"  [PostgreSQL] Seeding warning: {e}")
        return False
    finally:
        if session:
            session.close()


# ==========================================
# User Repository
# ==========================================

def create_user(name: str, email: str, phone: Optional[str] = None, role: str = "owner") -> Dict[str, Any]:
    """Register or return an existing user."""
    session = get_session()
    try:
        user = session.query(User).filter_by(email=email.strip().lower()).first()
        if not user:
            user = User(
                name=name.strip(),
                email=email.strip().lower(),
                phone=phone.strip() if phone else None,
                role=role,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
        return user.as_dict()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve user by ID."""
    session = get_session()
    try:
        user = session.query(User).filter_by(user_id=user_id).first()
        return user.as_dict() if user else None
    finally:
        session.close()


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Retrieve user by email."""
    session = get_session()
    try:
        user = session.query(User).filter_by(email=email.strip().lower()).first()
        return user.as_dict() if user else None
    finally:
        session.close()


def list_users() -> List[Dict[str, Any]]:
    """List all registered users."""
    session = get_session()
    try:
        users = session.query(User).order_by(User.user_id).all()
        return [u.as_dict() for u in users]
    finally:
        session.close()


# ==========================================
# Business Repository
# ==========================================

def save_business_to_db(data: Dict[str, Any], user_id: Optional[int] = None) -> Dict[str, Any]:
    """Create or update a business record in PostgreSQL."""
    session = get_session()
    try:
        biz_id = data.get("business_id")
        if not biz_id:
            # Generate ID if missing
            count = session.query(Business).count() + 1
            biz_id = f"B{count:03d}"
            data["business_id"] = biz_id

        biz = session.query(Business).filter_by(business_id=biz_id).first()
        if not biz:
            biz = Business(business_id=biz_id)
            session.add(biz)

        # Update attributes
        if user_id is not None:
            biz.user_id = user_id
        if "name" in data:
            biz.name = data["name"]
        if "business_name" in data and not biz.name:
            biz.name = data["business_name"]
        if "business_type" in data:
            biz.business_type = data["business_type"]
        if "turnover_lakh" in data and data["turnover_lakh"] is not None:
            biz.turnover_lakh = float(data["turnover_lakh"])
        if "employee_count" in data and data["employee_count"] is not None:
            biz.employee_count = int(data["employee_count"])
        if "state" in data:
            biz.state = data["state"]
        if "registration_status" in data:
            biz.registration_status = data["registration_status"]
        if "special_category_state" in data:
            biz.special_category_state = bool(data["special_category_state"])
        if "owner" in data:
            biz.owner = data["owner"]
        if "pan" in data:
            biz.pan = data["pan"]
        if "gstin" in data:
            biz.gstin = data["gstin"]
        if "mobile" in data:
            biz.mobile = data["mobile"]
        if "email" in data:
            biz.email = data["email"]
        if "address" in data:
            biz.address = data["address"]
        if "activity" in data:
            biz.activity = data["activity"]
        if "aadhaar" in data:
            biz.aadhaar_masked = mask_value(data["aadhaar"], "aadhaar")

        session.commit()
        session.refresh(biz)
        return biz.as_dict()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_business_from_db(business_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a business from PostgreSQL by ID."""
    session = get_session()
    try:
        biz = session.query(Business).filter_by(business_id=business_id).first()
        return biz.as_dict() if biz else None
    except Exception as e:
        logger.warning(f"Error reading business {business_id} from DB: {e}")
        return None
    finally:
        session.close()


def list_businesses_from_db() -> List[Dict[str, Any]]:
    """List all businesses in PostgreSQL."""
    session = get_session()
    try:
        businesses = session.query(Business).order_by(Business.business_id).all()
        return [b.as_dict() for b in businesses]
    except Exception as e:
        logger.warning(f"Error listing businesses: {e}")
        return []
    finally:
        session.close()


# ==========================================
# Document Upload Repository
# ==========================================

def save_document_upload(
    file_name: str,
    file_path: str,
    document_type: str,
    extracted_data: Dict[str, Any],
    business_id: Optional[str] = None,
    user_id: Optional[int] = None,
    confidence_score: float = 1.0,
) -> Dict[str, Any]:
    """Record an uploaded and OCR-analyzed document in PostgreSQL."""
    session = get_session()
    try:
        doc = DocumentUpload(
            business_id=business_id,
            user_id=user_id,
            file_name=file_name,
            file_path=file_path,
            document_type=document_type,
            extracted_data=json.dumps(extracted_data),
            confidence_score=confidence_score,
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)
        return doc.as_dict()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def list_document_uploads(business_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve uploaded documents, optionally filtered by business_id."""
    session = get_session()
    try:
        query = session.query(DocumentUpload)
        if business_id:
            query = query.filter_by(business_id=business_id)
        docs = query.order_by(DocumentUpload.upload_id.desc()).all()
        return [d.as_dict() for d in docs]
    finally:
        session.close()


# ==========================================
# Audit Findings Repository
# ==========================================

def record_audit_findings(business_id: str, findings: List[Any]) -> bool:
    """Store rules engine findings for a business in PostgreSQL."""
    session = get_session()
    try:
        # Clear previous findings for this business to avoid duplicates
        session.query(AuditFinding).filter_by(business_id=business_id).delete()
        for f in findings:
            finding_obj = AuditFinding(
                business_id=business_id,
                requirement=f.requirement if hasattr(f, "requirement") else f.get("requirement"),
                applies=f.applies if hasattr(f, "applies") else f.get("applies"),
                reason=f.reason if hasattr(f, "reason") else f.get("reason"),
                evidence_id=f.evidence_id if hasattr(f, "evidence_id") else f.get("evidence_id"),
            )
            session.add(finding_obj)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        logger.warning(f"Failed to record findings in DB: {e}")
        return False
    finally:
        session.close()


def get_findings_from_db(business_id: str) -> List[Dict[str, Any]]:
    """Get stored findings for a business."""
    session = get_session()
    try:
        findings = session.query(AuditFinding).filter_by(business_id=business_id).all()
        return [f.as_dict() for f in findings]
    finally:
        session.close()


# ==========================================
# Workflow Record Repository
# ==========================================

def record_workflow_state(
    workflow_id: str,
    business_id: str,
    workflow_name: str,
    status: str,
    stage: Optional[str] = None,
    steps: Optional[List[Dict[str, Any]]] = None,
) -> bool:
    """Persist workflow state transitions and audit logs."""
    session = get_session()
    try:
        rec = session.query(WorkflowRecord).filter_by(workflow_id=workflow_id).first()
        if not rec:
            rec = WorkflowRecord(
                workflow_id=workflow_id,
                business_id=business_id,
                workflow_name=workflow_name,
                status=status,
                stage=stage,
                steps_log=json.dumps(steps or []),
            )
            session.add(rec)
        else:
            rec.status = status
            rec.stage = stage
            if steps:
                rec.steps_log = json.dumps(steps)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        logger.warning(f"Failed to record workflow state in DB: {e}")
        return False
    finally:
        session.close()
