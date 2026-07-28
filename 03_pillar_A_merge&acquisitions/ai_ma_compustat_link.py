"""
Link CORE AI M&A deals to Compustat at the acquirer(buyer)-year level.

Key methodological points (professor-facing):
  1) Buyer gvkeys are taken from Buyer-ROLE rows, NOT from the deduplicated
     event row (whose gvkey may belong to a Seller/Target).
  2) Consortium deals: we report BOTH attribution schemes -
     full value to each buyer (upper bound, double-counts consortiums)
     and equal split across buyers (arbitrary but additive).
  3) Buyers without gvkey (private firms, funds) cannot be linked -
     their count is reported, not silently dropped.
Compustat: comp.funda with the four standard filters, pulling
xrd (R&D), capx (CapEx), at (assets), sale (revenue) for scaling.
"""
import sys
import wrds
import pandas as pd
import re
from ai_keyword_engine import count_ai_terms, AI_ABBREV_PATTERN

pd.set_option("display.max_colwidth", 100)

# --- self-test (same guard as v4) ------------------------------------
if AI_ABBREV_PATTERN.findall("(ENXTPA:AI) plus real AI") != ["AI"]:
    print("ENGINE FIX MISSING - update ai_keyword_engine.py first.")
    sys.exit(1)

# --- patterns (identical to v4 - single source of truth would be a
#     shared module; acceptable duplication for now, flagged for cleanup) ---
MONEY_SCALED = re.compile(
    r"\$\s?([\d][\d,\.]*)\s?(billion|million)", flags=re.IGNORECASE)
DEAL_VALUE = re.compile(
    r"for\s+(?:up\s+to\s+)?(?:approximately\s+)?\$\s?([\d][\d,\.]*)\s?(billion|million)",
    flags=re.IGNORECASE)
PROPOSAL_PHRASES = [
    "proposed to acquire", "proposal to acquire", "submitted a proposal",
    "made a proposal", "non-binding", "offered to acquire",
    "submitted an offer", "made an offer", "submitted a bid", "made a bid",
    "expressed interest",
]
SPAC_PATTERN = re.compile(r"acquisition\s+corp|\bSPAC\b", flags=re.IGNORECASE)

def to_musd(n, s):
    return float(n.replace(",", "")) * (1000 if s.lower() == "billion" else 1)

def extract_deal_value_musd(text):
    m = DEAL_VALUE.search(text)
    if m:
        return to_musd(m.group(1), m.group(2)), "for-pattern"
    scaled = MONEY_SCALED.findall(text)
    if scaled:
        return max(to_musd(n, s) for n, s in scaled), "max-fallback"
    return None, "none"

def classify_stage(text):
    t = text.lower()
    if re.search(r"definitive\s+(?:\w+\s+)?agreement", t):
        return "definitive_agreement"
    if any(p in t for p in PROPOSAL_PHRASES):
        return "proposal"
    if "letter of intent" in t:
        return "letter_of_intent"
    if "agreed to acquire" in t or "entered into an agreement" in t:
        return "agreement"
    return "other"

db = wrds.Connection(wrds_username="feketema")

# --- Stage 1-2: same filter chain as v4 --------------------------------
print("Stage 1: SQL pre-filter ...")
rows = db.raw_sql(r"""
    SELECT keydevid, companyid, companyname, gvkey,
           announcedate, objectroletype, headline, situation
    FROM ciq.wrds_keydev
    WHERE keydeveventtypeid = 80
      AND (
            headline  ~ '\yAI\y'
         OR situation ~ '\yAI\y'
         OR headline  ILIKE '%%artificial intelligence%%'
         OR situation ILIKE '%%artificial intelligence%%'
         OR headline  ILIKE '%%machine learning%%'
         OR situation ILIKE '%%machine learning%%'
      )
""")
rows["text"] = rows["headline"].fillna("") + " " + rows["situation"].fillna("")
rows = rows[rows["text"].apply(lambda t: count_ai_terms(t)["total_hits"] > 0)]
print(f"  AI-confirmed rows: {len(rows):,} "
      f"({rows['keydevid'].nunique():,} events)")

# --- Stage 3: event-level attributes (value, stage, SPAC) ---------------
rows["text_len"] = rows["text"].str.len()
events = (rows.sort_values("text_len", ascending=False)
              .drop_duplicates(subset="keydevid", keep="first")[
                  ["keydevid", "announcedate", "text"]].copy())
