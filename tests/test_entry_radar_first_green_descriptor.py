"""Synthetic-only tests for the first-green comparator on existing Phase-1 inputs."""
from __future__ import annotations
import copy
import unittest

from tests.test_entry_radar_rs_pullback_phase1 import candidate, fixture, minute
from engine.entry_radar.replay import first_green_reversal_descriptor as green
from engine.entry_radar.replay.rs_pullback_launch_data import InputContractError, digest


def witness(decision="2026-10-06T16:00:00Z"):
    b = fixture([candidate("green", decision)])
    for row in b["minutes"]:
        if row["stream"] != "stock":
            continue
        if "2026-10-06T15:00:00Z" <= row["start"] < "2026-10-06T15:30:00Z":
            row.update(open=101.0, high=102.0, low=99.0, close=100.0)
        elif "2026-10-06T15:30:00Z" <= row["start"] < "2026-10-06T16:00:00Z":
            row.update(open=100.0, high=102.0, low=99.0, close=101.0)
    return b


def followup(b, when="2026-10-06T16:05:00Z"):
    b["candidates"].append(candidate("following", when))
    return b


def frozen(b=None, expiry="2026-10-06T17:00:00Z"):
    b = witness() if b is None else b
    return green.freeze_first_green_reference(
        b, "green", buffer_size=0.01, episode_expires_at=expiry
    )


def confirm_minute(b):
    minute(b, "2026-10-06T16:01:00Z").update(
        open=101.0, high=103.0, low=100.0, close=102.5
    )


class FirstGreenFormationTests(unittest.TestCase):
    def test_red_to_green_forms_at_completed_target(self):
        d = green.describe_first_green_candidate(witness(), "green")
        self.assertEqual(d["state"], "FIRST_GREEN_FORMED")
        self.assertTrue(d["condition_met"])
        self.assertEqual(d["pivot"]["bar_end"], "2026-10-06T16:00:00Z")
        self.assertEqual(d["price_structure_known_at"], "2026-10-06T16:00:00Z")
        self.assertFalse(d["source_admitted"])
        self.assertTrue(all(v is False for v in d["authority"].values()))
        self.assertEqual(d["descriptor_sha256"], digest(
            {key: val for key, val in d.items() if key != "descriptor_sha256"}
        ))

    def test_red_target_is_not_green(self):
        b = witness()
        for r in b["minutes"]:
            if r["stream"] == "stock" and "2026-10-06T15:30:00Z" <= r["start"] < "2026-10-06T16:00:00Z":
                r["close"] = 99.5
        self.assertEqual(green.describe_first_green_candidate(b, "green")["state"], "NO_FIRST_GREEN")

    def test_doji_target_is_not_green(self):
        b = witness()
        for r in b["minutes"]:
            if r["stream"] == "stock" and "2026-10-06T15:30:00Z" <= r["start"] < "2026-10-06T16:00:00Z":
                r["close"] = 100.0
        self.assertEqual(green.describe_first_green_candidate(b, "green")["state"], "NO_FIRST_GREEN")

    def test_previous_green_does_not_form(self):
        b = witness()
        for r in b["minutes"]:
            if r["stream"] == "stock" and "2026-10-06T15:00:00Z" <= r["start"] < "2026-10-06T15:30:00Z":
                r["close"] = 101.5
        self.assertEqual(green.describe_first_green_candidate(b, "green")["state"], "NO_FIRST_GREEN")

    def test_previous_doji_does_not_form(self):
        b = witness()
        for r in b["minutes"]:
            if r["stream"] == "stock" and "2026-10-06T15:00:00Z" <= r["start"] < "2026-10-06T15:30:00Z":
                r["close"] = 101.0
        self.assertEqual(green.describe_first_green_candidate(b, "green")["state"], "NO_FIRST_GREEN")

    def test_first_completed_bar_has_no_prior_bar(self):
        b = fixture([candidate("green", "2026-10-06T14:00:00Z")])
        d = green.describe_first_green_candidate(b, "green")
        self.assertEqual(d["state"], "UNAVAILABLE")
        self.assertIn("NO_PREVIOUS_COMPLETED_SAME_SESSION_30M", d["refusals"])

    def test_missing_previous_minute_is_unavailable_not_negative(self):
        b = witness()
        b["minutes"].remove(minute(b, "2026-10-06T15:29:00Z"))
        d = green.describe_first_green_candidate(b, "green")
        self.assertEqual(d["state"], "UNAVAILABLE")
        self.assertIsNone(d["condition_met"])

    def test_missing_current_minute_is_unavailable(self):
        b = witness()
        b["minutes"].remove(minute(b, "2026-10-06T15:59:00Z"))
        d = green.describe_first_green_candidate(b, "green")
        self.assertEqual(d["state"], "UNAVAILABLE")
        self.assertIsNone(d["condition_met"])

    def test_owner_ineligible_does_not_form(self):
        b = witness()
        b["contexts"][0]["payload"]["controlled_pullback"] = False
        self.assertEqual(green.describe_first_green_candidate(b, "green")["state"], "NOT_ELIGIBLE")

    def test_future_correction_does_not_rewrite_early_descriptor(self):
        b = witness()
        original = green.describe_first_green_candidate(b, "green")
        corr = copy.deepcopy(minute(b, "2026-10-06T15:00:00Z"))
        corr.update(known_at="2026-10-06T16:10:00Z",
                    revision_id="synthetic-late-revision", close=101.7)
        b["minutes"].append(corr)
        self.assertEqual(original, green.describe_first_green_candidate(b, "green"))


