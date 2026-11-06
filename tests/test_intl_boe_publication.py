"""BoE native publication: capture, reader and field admission.

Every provider response here is a synthetic fixture built in this file. No
live Bank of England query is made, and no acquisition is attempted. The
composition owner executes the retained actual response.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
from pathlib import Path

import pandas as pd
import pytest

from lib import intl_boe_publication as boe
from lib.intl_boe_publication import (
    COLUMN,
    FIELD,
    POLICY_REF,
    SOURCE_URL,
    admit_boe_policy_field,
    capture_boe_commit,
    read_boe_materialization,
)

GOV = "http://www.gesmes.org/xml/2002-08-01"
AGG = ("https://web.prod.iadb.ext.az.cloud.bankofengland.co.uk"
       "/website/agg_series")

#: A current native response: the tail is fresh against the evaluation clock.
OBSERVED = [
    ("2026-08-28", 3.75, "observed", "2026-09-01 09:30:00"),
    ("2026-09-30", 3.75, "observed", "2026-10-01 09:30:00"),
    ("2026-11-02", 3.75, "observed", "2026-11-03 09:30:00"),
]
#: The same shape with a tail that is already stale at the evaluation clock.
STALE = [
    ("2026-08-28", 3.75, "observed", "2026-09-01 09:30:00"),
    ("2026-09-30", 3.75, "observed", "2026-10-01 09:30:00"),
    ("2026-10-20", 3.75, "observed", "2026-10-21 09:30:00"),
]
#: A native response whose tail the provider withheld.
WITHHELD_TAIL = [
    ("2026-08-28", 3.75, "observed", "2026-09-01 09:30:00"),
    ("2026-09-30", 3.75, "observed", "2026-10-01 09:30:00"),
    ("2026-11-02", None, "withheld", "2026-11-03 09:30:00"),
]

CLOCKS = {
    "requested_at": "2026-11-04T08:57:22.722700+00:00",
    "response_received_at": "2026-11-04T08:57:23.674719+00:00",
    "input_verified_at": "2026-11-04T08:57:24.311000+00:00",
    "committed_at": "2026-11-04T08:57:25.482000+00:00",
}
EVALUATED_AT = "2026-11-04T12:00:00+00:00"


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


def _response(rows, *, scode="IUDBEDR", desc="Official Bank Rate", freq="D"):
    """Build one minimal IUDBEDR provider response from supplied rows."""
    parts = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        '<Envelope xmlns="%s">' % GOV,
        '<Cube xmlns="%s" SCODE="%s" DESC="%s" COUNTRY="">' % (AGG, scode, desc),
        '<Cube FREQ_NAME="Daily" FREQ_CODE="%s" FREQ_ORD="1"/>' % freq,
        "<SERIES_COM>Fixture series note.</SERIES_COM>",
        '<Cube CAT_NAME="INSTRUMENTS" CAT_VAL="RBASER" VAL_DESC="Official Bank Rate" CAT_ORD="7"/>',
    ]
    for date, value, status, updated in rows:
        parts.append(
            '<Cube TIME="%s" OBS_VALUE="%s" OBS_CONF="%s" LAST_UPDATED="%s"></Cube>'
            % (date, "" if value is None else value,
               "N" if status == "observed" else "C", updated)
        )
    parts.append("</Cube></Envelope>")
    return "".join(parts).encode()


def _store(root, rows, *, values=None, column=COLUMN):
    """Write the canonical artifact a store.upsert would already have written."""
    frame = pd.DataFrame(
        {column: [value for _, value, _, _ in rows] if values is None else values},
        index=pd.DatetimeIndex([date for date, _, _, _ in rows]),
    )
    path = Path(root) / "intl_macro" / (column + ".parquet")
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path)
    return frame


def _capture(root, rows, *, values=None, response=None, **clocks):
    """Capture one committed response against the stored artifact."""
    frame = _store(root, rows, values=values)
    raw = response if response is not None else _response(rows)
    instants = dict(CLOCKS)
    instants.update(clocks)
    return capture_boe_commit(root, frame, raw, SOURCE_URL, **instants)


def _decision(receipt_sha, **overrides):
    """Return this owner's own decision, bound to one field and receipt."""
    decision = {
        "owner_ref": "scripts/build_intl.py",
        "policy_ref": POLICY_REF,
        "decision_ref": "fixture:boe-publication-1",
        "metadata": "allowed",
        "value_permission": "allowed",
        "binding": {"field": FIELD, "receipt_sha256": receipt_sha},
    }
    decision.update(overrides)
    return decision


def _admitted(root, **overrides):
    """Read one capture and admit its current field."""
    materialized = read_boe_materialization(root)
    decision = _decision(materialized.get("receipt_sha256"), **overrides)
    return admit_boe_policy_field(
        materialized, EVALUATED_AT, decision, observation_date=overrides.get("observation_date")
    )


