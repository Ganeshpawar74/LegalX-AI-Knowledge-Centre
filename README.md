# LegalX AI Knowledge Centre

An AI-powered Legal Knowledge Centre that **automatically generates** legal knowledge
cards — summaries, key information, audio explanations, and a RAG-based Q&A assistant —
from raw legal source text, using **Mistral AI**.


---

## 1. Project Overview

LegalX aims to make legal information accessible to everyone. This project implements a
simplified Knowledge Centre covering 5 legal topics:

1. POCSO Act
2. Consumer Protection Act, 2019
3. Cyber Crime Laws (IT Act)
4. Right to Information (RTI) Act, 2005
5. GST Registration

For each topic, the system **automatically** processes raw legal source text and
generates:

- **Feature 1** — A homepage knowledge card (topic name + AI-generated short description)
- **Feature 2** — A plain-language summary (\u2264 250 words)
- **Feature 3** — Extracted key information: Key Rights, Important Provisions,
  Penalties, Who Can Benefit
- **Feature 4** — An AI Legal Assistant that answers user questions using
  **RAG (Retrieval-Augmented Generation)** with source citations and chat history
- **Feature 5** — An audio version of the summary (play + download), generated via gTTS

**Nothing is hardcoded or manually written** — all card content, summaries, key info,
and Q&A answers are generated at runtime by the AI pipeline from the raw source text in
`data/raw_sources/`.

---

## 2. Architecture

See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for a full diagram and flow description.

**High-level flow:**

```
Raw Legal Text  →  Mistral AI (JSON generation)  →  SQLite (knowledge cards)
       ↓
   Chunking + Mistral Embeddings  →  ChromaDB (RAG vector store)
       ↓
   gTTS Audio Generation  →  MP3 files

Streamlit UI:
  Homepage (hero + cards) → Topic Detail (summary, key info tabs, audio, AI assistant)
  AI Assistant → RAG retrieval (ChromaDB) → Mistral AI grounded answer → SQLite chat history
```

---

## 3. AI Models Used

| Purpose | Model |
|---|---|
| Knowledge card generation (summary, key info extraction) | `mistral-large-latest` (via Mistral AI Chat API, JSON mode) |
| Embeddings for RAG vector store | `mistral-embed` |
| AI Legal Assistant (RAG-grounded Q&A) | `mistral-large-latest` |
| Audio generation | gTTS (Google Text-to-Speech) |

Model names are configurable via `.env` (`MISTRAL_MODEL`, `MISTRAL_EMBED_MODEL`).

---

## 4. Technologies Used

- **Language**: Python 3.10+
- **LLM**: Mistral AI (`mistralai` SDK)
- **Vector Database**: ChromaDB (persistent, local)
- **Database**: SQLite (knowledge cards + chat history)
- **Frontend**: Streamlit (multi-page app, with custom CSS for a polished UI)
- **Text-to-Speech**: gTTS
- **Config**: python-dotenv

---

## 5. Project Structure

```
legalx-ai/
├── backend/
│   ├── config.py          # Paths, topics registry, constants
│   ├── database.py         # SQLite layer (topics, chat_history)
│   ├── mistral_client.py   # Mistral chat + embeddings wrapper
│   ├── rag_store.py         # Chunking, embedding, ChromaDB RAG store
│   ├── pipeline.py          # AI processing pipeline (card generation)
│   ├── audio_generator.py   # gTTS audio generation
│   ├── source_fetcher.py     # Legal Content Source (live fetch + cache fallback)
│   └── qa_assistant.py       # RAG-based AI Legal Assistant
├── frontend/
│   ├── app.py                # Homepage: hero banner, pipeline trigger, topic cards grid
│   └── pages/
│       └── 1_Topic_Detail.py # Summary, key info tabs, audio card, AI assistant chat
├── data/
│   ├── raw_sources/*.txt     # Input legal source text (per topic)
│   ├── audio/                # Generated MP3 audio files
│   └── legalx.db             # SQLite database (generated)
├── vectorstore/              # ChromaDB persistent storage (generated)
├── run_pipeline.py           # CLI: run the full automation pipeline
├── requirements.txt
├── .env.example
└── ARCHITECTURE.md
```

---

## 6. Frontend (Streamlit UI)

### Homepage (`frontend/app.py`)

