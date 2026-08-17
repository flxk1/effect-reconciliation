# SPDX-License-Identifier: MIT
"""Reconcile Open Policy Agent decision logs against a webserver access log.

A universality test. Until now this package had only ever been pointed at
fixtures of its own author's design; OPA decision logs and HTTP access logs are
foreign, documented and ubiquitous. The rule: if the package must change to
consume them, its abstraction is wrong.

Decision-log fields follow OPA's documented event shape (decision_id, trace_id,
path, input, result, timestamp). The join key is `trace_id` — W3C trace-context —
which a real deployment propagates into its access log, giving BOUND matches.
Where it is absent, matching falls back to INFERRED within a window, and
`binding_rate` reports how much of the answer rests on inference.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from effect_reconciliation import Authorisation, Effect, reconcile

# --- OPA decision log (NDJSON in practice; three allows, one deny) -------------
DECISIONS = [
    {"decision_id": "d1", "trace_id": "t1", "path": "http/authz/allow",
     "input": {"method": "POST", "path": "/salary/bob"}, "result": True,
     "timestamp": "2026-03-01T10:00:00Z"},
    {"decision_id": "d2", "trace_id": "t2", "path": "http/authz/allow",
     "input": {"method": "GET", "path": "/report/q1"}, "result": True,
     "timestamp": "2026-03-01T10:05:00Z"},
    {"decision_id": "d3", "trace_id": "t3", "path": "http/authz/allow",
     "input": {"method": "DELETE", "path": "/user/42"}, "result": True,
     "timestamp": "2026-03-01T10:10:00Z"},
    {"decision_id": "d4", "trace_id": "t4", "path": "http/authz/allow",
     "input": {"method": "POST", "path": "/payroll/run"}, "result": False,   # DENIED
     "timestamp": "2026-03-01T10:15:00Z"},
]

# --- access log: method, path, status, trace id -------------------------------
ACCESS = [
    ("POST",   "/salary/bob",  201, "t1", "2026-03-01T10:00:01Z"),
    ("GET",    "/report/q1",   200, "t2", "2026-03-01T10:05:01Z"),
    # d3 authorised, never executed — client hung up
    ("POST",   "/payroll/run", 403, "t4", "2026-03-01T10:15:01Z"),  # the DENIAL, served
    ("PUT",    "/config/flags", 200, "t9", "2026-03-01T10:20:00Z"),  # NO decision at all
]

def authorisations(events):
    """Only permissions are reconcilable — OPA logs denials too, and a denial is
    not an authorisation."""
    return [Authorisation(e["trace_id"], f"{e['input']['method']} {e['input']['path']}",
                          e["input"]["path"], e["timestamp"])
            for e in events if e["result"] is True]

def effects(lines, *, governed_only: bool):
    out = []
    for method, path, status, trace, ts in lines:
        # An access log records ATTEMPTS. A 403 is a request that happened and a
        # side effect that did not. Treating every log line as an effect makes
        # every denial look like an ungoverned action.
        if governed_only and status >= 400:
            continue
        out.append(Effect(f"{trace}:{status}", f"{method} {path}", path, ts, authorisation_id=trace))
    return out

W = dict(since="2026-03-01T00:00:00Z", until="2026-03-02T00:00:00Z")
auths = authorisations(DECISIONS)

naive = reconcile(auths, effects(ACCESS, governed_only=False), **W)
right = reconcile(auths, effects(ACCESS, governed_only=True), **W)

for label, r in (("every access-log line as an effect", naive),
                 ("only effects that actually occurred", right)):
    print(f"\n{label}:")
    print(f"   status              {r.status.value}")
    print(f"   unauthorised_rate   {r.unauthorised_rate:.2f}")
    print(f"   binding_rate        {r.binding_rate:.2f}")
    print(f"   never observed      {[a.action for a in r.authorised_not_observed]}")
    print(f"   never authorised    {[e.action for e in r.observed_not_authorised]}")