def _blank(result):
    """True when a result carries no dynamic metadata and no number."""
    return (result["value"] is None and result["unit"] is None
            and result["instrument"] is None and result["period"] is None
            and result["observation_at"] is None and result["calculation_at"] is None
            and result["source_reference"] is None and result["evidence_key"] is None)


def _rewrite_receipt(root, mutate):
    """Rewrite the receipt and its sidecar together, keeping them consistent."""
    directory = Path(root) / boe.DIRECTORY
    pointer = directory / "current.json"
    receipt = json.loads(pointer.read_bytes())
    mutate(receipt)
    payload = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    for path in directory.glob("*.json"):
        if path.name != "current.json":
            path.unlink()
    (directory / (hashlib.sha256(payload).hexdigest() + ".json")).write_bytes(payload)
    pointer.write_bytes(payload)
    return payload


def _write_raw_receipt(root, payload):
    """Replace the receipt with raw bytes under their own digest."""
    directory = Path(root) / boe.DIRECTORY
    for path in directory.glob("*.json"):
        if path.name != "current.json":
            path.unlink()
    (directory / (hashlib.sha256(payload).hexdigest() + ".json")).write_bytes(payload)
    (directory / "current.json").write_bytes(payload)


def _forge_capture(root, rows):
    """Rewrite a capture so its receipt, response and store all agree."""
    raw = _response(rows)
    frame = _store(root, rows)
    artifact = (root / "intl_macro" / (COLUMN + ".parquet")).read_bytes()
    directory = root / boe.DIRECTORY
    for path in directory.glob("*.xml"):
        path.unlink()
    (directory / (hashlib.sha256(raw).hexdigest() + ".xml")).write_bytes(raw)
    receipt = json.loads((directory / "current.json").read_bytes())
    receipt["source_sha256"] = hashlib.sha256(raw).hexdigest()
    receipt["artifact_sha256"] = hashlib.sha256(artifact).hexdigest()
    receipt["rows"] = [{"date": date, "value": value, "status": status,
                         "source_updated_raw": updated}
                        for date, value, status, updated in rows]
    receipt["observation_label"] = rows[-1][0]
    receipt["value"] = rows[-1][1]
    receipt["value_status"] = rows[-1][2]
    receipt["response_rows"] = len(rows)
    receipt["observed_rows"] = sum(1 for row in rows if row[2] == "observed")
    receipt["withheld_rows"] = sum(1 for row in rows if row[2] != "observed")
    _write_raw_receipt(root, json.dumps(receipt, sort_keys=True,
                                         separators=(",", ":")).encode())
    return frame


@pytest.fixture
def captured(tmp_path):
    """One captured current response with its stored artifact."""
    root = tmp_path / "data"
    _capture(root, OBSERVED)
    return root


# --------------------------------------------------------------------------
# Capture
# --------------------------------------------------------------------------


def test_capture_binds_the_actual_artifact_and_the_original_response(tmp_path):
    root = tmp_path / "data"
    receipt = _capture(root, OBSERVED)
    artifact = (root / "intl_macro" / (COLUMN + ".parquet")).read_bytes()
    assert receipt["artifact_sha256"] == hashlib.sha256(artifact).hexdigest()
    assert receipt["source_sha256"] == hashlib.sha256(_response(OBSERVED)).hexdigest()
    assert receipt["schema"] == boe.SCHEMA and receipt["column"] == COLUMN
    assert receipt["provider"] == "boe" and receipt["series_id"] == "IUDBEDR"
    assert receipt["instrument_id"] == "bank_rate" and receipt["unit"] == "percent"
    assert receipt["market_id"] == "GB" and receipt["frequency"] == "daily"
    assert receipt["source_url"] == SOURCE_URL
    assert receipt["provider_published_at"] is None
    assert receipt["revision_vintage"] is None
    assert receipt["response_rows"] == 3 and receipt["observed_rows"] == 3
    assert receipt["withheld_rows"] == 0
    assert receipt["observation_label"] == "2026-11-02"
    assert receipt["value"] == 3.75


def test_capture_keeps_the_raw_provider_clock_without_a_time_zone(tmp_path):
    root = tmp_path / "data"
    receipt = _capture(root, OBSERVED)
    clocks = {row["date"]: row["source_updated_raw"] for row in receipt["rows"]}
    assert clocks["2026-11-02"] == "2026-11-03 09:30:00"
    assert clocks["2026-08-28"] == "2026-09-01 09:30:00"
    for raw in clocks.values():
        assert "T" not in raw and "+" not in raw and "Z" not in raw


def test_capture_does_not_modify_the_canonical_store(tmp_path):
    root = tmp_path / "data"
    _capture(root, OBSERVED)
    artifact = root / "intl_macro" / (COLUMN + ".parquet")
    before = artifact.read_bytes()
    _capture(root, OBSERVED)
    assert artifact.read_bytes() == before


def test_capture_refuses_a_foreign_source_url(tmp_path):
    root = tmp_path / "data"
    frame = _store(root, OBSERVED)
    with pytest.raises(ValueError):
        capture_boe_commit(root, frame, _response(OBSERVED),
                           "https://example.invalid/IUDBEDR.xml", **CLOCKS)
    assert not (root / boe.DIRECTORY).exists()


