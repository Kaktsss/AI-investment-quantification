import pandas as pd
import wrds

AI_PATH  = r"C:\Users\Fekete Marci\08_Corpfin_work\AI_project\data\firm_ai_patent_value_v2.csv"
OUT_PATH = r"C:\Users\Fekete Marci\08_Corpfin_work\AI_project\data\pillar_b_final_v2.csv"

ai = pd.read_csv(AI_PATH, dtype={"permno": str, "year": int})
print(f"AI patent firm-years: {len(ai):,}  (year range {ai['year'].min()}-{ai['year'].max()})")

db = wrds.Connection(wrds_username="feketema")
comp = db.raw_sql("""
    SELECT a.gvkey, a.fyear AS year, a.conm, a.at, a.xrd, a.capx, a.sale,
           b.lpermno AS permno
    FROM comp.funda AS a
    JOIN crsp.ccmxpf_lnkhist AS b ON a.gvkey = b.gvkey
    WHERE a.indfmt='INDL' AND a.datafmt='STD'
      AND a.popsrc='D'   AND a.consol='C'
      AND b.linktype IN ('LU','LC') AND b.linkprim IN ('P','C')
      AND a.datadate >= b.linkdt
      AND (a.datadate <= b.linkenddt OR b.linkenddt IS NULL)
      AND a.fyear BETWEEN 1990 AND 2023
""")
db.close()
comp["permno"] = comp["permno"].astype("Int64").astype(str)
comp["year"] = comp["year"].astype(int)

# Duplicate check BEFORE merge
dups = comp.duplicated(subset=["permno", "year"]).sum()
print(f"Compustat permno-year duplicates from link table: {dups:,}")
if dups:
    comp = comp.sort_values("gvkey").drop_duplicates(subset=["permno", "year"], keep="first")
    print("  -> deduplicated (kept first); flag for review if this is large.")

final = ai.merge(comp, on=["permno", "year"], how="left")
print(f"Merged rows: {len(final):,}; matched to Compustat: {final['at'].notna().sum():,}")

# Size-scaled RATIOS. NOTE: numerator is the market VALUE of AI patents
# (Kogan method, an OUTPUT measure), NOT accounting AI spending. Scaling
# by assets/R&D only removes the size effect for cross-firm comparison;
# a ratio > 1 is expected (market value of intangible AI knowledge can
# exceed book assets, esp. for firms like NVIDIA).
final["ai_patval_scaled_by_assets"] = final["ai_value_nom_musd_p50"] / final["at"]
final.loc[final["xrd"] <= 0, "xrd"] = pd.NA
final["ai_patval_scaled_by_rnd"] = final["ai_value_nom_musd_p50"] / final["xrd"]

final.to_csv(OUT_PATH, index=False)
print(f"Saved: {OUT_PATH}")

print("\nTop 10 by nominal AI patent value (with company names):")
cols = ["conm", "permno", "year", "n_ai_patents_p50",
        "ai_value_nom_musd_p50", "at", "xrd", "ai_patval_scaled_by_assets"]
print(final.nlargest(10, "ai_value_nom_musd_p50")[cols].to_string(index=False))