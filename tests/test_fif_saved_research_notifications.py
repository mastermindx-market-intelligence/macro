"""tests/test_fif_saved_research_notifications.py — the X2-n producer (spec §5).

Hermetic: the HTTP layer is a monkeypatched fake at the module's ONE IO seam
(`_pg`), and an autouse fixture makes socket connects raise so nothing in
this suite can touch a network by accident. Trigger inputs are local fixture
files (private state / receipt mirror / pointer mirror) under tmp_path.

Pins:
  1. one alert_outbox row per (user, event);
  2. replay over the same vintage inserts nothing (pre-insert SELECT dedupe
     AND the 409/23505 insert-or-ignore backstop);
  3. no row for a non-subscriber, and no cross-user row (two-user fixture,
     spec gate 3a);
  4. dormant default: with either flag unset/non-"1" the runner exits 0,
     performs ZERO HTTP calls and ZERO file writes, and never even imports
     the producer (S1);
  5. missing credentials / missing tables / missing inputs -> exit 0, 0 rows;
  6. missing generation pointer -> NO event, never an error (R5);
  7. the exact frozen fire_event_id format for all three kinds;
  8. payload: only the allowed fields, category "fif_saved_issuer", no
     banned tokens, no digits that are metric values;
  9. R3 recency gate: a high_finding row is emitted only when
     0 <= (as_of - filing_index date).days <= FIF_NEW_FINDING_WINDOW_DAYS,
     anchored on the state document's `as_of` — never wall clock — with every
     suppression counted under its typed key; new_filing and generation are
     ungated; the payload records event_date.
"""
from __future__ import annotations

import gzip
import io
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
from pathlib import Path

import pytest

from engine import fif_saved_research_notifications as producer

ROOT = Path(__file__).resolve().parents[1]

ALLOWED_PAYLOAD_FIELDS = {
    "ticker", "condition_plain", "evidence_url", "subject", "fired_at", "category",
    "event_date",
}


# ---------------------------------------------------------------------------
# Hermeticity: no socket may leave this suite.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def _refuse(*args, **kwargs):
        raise AssertionError("network access attempted in a hermetic test")

    monkeypatch.setattr("socket.socket.connect", _refuse, raising=True)


# ---------------------------------------------------------------------------
# A fake PostgREST at the producer's single IO seam.
# ---------------------------------------------------------------------------
class _Http409(urllib.error.HTTPError):
    def __init__(self):
        super().__init__("https://x/rest/v1/alert_outbox", 409, "duplicate key",
                         None, None)


class _Http404(urllib.error.HTTPError):
    def __init__(self):
        super().__init__("https://x", 404, "not found", None,
                         io.BytesIO(b'{"code":"PGRST205"}'))


class FakePg:
    """Minimal PostgREST double: filters only the shapes the producer builds."""

    def __init__(self, *, lists=None, symbols=None, outbox=None):
        self.calls: list[tuple] = []
        self.lists = [dict(r) for r in (lists or [])]
        self.symbols = [dict(r) for r in (symbols or [])]
        self.outbox = [dict(r) for r in (outbox or [])]

    @staticmethod
    def _eq_param(path: str, key: str):
        marker = f"{key}=eq."
        if marker not in path:
            return None
        rest = path.split(marker, 1)[1].split("&", 1)[0]
        return urllib.parse.unquote(rest)

    @staticmethod
    def _in_param(path: str, key: str):
        marker = f"{key}=in.("
        if marker not in path:
            return []
        rest = path.split(marker, 1)[1].split(")", 1)[0]
        return [urllib.parse.unquote(x) for x in rest.split(",") if x]

    def __call__(self, method, path, body=None, prefer=None, timeout=6):
        self.calls.append((method, path, body))
        if method == "GET":
            if path.startswith("watchlists?"):
                name = self._eq_param(path, "name")
                return [dict(r) for r in self.lists if name is None or r["name"] == name]
            if path.startswith("watchlist_symbols?"):
                ids = set(self._in_param(path, "watchlist_id"))
                return [dict(r) for r in self.symbols if str(r["watchlist_id"]) in ids]
            if path.startswith("alert_outbox?"):
                ids = set(self._in_param(path, "fire_event_id"))
                return [{"fire_event_id": r["fire_event_id"]}
                        for r in self.outbox if r["fire_event_id"] in ids]
            raise AssertionError(f"unexpected GET path: {path}")
        if method == "POST":
            assert path == "alert_outbox", path
            for existing in self.outbox:
                if existing["fire_event_id"] == body["fire_event_id"]:
                    raise _Http409()
            self.outbox.append(dict(body))
            return None
        raise AssertionError(f"unexpected {method} {path}")