def test_capture_refuses_a_foreign_series(tmp_path):
    root = tmp_path / "data"
    frame = _store(root, OBSERVED)
    raw = _response(OBSERVED, scode="IUDERB1", desc="Official Bank Rate")
    with pytest.raises(ValueError):
        capture_boe_commit(root, frame, raw, SOURCE_URL, **CLOCKS)


def test_capture_refuses_a_non_daily_series(tmp_path):
    root = tmp_path / "data"
    frame = _store(root, OBSERVED)
    raw = _response(OBSERVED, freq="M")
    with pytest.raises(ValueError):
        capture_boe_commit(root, frame, raw, SOURCE_URL, **CLOCKS)


def test_capture_refuses_a_response_that_does_not_match_the_store(tmp_path):
    root = tmp_path / "data"
    frame = _store(root, OBSERVED, values=[3.75, 3.75, 4.0])
    with pytest.raises(ValueError):
        capture_boe_commit(root, frame, _response(OBSERVED), SOURCE_URL, **CLOCKS)


def test_capture_refuses_a_store_that_does_not_cover_the_response(tmp_path):
    root = tmp_path / "data"
    frame = _store(root, OBSERVED[:2])
    with pytest.raises(ValueError):
        capture_boe_commit(root, frame, _response(OBSERVED), SOURCE_URL, **CLOCKS)


def test_capture_refuses_a_store_that_disagrees_with_the_response(tmp_path):
    root = tmp_path / "data"
    # The frame the store returned agrees with the response; the artifact
    # actually on disk does not.
    frame = _store(root, OBSERVED)
    _store(root, OBSERVED, values=[3.75, 3.75, 4.0])
    with pytest.raises(ValueError):
        capture_boe_commit(root, frame, _response(OBSERVED), SOURCE_URL, **CLOCKS)


def test_capture_refuses_a_returned_frame_that_disagrees_with_the_response(tmp_path):
    root = tmp_path / "data"
    # The artifact on disk agrees with the response; the frame the store
    # returned does not.
    _store(root, OBSERVED)
    returned = pd.DataFrame(
        {COLUMN: [3.75, 3.75, 4.0]},
        index=pd.DatetimeIndex([date for date, _, _, _ in OBSERVED]))
    with pytest.raises(ValueError):
        capture_boe_commit(root, returned, _response(OBSERVED), SOURCE_URL, **CLOCKS)


def test_capture_refuses_an_out_of_order_chronology(tmp_path):
    root = tmp_path / "data"
    frame = _store(root, OBSERVED)
    clocks = dict(CLOCKS)
    clocks["input_verified_at"] = "2026-11-04T08:00:00.000000+00:00"
    with pytest.raises(ValueError):
        capture_boe_commit(root, frame, _response(OBSERVED), SOURCE_URL, **clocks)


def test_capture_refuses_a_non_utc_clock(tmp_path):
    root = tmp_path / "data"
    frame = _store(root, OBSERVED)
    clocks = dict(CLOCKS)
    clocks["committed_at"] = "2026-11-04T09:57:25.482000+01:00"
    with pytest.raises(ValueError):
        capture_boe_commit(root, frame, _response(OBSERVED), SOURCE_URL, **clocks)


def test_capture_refuses_a_naive_clock(tmp_path):
    root = tmp_path / "data"
    frame = _store(root, OBSERVED)
    clocks = dict(CLOCKS)
    clocks["committed_at"] = "2026-11-04T08:57:25.482000"
    with pytest.raises(ValueError):
        capture_boe_commit(root, frame, _response(OBSERVED), SOURCE_URL, **clocks)


def test_capture_refuses_a_missing_canonical_artifact(tmp_path):
    root = tmp_path / "data"
    frame = _store(root, OBSERVED)
    (root / "intl_macro" / (COLUMN + ".parquet")).unlink()
    with pytest.raises(ValueError):
        capture_boe_commit(root, frame, _response(OBSERVED), SOURCE_URL, **CLOCKS)


def test_capture_never_acquires_anything():
    tree = ast.parse(inspect.getsource(boe))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imported.update("%s.%s" % (module, alias.name) if module else alias.name
                            for alias in node.names)
    forbidden = ("socket", "http.", "urllib.request", "requests", "httpx",
                 "aiohttp", "urllib3", "ftplib", "smtplib", "telnetlib", "xmlrpc")
    assert not [name for name in imported if name.startswith(forbidden)]
    assert "urlopen" not in inspect.getsource(boe)


# --------------------------------------------------------------------------
# Reader
# --------------------------------------------------------------------------


