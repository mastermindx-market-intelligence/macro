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
import os
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

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
        # A source-session mismatch with an intact, hash-bound board is disclosed
        # on every row, not confused with an unreadable population. The wrapper
        # publication date is a distinct clock and cannot repair stale prices.
        result = self.compose(expected_source_session="2026-09-24")
        self.assertEqual(result["source_state"], "UNAVAILABLE")
        self.assertIn("BOARD_SOURCE_HEALTH_UNQUALIFIED", result["errors"])
        self.assertEqual(len(result["rows"]), len(self.board["buy"]))
        with self.assertRaises(m.MarketEligibilityError):
            self.compose(expected_board_definition="us_prophet_v2_fallback")

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

    def test_coverage_inventory_cannot_omit_or_duplicate_sources(self):
        cases = [
            ("duplicate_fresh", lambda x: x["coverage"]["fresh"].append("measured")),
            ("overlapping_roles", lambda x: x["coverage"]["optional"].append("measured")),
            ("unreported_optional", lambda x: x["coverage"]["optional"].append("new-source")),
            ("wrong_source_count", lambda x: x["coverage"].update(source_count=3)),
            ("boolean_source_count", lambda x: x["coverage"].update(source_count=True)),
            ("extra_clock", lambda x: x["freshness"]["per_source"].update(extra={
                "as_of": SESSION, "state": "FRESH", "matches_session": True})),
        ]
        for name, edit in cases:
            with self.subTest(case=name):
                self.envelope = envelope_fixture()
                edit(self.envelope); reseal(self.envelope)
                self.unavailable("ENVELOPE_COVERAGE_UNQUALIFIED")

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

    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW"), "POSIX descriptor guard required")
    def test_symlink_swap_cannot_pass_a_prior_path_check(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); target = root / "target"; target.write_bytes(b"fictional")
            link = root / "link"; link.symlink_to(target)
            # Deterministically represents the link being swapped after a prior
            # path check. The opened descriptor must enforce refusal itself.
            with patch.object(Path, "is_symlink", return_value=False):
                with self.assertRaises((OSError, m.MarketEligibilityError)):
                    cli._read(link)

    @unittest.skipUnless(os.name == "posix", "POSIX regular-file policy")
    def test_device_source_is_not_a_regular_file(self):
        with self.assertRaises(m.MarketEligibilityError):
            cli._read(Path(os.devnull))

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX FIFO fixture")
    def test_fifo_source_refuses_without_waiting_for_a_writer(self):
        with tempfile.TemporaryDirectory() as td:
            fifo = Path(td) / "fixture.fifo"; os.mkfifo(fifo)
            command = [sys.executable, "-c", (
                "from pathlib import Path; "
                "from scripts.build_prophet_market_eligibility import _read; "
                "_read(Path(__import__('sys').argv[1]))"), str(fifo)]
            try:
                result = subprocess.run(command, cwd=ROOT, capture_output=True,
                                        text=True, timeout=2, check=False)
            except subprocess.TimeoutExpired:
                self.fail("source acquisition waited for a FIFO writer")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("SOURCE_NOT_REGULAR_FILE", result.stderr)

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


