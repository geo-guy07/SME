"""
Rules Engine — SME Compliance & Audit Assistant

Evaluates a BusinessProfile against structured statutory compliance rules and returns
Finding objects: requirement, whether it applies, the reason, and the
regulation ID used as evidence (for cross-referencing with regulations.py).
"""

from dataclasses import dataclass
from typing import List, Optional
try:
    from core.business_profile import BusinessProfile
except ImportError:
    from business_profile import BusinessProfile


@dataclass
class Finding:
    requirement: str
    applies: bool
    reason: str
    evidence_id: str  # regulation ID from regulations.py
    severity: str = "MEDIUM"  # HIGH, MEDIUM, LOW, ADVISORY


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
        severity="HIGH" if applies else "LOW",
    )


def check_composition_scheme(business: BusinessProfile) -> Finding:
    threshold = 75 if business.special_category_state else 150
    applies = business.turnover_lakh <= threshold
    return Finding(
        requirement="Composition Scheme Eligibility",
        applies=applies,
        reason=f"Turnover Rs.{business.turnover_lakh}L vs Rs.{threshold}L eligibility ceiling",
        evidence_id="GST-003",
        severity="MEDIUM" if applies else "LOW",
    )


def check_udyam_classification(business: BusinessProfile) -> Finding:
    """
    Classification thresholds per Ministry of MSME notification, revised
    composite criteria (turnover criterion).
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
        severity="HIGH" if category != "Not MSME-eligible" else "LOW",
    )


def check_shops_establishments(business: BusinessProfile) -> Finding:
    applies = business.employee_count >= 1
    return Finding(
        requirement="Shops & Establishments Registration",
        applies=applies,
        reason=f"Employs {business.employee_count} person(s); registration required once >=1 in commercial premises",
        evidence_id="SE-001",
        severity="HIGH" if applies else "LOW",
    )


def check_pf_registration(business: BusinessProfile) -> Finding:
    applies = business.employee_count >= 20
    return Finding(
        requirement="PF (Provident Fund) Registration",
        applies=applies,
        reason=f"Employs {business.employee_count}; mandatory PF required at >=20 employees",
        evidence_id="LAB-001",
        severity="HIGH" if applies else "LOW",
    )


def check_esi_registration(business: BusinessProfile) -> Finding:
    applies = business.employee_count >= 10
    return Finding(
        requirement="ESI (Employee State Insurance) Registration",
        applies=applies,
        reason=f"Employs {business.employee_count}; ESI registration required at >=10 employees",
        evidence_id="LAB-002",
        severity="HIGH" if applies else "LOW",
    )


def check_professional_tax(business: BusinessProfile) -> Finding:
    """State-specific Professional Tax (PT) evaluation."""
    state = (business.state or "").lower().strip()
    pt_states = {
        "maharashtra": "PT-001",
        "karnataka": "PT-002",
        "west bengal": "PT-003",
        "madhya pradesh": "PT-003",
        "gujarat": "PT-003",
        "telangana": "PT-003",
        "andhra pradesh": "PT-003",
        "tamil nadu": "PT-003",
    }
    
    applies = any(st in state for st in pt_states)
    reg_id = "PT-001" if "maharashtra" in state else ("PT-002" if "karnataka" in state else "PT-003")
    
    if applies:
        reason = f"Operating in {business.state}; liable for Professional Tax (Entity enrollment & salary deduction if employing staff)"
    else:
        reason = f"State {business.state or 'Not specified'} has no mandatory Professional Tax or not in notified slab"

    return Finding(
        requirement="Professional Tax (PT) Registration",
        applies=applies,
        reason=reason,
        evidence_id=reg_id,
        severity="MEDIUM" if applies else "LOW",
    )


def check_fssai_license(business: BusinessProfile) -> Finding:
    """Food Safety and Standards Authority of India (FSSAI) licensing."""
    text_to_check = f"{business.name or ''} {business.activity or ''}".lower()
    food_keywords = ["restaurant", "cafe", "food", "bakery", "sweet", "dairy", "catering", "grocery", "hotel", "snack", "kitchen"]
    is_food = any(k in text_to_check for k in food_keywords)

    if not is_food:
        return Finding(
            requirement="FSSAI Food Safety License / Registration",
            applies=False,
            reason="Activity does not involve food manufacturing, storage, handling, or distribution",
            evidence_id="FSSAI-001",
            severity="LOW",
        )

    turnover = business.turnover_lakh
    if turnover < 12:
        return Finding(
            requirement="FSSAI Basic Food Registration",
            applies=True,
            reason=f"Food business with turnover Rs.{turnover}L (< Rs.12L ceiling) requires 14-digit FSSAI Basic Registration",
            evidence_id="FSSAI-001",
            severity="HIGH",
        )
    elif turnover <= 2000:
        return Finding(
            requirement="FSSAI State Food License",
            applies=True,
            reason=f"Food business with turnover Rs.{turnover}L (between Rs.12L and Rs.20Cr) requires an FSSAI State License",
            evidence_id="FSSAI-002",
            severity="HIGH",
        )
    else:
        return Finding(
            requirement="FSSAI Central Food License",
            applies=True,
            reason=f"Large scale food business with turnover Rs.{turnover}L (> Rs.20Cr) requires an FSSAI Central License",
            evidence_id="FSSAI-003",
            severity="HIGH",
        )


def check_msme_delayed_payment_protection(business: BusinessProfile) -> Finding:
    """Section 43B(h) Income Tax & MSMED Act 45-day protection."""
    turnover_crore = business.turnover_lakh / 100
    is_micro_or_small = turnover_crore <= 50

    if is_micro_or_small:
        return Finding(
            requirement="MSME Section 43B(h) Payment Protection & Vendor Compliance",
            applies=True,
            reason=(
                f"As a Micro/Small enterprise, buyers must pay within 45 days. "
                "Simultaneously, any dues owed to other MSME suppliers must be cleared within 45 days to avoid tax disallowance."
            ),
            evidence_id="IT-003",
            severity="ADVISORY",
        )
    return Finding(
        requirement="MSME Section 43B(h) Vendor Payment Compliance",
        applies=True,
        reason="Medium/Large enterprise must ensure all payments to Micro/Small vendors are settled within 45 days under IT Sec 43B(h).",
        evidence_id="IT-003",
        severity="MEDIUM",
    )


def check_presumptive_taxation(business: BusinessProfile) -> Finding:
    """Income Tax Presumptive Scheme (Section 44AD / 44ADA)."""
    turnover = business.turnover_lakh
    act = (business.activity or "").lower()
    is_prof = "consult" in act or "service" in act or business.business_type == "services"

    if is_prof and turnover <= 75:
        return Finding(
            requirement="Presumptive Taxation for Professionals (Sec 44ADA)",
            applies=True,
            reason=f"Gross receipts of Rs.{turnover}L <= Rs.75L ceiling; eligible to declare 50% presumptive profit without statutory audit",
            evidence_id="IT-002",
            severity="ADVISORY",
        )
    elif not is_prof and turnover <= 300:
        return Finding(
            requirement="Presumptive Taxation for Small Businesses (Sec 44AD)",
            applies=True,
            reason=f"Turnover of Rs.{turnover}L <= Rs.300L ceiling; eligible to declare 6%-8% presumptive income and avoid maintenance of books",
            evidence_id="IT-001",
            severity="ADVISORY",
        )

    return Finding(
        requirement="Presumptive Taxation (Sec 44AD/44ADA)",
        applies=False,
        reason=f"Turnover Rs.{turnover}L exceeds the maximum statutory limit for presumptive schemes",
        evidence_id="IT-001",
        severity="LOW",
    )


ALL_RULES = [
    check_gst_registration,
    check_composition_scheme,
    check_udyam_classification,
    check_shops_establishments,
    check_pf_registration,
    check_esi_registration,
    check_professional_tax,
    check_fssai_license,
    check_msme_delayed_payment_protection,
    check_presumptive_taxation,
]


def evaluate_business(business: BusinessProfile) -> List[Finding]:
    """Run every statutory rule against a business profile and return all findings."""
    return [rule(business) for rule in ALL_RULES]


def check_requirements(business_id: str) -> dict:
    """
    Evaluate all compliance rules for a business by ID and return structured findings.
    Supplements/replaces single-requirement checks with a full compliance audit.
    """
    try:
        from core.business_profile import get_business
    except ImportError:
        from business_profile import get_business
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
            "severity": f.severity,
        }
        if "udyam" in f.requirement.lower() and f.applies:
            entry["workflow_available"] = "udyam_registration"
        findings.append(entry)

    # Persist findings to database
    try:
        from core.database import persist_findings
        persist_findings(biz.business_id, findings)
    except Exception as e:
        pass

    return {
        "business_id": biz.business_id,
        "business_name": biz.name,
        "applicable_count": sum(1 for f in findings if f["applies"]),
        "findings": findings,
    }


if __name__ == "__main__":
    try:
        from core.business_profile import SAMPLE_BUSINESSES
    except ImportError:
        from business_profile import SAMPLE_BUSINESSES

    for biz in SAMPLE_BUSINESSES:
        print("=" * 70)
        print(f"{biz.name}  (turnover=Rs.{biz.turnover_lakh}L, employees={biz.employee_count}, state={biz.state})")
        print("-" * 70)
        for finding in evaluate_business(biz):
            status = "APPLIES" if finding.applies else "not applicable"
            print(f"  [{status:14}] {finding.requirement} ({finding.severity})")
            print(f"                   Reason: {finding.reason}")
            print(f"                   Evidence: {finding.evidence_id}")
        print()