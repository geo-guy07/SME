import os, json
from pathlib import Path
from typing import Optional
import chromadb
from rank_bm25 import BM25Okapi

CHROMA_DB_PATH = str(Path(__file__).parent / "chroma_db")
COLLECTION_NAME = "sme_regulations"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")


class GeminiEmbeddingFunction:
    def __init__(self, api_key):
        from google import genai
        self._client = genai.Client(api_key=api_key)
    def name(self):
        return "google-gemini-embedding-001"
    def __call__(self, input):
        from google.genai import types
        result = self._client.models.embed_content(
            model="gemini-embedding-001",
            contents=input,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )
        return [e.values for e in result.embeddings]
    def embed_query(self, input):
        from google.genai import types
        result = self._client.models.embed_content(
            model="gemini-embedding-001",
            contents=input,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
        )
        return [e.values for e in result.embeddings]


def _get_embedding_function():
    if GEMINI_API_KEY:
        print("  [Embeddings] Using Google text-embedding-004")
        return GeminiEmbeddingFunction(api_key=GEMINI_API_KEY)
    from chromadb.utils import embedding_functions
    print("  [Embeddings] No GEMINI_API_KEY -- using local all-MiniLM-L6-v2")
    return embedding_functions.DefaultEmbeddingFunction()


def _make_metadata(doc):
    return {
        "title": doc.get("title", ""),
        "source": doc.get("source", ""),
        "category": doc.get("category", ""),
        "effective_date": doc.get("effective_date", ""),
        "applicability_states": json.dumps(doc.get("applicability_states", ["all"])),
        "tags": json.dumps(doc.get("tags", [])),
    }


class VectorStore:
    """Persistent ChromaDB vector store with hybrid BM25 + dense retrieval."""

    def __init__(self, db_path=CHROMA_DB_PATH, collection_name=COLLECTION_NAME):
        self.db_path = db_path
        self.collection_name = collection_name
        self._documents = []
        self._bm25 = None
        print("  [VectorStore] Connecting to ChromaDB at:", db_path)
        self._client = chromadb.PersistentClient(path=db_path)
        self._embed_fn = _get_embedding_function()
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            embedding_function=self._embed_fn,
            metadata={"hnsw:space": "cosine"},
        )
        print("  [VectorStore] Collection ready --", self._collection.count(), "docs stored.")

    def ingest(self, documents, overwrite=False):
        if overwrite:
            self._client.delete_collection(self.collection_name)
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name, embedding_function=self._embed_fn,
                metadata={"hnsw:space": "cosine"})
        existing_ids = set(self._collection.get()["ids"])
        new_docs = [d for d in documents if d["id"] not in existing_ids]
        if not new_docs:
            print("  [VectorStore] All", len(documents), "docs already stored. Skipping.")
        else:
            print("  [VectorStore] Ingesting", len(new_docs), "new documents...")
            self._collection.add(
                ids=[d["id"] for d in new_docs],
                documents=[d["text"] for d in new_docs],
                metadatas=[_make_metadata(d) for d in new_docs],
            )
            print("  [VectorStore] Done. Total:", self._collection.count())
        self._documents = documents
        self._bm25 = BM25Okapi([d["text"].lower().split() for d in documents])
        return len(new_docs)

    def search(self, query, top_k=5, category_filter=None, hybrid=True):
        where = {"category": category_filter} if category_filter else None
        n_fetch = min(top_k * 2, self._collection.count())
        vr = self._collection.query(query_texts=[query], n_results=n_fetch, where=where)
        vids = vr["ids"][0]
        vdists = vr["distances"][0]
        id_vscore = {did: 1.0 - dist for did, dist in zip(vids, vdists)}
        bids, id_bscore = [], {}
        if hybrid and self._bm25:
            scores = self._bm25.get_scores(query.lower().split())
            mx = max(scores) if max(scores) > 0 else 1.0
            for i in sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:n_fetch]:
                doc = self._documents[i]
                if category_filter and doc.get("category") != category_filter:
                    continue
                bids.append(doc["id"])
                id_bscore[doc["id"]] = scores[i] / mx
        id_to_doc = {d["id"]: d for d in self._documents}
        scored = []
        for did in dict.fromkeys(vids + bids):
            if did not in id_to_doc:
                continue
            vs = id_vscore.get(did, 0.0)
            bs = id_bscore.get(did, 0.0)
            doc = dict(id_to_doc[did])
            doc["score"] = round(0.6 * vs + 0.4 * bs, 4)
            doc["vector_score"] = round(vs, 4)
            doc["bm25_score"] = round(bs, 4)
            scored.append(doc)
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def count(self):
        return self._collection.count()

    def get_all_ids(self):
        return self._collection.get()["ids"]

    def clear(self):
        self._client.delete_collection(self.collection_name)
        print("  [VectorStore] Collection cleared.")

    def __repr__(self):
        return "VectorStore(docs=" + str(self.count()) + ")"


if __name__ == "__main__":
    from rag.regulations import REGULATIONS

    print("=" * 60)
    print("SME COMPLIANCE -- VECTOR STORE SETUP TEST")
    print("=" * 60)

    store = VectorStore()
    store.ingest(REGULATIONS)

    print("  Total docs:", store.count())
    print("  IDs:", store.get_all_ids())

    query = "My business turnover is 50 lakh. Do I need GST registration?"
    print("\nQuery:", query)
    print("-" * 60)
    for r in store.search(query, top_k=3):
        print(" [" + r["id"] + "]", r["title"])
        print("      Score:", r["score"], " (vec=" + str(r["vector_score"]) + " | bm25=" + str(r["bm25_score"]) + ")")
        print("     ", r["text"][:100], "...")
        print()

    print("=" * 60)
    print("Vector store persisted to ./chroma_db/")
    print("Run again -- will load from disk, no re-ingesting.")
    print("=" * 60)
