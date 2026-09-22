"""
Rules Engine — SME Compliance Assistant

Evaluates a BusinessProfile against structured compliance rules and returns
Finding objects: requirement, whether it applies, the reason, and the
regulation ID used as evidence (for cross-referencing with regulations.py).

This replaces the inline if/else logic that was previously stuffed inside
check_requirement() in agent_demo.py.
"""

from dataclasses import dataclass
from typing import List
from core.business_profile import BusinessProfile


@dataclass
class Finding:
    requirement: str
    applies: bool
    reason: str
    evidence_id: str  # regulation ID from regulations.py


def _gst_threshold(business: BusinessProfile) -> float:
    """Returns applicable GST turnover threshold in Rs. lakh."""
    if business.business_type == "goods":
        return 20 if business.special_category_state else 40
    return 10 if business.special_category_state else 20


def check_gst_registration(business: BusinessProfile) -> Finding:
    threshold = _gst_threshold(business)
    applies = business.turnover_lakh >= threshold
    reg_id = "GST-001" if business.business_type == "goods" else "GST-002"
    return Finding(
        requirement="GST Registration",
        applies=applies,
        reason=(
            f"Turnover Rs.{business.turnover_lakh}L vs Rs.{threshold}L threshold "
            f"for {business.business_type}"
            + (" (special category state)" if business.special_category_state else "")
        ),
        evidence_id=reg_id,
    )


def check_composition_scheme(business: BusinessProfile) -> Finding:
    threshold = 75 if business.special_category_state else 150
    applies = business.turnover_lakh <= threshold
    return Finding(
        requirement="Composition Scheme Eligibility",
        applies=applies,
        reason=f"Turnover Rs.{business.turnover_lakh}L vs Rs.{threshold}L eligibility ceiling",
        evidence_id="GST-003",
    )


def check_udyam_classification(business: BusinessProfile) -> Finding:
    """
    Classification thresholds per Ministry of MSME notification, revised
    effective April 2025 (turnover criterion; investment criterion not
    modeled here since BusinessProfile only tracks turnover).
    """
    turnover_crore = business.turnover_lakh / 100
    if turnover_crore <= 5:
        category, reg_id = "Micro", "MSME-001"
    elif turnover_crore <= 50:
        category, reg_id = "Small", "MSME-002"
    elif turnover_crore <= 250:
        category, reg_id = "Medium", "MSME-003"
    else:
        category, reg_id = "Not MSME-eligible", "MSME-003"
    return Finding(
        requirement=f"Udyam Registration — {category} classification",
        applies=category != "Not MSME-eligible",
        reason=f"Turnover Rs.{turnover_crore:.2f}cr places business in the {category} MSME band",
        evidence_id=reg_id,
    )


def check_shops_establishments(business: BusinessProfile) -> Finding:
    applies = business.employee_count >= 1
    return Finding(
        requirement="Shops & Establishments Registration",
        applies=applies,
        reason=f"Employs {business.employee_count} person(s); registration required once >=1",
        evidence_id="SE-001",
    )


def check_pf_registration(business: BusinessProfile) -> Finding:
    applies = business.employee_count >= 20
    return Finding(
        requirement="PF (Provident Fund) Registration",
        applies=applies,
        reason=f"Employs {business.employee_count}; PF required only at >=20 employees",
        evidence_id="LAB-001",
    )


def check_esi_registration(business: BusinessProfile) -> Finding:
    applies = business.employee_count >= 10
    return Finding(
        requirement="ESI (Employee State Insurance) Registration",
        applies=applies,
        reason=f"Employs {business.employee_count}; ESI required only at >=10 employees",
        evidence_id="LAB-002",
    )


ALL_RULES = [
    check_gst_registration,
    check_composition_scheme,
    check_udyam_classification,
    check_shops_establishments,
    check_pf_registration,
    check_esi_registration,
]


def evaluate_business(business: BusinessProfile) -> List[Finding]:
    """Run every rule against a business profile and return all findings."""
    return [rule(business) for rule in ALL_RULES]


def check_requirements(business_id: str) -> dict:
    """
    Evaluate all compliance rules for a business by ID and return structured findings.
    Supplements/replaces single-requirement checks with a full compliance audit.
    """
    from core.business_profile import get_business
    biz = get_business(business_id)
    if not biz:
        return {
            "business_id": business_id,
            "error": f"No business found for id {business_id}",
            "findings": []
        }

    raw_findings = evaluate_business(biz)
    findings = []
    for f in raw_findings:
        entry = {
            "requirement": f.requirement,
            "applies": f.applies,
            "reason": f.reason,
            "evidence_id": f.evidence_id,
        }
        if "udyam" in f.requirement.lower() and f.applies:
            entry["workflow_available"] = "udyam_registration"
        findings.append(entry)

    return {
        "business_id": biz.business_id,
        "business_name": biz.name,
        "applicable_count": sum(1 for f in findings if f["applies"]),
        "findings": findings,
    }


if __name__ == "__main__":
    from business_profile import SAMPLE_BUSINESSES

    for biz in SAMPLE_BUSINESSES:
        print("=" * 70)
        print(f"{biz.name}  (turnover=Rs.{biz.turnover_lakh}L, employees={biz.employee_count}, state={biz.state})")
        print("-" * 70)
        for finding in evaluate_business(biz):
            status = "APPLIES" if finding.applies else "not applicable"
            print(f"  [{status:14}] {finding.requirement}")
            print(f"                   Reason: {finding.reason}")
            print(f"                   Evidence: {finding.evidence_id}")
        print()