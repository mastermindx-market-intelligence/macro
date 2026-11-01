"""Unit tests for ``scripts.regime_outlook_replay`` (slice E1r / rule R-I).

Pure-path tests only: synthetic frames, injected mapping, injected producers.
Never reads ``data/``/``site/`` stores; never opens a parquet file.
"""
from __future__ import annotations

import importlib.util
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
SCRIPT_PATH = SCRIPTS_DIR / "regime_outlook_replay.py"
FIXTURE_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "regime_outlook" / "readings_golden_v2.json"
)


def _load_module():
    """Load the tool as a module without making ``scripts`` a package."""
    spec = importlib.util.spec_from_file_location(
        "regime_outlook_replay", SCRIPT_PATH,
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def tool():
    return _load_module()


@pytest.fixture(scope="module")
def mapping():
    from engine.rates_command_outlook import load_mapping
    return load_mapping()


@pytest.fixture(scope="module")
def mapping_sha(mapping):
    from engine.rates_command_outlook import mapping_sha256
    return mapping_sha256()


@pytest.fixture(scope="module")
def golden_base():
    with FIXTURE_PATH.open() as f:
        return json.load(f)["base"]


def _make_frame(d: str, *, extra_rows_pct: float = 0.0) -> pd.DataFrame:
    """Synthetic frame with business-day index spanning well past ``d``.

    ``extra_rows_pct`` lets a test inflate the tail past the date so the cut
    actually has something to clip.
    """
    start = pd.Timestamp(d) - pd.tseries.offsets.BDay(30)
    end = pd.Timestamp(d) + pd.tseries.offsets.BDay(60 + int(60 * extra_rows_pct))
    idx = pd.bdate_range(start, end)
    f = pd.DataFrame(index=idx)
    f["nfci"] = 0.0
    f["anfci"] = 0.0
    f["infl_exp_5y"] = 2.0
    f["indeed_postings"] = 100.0
    f["pct_above_200"] = 0.5
    f["net_liquidity_bn"] = 100.0
    f["zq_front"] = 95.0
    f["liquidity"] = "expanding"
    return f


# ---------------------------------------------------------------------------
# T1 / T2: build_frame
# ---------------------------------------------------------------------------

def test_build_frame_cuts_and_clears_attrs(tool):
    """The cut clips rows past the date and records what was cleared."""
    frame = _make_frame("2022-10-31")
    captured = {}

    def fake_bf(pit_basis=None, pit_as_of=None):
        captured["pit_basis"] = pit_basis
        captured["pit_as_of"] = pit_as_of
        return frame.copy()

    out = tool.build_frame("2022-10-31", build_features=fake_bf)
    assert captured["pit_basis"] == "release"
    assert captured["pit_as_of"] == "2022-10-31"
    assert out.index[-1] <= pd.Timestamp("2022-10-31")
    # attrs is cleared for downstream use; cleared copy lives under the key.
    assert "cleared_attrs" in out.attrs
    # Whatever was on the source frame lives in cleared_attrs (the source had
    # no attrs but the contract still records the cleared snapshot).
    assert isinstance(out.attrs["cleared_attrs"], dict)


def test_build_frame_empty(tool):
    """Empty frame raises ValueError."""
    empty = pd.DataFrame(index=pd.DatetimeIndex([], tz=None))
    with pytest.raises(ValueError, match="empty"):
        tool.build_frame("2022-10-31", build_features=lambda **_: empty)


# ---------------------------------------------------------------------------
# Producer helpers
# ---------------------------------------------------------------------------

def _golden_producers(base: dict, **overrides):
    """Producers that return the golden fixture's owner dicts.

    Each producer hands back the WHOLE dict the real producer returns (the
    shape the nightly stores), so the mapping's sibling-reading clocks and
    guards see what they see in production. ``yield_curve_regime`` returns the
    FLAT regime dict (``engine/yield_curve.py`` ``regime()``), which the tool
    nests under ``yield_curve.regime`` the way ``snapshot()`` does.
    """
    T, R, M = base["T"], base["R"], base["M"]
    comp = next(c for c in M["components"] if c.get("key") == "breadth")
    producers = {
        "current_state":            lambda f, **_: json.loads(json.dumps(T["state"])),
        "breakeven_decomposition":  lambda f, **_: json.loads(json.dumps(T["breakeven_decomp"])),
        "yield_curve_regime":       lambda f, **_: json.loads(json.dumps(T["yield_curve"]["regime"])),
        "build_yield_momentum":     lambda f, **_: json.loads(json.dumps(T["yield_momentum"])),
        "conditions_snapshot":      lambda f, **_: json.loads(json.dumps(R["conditions"])),
        "liquidity_overlay":        lambda f, **_: "neutral",
        "liquidity_quality":        lambda f, **_: json.loads(json.dumps(R["liquidity_quality"])),
        "comp_breadth":             lambda p, **_: json.loads(json.dumps(comp)),
    }
    producers.update(overrides)
    return producers


def _cut(d: str) -> pd.DataFrame:
    """Synthetic frame truncated at ``d`` (what ``build_frame`` hands over)."""
    return _make_frame(d).loc[:d]


def _letters_by_field(coverage: dict) -> dict[str, str]:
    seen: dict[str, str] = {}
    for letter, cov in coverage.items():
        for fid, mark in cov["fields"].items():
            assert fid not in seen, f"{fid} reported twice ({seen[fid]} and {letter})"
            seen[fid] = mark
    return seen


# ---------------------------------------------------------------------------
# T3: reconstruct_letters — every mapping field appears exactly once
# ---------------------------------------------------------------------------

def test_reconstruct_letters_field_inventory(tool, mapping, golden_base):
    """T/R/M bytes parse; L/B/D/C are None; every field reported once."""
    producers = _golden_producers(golden_base)
    input_bytes, coverage = tool.reconstruct_letters(
        _cut("2022-10-31"), "2022-10-31", producers=producers,
    )
    assert set(input_bytes) == set("TRMLBDC")
    for L in "TRM":
        parsed = json.loads(input_bytes[L].decode("utf-8"))
        assert parsed["asof"] == "2022-10-31", (L, parsed["asof"])
    for L in "LBDC":
        assert input_bytes[L] is None
        assert coverage[L]["status"] == "unavailable"
        assert coverage[L]["reason"]

    marks = _letters_by_field(coverage)
    assert set(marks) == {f["field_id"] for f in mapping["fields"]}
    for L in "LBDC":
        for fid, mark in coverage[L]["fields"].items():
            assert mark.startswith("not_produced:"), (fid, mark)


def test_reconstruct_letters_keeps_whole_owner_dicts(tool, golden_base):
    """The docs carry the producers' WHOLE dicts under the nightly's keys.

    The first replay run (2026-10-04) copied single leaves and read ``unknown``
    on every row because the mapping's clocks/guards read siblings
    (``breakeven_decomp.as_of``, ``velocity_bp.22d``, ``conditions.vintages``,
    ``stress_overlay.hy_oas_z``, ``components[].degraded``...).
    """
    producers = _golden_producers(golden_base)
    input_bytes, coverage = tool.reconstruct_letters(
        _cut("2022-10-31"), "2022-10-31", producers=producers,
    )
    T = json.loads(input_bytes["T"])
    R = json.loads(input_bytes["R"])
    M = json.loads(input_bytes["M"])
    base = golden_base
    assert T["state"] == base["T"]["state"]
    assert T["breakeven_decomp"] == base["T"]["breakeven_decomp"]
    assert T["yield_curve"]["regime"] == base["T"]["yield_curve"]["regime"]
    assert T["yield_curve"]["asof"] == "2022-10-31"
    assert T["yield_momentum"] == base["T"]["yield_momentum"]
    assert R["conditions"] == base["R"]["conditions"]
    assert R["liquidity_quality"] == base["R"]["liquidity_quality"]
    assert R["liquidity_overlay"] == "neutral"
    assert isinstance(M["components"], list)
    assert M["components"][0]["key"] == "breadth"
    assert M["components"][0]["degraded"] is False
    assert M["input_vintages"] == base["R"]["conditions"]["vintages"]
    # Golden 2y turn_watch is null: the producer ran, the leaf is null, so the
    # mark is produced_null (the mapping's turn_watch_null guard decides).
    assert coverage["T"]["fields"]["T.yield_momentum.series.2y.turn_watch"] == "produced_null"
    assert coverage["T"]["fields"]["T.yield_momentum.series.5y.turn_watch"] == "produced"
    assert coverage["R"]["labor_votes"] == 3
    assert coverage["R"]["fields"]["R.conditions.labor_nowcast.read"] == "produced"
    assert coverage["M"]["fields"]["M.components.breadth.tone"] == "produced"


def test_leaf_resolves_keyed_list_segments(tool):
    doc = {"components": [{"key": "x", "tone": 1}, {"key": "breadth", "tone": "bad"}]}
    assert tool._leaf(doc, ["components", {"key": "breadth"}, "tone"]) == "bad"
    assert tool._leaf(doc, ["components", {"key": "nope"}, "tone"]) is None
    assert tool._leaf({"components": {}}, ["components", {"key": "breadth"}, "tone"]) is None
    assert tool._leaf({"a": {"b": None}}, ["a", "b"]) is None
    assert tool._leaf({"a": {"b": False}}, ["a", "b"]) is False


# ---------------------------------------------------------------------------
# T4: the positive control — the golden base reads AVAILABLE through the
# real composer with the pinned tokens, at the fixture's own date.
# ---------------------------------------------------------------------------

def test_golden_base_reads_available_through_composer(tool, mapping, golden_base):
    """Every T/R/M field reads ``available`` with the pinned token.

    This is the control the first run lacked: if the reconstruction drops a
    sibling the mapping needs, the row reads ``unknown`` here and the test
    fails, instead of the replay output silently reading all-unknown.
    """
    from engine.rates_command_outlook_compose import evidence_rows, read_inputs

    with FIXTURE_PATH.open() as f:
        pin_fields = json.load(f)["pin"]["fields"]
    d = "2026-10-02"
    producers = _golden_producers(golden_base)
    input_bytes, coverage = tool.reconstruct_letters(_cut(d), d, producers=producers)
    docs, record = read_inputs(mapping, input_bytes)
    rows = evidence_rows(
        mapping, docs, record,
        analysis_cutoff=datetime(2026, 10, 2, 23, 59, tzinfo=timezone.utc),
        us_session=datetime(2026, 10, 2).date(),
    )
    by_id = {r["id"]: r for r in rows}
    produced = {
        fid for L in "TRM" for fid, mark in coverage[L]["fields"].items()
        if mark in ("produced", "produced_null")
    }
    assert produced, "no T/R/M field produced"
    bad = []
    for fid in sorted(produced):
        row = by_id.get(fid)
        pin = pin_fields.get(fid) or {}
        if row is None:
            bad.append((fid, "no evidence row"))
            continue
        if row["status"] != "available":
            bad.append((fid, row["status"], row.get("issues")))
            continue
        if pin.get("admitted") and pin.get("token") is not None:
            got = (row.get("owner_verdict") or {}).get("token")
            if got != pin["token"]:
                bad.append((fid, f"token {got!r} != pinned {pin['token']!r}"))
    assert not bad, bad


def test_fake_producers_read_available_at_replay_dates(tool, mapping):
    """The CLI's synthetic producers also clear the composer at every replay
    date (guards the fakes against drifting from the real shapes)."""
    from engine.rates_command_outlook_compose import evidence_rows, read_inputs

    producers = tool._fake_producers()
    for d in tool.REPLAY_DATES:
        input_bytes, coverage = tool.reconstruct_letters(_cut(d), d, producers=producers)
        docs, record = read_inputs(mapping, input_bytes)
        y, m, dd = (int(x) for x in d.split("-"))
        rows = evidence_rows(
            mapping, docs, record,
            analysis_cutoff=datetime(y, m, dd, 23, 59, tzinfo=timezone.utc),
            us_session=datetime(y, m, dd).date(),
        )
        fids = {f["field_id"] for f in mapping["fields"]}
        trm = [r for r in rows if r["id"] in fids and r["id"][0] in "TRM"]
        assert len(trm) == 19
        off = [(d, r["id"], r["status"], r.get("issues")) for r in trm if r["status"] != "available"]
        assert not off, off


# ---------------------------------------------------------------------------
# T5: F7 labour marking is DATA-DRIVEN (vote count), never date-driven
# ---------------------------------------------------------------------------

def _conditions_with_votes(base: dict, *present: str) -> dict:
    cond = json.loads(json.dumps(base["R"]["conditions"]))
    for k in ("claims_yoy_pct", "indeed_chg_3m_pct", "withheld_tax_yoy_pct"):
        if k not in present:
            cond["labor_nowcast"][k] = None
    return cond


@pytest.mark.parametrize("present, votes, mark, read_kept", [
    (("claims_yoy_pct", "indeed_chg_3m_pct", "withheld_tax_yoy_pct"), 3, "produced", True),
    (("claims_yoy_pct", "withheld_tax_yoy_pct"), 2, "partial:2_of_3_votes", True),
    (("claims_yoy_pct",), 1, "unavailable:single_vote", False),
    ((), 0, "unavailable:no_votes", False),
])
def test_labor_marking_follows_vote_count(tool, golden_base, present, votes, mark, read_kept):
    cond = _conditions_with_votes(golden_base, *present)
    producers = _golden_producers(golden_base, conditions_snapshot=lambda f, **_: cond)
    # Date is irrelevant: the same conditions dict yields the same mark on
    # every replay date (2018 and 2022 alike).
    for d in ("2018-10-31", "2022-10-31"):
        input_bytes, coverage = tool.reconstruct_letters(_cut(d), d, producers=producers)
        assert coverage["R"]["labor_votes"] == votes, d
        assert coverage["R"]["fields"]["R.conditions.labor_nowcast.read"] == mark, d
        R = json.loads(input_bytes["R"])
        assert ("read" in R["conditions"]["labor_nowcast"]) is read_kept, d
        if read_kept:
            assert R["conditions"]["labor_nowcast"]["read"] == "labor firm"


def test_labor_single_vote_reads_missing_not_unknown(tool, mapping, golden_base):
    """A dropped single-vote read surfaces as the composer's missing-leaf
    reading, not as a fabricated 'labor mixed' default."""
    from engine.rates_command_outlook_compose import evidence_rows, read_inputs

    cond = _conditions_with_votes(golden_base, "claims_yoy_pct")
    producers = _golden_producers(golden_base, conditions_snapshot=lambda f, **_: cond)
    d = "2026-10-02"
    input_bytes, _ = tool.reconstruct_letters(_cut(d), d, producers=producers)
    docs, record = read_inputs(mapping, input_bytes)
    rows = evidence_rows(
        mapping, docs, record,
        analysis_cutoff=datetime(2026, 10, 2, 23, 59, tzinfo=timezone.utc),
        us_session=datetime(2026, 10, 2).date(),
    )
    row = next(r for r in rows if r["id"] == "R.conditions.labor_nowcast.read")
    assert row["status"] != "available"
    assert (row.get("owner_verdict") or {}).get("token") != "labor mixed"


# ---------------------------------------------------------------------------
# T6: producer errors mark the letter unavailable; siblings unaffected
# ---------------------------------------------------------------------------

def test_letter_unavailable_when_producer_raises(tool, golden_base):
    def boom(f, **_):
        raise RuntimeError("synthetic")

    producers = _golden_producers(golden_base, current_state=boom)
    input_bytes, coverage = tool.reconstruct_letters(
        _cut("2022-10-31"), "2022-10-31", producers=producers,
    )
    assert input_bytes["T"] is None
    assert coverage["T"]["status"] == "unavailable"
    assert coverage["T"]["reason"] == "producer_error:RuntimeError"
    for fid, mark in coverage["T"]["fields"].items():
        assert mark.startswith("not_produced:producer_error:RuntimeError"), (fid, mark)
    assert coverage["R"]["status"] == "reconstructed"
    assert coverage["M"]["status"] == "reconstructed"


def test_m_marks_owner_none_when_breadth_component_absent(tool, golden_base):
    """_comp_breadth returns None without a breadth percentile; M says so."""
    producers = _golden_producers(golden_base, comp_breadth=lambda p, **_: None)
    input_bytes, coverage = tool.reconstruct_letters(
        _cut("2022-10-31"), "2022-10-31", producers=producers,
    )
    M = json.loads(input_bytes["M"])
    assert M["components"] == []
    assert coverage["M"]["status"] == "reconstructed"
    assert coverage["M"]["fields"]["M.components.breadth.tone"] == "not_produced:owner_returned_none"


# ---------------------------------------------------------------------------
# T7: replay end to end
# ---------------------------------------------------------------------------

def test_replay_end_to_end(tool, mapping, mapping_sha):
    """4 per_date rows; 9 cards in mapping order; byte-deterministic JSON;
    produced T/R/M rows read available under the synthetic producers."""
    producers = tool._fake_producers()

    def bf(d, **_):
        return _cut(d)

    out = tool.replay(
        mapping, mapping_sha256=mapping_sha, build_frame_fn=bf, producers=producers,
    )

    assert out["schema_version"] == "regime_outlook_replay.v1"
    assert out["label"] == tool.LABEL
    assert out["rule"] == "R-I"
    assert out["seen_history_row"] == "SH-12"
    assert out["revised_columns_caveat"]

    assert len(out["per_date"]) == 4
    expected_path_ids = [p["path_id"] for p in mapping["paths"]]
    for row in out["per_date"]:
        got = [c["path_id"] for c in row["paths"]]
        assert got == expected_path_ids, f"{row['date']}: got {got}"
        n_trm = sum(
            1 for L in "TRM" for mark in row["letters"][L]["fields"].values()
            if mark in ("produced", "produced_null")
        )
        assert n_trm == 19, (row["date"], n_trm)
        assert row["evidence_summary"]["available"] >= n_trm, row["evidence_summary"]
        # one reading per mapping field, in mapping order, each classed
        assert [e["id"] for e in row["readings"]] == [f["field_id"] for f in mapping["fields"]]
        for e in row["readings"]:
            assert e["history"] in tool.HISTORY_LEGEND, e
            if e["replay_mark"] == "produced":
                assert e["history"] == "read" and e["status"] == "available", e
    assert out["output_path"] == "config/regime_outlook_replay_v2_sh12.json"
    assert out["history_legend"] == tool.HISTORY_LEGEND

    out2 = tool.replay(
        mapping, mapping_sha256=mapping_sha, build_frame_fn=bf, producers=producers,
    )
    assert json.dumps(out) == json.dumps(out2)


# ---------------------------------------------------------------------------
# T8: CLI
# ---------------------------------------------------------------------------

def _run_cli(tool, monkeypatch, argv):
    """Invoke the CLI entry point in-process and return its exit code.

    Deliberately NOT a subprocess: the CI scope inference
    (scripts/ci_scope_dependencies.py) reads a ``subprocess.run`` inside a
    suite as an opaque edge and smears whole scan roots (``scripts/**``,
    ``config/**``, ...) into the owning job's fallback scope, so an ordinary
    PR touching any script would select the regime-outlook-mapping job —
    contract-delta's packing probe measured exactly that on this suite.
    ``main(argv)`` returns the exit code, so the process boundary buys
    nothing here.
    """
    monkeypatch.setenv("REGIME_OUTLOOK_REPLAY_FAKE_FRAME", "1")
    monkeypatch.chdir(REPO_ROOT)
    return tool.main(argv)


def test_cli_dry_run_writes_nothing(tool, tmp_path, monkeypatch, capsys):
    """--dry-run prints the table and does not write."""
    rc = _run_cli(tool, monkeypatch, ["--dry-run"])
    captured = capsys.readouterr()
    assert rc == 0, captured.err
    out_path = tmp_path / "should_not_exist.json"
    assert not out_path.exists()
    assert "T | R | M | L | B | D | C" in captured.out


def test_cli_writes_file(tool, tmp_path, monkeypatch, capsys):
    """--out writes a parseable JSON file ending in a newline."""
    out_path = tmp_path / "out.json"
    rc = _run_cli(tool, monkeypatch, ["--out", str(out_path)])
    captured = capsys.readouterr()
    assert rc == 0, captured.out + captured.err
    assert out_path.exists()
    raw = out_path.read_bytes()
    assert raw.endswith(b"\n")
    parsed = json.loads(raw.decode("utf-8"))
    assert parsed["schema_version"] == "regime_outlook_replay.v1"


@pytest.mark.parametrize("mark, cls", [
    ("produced", "read"),
    ("produced_null", "owner_null"),
    ("partial:2_of_3_votes", "partial_history"),
    ("unavailable:single_vote", "insufficient_history"),
    ("unavailable:no_votes", "insufficient_history"),
    ("not_produced:producer_error:KeyError", "producer_error"),
    ("not_produced:owner_returned_none", "not_in_replay"),
    ("not_produced:rate_futures_history_starts_2026_03_16", "insufficient_history"),
    ("not_produced:no_point_in_time_membership_and_no_as_of_seam", "not_in_replay"),
    (None, "not_in_replay"),
])
def test_history_class_vocabulary(tool, mark, cls):
    """Every replay mark maps onto a legend entry (R-I: insufficient_history
    is reported, never approximated)."""
    assert tool._history_class(mark) == cls
    assert cls in tool.HISTORY_LEGEND


def test_cli_accepts_config_out(tool, tmp_path, monkeypatch, capsys):
    """config/ is the contract's home for the output (E1r: beside the mapping);
    the CLI must not refuse it. Written under a tmp dir named config/."""
    out_dir = tmp_path / "config"
    out_dir.mkdir()
    out_path = out_dir / "regime_outlook_replay_v2_sh12.json"
    rc = _run_cli(tool, monkeypatch, ["--out", str(out_path)])
    captured = capsys.readouterr()
    assert rc == 0, captured.out + captured.err
    assert out_path.exists()


def test_cli_refuses_data_out(tool, monkeypatch, capsys):
    """--out under data/ exits 2 with the forbidden-root message."""
    rc = _run_cli(tool, monkeypatch, ["--out", "data/x.json"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "regime-outlook-replay-out-forbidden" in captured.out


# ---------------------------------------------------------------------------
# T9: source check — banned tokens absent from the module source
# ---------------------------------------------------------------------------

def test_module_does_not_call_banned_producers():
    """The module must never name these forbidden call shapes."""
    src = SCRIPT_PATH.read_text()
    banned = (
        "fed_path.snapshot",
        "rate_inflation_transmission.snapshot",
        "leadership_crack._build",
        "fed_path.compute",
    )
    for tok in banned:
        assert tok not in src, f"banned token present in source: {tok}"