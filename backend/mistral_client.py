"""
Thin wrapper around the Mistral AI client.

Centralizes:
- Chat completion calls (for summary / extraction / Q&A generation)
- Embedding calls (for RAG vector store)
- JSON-mode parsing helper for structured outputs
"""
import json
import re
from mistralai import Mistral

from backend.config import MISTRAL_API_KEY, MISTRAL_MODEL, MISTRAL_EMBED_MODEL


def _client() -> Mistral:
    if not MISTRAL_API_KEY:
        raise RuntimeError(
            "MISTRAL_API_KEY is not set. Please add it to your .env file."
        )
    return Mistral(api_key=MISTRAL_API_KEY)


def chat_completion(messages: list[dict], temperature: float = 0.3, json_mode: bool = False) -> str:
    """
    Call Mistral chat completion.
    messages: list of {"role": "system"|"user"|"assistant", "content": str}
    """
    client = _client()
    kwargs = {
        "model": MISTRAL_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.complete(**kwargs)
    return response.choices[0].message.content


def chat_completion_json(messages: list[dict], temperature: float = 0.2) -> dict:
    """Call Mistral and parse a JSON object response, with fallback cleanup."""
    raw = chat_completion(messages, temperature=temperature, json_mode=True)
    return _safe_json_parse(raw)


def _safe_json_parse(raw: str) -> dict:
    raw = raw.strip()
    # Strip markdown code fences if present
    raw = re.sub(r"^```(json)?", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract the largest {...} block
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Get embeddings for a list of texts using Mistral's embedding model."""
    client = _client()
    response = client.embeddings.create(
        model=MISTRAL_EMBED_MODEL,
        inputs=texts,
    )
    return [item.embedding for item in response.data]
