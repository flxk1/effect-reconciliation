# Usage and results


Reconciles an authorisation ledger against an effect ledger. Reports what was permitted and never
happened, what happened without permission, and what happened more than once.

Enforcement points record decisions. Most do not record effects. "We authorised 400 actions under
policy" is a statement about permissions granted, not about what the system did. This computes the
difference between the two.

## Install

```bash
pip install "git+https://github.com/flxk1/effect-reconciliation"
```

No runtime dependencies.

Distributed from this repository; there is no package-index release. Tests:
`pip install ".[test]"` from a clone.

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
