## Pillar C: AI Engagement Proxy & Hype Filtering (10-K Textual Analysis)

This pillar utilizes an automated pipeline (`edgar_downloader.py`) to process SEC Form 10-K filings. A critical challenge in quantifying corporate AI investment through textual analysis is the prevalence of "AI-washing" or "cheap talk" by management. Simple buzzword-counting mechanisms often fail to predict true capital expenditure, as they cannot distinguish between vague, forward-looking hype and actual technological implementation. 

To overcome this, our methodology aligns with recent empirical finance literature that leverages context-aware NLP models (e.g., BERT-based architectures) to filter out managerial hype and extract genuine AI engagement signals.

### Key Literature & Applied Methodology

*   **Soto (2025), *Research in Commotion: Measuring AI Research and Development through Conference Call Transcripts* (FEDS):** This paper highlights the fundamental limitations of naive buzzword-counting in financial disclosures, demonstrating that non-contextual keyword frequency lacks predictive power for actual corporate investment and necessitates advanced filtering techniques.
    * **Link:** https://www.federalreserve.gov/econres/feds/files/2025011pap.pdf
*   **Eisfeldt, Schubert, & Zhang (2023), *Generative AI and Firm Values* (NBER):** This study applies advanced contextual language models (RoBERTa) to corporate disclosures to measure firm-level exposure to AI, effectively separating substantial technological integration from superficial managerial mentions.
    * **Link:** https://www.nber.org/system/files/working_papers/w31222/w31222.pdf
*   **Ante & Saggu (2025), *Quantifying a firm's AI engagement* (Technological Forecasting and Social Change):** Provides the blueprint for deriving firm-level AI engagement metrics from 10-K disclosures, which serves as the foundational proxy structure for this pillar.
    * **Link:** https://www.sciencedirect.com/science/article/pii/S0040162524007637