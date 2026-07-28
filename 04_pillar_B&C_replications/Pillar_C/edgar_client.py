"""
SEC EDGAR client: ticker->CIK resolution (cached), 10-K filing listing,
and rate-limited/retrying HTTP access.

All network calls to sec.gov / data.sec.gov go through sec_get() so the
rate limit and retry policy are enforced in exactly one place.
"""

import json
import logging
import time
from datetime import datetime, timedelta, timezone

import requests

import config

logger = logging.getLogger("pillar_c.edgar_client")

_session = requests.Session()
_session.headers.update(config.HEADERS)

_last_request_time = 0.0


class SECFetchError(Exception):
    """Raised when a SEC EDGAR request fails after exhausting retries."""

    def __init__(self, message: str, stage: str, status_code: int | None = None):
        super().__init__(message)
        self.stage = stage
        self.status_code = status_code


def _throttle() -> None:
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    wait = config.RATE_LIMIT_MIN_INTERVAL - elapsed
    if wait > 0:
        time.sleep(wait)
    _last_request_time = time.monotonic()


def sec_get(url: str, stage: str, *, parse_json: bool = True):
    """
    Rate-limited, retrying GET against a sec.gov/data.sec.gov URL.

    404 is treated as permanent (no retry). 429/403/timeouts/connection
    errors are retried with backoff. Raises SECFetchError once retries
    are exhausted.
    """
    last_exc = None
    last_status = None
    for attempt in range(config.MAX_RETRIES + 1):
        _throttle()
        try:
            resp = _session.get(url, timeout=config.REQUEST_TIMEOUT)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            last_exc = exc
            logger.debug("Timeout/connection error on %s (attempt %d): %s", url, attempt, exc)
        else:
            last_status = resp.status_code
            if resp.status_code == 200:
                return resp.json() if parse_json else resp.text
            if resp.status_code == 404:
                raise SECFetchError(f"404 Not Found: {url}", stage=stage, status_code=404)
            if resp.status_code in (429, 403):
                retry_after = resp.headers.get("Retry-After")
                if retry_after is not None:
                    try:
                        time.sleep(float(retry_after))
                    except ValueError:
                        pass
                logger.debug("HTTP %d on %s (attempt %d)", resp.status_code, url, attempt)
            else:
                resp.raise_for_status()

        if attempt < config.MAX_RETRIES:
            backoff = config.RETRY_BACKOFF_SECONDS[min(attempt, len(config.RETRY_BACKOFF_SECONDS) - 1)]
            time.sleep(backoff)

    raise SECFetchError(
        f"Exhausted {config.MAX_RETRIES} retries fetching {url}: {last_exc or f'HTTP {last_status}'}",
        stage=stage,
        status_code=last_status,
    )


# ---------------------------------------------------------------------------
# Ticker -> CIK, cached
# ---------------------------------------------------------------------------
def load_cik_map(cache_path=None, ttl_hours: int | None = None) -> dict:
    """
    Loads (and caches locally) the SEC ticker->CIK map. Downloads at most
    once per ttl_hours; reused in-memory for the whole pipeline run so
    CIK resolution never re-hits the network per firm.
    """
    cache_path = cache_path or config.CIK_CACHE_PATH
    ttl_hours = config.CIK_CACHE_TTL_HOURS if ttl_hours is None else ttl_hours

    if cache_path.exists():
        age = datetime.now(timezone.utc) - datetime.fromtimestamp(
            cache_path.stat().st_mtime, tz=timezone.utc
        )
        if age < timedelta(hours=ttl_hours):
            with open(cache_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            logger.info("Loaded CIK map from cache (%s, age %.1fh)", cache_path, age.total_seconds() / 3600)
            return _build_ticker_index(raw)

    logger.info("Downloading fresh ticker->CIK map from SEC")
    raw = sec_get("https://www.sec.gov/files/company_tickers.json", stage="load_cik_map")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(raw, f)
    return _build_ticker_index(raw)


def _build_ticker_index(raw: dict) -> dict:
    index = {}
    for entry in raw.values():
        index[entry["ticker"].upper()] = str(entry["cik_str"]).zfill(10)
    return index


def get_cik(ticker: str, cik_map: dict) -> str:
    """O(1) lookup against a pre-loaded ticker->CIK map (see load_cik_map)."""
    ticker = ticker.upper()
    if ticker not in cik_map:
        raise ValueError(f"No CIK found for ticker: {ticker}")
    return cik_map[ticker]


# ---------------------------------------------------------------------------
# CIK -> 10-K filings
# ---------------------------------------------------------------------------
def get_10k_filings(cik: str, max_filings: int = None, years: int = 6) -> list:
    """
    Returns up to max_filings most recent 10-K filings for a CIK, restricted
    to the last `years` years. `years` defaults slightly wider than the
    5-year panel target so a firm whose most recent 10-K is a few months
    stale doesn't lose a panel year at the boundary.
    """
    max_filings = config.MAX_FILINGS_PER_FIRM if max_filings is None else max_filings
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    data = sec_get(url, stage="get_10k_filings")

    recent = data["filings"]["recent"]
    cutoff = datetime.now(timezone.utc) - timedelta(days=365 * years)

    candidates = []
    for form, acc_no, doc, date in zip(
        recent["form"],
        recent["accessionNumber"],
        recent["primaryDocument"],
        recent["filingDate"],
    ):
        if form != "10-K":
            continue
        filing_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if filing_date < cutoff:
            continue
        acc_clean = acc_no.replace("-", "")
        doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_clean}/{doc}"
        candidates.append(
            {
                "accession_number": acc_no,
                "filing_date": date,
                "fiscal_year": filing_date.year,
                "doc_url": doc_url,
            }
        )

    candidates.sort(key=lambda f: f["filing_date"], reverse=True)
    return candidates[:max_filings]


def download_filing_html(url: str) -> str:
    """Downloads the raw HTML of a filing document."""
    return sec_get(url, stage="download_filing_html", parse_json=False)