@pytest.fixture
def fake_pg(monkeypatch):
    def _install(**kwargs):
        fake = FakePg(**kwargs)
        monkeypatch.setattr(producer, "SUPABASE_SERVICE_ROLE_KEY", "test-key")
        monkeypatch.setattr(producer, "_pg", fake)
        return fake

    return _install


# ---------------------------------------------------------------------------
# Trigger-input fixtures (local mirrors under tmp_path).
# ---------------------------------------------------------------------------
def _write_state(root: Path, companies: dict, generated_at="2026-10-12T00:00:00Z",
                 as_of="2026-10-10", default_filed="2026-10-05"):
    """Write the private state in the REAL builder shape (R3): the document
    carries `as_of` (max latest_filed across the universe,
    scripts/build_fundamental_forensics.py:1209,1224) and every finding's
    `evidence` starts with a basis="filing_index" link whose `date` is the
    current period's filed date (:212-231,291). A finding written WITHOUT an
    explicit `evidence` gets the default_filed link — inside the R3 window —
    so pre-R3 fixtures keep their exact expectations under the gate. Pass
    as_of=None to omit the anchor (the as_of_missing case); pass a finding's
    own `evidence` to control or break its date."""
    def _norm(findings):
        out = []
        for finding in findings or []:
            clone = dict(finding)
            if "evidence" not in clone:
                clone["evidence"] = [{"basis": "filing_index", "date": default_filed}]
            out.append(clone)
        return out

    doc = {"schema": "fundamental_forensics_state.v1",
           "generated_at": generated_at,
           "companies": {k: {**v, "findings": _norm(v.get("findings"))}
                         for k, v in companies.items()}}
    if as_of is not None:
        doc["as_of"] = as_of
    target = root / "data/fundamental_forensics/private/state.json.gz"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(gzip.compress(json.dumps(doc).encode("utf-8")))


def _write_receipt(root: Path, detail: dict | None = None, **extra):
    target = root / producer.BROAD_SEC_RECEIPT_RELATIVE
    target.parent.mkdir(parents=True, exist_ok=True)
    doc = {"run_id": "run-1",
           "change_summary": {"new_relevant_accessions": 0, "affected_issuers": 0},
           **extra}
    if detail is not None:
        doc[producer.RECEIPT_DETAIL_KEY] = detail
    target.write_text(json.dumps(doc), encoding="utf-8")


def _write_pointer(root: Path, generations: dict):
    target = root / producer.PRODUCTION_POINTER_RELATIVE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({producer.POINTER_GENERATIONS_KEY: generations}),
                      encoding="utf-8")


@pytest.fixture
def two_user_world(tmp_path):
    """u1's designated list watches SMCI (high finding + accession +
    generation); u2 has ONLY an ordinary differently-named list (the
    non-subscriber control) carrying NVDA, which is outside the FIF universe."""
    _write_state(tmp_path, {
        "SMCI": {"symbol": "SMCI", "cik": 1374360, "findings": [
            {"id": "receivables_stretch:fy25-q3", "priority": "high",
             "title_en": "Receivables outran revenue"},
            {"id": "inventory_build:fy24-q4", "priority": "medium",
             "title_en": "Inventory outran revenue"},
        ]},
        "AAPL": {"symbol": "AAPL", "cik": 320193, "findings": [
            {"id": "margin_compression:fy25-q2", "priority": "high",
             "title_en": "Margin compression"},
        ]},
    })
    _write_receipt(tmp_path, detail={"0001374360": ["0001374360-25-000011"]})
    _write_pointer(tmp_path, {"0001374360": {"generation_id": "ffprods_abc123",
                                             "admitted_at": "2026-10-11T22:00:00Z"}})
    lists = [
        {"id": "L-FIF-U1", "user_id": "u1", "name": "Filing Forensics"},
        {"id": "L-OTHER-U2", "user_id": "u2", "name": "My Watchlist"},
    ]
    symbols = [
        {"watchlist_id": "L-FIF-U1", "symbol": "SMCI"},
        {"watchlist_id": "L-OTHER-U2", "symbol": "NVDA"},
    ]
    return tmp_path, lists, symbols