def test_reader_distinguishes_a_missing_capture_from_a_broken_one(tmp_path):
    root = tmp_path / "data"
    missing = read_boe_materialization(root)
    assert missing == {"status": "missing", "series": None, "receipt": None,
                       "receipt_sha256": None}
    _capture(root, OBSERVED)
    assert read_boe_materialization(root)["status"] == "ready"
    (root / boe.DIRECTORY / "current.json").unlink()
    assert read_boe_materialization(root) == {"status": "missing", "series": None,
                                              "receipt": None, "receipt_sha256": None}
    _capture(root, OBSERVED)
    (root / "intl_macro" / (COLUMN + ".parquet")).unlink()
    failed = read_boe_materialization(root)
    assert failed["status"] == "failed" and failed["series"] is None
    assert failed["receipt"] is None


def test_reader_returns_the_series_receipt_and_digest(captured):
    materialized = read_boe_materialization(captured)
    assert materialized["status"] == "ready"
    assert isinstance(materialized["series"], pd.Series)
    assert materialized["series"].name == COLUMN
    assert materialized["series"].index[-1].date().isoformat() == "2026-11-02"
    assert materialized["receipt"]["observation_label"] == "2026-11-02"
    assert materialized["receipt_sha256"] == hashlib.sha256(
        (captured / boe.DIRECTORY / "current.json").read_bytes()).hexdigest()


def test_reader_denies_a_mutated_store(tmp_path):
    root = tmp_path / "data"
    _capture(root, OBSERVED)
    _store(root, OBSERVED, values=[3.75, 3.75, 4.0])
    assert read_boe_materialization(root)["status"] == "failed"


def test_reader_denies_a_mutated_receipt_sidecar(tmp_path):
    root = tmp_path / "data"
    _capture(root, OBSERVED)
    sidecar = next(path for path in (root / boe.DIRECTORY).glob("*.json")
                   if path.name != "current.json")
    sidecar.write_bytes(sidecar.read_bytes().replace(b"3.75", b"4.00"))
    assert read_boe_materialization(root)["status"] == "failed"


def test_reader_denies_a_mutated_selector(tmp_path):
    root = tmp_path / "data"
    _capture(root, OBSERVED)
    (root / boe.DIRECTORY / "current.json").write_bytes(b"{}")
    assert read_boe_materialization(root)["status"] == "failed"


def test_reader_denies_a_missing_sidecar(tmp_path):
    root = tmp_path / "data"
    _capture(root, OBSERVED)
    for path in (root / boe.DIRECTORY).glob("*.json"):
        if path.name != "current.json":
            path.unlink()
    assert read_boe_materialization(root)["status"] == "failed"


def test_reader_denies_a_consistent_receipt_url_mutation(tmp_path):
    root = tmp_path / "data"
    _capture(root, OBSERVED)
    _rewrite_receipt(root, lambda receipt: receipt.__setitem__(
        "source_url", SOURCE_URL + "&Extra=1"))
    assert read_boe_materialization(root)["status"] == "failed"


def test_reader_denies_a_receipt_whose_clock_breaks_the_chronology(tmp_path):
    # The selector/sidecar equality binds the clock bytes; this proves the
    # receipt's own ordering is refused as well.
    root = tmp_path / "data"
    _capture(root, OBSERVED)
    _rewrite_receipt(root, lambda receipt: receipt.__setitem__(
        "committed_at", "2026-11-04T08:00:00.000000+00:00"))
    assert read_boe_materialization(root)["status"] == "failed"


def test_reader_denies_a_store_that_disagrees_with_the_source_rows(tmp_path):
    # The artifact hash is refreshed to match the mutated store, so only the
    # row-by-row agreement between the source and the actual store can deny.
    root = tmp_path / "data"
    _capture(root, OBSERVED)
    _store(root, OBSERVED, values=[3.75, 3.75, 4.0])
    artifact = (root / "intl_macro" / (COLUMN + ".parquet")).read_bytes()
    _rewrite_receipt(root, lambda receipt: receipt.__setitem__(
        "artifact_sha256", hashlib.sha256(artifact).hexdigest()))
    assert read_boe_materialization(root)["status"] == "failed"


def test_reader_denies_a_consistent_receipt_value_mutation(tmp_path):
    root = tmp_path / "data"
    _capture(root, OBSERVED)

    def mutate(receipt):
        receipt["rows"][-1]["value"] = 4.0
        receipt["value"] = 4.0

    _rewrite_receipt(root, mutate)
    assert read_boe_materialization(root)["status"] == "failed"


def test_reader_denies_a_mutated_original_response(tmp_path):
    root = tmp_path / "data"
    _capture(root, OBSERVED)
    blob = next((root / boe.DIRECTORY).glob("*.xml"))
    blob.write_bytes(blob.read_bytes().replace(b"3.75", b"4.00"))
    assert read_boe_materialization(root)["status"] == "failed"


def test_reader_denies_a_rewritten_original_response(tmp_path):
    root = tmp_path / "data"
    _capture(root, OBSERVED)
    # The same observations and the same notes, byte-different: only the
    # identity of the original response can refuse this.
    blob = next((root / boe.DIRECTORY).glob("*.xml"))
    blob.write_bytes(blob.read_bytes().replace(b"<Envelope xmlns=",
                                               b"<Envelope  xmlns="))
    assert read_boe_materialization(root)["status"] == "failed"