- A gradient hero banner introducing LegalX and the AI pipeline.
- If any topics haven't been processed yet, a warning banner lists them and a
  **"Run AI Processing Pipeline"** button triggers `process_topic`, `generate_audio`,
  and `upsert_topic_card` for each missing topic, with a progress bar.
- A "Legal Topics" section showing an indexed count and a responsive 3-column grid of
  topic cards (AI-Generated badge, name, short description, "Read More" button).
  Clicking "Read More" sets `st.session_state["selected_topic"]` and navigates to the
  detail page via `st.switch_page`.

### Topic Detail Page (`frontend/pages/1_Topic_Detail.py`)

- **Header**: topic name, short description, and a "Home" back button.
- **Summary panel** (Feature 2): the AI-generated plain-language summary with a word
  count and generation caption.
- **Key Information tabs** (Feature 3): four tabs — Key Rights, Important Provisions,
  Penalties, Who Can Benefit — each rendered as a styled list, with empty-state
  messages if no items were extracted.
- **Audio Summary sidebar** (Feature 5): an audio player and download button for the
  generated MP3, plus metadata about when the card was generated and the
  generation pipeline used.
- **AI Legal Assistant** (Feature 4): a gradient-headed chat section with an example
  question hint, a scrollable chat history (`st.chat_message`), per-answer source
  citations in an expander, a chat input box, and a "Clear chat history" button.

### Styling

Both pages share a consistent visual identity — a blue gradient hero/header, white
card panels with soft shadows and rounded corners — implemented via scoped CSS injected
with `st.markdown(..., unsafe_allow_html=True)`. The layout is responsive: card grids,
hero padding, and the assistant section adapt for narrower viewports via CSS media
queries. No backend contracts, function signatures, or data shapes were changed to
support the UI.

---

## 6.5 Legal Content Source (Step 1 of the Pipeline)

Per the assessment's "Expected Workflow", **Legal Content Source** is Step 1, feeding
into the AI Processing Pipeline. This is implemented in `backend/source_fetcher.py`:

- On each pipeline run, the system attempts a **live download** of the official Act/
  guidance document from government sources (`indiacode.nic.in`, `meity.gov.in`,
  `cic.gov.in`, `ncdrc.nic.in`, `gstcouncil.gov.in`), extracts text from the PDF, and
  saves it to `data/raw_sources/<topic>.txt`.
- If the live fetch fails (no internet, source temporarily down), the pipeline
  automatically falls back to the last successfully cached snapshot in
  `data/raw_sources/`.
- **Everything downstream of this raw text — short description, summary, key rights,
  provisions, penalties, who-benefits, and Q&A answers — is generated entirely by
  Mistral AI.** No legal content is manually written by the developer; only the raw
  input corpus is sourced (live, when possible) from official government publications.

---

## 7. Setup Instructions

### Step 1 — Clone & install dependencies

```bash
git clone <repo-url>
cd legalx-ai
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2 — Configure environment variables

Copy `.env.example` to `.env` and add your Mistral API key:

```bash
cp .env.example .env
```

```env
MISTRAL_API_KEY=your_mistral_api_key_here
MISTRAL_MODEL=mistral-large-latest
MISTRAL_EMBED_MODEL=mistral-embed
```

### Step 3 — Run the AI Processing Pipeline

This generates all knowledge cards, indexes content for RAG, and generates audio:

```bash
python run_pipeline.py
```

Options:
- `python run_pipeline.py --force` — regenerate everything even if unchanged
- `python run_pipeline.py --topic pocso_act` — process a single topic

> You can also trigger this pipeline directly from the Streamlit homepage if any
> topics haven't been processed yet.

### Step 4 — Launch the Streamlit app

```bash
cd frontend
streamlit run app.py
```

Open the URL shown in the terminal (typically `http://localhost:8501`).

---

## 8. Explanation of the Automation Pipeline

1. **Source ingestion (live fetch)**: `backend/source_fetcher.py` downloads the
   official Act/document PDF from a government source (indiacode.nic.in, meity.gov.in,
   cic.gov.in, ncdrc.nic.in, gstcouncil.gov.in) and extracts text via `pypdf`. If the
   live fetch fails, the last cached snapshot in `data/raw_sources/` is used instead.
2. **Content hashing**: `backend/pipeline.py` computes a SHA-256 hash of the source
   text. If the hash matches what's already stored, the LLM call is skipped
   (avoids redundant generation — automation with caching).
