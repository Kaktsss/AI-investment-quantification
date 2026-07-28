"""
v4 - Fixes driven by measured facts from v3's diagnostics:
  1) ENGINE SELF-TEST at startup: verifies the ticker fix ("(?<!:)")
     is actually loaded (v3 ran with the old engine: still 744 events).
  2) Acquirer role is "Buyer" - the measured role catalog is
     {Seller, Buyer, Target, Transaction}; there is NO "Acquirer" role,
     so v3's contains("acquir") filter matched nothing and names fell
     back to arbitrary companynames (e.g. Vanguard on IBM-Confluent).
  3) SPAC flag: "Acquisition Corp/Corporation" in text marks de-SPAC
     deals (shell mergers, not AI investment by an operating acquirer).
  4) Conservative deal-stage policy: the headline yearly series uses
     ONLY definitive_agreement + agreement events. "other" (204 events
     in v3, incl. the rejected $97.4B OpenAI bid) is reported separately,
     never silently mixed in.
"""
import sys
import wrds
import pandas as pd
import re
from ai_keyword_engine import count_ai_terms, AI_ABBREV_PATTERN

pd.set_option("display.max_colwidth", 100)

# --- 0) ENGINE SELF-TEST ----------------------------------------------
print("Engine self-test:")
print(f"  Loaded AI pattern: {AI_ABBREV_PATTERN.pattern}")
ticker_test = "L'Air Liquide SA (ENXTPA:AI) has no AI relevance"
hits = AI_ABBREV_PATTERN.findall(ticker_test)
# Expected with the fix: exactly 1 hit (the standalone 'AI'), because
# the ticker context ':AI' must be excluded.
if len(hits) == 1:
    print("  OK: ticker context ':AI' is excluded, standalone AI still counts.")
else:
    print(f"  ENGINE FIX MISSING: pattern found {len(hits)} hits in the test "
          f"string (expected 1).")
    print("  -> Update AI_ABBREV_PATTERN in ai_keyword_engine.py to:")
    print(r'     AI_ABBREV_PATTERN = re.compile(r"(?<!:)\bAI\b")')
    sys.exit(1)

# --- money patterns ------------------------------------------------------
MONEY_SCALED = re.compile(
    r"\$\s?([\d][\d,\.]*)\s?(billion|million)", flags=re.IGNORECASE)
DEAL_VALUE = re.compile(
    r"for\s+(?:up\s+to\s+)?(?:approximately\s+)?\$\s?([\d][\d,\.]*)\s?(billion|million)",
    flags=re.IGNORECASE)

def to_musd(num_str: str, scale: str) -> float:
    val = float(num_str.replace(",", ""))
    return val * 1000 if scale.lower() == "billion" else val

def extract_deal_value_musd(text: str):
    m = DEAL_VALUE.search(text)
    if m:
        return to_musd(m.group(1), m.group(2)), "for-pattern"
    scaled = MONEY_SCALED.findall(text)
    if scaled:
        return max(to_musd(n, s) for n, s in scaled), "max-fallback"
    return None, "none"

# --- deal stage classification ---------------------------------------------
PROPOSAL_PHRASES = [
    "proposed to acquire", "proposal to acquire", "submitted a proposal",
    "made a proposal", "non-binding", "offered to acquire",
    "submitted an offer", "made an offer", "submitted a bid", "made a bid",
    "expressed interest",
]

def classify_stage(text: str) -> str:
    """Order matters: most binding phrase wins; proposals checked early."""
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

SPAC_PATTERN = re.compile(r"acquisition\s+corp|\bSPAC\b", flags=re.IGNORECASE)

db = wrds.Connection(wrds_username="feketema")

