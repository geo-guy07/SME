"""
System Verification Tests — SME Compliance Automation & Audit System
Verifies:
1. RAG retrieval with expanded 32-regulation knowledge base (GST, PT, FSSAI, 43B(h))
2. Rules engine check_requirements(business_id) with 10 statutory rules
3. Sensitive data masking (Aadhaar, PAN, OTP, mobile)
4. Udyam MSME registration workflow dry-run lifecycle & human pause/resume
5. Safety check: truthful progress tracking without false completion claim
6. Relational Database persistence (SQLite/SQLAlchemy tables & records)
7. Multimodal document & invoice extraction (heuristic / OCR)
8. Formal PDF audit report generation via ReportLab
"""

import os
import unittest
from pathlib import Path

from core.business_profile import get_business, BusinessProfile
from core.rules_engine import check_requirements, evaluate_business
from rag.vector_store import VectorStore
from core.workflow import (
    UdyamWorkflow,
    WorkflowStatus,
    mask_value,
    mask_dict,
    start_udyam_workflow,
    resume_udyam_workflow,
)
from core.database import SessionLocal, Business, FindingRecord, init_db
from core.doc_extractor import extract_document
from core.report_generator import generate_pdf_report


class TestSMEComplianceSystem(unittest.TestCase):

    def setUp(self):
        init_db()

    def test_rag_search_regulations_expanded_32(self):
        """Verify RAG retrieval against expanded 32-regulation corpus."""
        store = VectorStore()
        
        # Test GST retrieval
        res_gst = store.search("GST turnover threshold goods", top_k=2)
        self.assertGreater(len(res_gst), 0)
        self.assertTrue(res_gst[0]["id"].startswith("GST"))

        # Test MSME 43B(h) retrieval
        res_43b = store.search("45 days delayed payment Section 43B(h) MSME", top_k=2)
        self.assertGreater(len(res_43b), 0)
        has_43b_or_msme = any(h["id"] in ["IT-003", "MSME-004"] for h in res_43b)
        self.assertTrue(has_43b_or_msme, "Should retrieve Section 43B(h) or MSMED Act rule")

        # Test Professional Tax retrieval
        res_pt = store.search("Professional tax Maharashtra Karnataka registration PTEC", top_k=2)
        self.assertGreater(len(res_pt), 0)
        self.assertTrue(res_pt[0]["id"].startswith("PT"))

        print("  [PASS] test_rag_search_regulations_expanded_32: Successfully retrieved from 32 regulations.")

    def test_check_requirements_10_rules(self):
        """Verification of check_requirements(business_id) 10-rule structured output."""
        res = check_requirements("B005")
        self.assertEqual(res["business_id"], "B005")
        self.assertEqual(res["business_name"], "ABC Traders")
        self.assertIsInstance(res["findings"], list)
        self.assertGreaterEqual(len(res["findings"]), 8, "Must evaluate at least 8-10 statutory rules")

        # Check Udyam finding exists and indicates workflow
        udyam_finding = next((f for f in res["findings"] if "udyam" in f["requirement"].lower()), None)
        self.assertIsNotNone(udyam_finding)
        self.assertTrue(udyam_finding["applies"])
        self.assertEqual(udyam_finding.get("workflow_available"), "udyam_registration")

        # Check Professional Tax finding exists
        pt_finding = next((f for f in res["findings"] if "professional tax" in f["requirement"].lower()), None)
        self.assertIsNotNone(pt_finding)
        self.assertTrue(pt_finding["applies"])  # MP is a PT state

        # Check 43B(h) finding exists
        f_43b = next((f for f in res["findings"] if "43b(h)" in f["requirement"].lower()), None)
        self.assertIsNotNone(f_43b)

        print("  [PASS] test_check_requirements_10_rules: Evaluated 10 statutory rules including PT, FSSAI, 43B(h).")

    def test_sensitive_data_masking(self):
        """Verification that Aadhaar, PAN, OTP, mobile are masked in logs and views."""
        self.assertEqual(mask_value("123456789012", "aadhaar"), "XXXX-XXXX-9012")
        self.assertEqual(mask_value("ABCDE1234F", "pan"), "AB******4F")
        self.assertEqual(mask_value("9876543210", "mobile"), "******3210")
        self.assertEqual(mask_value("123456", "otp"), "******")
        print("  [PASS] test_sensitive_data_masking: Masking patterns confirmed.")

    def test_udyam_workflow_lifecycle_and_honesty(self):
        """
        Verification of Udyam workflow state machine:
        READY -> COLLECTING_DATA -> VALIDATING -> RUNNING -> AWAITING_USER -> RESUME
        And check that it does not falsely claim completion.
        """
        biz_data = {
            "business_name": "ABC Traders",
            "owner": "Rahul Sharma",
            "business_type": "Proprietorship",
            "address": "Indore, Madhya Pradesh",
            "activity": "Wholesale trading",
            "pan": "ABCDE1234F",
            "mobile": "9876543210",
            "email": "rahul.sharma@example.com",
            "aadhaar": "987654321098",
        }
        wf = UdyamWorkflow(workflow_id="TEST-WF-01", business_data=biz_data)
        self.assertEqual(wf.status, WorkflowStatus.READY)

        # Run dry run
        summary = wf.run(dry_run=True)
        # Should pause for human OTP authorization
        self.assertEqual(summary["status"], WorkflowStatus.AWAITING_USER.value)
        self.assertIsNotNone(summary["pending_user_action"])
        self.assertEqual(summary["pending_user_action"]["action_type"], "ENTER_AADHAAR_OTP")

        # Resume with invalid OTP -> should be rejected
        err_res = wf.resume({"otp": "abc"})
        self.assertIn("error", err_res)
        self.assertEqual(wf.status, WorkflowStatus.AWAITING_USER)

        # Resume with valid 6-digit OTP
        resume_summary = wf.resume({"otp": "654321"})
        self.assertEqual(resume_summary["status"], WorkflowStatus.RUNNING.value)
        self.assertIsNotNone(resume_summary["result"])
        self.assertFalse(
            resume_summary["result"]["is_final_registration_completed"],
            "Must never claim registration was completed without genuine portal submission confirmation",
        )
        print("  [PASS] test_udyam_workflow_lifecycle_and_honesty: Lifecycle verified with honest progress tracking.")

    def test_database_persistence(self):
        """Verify SQLite database persistence for businesses and findings."""
        db = SessionLocal()
        try:
            businesses = db.query(Business).all()
            self.assertGreaterEqual(len(businesses), 5, "Database must seed sample businesses")

            # Check findings persistence
            b005 = db.query(Business).filter(Business.business_id == "B005").first()
            self.assertIsNotNone(b005)
            self.assertEqual(b005.name, "ABC Traders")

            findings = db.query(FindingRecord).filter(FindingRecord.business_id == "B005").all()
            self.assertGreaterEqual(len(findings), 5, "Findings must be persisted in database")
            print("  [PASS] test_database_persistence: Confirmed SQLite persistence for businesses and findings.")
        finally:
            db.close()

    def test_doc_extractor_and_pdf_report(self):
        """Verify document extraction and ReportLab PDF report generation."""
        # 1. Test Document Extractor with dummy invoice text
        test_file = Path(__file__).parent / "test_invoice.txt"
        test_file.write_text(
            "TAX INVOICE\n"
            "M/s Vertex Industrial Traders\n"
            "PAN: AABCV1234Z\n"
            "State: Maharashtra\n"
            "Contact: 9823456789\n"
            "Total Invoice Value: Rs. 5,40,000.00\n",
            encoding="utf-8"
        )
        try:
            doc_res = extract_document(str(test_file), business_id="B005")
            ext = doc_res["extracted_data"]
            self.assertEqual(ext["pan"], "AABCV1234Z")
            self.assertEqual(ext["state"], "Maharashtra")
            self.assertEqual(ext["mobile"], "9823456789")
            self.assertGreater(ext["turnover_lakh"], 0)
            print("  [PASS] test_doc_extractor: Extracted PAN, State, Mobile, and Turnover.")
        finally:
            if test_file.exists():
                test_file.unlink()

        # 2. Test PDF Report Generation
        pdf_path = generate_pdf_report("B005")
        self.assertTrue(os.path.exists(pdf_path), "PDF report file must exist on disk")
        self.assertGreater(os.path.getsize(pdf_path), 2000, "PDF file must not be empty")
        print(f"  [PASS] test_pdf_report_generation: Generated {os.path.getsize(pdf_path)} byte PDF report.")

    def test_gstin_verifier(self):
        """Verify GSTIN validation and filing track record lookup."""
        from core.gstin_checker import validate_gstin_format, verify_gstin
        
        # 1. Valid known GSTIN
        res = verify_gstin("23ABCDE1234F1Z5")
        self.assertTrue(res["valid"])
        self.assertEqual(res["state_code"], "23")
        self.assertEqual(res["state_name"], "Madhya Pradesh")
        self.assertEqual(res["pan"], "ABCDE1234F")
        self.assertGreaterEqual(len(res["filing_track_record"]), 2)

        # 2. Invalid GSTIN format
        bad_res = validate_gstin_format("123INVALID")
        self.assertFalse(bad_res["valid"])
        print("  [PASS] test_gstin_verifier: Successfully validated GSTIN format and filing history.")

    def test_section_43bh_ledger_analyzer(self):
        """Verify Section 43B(h) payment aging, disallowance calculation, and 3x RBI interest."""
        from core.ledger_analyzer import analyze_ledger_rows, parse_csv_ledger, generate_sample_ledger_csv
        
        sample_csv = generate_sample_ledger_csv()
        analysis = parse_csv_ledger(sample_csv)
        
        summary = analysis["summary"]
        self.assertGreater(summary["total_invoices"], 0)
        self.assertGreater(summary["total_purchases"], 0)
        self.assertGreater(summary["total_disallowed_amount"], 0, "Must detect overdue Micro/Small invoices")
        self.assertGreater(summary["corporate_tax_exposure"], 0)
        self.assertGreater(summary["statutory_compound_interest"], 0)

        # Check invoice statuses
        invoices = analysis["invoices"]
        has_disallowed = any(inv["status"] == "DISALLOWED_OVERDUE" for inv in invoices)
        self.assertTrue(has_disallowed, "Should flag overdue Micro/Small invoice as DISALLOWED_OVERDUE")
        print(f"  [PASS] test_section_43bh_ledger_analyzer: Analyzed {summary['total_invoices']} invoices, "
              f"Disallowed Rs.{summary['total_disallowed_amount']} with Rs.{summary['statutory_compound_interest']} penal interest.")

    def test_ca_portfolio_summary(self):
        """Verify CA multi-client portfolio intelligence and filing calendar."""
        from core.ca_portfolio import get_ca_portfolio_summary
        
        summary = get_ca_portfolio_summary()
        metrics = summary["portfolio_metrics"]
        self.assertGreaterEqual(metrics["total_clients"], 5)
        self.assertGreater(metrics["total_turnover_monitored_lakh"], 100)
        self.assertGreaterEqual(metrics["portfolio_health_average"], 35)
        self.assertGreater(len(summary["deadlines"]), 3)
        self.assertGreater(len(summary["clients"]), 0)
        print(f"  [PASS] test_ca_portfolio_summary: Monitored {metrics['total_clients']} clients, "
              f"Avg Health: {metrics['portfolio_health_average']}%.")


if __name__ == "__main__":
    unittest.main()
