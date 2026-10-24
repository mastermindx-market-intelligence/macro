"""A39-L localhost Excel refresh proof harness (Masterplan acceptance case A39).

Serves the real FIF financial query routes on ``127.0.0.1`` only, against the
committed golden corpus, with a controllable sign-in state, then checks by
machine that a workbook saved by Excel after a Power Query refresh equals the
API receipt.

Subcommands
-----------
serve
  Binds ``127.0.0.1`` (any other ``--host`` is refused), refuses to start when
  ``FIF_FINANCIAL_DATASET_MODE`` is set to anything other than ``golden`` or
  when any environment variable whose *name* starts with ``R2_`` is present
  (names only; values are never read), forces golden mode, mints two random
  bearer tokens, writes ``<out>/tokens.json`` (mode 0600), the four filled
  ``.pq`` files (also mode 0600 — each embeds its case token through the
  template's ``BearerToken`` placeholder) and ``<out>/receipts.json``, then
  runs the ASGI server.  The tokens are never printed: not to stdout, not to
  stderr, not to a log line.

verify-workbook
  Parses a saved ``.xlsx`` with the standard library only, finds the table
  Excel loaded (through ``xl/tables/*.xml`` refs, else the first sheet that
  carries the receipt's column headers) and compares the loaded rows to the
  matching ``receipts.json`` case, cell for cell: values as canonical decimal
  text, and the source-link fields ``accession``, ``entity_id``, ``filed_at``,
  ``accepted_at``, ``recorded_at`` plus any mapping/formula digest columns the
  receipt nodes carry.  A workbook loaded through the shipped Power Query
  template carries the node columns (``cell_id`` ... ``provenance``); the
  nested ``period``/``provenance`` records are bound by ``cell_id`` (the
  canonical hash over the whole node payload) instead of by cell text.

cases
  Prints the case table (case, token kind, cutoffs, expected status) without
  tokens.

Exit codes
----------
serve
  0  the server ran and stopped cleanly; every artifact is in ``--out``.
  1  preparation failed after the refusal gates (the golden corpus does not
     serve the chosen request, no cell differs between the pinned and current
     cutoffs, an artifact could not be written, or no ASGI runner is
     importable — uvicorn is the deployment runner, see
     ``app/deploy/macro-api.service``).
  2  refusal before anything is served: ``--host`` is not ``127.0.0.1``,
     ``FIF_FINANCIAL_DATASET_MODE`` is set to anything other than ``golden``,
     an ``R2_``-prefixed variable name is present, or bad usage.
verify-workbook
  0  verdict ``match``.
  1  verdict ``mismatch`` — including a ``signed_out``/``free_tier`` workbook
     that still presents rows as a fresh success.
  2  input error: unknown ``--case``, missing or unreadable ``receipts.json``
     or workbook, a success case whose receipts entry carries no receipt, or a
     workbook whose OOXML cannot be parsed at all.
cases
  0  the case table was printed.

Golden corpus request
---------------------
The entity, metrics, periods and both cutoff pairs below were found by
calling the routes in-process against the committed golden corpus (never by
reading gold review files).  The pinned pair sees only the earlier filing;
the current pair also sees the later one, which makes at least one cell
newly visible and moves the selected source of an unchanged value.  ``serve``
re-proves both facts on every run and refuses (exit 1) if the corpus stops
serving them.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import posixpath
import re
import secrets
import stat
import sys
import zipfile
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any
from xml.etree import ElementTree as ET

REPO_ROOT = Path(__file__).resolve().parents[1]
# Direct script invocation puts scripts/ at sys.path[0]; pin the repo root ahead
# of it so the engine and app imports inside the command tree resolve here.
sys.path.insert(0, str(REPO_ROOT))
QUERY_PATH = "/api/forensics/v1/financial/query"
REVISIONS_PATH = "/api/forensics/v1/financial/revisions"
PQ_TEMPLATE_PATH = REPO_ROOT / "contracts" / "excel" / "fif_financial_query.pq"
LOOPBACK_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DATASET_MODE_ENV = "FIF_FINANCIAL_DATASET_MODE"
RECEIPTS_SCHEMA = "fif_excel_refresh_harness.receipts/v1"

# Cutoff pairs discovered by calling the routes in-process over the golden
# corpus: the earlier filing is fixture-recorded 2026-08-23T00:32:31Z and the
# later one 2026-08-23T07:02:13Z, so a recorded_at between the two sees only
# the earlier filing while both were accepted long before either source
# cutoff.
PINNED_POLICY: dict[str, str] = {
    "selection": "latest_known_as_of",
    "source_snapshot_at": "2026-08-01T00:00:00Z",
    "recorded_at": "2026-08-23T03:00:00Z",
}
CURRENT_POLICY: dict[str, str] = {
    "selection": "latest_known_as_of",
    "source_snapshot_at": "2026-09-20T00:00:00Z",
    "recorded_at": "2026-09-20T00:00:00Z",
}
REQUEST_METRICS: tuple[str, ...] = ("revenue", "total_assets")
REQUEST_PERIODS: tuple[dict[str, Any], ...] = (
    {
        "kind": "duration",
        "start": "2026-03-29",
        "end": "2026-06-27",
        "label": "FY2026Q3",
    },
    {
        "kind": "instant",
        "start": None,
        "end": "2025-09-27",
        "label": "FY2025-09-27",
    },
)

CASE_ORDER = ("pinned", "current", "signed_out", "free_tier")
CASE_TOKEN_KIND = {
    "pinned": "full",
    "current": "full",
    "signed_out": "none (empty bearer)",
    "free_tier": "free",
}
CASE_POLICY = {
    "pinned": PINNED_POLICY,
    "current": CURRENT_POLICY,
    "signed_out": PINNED_POLICY,
    "free_tier": PINNED_POLICY,
}
CASE_EXPECTED_STATUS = {
    "pinned": 200,
    "current": 200,
    "signed_out": 401,
    "free_tier": 403,
}
SUCCESS_CASES = ("pinned", "current")
ERROR_CASES = ("signed_out", "free_tier")

_SSML = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_OD_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

# The CSV-projection columns the checker treats as the source-link contract.
_SOURCE_LINK_COLUMNS = (
    "accession",
    "entity_id",
    "filed_at",
    "accepted_at",
    "recorded_at",
    "mapping_digest",
    "formula_digest",
)
# Columns the Power Query node family must expose for a comparable load.
_PQ_REQUIRED_COLUMNS = ("cell_id", "metric_id", "state", "value")
_PQ_TEXT_FIELDS = (
    "cell_id",
    "governance_bundle_id",
    "ticker",
    "entity_id",
    "metric_id",
    "state",
    "status",
    "value",
    "unit",
    "reason",
)


# ---------------------------------------------------------------------------
# Environment / refusal gates
# ---------------------------------------------------------------------------


def check_environment() -> str | None:
    """Names-only refusal gates. Never reads or prints a variable value."""
    mode = os.environ.get(DATASET_MODE_ENV)
    if mode is not None and mode != "golden":
        return (
            f"{DATASET_MODE_ENV} is set to an unsupported mode; "
            "this harness serves the golden corpus only"
        )
    # Presence check by name only. The value is never read, never printed.
    present = sorted(name for name in os.environ if name.startswith("R2_"))
    if present:
        return (
            "refusing to start with R2_-prefixed variables present "
            f"(names only: {', '.join(present)})"
        )
    return None


def make_tokens() -> dict[str, str]:
    """Two fresh random bearer tokens; never logged or printed."""
    return {
        "full": secrets.token_urlsafe(32),
        "free": secrets.token_urlsafe(32),
    }


# ---------------------------------------------------------------------------
# App construction (no app.main import anywhere on this path)
# ---------------------------------------------------------------------------


def golden_entity_id() -> str:
    """The committed golden issuer id, imported — never a local literal."""
    from engine.security_state import PINNED_ISSUER_ID

    return PINNED_ISSUER_ID


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    if not authorization.startswith("Bearer "):
        return None
    token = authorization[len("Bearer "):].strip()
    return token or None


def build_app(repo_root: Path, tokens: Mapping[str, str]) -> Any:
    """Fresh FastAPI app, only the forensics router, stubbed entitlement.

    ``app.main`` is never imported: the entitlement dependency is replaced
    through ``dependency_overrides`` before any request can run.
    """
    os.environ.setdefault("MACRO_REPO", str(repo_root))
    from fastapi import FastAPI, Header

    import app.forensics as forensics_api

    # The harness serves the checkout it lives in.
    forensics_api.REPO = Path(repo_root)
    # BASE wires UnavailableFinancialPacketProvider for the revisions route in
    # golden mode, which would make the revisions evidence a bare 503. Wire a
    # packet provider built from the same committed golden corpus so the
    # revisions route answers over exactly the bytes the query route serves.
    forensics_api._financial_revision_provider = _golden_packet_provider_factory(
        Path(repo_root)
    )

    def _stub_entitlement(
        authorization: str | None = Header(default=None),
    ) -> dict[str, str]:
        token = _bearer_token(authorization)
        if token is None or token not in (tokens["full"], tokens["free"]):
            raise forensics_api._private_error(
                401, "harness: missing or unknown bearer token"
            )
        if token == tokens["free"]:
            raise forensics_api._private_error(
                403, "harness: free-tier token is not entitled to financial queries"
            )
        return {"id": "harness-full-user", "scope": "site_full"}

    app = FastAPI()
    app.include_router(forensics_api.router)
    app.dependency_overrides[forensics_api.require_site_full_user] = _stub_entitlement
    return app


def _golden_packet_provider_factory(repo_root: Path) -> Any:
    """Packet provider over the committed golden corpus (cached per process)."""
    from engine.fundamental_forensics.financial_intelligence_packet import (
        EntityInput,
        PacketBuildContext,
        PacketEvidenceDigests,
        digest_builder_source,
        load_packet_schema,
    )
    from engine.fundamental_forensics.ixbrl_raw_ledger import (
        FIF3A4_LINEAGE_AVAILABLE_AT,
        GoldenAaplFinancialQueryProvider,
    )
    from engine.fundamental_forensics.revision_service import FinancialPacketDataset

    entity_id = golden_entity_id()
    query_provider = GoldenAaplFinancialQueryProvider(
        repo_root, lineage_evidence_available_at=FIF3A4_LINEAGE_AVAILABLE_AT
    )
    cached: list[Any] = []

    class _GoldenPacketProvider:
        def resolve(self, entity_id_requested: str) -> Any:
            if entity_id_requested != entity_id:
                from engine.fundamental_forensics.query_service import (
                    FinancialQueryAdmissionError,
                )

                raise FinancialQueryAdmissionError(400, "unknown entity")
            if cached:
                return cached[0]
            dataset = query_provider.resolve(entity_id)
            binding = dataset.binding
            packet_dataset = FinancialPacketDataset(
                binding=binding,
                entity=EntityInput(
                    entity_id=binding.entity_id,
                    cik=binding.cik,
                    ticker=binding.ticker,
                    name="golden-issuer-harness",
                    identity_basis="sec-cik",
                    source_entity_id=binding.source_entity_id,
                ),
                ledger=dataset.ledger,
                filing_metadata=dataset.filing_metadata,
                registry=dataset.registry,
                context=PacketBuildContext(
                    packet_builder_digest=digest_builder_source(
                        (
                            repo_root
                            / "engine"
                            / "fundamental_forensics"
                            / "financial_intelligence_packet.py"
                        ).read_bytes()
                    ),
                    packet_schema=load_packet_schema(
                        repo_root
                        / "contracts"
                        / "financial_intelligence_packet.schema.json"
                    ),
                ),
                input_digests=PacketEvidenceDigests(),
                delivery=dict(dataset.delivery),
            )
            cached.append(packet_dataset)
            return packet_dataset

    def _factory() -> Any:
        return _GoldenPacketProvider()

    return _factory


# ---------------------------------------------------------------------------
# Request / receipt handling
# ---------------------------------------------------------------------------


def request_body(policy: Mapping[str, str]) -> dict[str, Any]:
    return {
        "schema": "fundamental_forensics.financial_query_request/v1",
        "entity_id": golden_entity_id(),
        "policy": dict(policy),
        "metric_ids": list(REQUEST_METRICS),
        "periods": [dict(item) for item in REQUEST_PERIODS],
    }


def revisions_request_body(policy: Mapping[str, str]) -> dict[str, Any]:
    body = request_body(policy)
    body["schema"] = "fundamental_forensics.financial_revision_request/v1"
    return body


def serialize_request(body: Mapping[str, Any]) -> bytes:
    return json.dumps(body, separators=(",", ":")).encode("utf-8")


def _post_json(client: Any, path: str, body: bytes, token: str) -> Any:
    """POST with exactly the header the .pq template sends (Bearer may be empty)."""
    return client.post(
        path,
        content=body,
        headers={
            "content-type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )


def _root_nodes(receipt: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    roots = set(receipt.get("root_cell_ids") or ())
    return [node for node in receipt.get("nodes") or () if node.get("cell_id") in roots]


def _node_identity(node: Mapping[str, Any]) -> str:
    period = node.get("period") or {}
    return "/".join(
        str(part)
        for part in (
            node.get("metric_id"),
            period.get("kind"),
            period.get("start") or "-",
            period.get("end"),
        )
    )


def _differing_cells(
    pinned_receipt: Mapping[str, Any], current_receipt: Mapping[str, Any]
) -> list[dict[str, Any]]:
    def _snapshot(node: Mapping[str, Any]) -> dict[str, Any]:
        provenance = node.get("provenance") or {}
        return {
            "state": node.get("state"),
            "value": node.get("value"),
            "accession": provenance.get("accession"),
            "recorded_at": provenance.get("recorded_at"),
        }

    current_by_identity = {
        _node_identity(node): node for node in _root_nodes(current_receipt)
    }
    differing: list[dict[str, Any]] = []
    for pinned_node in _root_nodes(pinned_receipt):
        identity = _node_identity(pinned_node)
        current_node = current_by_identity.get(identity)
        if current_node is None:
            continue
        pinned_snapshot = _snapshot(pinned_node)
        current_snapshot = _snapshot(current_node)
        if pinned_snapshot != current_snapshot:
            differing.append(
                {
                    "metric_period": identity,
                    "pinned": pinned_snapshot,
                    "current": current_snapshot,
                }
            )
    return differing


def _revision_mentions(
    evidence: Mapping[str, Any] | None, metric_period: str
) -> bool:
    """Does a revisions-route evidence dict carry a record for this cell?"""
    if not isinstance(evidence, Mapping):
        return False
    records = evidence.get("revisions")
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        return False
    metric_id, _, rest = metric_period.partition("/")
    period_end = rest.rsplit("/", 1)[-1]
    for record in records:
        if not isinstance(record, Mapping):
            continue
        if record.get("metric_id") != metric_id:
            continue
        if (record.get("period") or {}).get("end") == period_end:
            return True
    return False


def render_pq(port: int, token: str, request_json_text: str) -> str:
    """Fill the committed template. Only placeholders move; every other byte
    is preserved. Quotes inside the request JSON are doubled for the Power
    Query M string literal."""
    template = PQ_TEMPLATE_PATH.read_text(encoding="utf-8")
    url = f"http://{LOOPBACK_HOST}:{port}{QUERY_PATH}"
    filled = template
    for placeholder, value in (
        ("<<FIF_QUERY_URL>>", url),
        ("<<FIF_BEARER_TOKEN>>", token),
        ("<<FIF_REQUEST_JSON>>", request_json_text.replace('"', '""')),
    ):
        if placeholder not in filled:
            raise RuntimeError(f"pq template lost its {placeholder} placeholder")
        filled = filled.replace(placeholder, value)
    return filled


def _write_private(path: Path, payload: bytes, mode: int) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    try:
        os.write(fd, payload)
    finally:
        os.close(fd)
    if stat.S_IMODE(os.stat(path).st_mode) != mode:
        os.chmod(path, mode)


def prepare_outputs(
    repo_root: Path,
    out_dir: Path,
    port: int,
    tokens: Mapping[str, str] | None = None,
) -> dict[str, Any] | None:
    """In-process route calls and artifact writes. Returns a token-free
    summary (with the live app under ``app``), or None after a names-only
    stderr reason when the golden corpus does not serve the request."""
    from fastapi.testclient import TestClient

    if tokens is None:
        tokens = make_tokens()
    out_dir.mkdir(parents=True, exist_ok=True)
    app = build_app(repo_root, tokens)

    query_url = f"http://{LOOPBACK_HOST}:{port}{QUERY_PATH}"
    receipts: dict[str, Any] = {
        "schema": RECEIPTS_SCHEMA,
        "query_url": query_url,
        "entity_id": golden_entity_id(),
        "cases": {},
    }
    captured: dict[str, Any] = {}

    with TestClient(app) as client:
        for case in SUCCESS_CASES:
            body = request_body(CASE_POLICY[case])
            response = _post_json(
                client, QUERY_PATH, serialize_request(body), tokens["full"]
            )
            entry: dict[str, Any] = {
                "expected_status": CASE_EXPECTED_STATUS[case],
                "request_body": body,
                "status": response.status_code,
            }
            if response.status_code != 200:
                print(
                    f"harness: {case} query returned {response.status_code}; "
                    "the golden corpus does not serve the chosen request",
                    file=sys.stderr,
                )
                return None
            envelope = response.json()
            receipt = envelope["receipt"]
            entry["query_hash"] = receipt.get("query_hash")
            entry["receipt"] = receipt
            entry["response_sha256"] = response.headers.get("X-FIF-Response-SHA256")
            receipts["cases"][case] = entry
            captured[case] = receipt

        # Determinism: the pinned case twice must be byte-identical.
        pinned_again = _post_json(
            client,
            QUERY_PATH,
            serialize_request(request_body(PINNED_POLICY)),
            tokens["full"],
        )
        if pinned_again.status_code != 200:
            print(
                f"harness: pinned repeat query returned {pinned_again.status_code}",
                file=sys.stderr,
            )
            return None
        from engine.fundamental_forensics.raw_ledger import canonical_json

        repeat_receipt = pinned_again.json()["receipt"]
        receipts["determinism"] = {
            "pinned_query_hash_stable": (
                repeat_receipt.get("query_hash")
                == captured["pinned"].get("query_hash")
            ),
            "pinned_nodes_canonical_bytes_identical": (
                canonical_json(repeat_receipt.get("nodes"))
                == canonical_json(captured["pinned"].get("nodes"))
            ),
        }
        if not all(receipts["determinism"].values()):
            print(
                "harness: the pinned case is not deterministic across repeats",
                file=sys.stderr,
            )
            return None

        # Revisions evidence at the same cutoffs, through the mounted route.
        revisions_evidence: dict[str, Any] = {}
        for case in SUCCESS_CASES:
            raw = serialize_request(revisions_request_body(CASE_POLICY[case]))
            response = _post_json(client, REVISIONS_PATH, raw, tokens["full"])
            evidence: dict[str, Any] = {"status": response.status_code}
            if response.status_code == 200:
                payload = response.json()
                evidence["revisions"] = payload.get("revisions")
                evidence["packet_ref"] = payload.get("packet_ref")
            else:
                evidence["detail"] = (response.json() or {}).get("detail")
            revisions_evidence[case] = evidence
        receipts["revisions_evidence"] = revisions_evidence

        for case in ERROR_CASES:
            body = request_body(CASE_POLICY[case])
            token = "" if case == "signed_out" else tokens["free"]
            response = _post_json(client, QUERY_PATH, serialize_request(body), token)
            entry = {
                "expected_status": CASE_EXPECTED_STATUS[case],
                "request_body": body,
                "status": response.status_code,
                "detail": (response.json() or {}).get("detail"),
            }
            receipts["cases"][case] = entry
            if response.status_code != CASE_EXPECTED_STATUS[case]:
                print(
                    f"harness: {case} query returned {response.status_code}, "
                    f"expected {CASE_EXPECTED_STATUS[case]}",
                    file=sys.stderr,
                )
                return None

    differing = _differing_cells(captured["pinned"], captured["current"])
    if not differing:
        print(
            "harness: no cell differs between the pinned and current cutoffs; "
            "the golden corpus no longer serves the acceptance request",
            file=sys.stderr,
        )
        return None
    gaps: list[str] = []
    revision_record_count = sum(
        len(
            revisions_evidence[case].get("revisions")
            or ()
        )
        for case in SUCCESS_CASES
        if isinstance(revisions_evidence[case].get("revisions"), list)
    )
    for item in differing:
        item["in_revisions_response"] = any(
            _revision_mentions(revisions_evidence[case], item["metric_period"])
            for case in SUCCESS_CASES
        )
        if not item["in_revisions_response"]:
            if item["pinned"]["state"] != item["current"]["state"]:
                nature = "a newly visible FILED fact in the later filing"
            else:
                nature = (
                    "the same value re-sourced to the later filing's FILED fact"
                )
            gaps.append(
                f"golden corpus: the pinned->current difference at "
                f"{item['metric_period']} (pinned "
                f"{item['pinned']['state']}/{item['pinned']['value']}/"
                f"{item['pinned']['accession']} -> current "
                f"{item['current']['state']}/{item['current']['value']}/"
                f"{item['current']['accession']}) is {nature}, not a revision_of "
                "event; the revisions route cannot carry it (revision records "
                f"observed at these cutoffs: {revision_record_count})"
            )
    receipts["differing_cells"] = differing
    receipts["gaps"] = gaps

    # tokens.json — mode 0600, never printed.
    _write_private(
        out_dir / "tokens.json",
        (json.dumps({"full": tokens["full"], "free": tokens["free"]}) + "\n").encode(
            "utf-8"
        ),
        0o600,
    )

    for case in CASE_ORDER:
        filename = f"{case}.pq"
        if case == "signed_out":
            token = ""
        elif case == "free_tier":
            token = tokens["free"]
        else:
            token = tokens["full"]
        request_text = serialize_request(request_body(CASE_POLICY[case])).decode(
            "utf-8"
        )
        # The .pq fills embed their case token (the template's BearerToken
        # placeholder), so they carry the same 0600 discipline as tokens.json.
        _write_private(
            out_dir / filename,
            render_pq(port, token, request_text).encode("utf-8"),
            0o600,
        )

    (out_dir / "receipts.json").write_text(
        json.dumps(receipts, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )

    return {
        "out_dir": str(out_dir),
        "port": port,
        "query_url": query_url,
        "query_hash": {
            case: receipts["cases"][case].get("query_hash")
            for case in SUCCESS_CASES
        },
        "differing_cells": differing,
        "revisions_status": {
            case: revisions_evidence[case]["status"] for case in SUCCESS_CASES
        },
        "gaps": gaps,
        "app": app,
    }


def print_summary(summary: Mapping[str, Any]) -> None:
    out = summary["out_dir"]
    print(f"harness out dir : {out}")
    print(f"query url       : {summary['query_url']}")
    print(f"tokens.json     : {out}/tokens.json (mode 0600; tokens never printed)")
    for case in SUCCESS_CASES:
        print(f"{case} query_hash : {summary['query_hash'][case]}")
    for item in summary["differing_cells"]:
        print(
            f"differing cell  : {item['metric_period']} "
            f"{item['pinned']['state']}/{item['pinned']['value']} -> "
            f"{item['current']['state']}/{item['current']['value']}"
        )
    print(
        "revisions status: "
        + ", ".join(
            f"{case}={summary['revisions_status'][case]}" for case in SUCCESS_CASES
        )
    )
    for gap in summary["gaps"]:
        print(f"GAP             : {gap}", file=sys.stderr)
    print(
        "paste per case  : pinned.pq / current.pq / signed_out.pq / free_tier.pq"
    )


# ---------------------------------------------------------------------------
# Workbook parsing (stdlib only)
# ---------------------------------------------------------------------------


def _col_index(letters: str) -> int:
    index = 0
    for ch in letters:
        index = index * 26 + (ord(ch.upper()) - 64)
    return index


def _col_name(index: int) -> str:
    name = ""
    remaining = index
    while remaining:
        remaining, rem = divmod(remaining - 1, 26)
        name = chr(65 + rem) + name
    return name


def _parse_ref(ref: str) -> tuple[int, int, int, int] | None:
    match = re.fullmatch(r"([A-Za-z]+)(\d+):([A-Za-z]+)(\d+)", ref or "")
    if match is None:
        return None
    col_start, row_start, col_end, row_end = match.groups()
    return (
        int(row_start),
        _col_index(col_start),
        int(row_end),
        _col_index(col_end),
    )


def _shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for si in root.findall(f"{{{_SSML}}}si"):
        values.append("".join(t.text or "" for t in si.iter(f"{{{_SSML}}}t")))
    return values


def _cell_text(cell: ET.Element, shared: Sequence[str]) -> str:
    kind = cell.get("t")
    if kind == "inlineStr":
        return "".join(t.text or "" for t in cell.iter(f"{{{_SSML}}}t"))
    value_el = cell.find(f"{{{_SSML}}}v")
    if value_el is None or value_el.text is None:
        return ""
    if kind == "s":
        try:
            return shared[int(value_el.text)]
        except (ValueError, IndexError):
            return ""
    return value_el.text


def _sheet_grid(
    zf: zipfile.ZipFile, part: str, shared: Sequence[str]
) -> list[list[str]]:
    root = ET.fromstring(zf.read(part))
    rows: dict[int, dict[int, str]] = {}
    max_row = max_col = 0
    for row_el in root.iter(f"{{{_SSML}}}row"):
        for cell in row_el.findall(f"{{{_SSML}}}c"):
            ref = cell.get("r") or ""
            match = re.fullmatch(r"([A-Za-z]+)(\d+)", ref)
            if match is None:
                continue
            col = _col_index(match.group(1))
            row_index = int(match.group(2))
            rows.setdefault(row_index, {})[col] = _cell_text(cell, shared)
            max_row = max(max_row, row_index)
            max_col = max(max_col, col)
    grid: list[list[str]] = []
    for row_index in range(1, max_row + 1):
        cells = rows.get(row_index, {})
        grid.append([cells.get(col, "") for col in range(1, max_col + 1)])
    return grid


def _rels_by_id(zf: zipfile.ZipFile, part: str) -> dict[str, str]:
    rels_part = str(
        PurePosixPath(part).parent / "_rels" / (PurePosixPath(part).name + ".rels")
    )
    if rels_part not in zf.namelist():
        return {}
    root = ET.fromstring(zf.read(rels_part))
    out: dict[str, str] = {}
    for rel in root.findall(f"{{{_PKG_REL}}}Relationship"):
        target = rel.get("Target") or ""
        if target.startswith("/"):
            resolved = target.lstrip("/")
        else:
            resolved = posixpath.normpath(
                str(PurePosixPath(part).parent / target)
            )
        out[rel.get("Id") or ""] = resolved.replace("\\", "/")
    return out


def read_workbook_sheets(path: Path) -> list[dict[str, Any]]:
    """Every sheet with its grid and its table refs, in workbook order."""
    with zipfile.ZipFile(path) as zf:
        shared = _shared_strings(zf)
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        workbook_rels = _rels_by_id(zf, "xl/workbook.xml")
        sheets: list[dict[str, Any]] = []
        for sheet_el in workbook.iter(f"{{{_SSML}}}sheet"):
            name = sheet_el.get("name") or ""
            rid = sheet_el.get(f"{{{_OD_REL}}}id") or ""
            part = workbook_rels.get(rid, "")
            if not part or part not in zf.namelist():
                continue
            sheet_root = ET.fromstring(zf.read(part))
            table_refs: list[tuple[int, int, int, int]] = []
            for table_part_el in sheet_root.iter(f"{{{_SSML}}}tablePart"):
                table_rid = table_part_el.get(f"{{{_OD_REL}}}id") or ""
                table_part = _rels_by_id(zf, part).get(table_rid, "")
                if not table_part or table_part not in zf.namelist():
                    continue
                table_root = ET.fromstring(zf.read(table_part))
                bounds = _parse_ref(table_root.get("ref") or "")
                if bounds is not None:
                    table_refs.append(bounds)
            grid = _sheet_grid(zf, part, shared)
            sheets.append(
                {"name": name, "part": part, "grid": grid, "tables": table_refs}
            )
        return sheets


# ---------------------------------------------------------------------------
# Expected rows
# ---------------------------------------------------------------------------


def _expected_csv_rows(
    receipt: Mapping[str, Any],
) -> tuple[list[str], list[dict[str, str]]]:
    from engine.fundamental_forensics.query import MetricMatrix

    matrix = MetricMatrix.from_dict(dict(receipt))
    text = matrix.to_csv_bytes().decode("utf-8")
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return [], []
    header = rows[0]
    expected = [dict(zip(header, row)) for row in rows[1:]]
    return header, expected


def _expected_pq_rows(receipt: Mapping[str, Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for node in receipt.get("nodes") or ():
        row = {
            field: ("" if node.get(field) is None else str(node.get(field)))
            for field in _PQ_TEXT_FIELDS
        }
        out.append(row)
    return out


def _csv_identity(row: Mapping[str, str]) -> str | None:
    if row.get("metric_id") is None:
        return None
    return "/".join(
        row.get(field) or "-"
        for field in ("metric_id", "period_kind", "period_start", "period_end")
    )


def _pq_identity(row: Mapping[str, str]) -> str | None:
    return row.get("cell_id") or None


def _decimal_texts_equal(expected: str, actual: str) -> bool:
    from decimal import Decimal, InvalidOperation

    try:
        left = Decimal(expected)
        right = Decimal(actual)
    except (InvalidOperation, ValueError):
        return expected == actual
    return left == right


def _sheet_regions(sheet: Mapping[str, Any]) -> list[tuple[list[str], list[list[str]]]]:
    """(header, data rows) regions: the loaded table when one exists, else the
    whole used grid."""
    grid = sheet["grid"]
    if not grid:
        return []
    if sheet["tables"]:
        row_start, col_start, row_end, col_end = sheet["tables"][0]
        sliced = [
            row[col_start - 1 : col_end] for row in grid[row_start - 1 : row_end]
        ]
        if sliced:
            return [(sliced[0], sliced[1:])]
        return []
    return [(grid[0], grid[1:])]


def _compare_cells(
    sheet_name: str,
    header_row: Sequence[str],
    data_rows: Sequence[Sequence[str]],
    expected_rows: Sequence[Mapping[str, str]],
    identity_of: Any,
    required_columns: Sequence[str],
) -> tuple[int, list[dict[str, Any]]]:
    """Compare data rows against expected rows by identity. The ``value``
    column is compared as canonical decimal text; every other column as exact
    text. Returns (rows_compared, mismatches)."""
    column_index = {name: idx for idx, name in enumerate(header_row)}
    mismatches: list[dict[str, Any]] = []
    for column in required_columns:
        if column not in column_index:
            mismatches.append(
                {
                    "kind": "missing_column",
                    "sheet": sheet_name,
                    "column": column,
                    "expected": "present",
                    "actual": "absent",
                }
            )
    actual_by_identity: dict[str, tuple[int, list[str]]] = {}
    for row_number, row in enumerate(data_rows, start=1):
        padded = list(row) + [""] * max(0, len(header_row) - len(row))
        as_map = {
            name: (padded[idx] if idx < len(padded) else "")
            for name, idx in column_index.items()
        }
        identity = identity_of(as_map)
        if identity is None:
            continue
        if identity in actual_by_identity:
            mismatches.append(
                {
                    "kind": "duplicate_row",
                    "sheet": sheet_name,
                    "row": identity,
                    "expected": "one row",
                    "actual": "several rows",
                }
            )
            continue
        actual_by_identity[identity] = (row_number, padded)

    expected_identities = set()
    for expected in expected_rows:
        identity = identity_of(expected)
        if identity is None:
            continue
        expected_identities.add(identity)
        found = actual_by_identity.get(identity)
        if found is None:
            mismatches.append(
                {
                    "kind": "missing_row",
                    "sheet": sheet_name,
                    "row": identity,
                    "expected": "present",
                    "actual": "absent",
                }
            )
            continue
        row_number, padded = found
        for name, idx in column_index.items():
            if name not in expected:
                continue
            expected_text = expected.get(name) or ""
            actual_text = padded[idx] if idx < len(padded) else ""
            equal = (
                _decimal_texts_equal(expected_text, actual_text)
                if name == "value"
                else expected_text == actual_text
            )
            if not equal:
                mismatches.append(
                    {
                        "kind": "cell",
                        "sheet": sheet_name,
                        "ref": f"{_col_name(idx + 1)}{row_number + 1}",
                        "column": name,
                        "row": identity,
                        "expected": expected_text,
                        "actual": actual_text,
                    }
                )
    for identity in sorted(set(actual_by_identity) - expected_identities):
        mismatches.append(
            {
                "kind": "unexpected_row",
                "sheet": sheet_name,
                "row": identity,
                "expected": "absent",
                "actual": "present",
            }
        )
    return len(expected_rows), mismatches


def _classify_sheet(sheet: Mapping[str, Any]) -> str | None:
    grid = sheet["grid"]
    if not grid or not grid[0]:
        return None
    header = set(grid[0])
    # Deliberately not keyed on a source-link column: a workbook that DROPPED
    # one must classify as the csv family and be reported as a missing column,
    # not fall out of recognition.
    if {"root_cell_id", "query_hash"} <= header:
        return "csv"
    if {"cell_id", "provenance"} <= header:
        return "pq"
    return None


def _load_receipts(out_dir: Path) -> dict[str, Any] | None:
    path = out_dir / "receipts.json"
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _find_success_rows(
    sheets: Sequence[Mapping[str, Any]], pinned_receipt: Mapping[str, Any]
) -> list[dict[str, str]]:
    """Receipt-looking data rows anywhere in the workbook (either family)."""
    found: list[dict[str, str]] = []
    for sheet in sheets:
        family = _classify_sheet(sheet)
        if family is None:
            continue
        if family == "csv":
            header, expected = _expected_csv_rows(pinned_receipt)
            identities = {
                identity
                for identity in (_csv_identity(row) for row in expected)
                if identity is not None
            }
            for header_row, data_rows in _sheet_regions(sheet):
                index = {name: idx for idx, name in enumerate(header_row)}
                if not {"metric_id", "state", "value"} <= set(index):
                    continue
                for row in data_rows:
                    padded = list(row) + [""] * max(0, len(header_row) - len(row))
                    as_map = {
                        name: (padded[idx] if idx < len(padded) else "")
                        for name, idx in index.items()
                    }
                    identity = _csv_identity(as_map)
                    if identity in identities:
                        found.append({"sheet": sheet["name"], "row": identity})
                        break
                if found:
                    break
        else:
            expected = {
                row.get("cell_id") for row in _expected_pq_rows(pinned_receipt)
            }
            for header_row, data_rows in _sheet_regions(sheet):
                index = {name: idx for idx, name in enumerate(header_row)}
                if "cell_id" not in index:
                    continue
                for row in data_rows:
                    cell_id = (
                        row[index["cell_id"]]
                        if index["cell_id"] < len(row)
                        else ""
                    )
                    if cell_id in expected:
                        found.append({"sheet": sheet["name"], "row": cell_id})
                        break
                if found:
                    break
        if found:
            break
    return found


def verify_workbook(case: str, workbook: Path, out_dir: Path) -> int:
    receipts = _load_receipts(out_dir)
    if not isinstance(receipts, Mapping):
        print(
            f"verify-workbook: {out_dir / 'receipts.json'} does not exist",
            file=sys.stderr,
        )
        return 2
    cases = receipts.get("cases") or {}
    if case not in cases:
        print(
            f"verify-workbook: case {case!r} is not in "
            f"{out_dir / 'receipts.json'}",
            file=sys.stderr,
        )
        return 2
    entry = cases[case]
    if not workbook.is_file():
        print(f"verify-workbook: workbook {workbook} does not exist", file=sys.stderr)
        return 2
    try:
        sheets = read_workbook_sheets(workbook)
    except (zipfile.BadZipFile, ET.ParseError, OSError, ValueError) as exc:
        print(f"verify-workbook: cannot parse workbook: {exc}", file=sys.stderr)
        return 2

    verdict: dict[str, Any] = {
        "case": case,
        "rows_compared": 0,
        "mismatches": [],
        "verdict": "match",
    }

    if case in ERROR_CASES:
        expected_status = entry.get("expected_status")
        if entry.get("status") != expected_status or expected_status not in (401, 403):
            print(
                f"verify-workbook: receipts for {case} do not record the expected "
                "401/403 denial",
                file=sys.stderr,
            )
            return 2
        pinned_receipt = (cases.get("pinned") or {}).get("receipt")
        if not isinstance(pinned_receipt, Mapping):
            print(
                "verify-workbook: receipts carry no pinned receipt to compare "
                "cached rows against",
                file=sys.stderr,
            )
            return 2
        found = _find_success_rows(sheets, pinned_receipt)
        if found:
            verdict["mismatches"] = [
                {
                    "kind": "unexpected_success_rows",
                    "sheet": item["sheet"],
                    "row": item["row"],
                    "expected": (
                        f"no fresh-success rows behind the {expected_status} denial"
                    ),
                    "actual": "receipt-looking rows are presented as a fresh success",
                }
                for item in found
            ]
            verdict["verdict"] = "mismatch"
        _print_verdict(verdict)
        return 0 if verdict["verdict"] == "match" else 1

    receipt = entry.get("receipt")
    if not isinstance(receipt, Mapping):
        print(
            f"verify-workbook: receipts for {case} carry no receipt",
            file=sys.stderr,
        )
        return 2

    compared = 0
    mismatches: list[dict[str, Any]] = []
    matched = False
    for sheet in sheets:
        family = _classify_sheet(sheet)
        if family is None:
            continue
        matched = True
        if family == "csv":
            header, expected = _expected_csv_rows(receipt)
            required = [
                column
                for column in header
                if column in _SOURCE_LINK_COLUMNS or column in ("metric_id", "state", "value")
            ]
            for header_row, data_rows in _sheet_regions(sheet):
                count, problems = _compare_cells(
                    sheet["name"], header_row, data_rows, expected,
                    _csv_identity, required,
                )
                compared += count
                mismatches.extend(problems)
        else:
            expected = _expected_pq_rows(receipt)
            for header_row, data_rows in _sheet_regions(sheet):
                count, problems = _compare_cells(
                    sheet["name"], header_row, data_rows, expected,
                    _pq_identity, _PQ_REQUIRED_COLUMNS,
                )
                compared += count
                mismatches.extend(problems)
        break
    if not matched:
        mismatches.append(
            {
                "kind": "no_receipt_sheet",
                "expected": "a worksheet table with the receipt's column headers",
                "actual": "no sheet carries the receipt's column headers",
            }
        )
    verdict["rows_compared"] = compared
    verdict["mismatches"] = mismatches
    verdict["verdict"] = "match" if not mismatches else "mismatch"
    _print_verdict(verdict)
    return 0 if verdict["verdict"] == "match" else 1


def _print_verdict(verdict: Mapping[str, Any]) -> None:
    print(json.dumps(verdict, indent=2, sort_keys=False))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def cases_table() -> str:
    lines = [
        "case        token                source_snapshot_at   recorded_at          expected"
    ]
    for case in CASE_ORDER:
        policy = CASE_POLICY[case]
        lines.append(
            f"{case:<11} {CASE_TOKEN_KIND[case]:<20} "
            f"{policy['source_snapshot_at']:<20} {policy['recorded_at']:<20} "
            f"{CASE_EXPECTED_STATUS[case]}"
        )
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fif_excel_refresh_harness.py",
        description="A39-L localhost Excel refresh proof harness",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="serve the golden FIF routes on 127.0.0.1")
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve.add_argument("--host", default=LOOPBACK_HOST)
    serve.add_argument(
        "--out",
        required=True,
        help="directory for tokens.json, the .pq files and receipts.json",
    )

    verify = sub.add_parser("verify-workbook", help="check a saved workbook")
    verify.add_argument("--case", required=True, choices=list(CASE_ORDER))
    verify.add_argument("--workbook", required=True)
    verify.add_argument(
        "--out", required=True, help="the serve --out directory holding receipts.json"
    )

    sub.add_parser("cases", help="print the case table without tokens")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "cases":
        print(cases_table())
        return 0
    if args.command == "serve":
        if args.host != LOOPBACK_HOST:
            print(
                f"serve: refusing --host {args.host!r}; this harness binds "
                f"{LOOPBACK_HOST} only",
                file=sys.stderr,
            )
            return 2
        reason = check_environment()
        if reason is not None:
            print(f"serve: {reason}", file=sys.stderr)
            return 2
        # Force golden mode for the process (the refusal gates have passed).
        os.environ[DATASET_MODE_ENV] = "golden"
        summary = prepare_outputs(REPO_ROOT, Path(args.out), args.port)
        if summary is None:
            return 1
        app = summary.pop("app")
        print_summary(summary)
        try:
            import uvicorn  # noqa: PLC0415
        except ImportError:
            print(
                "serve: preparation complete, but no ASGI runner is importable; "
                "uvicorn is the deployment runner (app/deploy/macro-api.service)",
                file=sys.stderr,
            )
            return 1
        uvicorn.run(app, host=LOOPBACK_HOST, port=args.port)
        return 0
    return verify_workbook(args.case, Path(args.workbook), Path(args.out))


if __name__ == "__main__":
    raise SystemExit(main())
