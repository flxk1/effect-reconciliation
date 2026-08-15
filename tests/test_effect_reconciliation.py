# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""Tests for effect_reconciliation. Runs under both `pytest` and
`python -m unittest discover -s tests`.

Pure functions over two ledgers — no clock, no I/O. Every refusal is pinned:
not-observed vs observed-nothing, inferred-is-a-guess, and duplicates counted
rather than failed."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from effect_reconciliation import (  # noqa: E402
    Authorisation,
    Binding,
    Effect,
    Reconciliation,
    Status,
    reconcile,
)

SINCE, UNTIL = "2026-03-01T00:00:00Z", "2026-03-02T00:00:00Z"


def auth(i="a1", action="git.push", subject="repo:rvnd", at="2026-03-01T10:00:00Z"):
    return Authorisation(i, action, subject, at)


def eff(i="e1", action="git.push", subject="repo:rvnd", at="2026-03-01T10:00:00Z", aid=None):
    return Effect(i, action, subject, at, aid)


def run(auths, effects, **kw):
    return reconcile(auths, effects, since=SINCE, until=UNTIL, **kw)


class TestBoundMatching(unittest.TestCase):
    def test_a_bound_effect_matches_and_reconciles(self):
        r = run([auth()], [eff(aid="a1")])
        self.assertIs(r.status, Status.RECONCILED)
        self.assertTrue(r.ok)
        self.assertEqual(len(r.matched), 1)
        self.assertIs(r.matched[0].binding, Binding.BOUND)
        self.assertEqual(r.binding_rate, 1.0)

    def test_an_effect_naming_an_authorisation_outside_the_window_is_unauthorised(self):
        r = run([auth()], [eff(aid="somewhere-else")])
        self.assertIs(r.status, Status.DIVERGED)
        self.assertEqual(len(r.observed_not_authorised), 1)


class TestInferenceIsAGuess(unittest.TestCase):
    """Widening the window buys matches and spends certainty; the rate says so."""

    def test_an_unbound_effect_does_not_match_outside_the_window(self):
        r = run([auth(at="2026-03-01T10:00:00Z")], [eff(at="2026-03-01T10:00:30Z")])
        self.assertIs(r.status, Status.DIVERGED)
        self.assertEqual(len(r.observed_not_authorised), 1)
        self.assertEqual(len(r.authorised_not_observed), 1)

    def test_widening_the_window_matches_it_but_marks_it_inferred(self):
        r = run([auth(at="2026-03-01T10:00:00Z")], [eff(at="2026-03-01T10:00:30Z")], match_window_s=60)
        self.assertIs(r.status, Status.RECONCILED)
        self.assertIs(r.matched[0].binding, Binding.INFERRED)
        self.assertEqual(r.binding_rate, 0.0, "an inferred reconciliation must not read as proven")

    def test_binding_rate_reports_the_mix(self):
        auths = [auth("a1"), auth("a2", subject="repo:other")]
        effects = [eff("e1", aid="a1"), eff("e2", subject="repo:other")]
        r = run(auths, effects, match_window_s=60)
        self.assertIs(r.status, Status.RECONCILED)
        self.assertEqual(r.binding_rate, 0.5)

    def test_proof_beats_inference_when_both_could_claim(self):
        """A bound effect takes its authorisation first; the unbound one cannot steal it."""
        auths = [auth("a1")]
        effects = [eff("e-unbound"), eff("e-bound", aid="a1")]
        r = run(auths, effects, match_window_s=60)
        self.assertIs(r.matched[0].binding, Binding.BOUND)
        self.assertEqual([e.id for e in r.observed_not_authorised], ["e-unbound"])


