#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""Check an implementation against the published conformance vectors.

``vectors.json`` is the specification; this runner is one implementation's gate
against it.

Usage:
    python3 conformance/check_vectors.py [path-to-vectors.json]

Exit 0 = conformant · 1 = a vector failed · 2 = the suite could not be run.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from effect_reconciliation import Authorisation, Effect, reconcile  # noqa: E402


def _check(v: dict, window: dict) -> list[str]:
    opts = dict(window)
    opts.update(v.get("options") or {})
    effects = v["effects"]
    result = reconcile(
        [Authorisation(**a) for a in v["authorisations"]],
        None if effects is None else [Effect(**e) for e in effects],
        **opts,
    )
    want, errs = v["expect"], []

    def cmp(label, got, expected, tol=None):
        ok = abs(got - expected) <= tol if tol is not None else got == expected
        if not ok:
            errs.append(f"{label}: expected {expected!r}, got {got!r}")

    if "status" in want: cmp("status", result.status.value, want["status"])
    if "binding_rate" in want: cmp("binding_rate", result.binding_rate, want["binding_rate"], 1e-9)
    if "unauthorised_rate" in want: cmp("unauthorised_rate", result.unauthorised_rate, want["unauthorised_rate"], 1e-9)
    if "matched" in want: cmp("matched", len(result.matched), want["matched"])
    if "authorised_not_observed" in want: cmp("authorised_not_observed", len(result.authorised_not_observed), want["authorised_not_observed"])
    if "observed_not_authorised" in want: cmp("observed_not_authorised", len(result.observed_not_authorised), want["observed_not_authorised"])
    if "duplicated" in want: cmp("duplicated", len(result.duplicated), want["duplicated"])
    return errs


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent / "vectors.json"
    try:
        doc = json.loads(path.read_text())
    except Exception as exc:
        print(f"cannot read vectors: {exc}", file=sys.stderr)
        return 2
    vectors = doc.get("vectors") or []
    if not vectors:
        # Zero vectors passing is the silent-skip failure; refuse rather than report success.
        print("no vectors found — refusing to report conformance", file=sys.stderr)
        return 2

    failed = 0
    for v in vectors:
        try:
            errs = _check(v, doc["window"])
        except Exception as exc:
            errs = [f"<raised {type(exc).__name__}: {exc}>"]
        if errs:
            failed += 1
            print(f"FAIL {v['id']}")
            for e in errs:
                print(f"     {e}")
            print(f"     {v['note']}")
    print(f"{len(vectors) - failed}/{len(vectors)} vectors conformant"
          f"{'' if not failed else f' — {failed} FAILED'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
