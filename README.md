# Documentation Compliance Agent — WaiverPro

Automated pipeline: ingests guidelines, extracts live app UI, uses an LLM agent to flag discrepancies with citations and screenshots.

## Disclosure
The official WaiverPro guidelines PDF was never provided (points of contact were unreachable per assignment instructions). A stand-in guidelines PDF (`1_ingest/WaiverPro_User_Guidelines_MOCK.pdf`) was generated from the live app's own content, with deliberate documented discrepancies added so the comparison agent has real things to detect. The parser makes no assumptions specific to this mock file — it would run identically against the real PDF.

LLM provider: started with Gemini (free tier returned `limit: 0` quota — account/region issue, not a code bug), switched to Groq (`llama-3.1-8b-instant`), which worked reliably.

## Architecture

1_ingest/    -> PDF guidelines to structured rules (JSON)

2_extract/   -> Playwright login + crawl + screenshot of live app

3_compare/   -> LLM agent compares rules vs UI, flags discrepancies

4_report/    -> Generates final Markdown report

## Setup
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```
`.env`:

GROQ_API_KEY=your_key

## Run
```bash
python 1_ingest/parse_guidelines.py 1_ingest/WaiverPro_User_Guidelines_MOCK.pdf
python 2_extract/scrape_ui.py
python 3_compare/agent.py
python 4_report/generate_report.py
```

## Key challenges solved
- Login form lives at `/login`, not the homepage — found via debug screenshot.
- React-controlled inputs ignored `.fill()` silently — switched to `press_sequentially` + value verification.
- Auth redirect has a multi-second "Logging in..." loading state — replaced fixed delay with `wait_for_url` polling.
- Dashboard pages never reach `networkidle` (continuous polling) — added `domcontentloaded` fallback.

## Coverage
13/13 discovered pages crawled successfully, 0 failures, 585 UI components extracted, 45 guideline rules checked, 62 discrepancies flagged.

## Known limitations
- Mock guidelines PDF, not the real one.
- Per-page rule comparison is overly literal — flags page-specific rules (e.g. "Privacy Policy link in footer") as violations on pages where that rule doesn't really apply, producing some false positives. A retrieval step that maps rules to relevant pages first would fix this.
- No visual/screenshot-based comparison — text only.
- Naive sentence-split fallback (no API key) can break mid-sentence.

## What I'd improve next
- Embedding-based retrieval to match rules to relevant pages before comparing.
- Multimodal comparison using screenshots directly.
- Deduplicate/cluster near-identical discrepancies across pages.