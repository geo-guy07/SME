"""
Formal PDF Audit Report Generator — SME Compliance Assistant
Generates executive-ready, downloadable PDF compliance dossiers using ReportLab.
Includes compliance scorecards, detailed findings, statutory filing deadlines,
penalty risk matrix, and step-by-step remediation roadmaps.
"""

import os
from datetime import datetime
from typing import Dict, Any, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

try:
    from core.business_profile import get_business, BusinessProfile
    from core.rules_engine import check_requirements, evaluate_business
except ImportError:
    from business_profile import get_business, BusinessProfile
    from rules_engine import check_requirements, evaluate_business


def generate_pdf_report(business_id: str, output_path: Optional[str] = None) -> str:
    """
    Build a multi-page professional PDF compliance dossier for a business.
    Returns the absolute path to the generated PDF.
    """
    biz = get_business(business_id)
    if not biz:
        raise ValueError(f"Business profile '{business_id}' not found.")

    findings_data = check_requirements(business_id)
    findings = findings_data["findings"]

    if not output_path:
        reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
        os.makedirs(reports_dir, exist_ok=True)
        output_path = os.path.join(reports_dir, f"SME_Audit_Report_{business_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748b"),
    )
    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155"),
    )
    badge_applies = ParagraphStyle(
        "BadgeApplies",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#b91c1c"),
    )
    badge_exempt = ParagraphStyle(
        "BadgeExempt",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#15803d"),
    )
    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#1e293b"),
    )
    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0f172a"),
    )

    story = []

    # 1. Header Banner
    story.append(Paragraph("SME STATUTORY COMPLIANCE & AUDIT REPORT", title_style))
    story.append(Paragraph(f"Official Regulatory Dossier & Gap Analysis • Generated on {datetime.now().strftime('%d %B %Y, %H:%M IST')}", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563eb"), spaceAfter=14))

    # 2. Business Profile Card
    profile_data = [
        [
            Paragraph("<b>Business Name:</b>", table_cell),
            Paragraph(biz.name, table_cell_bold),
            Paragraph("<b>Business ID:</b>", table_cell),
            Paragraph(biz.business_id, table_cell_bold),
        ],
        [
            Paragraph("<b>Entity Type:</b>", table_cell),
            Paragraph(f"{biz.business_type.title()} ({biz.activity or 'Commercial'})", table_cell),
            Paragraph("<b>Operating State:</b>", table_cell),
            Paragraph(f"{biz.state} {'(Special Category)' if biz.special_category_state else ''}", table_cell),
        ],
        [
            Paragraph("<b>Annual Turnover:</b>", table_cell),
            Paragraph(f"₹ {biz.turnover_lakh:.2f} Lakhs", table_cell_bold),
            Paragraph("<b>Active Headcount:</b>", table_cell),
            Paragraph(f"{biz.employee_count} Employee(s)", table_cell_bold),
        ],
        [
            Paragraph("<b>Owner / Director:</b>", table_cell),
            Paragraph(biz.owner or "Not Recorded", table_cell),
            Paragraph("<b>PAN / ID:</b>", table_cell),
            Paragraph(biz.pan or "NOT LINKED", table_cell),
        ],
    ]

    t_profile = Table(profile_data, colWidths=[1.3 * inch, 2.3 * inch, 1.3 * inch, 2.3 * inch])
    t_profile.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_profile)
    story.append(Spacer(1, 14))

    # 3. Compliance Executive Scorecard
    applicable_count = sum(1 for f in findings if f["applies"])
    high_sev_count = sum(1 for f in findings if f["applies"] and f.get("severity") == "HIGH")
    exempt_count = len(findings) - applicable_count

    scorecard_data = [
        [
            Paragraph(f"<b>{len(findings)}</b><br/><font size=7 color='#64748b'>EVALUATED RULES</font>", table_cell_bold),
            Paragraph(f"<b><font color='#b91c1c'>{applicable_count}</font></b><br/><font size=7 color='#64748b'>ACTIONABLE APPLIES</font>", table_cell_bold),
            Paragraph(f"<b><font color='#15803d'>{exempt_count}</font></b><br/><font size=7 color='#64748b'>CURRENTLY EXEMPT</font>", table_cell_bold),
            Paragraph(f"<b><font color='#c2410c'>{high_sev_count}</font></b><br/><font size=7 color='#64748b'>HIGH PRIORITY RISKS</font>", table_cell_bold),
        ]
    ]
    t_score = Table(scorecard_data, colWidths=[1.8 * inch, 1.8 * inch, 1.8 * inch, 1.8 * inch])
    t_score.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t_score)
    story.append(Spacer(1, 14))

    # 4. Detailed Findings Table
    story.append(Paragraph("Statutory Audit Findings & Evidence", h2_style))

    findings_table_rows = [
        [
            Paragraph("<b>Statutory Requirement</b>", table_cell_bold),
            Paragraph("<b>Status</b>", table_cell_bold),
            Paragraph("<b>Severity</b>", table_cell_bold),
            Paragraph("<b>Regulatory Basis & Reason</b>", table_cell_bold),
            Paragraph("<b>Evidence ID</b>", table_cell_bold),
        ]
    ]

    for f in findings:
        applies_para = Paragraph("<b>MANDATORY</b>", badge_applies) if f["applies"] else Paragraph("EXEMPT", badge_exempt)
        sev_color = "#b91c1c" if f.get("severity") == "HIGH" else ("#c2410c" if f.get("severity") == "MEDIUM" else "#475569")
        sev_para = Paragraph(f"<font color='{sev_color}'><b>{f.get('severity', 'LOW')}</b></font>", table_cell)

        findings_table_rows.append([
            Paragraph(f["requirement"], table_cell_bold),
            applies_para,
            sev_para,
            Paragraph(f["reason"], table_cell),
            Paragraph(f["evidence_id"], table_cell_bold),
        ])

    t_findings = Table(findings_table_rows, colWidths=[1.8 * inch, 0.9 * inch, 0.9 * inch, 2.7 * inch, 0.9 * inch])
    t_findings.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_findings)
    story.append(Spacer(1, 14))

    # 5. Statutory Calendar & Filing Deadlines
    story.append(Paragraph("Statutory Compliance Calendar & Deadlines", h2_style))
    deadlines = [
        ["GSTR-1 (Outward Supplies)", "Monthly: 11th of succeeding month | QRMP: 13th of quarter", "Sec 37 CGST Act"],
        ["GSTR-3B (Summary Tax Return)", "Monthly: 20th of month | QRMP: 22nd/24th of quarter", "Sec 39 CGST Act"],
        ["EPF (Provident Fund) Remittance", "Monthly: 15th of the following month via EPFO Unified Portal", "EPF Act 1952"],
        ["ESIC Monthly Contribution", "Monthly: 15th of following month via ESIC Portal", "ESI Act 1948"],
        ["Professional Tax (PT) Return", "Monthly / Annual (by 10th-30th depending on state rules)", "State PT Acts"],
        ["Income Tax Advance Tax", "15% by Jun 15, 45% by Sep 15, 75% by Dec 15, 100% by Mar 15", "Sec 208-211 IT Act"],
        ["MSME Vendor Dues (Sec 43B(h))", "Payment within 15/45 days; all FY dues cleared before March 31", "Sec 43B(h) IT Act"],
    ]
    calendar_rows = [
        [Paragraph("<b>Compliance Head</b>", table_cell_bold), Paragraph("<b>Statutory Due Date</b>", table_cell_bold), Paragraph("<b>Legal Reference</b>", table_cell_bold)]
    ]
    for d in deadlines:
        calendar_rows.append([Paragraph(d[0], table_cell), Paragraph(d[1], table_cell), Paragraph(d[2], table_cell)])

    t_cal = Table(calendar_rows, colWidths=[2.2 * inch, 3.4 * inch, 1.6 * inch])
    t_cal.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_cal)
    story.append(Spacer(1, 14))

    # 6. Penalty Risks & Disallowance Notices
    story.append(Paragraph("Statutory Penalty Matrix & Disallowance Risks", h2_style))
    risks_data = [
        [
            Paragraph("<b>Area</b>", table_cell_bold),
            Paragraph("<b>Default Condition</b>", table_cell_bold),
            Paragraph("<b>Statutory Consequence / Penalty</b>", table_cell_bold),
        ],
        [
            Paragraph("GST Non-Filing", table_cell),
            Paragraph("Delay in filing GSTR-3B beyond due date", table_cell),
            Paragraph("₹50/day late fee (₹20/day for NIL) + 18% p.a. interest on net tax liability.", table_cell),
        ],
        [
            Paragraph("MSME Overdue Dues", table_cell),
            Paragraph("Payment to MSE delayed past 45 days (Sec 43B(h))", table_cell),
            Paragraph("Full expense disallowed from taxable income + compound interest at 3x RBI Bank Rate.", table_cell),
        ],
        [
            Paragraph("EPFO / ESIC Delay", table_cell),
            Paragraph("Failure to deposit employee & employer dues by 15th", table_cell),
            Paragraph("Damages from 5% to 25% p.a. under Sec 14B + 12% statutory interest under Sec 7Q.", table_cell),
        ],
        [
            Paragraph("Shops & Est. Non-Renewal", table_cell),
            Paragraph("Operating without valid registration renewal", table_cell),
            Paragraph("Sealing of commercial premises or spot compounding fines up to ₹10,000.", table_cell),
        ],
    ]
    t_risks = Table(risks_data, colWidths=[1.8 * inch, 2.4 * inch, 3.0 * inch])
    t_risks.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fef2f2")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#fecaca")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#fee2e2")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_risks)
    story.append(Spacer(1, 14))

    # 7. Step-by-Step Remediation Guide
    story.append(Paragraph("Recommended Action & Remediation Roadmap", h2_style))
    remediation_text = (
        "<b>Phase 1 (Immediate - 7 Days):</b> Complete Udyam MSME Registration on the official portal "
        "to secure statutory 45-day payment protection and priority banking eligibility.<br/>"
        "<b>Phase 2 (15 Days):</b> Reconcile inward supply invoices against GSTR-2B to safeguard Input Tax Credit (ITC) "
        "and remit monthly Professional Tax / PF liabilities.<br/>"
        "<b>Phase 3 (30 Days):</b> Audit vendor master lists to flag registered Micro and Small suppliers for compliance with "
        "Income Tax Section 43B(h)."
    )
    story.append(Paragraph(remediation_text, body_style))
    story.append(Spacer(1, 14))

    # Footer note
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=8))
    story.append(Paragraph(
        "<i>Disclaimer: This document is generated by SME Compliance AI as an audit advisory report based on current Indian statutory provisions. "
        "Formal filings should be validated with your registered Chartered Accountant or Company Secretary.</i>",
        subtitle_style
    ))

    # Build Document
    doc.build(story)
    return os.path.abspath(output_path)


if __name__ == "__main__":
    report_file = generate_pdf_report("B005")
    print(f"Report generated successfully: {report_file}")
