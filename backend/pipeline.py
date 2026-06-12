"""
Core AI Processing Pipeline.

Given raw legal source text for a topic, this module orchestrates the
automated generation of:
    1. Short description (for homepage card)
    2. AI-generated summary (<=250 words, simplified)
    3. Key information extraction (rights, provisions, penalties, who benefits)

All content is produced by prompting Mistral AI on the raw source text —
nothing here is manually written per-topic.
"""
import hashlib

from backend.mistral_client import chat_completion_json
from backend.rag_store import index_topic, is_topic_indexed
from backend.source_fetcher import fetch_topic_source
from backend.config import RAW_SOURCES_DIR, TOPICS


SYSTEM_PROMPT = """You are a legal content simplification engine for "LegalX", \
an AI-powered legal knowledge platform for ordinary, non-legal users in India.

Given raw legal source text about a law/act, you must analyze it and produce \
a structured JSON object that will populate a "Knowledge Centre" card.

Rules:
- Use ONLY the information present in the provided source text. Do not invent facts.
- Write in plain, simple, friendly language suitable for someone with no legal background.
- Avoid legal jargon where possible; if a legal term must be used, briefly explain it.
- The "summary" field MUST be 250 words or fewer.
- Extract concrete, specific items for the lists (rights, provisions, penalties, who_benefits) \
directly grounded in the source text — do not generate generic boilerplate.
- Return ONLY a valid JSON object matching the schema below, with no extra commentary.

JSON schema:
{
  "short_description": "<one engaging sentence, max ~20 words, for a homepage card>",
  "summary": "<plain-language summary, max 250 words>",
  "key_rights": ["<right 1>", "<right 2>", "..."],
  "important_provisions": ["<provision 1>", "<provision 2>", "..."],
  "penalties": ["<penalty 1>", "<penalty 2>", "..."],
  "who_benefits": ["<group 1>", "<group 2>", "..."]
}
"""


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_raw_source(topic_id: str) -> str:
    """
    Step 1 of the Expected Workflow — "Legal Content Source".

    Attempts a live fetch from the official public source(s) registered in
    backend/source_fetcher.py. Falls back to the last cached snapshot in
    data/raw_sources/ if live fetching fails (e.g. no internet access).
    """
    result = fetch_topic_source(topic_id)
    if result["status"] == "failed":
        # Last resort: try reading the cache path directly
        source_file = TOPICS[topic_id]["source_file"]
        path = RAW_SOURCES_DIR / source_file
        if not path.exists():
            raise FileNotFoundError(
                f"No live source reachable and no cached source found for '{topic_id}' "
                f"(expected at {path})."
            )
        return path.read_text(encoding="utf-8")
    return result["text"]


def generate_knowledge_card(topic_id: str, raw_text: str) -> dict:
    """
    Run the AI pipeline on raw_text and return the structured knowledge card dict.
    """
    topic_name = TOPICS[topic_id]["name"]

    user_prompt = f"""Topic name: {topic_name}

Raw legal source text:
---
{raw_text}
---

Generate the JSON knowledge card as instructed."""

    card = chat_completion_json(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )

    # Basic validation / defaults
    card.setdefault("short_description", "")
    card.setdefault("summary", "")
    card.setdefault("key_rights", [])
    card.setdefault("important_provisions", [])
    card.setdefault("penalties", [])
    card.setdefault("who_benefits", [])

    return card


def process_topic(topic_id: str, force: bool = False) -> dict:
    """
    Full automation step for a single topic:
      1. Load raw source text
      2. Compute a content hash (to detect changes / avoid redundant LLM calls)
      3. Generate the knowledge card via Mistral
      4. Index the raw text into the RAG vector store (if not already indexed)

    Returns: {"card": dict, "source_hash": str, "needs_audio": bool, "raw_text": str}
    """
    raw_text = load_raw_source(topic_id)
    # PDFs from official sources can be long; cap size for prompt/embedding efficiency
    raw_text = raw_text[:30000]
    source_hash = _content_hash(raw_text)

    from backend.database import get_topic_card  # local import to avoid circular import
    existing = get_topic_card(topic_id)

    needs_generation = force or existing is None or existing.get("source_hash") != source_hash

    if needs_generation:
        card = generate_knowledge_card(topic_id, raw_text)
    else:
        card = {
            "short_description": existing["short_description"],
            "summary": existing["summary"],
            "key_rights": existing["key_rights"],
            "important_provisions": existing["important_provisions"],
            "penalties": existing["penalties"],
            "who_benefits": existing["who_benefits"],
        }

    # Index for RAG if not already done (or if content changed)
    if force or not is_topic_indexed(topic_id) or needs_generation:
        index_topic(topic_id, raw_text)

    return {
        "card": card,
        "source_hash": source_hash,
        "needs_audio": needs_generation,
        "raw_text": raw_text,
    }


def process_all_topics(force: bool = False) -> dict:
    """Run the pipeline for every registered topic. Returns a status dict per topic."""
    results = {}
    for topic_id in TOPICS:
        try:
            results[topic_id] = {"status": "ok", **process_topic(topic_id, force=force)}
        except Exception as e:
            results[topic_id] = {"status": "error", "error": str(e)}
    return results