class FirstGreenProgressTests(unittest.TestCase):
    def test_reference_is_distinct_and_sealed(self):
        r = frozen()
        self.assertEqual(r["definition_id"], green.PROGRESS_DEFINITION_ID)
        self.assertEqual(r["formation"]["definition_id"], green.DEFINITION_ID)
        self.assertEqual(r["confirmation_level"], "102.01")
        self.assertEqual(r["invalidation_level"], "98.99")
        self.assertFalse(r["source_admitted"])
        self.assertEqual(r["reference_sha256"], digest({k:v for k,v in r.items() if k!="reference_sha256"}))

    def test_integer_and_float_buffers_have_same_identity(self):
        b = witness()
        x = green.freeze_first_green_reference(b, "green", buffer_size=1, episode_expires_at="2026-10-06T17:00:00Z")
        y = green.freeze_first_green_reference(b, "green", buffer_size=1.0, episode_expires_at="2026-10-06T17:00:00Z")
        self.assertEqual(x, y)

    def test_completed_close_above_high_confirms(self):
        b = witness()
        r = frozen(b)
        followup(b)
        confirm_minute(b)
        p = green.describe_first_green_progress(b, "following", reference=r)
        self.assertEqual(p["state"], "GREEN_BREAK_CONFIRMED")
        self.assertEqual(p["confirmation"]["bar_end"], "2026-10-06T16:02:00Z")
        self.assertEqual(p["confirmation"]["known_at"], "2026-10-06T16:02:00Z")
        self.assertFalse(p["actual_issuance_proven"])
        self.assertTrue(all(v is False for v in p["authority"].values()))

    def test_high_touch_without_close_remains_waiting(self):
        b = witness()
        r = frozen(b)
        followup(b)
        minute(b, "2026-10-06T16:01:00Z").update(open=101.0, high=103.0, low=100.0, close=101.5)
        p = green.describe_first_green_progress(b, "following", reference=r)
        self.assertEqual(p["state"], "WAITING_CONFIRMATION")
        self.assertIsNone(p["confirmation"])

    def test_low_breach_invalidates(self):
        b = witness()
        r = frozen(b)
        followup(b)
        minute(b, "2026-10-06T16:01:00Z").update(open=100.0, high=103.0, low=98.5, close=100.0)
        p = green.describe_first_green_progress(b, "following", reference=r)
        self.assertEqual(p["state"], "INVALIDATED")
        self.assertIsNone(p["confirmation"])
        self.assertEqual(p["invalidation"]["bar_end"], "2026-10-06T16:02:00Z")

    def test_same_minute_low_breach_beats_confirmation(self):
        b = witness()
        r = frozen(b)
        followup(b)
        minute(b, "2026-10-06T16:01:00Z").update(open=100.0, high=104.0, low=98.5, close=103.0)
        p = green.describe_first_green_progress(b, "following", reference=r)
        self.assertEqual(p["state"], "INVALIDATED")
        self.assertIsNone(p["confirmation"])

    def test_missing_earlier_minute_blocks_later_confirm(self):
        b = witness()
        r = frozen(b)
        followup(b)
        confirm_minute(b)
        b["minutes"].remove(minute(b, "2026-10-06T16:00:00Z"))
        p = green.describe_first_green_progress(b, "following", reference=r)
        self.assertEqual(p["state"], "UNAVAILABLE")
        self.assertIsNone(p["confirmation"])

    def test_later_gap_retains_earlier_confirmation(self):
        b = witness()
        r = frozen(b)
        followup(b)
        confirm_minute(b)
        b["minutes"].remove(minute(b, "2026-10-06T16:03:00Z"))
        p = green.describe_first_green_progress(b, "following", reference=r)
        self.assertEqual(p["state"], "UNAVAILABLE")
        self.assertIsNotNone(p["confirmation"])

    def test_reference_tamper_refused(self):
        b = witness()
        r = frozen(b)
        r["confirmation_level"] = "103.01"
        followup(b)
        with self.assertRaises(InputContractError):
            green.describe_first_green_progress(b, "following", reference=r)

    def test_basis_change_refused_in_followup(self):
        b = witness()
        r = frozen(b)
        followup(b)
        b["streams"]["stock"]["basis"]["basis_id"] = "another-basis"
        p = green.describe_first_green_progress(b, "following", reference=r)
        self.assertEqual(p["state"], "UNAVAILABLE")
        self.assertIn("FROZEN_IDENTITY_OR_BASIS_CHANGED", p["refusals"])

    def test_clean_expiry_without_confirmation(self):
        b = witness()
        r = frozen(b, expiry="2026-10-06T16:03:00Z")
        followup(b, "2026-10-06T16:03:00Z")
        p = green.describe_first_green_progress(b, "following", reference=r)
        self.assertEqual(p["state"], "EXPIRED")
        self.assertIsNone(p["confirmation"])