def test_reader_denies_a_store_rewritten_with_the_same_observations(tmp_path):
    root = tmp_path / "data"
    _capture(root, OBSERVED)
    # The same observations plus one older incumbent row: the values still
    # agree, so only the identity of the artifact can refuse this store.
    _store(root, [("2026-01-02", 3.75, "observed", "2026-01-05 09:30:00")]
           + list(OBSERVED))
    assert read_boe_materialization(root)["status"] == "failed"


def test_reader_denies_a_receipt_naming_a_reordered_carrier(tmp_path):
    root = tmp_path / "data"
    _capture(root, OBSERVED)
    reordered = ("https://www.bankofengland.co.uk/boeapps/database/"
                 "_iadb-fromshowcolumns.asp?SeriesCodes=IUDBEDR&CodeVer=new"
                 "&xml.x=yes&Datefrom=01%2FJan%2F2026&Dateto=02%2FNov%2F2026"
                 "&VPD=N&VFD=Y&VUD=A")
    _rewrite_receipt(root, lambda receipt: receipt.__setitem__(
        "source_url", reordered))
    assert read_boe_materialization(root)["status"] == "failed"


def test_a_broken_capture_still_carries_its_verified_receipt_digest(tmp_path):
    root = tmp_path / "data"
    _capture(root, OBSERVED)
    (root / "intl_macro" / (COLUMN + ".parquet")).unlink()
    materialized = read_boe_materialization(root)
    assert materialized["status"] == "failed"
    assert materialized["receipt_sha256"] is not None
    decision = _decision(materialized["receipt_sha256"])
    result = admit_boe_policy_field(materialized, EVALUATED_AT, decision)
    assert result["quality"] == "failed" and result["reason"] == "source_failed"
    assert result["metadata"] == "allowed" and result["value_permission"] == "allowed"
    assert result["value"] is None and result["observation_at"] is None


def test_reader_denies_a_duplicate_json_key(tmp_path):
    root = tmp_path / "data"
    _capture(root, OBSERVED)
    raw = (root / boe.DIRECTORY / "current.json").read_bytes()
    _write_raw_receipt(root, raw.replace(
        b'"column":"GB_bank_rate_official"',
        b'"column":"GB_bank_rate_official","column":"GB_bank_rate_official"', 1))
    assert read_boe_materialization(root)["status"] == "failed"


def test_reader_denies_a_nonfinite_json_value(tmp_path):
    root = tmp_path / "data"
    _capture(root, OBSERVED)
    raw = (root / boe.DIRECTORY / "current.json").read_bytes()
    _write_raw_receipt(root, raw.replace(
        b'"value":3.75,"value_status"', b'"value":NaN,"value_status"', 1))
    assert read_boe_materialization(root)["status"] == "failed"


# --------------------------------------------------------------------------
# Field admission
# --------------------------------------------------------------------------


def test_admitted_field_is_the_closed_native_measure_shape(captured):
    result = _admitted(captured)
    assert set(result) == {
        "quality", "reason", "metadata", "value_permission", "value", "unit",
        "instrument", "period", "observation_at", "calculation_at",
        "source_reference", "evidence_key"}
    assert result["quality"] == "qualified" and result["reason"] is None
    assert result["value"] == 3.75 and type(result["value"]) is float
    assert result["unit"] == "percent"
    assert result["instrument"] == {"kind": "official_policy", "id": "bank_rate",
                                     "market_id": "GB"}
    assert result["period"] is None and result["calculation_at"] is None
    assert result["observation_at"] == "2026-11-02"
    assert result["metadata"] == "allowed" and result["value_permission"] == "allowed"
    assert result["source_reference"].startswith(SOURCE_URL)
    assert result["evidence_key"].startswith("boe-bank-rate:")
    json.dumps(result, allow_nan=False)


def test_admitted_field_is_accepted_by_the_existing_measure_validator(captured):
    from lib.intl_workspace_macro import _measure

    output, value = _measure(FIELD, "GB", {FIELD: _admitted(captured)})
    assert value["quality"] == "qualified"
    assert output["value"] == 3.75 and output["observation_at"] == "2026-11-02"


def test_decision_binds_the_field_and_the_receipt(captured):
    materialized = read_boe_materialization(captured)
    decision = _decision(materialized["receipt_sha256"])
    result = admit_boe_policy_field(materialized, EVALUATED_AT, decision)
    assert result["quality"] == "qualified"
    foreign = _decision(materialized["receipt_sha256"],
                        binding={"field": "GB.other", "receipt_sha256": materialized["receipt_sha256"]})
    assert _blank(admit_boe_policy_field(materialized, EVALUATED_AT, foreign))
    stale = _decision(materialized["receipt_sha256"],
                      binding={"field": FIELD, "receipt_sha256": "0" * 64})
    assert _blank(admit_boe_policy_field(materialized, EVALUATED_AT, stale))