# ---------------------------------------------------------------------------
# 1 + 3 + 7 + 8 — rows, no-leak, id format, payload discipline
# ---------------------------------------------------------------------------
def test_one_row_per_user_event_and_no_cross_user_rows(two_user_world, fake_pg):
    root, lists, symbols = two_user_world
    fake = fake_pg(lists=lists, symbols=symbols)
    result = producer.run(root=root, dry_run=False)
    assert result.read_state == producer.READ_OK
    rows = fake.outbox
    # u1/SMCI: high finding + new filing + generation = 3 rows. The medium
    # finding is not an event. u2 has NO designated list (its only list is
    # named differently) -> zero rows despite its ordinary watchlist, and
    # nothing from u1's list ever lands in a u2 row (gate 3a).
    assert sorted((r["user_id"], r["payload"]["ticker"]) for r in rows) == [
        ("u1", "SMCI"), ("u1", "SMCI"), ("u1", "SMCI")]
    kinds = {r["fire_event_id"].split(":")[1] for r in rows}
    assert kinds == {"new_filing", "generation", "high_finding"}
    for r in rows:
        parts = r["fire_event_id"].split(":")
        assert parts[0] == "fif"
        assert parts[1] in ("new_filing", "generation", "high_finding")
        assert parts[2] == "0001374360"           # cik10 form
        # event_ref (middle) may itself contain ':' (finding ids do); the
        # subscriber is always the FINAL segment — the owning user only.
        assert r["fire_event_id"].endswith(":u1")
        assert r["channel"] == "email" and r["status"] == "pending"
        assert r["attempts"] == 0
    assert {r["fire_event_id"] for r in rows} == {
        "fif:high_finding:0001374360:receivables_stretch:fy25-q3:u1",
        "fif:new_filing:0001374360:0001374360-25-000011:u1",
        "fif:generation:0001374360:ffprods_abc123:u1",
    }
    for r in rows:
        assert set(r["payload"]) == ALLOWED_PAYLOAD_FIELDS
        assert r["payload"]["category"] == "fif_saved_issuer"
        for field in ("ticker", "condition_plain", "subject"):
            value = r["payload"][field]
            assert value
            for token in ("falsif", "refut", "证伪"):
                assert token not in value.lower()
            assert not any(ch.isdigit() for ch in value), (
                f"digit smuggled into glance-tier field {field}: {value!r}")
        assert r["payload"]["evidence_url"] == (
            "https://www.mastermind-x.com/fundamental_forensics.html?symbol=SMCI")
    # the relayed engine title is byte-verbatim (A7), never re-scored
    relay = [r for r in rows if r["fire_event_id"].startswith("fif:high_finding:")]
    assert len(relay) == 1
    assert relay[0]["payload"]["condition_plain"] == "Receivables outran revenue"
    # synthetic alert_id: stable uuid5 per user across events
    assert len({r["alert_id"] for r in rows}) == 1


def test_symbol_on_the_designated_list_only_for_its_owner(two_user_world, fake_pg):
    """The same ticker watched by TWO users yields one row each — and a user
    whose designated list exists but does NOT carry the symbol gets nothing."""
    root, _, _ = two_user_world
    lists = [
        {"id": "L-FIF-U1", "user_id": "u1", "name": "Filing Forensics"},
        {"id": "L-FIF-U2", "user_id": "u2", "name": "Filing Forensics"},
    ]
    symbols = [
        {"watchlist_id": "L-FIF-U1", "symbol": "SMCI"},
        # u2's designated list carries only a name outside the FIF universe
        {"watchlist_id": "L-FIF-U2", "symbol": "TSLA"},
    ]
    fake = fake_pg(lists=lists, symbols=symbols)
    producer.run(root=root, dry_run=False)
    assert [r["user_id"] for r in fake.outbox] == ["u1", "u1", "u1"]


