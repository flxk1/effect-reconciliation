# effect-reconciliation

Reconciles an authorisation ledger against an effect ledger. Reports what was permitted and never
happened, what happened without permission, and what happened more than once.

Enforcement points record decisions. Most do not record effects. "We authorised 400 actions under
policy" is a statement about permissions granted, not about what the system did. This computes the
difference between the two.

## Install

```bash
pip install "git+https://github.com/flxk1/effect-reconciliation"
```

No runtime dependencies. Tests: `pip install ".[test]"` from a clone. **Not yet on PyPI**, so the git URL is the
install.

## Usage

```python
from effect_reconciliation import Authorisation, Effect, reconcile

authorisations = [
    Authorisation("a1", "git.push",  "repo:rvnd", "2026-03-01T10:00:00Z"),
    Authorisation("a2", "mail.send", "ops@x",     "2026-03-01T11:00:00Z"),
]
effects = [
    Effect("e1", "git.push",  "repo:rvnd", "2026-03-01T10:00:01Z", authorisation_id="a1"),
    Effect("e2", "git.push",  "repo:rvnd", "2026-03-01T10:00:09Z", authorisation_id="a1"),
    Effect("e3", "net.fetch", "evil.example", "2026-03-01T12:00:00Z"),
]

r = reconcile(authorisations, effects,
              since="2026-03-01T00:00:00Z", until="2026-03-02T00:00:00Z")

print(r.status.value, r.unauthorised_rate, r.binding_rate)
print([a.action for a in r.authorised_not_observed])
print([e.action for e in r.observed_not_authorised])
print([(d.authorisation.action, d.excess) for d in r.duplicated])
```

```
diverged 0.3333333333333333 1.0
['mail.send']
['net.fetch']
[('git.push', 1)]
```

## Results

| field | meaning |
|---|---|
| `status` | `RECONCILED` · `DIVERGED` · `UNRECONCILED` |
| `matched` | authorisation + the effect it permitted, with its `Binding` |
| `authorised_not_observed` | permitted, no effect seen |
| `observed_not_authorised` | effect with no authorisation behind it |
| `duplicated` | more than one effect per authorisation; `.excess` is the surplus count |
| `unauthorised_rate` | unauthorised effects ÷ effects observed |
| `binding_rate` | proven matches ÷ all matches |

`unauthorised_rate` is a measurement of mediation coverage rather than a claim about it. Zero
means every observed effect passed the enforcement point in that window.

## Semantics

- **`effects=None` yields `UNRECONCILED`.** It means no observation was made. An empty sequence
  means observed, nothing happened. The two are not equivalent and are not collapsed.
- **Matching.** An effect carrying `authorisation_id` matches as `BOUND`. An effect without one
  matches on action + subject within `match_window_s` (default `0.0`) as `INFERRED`. Bound effects
  claim their authorisation first. `binding_rate` reports the ratio.
- **Duplicates are counted, not failed.** At-least-once delivery is common; a system that cannot
  guarantee exactly-once is not misbehaving by saying so.
- **Only permissions are inputs.** Refusals are not passed in. An effect matching a refused act
  appears as `observed_not_authorised`.
- **An effect is a side effect that occurred, not an attempt.** This decides the answer. Request
  logs record attempts including refused ones — a 403 response happened, the side effect it
  refused did not. Feed refused attempts in and every denial reads as `observed_not_authorised`:
  the enforcement point looks bypassed exactly when it is working, and real bypasses are buried.
  See `examples/opa_decision_logs.py`, where the same data reads 0.50 or 0.33 depending only on
  this.
- **No verdict on conduct.** There is no breach or severity field. Three of the four classes have
  ordinary explanations.
- No clock and no I/O; `since` / `until` are explicit and the window is half-open.

## Limitations

- `unauthorised_rate` is a **lower bound**. It measures the gap between two ledgers, not between a
  ledger and the world. An effect channel with no observer is invisible to it.
- Treat it as a trend, not a one-off assurance. An agent that meets a refusal routes around it, and
  the paths it moves to are the ones not being watched.
- Widening `match_window_s` buys matches and spends certainty. `binding_rate` reports the trade; it
  does not choose it.
- Disagreement is not misconduct.

## Consuming logs that are not ours

`examples/opa_decision_logs.py` reconciles **Open Policy Agent decision logs** against an HTTP
access log — two documented, widely deployed formats, neither designed for this package. The join
key is `trace_id` (W3C trace-context), which OPA emits and a real deployment propagates, giving
`BOUND` matches; without it, matching falls back to `INFERRED` within a window and `binding_rate`
reports how much rests on inference.

Both formats mapped with no change to the package. What the run did expose is the attempt-versus-
effect distinction above: the same inputs yield `unauthorised_rate` 0.50 or 0.33, and only the
lower one isolates the actual finding — a request that reached the world with no decision behind
it at all.

## Conformance

`conformance/vectors.json` is the specification: 11 language-agnostic vectors, each an input and
the result any implementation must produce. `conformance/check_vectors.py` checks this one.

```bash
python3 conformance/check_vectors.py
```

The refusals are most of the suite, because they are what a reimplementation gets wrong — and
getting one wrong converts a refusal into a false assurance, which is worse than the missing
feature. An empty suite exits 2 rather than reporting success.

## Prior art

Authorisation **decision logs** are a mature category (Permit.io, Aserto, Cerbos, SecureAuth) and
already support policy-drift detection. Access and execution logs are ubiquitous. Ledger
reconciliation is standard accounting practice.

What is not packaged elsewhere is the join: an authorisation ledger reconciled against an effect
ledger, classified into the four outcomes above, fail-closed when only one ledger is present,
explicit about inferred matches, and tolerant of at-least-once duplication.

```
PRIOR-ART:
  incumbent(s):      authorization decision logs (Permit.io · Aserto · Cerbos · SecureAuth) ·
                     access/execution logs · ledger reconciliation practice · XACML/OPA
  distinctive layer: the authorisation-vs-effect join with governance semantics — mediation
                     coverage as a computed rate, UNRECONCILED on a single ledger, BOUND vs
                     INFERRED matching, at-least-once duplication counted not failed
  decision:          build-distinctive (composes on the incumbents' logs; owns the reconciliation)
```

Relevant to EU AI Act (Reg. 2024/1689) Art. 12: a record of decisions describes conduct only once
reconciled against effects.

## Related

One of four narrow governance primitives, each usable alone:

- [`enforcement-posture`](https://github.com/flxk1/enforcement-posture) — binds evidence to the
  controls that were in force while it was recorded
- [`norm-freshness`](https://github.com/flxk1/norm-freshness) — whether the rule a gate applies
  still matches the text it was compiled from
- [`effect-reconciliation`](https://github.com/flxk1/effect-reconciliation) — permissions granted
  against effects observed
- [`oversight-certificate`](https://github.com/flxk1/oversight-certificate) — re-checkable proof
  that a qualified human decided

They answer different questions about the same decision: *who decided* (oversight-certificate),
*under what regime* (enforcement-posture), *against which version of the rule* (norm-freshness),
and *did the permission produce the effect* (effect-reconciliation).

## License

MIT. See `LICENSE`. Copyright 2026 flxk1.
