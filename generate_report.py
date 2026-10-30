
import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def create_element(name):
    return OxmlElement(name)

def set_cell_background(cell, fill_hex):
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def set_table_borders(table, color="D3D3D3"):
    tblPr = table._element.xpath('w:tblPr')
    if tblPr:
        borders = parse_xml(
            f'<w:tblBorders {nsdecls("w")}>'
            f'<w:top w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
            f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
            f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
            f'<w:insideV w:val="none"/>'
            f'<w:left w:val="none"/>'
            f'<w:right w:val="none"/>'
            f'</w:tblBorders>'
        )
        tblPr[0].append(borders)

def make_callout_box(doc, text_list, title="KEY HIGHLIGHT"):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    set_cell_background(cell, "F0F4F8")
    set_cell_margins(cell, top=140, bottom=140, left=200, right=200)
    
    # Left border only (Navy `#1B365D`)
    tcPr = cell._element.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:left w:val="single" w:sz="24" w:space="0" w:color="1B365D"/>'
        f'<w:top w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'<w:bottom w:val="none"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(4)
    run_title = p.add_run(f"📌 {title}\n")
    run_title.bold = True
    run_title.font.name = "Arial"
    run_title.font.size = Pt(11)
    run_title.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)
    
    for idx, t in enumerate(text_list):
        if idx > 0:
            p = cell.add_paragraph()
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(4)
        run_t = p.add_run(t)
        run_t.font.name = "Arial"
        run_t.font.size = Pt(10)
        run_t.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

