"""
Feature 4 — AI Legal Assistant (RAG-based Q&A)

For a given topic and user question:
  1. Retrieve the most relevant chunks of the topic's source text via the
     vector store (RAG).
  2. Build a grounded prompt containing only those chunks + recent chat history.
  3. Ask Mistral to answer using only that context, and cite which chunks
     were used (source citations).
"""
from backend.mistral_client import chat_completion
from backend.rag_store import retrieve_context
from backend.config import TOPICS


SYSTEM_PROMPT_TEMPLATE = """You are the LegalX AI Legal Assistant, helping a non-legal \
user understand "{topic_name}" in India.

You must answer the user's question using ONLY the "Retrieved Context" provided below, \
which comes from the official source text for this topic. 

Guidelines:
- Be clear, simple, and supportive — avoid heavy legal jargon.
- If the answer is not contained in the retrieved context, say that you don't have \
enough information on that specific point, and suggest the user consult the full Act \
or a qualified legal professional. Do NOT make up legal facts.
- Keep answers concise (3-6 sentences) unless the question requires more detail.
- This is general legal information, not legal advice — you may note this briefly if relevant.

Retrieved Context:
---
{context}
---
"""


def answer_question(topic_id: str, question: str, chat_history: list[dict] | None = None) -> dict:
    """
    Returns: {"answer": str, "sources": [chunk_ids], "retrieved_chunks": [...]}
    """
    topic_name = TOPICS[topic_id]["name"]

    retrieved = retrieve_context(topic_id, question)
    if not retrieved:
        context_text = "No relevant context found."
    else:
        context_text = "\n\n".join(
            f"[Source chunk {r['chunk_id']}]: {r['text']}" for r in retrieved
        )

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(topic_name=topic_name, context=context_text)

    messages = [{"role": "system", "content": system_prompt}]

    # Include recent chat history for conversational continuity (last 6 turns)
    if chat_history:
        for turn in chat_history[-6:]:
            role = "assistant" if turn["role"] == "assistant" else "user"
            messages.append({"role": role, "content": turn["content"]})

    messages.append({"role": "user", "content": question})

    answer = chat_completion(messages, temperature=0.3)

    sources = [r["chunk_id"] for r in retrieved]
    return {"answer": answer, "sources": sources, "retrieved_chunks": retrieved}
