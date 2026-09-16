"""
Section 43B(h) Vendor Ledger & Payment Aging Analyzer — SME Compliance Assistant
Evaluates accounts payable / vendor purchase ledgers against Section 15 of the MSMED Act
and Section 43B(h) of the Income Tax Act, 1961.
Calculates tax disallowance exposure, statutory compound penal interest (3x RBI Bank Rate),
and prioritizes urgent vendor payments.
"""

import os
import csv
import io
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from pathlib import Path

# Statutory Interest Rate under MSMED Act Section 16:
# 3 x RBI Bank Rate (currently RBI Bank Rate is 6.5%, so 3 x 6.5% = 19.5% p.a.)
RBI_BANK_RATE = 0.065
STATUTORY_PENAL_RATE_PER_ANNUM = 3.0 * RBI_BANK_RATE  # 19.5% p.a.
CORPORATE_TAX_RATE = 0.26  # 25% + surcharge/cess ~ 26%


def parse_date(date_str: Any) -> Optional[date]:
    """Parse various date formats (YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY)."""
    if not date_str or not str(date_str).strip():
        return None
    s = str(date_str).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def calculate_compound_interest(principal: float, days_overdue: int, annual_rate: float = STATUTORY_PENAL_RATE_PER_ANNUM) -> float:
    """
    Computes compound interest with monthly rests under Section 16 of MSMED Act.
    Formula: A = P * (1 + r/12)^(n/30) - P
    """
    if days_overdue <= 0 or principal <= 0:
        return 0.0
    monthly_rate = annual_rate / 12.0
    months = days_overdue / 30.0
    total_amount = principal * ((1.0 + monthly_rate) ** months)
    return round(total_amount - principal, 2)