3. **Structured generation**: The raw text is sent to Mistral AI (`mistral-large-latest`)
   with a system prompt enforcing a strict JSON schema (short description, summary
   \u2264250 words, key rights, provisions, penalties, who benefits). JSON mode ensures
   reliable parsing.
4. **RAG indexing**: The raw text is chunked (char-based sliding window with sentence-
   boundary snapping), embedded via `mistral-embed`, and upserted into a ChromaDB
   collection scoped by `topic_id`.
5. **Audio generation**: The generated summary is converted to MP3 via gTTS. Audio is
   cached by content hash so it's only regenerated when the summary text changes.
6. **Persistence**: The final card (description, summary, key info, audio path,
   source hash, timestamp) is upserted into SQLite.
7. **Serving**: The Streamlit homepage reads all cards from SQLite and renders them as
   topic cards. The topic detail page renders the summary panel, key info tabs, audio
   card, and assistant chat.
8. **AI Legal Assistant (RAG)**: User questions are embedded, the top-k most relevant
   chunks for that topic are retrieved from ChromaDB, and Mistral generates an answer
   grounded strictly in those chunks — with chunk IDs shown as source citations, and
   full conversational history stored in SQLite per topic.

---

## 9. Feature-to-Requirement Mapping

| PDF Requirement | Implementation |
|---|---|
| Feature 1 — Automated Knowledge Centre (homepage cards) | `frontend/app.py` — hero banner + responsive card grid, generated from `backend/pipeline.py` output stored in SQLite |
| Feature 2 — AI Generated Summary (\u2264250 words) | `backend/pipeline.py` (Mistral JSON generation) + enforced via prompt, displayed in the summary panel |
| Feature 3 — Key Information Extraction | Same pipeline call, extracts `key_rights`, `important_provisions`, `penalties`, `who_benefits`, displayed as tabs |
| Feature 4 — AI Legal Assistant | `backend/qa_assistant.py` — RAG via ChromaDB + Mistral, with chat history (SQLite), rendered as a chat UI |
| Feature 4 (Bonus) — RAG | ChromaDB + `mistral-embed` (`backend/rag_store.py`) |
| Feature 5 — Audio Summary (play/download) | `backend/audio_generator.py` (gTTS) + Streamlit audio player & download button in the sidebar audio card |
| Bonus — Source Citations | Retrieved chunk IDs shown in "Sources used" expander in chat |
| Bonus — Chat History | `chat_history` table in SQLite, per topic |
| Bonus — AI Search / Vector DB | ChromaDB persistent vector store |
| Automation Pipeline | `run_pipeline.py` + content-hash based caching, no manual content |

---

## 10. Challenges Faced

- **Ensuring strict word limits** (\u2264250 words) from an LLM required explicit prompt
  constraints and JSON-mode output to keep responses structured and parseable.
- **Avoiding hardcoded content** while still needing *some* raw legal text as input —
  resolved by clearly separating "raw source corpus" (factual, unprocessed input data)
  from "AI-generated output" (cards, summaries, key info, answers), all of which are
  produced by the pipeline, not manually written.
- **RAG grounding** — preventing the assistant from hallucinating answers outside the
  selected topic's context required scoping ChromaDB queries by `topic_id` and strict
  system-prompt instructions to only use retrieved context.
- **Idempotent pipeline runs** — using content hashing so re-running the pipeline
  doesn't waste API calls or regenerate unchanged audio.
- **UI/UX polish without touching backend contracts** — the frontend was restyled
  (gradient hero, card grid, tabbed key info, chat interface) using scoped CSS only,
  keeping all function signatures, session-state keys, and database calls unchanged.

---

## 11. Future Improvements

- Add authentication (per-user chat history, saved topics)
- Add speech-to-text for voice-based questions to the AI Legal Assistant
- Multi-language support (Hindi and regional languages) for summaries and audio
- Dockerize the application for one-command deployment
- Deploy to Streamlit Community Cloud / a cloud VM with persistent volume for SQLite + ChromaDB
- Expand topic coverage by adding more `.txt` sources to `data/raw_sources/` —
  the pipeline automatically picks up new topics added to `backend/config.py`
- Add a feedback mechanism for AI Legal Assistant answer quality
- Migrate to PostgreSQL + pgvector for production-scale deployment

---

## 12. Important Notes

- **API Key**: Add your Mistral API key to `.env` (never commit it — see `.gitignore`).
- **Disclaimer**: This system provides general legal information for educational
  purposes and is **not a substitute for professional legal advice**.