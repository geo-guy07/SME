# SME Compliance Assistant — Progress Prototypes

Runnable prototypes for the SME Compliance & Audit Assistant (Macro Project-I).
Tracks progress across milestones — this README reflects the current
(Milestone 3) state of the code.

## Setup (on your own machine)

```bash
pip install chromadb google-generativeai rank_bm25
export GEMINI_API_KEY="your_key_here"   # get one at aistudio.google.com
```

All scripts also run **without** an API key — they'll show retrieved
context / a deterministic mock of the tool-calling flow instead of a
live Gemini answer, so you can still test the pipeline before you have a key.

## Files

| File                  | Purpose                                                                                                       |
| --------------------- | ------------------------------------------------------------------------------------------------------------- |
| `regulations.py`      | Regulatory knowledge base — 10 real snippets (GST, Udyam/MSME, Shops & Establishments, PF/ESI)                |
| `rag_demo.py`         | RAG mini-demo — hybrid retrieval + Gemini answer                                                              |
| `business_profile.py` | Structured `BusinessProfile` dataclass + 4 sample businesses                                                  |
| `rules_engine.py`     | Real threshold rules engine — evaluates a business against 6 compliance rules                                 |
| `agent_demo.py`       | Agentic tool-calling demo — now wired to `business_profile.py` and `rules_engine.py` (no more hardcoded data) |

## 1. `rag_demo.py` — Regulatory RAG mini-demo

Pipeline: **Question -> Hybrid Retrieval (vector + BM25) -> Gemini answer, grounded in evidence**

```bash
python rag_demo.py
```

- Loads 10 real regulatory snippets (`regulations.py`) covering GST thresholds,
  Udyam/MSME classification, Shops & Establishments, PF/ESI.
- Retrieves the most relevant snippets for a sample query using both vector
  similarity (Chroma) and keyword search (BM25), then merges results.
- Passes retrieved context to Gemini, which must cite regulation IDs — no
  unsupported claims.
- Note: on a machine with normal internet access, Chroma will download its
  default sentence-transformer model automatically. If that download is
  blocked (like in a sandboxed environment), the script falls back to a
  simple offline embedding automatically — no code changes needed.

## 2. `business_profile.py` + `rules_engine.py` — Business data + Rules Engine

```bash
python rules_engine.py
```

- `business_profile.py` defines a `BusinessProfile` dataclass (turnover,
  employee count, state, business type, special-category-state flag) and
  four sample businesses for testing.
- `rules_engine.py` evaluates a `BusinessProfile` against six real threshold
  rules — GST registration, Composition Scheme eligibility, Udyam
  classification, Shops & Establishments, PF, and ESI — and returns a
  `Finding` (requirement, applies True/False, reason, evidence regulation ID)
  for each.
- Running `rules_engine.py` directly prints findings for all four sample
  businesses, useful for screenshotting/testing threshold edge cases
  (e.g. special-category-state GST limits).

## 3. `agent_demo.py` — Agentic tool-calling mini-demo

Pipeline: **Question -> LLM decides tool -> Tool executes -> LLM uses result -> final answer**

```bash
python agent_demo.py
```

- Defines three tools: `search_regulations()`, `query_business_data()`,
  `check_requirement()`.
- `query_business_data()` and `check_requirement()` now call directly into
  `business_profile.py` and `rules_engine.py` — no hardcoded dict or inline
  if/else remain.
- With a `GEMINI_API_KEY` set, uses Gemini's native function calling
  (`enable_automatic_function_calling=True`) so Gemini itself decides which
  tools to call and in what order.
- Without a key, runs a deterministic mock that follows the identical
  decide -> call -> use-result -> answer pattern, so you can see and screenshot
  the reasoning trace either way.
- To test a different sample business, change `ACTIVE_BUSINESS_ID` at the
  top of the file to any ID in `business_profile.SAMPLE_BUSINESSES`.

## For the progress report

- Run the scripts, screenshot the terminal output — that's your "work
  completed" evidence.
- `regulations.py` is your regulatory corpus (expand from 10 toward 30-50
  over the coming weeks).
- The architecture/ER diagram (shared separately) maps directly onto this
  code: `REGULATIONS` = `RegulatoryDocument`/`ComplianceRequirement`,
  `BusinessProfile` = `Business`, each tool call = a row in `ToolCallLog`,
  and each `Finding` returned by the rules engine = a `Finding` row (with
  evidence + reasoning).
- Next steps to mention: expand the regulatory corpus, add document/invoice
  extraction via Gemini Vision, wire the agent to a `generate_report()` tool,
  persist business profiles/findings in a real database, and connect a web
  chat interface.