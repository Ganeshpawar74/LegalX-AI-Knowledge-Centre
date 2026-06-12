"""
RAG vector store layer.

- Chunks raw legal source text
- Embeds chunks with Mistral embeddings
- Stores/queries them in a persistent ChromaDB collection (one per topic,
  plus ability to query across all topics)
"""
import chromadb
from chromadb.config import Settings

from backend.config import VECTORSTORE_DIR, CHUNK_SIZE, CHUNK_OVERLAP, RAG_TOP_K
from backend.mistral_client import embed_texts

_client = None


def get_chroma_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=str(VECTORSTORE_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def get_collection():
    """Single collection holding chunks from all topics, filtered via metadata."""
    client = get_chroma_client()
    return client.get_or_create_collection(name="legalx_chunks")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Simple sliding-window character chunker that tries to break on sentence boundaries."""
    text = text.strip().replace("\n\n", "\n")
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        # try to extend to the next sentence end (period) for cleaner chunks
        if end < n:
            next_period = text.find(". ", end)
            if next_period != -1 and next_period - end < 200:
                end = next_period + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks


def index_topic(topic_id: str, raw_text: str) -> int:
    """
    Chunk + embed + store all chunks for a given topic.
    Removes any previously indexed chunks for that topic first (idempotent re-indexing).
    """
    collection = get_collection()

    # Remove old chunks for this topic
    existing = collection.get(where={"topic_id": topic_id})
    if existing and existing.get("ids"):
        collection.delete(ids=existing["ids"])

    chunks = chunk_text(raw_text)
    if not chunks:
        return 0

    embeddings = embed_texts(chunks)
    ids = [f"{topic_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"topic_id": topic_id, "chunk_index": i} for i in range(len(chunks))]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )
    return len(chunks)


def retrieve_context(topic_id: str, query: str, top_k: int = RAG_TOP_K) -> list[dict]:
    """
    Retrieve the top_k most relevant chunks for a query, scoped to a single topic.
    Returns list of {"text": ..., "chunk_id": ..., "distance": ...}
    """
    collection = get_collection()
    query_embedding = embed_texts([query])[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where={"topic_id": topic_id},
    )

    output = []
    if not results["ids"] or not results["ids"][0]:
        return output

    for i in range(len(results["ids"][0])):
        output.append({
            "chunk_id": results["ids"][0][i],
            "text": results["documents"][0][i],
            "distance": results["distances"][0][i] if results.get("distances") else None,
        })
    return output


def is_topic_indexed(topic_id: str) -> bool:
    collection = get_collection()
    existing = collection.get(where={"topic_id": topic_id}, limit=1)
    return bool(existing and existing.get("ids"))