def analyze_ledger_rows(rows: List[Dict[str, Any]], reference_date: Optional[date] = None) -> Dict[str, Any]:
    """
    Analyzes vendor ledger rows and outputs comprehensive Section 43B(h) audit findings.
    """
    ref_date = reference_date or date.today()
    analyzed_invoices = []

    total_purchases = 0.0
    total_disallowed_amount = 0.0
    total_penal_interest = 0.0
    overdue_count = 0
    compliant_count = 0
    approaching_deadline_count = 0
    non_msme_count = 0

    for idx, row in enumerate(rows, start=1):
        inv_no = str(row.get("invoice_number") or row.get("Invoice No") or f"INV-{idx:04d}").strip()
        vendor = str(row.get("vendor_name") or row.get("Vendor Name") or f"Vendor {idx}").strip()
        msme_status = str(row.get("msme_status") or row.get("MSME Status") or "Micro").strip().title()

        # Amount parsing
        amt_raw = str(row.get("amount") or row.get("Amount") or row.get("Invoice Amount") or "0").replace(",", "").strip()
        try:
            amount = float(amt_raw)
        except ValueError:
            amount = 0.0

        total_purchases += amount

        inv_date = parse_date(row.get("invoice_date") or row.get("Invoice Date"))
        payment_date = parse_date(row.get("payment_date") or row.get("Payment Date"))
        has_agreement = str(row.get("has_agreement") or "yes").lower() in ("yes", "true", "1")

        # Statutory limit: 45 days with agreement, 15 days without
        statutory_limit_days = 45 if has_agreement else 15

        is_micro_or_small = msme_status in ("Micro", "Small")
        if not is_micro_or_small:
            non_msme_count += 1
            analyzed_invoices.append({
                "invoice_number": inv_no,
                "vendor_name": vendor,
                "msme_status": msme_status,
                "amount": amount,
                "invoice_date": str(inv_date) if inv_date else None,
                "status": "EXEMPT_NON_MSME",
                "status_label": f"Exempt ({msme_status})",
                "days_elapsed": (ref_date - inv_date).days if inv_date else 0,
                "statutory_limit_days": statutory_limit_days,
                "days_overdue": 0,
                "is_disallowed": False,
                "penal_interest": 0.0,
                "reason": "Section 43B(h) applies only to Micro and Small enterprise vendors.",
            })
            continue

        # For Micro & Small suppliers:
        if not inv_date:
            inv_date = ref_date - timedelta(days=30)

        # Elapsed days until payment or today
        cutoff = payment_date if payment_date else ref_date
        days_elapsed = (cutoff - inv_date).days
        days_overdue = max(0, days_elapsed - statutory_limit_days)

        is_paid = payment_date is not None
        is_disallowed = False
        penal_interest = 0.0

        if is_paid:
            if days_overdue > 0:
                status = "PAID_LATE"
                status_label = f"Paid Late ({days_overdue}d delay)"
                penal_interest = calculate_compound_interest(amount, days_overdue)
                total_penal_interest += penal_interest
            else:
                status = "COMPLIANT_ON_TIME"
                status_label = "Settled within 45 Days"
                compliant_count += 1
        else:
            # Unpaid invoice
            if days_overdue > 0:
                status = "DISALLOWED_OVERDUE"
                status_label = f"Overdue by {days_overdue} Days"
                is_disallowed = True
                overdue_count += 1
                total_disallowed_amount += amount
                penal_interest = calculate_compound_interest(amount, days_overdue)
                total_penal_interest += penal_interest
            elif (statutory_limit_days - days_elapsed) <= 10:
                status = "CRITICAL_APPROACHING"
                status_label = f"Due in {statutory_limit_days - days_elapsed} Days"
                approaching_deadline_count += 1
            else:
                status = "COMPLIANT_PENDING"
                status_label = f"Active ({days_elapsed}/{statutory_limit_days} Days)"
                compliant_count += 1

        analyzed_invoices.append({
            "invoice_number": inv_no,
            "vendor_name": vendor,
            "msme_status": msme_status,
            "amount": amount,
            "invoice_date": str(inv_date),
            "payment_date": str(payment_date) if payment_date else None,
            "status": status,
            "status_label": status_label,
            "days_elapsed": days_elapsed,
            "statutory_limit_days": statutory_limit_days,
            "days_overdue": days_overdue,
            "is_disallowed": is_disallowed,
            "penal_interest": penal_interest,
            "reason": (
                f"Exceeds statutory {statutory_limit_days}-day limit under MSMED Act Section 15. "
                f"Disallowed under Income Tax Section 43B(h)."
                if is_disallowed else "Within statutory compliance limits."
            ),
        })

    # Sort invoices: disallowed overdue first, then approaching deadline
    analyzed_invoices.sort(key=lambda x: (not x["is_disallowed"], -x["days_overdue"], -x["amount"]))

    corporate_tax_exposure = round(total_disallowed_amount * CORPORATE_TAX_RATE, 2)

    return {
        "summary": {
            "total_invoices": len(rows),
            "total_purchases": round(total_purchases, 2),
            "total_disallowed_amount": round(total_disallowed_amount, 2),
            "corporate_tax_exposure": corporate_tax_exposure,
            "statutory_compound_interest": round(total_penal_interest, 2),
            "overdue_invoices_count": overdue_count,
            "approaching_deadline_count": approaching_deadline_count,
            "compliant_invoices_count": compliant_count,
            "non_msme_count": non_msme_count,
            "statutory_interest_rate": f"{STATUTORY_PENAL_RATE_PER_ANNUM * 100:.1f}% p.a. (3x RBI Bank Rate)",
            "audit_date": str(ref_date),
        },
        "invoices": analyzed_invoices,
    }


def parse_csv_ledger(csv_content: str) -> Dict[str, Any]:
    """Parse CSV text and run Section 43B(h) ledger analysis."""
    reader = csv.DictReader(io.StringIO(csv_content.strip()))
    rows = list(reader)
    return analyze_ledger_rows(rows)


def generate_sample_ledger_csv() -> str:
    """Generate a realistic sample vendor ledger CSV with mixed MSME statuses for demonstration."""
    sample_rows = [
        ["invoice_number", "vendor_name", "msme_status", "invoice_date", "has_agreement", "amount", "payment_date"],
        ["INV-2026-001", "Precision Tools & Dies", "Micro", "2026-01-05", "yes", "240000.00", ""],
        ["INV-2026-002", "Balaji Packaging Solutions", "Small", "2026-01-12", "yes", "185000.00", ""],
        ["INV-2026-003", "Tata Steel Ltd", "Medium", "2026-01-15", "yes", "950000.00", ""],
        ["INV-2026-004", "Shree Ram Corrugators", "Micro", "2026-02-10", "yes", "78000.00", ""],
        ["INV-2026-005", "National Logistics Logistics", "Non-MSME", "2026-01-20", "yes", "320000.00", ""],
        ["INV-2026-006", "Kisan Agro Processing", "Micro", "2026-01-02", "no", "110000.00", ""],
        ["INV-2026-007", "Vanguard Industrial Gases", "Small", "2026-01-08", "yes", "45000.00", "2026-02-04"],
        ["INV-2026-008", "Modern Electrical Fittings", "Micro", "2026-02-28", "yes", "62000.00", ""],
    ]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(sample_rows)
    return output.getvalue()
