# README: Pillar B — Market Value of AI Innovation

This section details the data and methodology for **Pillar B**, which measures the monetary value of corporate AI innovations using patent data.

## 1. Replicated Methodology
*   **Main Approach:** This pillar strictly replicates the methodology from **Chen, Shi, & Srinivasan (2024) *"The Value of AI Innovations"* (HBS)**.
*   **Valuation Model:** It applies the **Kogan, Papanikolaou, Seru, and Stoffman (2017)** (KPSS) event-study framework, which estimates the dollar value of a patent based on the firm's abnormal stock return on the grant date.

## 2. Data Files & Sources

*   **`01_Raw_USPTO_AI_Patent_Dataset.csv`**
    *   **Content:** The raw list of US patents including machine-learning-based probabilities (e.g., `predict50_any_ai`) of being AI-related.
    *   **Source:** Official USPTO AI Patent Dataset.
    *   **Link:** https://data.uspto.gov/bulkdata/datasets/ecopatai?code=5_Po3SAK9M5VZl4DYLtcb7uEbGjAPY_o-2oKtyuD2qo&state=97AuTcedPNXDlhxziJtjiFQbEwzWD2FJnpjoFij9UTbsIDjiqyRYYN3hjZjXq1H5&fileDataFromDate=2021-07-30&fileDataToDate=2026-02-03

*   **`02_Raw_KPSS_Patent_Values_2024.csv`**
    *   **Content:** The raw dataset containing the estimated financial value (in millions of dollars) of all publicly traded firms' patents, extended through 2024.
    *   **Source:** Public repository maintained by the Kogan et al. (2017) authors.
    *   **Link:** https://github.com/KPSS2017/Technological-Innovation-Resource-Allocation-and-Growth-Extended-Data/tree/master

*   **`03_Final_Pillar_B_Firm_Year_Panel.csv`**
    *   **Content:** **The final, presentation-ready dataset.** A firm-year panel consisting of 23,955 observations (truncated at 2023). It aggregates the nominal dollar value of AI patents per firm and scales them using integrated Compustat financial data (e.g., Total Assets, CapEx).
    *   **Source:** Output of our custom Python pipeline processing files `01` and `02`.# README: Pillar B — Market Value of AI Innovation

*   ** `Papers`**
    * Technological Innovation, Resource Allocation, and Growth | Oxford Academic by L Kogan · 2017  https://www.aeaweb.org/conference/2013/retrieve.php?pdfid=311 (KPSS methodology)
    * The Value of AI Innovations" | Harvard Business School by Chen, Shi és Srinivasan · 2024 https://www.hbs.edu/ris/download.aspx?name=24-069.pdf (study itself)

This section details the data and methodology for **Pillar B**, which measures the monetary value of corporate AI innovations using patent data.

## 1. Replicated Methodology
*   **Main Approach:** This pillar strictly replicates the methodology from **Chen, Shi, & Srinivasan (2024) *"The Value of AI Innovations"* (HBS)**.
*   **Valuation Model:** It applies the **Kogan, Papanikolaou, Seru, and Stoffman (2017)** (KPSS) event-study framework, which estimates the dollar value of a patent based on the firm's abnormal stock return on the grant date.

## 2. Data Files & Sources

*   **`01_Raw_USPTO_AI_Patent_Dataset.csv`**
    *   **Content:** The raw list of US patents including machine-learning-based probabilities (e.g., `predict50_any_ai`) of being AI-related.
    *   **Source:** Official USPTO AI Patent Dataset.

*   **`02_Raw_KPSS_Patent_Values_2024.csv`**
    *   **Content:** The raw dataset containing the estimated financial value (in millions of dollars) of all publicly traded firms' patents, extended through 2024.
    *   **Source:** Public repository maintained by the Kogan et al. (2017) authors.

*   **`03_Final_Pillar_B_Firm_Year_Panel.csv`**
    *   **Content:** **The final, presentation-ready dataset.** A firm-year panel consisting of 23,955 observations (truncated at 2023). It aggregates the nominal dollar value of AI patents per firm and scales them using integrated Compustat financial data (e.g., Total Assets, CapEx).
    *   **Source:** Output of our custom Python pipeline processing files `01` and `02`.