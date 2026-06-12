"""
Central configuration for the LegalX AI Knowledge Centre.
Loads environment variables and defines shared paths/constants.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ---- Paths ----
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_SOURCES_DIR = DATA_DIR / "raw_sources"
AUDIO_DIR = DATA_DIR / "audio"
VECTORSTORE_DIR = BASE_DIR / "vectorstore"
DB_PATH = DATA_DIR / "legalx.db"

for d in [DATA_DIR, RAW_SOURCES_DIR, AUDIO_DIR, VECTORSTORE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ---- Mistral ----
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-large-latest")
MISTRAL_EMBED_MODEL = os.getenv("MISTRAL_EMBED_MODEL", "mistral-embed")

# ---- Topics registered in the system ----
# Maps a topic_id -> (display name, source file)
TOPICS = {
    "pocso_act": {
        "name": "POCSO Act",
        "source_file": "pocso_act.txt",
    },
    "consumer_protection_act": {
        "name": "Consumer Protection Act",
        "source_file": "consumer_protection_act.txt",
    },
    "cyber_crime_laws": {
        "name": "Cyber Crime Laws",
        "source_file": "cyber_crime_laws.txt",
    },
    "rti_act": {
        "name": "Right to Information (RTI) Act",
        "source_file": "rti_act.txt",
    },
    "gst_registration": {
        "name": "GST Registration",
        "source_file": "gst_registration.txt",
    },
}

# Chunking params for RAG
CHUNK_SIZE = 800        # characters per chunk
CHUNK_OVERLAP = 150     # overlap between consecutive chunks
RAG_TOP_K = 4           # number of chunks retrieved per query