@pytest.mark.parametrize("override", [
    {"owner_ref": "scripts/other.py"},
    {"policy_ref": "docs/INTERNATIONAL_MACRO_DATA_CONTRACT.md#official-ecb-deposit-level-admission"},
    {"policy_ref": ""},
    {"decision_ref": ""},
    {"decision_ref": "   "},
    {"decision_ref": 7},
    {"metadata": "maybe"},
    {"value_permission": "maybe"},
])
def test_an_unvalidated_decision_permits_no_metadata(captured, override):
    materialized = read_boe_materialization(captured)
    decision = _decision(materialized["receipt_sha256"], **override)
    result = admit_boe_policy_field(materialized, EVALUATED_AT, decision)
    assert _blank(result)
    assert result["metadata"] == "unknown" and result["value_permission"] == "unknown"


def test_a_missing_decision_permits_no_metadata(captured):
    materialized = read_boe_materialization(captured)
    for decision in (None, {}, [], "allowed"):
        result = admit_boe_policy_field(materialized, EVALUATED_AT, decision)
        assert _blank(result)


def test_denied_metadata_scrubs_the_source_and_the_clocks(captured):
    materialized = read_boe_materialization(captured)
    decision = _decision(materialized["receipt_sha256"], metadata="denied")
    result = admit_boe_policy_field(materialized, EVALUATED_AT, decision)
    assert result["quality"] == "denied" and result["reason"] == "metadata_denied"
    assert result["metadata"] == "denied"
    assert _blank(result)


def test_unknown_metadata_scrubs_the_source_and_the_clocks(captured):
    materialized = read_boe_materialization(captured)
    decision = _decision(materialized["receipt_sha256"], metadata="unknown")
    result = admit_boe_policy_field(materialized, EVALUATED_AT, decision)
    assert result["quality"] == "unknown" and result["reason"] == "disclosure_unknown"
    assert _blank(result)


def test_a_denied_value_permission_keeps_the_metadata_but_not_the_number(captured):
    materialized = read_boe_materialization(captured)
    decision = _decision(materialized["receipt_sha256"], value_permission="denied")
    result = admit_boe_policy_field(materialized, EVALUATED_AT, decision)
    assert result["quality"] == "denied" and result["reason"] == "value_denied"
    assert result["value"] is None
    assert result["unit"] == "percent" and result["observation_at"] == "2026-11-02"
    assert result["source_reference"] is not None


def test_an_unknown_value_permission_keeps_the_metadata_but_not_the_number(captured):
    materialized = read_boe_materialization(captured)
    decision = _decision(materialized["receipt_sha256"], value_permission="unknown")
    result = admit_boe_policy_field(materialized, EVALUATED_AT, decision)
    assert result["quality"] == "unknown" and result["reason"] == "disclosure_unknown"
    assert result["value"] is None


def test_a_missing_capture_is_not_supplied(tmp_path):
    root = tmp_path / "data"
    materialized = read_boe_materialization(root)
    result = admit_boe_policy_field(materialized, EVALUATED_AT, None)
    assert result["quality"] == "missing" and result["reason"] == "not_supplied"
    assert _blank(result)


def test_a_failed_capture_after_an_allowed_decision_keeps_the_permission(captured):
    materialized = read_boe_materialization(captured)
    materialized = {**materialized, "status": "failed"}
    decision = _decision(materialized["receipt_sha256"])
    result = admit_boe_policy_field(materialized, EVALUATED_AT, decision)
    assert result["quality"] == "failed" and result["reason"] == "source_failed"
    assert result["metadata"] == "allowed" and result["value_permission"] == "allowed"
    assert result["value"] is None and result["observation_at"] is None
    assert result["calculation_at"] is None and result["source_reference"] is None
    assert result["unit"] == "percent"


def test_a_chronology_failure_nulls_the_value(captured):
    materialized = read_boe_materialization(captured)
    decision = _decision(materialized["receipt_sha256"])
    early = admit_boe_policy_field(materialized, "2026-11-04T08:00:00+00:00", decision)
    assert early["quality"] == "failed" and early["reason"] == "source_failed"
    assert early["value"] is None and early["observation_at"] is None
    assert early["source_reference"] is None


def test_the_current_display_uses_the_existing_daily_age_rule(tmp_path):
    root = tmp_path / "data"
    _capture(root, STALE)
    result = _admitted(root)
    assert result["quality"] == "stale" and result["reason"] == "source_stale"
    assert result["value"] == 3.75
    assert result["observation_at"] == "2026-10-20"


def test_the_age_threshold_is_owned_by_the_existing_cb_policy(tmp_path, monkeypatch):
    from engine import cb_desk

    root = tmp_path / "data"
    _capture(root, OBSERVED)
    assert _admitted(root)["quality"] == "qualified"
    monkeypatch.setitem(cb_desk._STALE_DAYS, "daily", 0)
    assert _admitted(root)["quality"] == "stale"


