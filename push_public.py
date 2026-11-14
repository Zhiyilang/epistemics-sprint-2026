#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mirror the Epistemics sprint package to public GitHub + Gitee repos.

Stdlib only. Credentials are read at runtime from ~/.github_pat and
~/.git-credentials; no credential literal appears in this file. Only two
hosts are contacted: api.github.com and gitee.com. The Apart sprint site is
NEVER contacted and no form POST is performed.

For every pushed file the script reads the remote blob back and compares the
bytes with the local file, so "pushed" always means "verified byte-identical".
Usage: python push_public.py   (exit 0 = both mirrors fully verified)
Writes: push_verify.json
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "push_verify.json")
REPO = "epistemics-sprint-2026"
GH_OWNER = "Zhiyilang"
GT_OWNER = "ZhiYIlang"
GH_API = "https://api.github.com"
GT_API = "https://gitee.com/api/v5"
DESCRIPTION = ("AI x Epistemics Research Sprint 2026 (Track 2, Trust "
               "Infrastructure): anchored hash chains for agent audit logs. "
               "Zero-dependency measurement, raw data, 4-page report.")

FILES = (
    "LICENSE", "README.md", "REPORT.md", "REPORT.pdf", "SUBMISSION.md",
    "audit_log.py", "run_experiment.py", "eval.py", "validate.py",
    "make_pdf.py", "results.json",
    "probe_form.py", "probe_form_result.json",
    "probe_window.py", "window_check.json",
    "push_public.py",
)


def local_files():
    missing = [f for f in FILES
               if not os.path.isfile(os.path.join(HERE, f))]
    if missing:
        raise SystemExit("missing local files: %s" % ", ".join(missing))
    return [(f, open(os.path.join(HERE, f), "rb").read()) for f in FILES]


def load_gh_token():
    p = os.path.expanduser("~/.github_pat")
    if not os.path.isfile(p):
        return None
    raw = open(p, encoding="utf-8", errors="replace").read().strip()
    return raw.splitlines()[0].strip() if raw else None


def load_gt_token():
    p = os.path.expanduser("~/.git-credentials")
    if not os.path.isfile(p):
        return None
    for line in open(p, encoding="utf-8", errors="replace"):
        m = re.search(r"://([^:]+):([^@]+)@([^/\s]+)", line.strip())
        if m and "gitee" in m.group(3):
            return m.group(2)
    return None


def blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(raw) + raw).hexdigest()


class Client:
    def __init__(self, name, base, token):
        self.name, self.base, self.token = name, base, token

    def call(self, method, path, payload=None, form=None, retries=3):
        url = self.base + path
        headers = {"User-Agent": "epistemics-mirror/1.0",
                   "Accept": "application/json"}
        if self.token:
            headers["Authorization"] = "token " + self.token
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode()
        elif form is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            body = urllib.parse.urlencode(form).encode()
        req = urllib.request.Request(url, data=body, method=method,
                                     headers=headers)
        for i in range(retries):
            try:
                with urllib.request.urlopen(req, timeout=60) as fh:
                    raw = fh.read()
                    return fh.status, (json.loads(raw) if raw else {})
            except urllib.error.HTTPError as exc:
                if exc.code in (429, 502, 503) and i < retries - 1:
                    time.sleep(3 * (i + 1))
                    continue
                try:
                    detail = json.loads(exc.read().decode("utf-8", "replace"))
                except Exception:  # noqa: BLE001
                    detail = {}
                return exc.code, detail
            except Exception as exc:  # noqa: BLE001
                if i < retries - 1:
                    time.sleep(3 * (i + 1))
                    continue
                return 0, {"error": str(exc)}
        return 0, {"error": "exhausted"}


def gh_repo(c):
    st, d = c.call("GET", "/repos/%s/%s" % (GH_OWNER, REPO))
    if st == 200:
        return d, None
    if st != 404:
        return None, "GET repo %s %s" % (st, str(d)[:180])
    st, d = c.call("POST", "/user/repos", payload={
        "name": REPO, "description": DESCRIPTION, "private": False,
        "auto_init": False})
    if st not in (200, 201):
        return None, "CREATE %s %s" % (st, str(d)[:180])
    return d, None


def gt_repo(c, token):
    st, d = c.call("GET", "/repos/%s/%s" % (GT_OWNER, REPO))
    if st == 200:
        return d, None
    if st != 404:
        return None, "GET repo %s %s" % (st, str(d)[:180])
    st, d = c.call("POST", "/user/repos", payload={
        "name": REPO, "description": DESCRIPTION, "private": True,
        "auto_init": False})
    if st not in (200, 201):
        return None, "CREATE %s %s" % (st, str(d)[:180])
    return d, None


def gt_set_public(c, token):
    for i in range(4):
        c.call("PATCH", "/repos/%s/%s" % (GT_OWNER, REPO),
               payload={"name": REPO, "private": False})
        st, d = c.call("GET", "/repos/%s/%s" % (GT_OWNER, REPO))
        if st == 200 and d.get("private") is False:
            return True
        time.sleep(2 * (i + 1))
    return False