# ---------------------------------------------------------------------------
# 2 — replay inserts nothing
# ---------------------------------------------------------------------------
def test_replay_over_the_same_vintage_inserts_nothing(two_user_world, fake_pg):
    root, lists, symbols = two_user_world
    fake = fake_pg(lists=lists, symbols=symbols)
    first = producer.run(root=root, dry_run=False)
    assert first.enqueued_n == 3
    posts_before = [c for c in fake.calls if c[0] == "POST"]
    second = producer.run(root=root, dry_run=False)
    # the pre-insert SELECT saw all three ids -> zero rows planned
    assert second.planned_n == 0 and second.enqueued_n == 0
    assert [c for c in fake.calls if c[0] == "POST"] == posts_before
    assert len(fake.outbox) == 3


def test_unique_index_backstop_absorbs_a_blinded_replay(two_user_world, fake_pg, monkeypatch):
    root, lists, symbols = two_user_world
    fake = fake_pg(lists=lists, symbols=symbols)
    producer.run(root=root, dry_run=False)
    assert len(fake.outbox) == 3
    # blind the dedupe SELECT: pretend alert_outbox holds nothing
    monkeypatch.setattr(
        producer, "read_existing_fire_ids",
        lambda ids: producer.TypedRead(producer.READ_OK_ZERO, []))
    result = producer.run(root=root, dry_run=False)
    # insert-or-ignore absorbed every 409; no error, no duplicate rows
    assert result.error_class is None
    assert result.duplicate_n == 3 and result.enqueued_n == 0
    assert len(fake.outbox) == 3


# ---------------------------------------------------------------------------
# 5 + 6 — fail-soft states
# ---------------------------------------------------------------------------
def test_missing_credentials_is_typed_unavailable_zero_rows(tmp_path, monkeypatch, fake_pg):
    fake = fake_pg()  # installed, but must never be reached without creds
    monkeypatch.setattr(producer, "SUPABASE_SERVICE_ROLE_KEY", "")
    result = producer.run(root=tmp_path, dry_run=False)
    assert result.read_state == producer.READ_UNAVAILABLE
    assert result.error_class == "no_credentials"
    assert result.enqueued_n == 0 and result.planned_n == 0
    assert fake.calls == []


def test_missing_table_is_typed_unavailable(two_user_world, monkeypatch):
    root, _, _ = two_user_world

    def _absent(method, path, body=None, prefer=None, timeout=6):
        raise _Http404()

    monkeypatch.setattr(producer, "SUPABASE_SERVICE_ROLE_KEY", "test-key")
    monkeypatch.setattr(producer, "_pg", _absent)
    result = producer.run(root=root, dry_run=False)
    assert result.read_state == producer.READ_UNAVAILABLE
    assert result.error_class == "table_absent"
    assert result.enqueued_n == 0


def test_missing_inputs_is_zero_events_not_an_error(fake_pg, tmp_path):
    # no private state, no receipt, no pointer at all
    fake = fake_pg(lists=[{"id": "L", "user_id": "u1", "name": "Filing Forensics"}],
                   symbols=[{"watchlist_id": "L", "symbol": "SMCI"}])
    result = producer.run(root=tmp_path, dry_run=False)
    assert result.outcome == "ok"
    assert result.enqueued_n == 0 and result.planned_n == 0
    assert result.state_state == producer.READ_UNAVAILABLE
    assert result.receipt_state == producer.READ_UNAVAILABLE
    assert result.pointer_state == producer.READ_UNAVAILABLE
    assert fake.outbox == []


def test_missing_generation_pointer_is_no_event_never_an_error(two_user_world, fake_pg):
    """R5: the generation trigger reads a local pointer that does not exist
    today (the real one lives in the R2 vault); its absence drops exactly the
    generation events and nothing else."""
    root, lists, symbols = two_user_world
    (root / producer.PRODUCTION_POINTER_RELATIVE).unlink()
    fake = fake_pg(lists=lists, symbols=symbols)
    result = producer.run(root=root, dry_run=False)
    assert result.outcome == "ok" and result.pointer_state == producer.READ_UNAVAILABLE
    assert {r["fire_event_id"].split(":")[1] for r in fake.outbox} == {
        "new_filing", "high_finding"}


