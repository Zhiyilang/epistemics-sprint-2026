#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assertions for the audit-log experiment, including full re-execution.

Re-runs every (seed, attack, verifier) trial from the primitives and compares
against results.json, so no reported number can be a hand-written claim.
Usage: python eval.py   (exit 0 = all assertions pass)
"""

from __future__ import annotations

import json
import os
import sys

from audit_log import (ATTACKS, MODES, attack, make_anchor, make_records,
                       seal, verify)

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results.json")

SEEDS = list(range(40))
SEALED_AT = "2026-11-14T13:30:00+08:00"
LABEL = "epistemics-sprint-2026-11-14/synthetic-agent-log"

# Expected detection counts. Derived from the design, then verified against data.
EXPECTED = {
    "clean":          {"schema": 0,  "per_record": 0,  "chain": 0,  "anchored": 0},
    "edit_value":     {"schema": 0,  "per_record": 40, "chain": 40, "anchored": 40},
    "delete_middle":  {"schema": 0,  "per_record": 0,  "chain": 40, "anchored": 40},
    "insert_forged":  {"schema": 0,  "per_record": 0,  "chain": 40, "anchored": 40},
    "reorder":        {"schema": 0,  "per_record": 0,  "chain": 40, "anchored": 40},
    "truncate_tail":  {"schema": 0,  "per_record": 0,  "chain": 0,  "anchored": 40},
    "reseal_chain":   {"schema": 0,  "per_record": 0,  "chain": 0,  "anchored": 40},
}


def main() -> int:
    passed = 0
    failed = []

    def ck(label, cond):
        nonlocal passed
        if cond:
            passed += 1
        else:
            failed.append(label)

    with open(RESULTS, encoding="utf-8") as f:
        data = json.load(f)

    ck("meta present", "meta" in data and "matrix" in data and "per_seed" in data)
    ck("40 seeds x 7 attacks = 280 trials", len(data["per_seed"]) == 280)
    ck("meta says sprint-window work",
       "2026-11-14" in data["meta"]["sprint_window"])
    ck("synthetic-data disclosure present", "Synthetic" in data["meta"]["data_note"])

    # 1. Matrix values agree with the expected design pattern.
    for a in ATTACKS:
        for m in MODES:
            cell = data["matrix"][a][m]
            ck("matrix %s/%s count" % (a, m), cell["detected"] == EXPECTED[a][m])
            ck("matrix %s/%s total" % (a, m), cell["total"] == 40)
            ck("matrix %s/%s rate" % (a, m),
               abs(cell["rate"] - cell["detected"] / 40) < 1e-9)
            ck("matrix %s/%s timing measured" % (a, m), cell["mean_verify_us"] > 0)

    # 2. Full independent re-execution, compared trial by trial.
    by_key = {(r["seed"], r["attack"]): r["detected"] for r in data["per_seed"]}
    recomputed = {a: {m: 0 for m in MODES} for a in ATTACKS}
    mismatches = 0
    for seed in SEEDS:
        bundle = seal(make_records(seed, 24))
        anchor = make_anchor(bundle, LABEL, SEALED_AT)
        for a in ATTACKS:
            tampered = attack(bundle, a, seed)
            for m in MODES:
                ok, _ = verify(tampered, anchor, m)
                if ok:
                    recomputed[a][m] += 1
                if by_key.get((seed, a), {}).get(m) != bool(ok):
                    mismatches += 1
    ck("280x4 trials reproduce exactly (0 mismatches)", mismatches == 0)
    for a in ATTACKS:
        for m in MODES:
            ck("recomputed %s/%s" % (a, m), recomputed[a][m] == EXPECTED[a][m])

    # 3. Key scientific claims.
    ck("no false positives on clean logs",
       all(data["matrix"]["clean"][m]["detected"] == 0 for m in MODES))
    ck("unanchored chain fails on truncation",
       data["matrix"]["truncate_tail"]["chain"]["detected"] == 0)
    ck("unanchored chain fails on full re-sealing",
       data["matrix"]["reseal_chain"]["chain"]["detected"] == 0)
    ck("anchor detects every attack",
       all(data["matrix"][a]["anchored"]["detected"] == 40
           for a in ATTACKS if a != "clean"))
    ck("schema-only detects nothing",
       all(data["matrix"][a]["schema"]["detected"] == 0 for a in ATTACKS))

    print("EVAL: %d assertions, %d failed" % (passed + len(failed), len(failed)))
    for f in failed:
        print("  FAIL:", f, file=sys.stderr)
    if failed:
        return 1
    print("EVAL PASS - all numbers reproduced from source primitives")
    return 0


if __name__ == "__main__":
    sys.exit(main())
