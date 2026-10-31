"""Tests for scripts/evaluate_options_alpha_exact_option_outcome.py — the
read-only offline CLI adapter in front of the OA-3 exact-option ruler.

SYNTHETIC FIXTURES ONLY: every expression receipt, quote row, digest, clock,
and handoff manifest in this module is fabricated locally by these tests.
Nothing here reads production or private data, touches the network, invokes
any capture / deployment / publication surface, or imports a sibling test
module.  No fixture pretends to be a live receipt: clocks are explicit
caller-supplied values and every artifact is written into pytest's tmp tree.

Covered contract:

* the standalone script imports from ``scripts/`` via its ROOT bootstrap and
  exposes ``evaluate_input(path) -> dict`` and ``main(argv) -> int``;
* a real subprocess invocation from a foreign cwd emits the exact OA-3
  fixture JSON (one canonical line) with exit 0 for evaluated statuses;
* complete byte binding: raw SHA-256 + byte counts for expression and both
  role captures match the files on disk, and the net return is exact;
* whitespace-distinct raw bodies keep distinct hashes while yielding the
  same parsed evaluation;
* pending with a real premature exit request — and both real captures stay
  mandatory even for pending;
* malformed quote bytes evaluate ``unavailable`` (QUOTE_RESPONSE_INVALID)
  while the raw receipt stays bound;
* a well-formed but wrong upstream digest evaluates ``invalid``
  (EXPRESSION_DIGEST_MISMATCH) — the evaluator owns that verdict;
* exact manifest keysets (missing role / clock / query / raw_path / extra
  metadata), strict JSON (duplicate keys, non-finite numbers), clock and
  endpoint rejections, size bounds, and path escapes (``..``, absolute,
  symlink) are all rejected with exit 2 and concise stderr carrying no raw
  payload, filesystem path, or secret value;
* a CLI run leaves every repository source file and the handoff directory
  byte-unchanged (read-only by construction);
* the adapter source contains no network, clock, digesting, filesystem
  mutation, or subprocess machinery.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "evaluate_options_alpha_exact_option_outcome.py"
assert SCRIPT_PATH.is_file(), (
    "the OA-3 CLI adapter must be integrated at scripts/"
    "evaluate_options_alpha_exact_option_outcome.py"
)

sys.path.insert(0, str(REPO_ROOT))

from engine import options_alpha_exact_option_outcome as oa3  # noqa: E402
from engine import options_nbbo_cohort as cohort  # noqa: E402

_spec = importlib.util.spec_from_file_location("oa3_exact_option_outcome_cli", SCRIPT_PATH)
cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cli)

UTC = timezone.utc
ET = oa3.ET

# ─── Synthetic clock constants (all caller-supplied; nothing reads now()) ───

# A regular NYSE session (Thursday, full RTH).  SYNTHETIC.
ENTRY_AVAILABLE_UTC = datetime(2026, 10, 15, 14, 0, 0, tzinfo=UTC)  # 10:00 ET
ENTRY_BOUNDARY = ENTRY_AVAILABLE_UTC
ENTRY_QUERY_END = ENTRY_BOUNDARY + timedelta(seconds=oa3.ENTRY_WINDOW_SECONDS)
ENTRY_REQUEST = ENTRY_QUERY_END + timedelta(milliseconds=10)
ENTRY_RESPONSE = ENTRY_REQUEST + timedelta(seconds=1)
RETRIEVAL = datetime(2026, 10, 15, 17, 0, 0, tzinfo=UTC)
ENTRY_COMPUTED = RETRIEVAL + timedelta(seconds=1)

# The exit window binds to the admitted entry event + 60m; the synthetic
# entry quote below sits exactly on the entry boundary, so the exit boundary
# is available_at + 60m here.
EXIT_BOUNDARY = ENTRY_AVAILABLE_UTC + oa3.EXIT_HORIZON  # 15:00 UTC = 11:00 ET
EXIT_EVENT = EXIT_BOUNDARY + timedelta(seconds=5)  # synthetic exit quote instant
EXIT_QUERY_END = EXIT_BOUNDARY + timedelta(seconds=oa3.EXIT_WINDOW_SECONDS)
EXIT_REQUEST = EXIT_QUERY_END + timedelta(milliseconds=10)
EXIT_RESPONSE = EXIT_REQUEST + timedelta(seconds=1)
EXIT_COMPUTED = RETRIEVAL + timedelta(seconds=2)

# A premature (real but early) exit request: the exit window has not closed.
PREMATURE_EXIT_REQUEST = EXIT_BOUNDARY + timedelta(seconds=30)

EXPECTED_NET_RETURN = Decimal("8.107522")  # frozen ruler arithmetic on 2.30/2.50

# ─── Synthetic expression identity ───────────────────────────────────────────

EXPRESSION_ID = "oa3:expr:cli-0001"
SOURCE_CANDIDATE_ID = "oa3:cand:cli-0001"
DECISION_RECEIPT_SHA = "1" * 64
SOURCE_RULE_SHA = "2" * 64
SELECTION_FENCE_AT = "2026-10-15T13:00:00.000000Z"
DECISION_AT = "2026-10-15T13:00:00.000000Z"


def _iso(moment: datetime) -> str:
    return moment.isoformat().replace("+00:00", "Z")


def _synthetic_expression(**overrides) -> dict:
    receipt = {
        "expression_id": EXPRESSION_ID,
        "policy_version": "v1",
        "source_candidate_id": SOURCE_CANDIDATE_ID,
        "decision_receipt_sha256": DECISION_RECEIPT_SHA,
        "source_rule_digest_sha256": SOURCE_RULE_SHA,
        "selection_frozen_before_outcomes": True,
        "selection_fence_at": SELECTION_FENCE_AT,
        "root": "SOFI",
        "expiration": "2026-10-16",
        "right": "call",
        "strike": "16",
        "strike_millis": 16000,
        "occ_symbol": "SOFI  261016C00016000",
        "position": "long",
        "quantity_contracts": 1,
        "multiplier": 100,
        "standard_deliverable": True,
        "single_leg": True,
        "package": False,
        "decision_at": DECISION_AT,
        "available_at": _iso(ENTRY_AVAILABLE_UTC),
    }
    receipt.update(overrides)
    return receipt


def _canonical_digest_fields(receipt: dict) -> dict:
    """Mirror the engine's canonical immutable expression fields for the
    upstream digest binding (defensive against mutated single fields)."""

    def _opt(key: str, default: str = "") -> str:
        value = receipt.get(key)
        if isinstance(value, str):
            return value
        if value is None:
            return default
        return str(value)

    return {
        "expression_id": _opt("expression_id"),
        "policy_version": _opt("policy_version"),
        "source_candidate_id": _opt("source_candidate_id"),
        "decision_receipt_sha256": _opt("decision_receipt_sha256"),
        "source_rule_digest_sha256": _opt("source_rule_digest_sha256"),
        "selection_frozen_before_outcomes": receipt.get(
            "selection_frozen_before_outcomes", False
        ),
        "selection_fence_at": _opt("selection_fence_at"),
        "root": _opt("root"),
        "expiration": _opt("expiration"),
        "right": _opt("right"),
        "strike": _opt("strike"),
        "strike_millis": receipt.get("strike_millis", 0),
        "occ_symbol": _opt("occ_symbol"),
        "position": _opt("position"),
        "quantity_contracts": receipt.get("quantity_contracts", 0),
        "multiplier": receipt.get("multiplier", 0),
        "standard_deliverable": receipt.get("standard_deliverable", False),
        "single_leg": receipt.get("single_leg", False),
        "package": receipt.get("package", False),
        "decision_at": _opt("decision_at"),
        "available_at": _opt("available_at"),
    }


def _synthetic_expression_raw_and_digest(**overrides) -> tuple[bytes, str]:
    payload = _synthetic_expression(**overrides)
    raw = cohort.canonical_json_bytes(payload)
    digest = sha256(
        cohort.canonical_json_bytes(_canonical_digest_fields(payload))
    ).hexdigest()
    return raw, digest


def _synthetic_contract() -> dict:
    return cohort.validate_contract(
        {
            "root": "SOFI",
            "expiration": "2026-10-16",
            "right": "call",
            "strike": "16",
            "strike_millis": 16000,
            "occ_symbol": "SOFI  261016C00016000",
        }
    )


# ─── Synthetic quote rows ────────────────────────────────────────────────────


def _quote_row(
    *,
    timestamp: str,
    bid: str = "2.20",
    ask: str = "2.30",
    bid_size: int = 11,
    ask_size: int = 12,
    bid_exchange: int = 4,
    ask_exchange: int = 11,
    bid_condition: int = 50,
    ask_condition: int = 50,
    symbol: str = "SOFI",
    expiration: str = "2026-10-16",
    strike: float = 16.0,
) -> dict:
    return {
        "symbol": symbol,
        "expiration": expiration,
        "right": "call",
        "strike": strike,
        "timestamp": timestamp,
        "bid_size": bid_size,
        "ask_size": ask_size,
        "bid_exchange": bid_exchange,
        "ask_exchange": ask_exchange,
        "bid_condition": bid_condition,
        "ask_condition": ask_condition,
        "bid": bid,
        "ask": ask,
    }


def _row_at(event_at_utc: datetime, **overrides) -> dict:
    ts = event_at_utc.astimezone(ET).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
    return _quote_row(timestamp=ts, **overrides)


def _entry_rows() -> list[dict]:
    # First valid firm ask exactly at the entry boundary (10:00:00.000 ET).
    return [_row_at(ENTRY_AVAILABLE_UTC)]


def _exit_rows() -> list[dict]:
    # First valid firm bid five seconds into the exit window.
    return [_row_at(EXIT_BOUNDARY + timedelta(seconds=5), bid="2.50", ask="2.60")]


# ─── Synthetic handoff tree builder ─────────────────────────────────────────


def _role_section(
    contract: dict,
    *,
    raw_name: str,
    boundary: datetime,
    query_end: datetime,
    request: datetime,
    response: datetime,
    retrieval: datetime,
    computed: datetime,
) -> dict:
    return {
        "contract": contract,
        "boundary_at": _iso(boundary),
        "query_end_at": _iso(query_end),
        "query": cohort.source_query(
            contract=contract,
            boundary_at=boundary,
            available_at=request,
            ceiling_at=query_end,
        ),
        "raw_path": raw_name,
        "endpoint": cohort.SOURCE_ENDPOINT,
        "request_started_at": _iso(request),
        "response_observed_at": _iso(response),
        "retrieval_observed_at": _iso(retrieval),
        "computed_at": _iso(computed),
    }


def _synthetic_handoff(
    manifest_dir: Path,
    *,
    entry_raw: bytes | None = None,
    exit_raw: bytes | None = None,
    expression_raw: bytes | None = None,
    upstream_digest: str | None = None,
    exit_request: datetime | None = None,
    write_captures: bool = True,
    mutate: Callable[[dict], None] | None = None,
) -> Path:
    """Write one clearly synthetic handoff tree; return the manifest path."""

    manifest_dir.mkdir(parents=True, exist_ok=True)
    expression_bytes, digest = _synthetic_expression_raw_and_digest()
    if expression_raw is not None:
        expression_bytes = expression_raw
    if upstream_digest is not None:
        digest = upstream_digest
    entry_bytes = (
        entry_raw if entry_raw is not None else cohort.canonical_json_bytes(_entry_rows())
    )
    exit_bytes = (
        exit_raw if exit_raw is not None else cohort.canonical_json_bytes(_exit_rows())
    )
    if write_captures:
        (manifest_dir / "expression.json").write_bytes(expression_bytes)
        (manifest_dir / "entry_quotes.json").write_bytes(entry_bytes)
        (manifest_dir / "exit_quotes.json").write_bytes(exit_bytes)

    exit_request_at = exit_request if exit_request is not None else EXIT_REQUEST
    manifest = {
        "expression": {
            "raw_path": "expression.json",
            "upstream_digest_sha256": digest,
        },
        "entry": _role_section(
            _synthetic_contract(),
            raw_name="entry_quotes.json",
            boundary=ENTRY_BOUNDARY,
            query_end=ENTRY_QUERY_END,
            request=ENTRY_REQUEST,
            response=ENTRY_RESPONSE,
            retrieval=RETRIEVAL,
            computed=ENTRY_COMPUTED,
        ),
        "exit": _role_section(
            _synthetic_contract(),
            raw_name="exit_quotes.json",
            boundary=EXIT_BOUNDARY,
            query_end=EXIT_QUERY_END,
            request=exit_request_at,
            response=exit_request_at + timedelta(seconds=1),
            retrieval=RETRIEVAL,
            computed=EXIT_COMPUTED,
        ),
    }
    if mutate is not None:
        mutate(manifest)
    manifest_path = manifest_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest_path


def _handoff_digest(manifest_dir: Path) -> str:
    return json.loads((manifest_dir / "manifest.json").read_text())["expression"][
        "upstream_digest_sha256"
    ]


def _run_cli(manifest_path: Path | None, cwd: Path, *extra: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    command = [sys.executable, str(SCRIPT_PATH), *extra]
    if manifest_path is not None:
        command += ["--input", str(manifest_path)]
    return subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )


def _assert_rejected(
    proc: subprocess.CompletedProcess, protected_dir: Path, needle: str | None = None
) -> None:
    """Exit 2 with concise stderr and no stdout; no payload/path leakage."""

    assert proc.returncode == cli.EXIT_INPUT_ERROR
    assert proc.stdout == ""
    err = proc.stderr
    assert err.strip() != ""
    assert "Traceback" not in err
    for secret in (
        str(protected_dir),
        "manifest.json",
        "expression.json",
        "entry_quotes.json",
        "exit_quotes.json",
        "2.30",
        "2.50",
        '{"broken"',
    ):
        assert secret not in err, f"stderr leaked {secret!r}: {err}"
    if needle is not None:
        assert needle in err


def _assert_complete_record(
    record: dict,
    *,
    entry_bytes: bytes,
    exit_bytes: bytes,
    expression_bytes: bytes,
    digest: str,
) -> None:
    """Binding assertions against the in-process record (Decimals, datetimes)."""

    assert record["schema"] == oa3.SCHEMA
    assert record["status"] == oa3.STATUS_COMPLETE
    assert record["reason"] is None
    expected_net = cohort.net_return_pct(Decimal("2.30"), Decimal("2.50"))
    assert expected_net == EXPECTED_NET_RETURN
    assert record["net_return_pct"] == expected_net
    assert record["expression_upstream_digest_sha256"] == digest
    assert record["expression_raw_response_sha256"] == sha256(expression_bytes).hexdigest()
    assert record["expression_raw_response_bytes"] == len(expression_bytes)
    assert record["entry"]["raw_response_sha256"] == sha256(entry_bytes).hexdigest()
    assert record["entry"]["raw_response_bytes"] == len(entry_bytes)
    assert record["exit"]["raw_response_sha256"] == sha256(exit_bytes).hexdigest()
    assert record["exit"]["raw_response_bytes"] == len(exit_bytes)
    assert record["entry"]["selected"]["price"] == Decimal("2.30")
    assert record["exit"]["selected"]["price"] == Decimal("2.50")
    assert record["entry"]["selected"]["event_at"] == ENTRY_AVAILABLE_UTC
    assert record["exit"]["selected"]["event_at"] == EXIT_EVENT
    assert all(value is False for value in record["authority"].values())


def _assert_complete_json(
    parsed: dict,
    *,
    entry_bytes: bytes,
    exit_bytes: bytes,
    expression_bytes: bytes,
    digest: str,
) -> None:
    """Binding assertions against the stdout JSON (strings for the decimal /
    datetime views the encoder emits)."""

    assert parsed["schema"] == oa3.SCHEMA
    assert parsed["status"] == oa3.STATUS_COMPLETE
    assert parsed["reason"] is None
    assert parsed["net_return_pct"] == str(EXPECTED_NET_RETURN)
    assert parsed["expression_upstream_digest_sha256"] == digest
    assert parsed["expression_raw_response_sha256"] == sha256(expression_bytes).hexdigest()
    assert parsed["expression_raw_response_bytes"] == len(expression_bytes)
    assert parsed["entry"]["raw_response_sha256"] == sha256(entry_bytes).hexdigest()
    assert parsed["entry"]["raw_response_bytes"] == len(entry_bytes)
    assert parsed["exit"]["raw_response_sha256"] == sha256(exit_bytes).hexdigest()
    assert parsed["exit"]["raw_response_bytes"] == len(exit_bytes)
    assert parsed["entry"]["selected"]["price"] == "2.30"
    assert parsed["exit"]["selected"]["price"] == "2.50"
    assert datetime.fromisoformat(parsed["entry"]["selected"]["event_at"]) == ENTRY_AVAILABLE_UTC
    assert datetime.fromisoformat(parsed["exit"]["selected"]["event_at"]) == EXIT_EVENT
    assert all(value is False for value in parsed["authority"].values())


# ─── Import surface ──────────────────────────────────────────────────────────


def test_script_imports_from_scripts_dir_and_exposes_required_api(capsys) -> None:
    assert cli.REPO_ROOT == REPO_ROOT
    assert callable(cli.evaluate_input)
    assert callable(cli.main)
    assert issubclass(cli.ManifestInputError, Exception)
    assert cli.EXIT_INPUT_ERROR == 2
    assert cli.EXIT_OK == 0
    assert cli.main(["--help"]) == 0
    assert "--input" in capsys.readouterr().out


# ─── Happy path: subprocess from a foreign cwd ───────────────────────────────


def test_subprocess_from_foreign_cwd_emits_exact_fixture_json(tmp_path: Path) -> None:
    handoff = tmp_path / "handoff"
    manifest = _synthetic_handoff(handoff)
    proc = _run_cli(manifest, cwd=tmp_path)

    assert proc.returncode == cli.EXIT_OK, proc.stderr
    assert proc.stderr == ""
    lines = proc.stdout.splitlines()
    assert len(lines) == 1 and proc.stdout.endswith("\n")
    parsed = json.loads(lines[0])
    # Canonical emission: the line is the sorted compact form of its own value.
    assert lines[0] == json.dumps(
        parsed, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    )
    # The subprocess output matches the library entry point byte for byte.
    record = cli.evaluate_input(manifest)
    assert lines[0] == cli.fixture_json_bytes(record).decode("utf-8").rstrip("\n")
    _assert_complete_json(
        parsed,
        entry_bytes=(handoff / "entry_quotes.json").read_bytes(),
        exit_bytes=(handoff / "exit_quotes.json").read_bytes(),
        expression_bytes=(handoff / "expression.json").read_bytes(),
        digest=_handoff_digest(handoff),
    )


def test_evaluate_input_binds_exact_bytes_and_net_return(tmp_path: Path) -> None:
    handoff = tmp_path / "handoff"
    manifest = _synthetic_handoff(handoff)

    record = cli.evaluate_input(manifest)
    assert isinstance(record, dict)
    _assert_complete_record(
        record,
        entry_bytes=(handoff / "entry_quotes.json").read_bytes(),
        exit_bytes=(handoff / "exit_quotes.json").read_bytes(),
        expression_bytes=(handoff / "expression.json").read_bytes(),
        digest=_handoff_digest(handoff),
    )


# ─── Byte exactness under non-canonical whitespace ──────────────────────────


def test_whitespace_distinct_raw_bodies_keep_distinct_hashes(tmp_path: Path) -> None:
    canonical_entry = cohort.canonical_json_bytes(_entry_rows())
    pretty_entry = (json.dumps(_entry_rows(), indent=2) + "\n").encode("utf-8")
    assert pretty_entry != canonical_entry
    assert json.loads(pretty_entry) == json.loads(canonical_entry)

    manifest_a = _synthetic_handoff(tmp_path / "canonical")
    manifest_b = _synthetic_handoff(tmp_path / "pretty", entry_raw=pretty_entry)

    record_a = cli.evaluate_input(manifest_a)
    record_b = cli.evaluate_input(manifest_b)

    assert record_a["status"] == record_b["status"] == oa3.STATUS_COMPLETE
    assert record_a["net_return_pct"] == record_b["net_return_pct"] == EXPECTED_NET_RETURN
    assert (
        record_a["entry"]["raw_response_sha256"]
        != record_b["entry"]["raw_response_sha256"]
    )
    assert record_a["entry"]["raw_response_sha256"] == sha256(canonical_entry).hexdigest()
    assert record_b["entry"]["raw_response_sha256"] == sha256(pretty_entry).hexdigest()
    assert record_a["entry"]["raw_response_bytes"] == len(canonical_entry)
    assert record_b["entry"]["raw_response_bytes"] == len(pretty_entry)
    # The parsed payload view agrees for both byte-distinct bodies.
    assert record_a["entry"]["raw_payload_sha256"] == record_b["entry"]["raw_payload_sha256"]


# ─── Pending with a real premature exit request ─────────────────────────────


def test_subprocess_pending_with_real_premature_exit_request(tmp_path: Path) -> None:
    handoff = tmp_path / "handoff"
    manifest = _synthetic_handoff(handoff, exit_request=PREMATURE_EXIT_REQUEST)
    proc = _run_cli(manifest, cwd=tmp_path)

    assert proc.returncode == cli.EXIT_OK, proc.stderr
    parsed = json.loads(proc.stdout)
    assert parsed["status"] == oa3.STATUS_PENDING
    assert parsed["net_return_pct"] is None
    # Both real captures remain bound to the record even for pending.
    assert parsed["entry"]["raw_response_sha256"] == sha256(
        (handoff / "entry_quotes.json").read_bytes()
    ).hexdigest()
    assert parsed["exit"]["raw_response_sha256"] == sha256(
        (handoff / "exit_quotes.json").read_bytes()
    ).hexdigest()
    assert (
        parsed["exit"]["clocks"]["request_started_at"]
        == PREMATURE_EXIT_REQUEST.isoformat()
    )
    assert parsed["entry"]["selected"]["price"] == "2.30"
    # No exit outcome exists yet — the premature request leaves it unselected.
    assert parsed["exit"]["selected"] is None


def test_missing_exit_capture_is_rejected_even_when_pending(tmp_path: Path) -> None:
    handoff = tmp_path / "handoff"
    manifest = _synthetic_handoff(handoff, exit_request=PREMATURE_EXIT_REQUEST)
    (handoff / "exit_quotes.json").unlink()
    proc = _run_cli(manifest, cwd=tmp_path)
    _assert_rejected(proc, tmp_path, needle="missing or unreadable")
    assert "exit" in proc.stderr


# ─── Unavailable / invalid evaluated statuses ───────────────────────────────


def test_malformed_entry_quote_evaluates_unavailable_with_receipt(tmp_path: Path) -> None:
    malformed = b'{"broken":'
    manifest = _synthetic_handoff(tmp_path / "handoff", entry_raw=malformed)
    record = cli.evaluate_input(manifest)

    assert record["status"] == oa3.STATUS_UNAVAILABLE
    assert record["reason"] == "QUOTE_RESPONSE_INVALID"
    assert record["entry"]["parse_error"].startswith("QUOTE_RESPONSE_INVALID")
    assert record["entry"]["raw_response_sha256"] == sha256(malformed).hexdigest()
    assert record["entry"]["raw_response_bytes"] == len(malformed)
    # Evaluation stops at the entry role: the engine emits an empty exit block.
    assert record["exit"]["raw_response_sha256"] is None
    assert record["net_return_pct"] is None
    assert all(value is False for value in record["authority"].values())


def test_wellformed_wrong_upstream_digest_evaluates_invalid(tmp_path: Path) -> None:
    handoff = tmp_path / "handoff"
    manifest = _synthetic_handoff(handoff, upstream_digest="0" * 64)
    record = cli.evaluate_input(manifest)

    assert record["status"] == oa3.STATUS_INVALID
    assert record["reason"] == "EXPRESSION_DIGEST_MISMATCH"
    assert record["expression_upstream_digest_sha256"] == "0" * 64
    assert record["expression_raw_response_sha256"] == sha256(
        (handoff / "expression.json").read_bytes()
    ).hexdigest()


# ─── Exact manifest keysets ─────────────────────────────────────────────────


def _pop_nested(section: str, key: str) -> Callable[[dict], None]:
    def _mutate(manifest: dict) -> None:
        del manifest[section][key]

    return _mutate


def _put_nested(section: str, **values) -> Callable[[dict], None]:
    def _mutate(manifest: dict) -> None:
        manifest[section].update(values)

    return _mutate


def test_missing_or_extra_manifest_keys_are_rejected(tmp_path: Path) -> None:
    cases = {
        "missing-role": lambda m: m.pop("exit"),
        "missing-clock": _pop_nested("exit", "computed_at"),
        "missing-query": _pop_nested("entry", "query"),
        "missing-raw-path": _pop_nested("exit", "raw_path"),
        "extra-metadata": lambda m: m.update(notes="synthetic extra"),
        "extra-role-key": _put_nested("entry", captured_by="synthetic"),
        "extra-expression-key": _put_nested("expression", comment="synthetic"),
    }
    for name, mutate in cases.items():
        manifest = _synthetic_handoff(tmp_path / name, mutate=mutate)
        with pytest.raises(cli.ManifestInputError) as excinfo:
            cli.evaluate_input(manifest)
        message = str(excinfo.value)
        assert "keys are not exact" in message or "must be a JSON object" in message
        # Key NAMES may appear; filesystem paths may not.
        assert str(tmp_path) not in message


def test_key_rejection_via_subprocess(tmp_path: Path) -> None:
    manifest = _synthetic_handoff(tmp_path / "handoff", mutate=lambda m: m.pop("exit"))
    proc = _run_cli(manifest, cwd=tmp_path)
    _assert_rejected(proc, tmp_path, needle="missing: exit")


# ─── Path safety ────────────────────────────────────────────────────────────


def test_path_escape_and_absolute_refusals(tmp_path: Path) -> None:
    outside = tmp_path / "outside.json"
    outside.write_bytes(cohort.canonical_json_bytes(_entry_rows()))

    cases = {
        "absolute": _put_nested("entry", raw_path=str(outside)),
        "dotdot": _put_nested("entry", raw_path="../outside.json"),
    }
    for name, mutate in cases.items():
        manifest = _synthetic_handoff(tmp_path / name, mutate=mutate)
        with pytest.raises(cli.ManifestInputError) as excinfo:
            cli.evaluate_input(manifest)
        message = str(excinfo.value)
        assert "raw_path" in message
        # The refused path value itself never comes back.
        assert str(outside) not in message


def test_symlink_escape_refusal(tmp_path: Path) -> None:
    outside = tmp_path / "outside.json"
    outside.write_bytes(cohort.canonical_json_bytes(_entry_rows()))
    handoff = tmp_path / "symlink"
    manifest = _synthetic_handoff(
        handoff, mutate=_put_nested("entry", raw_path="entry_escape.json")
    )
    (handoff / "entry_escape.json").symlink_to(outside)

    proc = _run_cli(manifest, cwd=tmp_path)
    _assert_rejected(proc, tmp_path, needle="escapes the manifest directory")
    assert str(outside) not in proc.stderr


def test_missing_capture_file_is_rejected(tmp_path: Path) -> None:
    manifest = _synthetic_handoff(tmp_path / "handoff", write_captures=False)
    with pytest.raises(cli.ManifestInputError) as excinfo:
        cli.evaluate_input(manifest)
    assert "missing or unreadable" in str(excinfo.value)


# ─── Strict JSON manifest parsing ───────────────────────────────────────────


def test_duplicate_keys_and_nonfinite_manifest_json_are_rejected(tmp_path: Path) -> None:
    handoff = tmp_path / "handoff"
    _synthetic_handoff(handoff)
    sections = json.loads((handoff / "manifest.json").read_text())
    entry_text = json.dumps(sections["entry"], sort_keys=True)
    duplicate_text = (
        '{"expression": '
        + json.dumps(sections["expression"])
        + ', "entry": '
        + entry_text
        + ', "entry": '
        + entry_text
        + ', "exit": '
        + json.dumps(sections["exit"])
        + "}"
    )
    duplicate_path = handoff / "manifest_duplicate_key.json"
    duplicate_path.write_text(duplicate_text, encoding="utf-8")
    proc = _run_cli(duplicate_path, cwd=tmp_path)
    _assert_rejected(proc, tmp_path, needle="strict JSON object")

    exit_computed = sections["exit"]["computed_at"]
    assert exit_computed != sections["entry"]["computed_at"]
    manifest_text = (handoff / "manifest.json").read_text()
    nan_text = manifest_text.replace(f'"{exit_computed}"', "NaN")
    assert "NaN" in nan_text
    nan_path = handoff / "manifest_nonfinite.json"
    nan_path.write_text(nan_text, encoding="utf-8")
    proc = _run_cli(nan_path, cwd=tmp_path)
    _assert_rejected(proc, tmp_path, needle="strict JSON object")


# ─── Clock, endpoint, and query shape rejections ────────────────────────────


def test_clock_endpoint_and_query_shape_rejections(tmp_path: Path) -> None:
    cases = {
        "naive-clock": _put_nested("entry", boundary_at="2026-10-15T10:00:00"),
        "non-string-clock": _put_nested("exit", computed_at=17_000_000),
        "non-iso-clock": _put_nested(
            "exit", retrieval_observed_at="15/10/2026 17:00:00 +0000"
        ),
        "date-only-clock": _put_nested("entry", boundary_at="2026-10-15"),
        "wrong-endpoint": _put_nested(
            "entry", endpoint="https://example.invalid/v3/option/history/quote"
        ),
        "non-string-endpoint": _put_nested("exit", endpoint=3),
        "query-missing-field": lambda m: m["entry"]["query"].pop("format"),
        "query-extra-field": lambda m: m["exit"]["query"].update(page="1"),
        "uppercase-digest": _put_nested("expression", upstream_digest_sha256="A" * 64),
    }
    for name, mutate in cases.items():
        manifest = _synthetic_handoff(tmp_path / name, mutate=mutate)
        with pytest.raises(cli.ManifestInputError) as excinfo:
            cli.evaluate_input(manifest)
        assert str(tmp_path) not in str(excinfo.value)


def test_naive_clock_rejection_via_subprocess(tmp_path: Path) -> None:
    manifest = _synthetic_handoff(
        tmp_path / "handoff",
        mutate=_put_nested("entry", boundary_at="2026-10-15T10:00:00"),
    )
    proc = _run_cli(manifest, cwd=tmp_path)
    _assert_rejected(proc, tmp_path, needle="aware timezone")


# ─── Size bounds ────────────────────────────────────────────────────────────


def test_manifest_expression_and_quote_size_bounds(tmp_path: Path) -> None:
    manifest = _synthetic_handoff(tmp_path / "manifest_bound")
    manifest.write_text(
        manifest.read_text() + " " * cli.MANIFEST_MAX_BYTES, encoding="utf-8"
    )
    with pytest.raises(cli.ManifestInputError) as excinfo:
        cli.evaluate_input(manifest)
    assert "exceeds the" in str(excinfo.value)

    expression_handoff = tmp_path / "expression_bound"
    expression_manifest = _synthetic_handoff(expression_handoff)
    (expression_handoff / "expression.json").write_bytes(b"x" * (cli.EXPRESSION_MAX_BYTES + 1))
    with pytest.raises(cli.ManifestInputError) as excinfo:
        cli.evaluate_input(expression_manifest)
    assert "exceeds the" in str(excinfo.value)

    quote_handoff = tmp_path / "quote_bound"
    quote_manifest = _synthetic_handoff(quote_handoff)
    os.truncate(quote_handoff / "exit_quotes.json", cli.QUOTE_MAX_BYTES + 1)
    with pytest.raises(cli.ManifestInputError) as excinfo:
        cli.evaluate_input(quote_manifest)
    assert "exceeds the" in str(excinfo.value)


# ─── Missing manifest / missing argument ────────────────────────────────────


def test_missing_manifest_file_is_rejected(tmp_path: Path) -> None:
    proc = _run_cli(tmp_path / "nope" / "manifest.json", cwd=tmp_path)
    _assert_rejected(proc, tmp_path, needle="manifest")


def test_missing_input_argument_is_rejected(tmp_path: Path) -> None:
    proc = _run_cli(None, cwd=tmp_path)
    assert proc.returncode == cli.EXIT_INPUT_ERROR
    assert proc.stdout == ""
    assert "usage" in proc.stderr


# ─── Read-only discipline ───────────────────────────────────────────────────


def test_cli_leaves_source_files_and_manifest_dir_unchanged(tmp_path: Path) -> None:
    watched = [
        SCRIPT_PATH,
        REPO_ROOT / "engine" / "options_alpha_exact_option_outcome.py",
        REPO_ROOT / "engine" / "options_nbbo_cohort.py",
        REPO_ROOT / "engine" / "session_digest.py",
        REPO_ROOT / "lib" / "nyse_calendar.py",
    ]
    handoff = tmp_path / "handoff"
    manifest = _synthetic_handoff(handoff)

    def _snapshot() -> dict:
        state = {str(path): sha256(path.read_bytes()).hexdigest() for path in watched}
        state["manifest"] = sha256(manifest.read_bytes()).hexdigest()
        state["handoff_dir"] = sorted(
            (entry.name, entry.stat().st_size) for entry in handoff.iterdir()
        )
        return state

    before = _snapshot()
    assert _run_cli(manifest, cwd=tmp_path).returncode == cli.EXIT_OK
    assert cli.evaluate_input(manifest)["status"] == oa3.STATUS_COMPLETE
    rejection_manifest = _synthetic_handoff(
        tmp_path / "rejection_handoff", mutate=lambda m: m.pop("exit")
    )
    assert _run_cli(rejection_manifest, cwd=tmp_path).returncode == cli.EXIT_INPUT_ERROR
    assert before == _snapshot()


def test_adapter_source_has_no_network_clock_digest_write_or_subprocess() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    forbidden = (
        "import socket",
        "socket.socket",
        "import urllib",
        "urlopen(",
        "import http",
        "import requests",
        "urllib3",
        "import hashlib",
        "hashlib.",
        "sha256(",
        "datetime.now",
        "datetime.utcnow",
        "time.time(",
        "time.monotonic",
        "os.mkdir",
        "os.makedirs",
        "write_text(",
        "write_bytes(",
        "import subprocess",
        ".popen(",
    )
    for token in forbidden:
        assert token not in source, f"adapter source must not contain {token!r}"
    assert "def evaluate_input(" in source
    assert "def main(" in source
    assert "ManifestInputError" in source


def test_untrusted_extra_key_is_not_reflected_to_stderr(tmp_path: Path) -> None:
    manifest = _synthetic_handoff(
        tmp_path / 'private', mutate=lambda m: m.update({'PRIVATE_INPUT_MARKER': 'value'})
    )
    result = _run_cli(manifest, cwd=tmp_path)
    _assert_rejected(result, tmp_path)
    assert 'PRIVATE_INPUT_MARKER' not in result.stderr


def test_nul_raw_path_is_a_sanitized_input_error(tmp_path: Path) -> None:
    manifest = _synthetic_handoff(
        tmp_path / 'private', mutate=_put_nested('entry', raw_path='private\x00capture')
    )
    _assert_rejected(_run_cli(manifest, cwd=tmp_path), tmp_path)


def test_deeply_nested_manifest_is_a_sanitized_input_error(tmp_path: Path) -> None:
    manifest = tmp_path / 'manifest.json'
    manifest.write_bytes(b'{"expression":' + b'[' * 1500 + b'0' + b']' * 1500 + b'}')
    _assert_rejected(_run_cli(manifest, cwd=tmp_path), tmp_path)


# ─── ROOT pin precedence over a hostile PYTHONPATH ───────────────────────────


def test_root_pin_beats_hostile_pythonpath_decoy_engine(tmp_path: Path) -> None:
    """A foreign ``engine`` package placed earlier on PYTHONPATH must not
    hijack the adapter's imports.  The decoy plus the real repository root
    are BOTH on PYTHONPATH, so the real root is already somewhere on
    sys.path: only the unconditional ``sys.path.insert(0, REPO_ROOT)`` pin
    moves it ahead of the decoy, while the conditional "insert only when
    absent" pin leaves the decoy first and loses."""

    decoy_root = tmp_path / "decoy"
    (decoy_root / "engine").mkdir(parents=True)
    (decoy_root / "engine" / "__init__.py").write_text(
        "raise SystemExit('HIJACKED')\n", encoding="utf-8"
    )
    manifest = _synthetic_handoff(tmp_path / "handoff")

    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = os.pathsep.join([str(decoy_root), str(REPO_ROOT)])
    proc = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--input", str(manifest)],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )

    assert proc.returncode == cli.EXIT_OK, (
        f"exit {proc.returncode}; stderr: {proc.stderr!r}"
    )
    assert "HIJACKED" not in proc.stdout and "HIJACKED" not in proc.stderr
    assert proc.stderr == ""
    lines = proc.stdout.splitlines()
    assert len(lines) == 1 and proc.stdout.endswith("\n")
    parsed = json.loads(lines[0])
    assert parsed["status"] == oa3.STATUS_COMPLETE
    _assert_complete_json(
        parsed,
        entry_bytes=(tmp_path / "handoff" / "entry_quotes.json").read_bytes(),
        exit_bytes=(tmp_path / "handoff" / "exit_quotes.json").read_bytes(),
        expression_bytes=(tmp_path / "handoff" / "expression.json").read_bytes(),
        digest=_handoff_digest(tmp_path / "handoff"),
    )
