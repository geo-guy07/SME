# SME Audit AI — Agentic Compliance & Audit Automation System

An autonomous, dual-engine compliance automation and audit assistant designed specifically for Indian Small and Medium Enterprises (SMEs).

The system automates regulatory compliance checks across **GST, MSME (Udyam), Shops & Establishments, EPF, and ESIC**, combining an offline mathematical statutory rules engine with hybrid retrieval-augmented generation (RAG) and automated government portal interactions.

---

## 🌟 Key Features

### 1. Dual-Engine Autonomous Agent Core (`core/agent_engine.py`)
- **Online Engine:** Live Google Gemini 2.5 Flash function-calling agent that autonomously reasons, selects, and invokes tools.
- **Offline / Deterministic Engine:** Local autonomous tool dispatcher that executes real Python tools deterministically with zero LLM hallucination when disconnected or without an API key.
- **Unified Observability (`ToolTracer`):** Real-time millisecond-level latency tracking, payload inspection, and statutory-compliant PII masking (Aadhaar, PAN, phone).

### 2. Central Statutory Rules Engine (`core/rules_engine.py`)
Evaluates verified business profiles against 6 Indian statutory domains:
- **GST Registration Thresholds:** Differentiates goods (₹40L) vs. services (₹20L) and special category northeastern states (₹10L / ₹20L).
- **Composition Scheme Eligibility:** Validates Section 10 CGST Act thresholds (up to ₹1.5 Cr; ₹75L for special category) and service restrictions.
- **MSME Udyam Classification:** Categorizes enterprises into Micro, Small, and Medium bands based on official investment and turnover thresholds (S.O. 2119(E)).
- **Labor Laws:** Headcount-based statutory triggers for **EPF** (≥20 employees) and **ESIC** (≥10 employees).
- **Shops & Establishments:** State-specific commercial establishment requirements.

### 3. Regulatory RAG Pipeline (`rag/vector_store.py`)
- **Hybrid Retrieval:** Dense semantic vector search via **ChromaDB** combined with sparse keyword ranking via **BM25Okapi**.
- **Model Compatibility & Isolation:** Partitioned collection namespaces (`sme_regulations_local` for 384-dim local MiniLM vs. `sme_regulations_gemini` for 3072-dim Gemini embeddings) preventing dimension-mismatch crashes.
- **Evidence-Grounded Citations:** Every audit finding is linked to official Gazette of India notifications and statutory provisions.

### 4. Multimodal Document OCR & Regex Extraction (`core/doc_extractor.py`)
- Ingests scanned business documents, tax filings, and registration certificates (PDF / image).
- Online extraction via Gemini Vision; offline parsing via `pypdf`.
- Algorithmic statutory extractors for:
  - 15-character **GSTIN** checksum validation
  - PAN derivation (characters 3–12 of GSTIN)
  - Indian state code mapping (01–38)
  - Turnover and employee headcount detection

### 5. Udyam MSME Browser Automation (`core/workflow.py`)
- State machine workflow: `READY` → `VALIDATING` → `RUNNING` → `AWAITING_USER` → `COMPLETED`.
- Playwright-based interaction structure simulating `udyamregistration.gov.in`.
- **Honest Human-In-The-Loop (HITL) Boundary:** Respects statutory authentication rules by deliberately pausing at the government Aadhaar OTP checkpoint and prompting the user before completing the workflow.

### 6. Interactive Web Dashboard & Agent Studio (`web/`)
- Single Page Application (HTML5 / Vanilla JS / CSS) communicating with FastAPI backend.
- Real-time client-side compliance scorecard recalculation.
- Agent Studio with playbook mission buttons (`full_audit`, `udyam_automate`, `composition_check`, `labor_check`), execution trace timeline, and active engine indicators.

### 7. Dual Persistence Architecture (`core/database.py`)
- **Primary:** PostgreSQL relational store via SQLAlchemy for structured business profiles, audit findings, uploaded documents, and workflow states.
- **Failover:** Automatic zero-configuration **SQLite fallback** (`sme_audit.db`) if PostgreSQL is offline or unreachable.

---

## 🏗️ System Architecture

