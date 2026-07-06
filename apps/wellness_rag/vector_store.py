"""
Vector store for the wellness RAG engine, using two separate Chroma
collections:

- "maternal_knowledge" -- public, shared source material (WHO/NHS/PubMed
  excerpts you've scraped and chunked yourself, via the ingest_knowledge
  management command). Same content, visible to every mother.

- "user_reports" -- private, per-mother chunks generated automatically
  from each mother's own uploaded PDF reports (see pdf_insight). Every
  chunk is tagged with user_id in its metadata, and queries always filter
  on that id, so mothers never see each other's report data.
"""
from django.conf import settings
from functools import lru_cache


@lru_cache(maxsize=1)
def get_embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(settings.EMBEDDING_MODEL_NAME)


def embed_texts(texts):
    model = get_embedder()
    return model.encode(texts, convert_to_numpy=True).tolist()


@lru_cache(maxsize=1)
def _chroma_client():
    import chromadb
    return chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)


@lru_cache(maxsize=1)
def _public_collection():
    return _chroma_client().get_or_create_collection("maternal_knowledge")


@lru_cache(maxsize=1)
def _reports_collection():
    return _chroma_client().get_or_create_collection("user_reports")


# ---- Public knowledge base (WHO/NHS/etc -- shared by everyone) -----------

def ingest_chunks(chunks):
    """
    chunks: list of dicts -- id (str, unique), text (str), source_url (str),
    source_name (str). Feed this from your own scraper output via the
    `ingest_knowledge` management command.
    """
    if not chunks:
        return
    collection = _public_collection()
    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)
    collection.upsert(
        ids=[c["id"] for c in chunks],
        embeddings=embeddings,
        documents=texts,
        metadatas=[
            {"source_url": c.get("source_url", ""), "source_name": c.get("source_name", "")}
            for c in chunks
        ],
    )


def query_knowledge(query_text, top_k=4):
    collection = _public_collection()
    if collection.count() == 0:
        return []
    query_embedding = embed_texts([query_text])[0]
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
    )
    hits = []
    for doc, meta, dist in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
        hits.append({
            "text": doc,
            "source_url": meta.get("source_url", ""),
            "source_name": meta.get("source_name", ""),
            "distance": dist,
        })
    return hits


# ---- Personal knowledge base (each mother's own uploaded reports) -------

def ingest_report_chunks(user_id, report_id, items):
    """
    items: the `extracted_data` list from pdf_summarizer.summarize_report,
    e.g. [{"label": "Hemoglobin", "value": "9.1 g/dL"}, ...]. Each becomes
    its own searchable chunk, tagged with the owning user_id.
    """
    if not items:
        return
    collection = _reports_collection()
    texts = [f"{item['label']}: {item['value']}" for item in items]
    ids = [f"user{user_id}-report{report_id}-{i}" for i in range(len(items))]
    embeddings = embed_texts(texts)
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=[
            {"user_id": str(user_id), "report_id": str(report_id), "source_name": "Your medical report"}
            for _ in items
        ],
    )


def query_user_reports(query_text, user_id, top_k=3):
    collection = _reports_collection()
    query_embedding = embed_texts([query_text])[0]
    try:
        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"user_id": str(user_id)},
        )
    except Exception:
        # e.g. this user has fewer report chunks than top_k, or none yet
        return []

    docs = result.get("documents", [[]])[0]
    metas = result.get("metadatas", [[]])[0]
    dists = result.get("distances", [[]])[0]
    return [
        {"text": doc, "source_url": "", "source_name": meta.get("source_name", "Your medical report"), "distance": dist}
        for doc, meta, dist in zip(docs, metas, dists)
    ]