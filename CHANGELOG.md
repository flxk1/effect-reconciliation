# Changelog

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