class TestNamedPolicyOrigination(unittest.TestCase):
    """Fictional accepted-rule receipts; no production grant or market outcomes."""
    def setUp(self):
        from copy import deepcopy
        self.now = "2026-09-28T13:00:00Z"
        self.board = {"board_definition":"us_prophet_v3", "as_of":"2026-09-25",
            "staleness":{"price_through":"2026-09-25","observed_at_utc":"2026-09-28T13:00:00Z",
                         "delayed":False,"unknown":False,"basis":"panel_majority"},
            "gate_go":True,"buy":[]}
        for ticker,score in [("AAA",99),("BBB",90)]:
            self.board["buy"].append({"ticker":ticker,"dir":"up","act_level":3,
                "prophet":{"score":score},"conviction":{"score":score,"band":"high"},
                "entry_signal":{"status":"buy_now","spot":100.0,"trigger":99.0,
                                "signal_date":"2026-09-25"},
                "hold":{"anchor":"2026-09-25","invalidation":95.0}})
        self.rule = {"policy_id":"fixture-risk-pause", "rule_id":"fixture-no-new-long", "rule_version":"1",
            "authority_basis":"temporary_operator_safety", "grant_ref":"fixture-only:not-a-live-grant",
            "action":"NO_NEW_LONG_RISK", "state":"ACTIVE", "market":"US",
            "board_definition":"us_prophet_v3", "lifecycle":"NEW_LONG_RECOMMENDATION", "tickers":["*"],
            "starts_at":"2026-09-28T12:00:00Z","expires_at":"2026-09-28T20:00:00Z",
            "restore_condition":"Owning rule lifted or expired; native entry still required."}

    def bind(self, rules=None, *, available=True, expected=None):
        from engine.prophet_market_eligibility import bind_new_long_restrictions, _digest
        rules = [self.rule] if rules is None else rules
        if expected is None: expected = {p["policy_id"]:_digest(p) for p in rules}
        return bind_new_long_restrictions(self.board, rules, expected_rule_hashes=expected,
            observed_at=self.now, valid_until="2026-09-28T21:00:00Z", source_available=available)

    def invoke(self, context=None, *, existing_ids=None, active_keys=None, clock=None):
        from engine import prophet_bridge as pb
        from unittest.mock import patch
        import pandas as pd
        from tempfile import TemporaryDirectory
        prices=pd.DataFrame({"open":100.0,"high":102.0,"low":98.0,"close":100.0,"volume":1000000},
            index=pd.bdate_range(end="2026-09-25",periods=40))
        stats={}
        with TemporaryDirectory() as root, patch.object(pb,"_load_price_history",return_value=prices):
            plans=pb.originate_plans(Path(root)/"board.json","2026-09-28",existing_ids or set(),
                active_keys=active_keys, intake_stats=stats, standouts_doc=self.board,
                new_long_restrictions=context, policy_read_at=clock or self.now)
        return plans,stats

    def test_high_rank_native_admission_then_named_rule_stops_origination(self):
        from engine import prophet_bridge as pb
        self.assertEqual([r["ticker"] for r in pb.select_candidates(self.board,n=None)],["AAA","BBB"])
        plans,stats=self.invoke(self.bind())
        self.assertEqual(plans,[]);self.assertEqual(stats["admitted"],2)
        self.assertEqual(stats["market_policy_suppressed"],2)
        self.assertEqual(stats["validation_failed"],0);self.assertEqual(stats["unaccounted"],0)
        self.assertTrue(stats["lossless"])
        self.assertEqual([d["policy_ids"] for d in stats["market_policy_dispositions"]],
                         [["fixture-risk-pause"],["fixture-risk-pause"]])

    def test_unadopted_path_still_originates_native_plans(self):
        plans,stats=self.invoke()
        self.assertEqual(len(plans),2,stats)
        self.assertNotIn("market_policy_suppressed",stats)

    def test_expired_rule_returns_exact_base_plans(self):
        self.rule["expires_at"]="2026-09-28T12:59:59Z"
        base,base_stats=self.invoke();plans,stats=self.invoke(self.bind())
        self.assertEqual(len(base),2,base_stats);self.assertEqual(plans,base)
        self.assertEqual(stats["market_policy_suppressed"],0)

    def test_scope_only_removes_named_new_entry_not_other_candidate(self):
        self.rule["tickers"]=["AAA"]
        base,_=self.invoke();plans,stats=self.invoke(self.bind())
        self.assertEqual([p["id"] for p in plans],["BBB-BULL-20260925"])
        self.assertEqual(plans,[p for p in base if p["id"]=="BBB-BULL-20260925"])
        self.assertEqual(stats["market_policy_suppressed"],1)
        self.assertEqual(stats["unaccounted"],0)

    def test_existing_position_duplicate_protections_are_not_liquidation(self):
        from engine import prophet_bridge as pb
        key=pb.plan_key("AAA","BULL")
        plans,stats=self.invoke(self.bind(),active_keys={key})
        self.assertEqual(plans,[]);self.assertEqual(stats["reorigination_blocked"],1)
        self.assertEqual(stats["market_policy_suppressed"],1)
        self.assertEqual(stats["unaccounted"],0)

    def test_every_research_row_and_score_is_untouched(self):
        from copy import deepcopy
        original=deepcopy(self.board);self.invoke(self.bind())
        self.assertEqual(self.board,original)

    def test_missing_expected_record_withholds_not_all_clear(self):
        from engine.prophet_market_eligibility import _digest
        ctx=self.bind([],expected={self.rule["policy_id"]:_digest(self.rule)})
        self.assertEqual(ctx.decision("AAA",read_at=self.now)["state"],"UNAVAILABLE")
        plans,stats=self.invoke(ctx);self.assertEqual(plans,[])
        self.assertEqual(stats["market_policy_suppressed"],2)

    def test_missing_source_does_not_erase_active_rule(self):
        decision=self.bind(available=False).decision("AAA",read_at=self.now)
        self.assertEqual(decision["state"],"DENY_NEW_LONG")
        self.assertEqual(decision["policy_ids"],["fixture-risk-pause"])
        self.assertIn("POLICY_SOURCE_UNAVAILABLE",decision["errors"])

    def test_missing_source_without_current_rule_is_unavailable(self):
        self.rule["state"]="REVOKED"
        self.assertEqual(self.bind(available=False).decision("AAA",read_at=self.now)["state"],"UNAVAILABLE")

    def test_one_rule_revocation_cannot_cancel_another(self):
        from copy import deepcopy
        other=deepcopy(self.rule);other.update(policy_id="fixture-second",state="REVOKED")
        ctx=self.bind([other,self.rule]);self.assertEqual(ctx.decision("AAA",read_at=self.now)["policy_ids"],["fixture-risk-pause"])

    def test_policy_order_is_irrelevant_and_all_ids_print(self):
        from copy import deepcopy
        other=deepcopy(self.rule);other["policy_id"]="fixture-second"
        a=self.bind([self.rule,other]);b=self.bind([other,self.rule])
        self.assertEqual(a,b);self.assertEqual(len(a.decision("AAA",read_at=self.now)["rules"]),2)

    def test_rule_digest_mismatch_cannot_restore_permission(self):
        from engine.prophet_market_eligibility import _digest
        trusted={self.rule["policy_id"]:_digest(self.rule)}
        self.rule["state"]="REVOKED"
        self.assertEqual(self.bind(expected=trusted).decision("AAA",read_at=self.now)["state"],"UNAVAILABLE")

    def test_wrong_board_cannot_reuse_bound_read(self):
        from engine.prophet_market_eligibility import MarketEligibilityError
        ctx=self.bind();self.board["buy"][0]["prophet"]["score"]=100
        with self.assertRaisesRegex(MarketEligibilityError,"BOARD_BINDING_MISMATCH"):self.invoke(ctx)

    def test_outside_read_window_never_authorizes_new_plans(self):
        for clock in ["2026-09-28T12:59:59Z","2026-09-28T21:00:00Z"]:
            with self.subTest(clock=clock):
                plans,stats=self.invoke(self.bind(),clock=clock)
                self.assertEqual(plans,[]);self.assertEqual(stats["market_policy_suppressed"],2)

    def test_future_policy_has_no_effect_before_its_start(self):
        self.rule["starts_at"]="2026-09-28T14:00:00Z"
        self.assertEqual(self.bind().decision("AAA",read_at=self.now)["state"],"NO_POLICY_CONSTRAINT")

    def test_no_grant_set_is_not_an_opt_in(self):
        from engine.prophet_market_eligibility import MarketEligibilityError
        with self.assertRaisesRegex(MarketEligibilityError,"OWNER_BINDING_REQUIRED"):self.bind(expected={})

    def test_unsupported_action_or_scope_never_turns_into_buy_permission(self):
        from copy import deepcopy
        for key,value in [("action","AUTO_EXIT"),("market","CN"),("lifecycle","EXISTING_POSITION"),
                          ("authority_basis","MODEL_GUESS"),("tickers",["*","AAA"]),
                          ("board_definition","unknown")]:
            with self.subTest(key=key):
                p=deepcopy(self.rule);p[key]=value
                self.assertEqual(self.bind([p]).decision("AAA",read_at=self.now)["state"],"UNAVAILABLE")

    def test_input_mutation_cannot_change_frozen_policy(self):
        ctx=self.bind();self.rule["state"]="REVOKED"
        self.assertEqual(ctx.decision("AAA",read_at=self.now)["state"],"DENY_NEW_LONG")

    def test_duplicate_rule_does_not_create_extra_votes(self):
        from copy import deepcopy
        ctx=self.bind([self.rule,deepcopy(self.rule)])
        decision=ctx.decision("AAA",read_at=self.now)
        self.assertEqual(decision["policy_ids"],["fixture-risk-pause"])
        self.assertIn("POLICY_ID_DUPLICATE",decision["errors"])


