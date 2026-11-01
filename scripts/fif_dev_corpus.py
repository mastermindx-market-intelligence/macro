#!/usr/bin/env python3
"""FIF development-corpus instrument (DEC-FIF-PACK-GENERALIZATION-DEV-CORPUS).

Pack repairs are developed against filings of issuers DISJOINT from the five
held-out issuers. This script builds and probes that corpus; it never touches
the held-out stage, labels or fixtures:

* ``contract`` resolves dev tickers through the public EDGAR ticker map and
  each issuer's submissions JSON (the same declared SEC user agent, pacing
  and bounded retry the capture tool uses — imported from it, never
  re-implemented), REFUSES any ticker or CIK that appears in the frozen
  five-issuer coverage contract (loaded at run time, no literals), and writes
  a lane-local coverage contract the EXISTING capture tool accepts. The
  ``source_rights`` / ``retained_package_law`` / ``field_denominator`` blocks
  are copied verbatim from that five-issuer shape reference; no issuer row
  value is copied.
* ``manifest`` walks a completed capture (stage bytes + the capture tool's
  per-issuer ``capture_index.json`` / ``package_manifest.json`` outputs) and
  writes the DIGEST-ONLY corpus manifest that enters git: member digests,
  admission codes, no document bytes, no text excerpts, no XBRL values.
* ``probe`` re-admits every staged accession exactly as the held-out
  evaluator's staged admission does (stage index + witness + stored members
  through the unmodified ``admit_retained_filing_package``), builds the
  packet entity/query the generic path builds, runs ``produce_pack``, and
  prints per-field ``quality_state`` counts as sorted JSON. With
  ``--assertions`` it also checks each development assertion
  (``{ticker, accession, field_id, expected_value_text, tolerance}``;
  ``expected_value_text: "not_disclosed"`` asserts a typed absence) and
  prints pass/fail per assertion.

Held-out issuers are never fetched, never labelled and never read here: the
only held-out bytes this module opens are the five-issuer contract's own
ticker/CIK rows, for the disjointness refusal.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from collectors.sec_request_pacer import SecRequestPacer
from engine.fundamental_forensics.sec_document_spine import canonical_cik
from scripts.capture_fif_issuer_packages import (
    MIN_INTERVAL_FLOOR_SECONDS,
    FetchFailure,
    IssuerRequestLog,
    PacedFetcher,
    _capture_clock,
    _resolve_sec_user_agent,
    contract_declared_reason,
    load_contract,
)

CONTRACT_ID = "fif_dev_corpus_banks_v1"
CORPUS_ID = "banks_v1"
# The contract id is derived from the corpus id; the constants above stay the
# defaults so the default output is byte-identical to the first corpus.
CORPUS_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
CONTRACT_SCHEMA = "fundamental_forensics.coverage_contract/v1"
MANIFEST_SCHEMA = "fif_dev_corpus_manifest.v1"
TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_ORIGIN = "https://data.sec.gov/submissions"
HELD_OUT_CONTRACT_PATH = (
    _ROOT / "config" / "fundamental_forensics" / "coverage" / "five_issuer_v1.json"
)
DEFAULT_STAGE_ROOT = Path("~/lanes/stage/fif-dev-banks-20261101").expanduser()
DEFAULT_SCRATCH_ROOT = Path("/tmp/fif-pk11dev-r1")
# Blocks copied verbatim from the five-issuer shape reference.
VERBATIM_CONTRACT_BLOCKS = ("source_rights", "retained_package_law", "field_denominator")
DEV_ADMISSION = "admitted"
# Assertion sentinel: the filing genuinely does not disclose the field.
NOT_DISCLOSED = "not_disclosed"


class DevCorpusError(Exception):
    """A typed dev-corpus refusal; ``code`` names the class of refusal."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


def contract_id_for(corpus_id: str) -> str:
    """The dev contract id derived from a corpus id."""
    return f"fif_dev_corpus_{corpus_id}"


def validated_corpus_id(value: str) -> str:
    """The corpus id, or a typed refusal for anything outside the id pattern."""
    if not CORPUS_ID_PATTERN.fullmatch(value or ""):
        raise DevCorpusError(
            f"corpus id must match {CORPUS_ID_PATTERN.pattern}: {value!r}",
            code="corpus_id_invalid",
        )
    return value


# ---------------------------------------------------------------------------
# Held-out disjointness (the only held-out read this module performs).
# ---------------------------------------------------------------------------


