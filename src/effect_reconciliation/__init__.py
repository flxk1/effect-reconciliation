# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""effect-reconciliation — governance keeps a single-entry book; this is the other side.

An enforcement point records **decisions**. The world produces **effects**. Almost
every governance stack writes down only the first and reports it as though it
described the second: *"we authorised 400 actions under policy"* is a claim about
permissions granted, not about anything that happened. Double-entry bookkeeping
settled this in the fifteenth century — a ledger that is never reconciled against
reality cannot be checked — and governance has so far built only the authorisation
side of the book.

This reconciles the two and classifies the disagreement:

* **MATCHED** — an authorisation and the effect it permitted.
* **AUTHORISED_NOT_OBSERVED** — permission granted, nothing seen. Often perfectly
  legitimate (the agent chose not to act), so it is reported and **never** treated
  as a defect on its own.
* **OBSERVED_NOT_AUTHORISED** — an effect with no permission behind it. This is
  the interesting one: it is *mediation coverage measured rather than asserted*.
  Coverage stops being a property you claim about your architecture and becomes a
  number computed from two ledgers that disagree.
* **DUPLICATED** — several effects for one authorisation. Expected wherever
  delivery is at-least-once, so it is counted, not failed.

Three refusals carry the design, each a place where a tidy answer would be invented:

* **Not observed is not "nothing happened."** ``effects=None`` means *no
  observation was made* and yields :attr:`Status.UNRECONCILED`; an empty sequence
  means *observed, and nothing occurred*. A reconciliation with only one ledger is
  not a clean one.
* **An inferred match is a guess, and says so.** An effect carrying an
  ``authorisation_id`` is BOUND. Anything matched on action+subject inside a time
  window is INFERRED, and :attr:`Reconciliation.binding_rate` reports how much of
  the result rests on inference.
* **Nothing here is a verdict on conduct.** It computes and reports; whether an
  unauthorised effect is a breach, a gap or an instrumentation error is the
  reader's call.

Pure stdlib, no clock, no I/O: ``since``/``until`` are explicit so a run is
reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable, Sequence

__version__ = "0.1.0"

__all__ = [
    "Authorisation",
    "Effect",
    "Binding",
    "Match",
    "Duplicate",
    "Status",
    "Reconciliation",
    "reconcile",
]


def _ts(value: str) -> datetime:
    """Parse an RFC 3339 / ISO 8601 timestamp; naive input is read as UTC."""
    text = value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    parsed = datetime.fromisoformat(text)
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


# --------------------------------------------------------------------------- #
# the two ledgers
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Authorisation:
    """One permission granted by an enforcement point.

    Only permissions are reconcilable. A *refusal* should have produced no effect,
    so refusals are not passed here — an effect matching a refused act shows up as
    OBSERVED_NOT_AUTHORISED, which is the correct and louder reading.
    """

    id: str
    action: str
    subject: str
    at: str


@dataclass(frozen=True)
class Effect:
    """One governed side effect that actually occurred.

    **Not an attempt.** The distinction decides the answer. A request log records
    attempts, including refused ones: a 403 response *happened*, but the side
    effect it was refused did not. Feed refused attempts in as effects and every
    denial reads as OBSERVED_NOT_AUTHORISED — the enforcement point looks
    catastrophically bypassed precisely when it is working, and the genuine
    bypasses are buried in the noise. Filter to effects that occurred.

    ``authorisation_id`` is the binding an executor propagates when it can. Its
    absence is not an error; it downgrades the match to INFERRED and is counted
    against :attr:`Reconciliation.binding_rate`.
    """

    id: str
    action: str
    subject: str
    at: str
    authorisation_id: str | None = None


# --------------------------------------------------------------------------- #
# the reconciliation
# --------------------------------------------------------------------------- #

class Binding(str, Enum):
    """How an effect was tied to its authorisation."""

    BOUND = "bound"        # the effect carried the authorisation id — proof
    INFERRED = "inferred"  # matched on action + subject within the window — a guess


@dataclass(frozen=True)
class Match:
    authorisation: Authorisation
    effect: Effect
    binding: Binding


@dataclass(frozen=True)
class Duplicate:
    """More than one effect against a single authorisation.

    Ordinary wherever delivery is at-least-once. Counted, never failed — a system
    that cannot guarantee exactly-once is not misbehaving by saying so.
    """

    authorisation: Authorisation
    effects: tuple[Effect, ...]

    @property
    def excess(self) -> int:
        return max(0, len(self.effects) - 1)