# --- Stage 1: coarse SQL pre-filter (unchanged) -------------------------------
print("\nStage 1: SQL pre-filter ...")
candidates = db.raw_sql(r"""
    SELECT keydevid, companyid, companyname, gvkey,
           announcedate, eventtype, objectroletype,
           headline, situation
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
print(f"  rows: {len(candidates):,}, unique events: {candidates['keydevid'].nunique():,}")

# --- Stage 2: precise AI check with the verified engine ------------------------
candidates["text"] = (candidates["headline"].fillna("") + " "
                      + candidates["situation"].fillna(""))
candidates["ai_ok"] = candidates["text"].apply(
    lambda t: count_ai_terms(t)["total_hits"] > 0)
confirmed = candidates[candidates["ai_ok"]].copy()
print(f"Stage 2: AI-confirmed events: {confirmed['keydevid'].nunique():,} "
      f"(v3 with unfixed engine: 744 - expect a drop from ticker false positives)")

# --- Stage 3: one row per event + Buyer names -----------------------------------
confirmed["text_len"] = confirmed["text"].str.len()
events = (confirmed.sort_values("text_len", ascending=False)
                   .drop_duplicates(subset="keydevid", keep="first")
                   .copy())

buyers = (confirmed[confirmed["objectroletype"] == "Buyer"]
          .groupby("keydevid")["companyname"]
          .apply(lambda s: "; ".join(sorted(set(s.dropna()))))
          .reset_index()
          .rename(columns={"companyname": "buyer_names"}))
events = events.merge(buyers, on="keydevid", how="left")
n_with_buyer = events["buyer_names"].notna().sum()
print(f"Stage 3: {len(events):,} events, {n_with_buyer:,} with named Buyer(s)")

# --- Stage 4: value, stage, SPAC flag ----------------------------------------------
events[["deal_value_musd", "value_source"]] = events["text"].apply(
    lambda t: pd.Series(extract_deal_value_musd(t)))
events["deal_stage"] = events["text"].apply(classify_stage)
events["is_spac"] = events["text"].apply(lambda t: bool(SPAC_PATTERN.search(t)))

print("\nDeal stage distribution:")
print(events["deal_stage"].value_counts().to_string())
print(f"\nSPAC-flagged events: {events['is_spac'].sum():,}")

# --- Outputs -------------------------------------------------------------------------
events["year"] = pd.to_datetime(events["announcedate"]).dt.year
out_cols = ["keydevid", "year", "announcedate", "buyer_names",
            "companyname", "objectroletype", "headline", "deal_stage",
            "is_spac", "deal_value_musd", "value_source", "gvkey"]
events[out_cols].to_csv("ai_ma_events_v4.csv", index=False)

# Headline yearly series: FIRM stages only, SPACs excluded:
core = events[
    events["deal_stage"].isin(["definitive_agreement", "agreement"])
    & ~events["is_spac"]
]
yearly = (core.dropna(subset=["deal_value_musd"])
              .groupby("year")
              .agg(n_deals=("keydevid", "count"),
                   total_value_musd=("deal_value_musd", "sum"))
              .reset_index())
print("\n--- CORE AI M&A yearly series (definitive+agreement, non-SPAC) ---")
print(yearly.to_string(index=False))
yearly.to_csv("ai_ma_yearly_v4.csv", index=False)

# Transparency: what the conservative policy excluded, by bucket:
print("\n--- Excluded from core, by reason (events with value) ---")
excl = events.dropna(subset=["deal_value_musd"])
excl_spac = excl[excl["is_spac"]]
excl_stage = excl[~excl["is_spac"]
                  & ~excl["deal_stage"].isin(["definitive_agreement", "agreement"])]
print(f"  SPAC deals:               {len(excl_spac):3d} events, "
      f"${excl_spac['deal_value_musd'].sum():,.0f}M")
print(f"  proposal/LOI/other stage: {len(excl_stage):3d} events, "
      f"${excl_stage['deal_value_musd'].sum():,.0f}M")

print("\n--- Largest 'other'-stage events (manual review targets) ---")
others = events[events["deal_stage"] == "other"].nlargest(5, "deal_value_musd")
for _, r in others.iterrows():
    print(f"[{r['announcedate']}] ${r['deal_value_musd']:,.0f}M: {r['headline'][:110]}")

print("\n--- 10 largest CORE deals (check manually!) ---")
for _, r in core.nlargest(10, "deal_value_musd").iterrows():
    name = r["buyer_names"] if pd.notna(r["buyer_names"]) else r["companyname"]
    print(f"[{r['announcedate']}] {name}: ${r['deal_value_musd']:,.0f}M "
          f"({r['value_source']}, {r['deal_stage']})")
    print(f"   {r['headline'][:130]}")

# Random 50-event sample for manual precision validation:
sample = events.sample(n=min(50, len(events)), random_state=42)
sample[out_cols].to_csv("ai_ma_validation_sample_v4.csv", index=False)
sample[out_cols].to_excel("ai_ma_validation_sample_v4.xlsx", index=False)
print("\nSaved: ai_ma_events_v4.csv, ai_ma_yearly_v4.csv, ai_ma_validation_sample_v4.csv")