#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tamper-evident audit log primitives for the AI x Epistemics Research Sprint.

Track 2 - Trust Infrastructure. Zero third-party dependencies (stdlib only).

The module builds a synthetic agent audit log, seals it with a SHA-256 hash
chain, applies six realistic tampering attacks, and compares four verifier
strengths. All measurements in the report come from run_experiment.py calling
these functions on fixed seeds.

Written during the sprint window (2026-11-14, Beijing time). MIT licensed.
"""

from __future__ import annotations

import copy
import hashlib
import json
import random

DOMAIN = b"epistemics-audit-chain-v1|"
ZERO = "0" * 64

ACTORS = ("research-agent", "retriever", "verifier", "executor")
ACTIONS = ("claim", "cite", "revise", "commit", "retract")
CLAIMS = (
    "source A supports the forecast",
    "confidence in the estimate is high",
    "the earlier figure was superseded",
    "no contradictory evidence was found",
    "the commitment was accepted by the team",
    "the citation could not be resolved",
)
SOURCES = (
    "urn:doc:council-minutes:2026-10-02:p4",
    "urn:doc:internal-memo:2026-10-07:s2",
    "urn:doc:press-release:2026-10-11:p1",
    "urn:doc:dataset-snapshot:2026-10-15:r3",
)

FIELDS = ("seq", "actor", "action", "claim", "source_ref", "timestamp")


def canon(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def digest(obj) -> str:
    return hashlib.sha256(DOMAIN + canon(obj)).hexdigest()


def make_records(seed: int, n: int = 24) -> list[dict]:
    """Deterministic synthetic agent audit log. NOT real deployment data."""
    rng = random.Random(seed)
    out = []
    for i in range(n):
        out.append({
            "seq": i + 1,
            "actor": rng.choice(ACTORS),
            "action": rng.choice(ACTIONS),
            "claim": rng.choice(CLAIMS),
            "source_ref": rng.choice(SOURCES),
            "timestamp": "2026-11-14T%02d:%02d:00+08:00" % (9 + i // 12, (i * 7) % 60),
        })
    return out


def seal(records: list[dict]) -> dict:
    """Chain records: each entry commits to the previous entry's hash."""
    entries = []
    prev = ZERO
    for rec in records:
        body = {"record": rec, "prev": prev}
        h = digest(body)
        entries.append({"record": copy.deepcopy(rec), "prev": prev, "hash": h})
        prev = h
    return {"format": "epistemics-chain-v1", "entries": entries,
            "head": prev, "count": len(entries)}


def make_anchor(bundle: dict, label: str, sealed_at: str) -> dict:
    """Independent witness: stored outside the log's reach in real deployments."""
    return {
        "label": label,
        "head": bundle["head"],
        "count": bundle["count"],
        "records_digest": digest([e["record"] for e in bundle["entries"]]),
        "sealed_at": sealed_at,
    }


def _is_hex64(s) -> bool:
    return isinstance(s, str) and len(s) == 64 and all(c in "0123456789abcdef" for c in s)


def _schema_ok(bundle: dict) -> bool:
    """Structural validation only: fields exist and have legal types."""
    if not isinstance(bundle, dict) or bundle.get("format") != "epistemics-chain-v1":
        return False
    entries = bundle.get("entries")
    if not isinstance(entries, list) or not entries:
        return False
    for e in entries:
        if not isinstance(e, dict) or not _is_hex64(e.get("hash")) or not _is_hex64(e.get("prev")):
            return False
        r = e.get("record")
        if not isinstance(r, dict):
            return False
        for f in FIELDS:
            if f not in r:
                return False
        if not isinstance(r["seq"], int) or isinstance(r["seq"], bool):
            return False
        for f in ("actor", "action", "claim", "source_ref", "timestamp"):
            if not isinstance(r[f], str):
                return False
    return True


def _self_hash_ok(e: dict) -> bool:
    return digest({"record": e["record"], "prev": e["prev"]}) == e["hash"]


