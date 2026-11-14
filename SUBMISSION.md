# Submission metadata — AI x Epistemics Research Sprint ($2,000)

> Prepared 2026-11-14 during the sprint window. **This file is a hand-off note, not a submission.**
> The single-submission gate `7ff4841e` is scheduled for **2026-11-16 15:00 (Beijing)** and is the only component allowed to POST the official form.

## Verified official facts (read-only GET, 2026-11-14)

**Second independent re-check 2026-11-14 13:4x Beijing (`probe_window.py` →
`window_check.json`): HTTP 200, 719,338 B, sha256 `39cb04c3167bb6d3…`, title
`AI x Epistemics Research Sprint | Apart Research`, `Live now.` still present.
All five quoted strings below were found verbatim in the page text (deadline
×1, prize ×1, team ×1, no-background ×1, results ×1); tracks `Trust
Infrastructure` and `Epistemic Products` still appear. Dollar amounts found:
`$2,000`, `$1,000`, `$500`, `$300`, `$100`. Form reachable by GET. **No
eligibility / deadline / prize change. POST count 0.** Exclusion-term scan
(`not eligible`, `excluding`, `residents of`, `must be 18`,
`18 years of age`, `country restrictions`) returned 0 hits each — this is a
text scan, not a legal determination.

**Independent reproduction of the measurement (13:4x):** the experiment was
re-run from scratch in a clean temp directory using only `audit_log.py` +
`run_experiment.py`. All 280 per-seed trials and the full 7×4 detection matrix
matched `results.json` exactly; only `mean_verify_us` timing fields and the
Python version differ, as expected. `eval.py` 150 assertions / 0 failed;
`validate.py` 41 passed / 0 failed; `REPORT.pdf` 4 pages / 186,249 B /
sha256 `c5c5728f7540f244e7502d89…` unchanged.

- Sprint page: `https://apartresearch.com/sprints/ai-x-epistemics-research-sprint-2026-11-13-to-2026-11-15` — status **Live now.**
- Deadline verbatim: **"Submissions close Sunday, November 15 at 11:59 PM Anywhere on Earth (AoE)"** = **Beijing 2026-11-16 19:59**. (The page displays `Nov 16, 12:59 PM` for CET/UTC+1; that is not Beijing time.)
- Prizes verbatim: **"$2,000 in cash prizes across all tracks"** — 1st $1,000 / 2nd $500 / 3rd $300 / 4th $100 / 5th $100.
- Eligibility verbatim: **"Teams of one to five people"**, **"No prior background in AI safety is required"**; no country or age exclusion found on the page.
- Results verbatim: **"Results and winners are announced about 1 to 2 weeks after the judging deadline"**.
- Rubric (from the sprint prep notes, not re-verified on the page this round): technical quality and clarity of presentation, each 1–5. Report ≤8 pages, abstract 150–250 words, mandatory Limitations and Dual-Use appendix.

## Form values (for the gate to use)

| Field | Value |
| --- | --- |
| Project title | What Does "Tamper-Evident" Actually Buy You? Measuring Anchored Hash Chains for Agent Audit Logs |
| Track | 2 — Trust Infrastructure |
| Author / affiliation | Zhi Yilang · ZhiYiLab (independent) · Shanghai, China |
| Abstract | `REPORT.md` § Abstract — 228 words (measured) |
| PDF | `REPORT.pdf` (generated from `REPORT.md`, ≤8 pages) |
| Repository | optional; see below |
| Video | not produced (optional) |

## Package status

- `run_experiment.py` → `results.json` **61,633 B**, 280 raw trials, all numbers real.
- `eval.py` → **150 assertions, 0 failed, exit 0** (re-executes all 1,120 verifier calls).
- `validate.py` → run before the gate; checks artefacts, PDF header/trailer/pages, sections, abstract length, bilingual README, credential scan.
- `REPORT.md` → 1,842 words; includes Abstract, Method, Results, Discussion, Limitations, Dual-Use / Ethical Considerations, References, and Appendix A (sprint-window / pre-existing declaration).
- `REPORT.pdf` → **4 pages / 186,249 B**, `%PDF-` header + `%%EOF` trailer verified (within the 8-page limit). Rebuild with `python make_pdf.py`; sha256 prefix `c5c5728f7540f244e7502d89`.
- `validate.py` → artefact, format, section, abstract-length, reproducibility and credential checks.
- Font/format deviation disclosed in §5: the official template could not be retrieved, so the required structure is followed with our own typesetting.

## Transport risk found 2026-11-14 (critical)

`_apart_submit.py` is **not** parameterised: `SPRINT_URL`, `SPRINT_SLUG`, `TITLE`, `PDF_FILENAME`, `FALLBACK_PDF_URL`, the hard-coded form action anchor, `abstract_from_report()`, `report_data_is_sprint_safe()` and `SPRINT_START` all point at the already-submitted **Swarm** sprint. The original gate prompt's phrase "only change the sprint slug" was wrong; following it could have caused a second POST to Swarm and destroyed that $4k entry.

Mitigations now in place:
- `probe_form.py` — pure GET probe of the Epistemics form; `probe_form_result.json` (2,403 B) records the real action and field names. **0 POST.**
- The 11-16 gate prompt now forbids `_apart_submit.py --submit` / `--upload-only`, forbids any POST to a `swarm-alignment` URL, and requires a sprint-specific payload plus a dry-run assertion that no `swarm` string appears anywhere.

## Hard constraints for `7ff4841e`

1. Idempotency first: if `.workbuddy/epistemics_submit_attempted.json` exists, stop with no POST.
2. Only submit if the form is still open, the sprint slug/field names are read live from the page, and `validate.py` exits 0.
3. Write the marker **before** the POST. If the POST fails or the result is ambiguous, **never retry** — a duplicate research submission is riskier than a missed one.
4. No emails, no user prompts, no action cards, no sign-up, no real-name verification, no payment handling.
5. Honest accounting: cumulative received is still **¥0 / $0**; do not claim a win, shortlist, or payment.
