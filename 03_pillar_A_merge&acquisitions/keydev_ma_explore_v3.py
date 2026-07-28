import wrds
import pandas as pd

pd.set_option("display.max_colwidth", 80)
pd.set_option("display.width", 220)

db = wrds.Connection(wrds_username="feketema")

# 1) Counts per type id (same as before)
counts = db.raw_sql("""
    SELECT keydeveventtypeid, COUNT(*) AS n_events
    FROM ciq.wrds_keydev
    GROUP BY keydeveventtypeid
""")

# 2) Full name catalog from the lookup (small table -> pull all of it)
catalog = db.get_table(library="ciq", table="ciqkeydevcategorytype")
# One event type can belong to several categories (we saw type 7 twice),
# so for a clean type-level list we deduplicate on the type id + name:
type_names = catalog[["keydeveventtypeid", "keydeveventtypename"]].drop_duplicates()

# 3) Merge counts with names
merged = counts.merge(type_names, on="keydeveventtypeid", how="left")
merged = merged.sort_values("n_events", ascending=False).reset_index(drop=True)

print("=" * 90)
print("TOP 40 event types by frequency, WITH names")
print("=" * 90)
print(merged.head(40).to_string())

# 4) Flag M&A-suspect types by name
MA_WORDS = ["m&a", "merger", "acquisition", "acquis", "takeover", "divest"]
mask = merged["keydeveventtypename"].str.lower().str.contains("|".join(MA_WORDS), na=False)
ma_types = merged[mask]

print("\n" + "=" * 90)
print("M&A-SUSPECT event types (by name match) - REVIEW THIS LIST")
print("=" * 90)
print(ma_types.to_string())

# 5) Save both for documentation
merged.to_csv("keydev_types_named.csv", index=False)
ma_types.to_csv("keydev_types_ma_suspect.csv", index=False)
print("\nSaved: keydev_types_named.csv, keydev_types_ma_suspect.csv")