```
                       ┌─────────────────────────────────────────┐
                       │   Frontend SPA (Dashboard / Studio)     │
                       └────────────────────┬────────────────────┘
                                            │ REST / JSON (/api)
                                            ▼
                       ┌─────────────────────────────────────────┐
                       │          FastAPI Server (`server.py`)    │
                       └────────────────────┬────────────────────┘
                                            │
                    ┌───────────────────────┴───────────────────────┐
                    ▼                                               ▼
      ┌───────────────────────────┐                   ┌───────────────────────────┐
      │  Online Engine (Gemini)   │                   │  Offline Engine (Local)   │
      │  Gemini 2.5 Function Call │                   │  Deterministic Dispatcher │
      └─────────────┬─────────────┘                   └─────────────┬─────────────┘
                    │                                               │
                    └───────────────────────┬───────────────────────┘
                                            ▼
                       ┌─────────────────────────────────────────┐
                       │    Tool Execution Layer & Observability │
                       │    (ToolTracer: Latency, PII Masking)   │
                       └─┬──────────────┬──────────────┬────────┬┘
                         │              │              │        │
                         ▼              ▼              ▼        ▼
                   ┌──────────┐   ┌──────────┐   ┌──────────┐ ┌──────────┐
                   │  Rules   │   │  Hybrid  │   │ Document │ │ Playwright│
                   │  Engine  │   │   RAG    │   │   OCR    │ │  Workflow│
                   └──────────┘   └──────────┘   └──────────┘ └──────────┘
                         │              │              │        │
                         ▼              ▼              ▼        ▼
                   ┌─────────────────────────┐   ┌────────────────────────┐
                   │ PostgreSQL / SQLite DB  │   │  ChromaDB (Gazette)    │
                   └─────────────────────────┘   └────────────────────────┘
```

---

## 📁 Repository Structure

```
SME/
├── core/
│   ├── agent_engine.py       # Dual-engine autonomous orchestrator & ToolTracer
│   ├── database.py           # SQLAlchemy models + auto SQLite fallback
│   ├── db_service.py         # Business profile and audit finding DB operations
│   ├── doc_extractor.py      # Multimodal OCR, native PDF & regex extractors
│   ├── rules_engine.py       # Deterministic statutory compliance evaluator
│   └── workflow.py           # Udyam registration state machine & HITL workflow
├── rag/
│   ├── vector_store.py       # ChromaDB + BM25 hybrid search module
│   └── chroma_db/            # Local vector store directory
├── web/
│   ├── index.html            # Dashboard and Agent Studio interface
│   ├── app.js                # Dynamic scorecard recalculation & API client
│   └── style.css             # Responsive design styles
├── server.py                 # FastAPI application and REST endpoints
├── regulations.py            # Indian Gazette statutory knowledge corpus
├── test_system.py            # Automated test suite (rules, RAG, masking, workflow)
├── test_postgres_and_ocr.py  # Automated test suite (database CRUD, OCR, schema)
└── requirements.txt          # Production dependencies
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.11+
- Git

### 2. Installation

Clone the repository and set up a virtual environment:

```bash
git clone https://github.com/geo-guy07/SME.git
cd SME

python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Environment Variables (Optional)

The system works **100% offline out-of-the-box** using deterministic fallback rules and local vector embeddings. To enable Gemini 2.5 Flash live function calling:

```bash
# Windows (PowerShell):
$env:GEMINI_API_KEY="your_api_key_here"

# Linux/macOS:
export GEMINI_API_KEY="your_api_key_here"
```

*(Optional PostgreSQL setup: by default, if PostgreSQL is not running, the application automatically creates and uses `sme_audit.db` via SQLite).*

### 4. Running the Server

Start the FastAPI application:

```bash
uvicorn server:app --reload --host 127.0.0.1 --port 8000
```

Open your browser and navigate to:
- **Web Dashboard & Agent Studio:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Interactive OpenAPI Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🧪 Testing & Verification

Run the automated test suites:

```bash
# Verify rules engine, hybrid RAG, PII masking, and Udyam workflow
python test_system.py

# Verify database schema, SQLite failover, and OCR regex extractions
python test_postgres_and_ocr.py
```

Both test suites contain **10 comprehensive test cases (100% pass rate)** validating core functionalities across offline and database-backed execution paths.

---

## 🛡️ Data Privacy & Statutory Compliance

- **Zero Fabricated Claims:** Transparent execution labeling (`LOCAL_AUTONOMOUS_TOOL_DISPATCH` vs. `GEMINI_FUNCTION_CALLING`).
- **PII Masking:** Aadhaar (`XXXX-XXXX-1234`), PAN (`XXXXX1234X`), and mobile numbers are automatically sanitized across logs, tool traces, and stored outputs.
- **Statutory HITL Verification:** The automated Udyam portal registration strictly halts at UIDAI OTP authentication and requires manual human confirmation.
