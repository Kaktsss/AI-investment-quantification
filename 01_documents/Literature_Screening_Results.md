# Literature Screening Results — AI Investment Measurement
## Output of the systematic OpenAlex search (screened)

**Method:** Six themed queries via the OpenAlex API → 122 papers retrieved → 51 passed the automated on-topic filter → screened by relevance to *firm-level AI measurement using identifiable data*. Below are the papers that matter, grouped by what they contribute.

---

## Group 1 — Core measurement papers (the methods we build on)

These define the field's measurement approaches and directly support our three-pillar framework.

**Eisfeldt, Schubert & Zhang — "Generative AI and Firm Values" (NBER, 2023).** Firm-level workforce exposure to generative AI, validated against earnings-call data. Unit: exposure index (not dollars). Independently confirms our understanding of the task-exposure family. *This one surfaced in our own search — a good validation that the method finds the right papers.*

**"Quantifying a firm's AI engagement: AI stock indices using 10-K filings" (Tech. Forecasting & Social Change, 2025).** NLP on 10-K filings of 3,395 NASDAQ firms (2010–2022), building AI scores from AI-term frequency. **Directly relevant to Pillar C** — it is essentially the keyword-intensity approach we prototyped, published in a journal. Unit: binary/weighted AI score (not dollars). Data: free (SEC EDGAR). *Strong precedent: it shows our Pillar C design is publishable methodology.*

**"AI focus and firm performance" (J. Academy of Marketing Science, 2022).** Links firms' AI focus in **10-K reports** to operating efficiency. Another 10-K-text precedent for Pillar C.

**"Advanced Technologies Adoption and Use by U.S. Firms: Evidence from the Annual Business Survey" (NBER, 2020).** The Census ABS paper — the aggregate/official-statistics route (the professor's "aggregate data" question). Firm-level microdata exists but is FSRDC-restricted. Unit: adoption indicator.

## Group 2 — Historical parallel (the professor's "internet adoption" pointer)

**Brynjolfsson & Hitt — "Beyond Computation: IT, Organizational Transformation and Business Performance" (JEP, 2000)** and **"The Productivity J-Curve: How Intangibles Complement General Purpose Technologies" (AEJ:Macro, 2020).** These are the direct evidence that the 1990s IT-adoption problem = today's AI problem: intangible capital, poorly captured by accounting, measured via complementary data. The J-Curve paper explicitly frames AI as a GPT with intangible, mismeasured investment — a strong citation for our motivation.

**"IT Assets, Organizational Capabilities, and Firm Performance" (Organization Science, 2007)** and **"Measuring and Explaining Management Practices Across Firms and Countries" (NBER, 2006).** Methodological ancestors: how to measure intangible firm capabilities with survey/asset data.

## Group 3 — Firm-level AI & innovation/productivity (context, mostly proxy)

**"AI and industrial innovation: Evidence from German firm-level data" (Research Policy, 2022):** firm-level AI and innovation, European data. **"AI and firm-level productivity" (JEBO, 2023)** and **"The impact of AI on labor productivity" (2021):** productivity effects, some using patent activity. **"Epidemic effects in the diffusion of… AI" (Research Policy, 2023):** adoption diffusion patterns. These are context/validation rather than new monetary measures.

## Group 4 — Macro / not firm-level (exclude from core, cite for framing only)

Acemoglu "The Simple Macroeconomics of AI" (2024), IMF "Gen-AI" note (2024), the 2017 "Modern Productivity Paradox" (Brynjolfsson) — macro-level, useful for the introduction but not for firm-level measurement.

---

## What this screening tells us (the three takeaways to present)

1. **Our framework matches the published state of the art.** The three families we build on — text/10-K (Pillar C), patents (Pillar B), and acquisition/exposure — all appear as published, peer-reviewed methods. Nothing in our design is off-track.

2. **Pillar C has direct published precedent.** The 2025 "AI stock indices from 10-K filings" paper does almost exactly our keyword approach — which both validates it *and* motivates our planned upgrade to the semantic (Soto-style) measure, since that paper stops at frequency counts and is therefore exposed to the AI-washing critique.

3. **Monetary measurement remains the rare exception.** None of the screened papers produces a clean dollar figure for AI *spending*; the dollar-denominated approaches are patent value (our Pillar B) and, in our extension, acquisition value (Pillar A). This confirms our monetary angle is a genuine contribution, not a reinvention.

---

## Honest note on scope

This screening covered the OpenAlex results (122 papers, 51 on-topic). The three seed papers from the earlier review (Babina et al. JFE 2024; Soto/AIR Index Fed 2025; Chen–Shi–Srinivasan HBS 2024) are the backbone and were verified separately; some did not rank high in the raw OpenAlex citation counts because they are recent. A complete review would also screen Semantic Scholar and the citation graphs of the seed papers — a natural next extension. The full screened CSV (`literature_openalex_v2.csv`) with per-paper coding columns is the working record.
