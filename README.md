# SME Compliance Assistant — Progress Milestone Prototypes

Two runnable mini-demos proving the core pipeline works, built for today's milestone.

## Setup (on your own machine)

```bash
pip install chromadb google-generativeai rank_bm25
export GEMINI_API_KEY="your_key_here"   # get one at aistudio.google.com
```

Both scripts also run **without** an API key — they'll show retrieved
context / a deterministic mock of the tool-calling flow instead of a
live Gemini answer, so you can still test the pipeline before you have a key.

## 1. `rag_demo.py` — Regulatory RAG mini-demo

Pipeline: **Question → Hybrid Retrieval (vector + BM25) → Gemini answer, grounded in evidence**

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

## 2. `agent_demo.py` — Agentic tool-calling mini-demo

Pipeline: **Question → LLM decides tool → Tool executes → LLM uses result → final answer**

```bash
python agent_demo.py
```

- Defines three tools: `search_regulations()`, `query_business_data()`,
  `check_requirement()`.
- With a `GEMINI_API_KEY` set, uses Gemini's native function calling
  (`enable_automatic_function_calling=True`) so Gemini itself decides which
  tools to call and in what order.
- Without a key, runs a deterministic mock that follows the identical
  decide → call → use-result → answer pattern, so you can see and screenshot
  the reasoning trace either way.

## For the progress report

- Run both scripts, screenshot the terminal output — that's your "work
  completed" evidence.
- `regulations.py` is your initial real regulatory corpus (expand from 10
  toward 30-50 over the coming weeks).
- The architecture/ER diagram (shared separately) maps directly onto this
  code: `REGULATIONS` = `RegulatoryDocument`/`ComplianceRequirement`,
  `BUSINESS_PROFILE` = `Business`, each tool call = a row in `ToolCallLog`,
  and the final answer format = a `Finding` (with evidence + reasoning).
- Next steps to mention: replace `BUSINESS_PROFILE` mock with a real
  business-profile schema, expand the regulatory corpus, add document/invoice
  extraction via Gemini Vision, wire the agent to actually call
  `generate_report()`, and connect a web chat interface.