class TestTheThreeClasses(unittest.TestCase):
    def test_authorised_but_not_observed_is_reported_not_failed(self):
        """Permission granted and not used is ordinary — the agent may simply not have acted."""
        r = run([auth()], [])
        self.assertIs(r.status, Status.RECONCILED)
        self.assertTrue(r.ok)
        self.assertEqual(len(r.authorised_not_observed), 1)

    def test_observed_without_authorisation_diverges(self):
        r = run([], [eff()])
        self.assertIs(r.status, Status.DIVERGED)
        self.assertEqual(len(r.observed_not_authorised), 1)

    def test_unauthorised_rate_is_mediation_coverage_measured(self):
        auths = [auth("a1")]
        effects = [eff("e1", aid="a1"), eff("e2", action="net.fetch")]
        r = run(auths, effects)
        self.assertAlmostEqual(r.unauthorised_rate, 0.5)

    def test_the_denominator_is_effects_observed_not_rows_reported(self):
        """A duplicate's first effect is already in `matched`; counting the whole
        Duplicate tuple again would inflate the denominator and understate the rate."""
        auths = [auth("a1")]
        effects = [eff("e1", aid="a1"), eff("e2", aid="a1"), eff("e3", action="net.fetch")]
        r = run(auths, effects)
        self.assertEqual(len(effects), 3)
        self.assertAlmostEqual(r.unauthorised_rate, 1 / 3)

    def test_a_fully_mediated_window_scores_zero_unauthorised(self):
        r = run([auth("a1")], [eff("e1", aid="a1")])
        self.assertEqual(r.unauthorised_rate, 0.0)

    def test_duplicates_are_counted_never_failed_out_of_existence(self):
        """At-least-once delivery is a stated trade-off, not misbehaviour."""
        r = run([auth("a1")], [eff("e1", aid="a1"), eff("e2", aid="a1")])
        self.assertIs(r.status, Status.DIVERGED)
        self.assertEqual(len(r.duplicated), 1)
        self.assertEqual(r.duplicated[0].excess, 1)
        self.assertEqual(len(r.matched), 1, "a duplicate still has exactly one match")


class TestRefusals(unittest.TestCase):
    def test_no_observation_is_unreconciled_not_clean(self):
        """`None` means nobody looked. It must never read as agreement."""
        r = run([auth()], None)
        self.assertIs(r.status, Status.UNRECONCILED)
        self.assertFalse(r.ok)
        self.assertIn("not a reconciliation", r.detail)

    def test_observed_nothing_differs_from_not_observed(self):
        looked = run([auth()], [])
        did_not = run([auth()], None)
        self.assertIs(looked.status, Status.RECONCILED)
        self.assertIs(did_not.status, Status.UNRECONCILED)

    def test_unreconciled_outranks_diverged(self):
        r = reconcile([auth()], None, since=SINCE, until=UNTIL)
        self.assertIs(r.status, Status.UNRECONCILED)

    def test_an_inverted_window_is_unreconciled(self):
        r = reconcile([auth()], [eff()], since=UNTIL, until=SINCE)
        self.assertIs(r.status, Status.UNRECONCILED)

    def test_empty_everything_is_reconciled_with_no_signal(self):
        r = run([], [])
        self.assertIs(r.status, Status.RECONCILED)
        self.assertEqual(r.binding_rate, 0.0)
        self.assertEqual(r.unauthorised_rate, 0.0)

    def test_the_package_offers_no_verdict_on_conduct(self):
        forbidden = ("breach", "violation", "penalt", "guilty", "sanction")
        offenders = [n for n in dir(Reconciliation) if any(w in n.lower() for w in forbidden)]
        self.assertEqual(offenders, [], "it reports disagreement; it does not judge it")


class TestWindowing(unittest.TestCase):
    def test_records_outside_the_window_are_excluded_from_both_ledgers(self):
        r = run([auth(at="2026-02-01T00:00:00Z")], [eff(at="2026-02-01T00:00:00Z")])
        self.assertIs(r.status, Status.RECONCILED)
        self.assertEqual(r.matched, ())
        self.assertEqual(r.authorised_not_observed, ())

    def test_the_window_is_half_open(self):
        at_end = run([auth(at=UNTIL)], [eff(at=UNTIL, aid="a1")])
        self.assertEqual(at_end.matched, (), "until is exclusive")

    def test_reconciliation_is_deterministic(self):
        args = ([auth("a1"), auth("a2", subject="s2")], [eff("e1", aid="a1"), eff("e2", subject="s2")])
        first, second = run(*args, match_window_s=60), run(*args, match_window_s=60)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