def build_docx_report():
    doc = docx.Document()

    # Document margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # Color Palette Definitions
    PRIMARY_COLOR = RGBColor(0x1B, 0x36, 0x5D)   # Deep Navy Blue
    SECONDARY_COLOR = RGBColor(0x2B, 0x54, 0x8A) # Slate Blue
    BODY_COLOR = RGBColor(0x33, 0x33, 0x33)      # Off-Black
    MUTED_COLOR = RGBColor(0x66, 0x66, 0x66)     # Dark Gray

    # Helper styling functions
    def add_heading_1(text):
        h = doc.add_heading(text, level=1)
        h.paragraph_format.space_before = Pt(18)
        h.paragraph_format.space_after = Pt(8)
        h.paragraph_format.keep_with_next = True
        for r in h.runs:
            r.font.name = "Arial"
            r.font.size = Pt(18)
            r.font.bold = True
            r.font.color.rgb = PRIMARY_COLOR
        return h

    def add_heading_2(text):
        h = doc.add_heading(text, level=2)
        h.paragraph_format.space_before = Pt(14)
        h.paragraph_format.space_after = Pt(6)
        h.paragraph_format.keep_with_next = True
        for r in h.runs:
            r.font.name = "Arial"
            r.font.size = Pt(14)
            r.font.bold = True
            r.font.color.rgb = SECONDARY_COLOR
        return h

    def add_heading_3(text):
        h = doc.add_heading(text, level=3)
        h.paragraph_format.space_before = Pt(10)
        h.paragraph_format.space_after = Pt(4)
        h.paragraph_format.keep_with_next = True
        for r in h.runs:
            r.font.name = "Arial"
            r.font.size = Pt(12)
            r.font.bold = True
            r.font.color.rgb = PRIMARY_COLOR
        return h

    def add_body_paragraph(text, bold_prefix="", bullet=False):
        p = doc.add_paragraph(style='List Bullet' if bullet else 'Normal')
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.15

        if bold_prefix:
            r_pre = p.add_run(bold_prefix)
            r_pre.font.name = "Arial"
            r_pre.font.size = Pt(10.5)
            r_pre.font.bold = True
            r_pre.font.color.rgb = BODY_COLOR

        r_text = p.add_run(text)
        r_text.font.name = "Arial"
        r_text.font.size = Pt(10.5)
        r_text.font.color.rgb = BODY_COLOR
        return p

    # -------------------------------------------------------------
    # TITLE COVER / HEADER BLOCK
    # -------------------------------------------------------------
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    title_p.paragraph_format.space_before = Pt(10)
    title_p.paragraph_format.space_after = Pt(4)
    run_t = title_p.add_run("SME Compliance & Statutory Audit AI Assistant")
    run_t.font.name = "Arial"
    run_t.font.size = Pt(26)
    run_t.font.bold = True
    run_t.font.color.rgb = PRIMARY_COLOR

    sub_p = doc.add_paragraph()
    sub_p.paragraph_format.space_before = Pt(0)
    sub_p.paragraph_format.space_after = Pt(16)
    run_sub = sub_p.add_run("Comprehensive Technical Architecture, System Analysis & Milestone 3 Report")
    run_sub.font.name = "Arial"
    run_sub.font.size = Pt(14)
    run_sub.font.color.rgb = SECONDARY_COLOR

    # Meta Table (Date, Author, Version, Status)
    meta_table = doc.add_table(rows=2, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(meta_table, "CCCCCC")
    
    meta_data = [
        [("Project Name:", " SME Compliance Assistant (Macro Project-I)"), ("Date:", " September 2026")],
        [("Version / Milestone:", " 2.0.0 (Milestone 3 Completed)"), ("Database Engine:", " PostgreSQL + SQLAlchemy 2.0")]
    ]
    for row_idx, row in enumerate(meta_table.rows):
        for col_idx, cell in enumerate(row.cells):
            set_cell_background(cell, "F9FAFC")
            set_cell_margins(cell, top=80, bottom=80, left=120, right=120)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            lbl, val = meta_data[row_idx][col_idx]
            r1 = p.add_run(lbl)
            r1.bold = True
            r1.font.size = Pt(9.5)
            r1.font.name = "Arial"
            r1.font.color.rgb = PRIMARY_COLOR
            r2 = p.add_run(val)
            r2.font.size = Pt(9.5)
            r2.font.name = "Arial"
            r2.font.color.rgb = BODY_COLOR

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # -------------------------------------------------------------
    # 1. EXECUTIVE SUMMARY
    # -------------------------------------------------------------
    add_heading_1("1. Executive Summary")
    
    add_body_paragraph(
        "The SME Compliance & Statutory Audit AI Assistant is an enterprise-grade agentic system designed to simplify, automate, and streamline Indian statutory compliance for Small and Medium Enterprises (SMEs), Chartered Accountants (CAs), and compliance officers. Navigating complex multi-tiered regulatory environments—including GST registration, Udyam MSME classification, Shops & Establishments Act, Provident Fund (PF), and Employees' State Insurance (ESI)—presents a severe burden for business owners."
    )
    
    add_body_paragraph(
        "This project combines modern LLM tool-calling architectures (Google Gemini 2.5/1.5 Flash), hybrid Retrieval-Augmented Generation (ChromaDB dense vectors + BM25 sparse keyword search), vision OCR document parsing, a deterministic rules engine, and a state-machine workflow engine integrated into a full-stack web application backed by PostgreSQL."
    )

    make_callout_box(
        doc,
        [
            "• End-to-End Statutory Compliance Auditing: Evaluates turnover, employee count, state category, and business type against active Indian statutory thresholds.",
            "• Hybrid RAG Knowledge Base: Provides instant, evidence-grounded regulatory retrieval citing exact statute clauses (e.g., GST-001, MSME-002, LAB-001).",
            "• Multimodal Vision OCR: Extracts structured business entities directly from uploaded GST certificates, PAN cards, invoices, and utility bills.",
            "• Human-in-the-Loop Workflow Automation: Pre-fills portal applications (e.g. Udyam MSME) while strictly adhering to privacy boundary controls (Aadhaar OTP verification).",
            "• Enterprise PostgreSQL Persistence: Complete database layer managing users, business profiles, document uploads, audit findings, and auditable workflow state logs."
        ],
        title="Core System Capabilities"
    )

    # -------------------------------------------------------------
    # 2. SYSTEM ARCHITECTURE & DATA FLOW
    # -------------------------------------------------------------
    add_heading_1("2. System Architecture & Core Components")

    add_body_paragraph(
        "The application follows a clean, decoupled multi-tier architecture. High-level requests from the responsive single-page Web UI are processed by a FastAPI backend server, which orchestrates specialized subsystems:"
    )

    add_body_paragraph(
        " FastAPI (Python 3.11+) delivering RESTful endpoints for authentication, business profile management, document ingestion, statutory audits, RAG search, interactive AI chat, and workflow execution.",
        bold_prefix="1. REST API Layer (server.py):",
        bullet=True
    )
    add_body_paragraph(
        " SQLAlchemy 2.0 ORM with PostgreSQL database managing five core schemas: Users, Businesses, DocumentUploads, AuditFindings, and WorkflowRecords.",
        bold_prefix="2. Database Persistence Layer (core/database.py & db_service.py):",
        bullet=True
    )
    add_body_paragraph(
        " Evaluates business dataclasses against 6 real statutory rule functions, generating structured findings with mandatory evidence IDs.",
        bold_prefix="3. Deterministic Rules Engine (core/rules_engine.py):",
        bullet=True
    )
    add_body_paragraph(
        " Combines ChromaDB dense vector embeddings with BM25 Okapi keyword ranking over an indexed Indian regulatory corpus.",
        bold_prefix="4. Hybrid RAG Retrieval Engine (rag/vector_store.py & regulations.py):",
        bullet=True
    )
    add_body_paragraph(
        " Utilizes Gemini Vision API (or offline fallback) to parse document photos and automatically populate business profiles.",
        bold_prefix="5. Vision OCR Document Parsing (core/doc_extractor.py):",
        bullet=True
    )
    add_body_paragraph(
        " Implements a 6-stage lifecycle (READY, COLLECTING_DATA, VALIDATING, RUNNING, AWAITING_USER, COMPLETED) with sensitive data masking and pre-flight web structure checks.",
        bold_prefix="6. Automated Portal Workflow Engine (core/workflow.py):",
        bullet=True
    )
    add_body_paragraph(
        " Autonomous tool-calling agent enabling multi-step reasoning cycles (search_regulations, query_business_data, check_requirement).",
        bold_prefix="7. Tool-Calling Agent Loop (agent_demo.py):",
        bullet=True
    )

    # -------------------------------------------------------------
    # 3. DETAILED MODULE DEEP-DIVE
    # -------------------------------------------------------------
    add_heading_1("3. Detailed Module Deep-Dive")

    # 3.1 Relational Database Schema
    add_heading_2("3.1 Relational Database Layer (PostgreSQL & SQLAlchemy 2.0)")
    add_body_paragraph(
        "The persistence layer is implemented in core/database.py and core/db_service.py. It connects to PostgreSQL via SQLAlchemy 2.0 and psycopg2, automatically creating tables and seeding sample data upon startup."
    )

    db_table = doc.add_table(rows=6, cols=3)
    db_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(db_table, "B0C4DE")

    headers = ["Table Name", "Primary Keys / Foreign Keys", "Description & Key Attributes"]
    hdr_cells = db_table.rows[0].cells
    for idx, text in enumerate(headers):
        set_cell_background(hdr_cells[idx], "1B365D")
        set_cell_margins(hdr_cells[idx], top=100, bottom=100, left=120, right=120)
        p = hdr_cells[idx].paragraphs[0]
        r = p.add_run(text)
        r.bold = True
        r.font.name = "Arial"
        r.font.size = Pt(10)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    db_rows_data = [
        ["users", "user_id (PK)", "Application users (owners, CAs, compliance officers). Stores name, email, phone, role."],
        ["businesses", "business_id (PK), user_id (FK)", "SME profile parameters: turnover_lakh, employee_count, state, GSTIN, PAN, registration_status, special_category_state."],
        ["document_uploads", "upload_id (PK), business_id (FK), user_id (FK)", "Ingested files metadata, file_path, document_type, extracted_data (JSON), confidence_score."],
        ["findings", "finding_id (PK), business_id (FK)", "Persisted statutory audit results: requirement, applies (boolean), reason, evidence_id."],
        ["workflow_records", "workflow_id (PK), business_id (FK)", "Audit log for automated workflows: workflow_name, status, stage, steps_log (JSON execution trace)."]
    ]

    for row_idx, data in enumerate(db_rows_data, start=1):
        row_cells = db_table.rows[row_idx].cells
        bg_hex = "F9FAFC" if row_idx % 2 == 1 else "FFFFFF"
        for col_idx, text in enumerate(data):
            set_cell_background(row_cells[col_idx], bg_hex)
            set_cell_margins(row_cells[col_idx], top=80, bottom=80, left=100, right=100)
            p = row_cells[col_idx].paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(text)
            r.font.name = "Arial"
            r.font.size = Pt(9.5)
            r.font.color.rgb = BODY_COLOR

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # 3.2 Statutory Rules Engine
    add_heading_2("3.2 Statutory Rules Engine (core/rules_engine.py)")
    add_body_paragraph(
        "The statutory rules engine evaluates a BusinessProfile against active Indian compliance thresholds. Rather than relying solely on LLM text generation, statutory applicability is computed deterministically to eliminate hallucinations and guarantee legal accuracy."
    )

    # Table of Compliance Rules
    rules_table = doc.add_table(rows=7, cols=4)
    rules_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(rules_table, "B0C4DE")

    r_headers = ["Compliance Requirement", "Statutory Threshold", "Evidence ID", "Applicability Logic Summary"]
    r_hdr_cells = rules_table.rows[0].cells
    for idx, text in enumerate(r_headers):
        set_cell_background(r_hdr_cells[idx], "1B365D")
        set_cell_margins(r_hdr_cells[idx], top=100, bottom=100, left=100, right=100)
        p = r_hdr_cells[idx].paragraphs[0]
        r = p.add_run(text)
        r.bold = True
        r.font.name = "Arial"
        r.font.size = Pt(9.5)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    rules_data = [
        ["GST Mandatory Registration", "Rs. 40L (Goods) / Rs. 20L (Services) [Special states: Rs. 20L / 10L]", "GST-001 / GST-002", "Applies if turnover >= turnover threshold based on state category."],
        ["GST Composition Scheme", "Turnover <= Rs. 1.5 Crore [Special states: <= Rs. 75L]", "GST-003", "Eligible for simplified tax compliance if turnover is below statutory ceiling."],
        ["Udyam MSME Classification", "Micro: <= 5Cr | Small: <= 50Cr | Medium: <= 250Cr", "MSME-001/2/3", "Categorizes business into Micro, Small, or Medium Enterprise tier."],
        ["Shops & Establishments", "Employee count >= 1", "SE-001", "Mandatory commercial establishment registration upon hiring 1 worker."],
        ["Provident Fund (PF)", "Employee count >= 20", "LAB-001", "Mandatory EPF registration once workforce reaches 20 employees."],
        ["ESI Insurance", "Employee count >= 10", "LAB-002", "Mandatory ESIC employee health insurance at 10 or more employees."]
    ]

    for row_idx, data in enumerate(rules_data, start=1):
        row_cells = rules_table.rows[row_idx].cells
        bg_hex = "F9FAFC" if row_idx % 2 == 1 else "FFFFFF"
        for col_idx, text in enumerate(data):
            set_cell_background(row_cells[col_idx], bg_hex)
            set_cell_margins(row_cells[col_idx], top=80, bottom=80, left=100, right=100)
            p = row_cells[col_idx].paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(text)
            r.font.name = "Arial"
            r.font.size = Pt(9)
            r.font.color.rgb = BODY_COLOR

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # 3.3 Multimodal Document Extractor
    add_heading_2("3.3 Multimodal Document Extractor & Vision OCR (core/doc_extractor.py)")
    add_body_paragraph(
        "To remove manual data entry friction, doc_extractor.py enables business owners to upload photographs or scans of physical identity and statutory documents. It utilizes Google's Gemini Vision API (gemini-2.5-flash / gemini-1.5-flash) with structured JSON schema outputs."
    )
    add_body_paragraph(
        "Extracted fields (Business Name, PAN, GSTIN, Owner, Turnover, Employee Count, Address) are automatically parsed, assigned a confidence score, stored in document_uploads, and merged into the active Business profile in PostgreSQL."
    )

    # 3.4 Regulatory Hybrid RAG Engine
    add_heading_2("3.4 Regulatory RAG & Knowledge Retrieval (rag/vector_store.py)")
    add_body_paragraph(
        "The RAG system indexes structured statutory snippets (GST Act, MSME Development Act, Factories Act, PF/ESI Acts). To achieve high precision and recall, it uses a Hybrid Search strategy:"
    )
    add_body_paragraph(
        " Computes cosine similarity over dense vector embeddings stored in ChromaDB.",
        bold_prefix="• Dense Vector Retrieval (ChromaDB):",
        bullet=True
    )
    add_body_paragraph(
        " Uses BM25Okapi to match specific legal terms, section numbers, and threshold numbers.",
        bold_prefix="• Sparse Keyword Retrieval (BM25):",
        bullet=True
    )
    add_body_paragraph(
        " Merges and normalizes vector and keyword scores (Score = 0.6 * Dense + 0.4 * BM25), returning top-k grounded regulatory evidence.",
        bold_prefix="• Score Fusion:",
        bullet=True
    )

    # 3.5 Automated Portal Workflow Engine
    add_heading_2("3.5 Workflow State Machine & Privacy Safeguards (core/workflow.py)")
    add_body_paragraph(
        "Automating official portal filings (such as Udyam MSME registration) requires strict governance and data privacy controls:"
    )
    add_body_paragraph(
        " Deterministic status transitions prevent invalid states (e.g. attempting to submit without validation).",
        bold_prefix="1. State Machine:",
        bullet=True
    )
    add_body_paragraph(
        " All sensitive data (Aadhaar numbers, PAN, mobile numbers, passwords, OTPs) are masked prior to writing to console logs or stored workflow state records (e.g. 123456789012 becomes XXXX-XXXX-9012).",
        bold_prefix="2. Data Privacy & PII Masking:",
        bullet=True
    )
    add_body_paragraph(
        " Before interacting with live external portals, the workflow verifies DOM layout integrity. If portal structures change, the script fails safely rather than submitting corrupted data.",
        bold_prefix="3. Pre-flight Layout Verification:",
        bullet=True
    )
    add_body_paragraph(
        " The workflow pauses at e-KYC boundaries, requiring explicit human OTP entry before proceeding.",
        bold_prefix="4. Mandatory Human Verification Boundary:",
        bullet=True
    )
    add_body_paragraph(
        " The workflow engine never claims registration is COMPLETED without genuine portal acknowledgment receipts.",
        bold_prefix="5. Strict Status Honesty:",
        bullet=True
    )

    # -------------------------------------------------------------
    # 4. FRONTEND & USER INTERFACE
    # -------------------------------------------------------------
    add_heading_1("4. Web Frontend & Dashboard Interface")

    add_body_paragraph(
        "The project features a sleek, modern single-page web dashboard located in the web/ directory (index.html, styles.css, app.js). Built using responsive vanilla CSS and dynamic JavaScript, it provides:"
    )
    add_body_paragraph(
        " Displaying active business turnover, employee count, state classification, and total applicable compliance requirements.",
        bold_prefix="• Business Profile & Compliance Scorecard:",
        bullet=True
    )
    add_body_paragraph(
        " Drag-and-drop document uploader with instant OCR preview and field auto-population.",
        bold_prefix="• Document Vault & OCR Scanner:",
        bullet=True
    )
    add_body_paragraph(
        " Live cards for all 6 compliance rules showing status tags (APPLIES / NOT APPLICABLE), rule logic, and evidence links.",
        bold_prefix="• Statutory Audit Center:",
        bullet=True
    )
    add_body_paragraph(
        " Interactive chat window connected to the RAG and agent engine for querying compliance queries.",
        bold_prefix="• Conversational Compliance Assistant:",
        bullet=True
    )
    add_body_paragraph(
        " Interactive modal displaying step-by-step progress, pre-filled form fields, and OTP prompt dialogs.",
        bold_prefix="• Automated Workflow Execution Panel:",
        bullet=True
    )

    # -------------------------------------------------------------
    # 5. SYSTEM VERIFICATION & TESTING RESULTS
    # -------------------------------------------------------------
    add_heading_1("5. System Verification & Testing Suite")

    add_body_paragraph(
        "The repository includes a comprehensive automated test suite (test_system.py and test_postgres_and_ocr.py) validating system integrity, database operations, RAG retrieval, rules calculation, and privacy masking."
    )

    test_table = doc.add_table(rows=5, cols=3)
    test_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(test_table, "B0C4DE")

    t_headers = ["Test Module", "Verification Target", "Result / Status"]
    t_hdr_cells = test_table.rows[0].cells
    for idx, text in enumerate(t_headers):
        set_cell_background(t_hdr_cells[idx], "1B365D")
        set_cell_margins(t_hdr_cells[idx], top=100, bottom=100, left=100, right=100)
        p = t_hdr_cells[idx].paragraphs[0]
        r = p.add_run(text)
        r.bold = True
        r.font.name = "Arial"
        r.font.size = Pt(9.5)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    test_data = [
        ["test_rag_search_regulations_not_empty", "Ensures hybrid vector + BM25 search returns non-empty, relevant statutory snippets with valid regulation IDs.", "PASSED"],
        ["test_check_requirements_structured_json", "Verifies rules engine outputs structured findings for all 6 rules and flags workflow availability for Udyam.", "PASSED"],
        ["test_sensitive_data_masking", "Confirms masking logic correctly sanitizes Aadhaar, PAN, OTP, and mobile numbers in state logs.", "PASSED"],
        ["test_udyam_workflow_lifecycle_and_honesty", "Validates 6-stage lifecycle transitions, human OTP pause boundary, and truthful status tracking.", "PASSED"]
    ]

    for row_idx, data in enumerate(test_data, start=1):
        row_cells = test_table.rows[row_idx].cells
        bg_hex = "F9FAFC" if row_idx % 2 == 1 else "FFFFFF"
        for col_idx, text in enumerate(data):
            set_cell_background(row_cells[col_idx], bg_hex)
            set_cell_margins(row_cells[col_idx], top=80, bottom=80, left=100, right=100)
            p = row_cells[col_idx].paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(text)
            r.font.name = "Arial"
            r.font.size = Pt(9)
            if col_idx == 2:
                r.font.bold = True
                r.font.color.rgb = RGBColor(0x00, 0x80, 0x00) # Green
            else:
                r.font.color.rgb = BODY_COLOR

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # -------------------------------------------------------------
    # 6. ROADMAP & FUTURE DEVELOPMENT
    # -------------------------------------------------------------
    add_heading_1("6. Progress Summary & Future Roadmap")

    add_body_paragraph(
        "The project has successfully completed Milestone 3, transforming initial prototype concepts into a production-grade, persistent compliance assistant."
    )

    make_callout_box(
        doc,
        [
            "• Milestone 1 (Completed): Hybrid RAG retrieval engine + statutory regulations corpus (10 core snippets).",
            "• Milestone 2 (Completed): BusinessProfile schema, deterministic rules engine (6 rules), and agentic tool-calling demo.",
            "• Milestone 3 (Completed): FastAPI backend server, PostgreSQL persistence layer (SQLAlchemy 2.0 ORM), Gemini Vision OCR document extractor, Udyam portal workflow state machine with e-KYC boundary controls, responsive Web UI dashboard, and automated test suite.",
            "• Milestone 4 (Planned Roadmap):",
            "   1. Regulatory Corpus Expansion: Scale knowledge base from 10 to 50+ detailed statutory regulations across state-specific Shops & Establishments rules.",
            "   2. Multi-Portal Workflow Automation: Expand portal automation from Udyam to GST registration, Trade License application, and EPF/ESIC employer registration.",
            "   3. Live Browser Headless Playwright Integration: Connect Playwright live browser automation with real portal captcha solving.",
            "   4. Automated Statutory Calendar & Reminders: Scheduled cron notifications for GST return deadlines (GSTR-1, GSTR-3B) and PF/ESI monthly payouts."
        ],
        title="Project Milestones & Future Development Horizon"
    )

    # Save document
    output_filename = "SME_Compliance_Assistant_Project_Report.docx"
    doc.save(output_filename)
    print(f"Report successfully created: {output_filename}")

if __name__ == "__main__":
    build_docx_report()