events[["deal_value_musd", "value_source"]] = events["text"].apply(
    lambda t: pd.Series(extract_deal_value_musd(t)))
events["deal_stage"] = events["text"].apply(classify_stage)
events["is_spac"] = events["text"].apply(lambda t: bool(SPAC_PATTERN.search(t)))
events["year"] = pd.to_datetime(events["announcedate"]).dt.year

core_events = events[
    events["deal_stage"].isin(["definitive_agreement", "agreement"])
    & ~events["is_spac"]
    & events["deal_value_musd"].notna()
]
print(f"Core events with value: {len(core_events):,}")

# --- Stage 4: buyers of core events, WITH THEIR OWN gvkeys ---------------
buyers = rows[rows["objectroletype"] == "Buyer"][
    ["keydevid", "companyid", "companyname", "gvkey"]].drop_duplicates()
core_buyers = buyers.merge(
    core_events[["keydevid", "year", "deal_value_musd"]],
    on="keydevid", how="inner")

n_buyers_per_event = core_buyers.groupby("keydevid")["companyid"].nunique()
core_buyers = core_buyers.merge(
    n_buyers_per_event.rename("n_buyers"), on="keydevid")
core_buyers["deal_value_split"] = (core_buyers["deal_value_musd"]
                                   / core_buyers["n_buyers"])

has_gvkey = core_buyers["gvkey"].notna()
print(f"Buyer-event pairs: {len(core_buyers):,}; "
      f"with gvkey (Compustat-linkable): {has_gvkey.sum():,}; "
      f"without (private/funds): {(~has_gvkey).sum():,}")

linkable = core_buyers[has_gvkey].copy()

# --- Stage 5: acquirer-year aggregation -----------------------------------
acq_year = (linkable.groupby(["gvkey", "companyname", "year"])
            .agg(n_ai_deals=("keydevid", "nunique"),
                 ai_deal_value_full_musd=("deal_value_musd", "sum"),
                 ai_deal_value_split_musd=("deal_value_split", "sum"))
            .reset_index())
print(f"Acquirer-year observations: {len(acq_year):,} "
      f"({acq_year['gvkey'].nunique():,} unique acquirers)")

# --- Stage 6: Compustat financials for these gvkeys -------------------------
gvkeys = tuple(acq_year["gvkey"].unique())
print("Pulling Compustat annual financials ...")
comp = db.raw_sql(f"""
    SELECT gvkey, fyear, conm, xrd, capx, at, sale
    FROM comp.funda
    WHERE gvkey IN {gvkeys}
      AND indfmt = 'INDL' AND datafmt = 'STD'
      AND popsrc = 'D'    AND consol  = 'C'
      AND fyear >= 1999
""")
print(f"  Compustat rows: {len(comp):,}")

merged = acq_year.merge(
    comp, left_on=["gvkey", "year"], right_on=["gvkey", "fyear"], how="left")
merged["matched_compustat"] = merged["fyear"].notna()
print(f"Acquirer-years matched to Compustat: "
      f"{merged['matched_compustat'].sum():,} / {len(merged):,}")

# Scaling: AI deal value as % of the acquirer's R&D and CapEx that year
merged["ai_deals_vs_rd_pct"] = (
    100 * merged["ai_deal_value_split_musd"] / merged["xrd"])
merged["ai_deals_vs_capx_pct"] = (
    100 * merged["ai_deal_value_split_musd"] / merged["capx"])

out = merged[["gvkey", "companyname", "conm", "year", "n_ai_deals",
              "ai_deal_value_full_musd", "ai_deal_value_split_musd",
              "xrd", "capx", "at", "sale",
              "ai_deals_vs_rd_pct", "ai_deals_vs_capx_pct",
              "matched_compustat"]]
out.to_csv("ai_ma_acquirer_year_compustat.csv", index=False)

print("\n--- Top 15 acquirer-years by AI deal value (split) ---")
top = out.nlargest(15, "ai_deal_value_split_musd")
print(top[["companyname", "year", "n_ai_deals",
           "ai_deal_value_split_musd", "xrd", "capx"]].to_string(index=False))

print("\nSaved: ai_ma_acquirer_year_compustat.csv")