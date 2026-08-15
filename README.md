# effect-reconciliation

An enforcement point records **decisions**. The world produces **effects**. Almost every
governance stack writes down only the first and then reports it as though it described the second
— *"we authorised 400 actions under policy"* is a claim about permissions granted, not about
anything that happened.

Double-entry bookkeeping settled this in the fifteenth century: a ledger never reconciled against
reality cannot be checked. Governance has so far built only the authorisation side of the book.
This is the other side, and the disagreement between them.

It **computes and reports; it does not judge.** Whether an unauthorised effect is a breach, a
coverage gap or an instrumentation error is the reader's call.

## Why the disagreement is the product

| class | meaning |
|---|---|
| **MATCHED** | an authorisation and the effect it permitted |
| **AUTHORISED_NOT_OBSERVED** | permission granted, nothing seen. Often entirely legitimate — the agent may simply not have acted — so it is reported and **never** a defect on its own |
| **OBSERVED_NOT_AUTHORISED** | an effect with no permission behind it. **This is mediation coverage, measured** |
| **DUPLICATED** | several effects for one authorisation. Ordinary wherever delivery is at-least-once, so it is counted, not failed |

`unauthorised_rate` is the number worth reading. Zero means every observed effect passed the
enforcement point over this window — **a fact computed from two ledgers, not an assertion about
your architecture.** That is the difference between claiming complete mediation and demonstrating
it.

## The three refusals

- **"Not observed" is not "nothing happened."** `effects=None` means nobody looked and yields
  `UNRECONCILED`; an empty sequence means *observed, and nothing occurred*. A report built from
  one ledger is not a reconciliation and must not be allowed to read like one.
- **An inferred match is a guess, and says so.** An effect carrying an `authorisation_id` is
  `BOUND`. Anything matched on action + subject inside a time window is `INFERRED`, and
  `binding_rate` reports how much of the result rests on inference.
- **No verdict on conduct.** There is no `breach`, no `violation`, no severity. A test asserts the
  public surface offers none.

## Install

```bash
pip install .
```

Stdlib-only, no runtime dependencies. Tests need `pytest` (`pip install ".[test]"`).

## Usage

```python
from effect_reconciliation import Authorisation, Effect, reconcile

authorisations = [                                   # what the gate permitted
    Authorisation("a1", "git.push",  "repo:rvnd", "2026-03-01T10:00:00Z"),
    Authorisation("a2", "mail.send", "ops@x",     "2026-03-01T11:00:00Z"),
]
effects = [                                          # what actually happened
    Effect("e1", "git.push",  "repo:rvnd", "2026-03-01T10:00:01Z", authorisation_id="a1"),
    Effect("e2", "git.push",  "repo:rvnd", "2026-03-01T10:00:09Z", authorisation_id="a1"),  # retry
    Effect("e3", "net.fetch", "evil.example", "2026-03-01T12:00:00Z"),                      # ungoverned
]

r = reconcile(authorisations, effects,
              since="2026-03-01T00:00:00Z", until="2026-03-02T00:00:00Z")

print("status:", r.status.value)
print("unauthorised rate:", r.unauthorised_rate)
print("binding rate:", r.binding_rate)
print("authorised, never seen:", [a.action for a in r.authorised_not_observed])
print("seen, never authorised:", [e.action for e in r.observed_not_authorised])
print("duplicated:", [(d.authorisation.action, d.excess) for d in r.duplicated])

# And the distinction that matters most — nobody looked, versus looked and saw nothing:
blind = reconcile(authorisations, None, since="2026-03-01T00:00:00Z", until="2026-03-02T00:00:00Z")
print("no effect ledger ->", blind.status.value)
```

Output (behaviour proven by the test suite):

```
status: diverged
unauthorised rate: 0.3333333333333333
binding rate: 1.0
authorised, never seen: ['mail.send']
seen, never authorised: ['net.fetch']
duplicated: [('git.push', 1)]
```
```
no effect ledger -> unreconciled
```

Four things in that output. The retry is **duplicated, not a failure** — the system that produced
it may honestly be at-least-once. The unused `mail.send` permission is **reported, not blamed**.
The `net.fetch` nobody authorised gives an **unauthorised rate of 0.33**, which is one third of
observed effects bypassing the gate — measured, not assumed. And the last line is the refusal:
hand it no effect ledger and it declines to call anything reconciled.

## Limitations

- **It reconciles what you give it.** Effects it never sees cannot appear as
  `OBSERVED_NOT_AUTHORISED`, so `unauthorised_rate` is a *lower bound* on ungoverned activity —
  it measures the gap between two ledgers, not the gap between a ledger and the world. An effect
  channel with no observer at all is invisible to this and to everything else.
- **The measurement has a half-life.** A capable agent that meets a refusal plans around it, and
  the paths it migrates to are by construction the ones you were not watching. Read
  `unauthorised_rate` as a trend, never as a one-off assurance; a flat rate under an actively
  optimising agent is suspicious rather than reassuring.
- **Inference is bounded by your window, not by truth.** Widening `match_window_s` buys matches
  and spends certainty. `binding_rate` reports the exchange rate; it does not set it for you.
- **Refusals are not inputs.** Only permissions are reconcilable. An effect matching a *refused*
  act surfaces as `OBSERVED_NOT_AUTHORISED`, which is the louder and more correct reading.
- **It does not judge.** Disagreement is not misconduct; three of the four classes have entirely
  innocent explanations.

## Origin & prior art

Composed, not reinvented. Authorization **decision logs** are a mature commercial category —
Permit.io, Aserto, Cerbos and SecureAuth all ship them, and they already support policy-drift
detection when a recorded policy version no longer matches the active control set. **Access and
execution logs** are ubiquitous. **Data reconciliation** as a discipline is centuries old and
entirely routine in accounting: sub-ledger against general ledger, reconciling items, missing and
duplicated and miscoded entries.

What none of them packages is the join: **an authorisation ledger reconciled against an effect
ledger, classified into the four governance-meaningful outcomes, fail-closed when only one ledger
is present, honest about inferred matches, and tolerant of at-least-once duplication by design.**
The distinctive claim is narrower and more useful than "reconciliation": that
`OBSERVED_NOT_AUTHORISED` is *complete mediation measured rather than asserted* — the one number
in a governance stack that can be computed rather than promised.

Grounded in EU AI Act (Reg. 2024/1689) Art. 12 record-keeping: a record of decisions is
interpretable as a record of conduct only if the two have been reconciled.

```
PRIOR-ART:
  incumbent(s):      authorization decision logs (Permit.io · Aserto · Cerbos · SecureAuth) ·
                     access/execution logs · general-ledger reconciliation practice ·
                     XACML/OPA decision models
  distinctive layer: the authorisation-vs-effect join with governance semantics — mediation
                     coverage as a computed rate, UNRECONCILED when only one ledger exists,
                     BOUND vs INFERRED matching honesty, at-least-once duplication counted
                     rather than failed, and no verdict on conduct
  decision:          build-distinctive (composes on the incumbents' logs; owns the reconciliation)
```

## License

MIT. See `LICENSE`. Copyright 2026 flxk1.