def test_receipt_without_per_cik_detail_is_no_new_filing_event(two_user_world, fake_pg):
    """The real receipt's change_summary carries counters only — that shape
    must not mint events (it cannot name an accession)."""
    root, lists, symbols = two_user_world
    (root / producer.BROAD_SEC_RECEIPT_RELATIVE).unlink()
    _write_receipt(root, detail=None,
                   change_summary={"new_relevant_accessions": 7, "affected_issuers": 3})
    fake = fake_pg(lists=lists, symbols=symbols)
    result = producer.run(root=root, dry_run=False)
    assert result.outcome == "ok"
    assert {r["fire_event_id"].split(":")[1] for r in fake.outbox} == {
        "generation", "high_finding"}


# ---------------------------------------------------------------------------
# 4 — dormancy (S1)
# ---------------------------------------------------------------------------
def _tree_snapshot(root: Path) -> set:
    out = set()
    for path in sorted(root.rglob("*")):
        rel = str(path.relative_to(root))
        if path.is_dir():
            out.add(("d", rel))
        else:
            out.add(("f", rel, path.stat().st_size))
    return out


@pytest.mark.parametrize("env_overrides", [
    {},                                                        # both unset
    {"FIF_SAVED_RESEARCH_ENABLE": "1"},                        # drain flag unset
    {"ALERT_DRAIN_ENABLE": "1"},                               # producer flag unset
    {"FIF_SAVED_RESEARCH_ENABLE": "true", "ALERT_DRAIN_ENABLE": "1"},  # non-"1"
    {"FIF_SAVED_RESEARCH_ENABLE": "0", "ALERT_DRAIN_ENABLE": "0"},     # explicit off
])
def test_dormant_runner_writes_nothing_and_never_imports_the_producer(
        tmp_path, monkeypatch, env_overrides):
    monkeypatch.delenv("FIF_SAVED_RESEARCH_ENABLE", raising=False)
    monkeypatch.delenv("ALERT_DRAIN_ENABLE", raising=False)
    for key, value in env_overrides.items():
        monkeypatch.setenv(key, value)
    monkeypatch.chdir(tmp_path)
    # If the runner imported the producer while dormant, this poisoned entry
    # would turn that import into an ImportError (None halts the import).
    monkeypatch.setitem(sys.modules, "engine.fif_saved_research_notifications", None)
    from scripts import run_fif_saved_research_notifications as runner

    before = _tree_snapshot(tmp_path)
    assert runner.main([]) == 0
    assert _tree_snapshot(tmp_path) == before


