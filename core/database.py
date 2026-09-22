"""
Database Connection & ORM Models — SME Compliance Assistant
PostgreSQL persistence layer using SQLAlchemy 2.0.

Tables:
- users: Application users (owners, accountants, compliance officers)
- businesses: SME profile data evaluated by the rules engine
- document_uploads: Photos and documents uploaded by users (GST certs, PAN, invoices)
- findings: Statutory compliance evaluation results generated for a business
- workflow_records: State transitions and audit logs for automated portal workflows
"""

import os
import re
import json
from datetime import datetime
from typing import Optional, Dict, Any, List

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
    Index,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

Base = declarative_base()

# Default PostgreSQL connection settings
DB_USER = os.environ.get("POSTGRES_USER", "postgres")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")
DB_HOST = os.environ.get("POSTGRES_HOST", "localhost")
DB_PORT = os.environ.get("POSTGRES_PORT", "5432")
DB_NAME = os.environ.get("POSTGRES_DB", "sme_audit_db")

DEFAULT_DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def ensure_database_exists(db_name: str = DB_NAME):
    """Ensure that the target PostgreSQL database exists; if not, create it."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname="postgres",
            connect_timeout=3,
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (db_name,))
        exists = cur.fetchone()
        if not exists:
            # Safe SQL identifier creation
            cur.execute(f'CREATE DATABASE "{db_name}";')
            print(f"  [PostgreSQL] Created new database '{db_name}'.")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"  [PostgreSQL] Notice: Could not connect to ensure database '{db_name}' exists: {e}")
        return False


# Global engine and sessionmaker
_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        ensure_database_exists(DB_NAME)
        _engine = create_engine(
            DATABASE_URL,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 3},
        )
    return _engine


def get_session():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal()


# ==========================================
# ORM Models
# ==========================================

class User(Base):
    """Registered application user (business owner, accountant, compliance officer)."""
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    role = Column(String(50), default="owner")  # 'owner', 'accountant', 'compliance_officer', 'ca'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    businesses = relationship("Business", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("DocumentUpload", back_populates="user")

    def as_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Business(Base):
    """SME profile evaluated against statutory compliance thresholds."""
    __tablename__ = "businesses"

    business_id = Column(String(50), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False)
    business_type = Column(String(50), default="goods")  # 'goods' or 'services'
    turnover_lakh = Column(Float, default=0.0)
    employee_count = Column(Integer, default=1)
    state = Column(String(100), default="Madhya Pradesh")
    registration_status = Column(String(100), default="unregistered")
    special_category_state = Column(Boolean, default=False)
    owner = Column(String(200), nullable=True)
    pan = Column(String(20), nullable=True)
    gstin = Column(String(30), nullable=True)
    mobile = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    activity = Column(String(255), nullable=True)
    aadhaar_masked = Column(String(30), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="businesses")
    documents = relationship("DocumentUpload", back_populates="business", cascade="all, delete-orphan")
    findings = relationship("AuditFinding", back_populates="business", cascade="all, delete-orphan")
    workflow_records = relationship("WorkflowRecord", back_populates="business", cascade="all, delete-orphan")

    def as_dict(self) -> Dict[str, Any]:
        return {
            "business_id": self.business_id,
            "user_id": self.user_id,
            "name": self.name,
            "business_type": self.business_type,
            "turnover_lakh": self.turnover_lakh,
            "employee_count": self.employee_count,
            "state": self.state,
            "registration_status": self.registration_status,
            "special_category_state": self.special_category_state,
            "owner": self.owner,
            "pan": self.pan,
            "gstin": self.gstin,
            "mobile": self.mobile,
            "email": self.email,
            "address": self.address,
            "activity": self.activity,
            "aadhaar": self.aadhaar_masked,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DocumentUpload(Base):
    """Document or photo uploaded by the user, analyzed via Gemini Vision OCR."""
    __tablename__ = "document_uploads"

    upload_id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(String(50), ForeignKey("businesses.business_id", ondelete="CASCADE"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    document_type = Column(String(100), default="UNKNOWN")  # GST_CERTIFICATE, PAN_CARD, INVOICE, UTILITY_BILL
    extracted_data = Column(Text, nullable=True)  # JSON string of OCR-extracted fields
    confidence_score = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    business = relationship("Business", back_populates="documents")
    user = relationship("User", back_populates="documents")

    def as_dict(self) -> Dict[str, Any]:
        extracted = {}
        if self.extracted_data:
            try:
                extracted = json.loads(self.extracted_data)
            except Exception:
                extracted = {"raw": self.extracted_data}
        return {
            "upload_id": self.upload_id,
            "business_id": self.business_id,
            "user_id": self.user_id,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "document_type": self.document_type,
            "extracted_data": extracted,
            "confidence_score": self.confidence_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AuditFinding(Base):
    """Compliance finding generated by the statutory rules engine."""
    __tablename__ = "findings"

    finding_id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(String(50), ForeignKey("businesses.business_id", ondelete="CASCADE"), nullable=False)
    requirement = Column(String(200), nullable=False)
    applies = Column(Boolean, nullable=False)
    reason = Column(Text, nullable=False)
    evidence_id = Column(String(50), nullable=False)  # e.g., GST-001, MSME-001
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    business = relationship("Business", back_populates="findings")

    def as_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "business_id": self.business_id,
            "requirement": self.requirement,
            "applies": self.applies,
            "reason": self.reason,
            "evidence_id": self.evidence_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class WorkflowRecord(Base):
    """State machine transitions and execution records for compliance workflows."""
    __tablename__ = "workflow_records"

    workflow_id = Column(String(100), primary_key=True)
    business_id = Column(String(50), ForeignKey("businesses.business_id", ondelete="CASCADE"), nullable=False)
    workflow_name = Column(String(200), nullable=False)
    status = Column(String(50), nullable=False)  # READY, RUNNING, AWAITING_USER, COMPLETED, FAILED
    stage = Column(String(100), nullable=True)
    steps_log = Column(Text, nullable=True)  # JSON array of step details
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    business = relationship("Business", back_populates="workflow_records")

    def as_dict(self) -> Dict[str, Any]:
        steps = []
        if self.steps_log:
            try:
                steps = json.loads(self.steps_log)
            except Exception:
                steps = []
        return {
            "workflow_id": self.workflow_id,
            "business_id": self.business_id,
            "workflow_name": self.workflow_name,
            "status": self.status,
            "stage": self.stage,
            "steps": steps,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
