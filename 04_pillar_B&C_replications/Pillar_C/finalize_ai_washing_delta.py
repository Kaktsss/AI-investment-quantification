"""
Fills in the ai_washing_delta column of the Pillar C output CSV.

ai_washing_delta requires cross-sectional mean/std of tier1_per_10k_words
and tier2_semantic_score, which aren't known until (most of) the batch has
run - so pipeline_runner.py leaves this column blank per row, and this
script computes it in one pass over the full output file. Safe to re-run
any time after new rows have been appended; it recomputes and overwrites
the column in place each time rather than accumulating stale values.

Usage:
    python finalize_ai_washing_delta.py
    python finalize_ai_washing_delta.py --output pillar_c_output.csv
"""

import argparse
import logging
from pathlib import Path

import pandas as pd

import config

logger = logging.getLogger("pillar_c.finalize_ai_washing_delta")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")


def compute_ai_washing_delta(df: pd.DataFrame) -> pd.DataFrame:
    """
    z1 = z-score of tier1_per_10k_words across successfully-scored rows
    z2 = z-score of tier2_semantic_score across successfully-scored rows
    ai_washing_delta = z1 - z2

    Positive: keyword-heavy relative to peers but semantically thin relative
    to that intensity (hype signal). Negative: semantically substantive
    relative to keyword intensity (possible under-hyped genuine engagement).
    """
    scored_mask = (
        (df["status"] == "ok")
        & df["tier1_per_10k_words"].apply(pd.notna)
        & df["tier2_semantic_score"].apply(pd.notna)
    )
    n_scored = int(scored_mask.sum())
    if n_scored < 2:
        logger.warning(
            "Only %d fully-scored row(s) available; z-scoring needs at least 2. "
            "ai_washing_delta left blank.",
            n_scored,
        )
        df["ai_washing_delta"] = pd.NA
        return df

    tier1_vals = df.loc[scored_mask, "tier1_per_10k_words"]
    tier2_vals = df.loc[scored_mask, "tier2_semantic_score"]

    tier1_std = tier1_vals.std()
    tier2_std = tier2_vals.std()
    if tier1_std == 0 or tier2_std == 0 or pd.isna(tier1_std) or pd.isna(tier2_std):
        logger.warning("Zero or undefined variance in tier1/tier2 scores; ai_washing_delta left blank.")
        df["ai_washing_delta"] = pd.NA
        return df

    z1 = (tier1_vals - tier1_vals.mean()) / tier1_std
    z2 = (tier2_vals - tier2_vals.mean()) / tier2_std

    df["ai_washing_delta"] = pd.NA
    df.loc[scored_mask, "ai_washing_delta"] = z1 - z2

    logger.info("Computed ai_washing_delta for %d/%d rows", n_scored, len(df))
    return df


def main(output_csv_path: Path) -> None:
    if not output_csv_path.exists():
        raise FileNotFoundError(f"Output CSV not found: {output_csv_path}")

    df = pd.read_csv(output_csv_path, dtype={"cik": str, "accession_number": str})
    df = compute_ai_washing_delta(df)
    df.to_csv(output_csv_path, index=False)
    logger.info("Wrote updated ai_washing_delta column to %s", output_csv_path)


def parse_args():
    parser = argparse.ArgumentParser(description="Finalize ai_washing_delta on the Pillar C output CSV")
    parser.add_argument("--output", type=str, default=str(config.OUTPUT_CSV_PATH))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(Path(args.output))
