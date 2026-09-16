"""
Database Layer — SME Compliance & Audit Assistant
Relational persistence using SQLite & SQLAlchemy matching the SME Audit ER diagram.
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sme_audit.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Business(Base):
    __tablename__ = "businesses"

    business_id = Column(String(50), primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    type = Column(String(50), default="goods")
    turnover = Column(Float, default=0.0)  # in Lakhs
    employee_count = Column(Integer, default=1)
    state = Column(String(100), default="Madhya Pradesh")
    special_category_state = Column(Boolean, default=False)
    registration_status = Column(String(100), default="ACTIVE")
    owner = Column(String(100), nullable=True)
    activity = Column(String(200), nullable=True)
    address = Column(String(300), nullable=True)
    pan = Column(String(20), nullable=True)
    mobile = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    aadhaar = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="business", cascade="all, delete-orphan")
    findings = relationship("FindingRecord", back_populates="business", cascade="all, delete-orphan")
    uploads = relationship("DocumentUpload", back_populates="business", cascade="all, delete-orphan")
    sessions = relationship("QuerySession", back_populates="business", cascade="all, delete-orphan")
    workflows = relationship("WorkflowRecord", back_populates="business", cascade="all, delete-orphan")

    def as_dict(self) -> Dict[str, Any]:
        return {
            "business_id": self.business_id,
            "name": self.name,
            "business_type": self.type,
            "turnover_lakh": self.turnover,
            "employee_count": self.employee_count,
            "state": self.state,
            "special_category_state": self.special_category_state,
            "registration_status": self.registration_status,
            "owner": self.owner,
            "activity": self.activity,
            "address": self.address,
            "pan": self.pan,
            "mobile": self.mobile,
            "email": self.email,
            "aadhaar": self.aadhaar,
        }


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    role = Column(String(50), default="OWNER")
    business_id = Column(String(50), ForeignKey("businesses.business_id"), nullable=True)

    business = relationship("Business", back_populates="users")


class FindingRecord(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(String(50), ForeignKey("businesses.business_id"), nullable=False, index=True)
    requirement = Column(String(200), nullable=False)
    applies = Column(Boolean, nullable=False)
    reason = Column(Text, nullable=False)
    evidence_id = Column(String(50), nullable=False)
    severity = Column(String(20), default="MEDIUM")
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="findings")

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "business_id": self.business_id,
            "requirement": self.requirement,
            "applies": self.applies,
            "reason": self.reason,
            "evidence_id": self.evidence_id,
            "severity": self.severity,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class QuerySession(Base):
    __tablename__ = "query_sessions"

    session_id = Column(String(100), primary_key=True, index=True)
    business_id = Column(String(50), ForeignKey("businesses.business_id"), nullable=True)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="sessions")
    tool_calls = relationship("ToolCallLog", back_populates="session", cascade="all, delete-orphan")


class ToolCallLog(Base):
    __tablename__ = "tool_call_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), ForeignKey("query_sessions.session_id"), nullable=True, index=True)
    tool_name = Column(String(100), nullable=False)
    arguments_json = Column(Text, nullable=True)
    result_json = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("QuerySession", back_populates="tool_calls")


class DocumentUpload(Base):
    __tablename__ = "document_uploads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(String(50), ForeignKey("businesses.business_id"), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=True)
    file_size_bytes = Column(Integer, default=0)
    extracted_metadata_json = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="uploads")


class WorkflowRecord(Base):
    __tablename__ = "workflow_records"

    workflow_id = Column(String(100), primary_key=True, index=True)
    business_id = Column(String(50), ForeignKey("businesses.business_id"), nullable=True)
    workflow_name = Column(String(100), default="Udyam/MSME Registration")
    status = Column(String(50), default="READY")
    pending_action_json = Column(Text, nullable=True)
    result_json = Column(Text, nullable=True)
    steps_log_json = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    business = relationship("Business", back_populates="workflows")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables and seed sample businesses if not existing."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        from core.business_profile import SAMPLE_BUSINESSES
        for biz in SAMPLE_BUSINESSES:
            existing = db.query(Business).filter(Business.business_id == biz.business_id).first()
            if not existing:
                b = Business(
                    business_id=biz.business_id,
                    name=biz.name,
                    type=biz.business_type,
                    turnover=biz.turnover_lakh,
                    employee_count=biz.employee_count,
                    state=biz.state,
                    special_category_state=biz.special_category_state,
                    owner=biz.owner,
                    activity=biz.activity,
                    address=biz.address,
                    pan=biz.pan,
                    mobile=biz.mobile,
                    email=biz.email,
                    aadhaar=biz.aadhaar,
                )
                db.add(b)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"  [Database] Init seeding note: {e}")
    finally:
        db.close()


def log_tool_call(session_id: str, tool_name: str, args: Any, result: Any):
    """Record an agent tool call into the database."""
    db = SessionLocal()
    try:
        log = ToolCallLog(
            session_id=session_id,
            tool_name=tool_name,
            arguments_json=json.dumps(args, default=str),
            result_json=json.dumps(result, default=str),
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"  [Database] Failed to log tool call: {e}")
    finally:
        db.close()


def persist_findings(business_id: str, findings: List[Dict[str, Any]]):
    """Save compliance findings for a business."""
    db = SessionLocal()
    try:
        # Clear prior findings for fresh audit run
        db.query(FindingRecord).filter(FindingRecord.business_id == business_id).delete()
        for f in findings:
            record = FindingRecord(
                business_id=business_id,
                requirement=f.get("requirement", ""),
                applies=f.get("applies", False),
                reason=f.get("reason", ""),
                evidence_id=f.get("evidence_id", ""),
                severity=f.get("severity", "MEDIUM"),
            )
            db.add(record)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"  [Database] Failed to persist findings: {e}")
    finally:
        db.close()


# Ensure tables are initialized upon module load
init_db()
