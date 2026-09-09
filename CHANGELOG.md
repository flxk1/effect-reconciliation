# Changelog

## Unreleased

- Repository laid out on the measure skeleton: `LICENSES/MIT.txt` + `NOTICE` + `REUSE.toml` replace the bare `LICENSE`; `MANIFEST.in` dropped; version single-sourced from `src/effect_reconciliation/_version.py`; CI workflow and release-please config added.

## 0.2.0 — 2026-08-17

No behaviour change; a semantics clarification with a large consequence, found by consuming logs
this package did not design.

`examples/opa_decision_logs.py` reconciles OPA decision logs against an HTTP access log. Both
mapped unmodified. But **an `Effect` is a governed side effect that occurred, not an attempt** —
a request log records refused attempts too, and a 403 response happened while the side effect it
refused did not. Feed refusals in as effects and every denial reads as OBSERVED_NOT_AUTHORISED:
the enforcement point looks bypassed exactly when it is working, and genuine bypasses are buried.
In the example the same inputs give `unauthorised_rate` 0.50 or 0.33 on this distinction alone.

Documented on `Effect` and in the README's semantics.

## 0.1.0 — 2026-08-15

Initial draft. Reconciles an authorisation ledger against an effect ledger over an explicit
window and classifies the disagreement: MATCHED, AUTHORISED_NOT_OBSERVED (reported, never a
defect on its own), OBSERVED_NOT_AUTHORISED (**mediation coverage measured rather than
asserted**, via `unauthorised_rate`), and DUPLICATED (counted, not failed — at-least-once
delivery is a stated trade-off, not misbehaviour).

Three refusals: `effects=None` means nobody looked and yields UNRECONCILED, distinct from an
empty sequence meaning observed-and-nothing-happened; an unbound match is INFERRED and
`binding_rate` reports how much of the result rests on inference; and the package returns no
verdict on conduct. Stdlib-only, no clock — `since`/`until` are explicit.
