"""
Source Fetcher — "Legal Content Source" step of the Expected Workflow.

This module implements the FIRST step of the pipeline diagram in the assessment:

    Legal Content Source -> AI Processing Pipeline -> ...

It downloads raw legal reference material from official / public government
sources (PDFs from indiacode.nic.in, meity.gov.in, cic.gov.in, ncdrc.nic.in,
gstcouncil.gov.in, etc.), extracts plain text from the PDFs, and writes it to
data/raw_sources/<topic_id>.txt.

This text then feeds into backend/pipeline.py, which performs ALL summarization,
key-information extraction, and card generation via Mistral AI. No legal content
on the cards/summaries/Q&A is manually written — only this raw upstream corpus is
fetched from the web, exactly as described in the assessment's "Expected Workflow"
(Legal Content Source as Step 1).

If a live fetch fails (e.g. no internet access, source URL temporarily down), the
pipeline falls back to whatever is already cached in data/raw_sources/<topic_id>.txt
from a previous successful fetch, so the system keeps working offline.
"""
import io
import requests
from pypdf import PdfReader

from backend.config import RAW_SOURCES_DIR, TOPICS


# Official / public government source URLs for each topic.
# These are the "Legal Content Source" referenced in the assessment's workflow diagram.
SOURCES = {
    "pocso_act": [
        "https://www.indiacode.nic.in/bitstream/123456789/2188/1/A2012-32.pdf",
        "https://bhubaneswarcuttackpolice.gov.in/wp-content/uploads/2020/08/POCSO-ACT.pdf",
    ],
    "consumer_protection_act": [
        "https://ncdrc.nic.in/bare_acts/CPA2019.pdf",
        "https://www.indiacode.nic.in/bitstream/123456789/15256/1/a2019-35.pdf",
    ],
    "cyber_crime_laws": [
        "https://www.meity.gov.in/static/uploads/2024/03/ITbill_2000.pdf",
        "https://www.indiacode.nic.in/bitstream/123456789/13116/1/it_act_2000_updated.pdf",
    ],
    "rti_act": [
        "https://cic.gov.in/sites/default/files/RTI-Act_English.pdf",
        "https://rti.gov.in/rti-act.pdf",
    ],
    "gst_registration": [
        "https://gstcouncil.gov.in/sites/default/files/e-version-gst-flyers/Registration_under_GST_Law_new.pdf",
    ],
}

USER_AGENT = "Mozilla/5.0 (compatible; LegalXKnowledgeCentreBot/1.0; +educational-project)"
MIN_USABLE_CHARS = 500  # minimum extracted text length to consider a fetch "successful"


def _extract_pdf_text(pdf_bytes: bytes, max_pages: int = 40) -> str:
    """Extract plain text from PDF bytes (limits pages to keep prompts manageable)."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    texts = []
    for i, page in enumerate(reader.pages):
        if i >= max_pages:
            break
        try:
            texts.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(texts)


def _clean_text(text: str) -> str:
    """Light cleanup of PDF-extracted text: collapse excess whitespace/newlines."""
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def fetch_topic_source(topic_id: str, timeout: int = 20) -> dict:
    """
    Attempt to download and extract raw text for a topic from its official source URL(s).

    Returns:
        {
          "status": "fetched" | "cached" | "failed",
          "text": str,          # the resulting raw text (fetched or cached)
          "source_url": str|None,
          "cached_path": str
        }
    """
    cached_path = RAW_SOURCES_DIR / TOPICS[topic_id]["source_file"]
    urls = SOURCES.get(topic_id, [])

    for url in urls:
        try:
            resp = requests.get(
                url,
                timeout=timeout,
                headers={"User-Agent": USER_AGENT},
            )
            resp.raise_for_status()

            content_type = resp.headers.get("Content-Type", "")
            if "pdf" in content_type.lower() or url.lower().endswith(".pdf"):
                raw_text = _extract_pdf_text(resp.content)
            else:
                raw_text = resp.text

            raw_text = _clean_text(raw_text)

            if len(raw_text) >= MIN_USABLE_CHARS:
                cached_path.parent.mkdir(parents=True, exist_ok=True)
                cached_path.write_text(raw_text, encoding="utf-8")
                return {
                    "status": "fetched",
                    "text": raw_text,
                    "source_url": url,
                    "cached_path": str(cached_path),
                }
        except Exception:
            continue  # try next URL in the list

    # All live sources failed -> fall back to cached snapshot, if any
    if cached_path.exists():
        return {
            "status": "cached",
            "text": cached_path.read_text(encoding="utf-8"),
            "source_url": None,
            "cached_path": str(cached_path),
        }

    return {"status": "failed", "text": "", "source_url": None, "cached_path": str(cached_path)}


def fetch_all_sources() -> dict:
    """Run fetch_topic_source for every registered topic. Returns a status dict per topic."""
    results = {}
    for topic_id in TOPICS:
        results[topic_id] = fetch_topic_source(topic_id)
    return results