# Prior art and related

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
