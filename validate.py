#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pre-submission validation for the Epistemics research package.

Checks artefacts, PDF structure/page count, required report sections,
abstract length, reproducibility (by invoking eval.py), and credential leaks.
Usage: python validate.py   (exit 0 = all checks pass)
"""

from __future__ import annotations

import json
import os
import py_compile
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

REQUIRED_FILES = (
    "REPORT.md", "REPORT.pdf", "README.md", "LICENSE", "SUBMISSION.md",
    "audit_log.py", "run_experiment.py", "eval.py", "validate.py",
    "make_pdf.py", "results.json",
)
PY_FILES = ("audit_log.py", "run_experiment.py", "eval.py", "validate.py",
            "make_pdf.py")
SECTIONS = ("## Abstract", "## 1. Question", "## 2. Method", "## 3. Results",
            "## 4. Discussion", "## 5. Limitations",
            "## 6. Dual-Use / Ethical Considerations", "## References",
            "## Appendix A", "## Appendix B")
SECRET_MARKERS = ("ghp_", "github_pat_", "KGAT", "Bearer ", "api_key=",
                  "API_KEY=", "smtp_pass", "imap_pass", "-----BEGIN",
                  "token-plan-cn")


def main() -> int:
    passed = 0
    failed = []
    notes = []

    def ck(label, cond, detail=""):
        nonlocal passed
        if cond:
            passed += 1
        else:
            failed.append("%s | %s" % (label, detail))

    for name in REQUIRED_FILES:
        ck("file exists: %s" % name, os.path.isfile(os.path.join(HERE, name)))

    for name in PY_FILES:
        p = os.path.join(HERE, name)
        try:
            py_compile.compile(p, doraise=True)
            ck("py_compile: %s" % name, True)
        except Exception as exc:  # noqa: BLE001
            ck("py_compile: %s" % name, False, str(exc))

    # Reproducibility: eval.py re-executes all 1,120 verifier calls.
    proc = subprocess.run([sys.executable, os.path.join(HERE, "eval.py")],
                          capture_output=True, text=True, cwd=HERE)
    ck("eval.py exit 0", proc.returncode == 0, proc.stdout.strip()[-200:])
    ck("eval reports 0 failures", "0 failed" in proc.stdout, proc.stdout.strip()[-200:])

    # Report structure.
    report = open(os.path.join(HERE, "REPORT.md"), encoding="utf-8").read()
    for s in SECTIONS:
        ck("report section: %s" % s, s in report)
    m = re.search(r"## Abstract\s*\n+(.+?)\n+---", report, re.S)
    words = len(m.group(1).split()) if m else -1
    ck("abstract 150-250 words", 150 <= words <= 250, "words=%d" % words)
    notes.append("abstract_words=%d" % words)
    ck("author line present", "Zhi Yilang" in report and "ZhiYiLab" in report)
    ck("sprint-window declaration present",
       "produced during the sprint window" in report)

    # Raw data.
    data = json.load(open(os.path.join(HERE, "results.json"), encoding="utf-8"))
    ck("280 raw trials", len(data["per_seed"]) == 280)
    ck("4 verifiers declared", len(data["meta"]["verifiers"]) == 4)
    ck("7 conditions declared", len(data["meta"]["attacks"]) == 7)
    ck("sprint timestamp", "2026-11-14" in data["meta"]["generated_at"])

    # PDF.
    pdf = open(os.path.join(HERE, "REPORT.pdf"), "rb").read()
    ck("PDF header", pdf.startswith(b"%PDF-"))
    ck("PDF trailer", b"%%EOF" in pdf[-2048:])
    pages = len(re.findall(rb"/Type\s*/Page\b", pdf))
    if pages:
        ck("PDF <= 8 pages", pages <= 8, "pages=%d" % pages)
        notes.append("pdf_pages=%d" % pages)
    else:
        notes.append("pdf_pages=NOT_VERIFIABLE (compressed object streams); "
                     "page count not claimed")
    notes.append("pdf_bytes=%d" % len(pdf))

    # Bilingual README and credential scan.
    readme = open(os.path.join(HERE, "README.md"), encoding="utf-8").read()
    ck("README English", "English" in readme)
    ck("README Chinese", "中文" in readme)
    leaked = []
    for name in REQUIRED_FILES:
        # Skip the binary PDF and the scanner itself: validate.py necessarily
        # contains the marker strings it searches for (self-reference, not a key).
        if name in ("REPORT.pdf", "validate.py"):
            continue
        try:
            text = open(os.path.join(HERE, name), encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        for marker in SECRET_MARKERS:
            if marker in text:
                leaked.append("%s:%s" % (name, marker))
    ck("no credential literals", not leaked, ", ".join(leaked))

    print("VALIDATE: %d passed, %d failed" % (passed, len(failed)))
    for n in notes:
        print("  note:", n)
    for f in failed:
        print("  FAIL:", f, file=sys.stderr)
    if failed:
        return 1
    print("VALIDATE PASS - package ready for the 2026-11-16 single-submission gate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
