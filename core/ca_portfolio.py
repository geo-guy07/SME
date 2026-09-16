"""
CA / Auditor Client Portfolio Management — SME Compliance Assistant
Aggregates statutory compliance health, risk distribution, filing deadlines,
and 43B(h) disallowance exposures across multiple SME client portfolios.
"""

from typing import Dict, Any, List
from core.database import SessionLocal, Business, FindingRecord
from core.rules_engine import check_requirements


def get_ca_portfolio_summary() -> Dict[str, Any]:
    """
    Computes holistic audit intelligence for Chartered Accountants managing multiple SME clients.
    """
    db = SessionLocal()
    try:
        businesses = db.query(Business).all()
        client_summaries = []

        total_turnover = 0.0
        total_headcount = 0
        high_risk_clients = 0
        total_applicable_obligations = 0

        for b in businesses:
            audit = check_requirements(b.business_id)
            findings = audit.get("findings", [])
            applicable = [f for f in findings if f["applies"]]
            high_sev = [f for f in applicable if f.get("severity") == "HIGH"]

            is_high_risk = len(high_sev) >= 2 or (b.turnover > 40 and not b.pan)
            if is_high_risk:
                high_risk_clients += 1

            total_turnover += b.turnover
            total_headcount += b.employee_count
            total_applicable_obligations += len(applicable)

            # Score calculation: base 100, deducting for high-severity risk gaps
            score = max(35, round(100 - (len(high_sev) * 12 + max(0, len(applicable) - 4) * 3)))

            client_summaries.append({
                "business_id": b.business_id,
                "name": b.name,
                "turnover_lakh": b.turnover,
                "employee_count": b.employee_count,
                "state": b.state,
                "business_type": b.type,
                "applicable_count": len(applicable),
                "high_severity_count": len(high_sev),
                "health_score": score,
                "risk_level": "HIGH" if is_high_risk else ("MEDIUM" if len(high_sev) > 0 else "LOW"),
                "status": b.registration_status or "ACTIVE",
            })

        # Portfolio Deadlines Calendar
        portfolio_deadlines = [
            {"deadline": "11th of month", "obligation": "GSTR-1 Outward Supplies", "affected_clients": len([c for c in client_summaries if c['turnover_lakh'] >= 20])},
            {"deadline": "15th of month", "obligation": "EPFO & ESIC Remittance", "affected_clients": len([c for c in client_summaries if c['employee_count'] >= 10])},
            {"deadline": "20th of month", "obligation": "GSTR-3B Tax Return", "affected_clients": len([c for c in client_summaries if c['turnover_lakh'] >= 20])},
            {"deadline": "Quarterly (CMP-08)", "obligation": "Composition Tax Statement", "affected_clients": len([c for c in client_summaries if c['turnover_lakh'] <= 150])},
            {"deadline": "March 31st", "obligation": "Section 43B(h) Vendor Clearance", "affected_clients": len(client_summaries)},
        ]

        return {
            "portfolio_metrics": {
                "total_clients": len(businesses),
                "high_risk_clients": high_risk_clients,
                "total_turnover_monitored_lakh": round(total_turnover, 2),
                "total_workforce_monitored": total_headcount,
                "total_active_obligations": total_applicable_obligations,
                "portfolio_health_average": round(sum(c["health_score"] for c in client_summaries) / len(client_summaries)) if client_summaries else 100,
            },
            "deadlines": portfolio_deadlines,
            "clients": client_summaries,
        }
    finally:
        db.close()
