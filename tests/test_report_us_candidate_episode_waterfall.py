"""Entry Timing W1 waterfall report: explicit denominators, typed refusal classes,
and the as-known identity replay — on a synthetic generation, outcome-blind."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from scripts import report_us_candidate_episode_waterfall as rep

GEN = "peg:" + "ab" * 32


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


def _alias(symbol: str, security: str, ingested: str) -> dict:
    return {"vendor": "membership", "vendor_symbol": symbol, "security_id": security,
            "valid_from": None, "valid_to": None,
            "ingested_at": datetime.fromisoformat(ingested).replace(tzinfo=timezone.utc),
            "known_at": None, "evidence_sha256": "sha256:" + "0" * 64,
            "binding_sha256": "sha256:" + "1" * 64, "alias_kind": None}


def _world(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    gen = data / "us_prophet_rank" / "episodes" / "generations" / GEN
    (gen / "events").mkdir(parents=True)
    (gen / "suppressions").mkdir(parents=True)
    (data / "us_prophet_rank" / "episodes" / "HEAD.json").write_text(json.dumps({"generation_id": GEN}))
    events = [
        {"event_type": "OPENED", "source_system": "candidate", "occurred_at": "2026-10-20T20:00:00Z",
         "payload": {"opened_session": "2026-10-20"}},
        {"event_type": "OBSERVED", "source_system": "candidate", "occurred_at": "2026-10-20T20:00:00Z",
         "payload": {}},
        {"event_type": "OBSERVED", "source_system": "turn_watch", "occurred_at": "2026-10-21T14:00:00Z",
         "payload": {}},
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
        {"reason": "MISSING_STRUCTURAL_ANCHOR", "source_system": "candidate", "observation_session": "2026-10-20",
         "ticker_at_observation": "ANCH"},
        {"reason": "ACTIVE_EPISODE_DIFFERENT_ANCHOR", "source_system": "turn_watch",
         "observation_session": "2026-10-21", "ticker_at_observation": "KNOWN"},
    ]
    (gen / "suppressions" / "2026-10.jsonl").write_text("\n".join(json.dumps(s) for s in supp) + "\n")
    _write_reference(data, [
        _alias("WIDE", "SEC:US-XNAS-WIDE", "2026-10-21T00:00:00"),
        _alias("KNOWN", "SEC:US-XNYS-KNOWN", "2026-10-01T00:00:00"),
    ])
    return data


def test_waterfall_has_explicit_denominators_per_session_and_typed_classes(tmp_path):
    doc = rep.build(_world(tmp_path), replay=False)
    assert doc["schema"] == rep.SCHEMA and doc["outcome_blind"] is True
    assert doc["generation_id"] == GEN
    s20, s21 = doc["waterfall"]["sessions"]
    assert s20["session"] == "2026-10-20"
    assert (s20["inputs"], s20["mapped"], s20["refused"]) == (6, 2, 4)
    assert s20["mapped_by_source"] == {"candidate": 2}
    assert s20["refused_by_class"] == {"IDENTITY_UNRESOLVED": 3, "ISSUER_UNRESOLVED": 0,
                                       "MISSING_STRUCTURAL_ANCHOR": 1, "ACTIVE_EPISODE_DIFFERENT_ANCHOR": 0}
    assert s20["distinct_refused_tickers"] == 4
    assert (s21["inputs"], s21["mapped"], s21["refused"]) == (2, 1, 1)
    assert s21["refused_by_source"] == {"turn_watch": 1}
    totals = doc["waterfall"]["totals"]
    assert totals == {"sessions": 2, "inputs": 8, "mapped": 3, "refused": 5,
                      "refused_by_class": {"IDENTITY_UNRESOLVED": 3, "ISSUER_UNRESOLVED": 0,
                                           "MISSING_STRUCTURAL_ANCHOR": 1, "ACTIVE_EPISODE_DIFFERENT_ANCHOR": 1},
                      "unsessioned_events": 0}
    assert "identity_replay" not in doc


def test_identity_replay_splits_refusals_by_the_as_known_reference(tmp_path):
    doc = rep.build(_world(tmp_path), replay=True)
    replay = doc["identity_replay"]
    assert replay["vendor"] == "membership"
    assert replay["identity_unresolved_rows"] == 3 and replay["distinct_tickers"] == 3
    assert replay["rows_by_class"] == {"no_current_reference": 1, "reference_widened_after_session": 1,
                                       "resolvable_at_session": 1}
    assert replay["by_session"] == {"2026-10-20": {"no_current_reference": 1,
                                                   "reference_widened_after_session": 1,
                                                   "resolvable_at_session": 1}}
    [example] = replay["resolvable_at_session_examples"]
    assert example["ticker"] == "KNOWN" and example["security_id"] == "SEC:US-XNYS-KNOWN"
    assert example["alias_first_ingested"] == "2026-10-01"
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
    after = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())
    assert before == after


def test_no_outcome_surface_is_read():
    source = Path(rep.__file__).read_text("utf-8")
    code = source.split('"""', 2)[2].lower()  # strip the module docstring; the code is what reads
    for needle in ("grades", "paired", "w3/", "price", "mae", "outcome_"):
        assert needle not in code.replace("outcome_blind", ""), needle
