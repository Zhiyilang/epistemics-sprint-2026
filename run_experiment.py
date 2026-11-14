#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the tamper-evidence measurement and write results.json (raw data).

Usage: python run_experiment.py
Deterministic: fixed seeds, fixed anchor timestamp, no network, stdlib only.
"""

from __future__ import annotations

import json
import os
import platform
import sys
import time

from audit_log import (ATTACKS, ATTACK_DESCRIPTIONS, MODES, attack,
                       make_anchor, make_records, seal, verify)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results.json")

SEEDS = list(range(40))
RECORDS_PER_LOG = 24
SEALED_AT = "2026-11-14T13:30:00+08:00"
LABEL = "epistemics-sprint-2026-11-14/synthetic-agent-log"


def main() -> int:
    matrix = {a: {m: {"detected": 0, "total": 0, "us": 0.0}
                  for m in MODES} for a in ATTACKS}
    per_seed = []

    for seed in SEEDS:
        bundle = seal(make_records(seed, RECORDS_PER_LOG))
        anchor = make_anchor(bundle, LABEL, SEALED_AT)
        for a in ATTACKS:
            tampered = attack(bundle, a, seed)
            row = {"seed": seed, "attack": a, "detected": {}}
            for m in MODES:
                t0 = time.perf_counter()
                ok, _reason = verify(tampered, anchor, m)
                elapsed_us = (time.perf_counter() - t0) * 1_000_000.0
                cell = matrix[a][m]
                cell["total"] += 1
                cell["us"] += elapsed_us
                if ok:
                    cell["detected"] += 1
                row["detected"][m] = bool(ok)
            per_seed.append(row)

    for a in ATTACKS:
        for m in MODES:
            c = matrix[a][m]
            c["rate"] = round(c["detected"] / c["total"], 4)
            c["mean_verify_us"] = round(c["us"] / c["total"], 2)
            del c["us"]

    payload = {
        "meta": {
            "study": "Anchored hash chains for agent audit logs",
            "track": "2 - Trust Infrastructure",
            "generated_at": SEALED_AT,
            "sprint_window": "2026-11-13 to 2026-11-15 (work performed 2026-11-14, Beijing)",
            "python": platform.python_version(),
            "hash": "SHA-256 with domain separator, canonical JSON",
            "seeds": [SEEDS[0], SEEDS[-1]],
            "trials_per_attack": len(SEEDS),
            "records_per_log": RECORDS_PER_LOG,
            "verifiers": list(MODES),
            "attacks": ATTACK_DESCRIPTIONS,
            "data_note": "Synthetic logs generated deterministically; not real deployment data.",
        },
        "matrix": matrix,
        "per_seed": per_seed,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("wrote", OUT, os.path.getsize(OUT), "bytes")
    print("detection rates (detected / %d trials):" % len(SEEDS))
    header = "%-16s" % "attack" + "".join("%12s" % m for m in MODES)
    print(header)
    for a in ATTACKS:
        print("%-16s" % a + "".join("%12s" % ("%d/%d" % (matrix[a][m]["detected"],
                                                          matrix[a][m]["total"]))
                                   for m in MODES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
