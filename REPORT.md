# What Does "Tamper-Evident" Actually Buy You? Measuring Anchored Hash Chains for Agent Audit Logs

**Track 2 — Trust Infrastructure** · AI x Epistemics Research Sprint, 13–15 November 2026

**Author:** Zhi Yilang · ZhiYiLab (independent) · Shanghai, China · [github.com/Zhiyilang](https://github.com/Zhiyilang)

---

## Abstract

Audit logs are routinely described as tamper-evident, yet the phrase rarely states which adversary is being considered. We measure what four verifier designs actually guarantee against six concrete tampering attacks on a synthetic AI-agent audit log. Each trial seals 24 records with a SHA-256 hash chain, applies one attack, and runs four verifiers: structural schema validation, independent per-record hashing, an unanchored hash chain, and the same chain checked against an external witness recording the original head, record count and content digest. Across 40 fixed seeds per attack (280 trials, 1,120 verifier calls), structural validation detected zero attacks. Per-record hashes detected only in-place edits (40/40) and missed deletion, insertion, reordering, truncation and re-sealing. The unanchored chain detected edits, deletion, insertion and reordering (40/40 each) but detected neither truncation of the last three entries nor a complete re-sealing of the chain (0/40 for both), because a self-consistent chain carries no information about the chain it replaced. Only the external witness detected all six attacks (40/40 each) while producing zero false positives on unmodified logs (0/40). We conclude that the minimal missing layer in agent observability is not chaining but an independently stored anchor, and that claims of tamper-evidence should state where that anchor lives and who controls it. All code, raw trial data and assertions are included; the logs are synthetic, so these are mechanism results rather than deployment estimates.

---

## 1. Question

Track 2 asks which source-reliability and provenance techniques are hardest to cheat, and what minimal tamper-evident layer is missing from today's AI observability standards. A common answer in agent tooling is "hash-chain the log": every entry commits to the previous one, so any edit should break the chain. That answer is attractive because it needs no ML and no infrastructure beyond SHA-256. We test it directly. Our hypothesis was that an unanchored chain protects against *sloppy* edits but fails against an adversary who can rewrite the log and recompute the chain, and that an externally stored witness is the actual minimal requirement.

## 2. Method

**Data.** We generate deterministic synthetic agent audit logs with 24 records each (seeds 0–39). A record carries `seq`, `actor`, `action`, `claim`, `source_ref` and `timestamp`. These are synthetic logs of the kind an agentic research or negotiation system might emit; no real deployment data is used.

**Sealing.** With domain-separated SHA-256 over canonical JSON, each entry stores `hash = H({record, prev})` where `prev` is the preceding entry's hash (the first is 64 zero bytes). The bundle stores the final `head` and `count`. An external *anchor* — modelled as an independent, append-only witness — stores the original head, count and a digest of the full record list.

**Verifiers (increasing strength).**

| Verifier | What it checks |
| --- | --- |
| `schema` | Every entry has the required fields with legal types; hash strings are 64 hex chars. No values are recomputed. |
| `per_record` | Above, plus every entry's own hash is recomputed. No link between entries is checked. |
| `chain` | Above, plus every `prev` equals the preceding hash and `head` equals the last hash. No external reference. |
| `anchored` | Above, plus `head`, `count` and the content digest are compared with the external witness. |

**Attacks.** Six tampering operations, each applied to a fresh copy of the sealed bundle; the attacker never updates the witness. (i) `edit_value`: change one claim, recompute nothing. (ii) `delete_middle`: remove one middle entry. (iii) `insert_forged`: insert a forged entry whose own hash is correctly computed. (iv) `reorder`: swap two adjacent entries. (v) `truncate_tail`: drop the last three entries and update head/count to match, leaving a self-consistent prefix. (vi) `reseal_chain`: change one claim, then recompute the entire chain from scratch. `clean` is the unmodified control.

**Protocol.** 40 seeds × 7 conditions × 4 verifiers = 1,120 verification calls. A call is counted as a detection when the verifier reports tampering. `eval.py` re-executes all 1,120 calls from the primitives and compares them trial-by-trial with `results.json`; every number below is reproduced, not transcribed.

## 3. Results

Detections out of 40 trials per condition:

| Attack | `schema` | `per_record` | `chain` | `anchored` |
| --- | --- | --- | --- | --- |
| `clean` (control) | 0 | 0 | 0 | 0 |
| `edit_value` | 0 | **40** | **40** | **40** |
| `delete_middle` | 0 | 0 | **40** | **40** |
| `insert_forged` | 0 | 0 | **40** | **40** |
| `reorder` | 0 | 0 | **40** | **40** |
| `truncate_tail` | 0 | 0 | **0** | **40** |
| `reseal_chain` | 0 | 0 | **0** | **40** |

Four findings. (1) Structural validation is worthless against tampering: it detected 0/240 attacks while remaining silent on all 40 clean logs. (2) Independent per-record hashes catch only edits that leave the entry's hash stale; deleting a whole entry, inserting a well-formed one, or reordering entries preserves each surviving entry's own hash and goes unnoticed. (3) Hash chaining fixes those three cases via `prev` links, but **cannot detect truncation or full re-sealing** — both produce an internally consistent chain, and without an external reference the verifier has no way to know a different (or shorter) chain ever existed. (4) The anchored verifier detected all 240 tampered trials and produced no false positives on the 40 clean trials.

Mean verification cost was 0.43–1.64 ms per call across all conditions (std-lib SHA-256, 24 records, Python 3.13.14 on a general-purpose OS). These microbenchmarks are noisy and are reported only to show the overhead is negligible; no performance claim is made.

## 4. Discussion

The result is a scope condition, not a bug in hash chains. A chain is a *consistency* check: it proves the entries in front of you belong together. It is not an *existence* or *completeness* check: it cannot prove these are all the entries, or that they are the original ones. Conflating the two is what makes a log merely "tamper-evident" in marketing language while remaining trivially forgeable by anyone who controls the log file. For AI agent observability this matters because the party with the strongest incentive to rewrite a record is often the party operating the agent — precisely the party who can recompute the chain.

The minimal missing layer is therefore an anchor: a head hash, record count and content digest held somewhere the log writer cannot rewrite — an append-only store, a third-party timestamp, a transparency log, or a signed receipt held by a counterparty. Our `anchored` condition models this idealisation. We recommend observability standards require providers to state (a) where the anchor is stored, (b) who controls it, and (c) at what interval it is published, rather than accepting "hash-chained" as a sufficient description.

## 5. Limitations

- **Synthetic data.** Logs are generated, not collected from a live agent deployment. Detection rates are properties of the mechanism under a known attack set, not estimates of real-world tamper frequency.
- **Idealised anchor.** The witness is assumed immutable and out of the attacker's reach. An attacker who can alter both log and anchor still wins; the experiment does not model key compromise, collusion, or anchor rollback.
- **Limited adversary.** Six attacks only. We do not cover selective disclosure over long horizons, timestamp forgery, side channels, or application-level semantic edits that never touch the log.
- **No proof.** This is an empirical mechanism measurement, not a formal security reduction.
- **Timing noise.** The reported microsecond figures come from a shared OS and vary between runs; they support no performance conclusion.
- **Scope.** A three-day solo sprint. No user study, no integration into an existing agent framework, no evaluation of storage cost, privacy, or usability.
- **Format deviation.** The official report template could not be retrieved during this sprint; this document follows the stated requirements (title, 150–250 word abstract, author, ≤8 pages, Limitations and Dual-Use appendix) using our own typesetting.

## 6. Dual-Use / Ethical Considerations

**Benefit.** Cheap, auditable records of what an agent claimed, cited and committed to could help institutions verify AI-assisted decisions, attribute errors, and detect retroactive narrative changes. The finding that an anchor is required gives implementers a concrete, low-cost design requirement.

**Risk.** We describe and implement six attacks, including full chain re-sealing. The same technique could be used to make a falsified log look internally consistent to a weak verifier. We mitigate this in three ways: the code operates only on synthetic logs and cannot be pointed at a real log store; we publish the failure mode prominently so that "hash-chained" is not mistaken for a complete defence; and we do not provide tooling for identifying or modifying production audit systems. We believe the defensive value of stating the failure mode outweighs the marginal uplift to an attacker who already controls the log file — such an attacker can trivially re-seal a chain without our code.

No personal, proprietary or user data was collected or processed. All artefacts are synthetic and MIT-licensed.

## References

1. Haber, S. and Stornetta, W. S. (1991). How to Time-Stamp a Digital Document. *Journal of Cryptology*, 3, 99–111.
2. Laurie, B., Langley, A. and Kasper, E. (2013). Certificate Transparency. *RFC 6962*, IETF.
3. Merkle, R. C. (1979). *Secrecy, Authentication, and Public Key Systems*. PhD thesis, Stanford University.
4. National Institute of Standards and Technology (2015). *FIPS PUB 180-4: Secure Hash Standard (SHS)*.
5. Coalition for Content Provenance and Authenticity (C2PA). *Content Credentials / C2PA Technical Specification*, c2pa.org.
6. Apart Research (2026). *AI x Epistemics Research Sprint — Track 2: Trust Infrastructure*. apartresearch.com/sprints/ai-x-epistemics-research-sprint-2026-11-13-to-2026-11-15

---

## Appendix A — Sprint-window and pre-existing work declaration

- **All research content in this submission was produced during the sprint window**, on 14 November 2026 (Beijing time), after the sprint opened on 13 November: `audit_log.py`, `run_experiment.py`, `eval.py`, `validate.py`, `results.json`, `REPORT.md`, `REPORT.pdf`, `README.md`, `LICENSE`, `SUBMISSION.md`. The experiment timestamp is fixed at `2026-11-14T13:30:00+08:00` in `results.json`.
- **Pre-existing (not counted as sprint work):** the author's earlier open-source repositories `swarmbox` and `collusionlab` informed the general notion of agent action logs; no code from them is used here. The project-level utility `_md2pdf.py` (written before the sprint) was used only for Markdown-to-PDF typesetting and is not a research contribution. The Apart submission form helper `_apart_submit.py` is a pre-existing transport tool and is not part of this study.
- No pre-existing experimental data, figures or results were reused. Every number in Section 3 comes from `results.json`, produced by `run_experiment.py` during the sprint and re-verified by `eval.py`.

## Appendix B — Reproducibility

```bash
cd epistemics
python run_experiment.py     # writes results.json (280 trials, raw per-trial outcomes)
python eval.py               # re-executes all 1,120 verifier calls; exit 0 = reproduced
python validate.py           # artefacts, PDF headers/pages, required sections, no credentials
python make_pdf.py              # Markdown -> PDF (private Chrome user-data-dir)
```

Requirements: Python 3.9+ standard library only. No network access, no API keys, no third-party packages.
