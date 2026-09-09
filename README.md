# effect-reconciliation

Reconciles an authorisation ledger against an effect ledger and reports three mismatches: permitted but unobserved, observed but unpermitted, duplicated.

## Install

`pip install "git+https://github.com/flxk1/effect-reconciliation"`

## Usage

```python
r = reconcile(authorisations, effects, since="2026-03-01T00:00:00Z", until="2026-03-02T00:00:00Z")
r.status.value, r.unauthorised_rate, r.binding_rate   # diverged 0.333 1.0
```

## Interface

- inputs: `Authorisation(id, action, subject, at)`, `Effect(id, action, subject, at, authorisation_id=None)`, window `since`, `until`, `match_window_s`
- `reconcile(...) -> Reconciliation`; `status`: RECONCILED, DIVERGED, UNRECONCILED (`effects=None`)
- mismatches: `authorised_not_observed`, `observed_not_authorised`, `duplicated` (`.excess`)
- `matched` carries `Binding` BOUND (by `authorisation_id`) or INFERRED (action + subject within window)
- `unauthorised_rate`: unauthorised ÷ observed effects, a lower bound; `binding_rate`: bound ÷ all matches

## Family

Assurance artifact, pillar "observed effects" of [governance-certification](https://github.com/flxk1/governance-certification). Consumes: authorisation decision logs (OPA, XACML) and effect logs, joined on `trace_id` (`examples/opa_decision_logs.py`). Docs: [docs/](docs/).

## Status

0.2.0 · 22 tests · 11 conformance vectors · Python ≥ 3.10

## License

MIT — [LICENSES/MIT.txt](LICENSES/MIT.txt)
