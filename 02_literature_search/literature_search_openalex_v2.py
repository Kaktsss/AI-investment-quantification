import time
import re
import requests
import pandas as pd

MY_EMAIL = "marcell.fekete.1@hu-berlin.de"
BASE = "https://api.openalex.org/works"

# Two groups: modern AI measurement (2018+) and historical IT adoption.
AI_QUERIES = {
    "firm_ai_investment": "firm-level artificial intelligence investment measurement",
    "ai_adoption":        "firm artificial intelligence adoption measurement",
    "ai_exposure":        "generative AI firm value stock returns exposure",
    "ai_patents_value":   "artificial intelligence patents firm market value",
    "ai_disclosure_nlp":  "artificial intelligence earnings calls 10-K textual analysis",
}
HISTORICAL_QUERIES = {
    "it_adoption_history": "information technology adoption firm productivity Brynjolfsson Hitt",
}

# A paper is kept only if title+abstract mention at least one term from EACH
# of these two groups: it must be about AI/tech AND about firms/measurement.
TOPIC_TERMS = ["artificial intelligence", r"\bAI\b", "machine learning",
               "generative", "patent", "algorithm"]
FIRM_TERMS = ["firm", "investment", "adoption", "corporate", "productivity",
              "market value", "stock", "measure", "exposure", "R&D"]

def reconstruct_abstract(inv_index):
    if not inv_index:
        return ""
    positions = {}
    for word, idxs in inv_index.items():
        for i in idxs:
            positions[i] = word
    return " ".join(positions[i] for i in sorted(positions))

def search(query, per_page=25, min_year=None):
    params = {"search": query, "per-page": per_page, "mailto": MY_EMAIL,
              "sort": "relevance_score:desc"}
    if min_year:
        params["filter"] = f"from_publication_date:{min_year}-01-01"
    r = requests.get(BASE, params=params, timeout=60)
    r.raise_for_status()
    out = []
    for w in r.json().get("results", []):
        authors = [a["author"]["display_name"]
                   for a in w.get("authorships", [])][:6]
        venue = ((w.get("primary_location") or {}).get("source") or {}).get(
            "display_name", "")
        out.append({
            "title": w.get("title", "") or "",
            "year": w.get("publication_year"),
            "authors": "; ".join(authors),
            "venue": venue,
            "cited_by": w.get("cited_by_count", 0),
            "doi": w.get("doi", ""),
            "abstract": reconstruct_abstract(w.get("abstract_inverted_index")),
        })
    return out

def is_on_topic(row):
    """Keep only papers mentioning BOTH a tech term AND a firm/measure term."""
    text = f"{row['title']} {row['abstract']}".lower()
    has_topic = any(re.search(t.lower(), text) for t in TOPIC_TERMS)
    has_firm = any(f.lower() in text for f in FIRM_TERMS)
    return has_topic and has_firm

def run(queries, min_year, label):
    rows = []
    for theme, q in queries.items():
        print(f"[{label}] querying '{theme}' ...")
        try:
            for paper in search(q, min_year=min_year):
                paper["search_theme"] = theme
                rows.append(paper)
        except Exception as e:
            print(f"  ERROR on '{theme}': {e}")
        time.sleep(1)
    return rows

def main():
    ai_rows = run(AI_QUERIES, 2018, "AI")
    hist_rows = run(HISTORICAL_QUERIES, None, "HIST")
    df = pd.DataFrame(ai_rows + hist_rows)

    # On-topic filter (applied to AI rows; historical kept as-is)
    df["on_topic"] = df.apply(is_on_topic, axis=1)

    # Deduplicate, recording all themes a paper matched
    themes = (df.groupby("title")["search_theme"]
                .apply(lambda s: "; ".join(sorted(set(s)))))
    df = df.drop_duplicates(subset="title").copy()
    df["found_under_themes"] = df["title"].map(themes)
    df = df.drop(columns=["search_theme"])

    # Empty screening columns for manual coding (the review workflow)
    for col in ["SCREEN_relevant_yn", "data_source", "ai_measure_unit",
                "monetary_yn", "sample", "validation", "data_free_or_commercial"]:
        df[col] = ""

    df = df.sort_values(["on_topic", "cited_by"],
                        ascending=[False, False]).reset_index(drop=True)
    df.to_csv("literature_openalex_v2.csv", index=False)
    df.to_excel("literature_openalex_v2.xlsx", index=False)

    n_on = df["on_topic"].sum()
    print(f"\nSaved {len(df)} papers ({n_on} pass the on-topic filter) "
          f"to literature_openalex_v2.csv")
    print("\nTop 20 on-topic papers (screen these first):")
    view = df[df["on_topic"]].head(20)
    print(view[["title", "year", "venue", "cited_by"]].to_string(index=False))
    print("\nWorkflow: open the CSV, read abstracts of on-topic papers, fill "
          "SCREEN_relevant_yn and the data_* columns for the relevant ones.")

if __name__ == "__main__":
    main()
