"""Machine-readable "no silent skip" guard (Final Practical Closeout Directive, P0).

The browser-contract lane exists to prove the render pipeline really ran. A
skipped browser test there means it did *not* run — the contract is unproven, so
the lane must **fail**, not pass with a green check.

The old guard grepped pytest's human-readable ``-rs`` output for the string
``"no functional browser"``. That is brittle (it depends on message wording) and
it re-ran the whole suite just to read the log. This guard instead reads pytest's
**JUnit XML** — a structured, machine-readable result — and fails when any test
was skipped unless that skip is explicitly allow-listed.

Usage (CI):

    pytest tests -q --junitxml=/tmp/results.xml
    python tools/skip_guard.py --junit /tmp/results.xml --forbid-skip

Exit codes: 0 = ok, 1 = forbidden skip(s) present (contract unproven),
2 = malformed/missing report.
"""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional


def parse_junit(path: str) -> Dict[str, Any]:
    """Return ``{tests, skipped:[{name,classname,message}], ...}`` from JUnit XML."""
    tree = ET.parse(path)
    root = tree.getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))

    skipped: List[Dict[str, str]] = []
    tests = 0
    failures = 0
    errors = 0
    for suite in suites:
        for case in suite.iter("testcase"):
            tests += 1
            if case.find("failure") is not None:
                failures += 1
            if case.find("error") is not None:
                errors += 1
            sk = case.find("skipped")
            if sk is not None:
                skipped.append({
                    "name": case.get("name", ""),
                    "classname": case.get("classname", ""),
                    "message": (sk.get("message") or (sk.text or "")).strip(),
                })
    return {"tests": tests, "failures": failures, "errors": errors,
            "skipped": skipped}


def forbidden_skips(report: Dict[str, Any], allow_patterns: List[str],
                    reason_patterns: Optional[List[str]] = None) -> List[Dict[str, str]]:
    """Skips that are not allow-listed. ``reason_patterns`` narrows to browser skips."""
    out: List[Dict[str, str]] = []
    for s in report.get("skipped", []):
        ident = "%s::%s" % (s.get("classname", ""), s.get("name", ""))
        if any(p and p in ident for p in allow_patterns):
            continue
        if reason_patterns:
            msg = s.get("message", "")
            if not any(r.lower() in msg.lower() for r in reason_patterns):
                continue
        out.append(s)
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Fail when tests were silently skipped.")
    ap.add_argument("--junit", required=True, help="pytest --junitxml report path")
    ap.add_argument("--forbid-skip", action="store_true",
                    help="fail if any test was skipped")
    ap.add_argument("--allow", action="append", default=[],
                    help="substring of an allow-listed (expected) skip; repeatable")
    ap.add_argument("--reason-contains", action="append", default=[],
                    help="only count skips whose message contains this text; repeatable")
    ap.add_argument("--summary-out", default=None,
                    help="optional path to write a machine-readable summary JSON")
    args = ap.parse_args(argv)

    try:
        report = parse_junit(args.junit)
    except (OSError, ET.ParseError) as exc:
        print("::error::could not read junit report %s: %s" % (args.junit, exc))
        return 2

    bad = forbidden_skips(report, args.allow, args.reason_contains)

    summary = {
        "junit": args.junit,
        "tests": report["tests"],
        "failures": report["failures"],
        "errors": report["errors"],
        "skipped_total": len(report["skipped"]),
        "skipped": report["skipped"],
        "forbidden_skips": bad,
        "forbid_skip": args.forbid_skip,
    }
    if args.summary_out:
        import json
        with open(args.summary_out, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False, sort_keys=True)
            f.write("\n")

    if report["failures"] or report["errors"]:
        print("::error::pytest report already contains %d failure(s) / %d error(s)"
              % (report["failures"], report["errors"]))
        return 1

    if args.forbid_skip and bad:
        for s in bad:
            print("::error::unexpected skip: %s::%s — %s"
                  % (s.get("classname", ""), s.get("name", ""), s.get("message", "")))
        print("::error::%d unexpected skip(s): the contract lane did not actually run"
              % len(bad))
        return 1

    print("skip-guard OK: tests=%d skipped=%d (allowed=%d forbidden=0)"
          % (report["tests"], len(report["skipped"]),
             len(report["skipped"]) - len(bad)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
