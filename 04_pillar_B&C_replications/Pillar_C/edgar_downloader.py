"""
SEC EDGAR Download + AI Analysis
=============================
Run this script on YOUR OWN COMPUTER (not in WRDS and not here), because
sec.gov is free, but access from external servers is sometimes restricted.

What it does:
  1) It looks up the SEC CIK ID for a ticker (e.g., MSFT).
  2) It retrieves the company’s filings and selects the 10-Ks.
  3) It downloads the 10-K text and runs the AI search engine on it.
  4) It outputs the number of AI mentions and highlights the relevant sentences.
"""


import re
import time
import requests
from ai_keyword_engine import count_ai_terms, SAFE_PATTERN, AI_ABBREV_PATTERN

# =============================================================================
# ALLITSD BE EZT:
# =============================================================================
MY_EMAIL = "marcell.fekete.1@hu-berlin.de" 

HEADERS = {"User-Agent": f"AI-research-project {MY_EMAIL}"}


# -----------------------------------------------------------------------------
# 1) Ticker -> CIK
# -----------------------------------------------------------------------------
def get_cik(ticker: str) -> str:
    """The SEC searches its free ticker->CIK list for the 10-digit CIK."""
    url = "https://www.sec.gov/files/company_tickers.json"
    data = requests.get(url, headers=HEADERS).json()
    ticker = ticker.upper()
    for entry in data.values():
        if entry["ticker"] == ticker:
            # The CIK must be reset to zero using 10 digits (e.g., 789019 -> 0000789019)
            return str(entry["cik_str"]).zfill(10)
    raise ValueError(f"No CIK found for ticker: {ticker}")


# -----------------------------------------------------------------------------
# 2) CIK -> List of 10-K Filings
# -----------------------------------------------------------------------------
def get_10k_filings(cik: str, max_filings: int = 3) -> list:
    """Returns the most recent 10-K filings for a given CIK."""
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    data = requests.get(url, headers=HEADERS).json()

    recent = data["filings"]["recent"]
    results = []
    for form, acc_no, doc, date in zip(
        recent["form"],
        recent["accessionNumber"],
        recent["primaryDocument"],
        recent["filingDate"],
    ):
        if form == "10-K":
            acc_clean = acc_no.replace("-", "")
            doc_url = (
                f"https://www.sec.gov/Archives/edgar/data/"
                f"{int(cik)}/{acc_clean}/{doc}"
            )
            results.append({"date": date, "url": doc_url})
        if len(results) >= max_filings:
            break
    return results


# -----------------------------------------------------------------------------
# 3) Text Downloading + HTML Cleaning
# -----------------------------------------------------------------------------
def download_text(url: str) -> str:
    """Downloads the 10-K and extracts the raw text (without HTML)."""
    html = requests.get(url, headers=HEADERS).text
    # Simple HTML tag removal. (We can improve this with BeautifulSoup later.)
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&#\d+;", " ", text)      # HTML entities
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"\s+", " ", text)         # multiple spaces combined
    return text


# -----------------------------------------------------------------------------
# 4)  Extracting Sentences About Money (Identifying the “Money-Related” Layer)
#    We collect sentences where the AI keyword and a monetary amount appear together.
# -----------------------------------------------------------------------------
MONEY_PATTERN = re.compile(
    r"\$\s?\d[\d,\.]*\s?(?:million|billion|thousand)?",
    flags=re.IGNORECASE,
)

def find_ai_money_sentences(text: str) -> list:
    """Finds sentences that contain both AI-related terms and monetary amounts."""
    sentences = re.split(r"(?<=[\.!?])\s+", text)
    hits = []
    for s in sentences:
        has_ai = bool(SAFE_PATTERN.search(s)) or bool(AI_ABBREV_PATTERN.search(s))
        has_money = bool(MONEY_PATTERN.search(s))
        if has_ai and has_money:
            hits.append(s.strip())
    return hits


# =============================================================================
# TEST: one, significant company (Microsoft)
# =============================================================================
if __name__ == "__main__":
    ticker = "MSFT"
    print(f"[1/4] CIK search: {ticker} ...")
    cik = get_cik(ticker)
    print(f"      CIK = {cik}")
    time.sleep(0.5)   # udvariassagi szunet a SEC fele

    print(f"[2/4] 10-K filings search ...")
    filings = get_10k_filings(cik, max_filings=1)   # eloszor csak 1 db
    print(f"      Found: {len(filings)} filings, most recent: {filings[0]['date']}")
    time.sleep(0.5)

    print(f"[3/4] Downloading text ...")
    text = download_text(filings[0]["url"])
    print(f"      Downloaded text length: {len(text.split()):,} words")

    print(f"[4/4] AI analysis ...")
    counts = count_ai_terms(text)
    print(f"      Safe keywords: {counts['safe_hits']}")
    print(f"      Unconfirmed 'AI':        {counts['ai_hits']}")
    print(f"      Total AI mentions:  {counts['total_hits']}")
    print(f"      / 10,000 words:     "
          f"{10000 * counts['total_hits'] / counts['total_words']:.1f}")

    money_sentences = find_ai_money_sentences(text)
    print(f"\n[MONEY] AI + monetary amount sentences: {len(money_sentences)}")
    for i, s in enumerate(money_sentences[:5], 1):
        print(f"  ({i}) {s[:200]}...")
