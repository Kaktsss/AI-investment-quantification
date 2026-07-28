"""
Pillar C pipeline configuration.
All tunables live here so pipeline_runner.py's CLI flags have a single
source of defaults, and so every module (edgar_client, text_chunking,
semantic_tier2) reads the same constants.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# SEC EDGAR contact / compliance
# ---------------------------------------------------------------------------
# SEC requires a working contact email in the User-Agent header for all
# automated access (https://www.sec.gov/os/webmaster-faq#developers).
# Kept out of source control: set it in your shell before running, e.g.
#   Windows:      set SEC_CONTACT_EMAIL=you@example.com
#   PowerShell:   $env:SEC_CONTACT_EMAIL = "you@example.com"
SEC_CONTACT_EMAIL = os.environ.get("SEC_CONTACT_EMAIL", "").strip()
if not SEC_CONTACT_EMAIL:
    raise RuntimeError(
        "SEC_CONTACT_EMAIL environment variable is not set. "
        "SEC EDGAR requires a contact email in every request's User-Agent. "
        "Set it before running, e.g. (Windows) `set SEC_CONTACT_EMAIL=you@example.com`."
    )

HEADERS = {"User-Agent": f"AI-research-project ({SEC_CONTACT_EMAIL})"}

# ---------------------------------------------------------------------------
# I/O paths (overridable via pipeline_runner.py CLI flags)
# ---------------------------------------------------------------------------
INPUT_CSV_PATH = BASE_DIR / "tickers_test_batch.csv"
OUTPUT_CSV_PATH = BASE_DIR / "pillar_c_output.csv"
ERROR_LOG_PATH = BASE_DIR / "pillar_c_errors_log.csv"
RUN_LOG_PATH = BASE_DIR / "pillar_c_run.log"
CIK_CACHE_PATH = BASE_DIR / "cik_cache" / "company_tickers_cache.json"
CIK_CACHE_TTL_HOURS = 24

# ---------------------------------------------------------------------------
# Filing selection
# ---------------------------------------------------------------------------
MAX_FILINGS_PER_FIRM = 5  # most recent N 10-Ks per firm (~5-year panel)

# ---------------------------------------------------------------------------
# Chunking (text_chunking.py)
# ---------------------------------------------------------------------------
CHUNK_TARGET_WORDS = 180       # word-count proxy for MiniLM's 256-token budget
MIN_PARAGRAPH_WORDS = 8        # drop paragraphs shorter than this (boilerplate/headers)
MIN_ALPHA_FRACTION = 0.5       # drop paragraphs with less alphabetic content than this
MIN_CHUNK_WORDS = 40           # tail sub-chunks smaller than this get merged back
TAIL_MERGE_CEILING = 1.2       # allow merged tail chunk up to CHUNK_TARGET_WORDS * this

# ---------------------------------------------------------------------------
# Tier 2 semantic scoring (semantic_tier2.py)
# ---------------------------------------------------------------------------
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
TIER1_GATES_TIER2 = False      # test-batch decision: embed ALL chunks, not just keyword-hit ones
TOP_K_CHUNKS_FOR_TIER2 = 10    # per-filing score = mean of top-k chunk similarities
MIN_K_CHUNKS_FOR_TIER2 = 3
MAX_CHUNKS_PER_FILING = 300    # cap embedding cost per filing; subsample beyond this
RANDOM_STATE = 42              # seeds chunk subsampling (numpy.random.default_rng)

# ---------------------------------------------------------------------------
# SEC rate limiting & retry (edgar_client.py)
# ---------------------------------------------------------------------------
RATE_LIMIT_MIN_INTERVAL = 0.11   # seconds between requests (~9 req/sec, under SEC's 10/sec cap)
REQUEST_TIMEOUT = 30             # seconds
MAX_RETRIES = 5
RETRY_BACKOFF_SECONDS = [1, 2, 5, 10, 20]

# ---------------------------------------------------------------------------
# Resume / checkpointing
# ---------------------------------------------------------------------------
RETRY_ERRORS_ON_RESUME = False   # if True, rows with status != "ok" are reprocessed on resume