def test_dormant_runner_subprocess_exits_zero():
    env = {k: v for k, v in os.environ.items()
           if k not in ("FIF_SAVED_RESEARCH_ENABLE", "ALERT_DRAIN_ENABLE")}
    res = subprocess.run(
        [sys.executable, "-m", "scripts.run_fif_saved_research_notifications"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    assert res.returncode == 0
    assert "DORMANT" in res.stdout


def test_armed_flags_must_both_be_exactly_one(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FIF_SAVED_RESEARCH_ENABLE", "1")
    monkeypatch.setenv("ALERT_DRAIN_ENABLE", "1")
    # Armed with no creds: the producer's first typed read is unavailable and
    # the runner STILL exits 0 with zero writes (fail-soft, S5).
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://example.invalid")
    from scripts import run_fif_saved_research_notifications as runner

    before = _tree_snapshot(tmp_path)
    assert runner.main([]) == 0
    assert _tree_snapshot(tmp_path) == before


# ---------------------------------------------------------------------------
# 9 — R3: the high_finding recency gate (typed counts, as_of anchor)
# ---------------------------------------------------------------------------
_FIF_LISTS = [{"id": "L-FIF-U1", "user_id": "u1", "name": "Filing Forensics"}]
_FIF_SYMBOLS = [{"watchlist_id": "L-FIF-U1", "symbol": "SMCI"}]


def _zero_suppressed() -> dict:
    return {key: 0 for key in producer.SUPPRESSION_KEYS}


def _supp(**counts: int) -> dict:
    out = _zero_suppressed()
    out.update(counts)
    return out


def _kinds(fake: FakePg) -> list:
    return sorted(r["fire_event_id"].split(":")[1] for r in fake.outbox)


def _high_world(tmp_path: Path, filed, *, as_of="2026-10-10",
                extra_findings=()) -> Path:
    _write_state(tmp_path, {
        "SMCI": {"symbol": "SMCI", "cik": 1374360, "findings": [
            {"id": "receivables_stretch:fy25-q3", "priority": "high",
             "title_en": "Receivables outran revenue",
             "evidence": [{"basis": "filing_index", "date": filed}]},
            *extra_findings,
        ]},
    }, as_of=as_of)
    return tmp_path


@pytest.mark.parametrize("filed,days", [("2026-10-10", 0), ("2026-09-26", 14)])
def test_r3_high_finding_inside_window_emits(tmp_path, fake_pg, filed, days):
    """Both window edges emit: 0 days old and exactly 14 days old."""
    root = _high_world(tmp_path, filed)
    fake = fake_pg(lists=_FIF_LISTS, symbols=_FIF_SYMBOLS)
    result = producer.run(root=root, dry_run=False)
    assert _kinds(fake) == ["high_finding"]
    assert result.suppressed == _zero_suppressed()


def test_r3_high_finding_15_days_old_is_suppressed_with_exact_counts(
        tmp_path, fake_pg):
    root = _high_world(tmp_path, "2026-09-25")
    fake = fake_pg(lists=_FIF_LISTS, symbols=_FIF_SYMBOLS)
    result = producer.run(root=root, dry_run=False)
    assert fake.outbox == []
    # counts exact: the full typed vocabulary at zero except the one that fired
    assert result.suppressed == _supp(high_finding_outside_window=1)
    assert result.planned_n == 0 and result.enqueued_n == 0
    # the candidate was still DERIVED (it is an event the gate then refused) —
    # events_n counts pairs, the suppression count explains the difference
    assert result.events_n == 1


def test_r3_high_finding_future_dated_is_suppressed(tmp_path, fake_pg):
    root = _high_world(tmp_path, "2026-10-11")   # one day AFTER as_of
    fake = fake_pg(lists=_FIF_LISTS, symbols=_FIF_SYMBOLS)
    result = producer.run(root=root, dry_run=False)
    assert fake.outbox == []
    assert result.suppressed == _supp(high_finding_date_after_as_of=1)


@pytest.mark.parametrize("evidence", [
    [{"basis": "companyfacts_source", "date": "2026-10-05"}],  # no filing_index link
    [{"basis": "filing_index", "date": "filed 2026-10-05"}],   # not a leading YYYY-MM-DD
    [{"basis": "filing_index", "date": "2026-10-05T00:00:00Z"}],  # parses (leading form)
    [],                                                        # no evidence at all
])
def test_r3_high_finding_date_shapes(tmp_path, fake_pg, evidence):
    """Only a leading YYYY-MM-DD on a filing_index entry is a date. A full
    ISO timestamp still parses (its leading form IS the date); the others are
    missing -> suppressed, never sent, never an error."""
    root = _high_world(tmp_path, None)
    # swap the fixture's evidence for the parametrized shape
    (root / "data/fundamental_forensics/private/state.json.gz").unlink()
    _write_state(root, {
        "SMCI": {"symbol": "SMCI", "cik": 1374360, "findings": [
            {"id": "receivables_stretch:fy25-q3", "priority": "high",
             "title_en": "Receivables outran revenue", "evidence": evidence}]},
    })
    fake = fake_pg(lists=_FIF_LISTS, symbols=_FIF_SYMBOLS)
    result = producer.run(root=root, dry_run=False)
    if evidence and evidence[0].get("date") == "2026-10-05T00:00:00Z":
        assert _kinds(fake) == ["high_finding"]
        assert result.suppressed == _zero_suppressed()
    else:
        assert fake.outbox == []
        assert result.suppressed == _supp(high_finding_date_missing=1)


def test_r3_missing_as_of_suppresses_all_high_findings_but_other_kinds_emit(
        tmp_path, fake_pg):
    root = _high_world(tmp_path, "2026-10-05", as_of=None)
    _write_receipt(root, detail={"0001374360": ["0001374360-25-000011"]})
    _write_pointer(root, {"0001374360": {"generation_id": "ffprods_abc123",
                                         "admitted_at": "2026-10-11T22:00:00Z"}})
    fake = fake_pg(lists=_FIF_LISTS, symbols=_FIF_SYMBOLS)
    result = producer.run(root=root, dry_run=False)
    assert _kinds(fake) == ["generation", "new_filing"]   # high_finding gone
    assert result.suppressed == _supp(high_finding_as_of_missing=1)


def test_r3_counts_are_per_candidate_and_payload_carries_event_date(
        tmp_path, fake_pg):
    """Two high findings on one watched issuer: one inside the window, one
    40 days stale — one row, one typed suppression, and the row's payload
    records the finding date it was judged by."""
    root = _high_world(
        tmp_path, "2026-10-05",
        extra_findings=[{"id": "inventory_build:fy24-q4", "priority": "high",
                         "title_en": "Inventory outran revenue",
                         "evidence": [{"basis": "filing_index",
                                       "date": "2026-08-31"}]}],
    )
    fake = fake_pg(lists=_FIF_LISTS, symbols=_FIF_SYMBOLS)
    result = producer.run(root=root, dry_run=False)
    assert _kinds(fake) == ["high_finding"]
    assert result.suppressed == _supp(high_finding_outside_window=1)
    assert result.events_n == 2 and result.enqueued_n == 1
    row = fake.outbox[0]
    assert row["fire_event_id"] == (
        "fif:high_finding:0001374360:receivables_stretch:fy25-q3:u1")
    assert row["payload"]["event_date"] == "2026-10-05"


def test_r3_payload_event_date_is_none_for_kinds_without_one(two_user_world,
                                                             fake_pg):
    root, lists, symbols = two_user_world
    fake = fake_pg(lists=lists, symbols=symbols)
    producer.run(root=root, dry_run=False)
    by_kind = {r["fire_event_id"].split(":")[1]: r for r in fake.outbox}
    assert by_kind["high_finding"]["payload"]["event_date"] == "2026-10-05"
    assert by_kind["new_filing"]["payload"]["event_date"] is None
    assert by_kind["generation"]["payload"]["event_date"] is None


def test_r3_runner_summary_line_carries_the_suppressed_counts(
        monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FIF_SAVED_RESEARCH_ENABLE", "1")
    monkeypatch.setenv("ALERT_DRAIN_ENABLE", "1")
    stub = producer.ProducerResult(
        outcome="ok", read_state=producer.READ_OK, error_class=None,
        users_n=1, symbols_n=1, events_n=2, enqueued_n=1, duplicate_n=0,
        planned_n=1, state_state=producer.READ_OK,
        receipt_state=producer.READ_UNAVAILABLE,
        pointer_state=producer.READ_UNAVAILABLE,
        suppressed=_supp(high_finding_outside_window=1))
    monkeypatch.setattr(producer, "run", lambda **kw: stub)
    from scripts import run_fif_saved_research_notifications as runner

    assert runner.main([]) == 0
    line = capsys.readouterr().out
    assert "suppressed=high_finding_outside_window=1" in line
    # and the all-zero render is an explicit 0, never a missing field
    stub_zero = producer.ProducerResult(
        outcome="ok", read_state=producer.READ_OK, error_class=None,
        users_n=0, symbols_n=0, events_n=0, enqueued_n=0, duplicate_n=0,
        planned_n=0, state_state=producer.READ_OK,
        receipt_state=producer.READ_UNAVAILABLE,
        pointer_state=producer.READ_UNAVAILABLE)
    capsys.readouterr()
    monkeypatch.setattr(producer, "run", lambda **kw: stub_zero)
    assert runner.main([]) == 0
    assert "suppressed=0" in capsys.readouterr().out
