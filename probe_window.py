#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""READ-ONLY window verification for the AI x Epistemics Research Sprint.

Fetches the official sprint page with a single GET, records the HTTP status,
the exact quoted strings used for eligibility / deadline / prize / track
claims, and whether the submission form is present. Never POSTs, never
uploads, never signs up.

Usage: python probe_window.py   (exit 0 = window verified open)
Writes: window_check.json
"""

from __future__ import annotations

import datetime
import hashlib
import html as html_mod
import json
import os
import re
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "window_check.json")
URL = ("https://apartresearch.com/sprints/"
       "ai-x-epistemics-research-sprint-2026-11-13-to-2026-11-15")

# Strings that the submission hand-off claims as verbatim. Each is searched in
# the human-readable text of the page; a miss is recorded, never smoothed over.
PHRASES = (
    "Live now.",
    "Submissions close Sunday, November 15 at 11:59 PM Anywhere on Earth (AoE)",
    "$2,000 in cash prizes across all tracks",
    "Teams of one to five people",
    "No prior background in AI safety is required",
    "Results and winners are announced about 1 to 2 weeks after the judging deadline",
    "Friday, November 13",
    "Sunday, November 15",
    "Trust Infrastructure",
    "Epistemic Products",
    "Submit your project",
)

FORM_MARKERS = ("PDF File", "ProjectTitle_Framer", "ProjectSummary_Framer",
                "Tracks", "$ACTION_KEY", "project-submission",
                "success-submission")

# Only used to report what the page says; a hit here is not by itself proof of
# an exclusion, and a miss is not proof of absence.
EXCLUSION_TERMS = ("not eligible", "excluding", "residents of", "must be 18",
                   "18 years of age", "country restrictions")


def readable(page: str) -> str:
    """Tag-free, entity-decoded, whitespace-collapsed page text."""
    no_script = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", page,
                       flags=re.S | re.I)
    return re.sub(r"\s+", " ", html_mod.unescape(
        re.sub(r"<[^>]+>", " ", no_script))).strip()


def fetch() -> tuple[int, bytes]:
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    last = None
    for k in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.read()
        except Exception as exc:  # noqa: BLE001
            last = exc
            if k < 2:
                time.sleep(2 + 2 * k)
    raise last


def main() -> int:
    status, raw = fetch()
    page = raw.decode("utf-8", "replace")
    text = readable(page)
    m = re.search(r"<title[^>]*>(.*?)</title>", page, re.S | re.I)
    title = html_mod.unescape(m.group(1)).strip() if m else ""

    evidence = {}
    for phrase in PHRASES:
        i = text.find(phrase)
        evidence[phrase] = {
            "found": i >= 0,
            "occurrences": text.count(phrase),
            "context": (text[max(0, i - 110):i + len(phrase) + 110]
                        if i >= 0 else ""),
        }

    form = {k: {"in_page": k in page, "raw_hits": page.count(k)}
            for k in FORM_MARKERS}
    exclusions = {k: text.lower().count(k) for k in EXCLUSION_TERMS}

    prize_hits = sorted(set(re.findall(r"\$[\d,]+", text)))
    form_open = (evidence["Submit your project"]["found"]
                 and form["PDF File"]["in_page"]
                 and form["ProjectTitle_Framer"]["in_page"])
    live = evidence["Live now."]["found"]

    result = {
        "checked_at_beijing": datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=8))
        ).isoformat(timespec="seconds"),
        "url": URL,
        "http_status": status,
        "page_bytes": len(raw),
        "page_sha256": hashlib.sha256(raw).hexdigest(),
        "title": title,
        "readable_chars": len(text),
        "live_now": live,
        "submission_form_reachable_by_get": form_open,
        "window_open": bool(status == 200 and live and form_open),
        "evidence": evidence,
        "form_markers": form,
        "exclusion_term_counts": exclusions,
        "dollar_amounts_on_page": prize_hits,
        "post_count": 0,
        "note": ("Pure GET only. No POST, no sign-up, no PDF upload, "
                 "no submission. Verdicts are recorded as found/not found; "
                 "a missing phrase is not filled in from memory."),
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("HTTP", status, "| bytes", len(raw), "| sha16",
          result["page_sha256"][:16])
    print("title:", title)
    print("window_open:", result["window_open"],
          "| live_now:", live, "| form_reachable:", form_open)
    for phrase in PHRASES:
        e = evidence[phrase]
        print("  %-5s x%-2d %s" % ("FOUND" if e["found"] else "MISS",
                                   e["occurrences"], phrase[:78]))
    print("dollar amounts:", prize_hits)
    print("exclusion term counts:", exclusions)
    print("wrote", OUT, os.path.getsize(OUT), "bytes | POST=0")
    return 0 if result["window_open"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
