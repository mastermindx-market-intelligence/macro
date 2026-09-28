"""Synthetic contract tests for the real GD-6A module and stdout qualification CLI.

Fixtures follow the inspected native v0 envelope shape; they are not market data,
source-authentication proof, performance observations, or deployed UI evidence.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from hashlib import sha256
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import prophet_market_eligibility as m
from scripts import build_prophet_market_eligibility as cli

SESSION = "2026-09-25"
DECISION = "2026-09-28T13:20:00Z"
EXPIRY = "2026-09-28T14:00:00Z"
READ = "2026-09-28T13:25:00Z"


def encode(doc):
    return json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def reseal(doc):
    semantic = {k: v for k, v in doc.items()
                if k not in {"bundle_id", "observed_at", "produced_at", "stale_after"}}
    doc["bundle_id"] = sha256(encode(semantic)).hexdigest()[:16]
    return doc


def board_fixture():
    return {
        "board_definition": "us_prophet_v3", "as_of": SESSION,
        "staleness": {"price_through": SESSION, "delayed": False, "unknown": False,
                      "basis": "panel_majority"},
        "gate_go": False,
        "buy": [
            {"ticker": "SYNTH_A", "lane": "buy", "prophet": {"rank": 1, "score": 99},
             "entry_signal": {"status": "buy_now"}, "fictional": True},
            {"ticker": "SYNTH_B", "lane": "watch", "prophet": None, "fictional": True},
        ],
        "opaque_owner_field": {"keep": [1, None, "原始"]},
    }


def envelope_fixture():
    return reseal({
        "schema": m.ENVELOPE_SCHEMA, "definition_id": m.ENVELOPE_DEFINITION,
        "market": "US", "revision": "settled", "source_session": SESSION, "as_of": SESSION,
        "measured_state": {"verdict": "RISK_OFF", "score": 12, "usable": True},
        "hazard_summary": {"stage": "FRAGILE", "display_only": True},
        "episodes": [], "policies": [],
        "policy_summary": {"posture": "NORMAL", "active_policy_ids": [], "policy_count": 0,
                           "basis": "zero_active_policies", "display_only": True},
        "data_state": "FRESH", "repair_state": None,
        "coherence": {"state": "MIXED", "scope": "market_reads"},
        "coverage": {"required": ["measured", "leadership"], "optional": [],
                     "fresh": ["measured", "leadership"], "missing": [], "stale": [], "source_count": 2},
        "freshness": {"source_session": SESSION, "all_on_session": True, "off_session_sources": [],
                      "per_source": {key: {"as_of": SESSION, "state": "FRESH", "matches_session": True}
                                     for key in ("measured", "leadership")}},
        "correction": None, "provenance": {"sources": []},
        "authority": dict(m._ENVELOPE_AUTHORITY),
        "observed_at": "2026-09-25T21:00:00Z", "produced_at": "2026-09-25T21:00:00Z",
        "stale_after": None,
    })


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.board, self.envelope = board_fixture(), envelope_fixture()

    def kwargs(self, raw_board=None, raw_envelope=None):
        return dict(expected_board_sha256=sha256(raw_board or encode(self.board)).hexdigest(),
                    expected_board_definition=self.board["board_definition"],
                    expected_source_session=SESSION,
                    expected_envelope_sha256=sha256(raw_envelope or encode(self.envelope)).hexdigest(),
                    decision_at=DECISION, valid_until=EXPIRY)

    def compose(self, **overrides):
        kw = self.kwargs()
        kw.update(overrides)
        return m.compose_market_eligibility(encode(self.board), encode(self.envelope), **kw)

    def unavailable(self, reason):
        result = self.compose()
        self.assertEqual(result["source_state"], "UNAVAILABLE")
        self.assertIn(reason, result["errors"])
        self.assertEqual(len(result["rows"]), len(self.board["buy"]))
        self.assertTrue(all(row["market_eligibility"]["action"] is None for row in result["rows"]))
        self.assertTrue(all(v is False for v in result["authority"].values()))
        return result

    def bound_view(self, sidecar=None, **overrides):
        kw = self.kwargs()
        kw["expected_decision_at"] = kw.pop("decision_at")
        kw["expected_valid_until"] = kw.pop("valid_until")
        kw["read_at"] = READ
        kw.update(overrides)
        return m.bind_shadow_view(sidecar or self.compose(), encode(self.board), encode(self.envelope), **kw)

    def test_zero_policy_is_not_buy_permission(self):
        result = self.compose()
        self.assertEqual(result["source_state"], "AVAILABLE")
        self.assertEqual(result["production_behavior"], "UNCHANGED")
        self.assertTrue(all(v is False for v in result["authority"].values()))
        for row in result["rows"]:
            self.assertEqual(row["market_eligibility"]["action"], "ELIGIBLE")
            self.assertEqual(row["market_eligibility"]["action_meaning"],
                             "NO_MARKET_POLICY_CONSTRAINT_NOT_BUY_PERMISSION")

    def test_raw_board_and_order_byte_preserved(self):
        raw = encode(self.board)
        result = self.compose()
        self.assertEqual(raw, encode(self.board))
        self.assertEqual([r["ticker"] for r in result["rows"]], ["SYNTH_A", "SYNTH_B"])
        self.assertEqual(result["rows"][1]["raw_rank"], None)
        self.assertEqual(result["rows"][1]["source_position"], 2)
        self.assertEqual(self.bound_view()["rows"][0]["candidate"], self.board["buy"][0])

    def test_raw_rank_never_inferred_from_position(self):
        self.board["buy"][0]["prophet"]["rank"] = 17
        out = self.compose()["rows"]
        self.assertEqual(out[0]["raw_rank"], 17)
        self.assertEqual(out[0]["source_position"], 1)
        self.assertIsNone(out[1]["raw_rank_basis"])

    def test_duplicate_aliases_are_not_deduplicated(self):
        self.board["buy"].append(deepcopy(self.board["buy"][0]))
        rows = self.compose()["rows"]
        self.assertEqual(len(rows), 3)
        self.assertNotEqual(rows[0]["source_pointer"], rows[2]["source_pointer"])
        self.assertNotIn("security_id", rows[0])

    def test_empty_board_is_not_missing_board(self):
        self.board["buy"] = []
        self.assertEqual(self.compose()["rows"], [])
        del self.board["buy"]
        with self.assertRaisesRegex(m.MarketEligibilityError, "BOARD_POPULATION_UNREADABLE"):
            self.compose()

    def test_foreign_board_definition_refused(self):
        self.board["board_definition"] = "cn_prophet_v2"
        with self.assertRaisesRegex(m.MarketEligibilityError, "BOARD_DEFINITION_UNSUPPORTED"):
            self.compose()

    def test_fallback_era_preserved_not_renamed(self):
        self.board["board_definition"] = "us_prophet_v2_fallback"
        self.assertEqual(self.compose()["board"]["definition"], "us_prophet_v2_fallback")

    def test_board_raw_hash_not_reencoded_hash(self):
        raw = json.dumps(self.board, indent=2).encode()
        with self.assertRaisesRegex(m.MarketEligibilityError, "BOARD_HASH_MISMATCH"):
            m.compose_market_eligibility(raw, encode(self.envelope), **self.kwargs())
        result = m.compose_market_eligibility(raw, encode(self.envelope), **self.kwargs(raw))
        self.assertEqual(result["board"]["sha256"], sha256(raw).hexdigest())

    def test_session_and_definition_mismatch(self):
        for kw in ({"expected_source_session": "2026-09-24"},
                   {"expected_board_definition": "us_prophet_v2_fallback"}):
            with self.subTest(kw=kw), self.assertRaises(m.MarketEligibilityError):
                self.compose(**kw)

    def test_malformed_board_has_no_partial_denominator(self):
        for raw in (b"[]", b"null", b"", b'{"buy": [1]}', b'{"x":1,"x":2}'):
            with self.subTest(raw=raw), self.assertRaises(m.MarketEligibilityError):
                m.compose_market_eligibility(raw, encode(self.envelope), **self.kwargs(raw))

    def test_bad_row_is_not_silently_dropped(self):
        self.board["buy"].append(None)
        with self.assertRaisesRegex(m.MarketEligibilityError, "BOARD_POPULATION_UNREADABLE"):
            self.compose()

    def test_health_unknown_retains_research(self):
        self.board.pop("staleness")
        self.unavailable("BOARD_SOURCE_HEALTH_UNQUALIFIED")
        self.assertEqual(len(self.bound_view()["rows"]), 2)

    def test_numeric_false_not_boolean_health(self):
        self.board["staleness"]["delayed"] = 0
        self.unavailable("BOARD_SOURCE_HEALTH_UNQUALIFIED")

    def test_board_clock_mismatch_unavailable(self):
        self.board["staleness"]["price_through"] = "2026-09-24"
        self.unavailable("BOARD_SOURCE_HEALTH_UNQUALIFIED")

    def test_missing_envelope_retains_every_row(self):
        kw = self.kwargs(); kw["expected_envelope_sha256"] = None
        result = m.compose_market_eligibility(encode(self.board), None, **kw)
        self.assertEqual(result["errors"], ["ENVELOPE_MISSING"])
        self.assertEqual(len(result["rows"]), 2)

    def test_envelope_hash_required_and_exact(self):
        for val, reason in ((None, "ENVELOPE_EXPECTED_HASH_MISSING"), ("0"*64, "ENVELOPE_RAW_HASH_MISMATCH")):
            with self.subTest(val=val):
                self.assertIn(reason, self.compose(expected_envelope_sha256=val)["errors"])

    def test_raw_envelope_clock_change_not_hidden_by_same_bundle(self):
        old = sha256(encode(self.envelope)).hexdigest()
        bundle = self.envelope["bundle_id"]
        self.envelope["produced_at"] = "2026-09-25T21:01:00Z"
        self.assertEqual(self.envelope["bundle_id"], bundle)
        self.assertIn("ENVELOPE_RAW_HASH_MISMATCH", self.compose(expected_envelope_sha256=old)["errors"])

    def test_envelope_semantic_hash_checked(self):
        self.envelope["measured_state"]["score"] = 70
        self.unavailable("ENVELOPE_BUNDLE_MISMATCH")

    def test_no_policy_fabricated_from_red_or_calm(self):
        for state in ("RISK_ON", "MIXED", "RISK_OFF"):
            self.envelope["measured_state"]["verdict"] = state
            reseal(self.envelope)
            with self.subTest(state=state):
                self.assertEqual(self.compose()["rows"][0]["market_eligibility"]["policy_ids"], [])
                self.assertEqual(self.compose()["source_state"], "AVAILABLE")

    def test_fabricated_deny_not_promoted_from_unowned_policy(self):
        self.envelope["policies"] = [{"action": "NO_NEW_LONG_RISK", "authority_basis": "earned"}]
        reseal(self.envelope)
        self.unavailable("POLICY_PRODUCER_NOT_SUPPORTED")

    def test_null_policies_are_not_empty(self):
        self.envelope["policies"] = None; reseal(self.envelope)
        self.unavailable("POLICY_PRODUCER_NOT_SUPPORTED")

    def test_false_policy_count_not_zero(self):
        self.envelope["policy_summary"]["policy_count"] = False; reseal(self.envelope)
        self.unavailable("POLICY_SUMMARY_NOT_ZERO_POLICY")

    def test_false_authority_must_be_actual_boolean(self):
        self.envelope["authority"]["envelope_may_gate"] = 0; reseal(self.envelope)
        self.unavailable("ENVELOPE_AUTHORITY_UNSUPPORTED")

    def test_authority_widening_rejected_even_with_valid_hash(self):
        self.envelope["authority"]["envelope_may_gate"] = True; reseal(self.envelope)
        self.unavailable("ENVELOPE_AUTHORITY_UNSUPPORTED")

    def test_future_unknown_or_foreign_envelope_held(self):
        for key, val, reason in (("schema", "mastermind.risk_envelope/v2", "ENVELOPE_DEFINITION_UNSUPPORTED"),
                                 ("market", "CN", "ENVELOPE_MARKET_MISMATCH"),
                                 ("revision", "live_provisional", "UNSETTLED_ENVELOPE"),
                                 ("source_session", "2026-09-24", "ENVELOPE_SESSION_MISMATCH")):
            with self.subTest(key=key):
                self.envelope = envelope_fixture(); self.envelope[key] = val; reseal(self.envelope)
                self.unavailable(reason)

    def test_missing_and_stale_not_calm(self):
        for state in ("PARTIAL", "DEGRADED", "STALE", "UNKNOWN", None):
            with self.subTest(state=state):
                self.envelope["data_state"] = state; reseal(self.envelope)
                self.unavailable("ENVELOPE_DATA_NOT_FRESH")

    def test_per_source_clock_cannot_be_hidden_by_summary(self):
        self.envelope["freshness"]["per_source"]["leadership"]["as_of"] = None
        reseal(self.envelope)
        self.unavailable("ENVELOPE_SOURCE_CLOCKS_UNQUALIFIED")

    def test_zero_required_coverage_not_full(self):
        self.envelope["coverage"]["required"] = []; reseal(self.envelope)
        self.unavailable("ENVELOPE_COVERAGE_UNQUALIFIED")

    def test_absent_required_source_not_renormalized(self):
        self.envelope["coverage"]["fresh"].remove("leadership"); reseal(self.envelope)
        self.unavailable("ENVELOPE_COVERAGE_UNQUALIFIED")

    def test_future_emission_or_reverse_clock(self):
        for observed, produced in (("2026-09-28T13:21:00Z", "2026-09-28T13:21:00Z"),
                                   ("2026-09-25T22:00:00Z", "2026-09-25T21:00:00Z")):
            with self.subTest(observed=observed):
                self.envelope["observed_at"], self.envelope["produced_at"] = observed, produced
                self.unavailable("ENVELOPE_NOT_AVAILABLE_AT_DECISION")

    def test_native_expiry_is_half_open(self):
        self.envelope["stale_after"] = DECISION
        self.unavailable("ENVELOPE_EXPIRED")

    def test_projection_cannot_outlive_native_expiry(self):
        self.envelope["stale_after"] = "2026-09-28T13:30:00Z"
        self.unavailable("WINDOW_EXCEEDS_ENVELOPE_EXPIRY")
        out = self.compose(valid_until="2026-09-28T13:30:00Z")
        self.assertEqual(out["source_state"], "AVAILABLE")

    def test_native_null_expiry_does_not_invent_calendar(self):
        self.assertEqual(self.compose()["valid_until"], EXPIRY)
        with self.assertRaises(m.MarketEligibilityError):
            self.compose(valid_until=None)

    def test_invalid_or_naive_clocks_refused(self):
        for value in ("2026-09-28", "2026-09-28T13:20:00", "2026-09-28T13:20:00+00:00", "bad"):
            with self.subTest(value=value), self.assertRaises(m.MarketEligibilityError):
                self.compose(decision_at=value)

    def test_invalid_window_or_hash_refused(self):
        for kw in ({"valid_until": DECISION}, {"expected_board_sha256": "ABC"},
                   {"expected_envelope_sha256": True}, {"expected_source_session": "20260925"}):
            with self.subTest(kw=kw), self.assertRaises(m.MarketEligibilityError):
                self.compose(**kw)

    def test_nonfinite_surrogate_duplicate_nested_keys(self):
        for raw in (b'{"x":NaN}', b'{"x":1e999}', b'{"x":"\\ud800"}', b'{"x":{"z":1,"z":2}}'):
            with self.subTest(raw=raw), self.assertRaises(m.MarketEligibilityError):
                m.compose_market_eligibility(raw, None, **self.kwargs(raw))

    def test_malformed_envelope_is_unavailable_not_empty_policy(self):
        for raw in (b'{"x":NaN}', b'{"x":1e999}', b'{"x":1,"x":2}', b'[]'):
            with self.subTest(raw=raw):
                kw = self.kwargs(raw_envelope=raw)
                out = m.compose_market_eligibility(encode(self.board), raw, **kw)
                self.assertIn("ENVELOPE_UNREADABLE", out["errors"])

    def test_same_inputs_are_byte_deterministic(self):
        self.assertEqual(encode(self.compose()), encode(self.compose()))

    def test_input_order_preserved_when_not_rank_order(self):
        self.board["buy"].reverse()
        self.assertEqual([r["ticker"] for r in self.compose()["rows"]], ["SYNTH_B", "SYNTH_A"])

    def test_bound_view_preserves_all_candidate_content(self):
        view = self.bound_view()
        self.assertEqual([r["candidate"] for r in view["rows"]], self.board["buy"])
        view["rows"][0]["candidate"]["prophet"]["score"] = -1
        self.assertEqual(self.board["buy"][0]["prophet"]["score"], 99)

    def test_rehashed_sidecar_widening_cannot_pass(self):
        for key in m._AUTHORITY:
            with self.subTest(key=key):
                changed = self.compose(); changed["authority"][key] = True
                changed["sidecar_id"] = "pme:" + m._digest({k: v for k, v in changed.items() if k != "sidecar_id"})
                with self.assertRaisesRegex(m.MarketEligibilityError, "SIDECAR_SEMANTIC_MISMATCH"):
                    self.bound_view(changed)

    def test_numeric_authority_sidecar_rejected(self):
        out = self.compose(); out["authority"]["can_execute"] = 0
        with self.assertRaises(m.MarketEligibilityError): self.bound_view(out)

    def test_sidecar_reordering_deletion_or_action_edit_rejected(self):
        for edit in (lambda x: x["rows"].reverse(), lambda x: x["rows"].pop(),
                     lambda x: x["rows"][0]["market_eligibility"].update(action="NO_NEW_LONG_RISK")):
            changed = self.compose(); edit(changed)
            changed["sidecar_id"] = "pme:" + m._digest({k: v for k, v in changed.items() if k != "sidecar_id"})
            with self.assertRaises(m.MarketEligibilityError): self.bound_view(changed)

    def test_expiry_rehash_does_not_extend_consumer_window(self):
        out = self.compose(); out["valid_until"] = "2026-10-01T00:00:00Z"
        out["sidecar_id"] = "pme:" + m._digest({k: v for k, v in out.items() if k != "sidecar_id"})
        with self.assertRaises(m.MarketEligibilityError): self.bound_view(out)

    def test_read_expiry_boundary(self):
        for clock in (EXPIRY, "2026-09-28T13:19:59Z"):
            with self.subTest(clock=clock), self.assertRaisesRegex(m.MarketEligibilityError, "SIDECAR_OUTSIDE_VALIDITY_WINDOW"):
                self.bound_view(read_at=clock)
        self.assertEqual(self.bound_view(read_at=DECISION)["source_state"], "AVAILABLE")

    def test_source_generation_change_refuses_old_sidecar(self):
        old = self.compose()
        self.board["buy"][0]["prophet"]["score"] = 100
        with self.assertRaises(m.MarketEligibilityError): self.bound_view(old)

    def test_pure_module_contains_no_io_clock_or_registry(self):
        tree = ast.parse(Path(m.__file__).read_text())
        calls = [n.func.id if isinstance(n.func, ast.Name) else n.func.attr
                 for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, (ast.Name, ast.Attribute))]
        for prohibited in ("open", "read_bytes", "write_text", "write_bytes", "getenv", "now", "today", "urlopen"):
            self.assertNotIn(prohibited, calls)


class CliTests(unittest.TestCase):
    def execute(self, changes=None):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); b = encode(board_fixture()); e = encode(envelope_fixture())
            (root / "b.json").write_bytes(b); (root / "e.json").write_bytes(e)
            args = ["--board", str(root / "b.json"), "--board-sha256", sha256(b).hexdigest(),
                    "--board-definition", "us_prophet_v3", "--source-session", SESSION,
                    "--risk-envelope", str(root / "e.json"), "--envelope-sha256", sha256(e).hexdigest(),
                    "--decision-at", DECISION, "--valid-until", EXPIRY]
            if changes: changes(args, root)
            before = {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = cli.main(args)
            after = {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}
            self.assertEqual(before, after)
            return code, out.getvalue(), err.getvalue()

    def test_real_stdout_entry_point_no_file_mutation(self):
        code, out, err = self.execute()
        self.assertEqual(code, 0); self.assertEqual(err, "")
        self.assertEqual(json.loads(out)["mode"], "SHADOW_ONLY")

    def test_wrong_hash_returns_nonzero_no_result(self):
        code, out, err = self.execute(lambda a, _: a.__setitem__(a.index("--board-sha256")+1, "0"*64))
        self.assertEqual(code, 1); self.assertEqual(out, "")
        self.assertIn("BOARD_HASH_MISMATCH", err)

    def test_missing_file_not_zero_policy(self):
        code, out, err = self.execute(lambda a, r: a.__setitem__(a.index("--risk-envelope")+1, str(r/"missing")))
        self.assertEqual(code, 1); self.assertEqual(out, "")
        self.assertIn("SOURCE_READ_FAILED", err)
        self.assertNotIn("missing", err)

    def test_explicit_unavailable_has_distinct_exit(self):
        def change(args, _):
            idx = args.index("--risk-envelope"); del args[idx:idx+2]
            idx = args.index("--envelope-sha256"); del args[idx:idx+2]
            args.append("--risk-unavailable")
        code, out, err = self.execute(change)
        self.assertEqual(code, 2); self.assertEqual(err, "")
        self.assertEqual(json.loads(out)["errors"], ["ENVELOPE_MISSING"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
