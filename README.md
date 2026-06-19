# Documentation Compliance Agent — WaiverPro

An automated pipeline that ingests product guidelines, extracts the live state
of a web application, and uses an LLM agent to flag discrepancies between the
two — with citations and screenshot evidence. Built for the Novulis R&D
engineering assignment ("Building a Documentation Compliance Agent").

---

## 0. Disclosure (read this first)

Section 10 of the assignment names two points of contact for clarification.
I was told **not to contact them under any circumstance**, and the official
"WaiverPro User Guidelines" PDF referenced in Section 3 was never made
available to me.

Rather than stall on a blocked dependency, I treated this as exactly the kind
of ambiguity the assignment says it wants to see handled ("Ask questions
early and often... if anything is unclear, reach out" — Section 1; "Honesty
about limitations" — Section 9, criterion 6). Since asking wasn't an option
here, I:

1. Built and validated the **entire four-stage pipeline** end-to-end against
   the real, live WaiverPro application.
2. For the one missing input — the guidelines PDF — generated a **stand-in
   document** (`1_ingest/WaiverPro_User_Guidelines_MOCK.pdf`), reconstructed
   from the live app's own visible content, with a small number of
   **deliberately introduced, documented discrepancies**. This lets the
   comparison agent demonstrate genuine, verifiable detections instead of
   trivially reporting "fully compliant" against a guideline copied from the
   site itself.
3. `1_ingest/parse_guidelines.py` makes no assumption about the mock content
   — it would run identically against the real PDF if provided later.

I'm flagging this prominently rather than quietly working around it, in line
with Section 9's evaluation criteria.

---

## 1. Pipeline (maps to Assignment Section 3)

| Assignment step                | Implementation                            |
| ------------------------------ | ----------------------------------------- |
| 1. Ingest & Parse              | `1_ingest/parse_guidelines.py`            |
| 2. Extract                     | `2_extract/scrape_ui.py`                  |
| 3. (implicit: store/structure) | `data/ui_states/extracted_ui_state.jsonl` |
| 4. Compare (The AI Agent)      | `3_compare/agent.py`                      |
| 5. Report                      | `4_report/generate_report.py`             |

---

## 2. Setup

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
playwright install chromium
```

`.env` in the project root:

(See Section 6 — "Tool Justification" — for why Groq instead of the
originally-planned Gemini.)

## 3. Running each stage (maps to Assignment Section 8: "How to run each stage")

```bash
# Stage 1: Ingest guidelines PDF -> structured rules
python 1_ingest/parse_guidelines.py 1_ingest/WaiverPro_User_Guidelines_MOCK.pdf

# Stage 2: Extract live UI (login, crawl, screenshot, structured JSONL)
python 2_extract/scrape_ui.py

# Stage 3: Run the comparison agent (batch mode — checks every rule against every page)
python 3_compare/agent.py

# Stage 3 (alt): Ask the agent a specific question (Section 7 examples)
python 3_compare/agent.py --ask "Is the support contact information on the live site correct according to the manual?"

# Stage 4: Generate the final report
python 4_report/generate_report.py
```

Output: `reports/compliance_report.md`

---

## 4. Canonical Data Schema (Assignment Section 5)

Every extracted UI component and every discrepancy follows the exact fields
the assignment specifies:

```json
{
  "page_url": "...",
  "component_type": "button | text_block | nav_item | input | image | ...",
  "component_selector": "structural CSS path, e.g. div#root > div:nth-of-type(2) > button:nth-of-type(1)",
  "actual_text_content": "...",
  "expected_text_content": "... (filled in by Stage 3)",
  "guideline_reference": "Section N: Title (filled in by Stage 3)",
  "discrepancy_flag": true,
  "discrepancy_reason": "... (LLM-generated, filled in by Stage 3)",
  "screenshot_path": "...",
  "retrieved_at": "ISO timestamp"
}
```

Per Section 5's note ("not all components will have text"), missing fields
are stored as explicit `null` rather than omitted or defaulted to empty
strings, so downstream consumers can distinguish "no text" from "not yet
processed."

---

## 5. Extraction & UI State Capture (Assignment Section 6)

**Handling Dynamic Content & Auth:** WaiverPro is a JS-rendered SPA — the raw
HTML payload contains only a title tag and viewport meta, confirmed before
choosing a tool. Login required discovery, since the form is not on the
homepage (see Key Challenges below).

**Structured Output & Evidence:** All components are written to
`data/ui_states/extracted_ui_state.jsonl` (JSONL, not a single JSON array, so
an interrupted run never corrupts already-written data). Every page gets a
full-page screenshot in `data/screenshots/`.

**Resilience:** Every navigation and the login flow itself are wrapped in a
`with_retries()` helper (2 retries, exponential backoff). All retries,
warnings, and errors are logged to `data/extraction_log.jsonl` as
structured, timestamped JSON lines — nothing is silently swallowed.

---

## 6. Tool Justification (Assignment Section 6, "Crucial")

| Decision           | Choice                            | Alternatives considered                    | Why                                                                                                                                                                                                                                                                                                                                                                                                 |
| ------------------ | --------------------------------- | ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Browser automation | **Playwright**                    | Selenium, `requests`+BeautifulSoup         | App is a JS-rendered SPA (verified via raw HTML inspection). Playwright's auto-waiting and `networkidle`/`domcontentloaded` semantics are more reliable for dynamic content than Selenium's manual waits or a non-JS HTTP client.                                                                                                                                                                   |
| PDF parsing        | **pdfplumber**                    | PyPDF2, pypdf                              | Better layout preservation for prose-with-headings documents, which matters for splitting into sections accurately.                                                                                                                                                                                                                                                                                 |
| LLM provider       | **Groq** (`llama-3.1-8b-instant`) | Google Gemini (originally planned), OpenAI | Gemini's free tier returned a hard `limit: 0` quota error on `generate_content` for this account (a project/region-level restriction, not a code bug — confirmed via direct API test outside the pipeline). Groq's free tier worked immediately. All LLM calls are isolated behind small functions (`get_llm_client`, `call_llm`) so swapping providers again is a localized change, not a rewrite. |
| Data format        | **JSON / JSONL**                  | SQLite, CSV                                | The assignment's canonical schema (Section 5) maps directly to JSON objects. JSONL specifically for UI state so the extractor is resumable/streamable.                                                                                                                                                                                                                                              |
| Report format      | **Markdown**                      | HTML, PDF                                  | Git-friendly, renders directly on GitHub, easy to convert later.                                                                                                                                                                                                                                                                                                                                    |

---

## 7. Key Technical Challenges (Assignment Section 4) & How They Were Solved

This section documents the "reliably mapping unstructured, dynamic live UI
states to structured guideline requirements" challenge the assignment calls
out as the core difficulty, plus the concrete dead ends hit along the way.

**1. Login form discovery.** The login form is not on the homepage. The
homepage's only clickable elements (confirmed by dumping all button/link
text during debugging) were product/footer links — no "Sign In" trigger. A
debug screenshot of `/login` showed the actual form lives at that dedicated
route. Fixed by navigating there directly instead of trying to trigger a
modal from the homepage.

**2. React-controlled inputs silently rejecting `.fill()`.** Initial attempts
submitted the form with visibly empty fields and no error — `.fill()` sets
the DOM value directly but didn't trigger the framework's `onChange` state
update. Switched to `.press_sequentially()` (real keystroke events) plus an
explicit `input_value()` check logged after typing, so a future silent
failure would be visible in the logs rather than discovered by accident.

**3. Authentication redirect timing.** After clicking "Login," the UI shows
a multi-second "Logging in..." loading state (cold-start serverless auth)
before redirecting. A fixed delay was unreliable — caught via a debug
screenshot taken right after submit, which showed the loading state mid-flight.
Replaced with `page.wait_for_url()` polling for the URL to leave `/login`
(20s timeout) instead of a guessed sleep duration.

**4. Dashboard pages never reaching `networkidle`.** Authenticated dashboard
routes appear to poll continuously, so `networkidle` reliably timed out.
Added a fallback to `domcontentloaded` specifically when `networkidle` times
out, logged as a warning (not a silent failure) so coverage reporting still
reflects that a lighter wait condition was used.

**5. Per-page-vs-all-rules comparison producing false positives.** Running
every guideline rule against every page (brute-force, no retrieval step)
means page-specific rules sometimes get flagged as "violated" on pages where
they were never meant to apply (e.g. a rule about the My Applications
dashboard layout getting flagged on the Contact page). This is a known,
documented limitation below rather than something papered over.

---

## 8. AI / Comparison Agent (Assignment Section 7)

`3_compare/agent.py` runs two modes:

- **Batch mode** (default): checks every extracted guideline rule against
  every crawled page, flags discrepancies.
- **Query mode** (`--ask "..."`): answers ad-hoc questions like the
  assignment's own examples ("Does the live landing page match the official
  guidelines?", "Is the support contact information correct?") by passing
  all guideline sections plus per-page content into the prompt and requiring
  the model to cite a specific section for every claim.

Every discrepancy and every query-mode answer is required (by prompt
instruction) to cite a `guideline_reference` and ends with the assignment's
required disclaimer: _"This is an automated compliance check generated by an
LLM-based agent. It is NOT a substitute for manual QA review."_

This is structured LLM prompting against retrieved guideline text, not
unconstrained generation — every claim is grounded in the actual section
text passed into the prompt, not the model's general knowledge.

---

## 9. Coverage (Assignment Section 8: "Coverage/completeness report")

Final extraction run: **13/13 discovered pages crawled successfully, 0
failures** — both public pages (`/`, `/privacy`, `/terms`, `/login`) and
authenticated dashboard routes (`my-applications`, `user-management`,
`contact`, `announcements`, `tickets`, `settings`, `faqs`, `action-items`,
`facilities`). 585 UI components extracted. Full numbers in
`data/coverage_report.json` after running Stage 2.

Stage 1 extracted 45 atomic guideline rules from the 9-section mock PDF.
Stage 3 ran 585 rule-vs-page checks and flagged 62 discrepancies (see
limitations below on false-positive rate).

---

## 10. Known Limitations (Assignment Section 9, criterion 6)

- **Mock guidelines PDF**, not the real one (see Disclosure above).
- **Per-page comparison is overly literal.** Without a retrieval step that
  first maps each rule to the page(s) it actually applies to, the agent
  sometimes flags a rule as "violated" on pages where it was never meant to
  apply (e.g. flagging a missing footer link on a settings page when that
  rule was about the public landing page). Real signal (e.g. the waiver
  period date mismatch, the Login-vs-Sign-In button text mismatch) is mixed
  in with this noise rather than cleanly separated.
- **No visual/pixel-level comparison.** The agent compares extracted text
  against guideline text. Screenshots are captured and linked as evidence
  but are not themselves fed into the LLM's reasoning — a wrong color or
  layout shift not reflected in text would not be caught.
- **Naive sentence-split fallback.** If no `GROQ_API_KEY` is set, Stage 1
  falls back to splitting guideline text on periods, which can break
  mid-sentence on line-wrapped text. The LLM-based path doesn't have this
  issue.
- **Single login session, no role-based testing.** Only the provided
  `admin@gmail.com` account was tested.

## 11. What I'd Improve Next (Assignment Section 8)

- Add an embedding-based retrieval step so each rule is only checked against
  pages it's actually relevant to, cutting false positives substantially.
- Feed screenshots directly into a vision-capable LLM call for visual-only
  discrepancy detection.
- Deduplicate/cluster near-identical discrepancies currently repeated across
  multiple pages into a single finding with multiple locations.
- Add run IDs / idempotency keys to `data/` outputs so reruns don't silently
  overwrite previous results.
- Wrap `3_compare/agent.py --ask` in a small CLI/API layer for interactive
  querying rather than one-shot command-line args.
