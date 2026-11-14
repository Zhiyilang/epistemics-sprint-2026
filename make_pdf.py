#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render REPORT.md to REPORT.pdf using the project's Markdown->HTML helper.

The shared project helper _md2pdf.py is reused for CSS/HTML conversion, but the
Chrome invocation uses a private --user-data-dir: on this machine Chrome hangs
when it tries to attach to an already-running instance. No source file of the
shared helper is modified.

Usage: python make_pdf.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
sys.path.insert(0, PROJECT)
import _md2pdf as base  # noqa: E402  (project-level helper, read-only)

SRC = os.path.join(HERE, "REPORT.md")
DST = os.path.join(HERE, "REPORT.pdf")
CHROME = base.CHROME


def main() -> int:
    md = open(SRC, encoding="utf-8").read()
    doc = ("<!DOCTYPE html><html><head><meta charset='utf-8'>"
           "<style>%s</style></head><body>%s</body></html>"
           % (base.CSS, base.md_to_html(md)))
    tmp_html = os.path.join(HERE, "_report_render.html")
    with open(tmp_html, "w", encoding="utf-8") as f:
        f.write(doc)
    profile = tempfile.mkdtemp(prefix="epistemics_chrome_")
    try:
        cmd = [
            CHROME, "--headless", "--disable-gpu", "--no-sandbox",
            "--user-data-dir=" + profile,
            "--no-pdf-header-footer",
            "--print-to-pdf=" + os.path.abspath(DST),
            "file:///" + os.path.abspath(tmp_html).replace("\\", "/"),
        ]
        r = subprocess.run(cmd, capture_output=True, timeout=120)
        if r.returncode != 0:
            print("chrome rc=%d %s" % (r.returncode,
                                       r.stderr.decode("utf-8", "replace")[-300:]))
            return 1
    finally:
        try:
            os.unlink(tmp_html)
        except OSError:
            pass
        shutil.rmtree(profile, ignore_errors=True)

    data = open(DST, "rb").read()
    if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-2048:]:
        print("FAIL: PDF structure invalid")
        return 1
    import re
    pages = len(re.findall(rb"/Type\s*/Page\b", data))
    print("OK REPORT.pdf | %d bytes | %d pages" % (len(data), pages))
    return 0


if __name__ == "__main__":
    sys.exit(main())
