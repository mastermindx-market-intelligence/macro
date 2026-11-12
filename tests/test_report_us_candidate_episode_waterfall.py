"""Entry Timing W1 waterfall report: explicit denominators, typed refusal classes,
the turn_watch source-document clock, and the as-known identity replay — on a
synthetic generation, outcome-blind."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

import pandas as pd
import pytest

from engine.us_candidate_episode_intake import canonical_json
from scripts import report_us_candidate_episode_waterfall as rep

GEN = "peg:" + "ab" * 32
TW_SCHEMA = "prophet.candidate_episode_input.turn_watch/v1"


def _turn_watch_document(session: str, marker: str) -> tuple[dict, str]:
    """A digest-verified turn_watch source document; returns (document, receipt)."""
    body = {"schema": TW_SCHEMA, "data_session": session, "rows": [], "marker": marker}
    digest = sha256(canonical_json(body).encode("utf-8")).hexdigest()
    return {**body, "content_sha256": digest}, f"sha256:{digest}"


def _write_reference(root: Path, rows: list[dict]) -> None:
    path = root / "reference" / "vendor_aliases.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=[
        "vendor", "vendor_symbol", "security_id", "valid_from", "valid_to",
        "ingested_at", "known_at", "evidence_sha256", "binding_sha256", "alias_kind",
    ]).to_parquet(path, index=False)
    master = root / "reference" / "security_master.parquet"
    pd.DataFrame([{
        "security_id": r["security_id"], "issuer_id": "ISS:" + r["security_id"][4:],
        "issuer_state": "RESOLVED", "issuer_cik": None, "issuer_evidence_snapshot": None,
        "listing_key": r["security_id"][4:], "country": "US", "mic": r["security_id"][7:11],
        "inception_code": r["vendor_symbol"], "effective_at": "2026-01-01T00:00:00Z",
        "ingested_at": "2026-01-01T00:00:00Z", "security_state": None, "superseded_by": None,
    } for r in rows]).to_parquet(master, index=False)


def _alias(symbol: str, security: str, ingested: str | None, *, valid_to: str | None = None) -> dict:
    return {"vendor": "membership", "vendor_symbol": symbol, "security_id": security,
            "valid_from": None,
            "valid_to": valid_to,  # the alias reader takes an ISO date
            "ingested_at": datetime.fromisoformat(ingested).replace(tzinfo=timezone.utc) if ingested else pd.NaT,
            "known_at": None, "evidence_sha256": "sha256:" + "0" * 64,
            "binding_sha256": "sha256:" + "1" * 64, "alias_kind": None}


def _world(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    gen = data / "us_prophet_rank" / "episodes" / "generations" / GEN
    (gen / "events").mkdir(parents=True)
    (gen / "suppressions").mkdir(parents=True)
    (data / "us_prophet_rank" / "episodes" / "HEAD.json").write_text(json.dumps({"generation_id": GEN}))
    doc21, receipt21 = _turn_watch_document("2026-10-21", "current")
    inputs = data / rep.TURN_WATCH_INPUTS
    inputs.mkdir(parents=True)
    (inputs / "2026-10-21.json").write_text(json.dumps(doc21))
    events = [
        {"event_type": "OPENED", "source_system": "candidate", "occurred_at": "2026-10-20T20:00:00Z",
         "payload": {"opened_session": "2026-10-20"}},
        {"event_type": "OBSERVED", "source_system": "candidate", "occurred_at": "2026-10-20T20:00:00Z",
         "payload": {}},
        # turn_watch: the trigger fired on 10-15 but the row was READ from the 10-21 document
        {"event_type": "OBSERVED", "source_system": "turn_watch", "occurred_at": "2026-10-15T20:00:00Z",
         "source_receipt": receipt21, "payload": {}},
        # turn_watch row whose document is gone (receipt unknown): never binned by its trigger clock
        {"event_type": "OBSERVED", "source_system": "turn_watch", "occurred_at": "2026-05-07T20:00:00Z",
         "source_receipt": "sha256:" + "f" * 64, "payload": {"opened_session": "2026-05-07"}},
    ]
    (gen / "events" / "2026-10.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n")
    supp = [
        # no reference knows ZZZZ at all
        {"reason": "IDENTITY_UNRESOLVED", "source_system": "candidate", "observation_session": "2026-10-20",
         "ticker_at_observation": "ZZZZ"},
        # WIDE was ingested on 10-21, after the 10-20 session: lawful as-known refusal
        {"reason": "IDENTITY_UNRESOLVED", "source_system": "candidate", "observation_session": "2026-10-20",
         "ticker_at_observation": "WIDE"},
        # KNOWN was ingested 10-01, before the 10-20 session, yet refused: the only defect-candidate class
        {"reason": "IDENTITY_UNRESOLVED", "source_system": "candidate", "observation_session": "2026-10-20",
         "ticker_at_observation": "KNOWN"},
        # NOSTAMP resolves today but its alias row carries no ingest stamp: counted conservatively
        {"reason": "IDENTITY_UNRESOLVED", "source_system": "candidate", "observation_session": "2026-10-20",
         "ticker_at_observation": "NOSTAMP"},
        # GONE's alias expired on 09-01: it does not cover the 10-20 session today either
        {"reason": "IDENTITY_UNRESOLVED", "source_system": "candidate", "observation_session": "2026-10-20",
         "ticker_at_observation": "GONE"},
        {"reason": "MISSING_STRUCTURAL_ANCHOR", "source_system": "candidate", "observation_session": "2026-10-20",
         "ticker_at_observation": "ANCH"},
        # turn_watch refusal: the ledger stamped the trigger date, the document says 10-21
        {"reason": "ACTIVE_EPISODE_DIFFERENT_ANCHOR", "source_system": "turn_watch",
         "observation_session": "2026-10-15", "source_receipt": receipt21, "ticker_at_observation": "KNOWN"},
        # turn_watch refusal whose document is gone
        {"reason": "IDENTITY_UNRESOLVED", "source_system": "turn_watch", "observation_session": "2026-05-07",
         "source_receipt": "sha256:" + "f" * 64, "ticker_at_observation": "LOST"},
    ]
    (gen / "suppressions" / "2026-10.jsonl").write_text("\n".join(json.dumps(s) for s in supp) + "\n")
    _write_reference(data, [
        _alias("WIDE", "SEC:US-XNAS-WIDE", "2026-10-21T00:00:00"),
        _alias("KNOWN", "SEC:US-XNYS-KNOWN", "2026-10-01T00:00:00"),
        _alias("NOSTAMP", "SEC:US-XNYS-NOSTAMP", None),
        _alias("GONE", "SEC:US-XNYS-GONE", "2026-08-01T00:00:00", valid_to="2026-09-01"),
    ])
    return data


def test_waterfall_has_explicit_denominators_per_session_and_typed_classes(tmp_path):
    doc = rep.build(_world(tmp_path), replay=False)
    assert doc["schema"] == rep.SCHEMA and doc["outcome_blind"] is True
    assert doc["generation_id"] == GEN
    assert doc["turn_watch_receipts"] == {"documents": 1, "receipts": 1, "git_history": None}
    s20, s21 = doc["waterfall"]["sessions"]
    assert s20["session"] == "2026-10-20"
    assert (s20["inputs"], s20["mapped"], s20["refused"]) == (8, 2, 6)
    assert s20["mapped_by_source"] == {"candidate": 2}
    assert s20["refused_by_class"] == {"IDENTITY_UNRESOLVED": 5, "ISSUER_UNRESOLVED": 0,
                                       "MISSING_STRUCTURAL_ANCHOR": 1, "ACTIVE_EPISODE_DIFFERENT_ANCHOR": 0}
    assert s20["distinct_refused_tickers"] == 6
    assert (s21["inputs"], s21["mapped"], s21["refused"]) == (2, 1, 1)
    assert s21["mapped_by_source"] == {"turn_watch": 1}
    assert s21["refused_by_source"] == {"turn_watch": 1}
    totals = doc["waterfall"]["totals"]
    assert totals == {"sessions": 2, "inputs": 10, "mapped": 3, "refused": 7,
                      "refused_by_class": {"IDENTITY_UNRESOLVED": 5, "ISSUER_UNRESOLVED": 0,
                                           "MISSING_STRUCTURAL_ANCHOR": 1, "ACTIVE_EPISODE_DIFFERENT_ANCHOR": 1},
                      "unsessioned_events": 0, "unsessioned_suppressions": 0,
                      "unrecovered_turn_watch": {"events": 1, "suppressions": 1}}
    assert "identity_replay" not in doc


def test_turn_watch_rows_sit_on_the_source_document_clock_never_the_trigger_clock(tmp_path):
    doc = rep.build(_world(tmp_path), replay=False)
    sessions = [s["session"] for s in doc["waterfall"]["sessions"]]
    assert "2026-10-15" not in sessions and "2026-05-07" not in sessions  # no trigger-date sessions
    clock = doc["waterfall"]["clock"]
    assert clock["turn_watch_session_basis"] == "source document data_session via source_receipt"
    assert clock["turn_watch_events_recovered"] == 1
    assert clock["turn_watch_events_trigger_before_session"] == 1
    assert clock["turn_watch_suppressions_recovered"] == 1
    assert clock["turn_watch_suppressions_ledger_session_differs"] == 1


def test_git_history_recovers_a_receipt_whose_document_was_rewritten(tmp_path):
    data = _world(tmp_path)
    repo = tmp_path  # data_root.parent is the repository, as in the real checkout
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@t", "HOME": str(tmp_path)}
    git = lambda *a: subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, env=env)  # noqa: E731
    git("init", "-q")
    inputs = data / rep.TURN_WATCH_INPUTS
    old_doc, old_receipt = _turn_watch_document("2026-10-14", "old")
    (inputs / "2026-10-14.json").write_text(json.dumps(old_doc))
    git("add", "-A")
    git("commit", "-q", "-m", "old 10-14 document")
    new_doc, _new_receipt = _turn_watch_document("2026-10-14", "rewritten")  # nightly rewrote it in place
    (inputs / "2026-10-14.json").write_text(json.dumps(new_doc))
    git("add", "-A")
    git("commit", "-q", "-m", "rewritten 10-14 document")
    gen = data / "us_prophet_rank" / "episodes" / "generations" / GEN
    with (gen / "events" / "2026-10.jsonl").open("a") as handle:
        handle.write(json.dumps({"event_type": "OBSERVED", "source_system": "turn_watch",
                                 "occurred_at": "2026-10-02T20:00:00Z", "source_receipt": old_receipt,
                                 "payload": {}}) + "\n")
    tracked_only = rep.build(data, replay=False)
    assert tracked_only["waterfall"]["totals"]["unrecovered_turn_watch"]["events"] == 2
    assert "2026-10-14" not in [s["session"] for s in tracked_only["waterfall"]["sessions"]]
    with_history = rep.build(data, replay=False, git_ref="HEAD")
    assert with_history["turn_watch_receipts"]["git_history"] == {"ref": "HEAD", "commits": 2, "blobs": 3}
    assert with_history["turn_watch_receipts"]["receipts"] == 3 and with_history["turn_watch_receipts"]["documents"] == 3
    assert with_history["waterfall"]["totals"]["unrecovered_turn_watch"]["events"] == 1
    s14 = next(s for s in with_history["waterfall"]["sessions"] if s["session"] == "2026-10-14")
    assert (s14["inputs"], s14["mapped"], s14["mapped_by_source"]) == (1, 1, {"turn_watch": 1})


def test_a_document_whose_digest_does_not_match_is_never_used(tmp_path):
    data = _world(tmp_path)
    forged, receipt = _turn_watch_document("2026-10-22", "forged")
    forged["data_session"] = "2026-10-23"  # content no longer matches the stored digest
    (data / rep.TURN_WATCH_INPUTS / "2026-10-22.json").write_text(json.dumps(forged))
    receipts = rep.turn_watch_receipt_sessions(data)
    assert receipt not in receipts["sessions"] and receipts["documents"] == 1


def test_identity_replay_splits_refusals_by_the_as_known_reference_on_the_same_clock(tmp_path):
    doc = rep.build(_world(tmp_path), replay=True)
    replay = doc["identity_replay"]
    assert replay["vendor"] == "membership"
    assert replay["identity_unresolved_rows"] == 5 and replay["distinct_tickers"] == 5
    assert replay["identity_unresolved_rows_unrecovered_session"] == 1  # LOST: no document, not replayed
    assert replay["rows_by_class"] == {"no_current_reference": 2, "reference_widened_after_session": 1,
                                       "resolvable_at_session": 2}
    assert replay["by_session"] == {"2026-10-20": {"no_current_reference": 2,
                                                   "reference_widened_after_session": 1,
                                                   "resolvable_at_session": 2}}
    examples = {e["ticker"]: e for e in replay["resolvable_at_session_examples"]}
    assert set(examples) == {"KNOWN", "NOSTAMP"}
    assert examples["KNOWN"]["security_id"] == "SEC:US-XNYS-KNOWN"
    assert examples["KNOWN"]["alias_first_ingested"] == "2026-10-01"
    assert examples["NOSTAMP"]["alias_first_ingested"] == "None"  # conservative: no stamp, no excuse
    assert replay["reference"] and replay["reference"][0]["sha256"].startswith("sha256:")


def test_cli_renders_a_run_document_and_writes_nothing(tmp_path, capsys):
    data = _world(tmp_path)
    before = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())
    assert rep.main(["--root", str(data), "--json"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["authority"] == "measurement only / none"
    assert rep.main(["--root", str(data), "--no-replay"]) == 0
    text = capsys.readouterr().out
    assert "2026-10-20" in text and "TOTAL" in text and "identity replay" not in text
    assert "unrecovered (excluded above): events=1 suppressions=1" in text
    after = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())
    assert before == after


def test_no_outcome_surface_is_read():
    source = Path(rep.__file__).read_text("utf-8")
    code = source.split('"""', 2)[2].lower()  # strip the module docstring; the code is what reads
    for needle in ("grades", "paired", "w3/", "price", "mae", "outcome_"):
        assert needle not in code.replace("outcome_blind", ""), needle
