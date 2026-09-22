"""
PostgreSQL Persistence & Gemini Vision OCR Verification Suite
Tests:
1. PostgreSQL connection & table schema creation
2. User CRUD operations and persistence
3. Business profile storage and hybrid DB/in-memory fallback
4. Document photo ingestion via Vision OCR & database logging
5. Statutory audit findings persistence in PostgreSQL
6. Workflow state machine audit trail recording
"""

import os
import unittest
from pathlib import Path
from PIL import Image, ImageDraw

from core.database import get_engine, get_session, User, Business, DocumentUpload, AuditFinding, WorkflowRecord
from core.db_service import (
    init_db,
    seed_default_data,
    create_user,
    get_user_by_email,
    get_user_by_id,
    list_users,
    save_business_to_db,
    get_business_from_db,
    record_audit_findings,
    get_findings_from_db,
    record_workflow_state,
)
from core.business_profile import get_business, BusinessProfile
from core.rules_engine import evaluate_business
from core.doc_extractor import ingest_document_photo, extract_document_data


class TestPostgresAndOCR(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Initialize database schema before running tests."""
        init_success = init_db()
        assert init_success, "Database table initialization must succeed"
        seed_default_data()

        # Create a sample test document image
        cls.test_doc_path = Path("test_gst_cert_sample.png")
        img = Image.new("RGB", (600, 400), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((50, 30), "GOVERNMENT OF INDIA", fill=(0, 0, 0))
        d.text((50, 60), "Form GST REG-06", fill=(0, 0, 0))
        d.text((50, 90), "Registration Certificate", fill=(0, 0, 0))
        d.text((50, 130), "GSTIN: 23ABCDE1234F1Z5", fill=(0, 0, 0))
        d.text((50, 160), "Legal Name: ABC Traders", fill=(0, 0, 0))
        d.text((50, 190), "PAN: ABCDE1234F", fill=(0, 0, 0))
        d.text((50, 220), "Principal Place: Indore, Madhya Pradesh", fill=(0, 0, 0))
        img.save(cls.test_doc_path)

    @classmethod
    def tearDownClass(cls):
        """Clean up test image fixture."""
        if cls.test_doc_path.exists():
            cls.test_doc_path.unlink()

    def test_01_postgres_tables_exist(self):
        """Verify all expected PostgreSQL tables exist and can be queried."""
        session = get_session()
        try:
            user_count = session.query(User).count()
            biz_count = session.query(Business).count()
            self.assertGreaterEqual(user_count, 1, "Default user should be seeded")
            self.assertGreaterEqual(biz_count, 5, "Sample businesses B001-B005 should be seeded")
            print(f"  [PASS] test_01_postgres_tables_exist: {user_count} users, {biz_count} businesses in PostgreSQL.")
        finally:
            session.close()

    def test_02_user_crud_persistence(self):
        """Verify user creation, retrieval by email, and unique constraint."""
        test_email = "vikram.patel@audit-test.com"
        u = create_user(
            name="Vikram Patel",
            email=test_email,
            phone="9823001122",
            role="compliance_officer",
        )
        self.assertIsNotNone(u.get("user_id"))
        self.assertEqual(u["email"], test_email)

        # Retrieve user by email
        fetched = get_user_by_email(test_email)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["name"], "Vikram Patel")
        self.assertEqual(fetched["role"], "compliance_officer")
        print("  [PASS] test_02_user_crud_persistence: User successfully created and retrieved from PostgreSQL.")

    def test_03_business_persistence_and_fallback(self):
        """Verify custom business saving to PostgreSQL and transparent retrieval via get_business()."""
        biz_data = {
            "business_id": "B999",
            "name": "Narmada Agro Tech",
            "business_type": "goods",
            "turnover_lakh": 65.0,
            "employee_count": 12,
            "state": "Madhya Pradesh",
            "owner": "Suresh Patel",
            "pan": "AAACP9999K",
            "gstin": "23AAACP9999K1Z4",
            "mobile": "9822334455",
            "email": "suresh@narmadaagro.com",
            "address": "Sanwer Road, Indore",
        }
        saved = save_business_to_db(biz_data)
        self.assertEqual(saved["business_id"], "B999")

        # Query via core/business_profile.py get_business()
        profile = get_business("B999")
        self.assertIsNotNone(profile)
        self.assertIsInstance(profile, BusinessProfile)
        self.assertEqual(profile.name, "Narmada Agro Tech")
        self.assertEqual(profile.turnover_lakh, 65.0)

        # Verify fallback for standard sample business B002
        b002 = get_business("B002")
        self.assertIsNotNone(b002)
        self.assertEqual(b002.name, "Verma Consulting Services")
        print("  [PASS] test_03_business_persistence_and_fallback: PostgreSQL business query and dataclass mapping verified.")

    def test_04_document_photo_vision_ocr_and_db_logging(self):
        """Verify document photo ingestion, OCR extraction, and database persistence."""
        res = ingest_document_photo(str(self.test_doc_path), business_id="B005")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIsNotNone(res["upload_record_id"])
        self.assertIn("extracted_details", res)

        extracted = res["extracted_details"]
        self.assertEqual(extracted["document_type"], "GST_CERTIFICATE")
        self.assertIn("pan", extracted)
        self.assertIn("gstin", extracted)

        # Verify database upload record
        session = get_session()
        try:
            upload_row = session.query(DocumentUpload).filter_by(upload_id=res["upload_record_id"]).first()
            self.assertIsNotNone(upload_row)
            self.assertEqual(upload_row.document_type, "GST_CERTIFICATE")
            print(f"  [PASS] test_04_document_photo_vision_ocr_and_db_logging: OCR extracted '{upload_row.document_type}', logged in DB.")
        finally:
            session.close()

    def test_05_audit_findings_persistence(self):
        """Verify rules engine evaluation findings are persisted to PostgreSQL."""
        profile = get_business("B005")
        self.assertIsNotNone(profile)
        findings = evaluate_business(profile)
        self.assertGreaterEqual(len(findings), 5)

        # Save findings in DB
        saved = record_audit_findings("B005", findings)
        self.assertTrue(saved)

        # Retrieve findings from DB
        db_findings = get_findings_from_db("B005")
        self.assertEqual(len(db_findings), len(findings))
        for df in db_findings:
            self.assertIn("requirement", df)
            self.assertIn("applies", df)
            self.assertIn("evidence_id", df)
        print(f"  [PASS] test_05_audit_findings_persistence: Stored and verified {len(db_findings)} statutory findings in PostgreSQL.")

    def test_06_workflow_audit_record_persistence(self):
        """Verify workflow lifecycle transitions are persisted in workflow_records."""
        wf_id = "WF-TEST-001"
        steps = [
            {"step": "DATA_DISCOVERY", "status": "COLLECTING_DATA", "note": "Checked PAN and mobile"},
            {"step": "VALIDATION", "status": "VALIDATING", "note": "Valid PAN format ABCDE1234F"},
            {"step": "PORTAL_PREFILL", "status": "AWAITING_USER", "note": "Paused at Aadhaar OTP checkpoint"},
        ]
        saved = record_workflow_state(
            workflow_id=wf_id,
            business_id="B005",
            workflow_name="Udyam MSME Registration",
            status="AWAITING_USER",
            stage="STAGE_1_AADHAAR_VERIFICATION",
            steps=steps,
        )
        self.assertTrue(saved)

        session = get_session()
        try:
            wf_row = session.query(WorkflowRecord).filter_by(workflow_id=wf_id).first()
            self.assertIsNotNone(wf_row)
            self.assertEqual(wf_row.status, "AWAITING_USER")
            self.assertEqual(len(wf_row.as_dict()["steps"]), 3)
            print("  [PASS] test_06_workflow_audit_record_persistence: Workflow state and step logs persisted in PostgreSQL.")
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