def load_held_out_exclusions(path: Path) -> tuple[frozenset[str], frozenset[str]]:
    """(tickers, cik10s) of the frozen five-issuer contract, read at run time."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping) or payload.get("schema") != CONTRACT_SCHEMA:
        raise DevCorpusError(
            f"held-out shape reference is not a coverage contract: {path}",
            code="held_out_contract_unreadable",
        )
    tickers: set[str] = set()
    ciks: set[str] = set()
    for row in payload.get("issuers") or []:
        if not isinstance(row, Mapping):
            continue
        if isinstance(row.get("ticker"), str) and row["ticker"]:
            tickers.add(row["ticker"].upper())
        if isinstance(row.get("cik"), (str, int)):
            try:
                ciks.add(canonical_cik(row["cik"]))
            except Exception:
                continue
    return frozenset(tickers), frozenset(ciks)


def _refuse_held_out_overlap(
    tickers: Sequence[str], resolved: Mapping[str, str], held_out_path: Path
) -> None:
    held_tickers, held_ciks = load_held_out_exclusions(held_out_path)
    for ticker in tickers:
        if ticker.upper() in held_tickers:
            raise DevCorpusError(
                f"ticker {ticker} is a held-out issuer; the development corpus "
                "is disjoint from the held-out split by DEC-FIF-PACK-"
                "GENERALIZATION-DEV-CORPUS",
                code=f"held_out_ticker:{ticker}",
            )
    for ticker, cik10 in resolved.items():
        if cik10 in held_ciks:
            raise DevCorpusError(
                f"ticker {ticker} resolves to held-out CIK {cik10}",
                code=f"held_out_cik:{cik10}",
            )


# ---------------------------------------------------------------------------
# Paced public-EDGAR client (contract subcommand only).
# ---------------------------------------------------------------------------


class DevCorpusClient:
    """One paced, logged, retried GET client for the contract build.

    ``get`` is the single network seam: the hermetic tests monkeypatch it and
    the real client delegates to the capture tool's ``PacedFetcher`` (its
    shared ``SecRequestPacer``, its bounded retry, its per-attempt log), so
    pacing and retry semantics are never re-implemented here.
    """

    def __init__(
        self,
        *,
        user_agent: str,
        min_interval: float = MIN_INTERVAL_FLOOR_SECONDS,
        log_path: Path,
    ) -> None:
        self._log = IssuerRequestLog(log_path)
        self._log.open()
        self._fetcher = PacedFetcher(
            SecRequestPacer(min_interval_seconds=min_interval), user_agent, self._log
        )

    def get(self, url: str) -> bytes:
        body, _last_modified = self._fetcher.get(url)
        return body

    def close(self) -> None:
        self._log.close()


def _get_json(client: DevCorpusClient, url: str, *, what: str) -> dict[str, Any]:
    raw = client.get(url)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DevCorpusError(
            f"{what} is not JSON: {url}: {exc}", code=f"fetch_unusable:{what}"
        ) from exc
    if not isinstance(payload, dict):
        raise DevCorpusError(f"{what} is not an object: {url}", code=f"fetch_unusable:{what}")
    return payload


# ---------------------------------------------------------------------------
# Issuer rows from the public ticker map + submissions JSON.
# ---------------------------------------------------------------------------


def _cik10_from_map_entry(cik_str: Any) -> str:
    try:
        return canonical_cik(str(int(cik_str)))
    except (TypeError, ValueError) as exc:
        raise DevCorpusError(
            f"ticker map row carries an unusable CIK: {cik_str!r}",
            code="ticker_map_cik_unusable",
        ) from exc


def resolve_ticker_map(
    payload: Mapping[str, Any], tickers: Sequence[str]
) -> dict[str, str]:
    """ticker -> cik10 from the SEC company_tickers map; typed refusals."""
    wanted = {ticker.upper() for ticker in tickers}
    hits: dict[str, set[str]] = {ticker: set() for ticker in wanted}
    for row in payload.values():
        if not isinstance(row, Mapping):
            continue
        ticker = row.get("ticker")
        if not isinstance(ticker, str) or ticker.upper() not in wanted:
            continue
        hits[ticker.upper()].add(_cik10_from_map_entry(row.get("cik_str")))
    resolved: dict[str, str] = {}
    for ticker in sorted(wanted):
        ciks = hits[ticker]
        if not ciks:
            raise DevCorpusError(
                f"ticker is absent from the SEC ticker map: {ticker}",
                code=f"ticker_unknown:{ticker}",
            )
        if len(ciks) > 1:
            raise DevCorpusError(
                f"ticker maps to multiple CIKs: {ticker}: {sorted(ciks)}",
                code=f"ticker_ambiguous:{ticker}",
            )
        resolved[ticker] = ciks.pop()
    return resolved


def _fiscal_year_end(submissions: Mapping[str, Any], ticker: str) -> str:
    raw = str(submissions.get("fiscalYearEnd") or "")
    digits = "".join(character for character in raw if character.isdigit())
    if len(digits) != 4 or not digits.isdigit():
        raise DevCorpusError(
            f"submissions fiscalYearEnd is unusable for {ticker}: {raw!r}",
            code="submissions_fiscal_year_end_unusable",
        )
    return f"{digits[:2]}-{digits[2:]}"


def _recent_periodic_rows(
    submissions: Mapping[str, Any], ticker: str
) -> list[dict[str, str]]:
    """Every 10-K and 10-Q row of the recent filings list, as contract rows."""
    recent = (submissions.get("filings") or {}).get("recent")
    if not isinstance(recent, Mapping):
        raise DevCorpusError(
            f"submissions JSON carries no filings.recent block: {ticker}",
            code="submissions_recent_missing",
        )
    rows: list[dict[str, str]] = []
    length = len(recent.get("accessionNumber") or [])
    for index in range(length):
        form = str(recent.get("form", [""] * length)[index])
        if form not in ("10-K", "10-Q"):
            continue
        accession = str(recent.get("accessionNumber", [""] * length)[index])
        filing_date = str(recent.get("filingDate", [""] * length)[index])
        report_date = str(recent.get("reportDate", [""] * length)[index])
        if not (accession and filing_date and report_date):
            raise DevCorpusError(
                f"submissions 10-K/10-Q row is incomplete for {ticker}: "
                f"{accession or index}",
                code="submissions_row_incomplete",
            )
        rows.append(
            {
                "accession": accession,
                "census_ref": "sec_submissions",
                "filing_date": filing_date,
                "form": form,
                "period_of_report": report_date,
                "retention_state": "candidate",
            }
        )
    if not rows:
        raise DevCorpusError(
            f"submissions recent filings carry no 10-K/10-Q rows: {ticker}",
            code="submissions_periodic_rows_empty",
        )
    return rows


def build_issuer_row(
    *,
    ticker: str,
    cik10: str,
    submissions: Mapping[str, Any],
    submissions_bytes: bytes,
    submissions_path: Path,
    captured_at: str,
    issuer_class: str,
) -> dict[str, Any]:
    """One dev-corpus issuer row in the frozen contract shape."""
    filed_tickers = {
        str(value).upper() for value in submissions.get("tickers") or []
    }
    if ticker.upper() not in filed_tickers:
        raise DevCorpusError(
            f"submissions document of CIK {cik10} does not claim ticker {ticker}",
            code="ticker_map_binding_failed",
        )
    sic = submissions.get("sic")
    if not isinstance(sic, str) or not sic.isdigit():
        raise DevCorpusError(
            f"submissions SIC is unusable for {ticker}: {sic!r}",
            code="submissions_sic_unusable",
        )
    description = submissions.get("sicDescription")
    if not isinstance(description, str) or not description:
        raise DevCorpusError(
            f"submissions sicDescription is unusable for {ticker}",
            code="submissions_sic_unusable",
        )
    name = submissions.get("name")
    if not isinstance(name, str) or not name:
        raise DevCorpusError(
            f"submissions name is unusable for {ticker}", code="submissions_name_unusable"
        )
    return {
        "ticker": ticker,
        "cik": cik10,
        "legal_name": name,
        "sic": sic,
        "sic_source": {
            "capture_path": str(submissions_path),
            "retrieved_at": captured_at,
            "sha256": hashlib.sha256(submissions_bytes).hexdigest(),
            "sic_description": description,
            "source_url": f"{SUBMISSIONS_ORIGIN}/CIK{cik10}.json",
        },
        "fiscal_year_end": _fiscal_year_end(submissions, ticker),
        "identity_binding_state": "sec_submissions_ticker_map",
        "issuer_class": issuer_class,
        "security_master_binding": {
            "issuer_id": f"DEV:{ticker}",
            "security_id": f"DEV:{ticker}:EQ",
            "listing_key": f"DEV:{ticker}",
            "issuer_cik": cik10,
            "security_state": "dev_corpus_unbound",
            "effective_at": captured_at,
        },
        "accessions": _recent_periodic_rows(submissions, ticker),
    }


def build_dev_contract(
    *,
    issuer_rows: Sequence[Mapping[str, Any]],
    captured_at: str,
    shape_reference: Mapping[str, Any],
    corpus_id: str = CORPUS_ID,
) -> dict[str, Any]:
    """The lane-local dev contract; verbatim blocks come from the shape reference."""
    contract: dict[str, Any] = {
        "schema": CONTRACT_SCHEMA,
        "contract_id": contract_id_for(corpus_id),
        "attested": False,
        "capture_basis": "dev_corpus",
        "captured_at": captured_at,
        "issuers": [dict(row) for row in issuer_rows],
    }
    for block in VERBATIM_CONTRACT_BLOCKS:
        if block not in shape_reference:
            raise DevCorpusError(
                f"shape reference carries no {block} block to copy verbatim",
                code="shape_reference_block_missing",
            )
        contract[block] = json.loads(json.dumps(shape_reference[block]))
    contract_declared_reason(contract)  # the capture tool's own gate, up front
    return contract


# ---------------------------------------------------------------------------
# manifest subcommand.
# ---------------------------------------------------------------------------


def _load_submissions_index(stage_root: Path, cik10: str) -> dict[str, Any]:
    path = stage_root / "submissions" / f"CIK{cik10}.json"
    try:
        payload = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DevCorpusError(
            f"staged submissions JSON is unreadable: {path}: {exc}",
            code="stage_submissions_unreadable",
        ) from exc
    if not isinstance(payload, dict):
        raise DevCorpusError(
            f"staged submissions JSON is not an object: {path}",
            code="stage_submissions_unreadable",
        )
    return payload


def _issuer_identity(stage_root: Path, cik10: str) -> tuple[str, str]:
    """(ticker, sic) from the staged submissions JSON of one dev issuer.

    The submissions ``tickers`` list leads with the issuer's primary common
    listing (preferred/Depositary variants follow); the first entry is the
    ticker the corpus binds, as in the coverage contract.
    """
    payload = _load_submissions_index(stage_root, cik10)
    tickers = [str(value) for value in payload.get("tickers") or []]
    if not tickers:
        raise DevCorpusError(
            f"staged submissions tickers list is empty: {cik10}",
            code="stage_submissions_tickers_unusable",
        )
    sic = payload.get("sic")
    if not isinstance(sic, str) or not sic.isdigit():
        raise DevCorpusError(
            f"staged submissions SIC is unusable: {cik10}",
            code="stage_submissions_unusable",
        )
    return tickers[0], sic


def _stage_digest(stage_dir: Path, name: str) -> str | None:
    path = stage_dir / name
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest(
    *,
    stage_root: Path,
    capture_out: Path,
    held_out_path: Path,
    corpus_id: str = CORPUS_ID,
) -> dict[str, Any]:
    """Digest-only corpus manifest over a completed capture."""
    _, held_ciks = load_held_out_exclusions(held_out_path)
    issuers: list[dict[str, Any]] = []
    captured_ats: set[str] = set()
    for cik_dir in sorted(
        path for path in capture_out.iterdir() if path.is_dir() and path.name.isdigit()
    ):
        cik10 = canonical_cik(cik_dir.name)
        if cik10 in held_ciks:
            raise DevCorpusError(
                f"capture output holds held-out CIK {cik10}",
                code=f"held_out_cik:{cik10}",
            )
        index_path = cik_dir / "capture_index.json"
        try:
            rows = json.loads(index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DevCorpusError(
                f"capture index is unreadable: {index_path}: {exc}",
                code="capture_index_unreadable",
            ) from exc
        if not isinstance(rows, list):
            raise DevCorpusError(
                f"capture index is not a list: {index_path}",
                code="capture_index_unreadable",
            )
        ticker, sic = _issuer_identity(stage_root, cik10)
        accessions: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, Mapping) or not row.get("accession"):
                continue
            accession = str(row["accession"])
            admission = (
                DEV_ADMISSION
                if row.get("admission") == "ADMITTED"
                else str(row.get("admission") or "capture_row_unknown")
            )
            entry: dict[str, Any] = {
                "accession": accession,
                "form": str(row.get("form") or ""),
                "period_of_report": str(row.get("period_of_report") or ""),
                "filing_date": "",
                "admission": admission,
                "members": {},
            }
            stage_dir = stage_root / cik10 / accession
            package_manifest_path = cik_dir / accession / "package_manifest.json"
            if package_manifest_path.is_file():
                raw = package_manifest_path.read_bytes()
                package_manifest = json.loads(raw.decode("utf-8"))
                entry["filing_date"] = str(package_manifest.get("filing_date") or "")
                entry["package_manifest_sha256"] = hashlib.sha256(raw).hexdigest()
                captured_ats.add(str(package_manifest.get("fixture_recorded_at") or ""))
                members = {
                    str(item["name"]): str(item["content_sha256"])
                    for item in package_manifest.get("members") or []
                    if isinstance(item, Mapping)
                    and item.get("state") == "stored"
                    and item.get("name")
                    and item.get("content_sha256")
                }
            else:
                members = {}
            for staged_name in ("index.json", "sec_submissions_witness.json"):
                digest = _stage_digest(stage_dir, staged_name)
                if digest is not None:
                    members[staged_name] = digest
            entry["members"] = dict(sorted(members.items()))
            accessions.append(entry)
        issuers.append(
            {
                "ticker": ticker,
                "cik10": cik10,
                "sic": sic,
                "accessions": accessions,
            }
        )
    if len(captured_ats) > 1:
        raise DevCorpusError(
            "package manifests disagree on fixture_recorded_at",
            code="capture_clock_divergent",
        )
    return {
        "schema": MANIFEST_SCHEMA,
        "corpus_id": corpus_id,
        "contract_id": contract_id_for(corpus_id),
        "held_out_disjoint": True,
        "captured_at": (captured_ats.pop() if captured_ats else ""),
        "stage_root": str(stage_root),
        "capture_out_root": str(capture_out),
        "issuers": issuers,
    }


# ---------------------------------------------------------------------------
# probe subcommand.
# ---------------------------------------------------------------------------


def admit_staged_package(
    stage_root: Path, cik10: str, accession: str, manifest: Mapping[str, Any]
) -> tuple[str, str, Any]:
    """(outcome, detail, admitted package) — the held-out staged-admission shape.

    Checks the read-only stage for every retained member BEFORE admission; the
    manifest and members are never patched to make an accession admit.
    """
    from engine.fundamental_forensics.admitted_filing_package import (
        AdmittedFilingPackageError,
        admit_retained_filing_package,
    )

    stage_dir = stage_root / cik10 / accession
    index_path = stage_dir / "index.json"
    witness_path = stage_dir / "sec_submissions_witness.json"
    if not index_path.is_file():
        return "package_unavailable", "stage_index_missing", None
    if not witness_path.is_file():
        return "package_unavailable", "stage_witness_missing", None
    members: dict[str, bytes] = {}
    for item in manifest["members"]:
        if item.get("state") != "stored":
            continue
        member_path = stage_dir / "members" / item["name"]
        if not member_path.is_file():
            return "package_unavailable", f"stage_member_missing:{item['name']}", None
        members[item["name"]] = member_path.read_bytes()
    try:
        package = admit_retained_filing_package(
            index_bytes=index_path.read_bytes(),
            manifest=manifest,
            members=members,
            witness_bytes=witness_path.read_bytes(),
            capture_recorded_at=manifest["fixture_recorded_at"],
        )
    except AdmittedFilingPackageError as exc:
        return "package_admission_refused", str(exc.code), None
    return "ADMITTED", "", package


def _entity_for(
    package_manifest: Mapping[str, Any], ticker: str, *, contract_id: str = CONTRACT_ID
) -> dict[str, str]:
    return {
        "entity_id": package_manifest["entity_id"],
        "cik": package_manifest["cik"],
        "ticker": ticker,
        "name": package_manifest["legal_name"],
        "identity_basis": f"{contract_id}:sec_submissions_ticker_map",
        "source_entity_id": package_manifest["cik"],
    }


def _query_for(package_manifest: Mapping[str, Any], pack_id: str) -> dict[str, Any]:
    return {
        "policy": "as_reported",
        "source_event_cutoff": package_manifest["source_accepted_at"],
        "system_recorded_cutoff": package_manifest["fixture_recorded_at"],
        "requested_metrics": [pack_id.lower()],
        "requested_periods": [package_manifest["period_of_report"]],
        "evaluation_mode": "historical_replay",
    }


def _assertion_id(index: int, assertion: Mapping[str, Any]) -> str:
    explicit = assertion.get("id")
    if isinstance(explicit, str) and explicit:
        return explicit
    return (
        f"{assertion.get('ticker')}:{assertion.get('accession')}:"
        f"{assertion.get('field_id')}"
    )


def _check_assertion(
    assertion: Mapping[str, Any], field_rows: Mapping[str, Mapping[str, Any]]
) -> tuple[bool, str]:
    """(passed, detail) for one dev assertion against one pack result."""
    from decimal import Decimal, InvalidOperation

    row = field_rows.get(str(assertion.get("field_id")))
    if row is None:
        return False, "field row absent from the pack result"
    expected = assertion.get("expected_value_text")
    if isinstance(expected, str) and expected == NOT_DISCLOSED:
        typed_absence = (
            row.get("value") is None and row.get("quality_state") != "valued"
        )
        return (
            typed_absence,
            f"expected typed absence, got {row.get('quality_state')} "
            f"({row.get('value')})",
        )
    if row.get("quality_state") != "valued" or row.get("value") is None:
        return False, f"expected a value, got {row.get('quality_state')}"
    try:
        observed = Decimal(str(row["value"]))
        wanted = Decimal(str(expected))
    except (InvalidOperation, TypeError) as exc:
        return False, f"unparseable numeric assertion: {exc}"
    tolerance = assertion.get("tolerance")
    bound = Decimal(str(tolerance)) if tolerance is not None else Decimal(0)
    return (
        abs(observed - wanted) <= bound,
        f"observed {observed}, expected {wanted} (tolerance {bound})",
    )


def probe_corpus(
    *,
    stage_root: Path,
    manifest_path: Path,
    pack_id: str,
    capture_out: Path | None = None,
    assertions_path: Path | None = None,
) -> dict[str, Any]:
    """Re-admit and produce one pack over every admitted dev accession."""
    from engine.fundamental_forensics.specialist_packs import PackInput, produce_pack

    corpus = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(corpus, Mapping) or corpus.get("schema") != MANIFEST_SCHEMA:
        raise DevCorpusError(
            f"not a dev-corpus manifest: {manifest_path}", code="manifest_schema_mismatch"
        )
    root = (
        capture_out
        if capture_out is not None
        else Path(str(corpus.get("capture_out_root") or ""))
    )
    assertions: list[dict[str, Any]] = []
    if assertions_path is not None:
        payload = json.loads(assertions_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise DevCorpusError(
                f"assertions file is not a list: {assertions_path}",
                code="assertions_unusable",
            )
        assertions = [dict(item) for item in payload if isinstance(item, Mapping)]

    per_field: dict[str, dict[str, int]] = {}
    per_accession: list[dict[str, Any]] = []
    assertion_rows: list[dict[str, Any]] = []
    probed = 0
    # The probed corpus names its own contract; probe never re-derives it.
    corpus_contract_id = str(corpus.get("contract_id") or CONTRACT_ID)
    for issuer in corpus.get("issuers") or []:
        cik10 = str(issuer.get("cik10") or "")
        ticker = str(issuer.get("ticker") or "")
        for accession_row in issuer.get("accessions") or []:
            accession = str(accession_row.get("accession") or "")
            if accession_row.get("admission") != DEV_ADMISSION:
                continue
            package_manifest_path = root / cik10 / accession / "package_manifest.json"
            if not package_manifest_path.is_file():
                per_accession.append(
                    {
                        "ticker": ticker,
                        "accession": accession,
                        "outcome": "package_unavailable",
                        "detail": "package_manifest_missing",
                    }
                )
                continue
            package_manifest = json.loads(
                package_manifest_path.read_text(encoding="utf-8")
            )
            outcome, detail, package = admit_staged_package(
                stage_root, cik10, accession, package_manifest
            )
            if outcome != "ADMITTED":
                per_accession.append(
                    {
                        "ticker": ticker,
                        "accession": accession,
                        "outcome": outcome,
                        "detail": detail,
                    }
                )
                continue
            result = produce_pack(
                pack_id,
                PackInput(
                    packages=(package,),
                    entity=_entity_for(
                    package_manifest, ticker, contract_id=corpus_contract_id
                ),
                    query=_query_for(package_manifest, pack_id),
                    issuer_sic=str(issuer.get("sic") or "") or None,
                    sic_source="sec_submissions",
                ),
            )
            probed += 1
            field_rows = {
                str(row["field_id"]): row for row in result.get("fields") or []
            }
            for field_id, row in sorted(field_rows.items()):
                state = str(row.get("quality_state") or "unknown")
                counts = dict(per_field.get(field_id) or {})
                counts[state] = counts.get(state, 0) + 1
                per_field[field_id] = counts
            accession_summary = {
                "ticker": ticker,
                "accession": accession,
                "form": package_manifest.get("form"),
                "period_of_report": package_manifest.get("period_of_report"),
                "outcome": "ADMITTED",
                "applicability": (result.get("applicability") or {}).get("state"),
                "fields": {
                    field_id: row.get("quality_state")
                    for field_id, row in sorted(field_rows.items())
                },
            }
            per_accession.append(accession_summary)
            for index, assertion in enumerate(assertions):
                if str(assertion.get("ticker")) != ticker or str(
                    assertion.get("accession")
                ) != accession:
                    continue
                passed, why = _check_assertion(assertion, field_rows)
                assertion_rows.append(
                    {
                        "id": _assertion_id(index, assertion),
                        "ticker": ticker,
                        "accession": accession,
                        "field_id": assertion.get("field_id"),
                        "expected_value_text": assertion.get("expected_value_text"),
                        "pass": passed,
                        "detail": why,
                    }
                )
    report: dict[str, Any] = {
        "pack": pack_id,
        "corpus_id": corpus.get("corpus_id"),
        "manifest": str(manifest_path),
        "accessions_probed": probed,
        "admitted_accessions": sum(
            1
            for issuer in corpus.get("issuers") or []
            for row in issuer.get("accessions") or []
            if row.get("admission") == DEV_ADMISSION
        ),
        "per_field": dict(sorted(per_field.items())),
        "per_accession": per_accession,
    }
    if assertions_path is not None:
        report["assertions"] = assertion_rows
        report["assertions_passed"] = sum(1 for row in assertion_rows if row["pass"])
        report["assertions_failed"] = sum(1 for row in assertion_rows if not row["pass"])
    return report


# ---------------------------------------------------------------------------
# CLI edge.
# ---------------------------------------------------------------------------


def _utc_text(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _issuer_class(sic: str) -> str:
    from engine.fundamental_forensics import detectors

    return detectors.issuer_class_for_sic(sic)


def _run_contract(args: argparse.Namespace) -> int:
    try:
        corpus_id = validated_corpus_id(args.corpus_id)
    except DevCorpusError as exc:
        print(f"dev_corpus_refusal: {exc.code}: {exc}")
        return 2
    if args.min_interval < MIN_INTERVAL_FLOOR_SECONDS:
        print(
            f"dev_corpus_refusal: min_interval_below_floor: {args.min_interval} < "
            f"{MIN_INTERVAL_FLOOR_SECONDS}"
        )
        return 2
    try:
        clock = _capture_clock(args.captured_at)
    except SystemExit as exc:
        print(f"dev_corpus_refusal: {exc}")
        return 2
    captured_at = _utc_text(clock)
    held_out_path = Path(args.held_out_contract)
    tickers = [ticker.strip().upper() for ticker in args.tickers if ticker.strip()]
    if not tickers:
        print("dev_corpus_refusal: tickers_required")
        return 2
    try:
        shape_reference = json.loads(held_out_path.read_text(encoding="utf-8"))
        # The disjointness gate runs on the SAME read as the verbatim blocks:
        # no held-out ticker or CIK can enter the dev contract.
        _refuse_held_out_overlap(tickers, {}, held_out_path)
    except DevCorpusError as exc:
        print(f"dev_corpus_refusal: {exc.code}: {exc}")
        return 2
    except (OSError, json.JSONDecodeError) as exc:
        print(f"dev_corpus_refusal: held_out_contract_unreadable: {held_out_path}: {exc}")
        return 2

    try:
        user_agent = _resolve_sec_user_agent()
    except Exception as exc:  # the capture tool's own refusal types
        print(f"dev_corpus_refusal: sec_user_agent_unavailable: {type(exc).__name__}: {exc}")
        return 2

    submissions_dir = Path(args.submissions_dir).expanduser()
    submissions_dir.mkdir(parents=True, exist_ok=True)
    client = DevCorpusClient(
        user_agent=user_agent,
        min_interval=args.min_interval,
        log_path=submissions_dir / "contract_request_log.jsonl",
    )
    try:
        try:
            ticker_map = _get_json(client, TICKER_MAP_URL, what="ticker_map")
        except (DevCorpusError, FetchFailure) as exc:
            code = exc.code if isinstance(exc, DevCorpusError) else "fetch_failed:ticker_map"
            print(f"dev_corpus_refusal: {code}: {exc}")
            return 2
        try:
            resolved = resolve_ticker_map(ticker_map, tickers)
        except DevCorpusError as exc:
            print(f"dev_corpus_refusal: {exc.code}: {exc}")
            return 2
        try:
            _refuse_held_out_overlap(tickers, resolved, held_out_path)
        except DevCorpusError as exc:
            print(f"dev_corpus_refusal: {exc.code}: {exc}")
            return 2
        issuer_rows: list[dict[str, Any]] = []
        for ticker in tickers:
            cik10 = resolved[ticker]
            url = f"{SUBMISSIONS_ORIGIN}/CIK{cik10}.json"
            try:
                raw = client.get(url)
            except FetchFailure as exc:
                print(f"dev_corpus_refusal: fetch_failed:submissions: {ticker}: {exc}")
                return 2
            staged = submissions_dir / f"CIK{cik10}.json"
            staged.write_bytes(raw)
            try:
                submissions = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                print(f"dev_corpus_refusal: fetch_unusable:submissions: {ticker}: {exc}")
                return 2
            try:
                row = build_issuer_row(
                    ticker=ticker,
                    cik10=cik10,
                    submissions=submissions,
                    submissions_bytes=raw,
                    submissions_path=staged,
                    captured_at=captured_at,
                    issuer_class=_issuer_class(str(submissions.get("sic") or "")),
                )
            except DevCorpusError as exc:
                print(f"dev_corpus_refusal: {exc.code}: {exc}")
                return 2
            issuer_rows.append(row)
    finally:
        client.close()

    contract = build_dev_contract(
        issuer_rows=issuer_rows,
        captured_at=captured_at,
        shape_reference=shape_reference,
        corpus_id=corpus_id,
    )
    # The capture tool must accept what this lane-local contract declares:
    # prove it with the tool's own gates before writing.
    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(contract, indent=2, sort_keys=True) + "\n"
    out_path.write_text(payload, encoding="utf-8")
    written = load_contract(out_path)
    contract_declared_reason(written)
    print(
        json.dumps(
            {
                "contract": str(out_path),
                "contract_id": contract_id_for(corpus_id),
                "issuers": [
                    {
                        "ticker": row["ticker"],
                        "cik": row["cik"],
                        "sic": row["sic"],
                        "issuer_class": row["issuer_class"],
                        "accessions": len(row["accessions"]),
                    }
                    for row in issuer_rows
                ],
            },
            sort_keys=True,
        )
    )
    return 0


def _run_manifest(args: argparse.Namespace) -> int:
    try:
        corpus_id = validated_corpus_id(args.corpus_id)
        manifest = build_manifest(
            stage_root=Path(args.stage_root).expanduser(),
            capture_out=Path(args.capture_out).expanduser(),
            held_out_path=Path(args.held_out_contract),
            corpus_id=corpus_id,
        )
    except DevCorpusError as exc:
        print(f"dev_corpus_refusal: {exc.code}: {exc}")
        return 2
    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    totals = {
        issuer["ticker"]: {
            "accessions": len(issuer["accessions"]),
            DEV_ADMISSION: sum(
                1
                for row in issuer["accessions"]
                if row["admission"] == DEV_ADMISSION
            ),
        }
        for issuer in manifest["issuers"]
    }
    print(json.dumps({"manifest": str(out_path), "issuers": totals}, sort_keys=True))
    return 0


def _run_probe(args: argparse.Namespace) -> int:
    try:
        report = probe_corpus(
            stage_root=Path(args.stage_root).expanduser(),
            manifest_path=Path(args.manifest).expanduser(),
            pack_id=args.pack,
            capture_out=(
                Path(args.capture_out).expanduser()
                if args.capture_out
                else None
            ),
            assertions_path=(
                Path(args.assertions).expanduser() if args.assertions else None
            ),
        )
    except DevCorpusError as exc:
        print(f"dev_corpus_refusal: {exc.code}: {exc}")
        return 2
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        out_path = Path(args.out).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="FIF development corpus: contract, digest-only manifest, pack probe"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    contract_parser = subparsers.add_parser(
        "contract", help="build the lane-local dev coverage contract"
    )
    contract_parser.add_argument("--tickers", nargs="+", required=True)
    contract_parser.add_argument(
        "--corpus-id",
        default=CORPUS_ID,
        help="corpus id; the contract id is derived as fif_dev_corpus_<corpus-id>",
    )
    contract_parser.add_argument("--captured-at", required=True)
    contract_parser.add_argument(
        "--out", required=True, help="lane-local contract path (never committed)"
    )
    contract_parser.add_argument(
        "--min-interval",
        type=float,
        default=MIN_INTERVAL_FLOOR_SECONDS,
        help="minimum seconds between SEC requests (floor 1.0)",
    )
    contract_parser.add_argument(
        "--submissions-dir",
        default=str(DEFAULT_STAGE_ROOT / "submissions"),
        help="where the fetched submissions JSON bytes are staged",
    )
    contract_parser.add_argument(
        "--held-out-contract",
        default=str(HELD_OUT_CONTRACT_PATH),
        help="frozen five-issuer contract whose tickers/CIKs are refused",
    )
    contract_parser.set_defaults(handler=_run_contract)

    manifest_parser = subparsers.add_parser(
        "manifest", help="write the digest-only corpus manifest"
    )
    manifest_parser.add_argument("--stage-root", required=True)
    manifest_parser.add_argument("--capture-out", required=True)
    manifest_parser.add_argument("--out", required=True)
    manifest_parser.add_argument(
        "--corpus-id",
        default=CORPUS_ID,
        help="corpus id; the contract id is derived as fif_dev_corpus_<corpus-id>",
    )
    manifest_parser.add_argument(
        "--held-out-contract", default=str(HELD_OUT_CONTRACT_PATH)
    )
    manifest_parser.set_defaults(handler=_run_manifest)

    probe_parser = subparsers.add_parser(
        "probe", help="admit staged dev accessions and run one pack"
    )
    probe_parser.add_argument("--stage-root", required=True)
    probe_parser.add_argument("--manifest", required=True)
    probe_parser.add_argument("--pack", required=True)
    probe_parser.add_argument("--assertions", default=None)
    probe_parser.add_argument(
        "--capture-out",
        default=None,
        help="override the capture output root recorded in the manifest",
    )
    probe_parser.add_argument("--out", default=None)
    probe_parser.set_defaults(handler=_run_probe)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