def test_a_historical_exact_endpoint_bypasses_the_current_age(tmp_path):
    root = tmp_path / "data"
    _capture(root, STALE)
    materialized = read_boe_materialization(root)
    decision = _decision(materialized["receipt_sha256"])
    result = admit_boe_policy_field(materialized, EVALUATED_AT, decision,
                                    observation_date="2026-09-30")
    assert result["quality"] == "qualified" and result["reason"] is None
    assert result["value"] == 3.75 and result["observation_at"] == "2026-09-30"
    assert "endpoint=historical_exact" in result["source_reference"]
    assert "vintage=latest_retrieval" in result["source_reference"]
    current = admit_boe_policy_field(materialized, EVALUATED_AT, decision)
    assert current["quality"] == "stale"


def test_a_historical_endpoint_absent_from_the_source_is_withheld(tmp_path):
    root = tmp_path / "data"
    _capture(root, OBSERVED)
    materialized = read_boe_materialization(root)
    decision = _decision(materialized["receipt_sha256"])
    result = admit_boe_policy_field(materialized, EVALUATED_AT, decision,
                                    observation_date="2026-10-05")
    assert result["value"] is None
    assert result["quality"] == "failed" and result["reason"] == "source_failed"
    assert result["observation_at"] is None and result["source_reference"] is None


def test_a_historical_endpoint_never_falls_back_to_a_nearest_row(tmp_path):
    root = tmp_path / "data"
    _capture(root, OBSERVED)
    materialized = read_boe_materialization(root)
    decision = _decision(materialized["receipt_sha256"])
    result = admit_boe_policy_field(materialized, EVALUATED_AT, decision,
                                    observation_date="2026-10-05")
    assert result["value"] is None
    # No endpoint date at all: no nearest supplied row was substituted.
    assert result["observation_at"] is None
    assert result["source_reference"] is None
    assert result["quality"] == "failed" and result["reason"] == "source_failed"


def test_admission_refuses_a_stored_row_that_disagrees_with_the_native_row(tmp_path):
    root = tmp_path / "data"
    _capture(root, OBSERVED)
    materialized = read_boe_materialization(root)
    series = materialized["series"].copy()
    series.iloc[-1] = 4.0
    materialized = {**materialized, "series": series}
    decision = _decision(materialized["receipt_sha256"])
    result = admit_boe_policy_field(materialized, EVALUATED_AT, decision)
    assert result["value"] is None
    assert result["quality"] == "failed" and result["reason"] == "source_failed"
    assert result["observation_at"] is None


def test_a_withheld_tail_never_resurrects_the_cached_value(tmp_path):
    root = tmp_path / "data"
    # The cache still carries an older value for the withheld native date.
    _capture(root, WITHHELD_TAIL, values=[3.75, 3.75, 3.75])
    materialized = read_boe_materialization(root)
    assert materialized["status"] == "ready"
    decision = _decision(materialized["receipt_sha256"])
    current = admit_boe_policy_field(materialized, EVALUATED_AT, decision)
    assert current["value"] is None
    assert current["quality"] == "unknown" and current["reason"] == "disclosure_unknown"
    exact = admit_boe_policy_field(materialized, EVALUATED_AT, decision,
                                   observation_date="2026-11-02")
    assert exact["value"] is None
    assert exact["observation_at"] == "2026-11-02"


def test_a_withheld_row_is_never_filled_from_the_store(tmp_path):
    root = tmp_path / "data"
    _capture(root, WITHHELD_TAIL, values=[3.75, 3.75, 3.75])
    materialized = read_boe_materialization(root)
    decision = _decision(materialized["receipt_sha256"])
    result = admit_boe_policy_field(materialized, EVALUATED_AT, decision,
                                    observation_date="2026-11-02")
    assert result["value"] is None


def test_a_future_observation_is_refused(tmp_path):
    root = tmp_path / "data"
    # The capture predates the observation, so the refusal is the future
    # observation and not the committed-after-evaluation chronology.
    _capture(root, OBSERVED,
             requested_at="2026-10-01T08:00:00.000000+00:00",
             response_received_at="2026-10-01T08:00:01.000000+00:00",
             input_verified_at="2026-10-01T08:00:02.000000+00:00",
             committed_at="2026-10-01T08:00:03.000000+00:00")
    materialized = read_boe_materialization(root)
    decision = _decision(materialized["receipt_sha256"])
    evaluated = "2026-10-01T12:00:00+00:00"
    result = admit_boe_policy_field(materialized, evaluated, decision)
    assert result["value"] is None
    assert result["quality"] == "failed" and result["reason"] == "source_failed"
    assert result["observation_at"] is None
    # The past row of the same response is still an exact native endpoint.
    historical = admit_boe_policy_field(materialized, evaluated, decision,
                                        observation_date="2026-09-30")
    assert historical["value"] == 3.75
    assert historical["observation_at"] == "2026-09-30"


@pytest.mark.parametrize("date,quality", [("2026-10-23", "qualified"),
                                           ("2026-10-22", "stale")])
