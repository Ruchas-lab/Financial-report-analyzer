# Financial Report Analyzer

> Automating the first-pass financial document review that analysts at consulting and advisory firms perform manually — from ratio calculation to full annual report analysis and executive briefing generation.

## The problem this solves

Financial analysts and consulting associates spend 4–6 hours on a single annual report before they can produce a first-pass briefing for a senior team member. They are manually calculating ratios, scanning for risk language, extracting margin and leverage metrics, and synthesising findings across hundreds of pages of filings.

This tool automates that process — starting with instant ratio analysis and building towards full AI-powered document review.


## What it does

### ✅ v0.1 — Financial Ratio Calculator (live now)
Input raw numbers from any company's income statement and balance sheet and instantly receive:

- **Gross Profit Margin** — core business efficiency after direct costs
- **Net Profit Margin** — actual profit as a percentage of revenue
- **Return on Equity (ROE)** — how effectively the company uses shareholder capital
- **Debt-to-Equity Ratio** — leverage and financial risk indicator
- **Current Ratio** — short-term liquidity health check

Each ratio comes with a plain-English interpretation — not just the number, but what it means for the business.

### 🔄 v0.2 — Financial Report Analyzer (in development)
Upload any annual report PDF and receive:

- **Key financial metrics** — revenue, EBITDA margin, net debt/EBITDA, working capital ratio, YoY changes
- **Risk language detection** — flags going concern disclosures, material uncertainty, covenant references, and impairment indicators
- **Executive briefing** — a structured 5-point summary formatted for senior stakeholder review
- **IFRS vs GAAP identification** — critical context for cross-border analysis
- **Two-company comparison** — side-by-side benchmarking

## Consulting relevance

Ratio analysis is the entry point of every financial engagement. Before a consultant builds a model, before a banker runs a DCF, before an analyst writes a memo — someone calculates these numbers. This tool automates that entry point and adds the interpretive layer that turns raw numbers into business insight.

In 2025–2026, all four Big Four firms — Deloitte (Zora AI), EY, PwC, and KPMG — launched internal AI platforms focused on automating financial statement analysis and risk detection. This project is built on the same underlying logic: domain knowledge in finance, applied through AI, to eliminate low-value manual work.

## Tech stack

| Layer | Tool | Purpose |
|---|---|---|
| Language | Python 3.11 | Core logic |
| Interface | Streamlit | Web dashboard |
| PDF extraction | pdfplumber | Ingests annual report filings *(v0.2)* |
| AI analysis | Claude API | Financial reasoning & summarisation *(v0.2)* |
| Deployment | Streamlit Cloud | Live, shareable URL |

## Project status

| Component | Status |
|---|---|
| Financial ratio calculator | ✅ In development |
| Live Streamlit deployment | 🔄 Planned |
| PDF ingestion & section extraction | 🔄 Planned |
| Financial metrics extraction | 🔄 Planned |
| Risk language detection | 🔄 Planned |
| Executive briefing generator | 🔄 Planned |

## Methodology

The financial analysis logic underpinning this tool — including the risk detection framework and metrics selection — is documented in METHODOLOGY.md.

## About

Built by **Ruchas** — Masters student in International Business & Finance, building at the intersection of financial analysis and applied AI.

Focused on how AI is reshaping the workflow of consulting, investment banking, and corporate finance teams — and building the tools that demonstrate it.

🔗 https://www.linkedin.com/in/rucha-soni-8057011b3/