class TestNamedPolicyPublication(unittest.TestCase):
    """Actual main and Arena, isolated roots/prices, fictional already-bound rules."""
    def setUp(self):
        self.fixture = TestNamedPolicyOrigination()
        self.fixture.setUp()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sequence = 0

    def build(self, context=None, *, clock=None, alter_stats=None, legacy_clock=False, seed_root=None):
        from contextlib import ExitStack
        from datetime import datetime, timezone
        from unittest.mock import patch
        import pandas as pd
        from engine import prophet_bridge as bridge
        from engine import prophet_arena as arena
        from lib import config
        from scripts import build_prophet as bp
        self.sequence += 1
        root = self.root / str(self.sequence)
        if seed_root is not None:
            import shutil
            shutil.copytree(seed_root,root)
        board_path = root / "site/factordata/us_standouts.json"
        board_path.parent.mkdir(parents=True,exist_ok=True)
        board_raw = json.dumps(self.fixture.board).encode()
        board_path.write_bytes(board_raw)
        prices = pd.DataFrame({"open":100.0,"high":102.0,"low":98.0,"close":100.0,"volume":1000000},
            index=pd.bdate_range(end="2026-09-25",periods=40))
        arena_real = arena.run_arena
        calls = []
        def scoped_arena(*args, **kwargs):
            calls.append(kwargs.get("live_plan_ids"))
            return arena_real(*args, **{**kwargs, "repo_root": root, "tilt_inputs": None})
        original_originator = bp.originate_plans
        def observed_originator(*args, **kwargs):
            result = original_originator(*args, **kwargs)
            if alter_stats is not None:
                alter_stats(kwargs["intake_stats"])
            return result
        shadow_real = bp._write_market_eligibility_shadow
        showcase_real = bp.write_showcase
        with ExitStack() as st:
            for key, value in {
                "STANDOUTS_PATH":board_path,"PLANS_DIR":root/"site/prophet/plans",
                "STATES_DIR":root/"site/prophet/states","INDEX_PATH":root/"site/prophet/index.json",
                "LEDGER_DIR":root/"data/prophet","LEDGER_PATH":root/"data/prophet/ledger.jsonl",
                "STOCKDATA_DIR":root/"site/stockdata","_REPO":root,
            }.items():
                st.enter_context(patch.object(bp,key,value))
            st.enter_context(patch.object(config,"ROOT",root))
            st.enter_context(patch.object(arena,"run_arena",side_effect=scoped_arena))
            st.enter_context(patch.object(bridge,"_load_price_history",return_value=prices))
            st.enter_context(patch.object(bp,"_load_price_history_for_management",return_value=prices))
            st.enter_context(patch.object(bp,"originate_plans",side_effect=observed_originator))
            st.enter_context(patch.object(bp,"_write_market_eligibility_shadow",
                side_effect=lambda index: shadow_real(index,datetime(2026,9,28,13,tzinfo=timezone.utc))))
            st.enter_context(patch.object(bp,"write_showcase",side_effect=lambda:showcase_real(out_path=root/"site/prophet/showcase.json")))
            st.enter_context(patch("engine.thetadata_store.resolve_thetadata_store",return_value=None))
            st.enter_context(patch.object(sys,"argv",["build_prophet","--date","2026-09-28"]))
            if context is None and not legacy_clock:
                bp.main()
            else:
                bp.main(new_long_restrictions=context,policy_read_at=clock or self.fixture.now)
            index = json.loads(bp.INDEX_PATH.read_text())
            plans = {x.name:x.read_bytes() for x in bp.PLANS_DIR.glob("*.json")}
            self.assertEqual(board_path.read_bytes(),board_raw)
        return {"index":index,"plans":plans,"arena_calls":calls,"root":root,
                "states":{x.name:x.read_bytes() for x in (root/"site/prophet/states").glob("*.json")},
                "ledger":(root/"data/prophet/ledger.jsonl").read_bytes()}

    def test_broad_pause_reaches_published_counts_and_named_reasons(self):
        result=self.build(self.fixture.bind());intake=result["index"]["intake"]
        for key in ("market_policy_suppressed", "market_policy_denied", "market_policy_unavailable",
                    "market_policy_dispositions", "market_policy_read", "market_policy_mode"):
            self.assertIn(key,intake)
        self.assertEqual(result["plans"],{})
        self.assertEqual(intake["admitted"],2)
        self.assertEqual(intake["originated"],0)
        self.assertEqual(intake["market_policy_suppressed"],2)
        self.assertEqual(intake["market_policy_denied"],2)
        self.assertEqual(intake["market_policy_unavailable"],0)
        self.assertEqual(intake["validation_failed"],0)
        self.assertEqual(intake["unaccounted"],0)
        self.assertTrue(intake["lossless"])
        self.assertEqual([x["ticker"] for x in intake["market_policy_dispositions"]],["AAA","BBB"])
        self.assertEqual(intake["market_policy_dispositions"][0]["rules"][0]["grant_ref"],self.fixture.rule["grant_ref"])
        self.assertTrue(intake["market_policy_read"]["not_buy_permission"])

    def test_legacy_builder_omits_new_control_fields(self):
        result=self.build();self.assertEqual(len(result["plans"]),2)
        self.assertFalse(any(k.startswith("market_policy_") for k in result["index"]["intake"]))
        self.assertNotIn("market_policy_counterfactual",result["index"])
        self.assertEqual(len(result["arena_calls"][0]),2)

    def test_ticker_scope_preserves_other_plan_bytes(self):
        control=self.build();self.fixture.rule["tickers"]=["AAA"]
        result=self.build(self.fixture.bind())
        self.assertEqual(list(result["plans"]),["BBB-BULL-20260925.json"])
        self.assertEqual(result["plans"]["BBB-BULL-20260925.json"],control["plans"]["BBB-BULL-20260925.json"])
        self.assertEqual(result["index"]["intake"]["market_policy_denied"],1)

    def test_expired_rule_preserves_all_native_plan_bytes(self):
        control=self.build();self.fixture.rule["expires_at"]="2026-09-28T12:59:59Z"
        result=self.build(self.fixture.bind())
        self.assertEqual(result["plans"],control["plans"])
        self.assertEqual(result["index"]["intake"]["market_policy_suppressed"],0)
        self.assertIn("market_policy_mode",result["index"]["intake"])

    def test_missing_expected_evidence_is_not_a_market_denial(self):
        context=self.fixture.bind([],expected={self.fixture.rule["policy_id"]:m._digest(self.fixture.rule)})
        result=self.build(context);intake=result["index"]["intake"]
        self.assertEqual(intake["market_policy_suppressed"],2)
        self.assertEqual(intake["market_policy_denied"],0)
        self.assertEqual(intake["market_policy_unavailable"],2)
        self.assertTrue(all(d["state"]=="UNAVAILABLE" for d in intake["market_policy_dispositions"]))

    def test_valid_active_rule_survives_evidence_gap_in_publication(self):
        result=self.build(self.fixture.bind(available=False));intake=result["index"]["intake"]
        self.assertEqual(intake["market_policy_denied"],2)
        self.assertEqual(intake["market_policy_unavailable"],0)
        self.assertIn("POLICY_SOURCE_UNAVAILABLE",intake["market_policy_dispositions"][0]["errors"])

    def test_expired_read_is_explicitly_unavailable(self):
        result=self.build(self.fixture.bind(),clock="2026-09-28T21:00:00Z")
        self.assertEqual(result["index"]["intake"]["market_policy_unavailable"],2)
        self.assertEqual(result["plans"],{})

    def test_controlled_build_does_not_fake_arena_live_mirror_parity(self):
        result=self.build(self.fixture.bind())
        self.assertEqual(result["arena_calls"],[None])
        self.assertEqual(result["index"]["market_policy_counterfactual"]["live_id_comparison"],"NOT_COMPARABLE_UNDER_NAMED_POLICY")
        self.assertFalse(result["index"]["market_policy_counterfactual"]["market_policy_changes_research"])
        self.assertTrue((result["root"]/"data/prophet_arena/scoreboard.json").is_file())

    def test_board_mismatch_fails_before_native_ledger_initialization(self):
        context=self.fixture.bind();self.fixture.board["buy"][0]["prophet"]["score"]=80
        with self.assertRaisesRegex(m.MarketEligibilityError,"BOARD_BINDING_MISMATCH"):
            self.build(context)
        self.assertFalse(any(self.root.rglob("ledger.jsonl")))
        self.assertFalse(any(self.root.rglob("index.json")))

    def test_wrong_internal_type_cannot_reach_builder(self):
        with self.assertRaisesRegex(m.MarketEligibilityError,"POLICY_READ_TYPE_INVALID"):
            self.build({"state":"DENY_NEW_LONG"})
        self.assertFalse(any(self.root.rglob("ledger.jsonl")))

    def test_clock_alone_cannot_silently_opt_in(self):
        with self.assertRaisesRegex(m.MarketEligibilityError,"POLICY_CLOCK_WITHOUT_READ"):
            self.build(legacy_clock=True)
        self.assertFalse(any(self.root.rglob("ledger.jsonl")))

    def test_inconsistent_count_blocks_new_published_index(self):
        with self.assertRaisesRegex(m.MarketEligibilityError,"POLICY_INTAKE_BALANCE_INVALID"):
            self.build(self.fixture.bind(),alter_stats=lambda s:s.update(market_policy_suppressed=1))
        self.assertFalse(any(self.root.rglob("index.json")))

    def test_dropped_disposition_is_not_accepted_as_lossless(self):
        with self.assertRaisesRegex(m.MarketEligibilityError,"POLICY_INTAKE_POPULATION_MISMATCH"):
            self.build(self.fixture.bind(),alter_stats=lambda s:s["market_policy_dispositions"].pop())
        self.assertFalse(any(self.root.rglob("index.json")))

    def test_altered_reason_cannot_reach_published_index(self):
        def change(s):s["market_policy_dispositions"][0]["rules"][0]["grant_ref"]="invented"
        with self.assertRaisesRegex(m.MarketEligibilityError,"POLICY_INTAKE_DISPOSITION_MISMATCH"):
            self.build(self.fixture.bind(),alter_stats=change)
        self.assertFalse(any(self.root.rglob("index.json")))

    def test_original_acceptance_alarm_accepts_honest_full_pause(self):
        from scripts.prophet_board_acceptance import check
        from datetime import datetime,timezone
        result=self.build(self.fixture.bind())
        self.assertEqual(check(result["root"],"fixture-run",datetime(2026,9,28,13,tzinfo=timezone.utc)),[])

    def test_projection_is_an_independent_copy(self):
        context=self.fixture.bind();_,stats=self.fixture.invoke(context)
        projected=m.project_new_long_intake(stats,context,read_at=self.fixture.now)
        stats["market_policy_dispositions"][0]["rules"][0]["grant_ref"]="changed after projection"
        self.assertEqual(projected["market_policy_dispositions"][0]["rules"][0]["grant_ref"],self.fixture.rule["grant_ref"])


    def test_existing_positions_remain_under_native_management(self):
        seed=self.build()
        control=self.build(seed_root=seed["root"])
        restricted=self.build(self.fixture.bind(),seed_root=seed["root"])
        self.assertEqual(restricted["plans"],control["plans"])
        self.assertEqual(restricted["states"],control["states"])
        self.assertEqual(restricted["ledger"],control["ledger"])
        self.assertEqual(len(restricted["plans"]),2)
        self.assertEqual(restricted["index"]["intake"]["duplicate_id_blocked"],2)
        self.assertEqual(restricted["index"]["intake"]["market_policy_suppressed"],0)
        self.assertEqual(restricted["index"]["intake"]["market_policy_dispositions"],[])
