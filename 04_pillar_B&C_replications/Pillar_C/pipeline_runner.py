"""
Pillar C orchestrator: reads a ticker CSV, pulls each firm's last N 10-Ks
from SEC EDGAR, runs Tier 1 (keyword) + Tier 2 (semantic) scoring per
filing, and appends one row per filing to the output CSV immediately
(checkpointed - safe to Ctrl+C and rerun the same command to resume).

Usage:
    python pipeline_runner.py
    python pipeline_runner.py --input tickers_test_batch.csv --output pillar_c_output.csv
"""

import argparse
import logging
import sys
import time
from datetime import datetime, timezone

import pandas as pd
from tqdm import tqdm

import config
from ai_keyword_engine import count_ai_terms
from edgar_client import download_filing_html, get_10k_filings, get_cik, load_cik_map
from semantic_tier2 import score_filing
from text_chunking import chunk_filing_text

OUTPUT_COLUMNS = [
    "ticker",
    "cik",
    "gvkey",
    "fiscal_year",
    "filing_date",
    "accession_number",
    "doc_url",
    "n_chunks_analyzed",
    "tier1_safe_hits",
    "tier1_ai_hits",
    "tier1_total_hits",
    "tier1_per_10k_words",
    "tier2_semantic_score",
    "ai_washing_delta",
    "status",
    "error_message",
]

ERROR_LOG_COLUMNS = [
    "ticker",
    "cik",
    "accession_number",
    "stage",
    "error_type",
    "error_message",
    "timestamp",
]

logger = logging.getLogger("pillar_c.pipeline_runner")


def setup_logging(log_path) -> None:
    root = logging.getLogger("pillar_c")
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S"))
    root.addHandler(console)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    root.addHandler(file_handler)


def load_existing_results(output_csv_path) -> pd.DataFrame:
    if not output_csv_path.exists():
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    return pd.read_csv(output_csv_path, dtype={"cik": str, "accession_number": str})


def _counts_as_done(existing_df: pd.DataFrame) -> pd.Series:
    if existing_df.empty:
        return pd.Series(dtype=bool)
    if config.RETRY_ERRORS_ON_RESUME:
        return existing_df["status"] == "ok"
    return pd.Series(True, index=existing_df.index)


def ticker_has_blocking_failure(existing_df: pd.DataFrame, ticker: str) -> bool:
    """A CIK/filing-list-level failure has no accession_number; treat as done unless retrying errors."""
    if existing_df.empty or config.RETRY_ERRORS_ON_RESUME:
        return False
    sub = existing_df[
        (existing_df["ticker"] == ticker) & existing_df["accession_number"].apply(lambda x: not pd.notna(x))
    ]
    return len(sub) > 0


def ticker_done_count(existing_df: pd.DataFrame, ticker: str) -> int:
    if existing_df.empty:
        return 0
    sub = existing_df[existing_df["ticker"] == ticker]
    return int(_counts_as_done(sub).sum())


def filing_already_done(existing_df: pd.DataFrame, ticker: str, accession_number: str) -> bool:
    if existing_df.empty:
        return False
    sub = existing_df[
        (existing_df["ticker"] == ticker) & (existing_df["accession_number"] == accession_number)
    ]
    return int(_counts_as_done(sub).sum()) > 0


def append_output_row(row: dict, output_csv_path) -> None:
    write_header = not output_csv_path.exists()
    pd.DataFrame([row], columns=OUTPUT_COLUMNS).to_csv(
        output_csv_path, mode="a", header=write_header, index=False
    )


