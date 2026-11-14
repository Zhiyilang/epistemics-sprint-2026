# Anchored Hash Chains for Agent Audit Logs

AI x Epistemics Research Sprint (13–15 Nov 2026), **Track 2 — Trust Infrastructure**.
Study written on 14 Nov 2026 during the sprint window. MIT licensed. Python standard library only.

**English.** We measure what four verifier designs actually guarantee against six tampering attacks on a synthetic AI-agent audit log. Across 40 seeds (280 trials, 1,120 verifier calls), structural validation detected nothing, per-record hashes caught only in-place edits, and an unanchored hash chain failed against truncation and full re-sealing. Only a chain checked against an independent external witness detected all six attacks with zero false positives. Conclusion: the minimal missing layer in agent observability is an anchor, not a chain.

**中文.** 本研究测量四种日志校验方式在六种篡改攻击下的真实检出能力。40 个固定种子、280 次试验、1,120 次校验调用的实测显示：仅做结构校验全部检不出；逐条哈希只能发现原地改值；无外部锚点的哈希链对「截断末尾」和「整链重算」完全失效（各 0/40）；只有与外部独立见证比对的锚定链对六种攻击全部 40/40 检出，且对未篡改日志 0/40 误报。结论：AI agent 可观测性标准里缺的不是哈希链，而是独立锚点。

## Files

| File | Purpose |
| --- | --- |
| `REPORT.md` / `REPORT.pdf` | Research report (submission deliverable, ≤8 pages) |
| `audit_log.py` | Log generation, sealing, six attacks, four verifiers |
| `run_experiment.py` | Produces `results.json` with raw per-trial outcomes |
| `results.json` | Raw measurement data (61 KB, 280 trials) |
| `eval.py` | Re-executes all 1,120 verifier calls; exit 0 = reproduced |
| `validate.py` | Artefact, format, section and credential checks |
| `make_pdf.py` | Renders `REPORT.md` to `REPORT.pdf` (4 pages) |
| `probe_form.py` / `probe_form_result.json` | Read-only GET probe of the official form (0 POST) |
| `probe_window.py` / `window_check.json` | Read-only GET re-verification of the sprint window (0 POST) |
| `push_public.py` / `push_verify.json` | Public GitHub/Gitee mirror with byte-for-byte read-back |
| `LICENSE` | MIT |
| `SUBMISSION.md` | Submission metadata and deadline notes |

## Official window verification (14 Nov 2026, 13:4x Beijing)

`python probe_window.py` fetched the sprint page with one GET: **HTTP 200**,
`719,338` bytes, `sha256 39cb04c3167bb6d3…`, title
`AI x Epistemics Research Sprint | Apart Research`. The page still says
verbatim `"Live now."`, `"Submissions close Sunday, November 15 at 11:59 PM
Anywhere on Earth (AoE)"`, `"$2,000 in cash prizes across all tracks"`,
`"Teams of one to five people"` and `"No prior background in AI safety is
required"`. The submission form is reachable by GET (`PDF File`,
`ProjectTitle_Framer`, `Tracks`, `$ACTION_KEY`, `project-submission`,
`success-submission`). No eligibility, deadline or prize change was found.
`window_check.json` stores the exact quotes and contexts. **POST count = 0.**

The measurement was independently re-executed in a clean temporary directory
from `audit_log.py` + `run_experiment.py`: all 280 trials and the full 7×4
detection matrix matched `results.json` exactly (only timing fields differ,
as expected).

## Reproduce

```bash
python run_experiment.py
python eval.py
python validate.py
```

No network, no API keys, no third-party packages. The logs are synthetic; see REPORT.md §5 for limitations.

## Licence

MIT. See `LICENSE`.
