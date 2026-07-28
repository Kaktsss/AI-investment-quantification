"""
Map the ciq schema from a transactions/M&A perspective:
1) list all ciq-related libraries,
2) find tables whose names suggest transactions/acquisitions/key developments,
3) empirically test access on the candidates.
"""
import wrds

db = wrds.Connection(wrds_username="feketema")

libs = db.list_libraries()
ciq_libs = [l for l in libs if "ciq" in l.lower()]
print("CIQ-related libraries:", ciq_libs)

# Collect candidate tables across all ciq libraries
KEYWORDS = ["transact", "acq", "merger", "ma_", "deal", "keydev", "invest"]

candidates = []
for lib in ciq_libs:
    try:
        tables = db.list_tables(library=lib)
    except Exception as e:
        print(f"  Could not list tables in {lib}: {str(e)[:60]}")
        continue
    for t in tables:
        if any(k in t.lower() for k in KEYWORDS):
            candidates.append((lib, t))

print(f"\nCandidate tables ({len(candidates)}):")
for lib, t in candidates:
    print(f"  {lib}.{t}")

# Empirical access test on each candidate (3 rows)
print("\n" + "=" * 70)
print("ACCESS TEST")
print("=" * 70)
for lib, t in candidates:
    try:
        df = db.get_table(library=lib, table=t, obs=3)
        print(f"  OK      {lib}.{t}  ({len(df.columns)} cols)")
    except Exception as e:
        reason = str(e).split("\n")[0][:60]
        print(f"  DENIED  {lib}.{t}  ({reason})")