import pandas as pd

AIPD_PATH = r"C:\Users\Fekete Marci\08_Corpfin_work\AI_project\data\ai_model_predictions.csv"
KPSS_PATH = r"C:\Users\Fekete Marci\08_Corpfin_work\AI_project\data\KPSS_2024.csv"
OUT_PATH  = r"C:\Users\Fekete Marci\08_Corpfin_work\AI_project\data\firm_ai_patent_value_v2.csv"

print("Reading AIPD (only needed columns)...")
aipd = pd.read_csv(
    AIPD_PATH,
    usecols=["doc_id", "flag_patent", "pub_dt",
             "predict50_any_ai", "predict86_any_ai", "predict93_any_ai"],
    dtype={"doc_id": str},
    low_memory=False,
)

# --- DIAGNOSTIC 1: what does AIPD actually cover? -----------------------
aipd["pub_year"] = pd.to_datetime(aipd["pub_dt"], errors="coerce").dt.year
print("\n=== AIPD coverage (MEASURED, not assumed) ===")
print(f"Rows: {len(aipd):,}  |  granted patents (flag_patent=1): "
      f"{(aipd['flag_patent']==1).sum():,}")
print(f"pub_year range: {aipd['pub_year'].min()} - {aipd['pub_year'].max()}")
print("Last 6 years, row counts:")
print(aipd["pub_year"].value_counts().sort_index().tail(6).to_string())

# Granted patents only:
aipd = aipd[aipd["flag_patent"] == 1].copy()
aipd = aipd.rename(columns={"doc_id": "patent_num"})

print("\nReading KPSS...")
kpss = pd.read_csv(
    KPSS_PATH,
    usecols=["patent_num", "permno", "issue_date", "xi_nominal", "xi_real"],
    dtype={"patent_num": str, "permno": str, "issue_date": str},
    low_memory=False,
)
kpss["year"] = kpss["issue_date"].str[:4].astype(int)
kpss = kpss.dropna(subset=["permno"])
kpss["xi_nominal"] = pd.to_numeric(kpss["xi_nominal"], errors="coerce")
kpss["xi_real"] = pd.to_numeric(kpss["xi_real"], errors="coerce")

print("=== KPSS coverage ===")
print(f"Rows: {len(kpss):,}  |  year range: {kpss['year'].min()} - {kpss['year'].max()}")

# --- Merge --------------------------------------------------------------
merged = kpss.merge(aipd, on="patent_num", how="inner")

# --- DIAGNOSTIC 2: where does the MERGED AI sample end? ------------------
ai = merged[merged["predict50_any_ai"] == 1]
print("\n=== Merged AI patents (predict50) by grant year, last 8 years ===")
yearly_diag = (ai.groupby("year")
                 .agg(n_patents=("patent_num", "count"),
                      total_xi_nominal=("xi_nominal", "sum")))
print(yearly_diag.tail(8).to_string())
print("\n^^ If counts collapse after a certain year, that is the AIPD")
print("   truncation point - Pillar B's series must be cut there.")

# --- Firm-year aggregation, all thresholds, both units -------------------
def agg_for(flag_col, label):
    sub = merged[merged[flag_col] == 1]
    g = (sub.groupby(["permno", "year"])
            .agg(**{f"n_ai_patents_{label}": ("patent_num", "count"),
                    f"ai_value_nom_musd_{label}": ("xi_nominal", "sum"),
                    f"ai_value_real_musd_{label}": ("xi_real", "sum")})
            .reset_index())
    return g

out = agg_for("predict50_any_ai", "p50")
for col, lab in [("predict86_any_ai", "p86"), ("predict93_any_ai", "p93")]:
    out = out.merge(agg_for(col, lab), on=["permno", "year"], how="left")

out.to_csv(OUT_PATH, index=False)
print(f"\nSaved: {OUT_PATH}  ({len(out):,} firm-year rows)")
print("\nTop 5 by nominal AI value (p50):")
print(out.nlargest(5, "ai_value_nom_musd_p50")[
    ["permno", "year", "n_ai_patents_p50",
     "ai_value_nom_musd_p50", "ai_value_real_musd_p50"]].to_string(index=False))