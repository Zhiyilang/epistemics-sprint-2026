#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""READ-ONLY probe of the Epistemics sprint submission form.

Why this exists: the shared _apart_submit.py hard-codes the Swarm sprint URL,
slug, title, PDF filename, track and start-time gate. Pointing it at a new
sprint would risk a second POST to the already-submitted Swarm entry. This
probe never POSTs; it only reads the live form and records the real field
names so the 2026-11-16 gate can build a sprint-specific payload.

Usage: python probe_form.py   (exit 0 = form found and recorded)
"""

from __future__ import annotations

import html as html_mod
import json
import os
import re
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "probe_form_result.json")
URL = ("https://apartresearch.com/sprints/"
       "ai-x-epistemics-research-sprint-2026-11-13-to-2026-11-15")
KEYWORDS = ("PDF File", "project-submission", "Submit your project",
            "success-submission", "ProjectTitle_Framer",
            "ProjectSummary_Framer", "Tracks", "_ref", "$ACTION_KEY",
            "Live now.", "Submissions close")


def fetch(tries: int = 4) -> str:
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001
            last = exc
            if k + 1 < tries:
                time.sleep(2 + 2 * k)
    raise last


def main() -> int:
    page = fetch()
    actions = re.findall(r'<form[^>]*action="([^"]+)"[^>]*>', page, re.I)
    sub_actions = [a for a in actions if "submission" in a.lower()]

    hidden = {}
    named = []
    fragment = ""
    if sub_actions:
        anchor = 'action="%s"' % sub_actions[0]
        i = page.find(anchor)
        start = page.rfind("<form", 0, i)
        end = page.find("</form>", i)
        if start >= 0 and end > start:
            fragment = page[start:end]
            for tag in re.findall(r"<input[^>]*>", fragment, re.I):
                n = re.search(r'name="([^"]+)"', tag)
                v = re.search(r'value="([^"]*)"', tag)
                if not n:
                    continue
                name = html_mod.unescape(n.group(1))
                named.append(name)
                if re.search(r'type="hidden"', tag, re.I):
                    hidden[name] = html_mod.unescape(v.group(1)) if v else ""
            for tag in re.findall(r"<(?:select|textarea)[^>]*>", fragment, re.I):
                n = re.search(r'name="([^"]+)"', tag)
                if n:
                    named.append(html_mod.unescape(n.group(1)))

    hits = {k: page.count(k) for k in KEYWORDS}
    result = {
        "url": URL,
        "http_note": "urllib GET, 200 implied by successful read",
        "page_bytes_utf8": len(page.encode("utf-8")),
        "form_actions": actions[:10],
        "submission_actions": sub_actions[:10],
        "hidden_fields": hidden,
        "field_names": sorted(set(named)),
        "keyword_hits": hits,
        "post_count": 0,
        "note": "Pure GET. No POST, no upload token, no PDF upload, no submission.",
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("page_bytes", result["page_bytes_utf8"])
    print("submission_actions", sub_actions[:3])
    print("field_names", sorted(set(named))[:25])
    print("keyword_hits", hits)
    print("wrote", OUT, os.path.getsize(OUT), "bytes | POST=0")
    return 0 if sub_actions and "PDF File" in page else 1


if __name__ == "__main__":
    raise SystemExit(main())