class Status(str, Enum):
    """UNRECONCILED outranks DIVERGED: an unanswered question is not agreement."""

    RECONCILED = "reconciled"
    DIVERGED = "diverged"
    UNRECONCILED = "unreconciled"


@dataclass(frozen=True)
class Reconciliation:
    """The two books, and where they disagree."""

    status: Status
    matched: tuple[Match, ...] = ()
    authorised_not_observed: tuple[Authorisation, ...] = ()
    observed_not_authorised: tuple[Effect, ...] = ()
    duplicated: tuple[Duplicate, ...] = ()
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status is Status.RECONCILED

    @property
    def binding_rate(self) -> float:
        """Share of matches that were proven rather than inferred. ``0.0`` if none.

        A reconciliation resting mostly on inference is a weaker instrument, and
        this is the number that says so.
        """
        if not self.matched:
            return 0.0
        bound = sum(1 for m in self.matched if m.binding is Binding.BOUND)
        return bound / len(self.matched)

    @property
    def unauthorised_rate(self) -> float:
        """Effects with no permission behind them, over all effects seen.

        **Mediation coverage, measured.** Zero means every observed effect passed
        the enforcement point over this window — a fact rather than an assertion
        about the architecture.
        """
        # A duplicated authorisation's first effect is already counted in `matched`,
        # so only its EXCESS effects are added — otherwise the denominator exceeds
        # the number of effects actually observed and the rate reads low.
        seen = (
            len(self.matched)
            + sum(d.excess for d in self.duplicated)
            + len(self.observed_not_authorised)
        )
        return len(self.observed_not_authorised) / seen if seen else 0.0


def reconcile(
    authorisations: Iterable[Authorisation],
    effects: Iterable[Effect] | None,
    *,
    since: str,
    until: str,
    match_window_s: float = 0.0,
) -> Reconciliation:
    """Reconcile permissions granted against effects observed over a window.

    ``effects=None`` means **no observation was made** and yields UNRECONCILED —
    distinct from an empty sequence, which means *observed, and nothing happened*.
    That distinction is the whole point: a governance report built from one ledger
    is not a reconciliation, and must not be allowed to read like one.

    ``match_window_s`` permits inferred matching of an unbound effect to an
    authorisation of the same action and subject occurring within that many seconds
    (default 0.0 — exact-instant only). Widening it buys matches and spends
    certainty; :attr:`Reconciliation.binding_rate` reports the exchange rate.
    """
    lo, hi = _ts(since), _ts(until)
    if hi <= lo:
        return Reconciliation(Status.UNRECONCILED, detail="window end is not after window start")
    if effects is None:
        return Reconciliation(Status.UNRECONCILED, detail="no effect observation supplied; one ledger is not a reconciliation")

    auths = [a for a in authorisations if lo <= _ts(a.at) < hi]
    effs = [e for e in effects if lo <= _ts(e.at) < hi]

    by_id = {a.id: a for a in auths}
    claimed: dict[str, list[Effect]] = {a.id: [] for a in auths}
    unmatched: list[Effect] = []

    # 1. bound effects first — proof beats inference, so they claim their authorisation
    deferred: list[Effect] = []
    for e in effs:
        if e.authorisation_id is not None and e.authorisation_id in claimed:
            claimed[e.authorisation_id].append(e)
        elif e.authorisation_id is not None:
            unmatched.append(e)  # names an authorisation not in this window
        else:
            deferred.append(e)

    # 2. unbound effects may be inferred onto an as-yet-unclaimed authorisation
    for e in deferred:
        candidate = None
        for a in auths:
            if claimed[a.id]:
                continue
            if a.action == e.action and a.subject == e.subject:
                delta = abs((_ts(e.at) - _ts(a.at)).total_seconds())
                if delta <= match_window_s:
                    candidate = a
                    break
        if candidate is None:
            unmatched.append(e)
        else:
            claimed[candidate.id].append(e)

    matched: list[Match] = []
    duplicated: list[Duplicate] = []
    not_observed: list[Authorisation] = []
    for aid, es in claimed.items():
        a = by_id[aid]
        if not es:
            not_observed.append(a)
            continue
        first = es[0]
        matched.append(Match(a, first, Binding.BOUND if first.authorisation_id == aid else Binding.INFERRED))
        if len(es) > 1:
            duplicated.append(Duplicate(a, tuple(es)))

    diverged = bool(unmatched) or bool(duplicated)
    return Reconciliation(
        Status.DIVERGED if diverged else Status.RECONCILED,
        tuple(matched),
        tuple(not_observed),
        tuple(unmatched),
        tuple(duplicated),
        detail="",
    )