def push_one(c, token, path, raw, platform, default_branch):
    quoted = urllib.parse.quote(path, safe="/")
    if platform == "github":
        base = "/repos/%s/%s/contents/%s" % (GH_OWNER, REPO, quoted)
        ref = "?ref=" + urllib.parse.quote(default_branch)
    else:
        base = "/repos/%s/%s/contents/%s" % (GT_OWNER, REPO, quoted)
        ref = "?ref=" + urllib.parse.quote(default_branch)

    st, cur = c.call("GET", base + ref)
    sha = cur.get("sha") if st == 200 and isinstance(cur, dict) else None
    content = base64.b64encode(raw).decode()
    message = "Add %s (AI x Epistemics Research Sprint 2026)" % path
    if platform == "github":
        payload = {"message": message, "content": content}
        if sha:
            payload["sha"] = sha
        st, d = c.call("PUT", base, payload=payload)
    else:
        form = {"access_token": token, "content": content,
                "message": message}
        if sha:
            form["sha"] = sha
        st, d = c.call("PUT" if sha else "POST", base, form=form)
    if st not in (200, 201):
        return {"path": path, "put_status": st,
                "error": str(d)[:220], "byte_identical": False}

    # Byte-for-byte read-back. The contents endpoint returns base64, so this
    # is a comparison of the actual remote blob, not of an HTTP status.
    st2, back = c.call("GET", base + ref)
    ok, why = False, "read-back status %s" % st2
    if st2 == 200 and isinstance(back, dict) and back.get("content"):
        try:
            remote = base64.b64decode("".join(back["content"].split()))
        except Exception as exc:  # noqa: BLE001
            remote, why = b"", "base64 decode: %s" % exc
        if remote == raw:
            ok, why = True, "ok"
        else:
            why = "remote %d bytes vs local %d bytes" % (len(remote), len(raw))
    return {
        "path": path,
        "put_status": st,
        "get_status": st2,
        "local_bytes": len(raw),
        "local_sha256": hashlib.sha256(raw).hexdigest(),
        "local_blob_sha1": blob_sha(raw),
        "remote_blob_sha1": back.get("sha") if isinstance(back, dict) else "",
        "blob_sha_match": (isinstance(back, dict)
                           and back.get("sha") == blob_sha(raw)),
        "byte_identical": ok,
        "note": why,
    }


def mirror(platform, token, items):
    if platform == "github":
        c = Client(platform, GH_API, token)
        repo, err = gh_repo(c)
        default_branch = (repo or {}).get("default_branch") or "main"
    else:
        c = Client(platform, GT_API, token)
        repo, err = gt_repo(c, token)
        default_branch = (repo or {}).get("default_branch") or "master"
    if err:
        return {"platform": platform, "error": err, "files": [],
                "all_verified": False}

    rows = []
    for path, raw in items:
        rows.append(push_one(c, token, path, raw, platform, default_branch))
        time.sleep(0.25)

    extra = {}
    if platform == "gitee":
        extra["public_flip"] = gt_set_public(c, token)
        st, d = c.call("GET", "/repos/%s/%s" % (GT_OWNER, REPO))
        extra["repo_get_status"] = st
        extra["repo_private"] = d.get("private") if isinstance(d, dict) else None
    else:
        st, d = c.call("GET", "/repos/%s/%s" % (GH_OWNER, REPO))
        extra["repo_get_status"] = st
        extra["repo_private"] = d.get("private") if isinstance(d, dict) else None
        extra["default_branch"] = (d.get("default_branch")
                                   if isinstance(d, dict) else default_branch)

    ok = (all(r.get("byte_identical") for r in rows)
          and len(rows) == len(items)
          and extra.get("repo_private") is False)
    if platform == "gitee":
        ok = ok and extra.get("public_flip") is True
    return {"platform": platform, "repo": "%s/%s" % (
                GH_OWNER if platform == "github" else GT_OWNER, REPO),
            "files": rows, "verified_files": sum(
                1 for r in rows if r.get("byte_identical")),
            "expected_files": len(items), "extra": extra,
            "all_verified": bool(ok)}


def main() -> int:
    items = local_files()
    tokens = {"github": load_gh_token(), "gitee": load_gt_token()}
    result = {
        "generated_at_beijing": time.strftime("%Y-%m-%d %H:%M:%S +08:00",
                                              time.localtime()),
        "repo": REPO,
        "note": ("push_verify.json is excluded from its own file table; it is "
                 "read back separately after being pushed. No Apart form "
                 "POST was performed; POST count to the sprint site = 0."),
        "platforms": {},
    }
    for platform in ("github", "gitee"):
        if not tokens[platform]:
            result["platforms"][platform] = {
                "error": "credential file missing or empty",
                "all_verified": False}
            print("%-7s SKIP (no credential)" % platform)
            continue
        r = mirror(platform, tokens[platform], items)
        result["platforms"][platform] = r
        print("%-7s verified=%d/%d all_verified=%s %s"
              % (platform, r.get("verified_files", 0), r.get("expected_files", 0),
                 r.get("all_verified"), r.get("error", "")))
        for row in r.get("files", []):
            if not row.get("byte_identical"):
                print("   FAIL", row["path"], row.get("note", ""))

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("wrote", OUT, os.path.getsize(OUT), "bytes")

    ok = all(p.get("all_verified") for p in result["platforms"].values())
    if not ok:
        return 1

    # Push the verification manifest itself, then read it back from both hosts.
    gh_tok, gt_tok = tokens["github"], tokens["gitee"]
    raw = open(OUT, "rb").read()
    for platform, tok in (("github", gh_tok), ("gitee", gt_tok)):
        owner = GH_OWNER if platform == "github" else GT_OWNER
        c = Client(platform, GH_API if platform == "github" else GT_API, tok)
        st, d = c.call("GET", "/repos/%s/%s" % (owner, REPO))
        branch = (d.get("default_branch") if isinstance(d, dict) else None) \
            or ("main" if platform == "github" else "master")
        row = push_one(c, tok, "push_verify.json", raw, platform, branch)
        print("manifest %-7s byte_identical=%s status=%s/%s"
              % (platform, row.get("byte_identical"), row.get("put_status"),
                 row.get("get_status")))
        if not row.get("byte_identical"):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
