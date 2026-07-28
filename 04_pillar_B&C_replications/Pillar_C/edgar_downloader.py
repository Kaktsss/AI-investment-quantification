"""
SEC EDGAR single-ticker demo + qualitative "AI + $ amount" diagnostic.

For the production, multi-firm, checkpointed pipeline see pipeline_runner.py
(Tier 1 + Tier 2 scoring, resumable, S&P-500 scale). This script keeps the
original single-ticker smoke test plus find_ai_money_sentences(), which is
useful for eyeballing which sentences in one filing mention both AI and a
dollar amount - a qualitative check, not part of the Tier1/Tier2 output.

CIK lookup, filing listing, and HTTP access (rate limiting, retries, User-
Agent) now live in edgar_client.py and are reused here rather than
duplicated.
"""

import re

from ai_keyword_engine import AI_ABBREV_PATTERN, SAFE_PATTERN, count_ai_terms
from edgar_client import download_filing_html, get_10k_filings, get_cik, load_cik_map

MONEY_PATTERN = re.compile(
    r"\$\s?\d[\d,\.]*\s?(?:million|billion|thousand)?",
    flags=re.IGNORECASE,
)


def download_text(url: str) -> str:
    """
    Downloads filing HTML and flattens it to plain text for the sentence-level
    diagnostic below. The production pipeline uses text_chunking.py instead,
    which preserves paragraph structure for chunk-level Tier 2 scoring.
    """
    html = download_filing_html(url)
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&#\d+;", " ", text)
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def find_ai_money_sentences(text: str) -> list:
    """Finds sentences that contain both AI-related terms and monetary amounts."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    hits = []
    for s in sentences:
        has_ai = bool(SAFE_PATTERN.search(s)) or bool(AI_ABBREV_PATTERN.search(s))
        has_money = bool(MONEY_PATTERN.search(s))
        if has_ai and has_money:
            hits.append(s.strip())
    return hits


# =============================================================================
# DEMO: one company (Microsoft)
# =============================================================================
if __name__ == "__main__":
    ticker = "MSFT"
    print(f"[1/4] CIK search: {ticker} ...")
    cik_map = load_cik_map()
    cik = get_cik(ticker, cik_map)
    print(f"      CIK = {cik}")

    print("[2/4] 10-K filings search ...")
    filings = get_10k_filings(cik, max_filings=1)
    print(f"      Found: {len(filings)} filings, most recent: {filings[0]['filing_date']}")

    print("[3/4] Downloading text ...")
    text = download_text(filings[0]["doc_url"])
    print(f"      Downloaded text length: {len(text.split()):,} words")

    print("[4/4] AI analysis ...")
    counts = count_ai_terms(text)
    print(f"      Safe keywords: {counts['safe_hits']}")
    print(f"      Unconfirmed 'AI':        {counts['ai_hits']}")
    print(f"      Total AI mentions:  {counts['total_hits']}")
    print(f"      / 10,000 words:     " f"{10000 * counts['total_hits'] / counts['total_words']:.1f}")

    money_sentences = find_ai_money_sentences(text)
    print(f"\n[MONEY] AI + monetary amount sentences: {len(money_sentences)}")
    for i, s in enumerate(money_sentences[:5], 1):
        print(f"  ({i}) {s[:200]}...")
