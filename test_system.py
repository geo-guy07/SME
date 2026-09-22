"""
System Verification Tests — SME Compliance Automation System
Verifies:
1. RAG retrieval (ensures search_regulations does not return empty results)
2. Rules engine check_requirements(business_id) returns structured JSON
3. Reusable workflow state transitions and sensitive data masking
4. Udyam MSME registration workflow dry-run lifecycle & human pause/resume
5. Safety check: never claims registration is completed prematurely
"""

import unittest
from core.business_profile import get_business, BusinessProfile
from core.rules_engine import check_requirements
from rag.vector_store import VectorStore
from core.workflow import (
    UdyamWorkflow,
    WorkflowStatus,
    mask_value,
    mask_dict,
    start_udyam_workflow,
    resume_udyam_workflow,
)


class TestSMEComplianceSystem(unittest.TestCase):

    def test_rag_search_regulations_not_empty(self):
        """Fix verification: search_regulations must not return empty results."""
        store = VectorStore()
        results = store.search("GST turnover threshold goods", top_k=2)
        self.assertGreater(len(results), 0, "RAG search must return at least one result")
        self.assertIn("id", results[0])
        self.assertIn("title", results[0])
        self.assertTrue(results[0]["id"].startswith("GST"), "Top result should be a GST regulation")
        print("  [PASS] test_rag_search_regulations_not_empty: Retrieved", results[0]["id"], "-", results[0]["title"])

    def test_check_requirements_structured_json(self):
        """Verification of check_requirements(business_id) structured JSON output."""
        res = check_requirements("B005")
        self.assertEqual(res["business_id"], "B005")
        self.assertEqual(res["business_name"], "ABC Traders")
        self.assertIsInstance(res["findings"], list)
        self.assertGreaterEqual(len(res["findings"]), 5)

        # Check that Udyam finding exists and indicates workflow availability
        udyam_finding = next((f for f in res["findings"] if "udyam" in f["requirement"].lower()), None)
        self.assertIsNotNone(udyam_finding)
        self.assertTrue(udyam_finding["applies"])
        self.assertEqual(udyam_finding.get("workflow_available"), "udyam_registration")
        print("  [PASS] test_check_requirements_structured_json: Found", len(res["findings"]), "rules, Udyam eligible.")

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


if __name__ == "__main__":
    unittest.main()
