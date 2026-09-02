"""
RAG Mini-Demo — SME Compliance Assistant
Pipeline: Query -> Hybrid Retrieval (BM25 + embeddings via Chroma) -> Gemini answer

Setup:
    pip install chromadb google-generativeai rank_bm25
    export GEMINI_API_KEY="your_key_here"

Run:
    python rag_demo.py
"""

import os
import hashlib
import chromadb
from chromadb.utils import embedding_functions
from rank_bm25 import BM25Okapi
from regulations import REGULATIONS

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")


def _hash_embed(text, dim=384):
    """Offline fallback embedding: bag-of-words hashed into a fixed vector."""
    vec = [0.0] * dim
    for word in text.lower().split():
        idx = int(hashlib.md5(word.encode()).hexdigest(), 16) % dim
        vec[idx] += 1.0
    return vec


def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


class FallbackVectorIndex:
    """
    Minimal in-memory vector index used only if the default sentence-transformer
    model can't be downloaded (e.g. restricted network, as in this sandbox).
    On a normal machine with internet access, Chroma's DefaultEmbeddingFunction
    (or Google's text-embedding-004 for production) is used instead and gives
    much better semantic results than this bag-of-words fallback.
    """
    def __init__(self, docs):
        self.docs = docs
        self.vectors = {d["id"]: _hash_embed(d["text"]) for d in docs}

    def query(self, query_texts, n_results=3):
        qvec = _hash_embed(query_texts[0])
        scored = sorted(self.vectors.items(), key=lambda kv: _cosine(qvec, kv[1]), reverse=True)
        top_ids = [doc_id for doc_id, _ in scored[:n_results]]
        return {"ids": [top_ids]}


def build_knowledge_base():
    """Chunk + embed the regulatory snippets into a Chroma collection (or fallback index)."""
    client = chromadb.Client()  # in-memory for demo; use PersistentClient for real use
    try:
        embed_fn = embedding_functions.DefaultEmbeddingFunction()
        collection = client.create_collection(name="sme_regulations", embedding_function=embed_fn)
        collection.add(
            ids=[r["id"] for r in REGULATIONS],
            documents=[r["text"] for r in REGULATIONS],
            metadatas=[{"title": r["title"], "source": r["source"], "category": r["category"]} for r in REGULATIONS],
        )
        return collection
    except Exception as e:
        print(f"    [!] Default embedding model unavailable ({type(e).__name__}); using offline fallback embedding.")
        return FallbackVectorIndex(REGULATIONS)


def build_bm25_index():
    """Build a keyword (BM25) index over the same regulatory snippets."""
    tokenized_corpus = [r["text"].lower().split() for r in REGULATIONS]
    bm25 = BM25Okapi(tokenized_corpus)
    return bm25


def hybrid_retrieve(query, collection, bm25, top_k=3):
    """Combine vector similarity (Chroma) and keyword search (BM25) results."""
    # Vector search
    vector_results = collection.query(query_texts=[query], n_results=top_k)
    vector_ids = vector_results["ids"][0]

    # Keyword search
    tokenized_query = query.lower().split()
    bm25_scores = bm25.get_scores(tokenized_query)
    ranked_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:top_k]
    bm25_ids = [REGULATIONS[i]["id"] for i in ranked_indices]

    # Merge (dedupe, preserve order: vector first then bm25-only extras)
    merged_ids = list(dict.fromkeys(vector_ids + bm25_ids))[:top_k]
    id_to_reg = {r["id"]: r for r in REGULATIONS}
    return [id_to_reg[i] for i in merged_ids if i in id_to_reg]


def generate_answer(query, retrieved_docs):
    """Call Gemini with retrieved context to produce an evidence-grounded answer."""
    context = "\n\n".join(
        f"[{d['id']}] {d['title']} (Source: {d['source']})\n{d['text']}" for d in retrieved_docs
    )

    prompt = f"""You are an SME compliance assistant. Answer the business owner's question
using ONLY the regulatory context provided below. Cite the specific regulation ID(s) you
used as evidence. If the context doesn't fully answer the question, say so explicitly.
Do not invent thresholds or requirements not present in the context.

CONTEXT:
{context}

QUESTION: {query}

Respond in this format:
Finding: <your finding>
Reason: <why, referencing the business facts in the question>
Evidence: <regulation ID(s) and source>
"""

    if not GEMINI_API_KEY:
        return (
            "[No GEMINI_API_KEY set — showing retrieved context only. "
            "Set GEMINI_API_KEY to see the generated answer.]\n\n" + context
        )

    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(prompt)
    return response.text


def main():
    print("=" * 70)
    print("SME COMPLIANCE ASSISTANT — RAG MINI-DEMO")
    print("=" * 70)

    print("\n[1] Building knowledge base from regulatory snippets...")
    collection = build_knowledge_base()
    bm25 = build_bm25_index()
    print(f"    Loaded {len(REGULATIONS)} regulatory snippets into vector + BM25 index.")

    query = "My business has an annual turnover of 50 lakh rupees and 8 employees. What registrations or compliances apply to me?"
    print(f"\n[2] Query: {query}")

    print("\n[3] Retrieving relevant regulations (hybrid: vector + BM25)...")
    retrieved = hybrid_retrieve(query, collection, bm25, top_k=3)
    for r in retrieved:
        print(f"    - [{r['id']}] {r['title']}")

    print("\n[4] Generating evidence-grounded answer...")
    answer = generate_answer(query, retrieved)
    print("\n" + "-" * 70)
    print(answer)
    print("-" * 70)


if __name__ == "__main__":
    main()