def _chain_links_ok(entries: list[dict]) -> bool:
    for i, e in enumerate(entries):
        expected = ZERO if i == 0 else entries[i - 1]["hash"]
        if e["prev"] != expected:
            return False
    return True


def verify(bundle: dict, anchor: dict | None, mode: str) -> tuple[bool, str]:
    """Return (tampering_detected, reason). Modes: schema, per_record, chain, anchored."""
    if not _schema_ok(bundle):
        return True, "schema-invalid"
    entries = bundle["entries"]

    if mode == "schema":
        return False, "structure-valid"

    if mode in ("per_record", "chain", "anchored"):
        for i, e in enumerate(entries):
            if not _self_hash_ok(e):
                return True, "self-hash-mismatch@%d" % i
        if mode == "per_record":
            return False, "each-record-hash-valid"

        if not _chain_links_ok(entries):
            return True, "broken-prev-link"
        if bundle.get("head") != entries[-1]["hash"]:
            return True, "head-mismatch"
        if mode == "chain":
            return False, "chain-internally-consistent"

        # anchored: the witness is an independent record of the original seal
        if anchor is None:
            return False, "no-witness-available"
        if bundle.get("head") != anchor.get("head"):
            return True, "witness-head-mismatch"
        if bundle.get("count") != anchor.get("count"):
            return True, "witness-count-mismatch"
        if digest([e["record"] for e in entries]) != anchor.get("records_digest"):
            return True, "witness-content-mismatch"
        return False, "witness-confirmed"

    raise ValueError("unknown verifier mode: %s" % mode)


MODES = ("schema", "per_record", "chain", "anchored")
ATTACKS = ("clean", "edit_value", "delete_middle", "insert_forged",
           "reorder", "truncate_tail", "reseal_chain")

ATTACK_DESCRIPTIONS = {
    "clean": "unmodified control log",
    "edit_value": "change one claim string, do not recompute any hash",
    "delete_middle": "remove one middle entry, leave remaining entries untouched",
    "insert_forged": "insert a forged entry with a correctly computed self-hash",
    "reorder": "swap two adjacent entries, keeping their contents intact",
    "truncate_tail": "drop the last three entries, leaving a self-consistent prefix",
    "reseal_chain": "change one claim, then recompute the entire chain from scratch",
}


def attack(bundle: dict, kind: str, seed: int) -> dict:
    """Apply one tampering attack. The attacker never updates the witness."""
    b = copy.deepcopy(bundle)
    entries = b["entries"]
    n = len(entries)
    if n < 8:
        raise ValueError("log too short for this attack set")
    rng = random.Random(seed * 7919 + 13)
    i = 4 + rng.randrange(n - 8)

    if kind == "clean":
        return b

    if kind == "edit_value":
        entries[i]["record"]["claim"] = CLAIMS[(i + 3) % len(CLAIMS)] + " (amended)"

    elif kind == "delete_middle":
        entries.pop(i)

    elif kind == "insert_forged":
        forged_rec = {
            "seq": entries[i]["record"]["seq"],
            "actor": "executor",
            "action": "commit",
            "claim": "the team approved the amended figure",
            "source_ref": SOURCES[0],
            "timestamp": "2026-11-14T10:00:00+08:00",
        }
        prev = entries[i]["prev"]
        forged = {"record": forged_rec, "prev": prev,
                  "hash": digest({"record": forged_rec, "prev": prev})}
        entries.insert(i, forged)

    elif kind == "reorder":
        entries[i], entries[i + 1] = entries[i + 1], entries[i]

    elif kind == "truncate_tail":
        del entries[-3:]
        b["head"] = entries[-1]["hash"]
        b["count"] = len(entries)

    elif kind == "reseal_chain":
        recs = [e["record"] for e in entries]
        recs[i]["claim"] = CLAIMS[(i + 4) % len(CLAIMS)] + " (amended)"
        return seal(recs)

    else:
        raise ValueError("unknown attack: %s" % kind)

    return b
