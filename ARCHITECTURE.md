# LegalX AI Knowledge Centre — Architecture

```mermaid
flowchart TD
    A[Raw Legal Source Text<br/>data/raw_sources/*.txt] --> B[AI Processing Pipeline<br/>backend/pipeline.py]
    B --> C[Mistral AI - Chat Completion<br/>JSON-mode structured generation]
    C --> D[Generated Knowledge Card<br/>short_description, summary,<br/>key_rights, provisions,<br/>penalties, who_benefits]
    D --> E[(SQLite DB<br/>topics table)]

    A --> F[Chunking<br/>backend/rag_store.py]
    F --> G[Mistral Embeddings<br/>mistral-embed]
    G --> H[(ChromaDB<br/>Vector Store)]

    D --> I[Audio Generator<br/>gTTS]
    I --> J[(MP3 files<br/>data/audio/)]

    E --> K[Streamlit Homepage<br/>Knowledge Centre Cards]
    K --> L[Streamlit Topic Detail Page]
    L --> M[Summary + Key Info + Audio Player]
    L --> N[AI Legal Assistant - Chat UI]

    N --> O[RAG Retriever<br/>backend/qa_assistant.py]
    O --> H
    O --> P[Mistral AI - Chat Completion<br/>grounded answer + citations]
    P --> Q[(SQLite DB<br/>chat_history table)]
    Q --> N
```

## Flow Summary

1. **Ingestion**: Raw legal text per topic lives in `data/raw_sources/*.txt`.
2. **AI Processing Pipeline** (`backend/pipeline.py`): sends raw text to Mistral AI with a
   strict JSON schema prompt → produces card content (description, summary, key info).
3. **Storage**: Generated cards persisted in SQLite (`data/legalx.db`).
4. **RAG Indexing** (`backend/rag_store.py`): raw text is chunked, embedded via
   `mistral-embed`, and stored in a persistent ChromaDB collection.
5. **Audio Generation** (`backend/audio_generator.py`): summary text converted to MP3
   via gTTS, cached on disk.
6. **Frontend** (Streamlit): homepage lists auto-generated cards; topic detail page shows
   summary, key info tabs, audio player/download, and an AI Legal Assistant chat.
7. **AI Legal Assistant** (`backend/qa_assistant.py`): retrieves top-k relevant chunks for
   the user's question (scoped to the selected topic), builds a grounded prompt, and asks
   Mistral to answer using only that context — with source chunk citations and chat history.
