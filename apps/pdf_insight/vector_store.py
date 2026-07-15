"""
Vector store for the PDF Health Insight app, fully self-contained.

Uses its own Chroma collection ("pdf_insight_reports") so this app does
not depend on wellness_rag's internals. Each chunk is tagged with user_id
and report_id in its metadata; queries always filter on user_id so a
mother only ever retrieves her own report content.
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
def _reports_collection():
    return _chroma_client().get_or_create_collection("pdf_insight_reports")


def ingest_report_chunks(user_id, report_id, chunks):
    """
    chunks: list of plain text strings (from chunking.chunk_text), covering
    either the full extracted report text or structured "label: value"
    lines. Each becomes its own searchable, user-scoped chunk.
    """
    if not chunks:
        return
    collection = _reports_collection()
    ids = [f"user{user_id}-report{report_id}-{i}" for i in range(len(chunks))]
    embeddings = embed_texts(chunks)
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=[
            {"user_id": str(user_id), "report_id": str(report_id)}
            for _ in chunks
        ],
    )


def query_report_chunks(query_text, user_id, top_k=5):
    """
    Retrieves the most relevant chunks from this mother's own reports only.
    Always scoped by user_id -- mothers never see each other's data.
    """
    collection = _reports_collection()
    if collection.count() == 0:
        return []

    query_embedding = embed_texts([query_text])[0]
    try:
        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"user_id": str(user_id)},
        )
    except Exception:
        return []

    docs = result.get("documents", [[]])[0]
    metas = result.get("metadatas", [[]])[0]
    dists = result.get("distances", [[]])[0]
    return [
        {"text": doc, "report_id": meta.get("report_id"), "distance": dist}
        for doc, meta, dist in zip(docs, metas, dists)
    ]


def delete_report_chunks(report_id):
    """Optional: call this if a mother deletes an uploaded report, so
    stale chunks don't linger in the vector store."""
    collection = _reports_collection()
    collection.delete(where={"report_id": str(report_id)})