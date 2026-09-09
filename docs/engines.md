# Consuming logs that are not ours

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