def append_error_log(ticker, cik, accession_number, stage, exc, error_log_path) -> None:
    write_header = not error_log_path.exists()
    row = {
        "ticker": ticker,
        "cik": cik,
        "accession_number": accession_number,
        "stage": stage,
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    pd.DataFrame([row], columns=ERROR_LOG_COLUMNS).to_csv(
        error_log_path, mode="a", header=write_header, index=False
    )


def run_tier1(chunks: list) -> tuple:
    """Aggregates Tier 1 keyword counts across a filing's chunks; also
    returns a per-chunk boolean hit mask for Tier 2 gating."""
    safe_hits = ai_hits = total_words = 0
    hit_mask = []
    for chunk in chunks:
        counts = count_ai_terms(chunk["text"])
        safe_hits += counts["safe_hits"]
        ai_hits += counts["ai_hits"]
        total_words += counts["total_words"]
        hit_mask.append(counts["total_hits"] > 0)

    total_hits = safe_hits + ai_hits
    per_10k_words = (10000 * total_hits / total_words) if total_words else None

    return (
        {
            "tier1_safe_hits": safe_hits,
            "tier1_ai_hits": ai_hits,
            "tier1_total_hits": total_hits,
            "tier1_per_10k_words": per_10k_words,
        },
        hit_mask,
    )


def build_row(*, ticker, cik, filing, tier1=None, tier2=None, n_chunks=None, status, error_message=None) -> dict:
    return {
        "ticker": ticker,
        "cik": cik,
        "gvkey": "",  # filled in manually later via a gvkey/CIK mapping if merging with Pillar A/B
        "fiscal_year": filing.get("fiscal_year") if filing else None,
        "filing_date": filing.get("filing_date") if filing else None,
        "accession_number": filing.get("accession_number") if filing else None,
        "doc_url": filing.get("doc_url") if filing else None,
        "n_chunks_analyzed": n_chunks,
        "tier1_safe_hits": tier1["tier1_safe_hits"] if tier1 else None,
        "tier1_ai_hits": tier1["tier1_ai_hits"] if tier1 else None,
        "tier1_total_hits": tier1["tier1_total_hits"] if tier1 else None,
        "tier1_per_10k_words": tier1["tier1_per_10k_words"] if tier1 else None,
        "tier2_semantic_score": tier2["tier2_semantic_score"] if tier2 else None,
        "ai_washing_delta": None,  # filled by finalize_ai_washing_delta.py once the batch is complete
        "status": status,
        "error_message": error_message,
    }


def process_filing(ticker: str, cik: str, filing: dict) -> dict:
    html = download_filing_html(filing["doc_url"])
    chunks = chunk_filing_text(html)
    tier1, hit_mask = run_tier1(chunks)
    tier2 = score_filing(chunks, keyword_hit_mask=hit_mask)
    return build_row(
        ticker=ticker,
        cik=cik,
        filing=filing,
        tier1=tier1,
        tier2=tier2,
        n_chunks=len(chunks),
        status="ok",
    )


def run_pipeline(input_csv_path, output_csv_path, error_log_path, max_filings_per_firm) -> None:
    tickers_df = pd.read_csv(input_csv_path)
    tickers = [t.strip().upper() for t in tickers_df["ticker"].dropna().tolist()]
    logger.info("Loaded %d tickers from %s", len(tickers), input_csv_path)

    existing_df = load_existing_results(output_csv_path)
    logger.info("Found %d existing result rows in %s", len(existing_df), output_csv_path)

    cik_map = load_cik_map()
    logger.info("Loaded CIK map with %d tickers", len(cik_map))

    for ticker in tqdm(tickers, desc="Firms"):
        if ticker_has_blocking_failure(existing_df, ticker):
            logger.info("[%s] skipping: prior run recorded a CIK/filing-list failure", ticker)
            continue
        if ticker_done_count(existing_df, ticker) >= max_filings_per_firm:
            logger.info("[%s] skipping: already has %d+ completed filings", ticker, max_filings_per_firm)
            continue

        cik = None
        try:
            cik = get_cik(ticker, cik_map)
            filings = get_10k_filings(cik, max_filings=max_filings_per_firm)

            if not filings:
                logger.warning("[%s] no 10-K filings found in window", ticker)

            for filing in filings:
                if filing_already_done(existing_df, ticker, filing["accession_number"]):
                    continue
                try:
                    row = process_filing(ticker, cik, filing)
                except Exception as exc:  # noqa: BLE001 - must never kill the loop
                    logger.exception("[%s] filing %s failed", ticker, filing.get("accession_number"))
                    row = build_row(
                        ticker=ticker, cik=cik, filing=filing, status="error", error_message=str(exc)
                    )
                    append_error_log(
                        ticker, cik, filing.get("accession_number"), "download_or_process", exc, error_log_path
                    )
                append_output_row(row, output_csv_path)

        except Exception as exc:  # noqa: BLE001 - must never kill the loop
            logger.exception("[%s] CIK/filing-list lookup failed", ticker)
            append_error_log(ticker, cik, None, "cik_or_filing_list", exc, error_log_path)
            append_output_row(
                build_row(ticker=ticker, cik=cik, filing=None, status="error", error_message=str(exc)),
                output_csv_path,
            )


def parse_args():
    parser = argparse.ArgumentParser(description="Pillar C: two-tier AI engagement pipeline")
    parser.add_argument("--input", type=str, default=str(config.INPUT_CSV_PATH))
    parser.add_argument("--output", type=str, default=str(config.OUTPUT_CSV_PATH))
    parser.add_argument("--error-log", type=str, default=str(config.ERROR_LOG_PATH))
    parser.add_argument("--max-filings", type=int, default=config.MAX_FILINGS_PER_FIRM)
    return parser.parse_args()


if __name__ == "__main__":
    from pathlib import Path

    args = parse_args()
    setup_logging(config.RUN_LOG_PATH)

    start = time.monotonic()
    run_pipeline(
        input_csv_path=Path(args.input),
        output_csv_path=Path(args.output),
        error_log_path=Path(args.error_log),
        max_filings_per_firm=args.max_filings,
    )
    logger.info("Run finished in %.1f minutes", (time.monotonic() - start) / 60)