def test_the_daily_age_boundary_is_exclusive(tmp_path, date, quality):
    root = tmp_path / "data"
    _capture(root, [(date, 3.75, "observed", date + " 09:30:00")])
    result = _admitted(root)
    assert result["quality"] == quality
    assert result["value"] == 3.75


def test_capture_refuses_an_observation_outside_the_supplied_range(tmp_path):
    root = tmp_path / "data"
    rows = [("2019-06-01", 3.75, "observed", "2019-06-02 09:30:00"),
            ("2026-11-02", 3.75, "observed", "2026-11-03 09:30:00")]
    frame = _store(root, rows)
    with pytest.raises(ValueError):
        capture_boe_commit(root, frame, _response(rows), SOURCE_URL, **CLOCKS)


def test_admission_refuses_an_observation_outside_the_supplied_range(tmp_path):
    root = tmp_path / "data"
    _capture(root, OBSERVED)
    widened = [("2019-06-01", 3.75, "observed", "2019-06-02 09:30:00")] + list(OBSERVED)
    frame = _forge_capture(root, widened)
    materialized = read_boe_materialization(root)
    assert materialized["status"] == "failed"
    # The forged capture is refused by the reader; the admission refuses the
    # same row even when the reader is handed it directly.
    receipt = json.loads((root / boe.DIRECTORY / "current.json").read_bytes())
    materialized = {"status": "ready", "series": frame[COLUMN], "receipt": receipt,
                    "receipt_sha256": hashlib.sha256(
                        (root / boe.DIRECTORY / "current.json").read_bytes()).hexdigest()}
    decision = _decision(materialized["receipt_sha256"])
    result = admit_boe_policy_field(materialized, EVALUATED_AT, decision,
                                    observation_date="2019-06-01")
    assert result["value"] is None
    assert result["quality"] == "failed" and result["reason"] == "source_failed"
    assert result["observation_at"] is None


def test_no_publication_or_vintage_clock_is_fabricated(captured):
    materialized = read_boe_materialization(captured)
    receipt = materialized["receipt"]
    assert receipt["provider_published_at"] is None
    assert receipt["revision_vintage"] is None
    result = _admitted(captured)
    assert result["calculation_at"] is None
    assert result["observation_at"] == "2026-11-02"


def test_the_admitted_field_is_json_serialisable_without_nan(captured):
    result = _admitted(captured)
    assert json.loads(json.dumps(result, allow_nan=False))["value"] == 3.75


def test_parent_current_calendar_year_carrier_is_not_pinned_to_old_download_end(tmp_path):
    root = tmp_path / 'data'
    frame = _store(root, OBSERVED)
    url = SOURCE_URL.replace('Dateto=02%2FNov%2F2026', 'Dateto=04%2FNov%2F2026')
    r = capture_boe_commit(root, frame, _response(OBSERVED), url, **CLOCKS)
    assert r['source_query']['Dateto'] == '04/Nov/2026'
    m = read_boe_materialization(root)
    assert m['status'] == 'ready'
    assert admit_boe_policy_field(m, EVALUATED_AT, _decision(m['receipt_sha256']))['value'] == 3.75


@pytest.mark.parametrize('query', [
    'Datefrom=01%2FJan%2F2025', 'Dateto=02%2FJan%2F2026',
    'Datefrom=1%2FJan%2F2026', 'Datefrom=01%2FXXX%2F2026'])
def test_parent_native_range_bounds_reject_cross_year_reversed_or_malformed(tmp_path, query):
    root = tmp_path / 'data'; frame = _store(root, OBSERVED)
    key = query.split('=')[0]
    import re
    url = re.sub(key + '=[^&]*', query, SOURCE_URL)
    with pytest.raises(ValueError):
        capture_boe_commit(root, frame, _response(OBSERVED), url, **CLOCKS)


@pytest.mark.parametrize('mutation', ['requested_at','rows','series'])
def test_parent_pure_admission_does_not_trust_mutated_receipt_or_absent_store(captured, mutation):
    from copy import deepcopy
    m = deepcopy(read_boe_materialization(captured)); decision = _decision(m['receipt_sha256'])
    if mutation == 'requested_at':m['receipt']['requested_at'] = '2026-11-05T00:00:00+00:00'
    if mutation == 'rows':m['receipt']['rows'][-1]['source_updated_raw'] = 'forged'
    if mutation == 'series':m['series'] = None
    r = admit_boe_policy_field(m, EVALUATED_AT, decision)
    assert r['quality'] == 'failed' and r['reason'] == 'source_failed'
    assert r['metadata'] == r['value_permission'] == 'allowed'
    assert r['value'] is r['source_reference'] is r['observation_at'] is None


def test_parent_denied_value_precedence_is_preserved_for_withheld_tail(tmp_path):
    root=tmp_path/'data';_capture(root, WITHHELD_TAIL, values=[3.75,3.75,3.75])
    m=read_boe_materialization(root);r=admit_boe_policy_field(m,EVALUATED_AT,_decision(m['receipt_sha256'],value_permission='denied'))
    assert r['quality']=='denied' and r['reason']=='value_denied' and r['value'] is None
