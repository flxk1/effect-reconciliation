# Semantics and limitations

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
