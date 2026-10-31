#!/usr/bin/env python3
"""G-SRC issuer-generic retained SEC filing-package capture (FIF seat ruling R8).

Generalises the one-time AAPL capture scripts (capture_fif3a1/3a2) into ONE
issuer-generic capture. No ticker, CIK or accession literal lives in this
file: issuers and accessions come ONLY from D0 coverage-contract rows
(``--contract``, default ``config/fundamental_forensics/coverage/
five_issuer_v1.json``), selected by ``--issuer <TICKER>`` (repeatable).

Frozen rules implemented here (G_PACK spec R5/R7/R8):

* Selection per issuer (pure, ``select_issuer_accessions``):
  - ADMISSION CANDIDATES = the two most recent 10-K rows and the two most
    recent 10-Q rows by ``filing_date`` (tie-break on accession, desc).
  - CAPTURE-ONLY extras = the 10-Q whose ``period_of_report`` is the same
    month one year before the latest 10-Q's period (year-ago comparable),
    plus every ``--extra-accession`` that is itself a D0 row of that issuer.
  - An accession not present in D0 (or belonging to an issuer outside the
    ``--issuer`` selection) is refused with a typed message and exit != 0.
* Capture clock: ``--captured-at`` (aware ISO-8601 UTC) is REQUIRED; a run
  without it is refused with ``gsrc_refusal: captured_at_required`` and the
  script never falls back to the wall clock. The manifest
  ``fixture_recorded_at`` is minted from that injected clock via
  ``mint_fixture_recorded_at`` and reused verbatim as ``capture_recorded_at``
  for self-admission. Pure helpers never read the clock.
* Fetching: stdlib urllib through ONE ``SecRequestPacer`` instance
  (``--min-interval``, default 1.0 s; values below 1.0 s are refused — this
  lane's share of a 2 req/s budget shared with another lane). Bounded retry
  on HTTP 429/503, timeout, or a status-less ``URLError`` (DNS, refused or
  reset connection): at most 3 attempts, 10 s then 30 s backoff, every
  attempt appended to the issuer's request log line-by-line (a status-less
  failure is logged as ``status: "url_error"``). Exhaustion raises
  ``FetchFailure``, recorded as a typed ``fetch_failed:<what>`` row.
* User agent: the FIF-family canonical SEC user agent,
  ``collectors.edgar_forensics._user_agent`` (``config.yml``
  ``edgar.user_agent``, the helper the FIF broad-SEC and wave-2 runners use),
  resolved once at the CLI edge. It is imported there, not at module import,
  so this stdlib-only module and its hermetic tests stay importable without
  that collector's pandas/requests dependencies; an unresolvable user agent
  is refused with ``gsrc_refusal: sec_user_agent_unavailable``.
* Interrupted runs: if anything escapes an issuer's capture loop (an
  unexpected error or an interrupt), ``capture_index.json`` is still written
  but every planned accession that produced no row is recorded as
  ``capture_incomplete:<ExceptionClass>`` and the exception propagates (exit
  != 0) — a partial index is never presented as a complete one.
* statement_roles (deterministic, NO hard-coded role URIs): candidate role
  URIs are the ``xlink:role`` values of ``presentationLink`` elements in the
  ``_pre.xml`` member whose role URI carries a ``roleType`` definition in the
  ``.xsd`` member of the form ``<digits> - Statement - <title>`` (titles
  containing "Parenthetical" are skipped). Classification by title keywords:
  income_statement matches OPERATIONS|INCOME|EARNINGS|RESULTS OF OPERATIONS
  and not COMPREHENSIVE (a combined "INCOME AND COMPREHENSIVE INCOME" title
  is allowed only when no plain income title exists); balance_sheet matches
  BALANCE SHEET|FINANCIAL POSITION|FINANCIAL CONDITION; cash_flow matches
  CASH FLOW. Exactly one candidate per kind is required, else the package's
  roles are refused with a typed code (``statement_roles_ambiguous:<kind>:
  <titles>`` or ``statement_roles_missing:<kind>``), the manifest records
  ``statement_roles: null`` and D1 self-admission is not attempted — never
  a guess. ``title_search`` is derived by one stated rule: the title with a
  single trailing parenthesised suffix removed, so
  "STATEMENTS OF OPERATIONS (Unaudited)" -> "STATEMENTS OF OPERATIONS".
* Every fully-assembled ADMISSION-CANDIDATE package (roles included) is
  self-checked with the UNMODIFIED D1 function
  ``admit_retained_filing_package`` (capture_basis="reconstruction"); its
  verdict or typed refusal code is recorded. The admission function is never
  modified to make a package pass.
* CAPTURE-ONLY rows (the year-ago 10-Q and ``--extra-accession`` vintages)
  are retained and flagged but NEVER admitted: D1 is not consulted for them,
  and their capture_index ``admission`` is the fixed marker
  ``CAPTURE_ONLY_ADMISSION`` rather than any admission outcome.
* Retained bytes stay OUTSIDE git: staged under ``--stage-root`` (default
  ``~/lanes/stage/fif-gsrc``) per package as
  ``<stage>/<cik10>/<accession>/{index.json, sec_submissions_witness.json,
  members/<name>}``. Only ``package_manifest.json`` per package plus per
  issuer ``request_log.jsonl`` and ``capture_index.json`` are written under the
  fixture output root: ``--out-root``, default
  ``tests/fixtures/fundamental_forensics/g_src`` under the repo root (every
  pre-flag caller stays byte-identical in behaviour).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import socket
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from xml.etree import ElementTree as ET

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from collectors.sec_request_pacer import SecRequestPacer
from engine.fundamental_forensics.admitted_filing_package import (
    AdmittedFilingPackageError,
    admit_retained_filing_package,
)
from engine.fundamental_forensics.sec_document_spine import (
    HARD_MAX_ARCHIVE_DOCUMENT_BYTES,
    archive_document_url,
    archive_index_url,
    canonical_cik,
)
from engine.fundamental_forensics.source_rights import (
    SourceRightsError,
    read_source_rights,
    rights_hold,
)
from engine.fundamental_forensics.statement_graph import mint_fixture_recorded_at

GOLDEN_PACKAGE_SCHEMA = "fundamental_forensics.golden_filing_package/v1"
CONTRACT_SCHEMA = "fundamental_forensics.coverage_contract/v1"
SUBMISSIONS_ORIGIN = "https://data.sec.gov/submissions"
XLINK = "http://www.w3.org/1999/xlink"
HTTP_TIMEOUT_SECONDS = 60
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = (10.0, 30.0)
RETRY_STATUS_CODES = frozenset({429, 503})
MIN_INTERVAL_FLOOR_SECONDS = 1.0
MEMBER_SUFFIX_ROLES = (
    ("primary", None),
    ("schema", ".xsd"),
    ("presentation", "_pre.xml"),
    ("calculation", "_cal.xml"),
    ("definition", "_def.xml"),
    ("label", "_lab.xml"),
)
WITNESS_FIELDS = (
    "source_url",
    "source_path",
    "accessionNumber",
    "form",
    "filingDate",
    "reportDate",
    "acceptanceDateTime",
    "primaryDocument",
)
_STATEMENT_DEFINITION_RE = re.compile(r"^\d+\s*-\s*Statement\s*-\s*(.+)$", re.IGNORECASE)
_TRAILING_PAREN_RE = re.compile(r"\s*\([^()]*\)\s*$")
_INCOME_RE = re.compile(r"OPERATIONS|INCOME|EARNINGS|RESULTS OF OPERATIONS")
_BALANCE_RE = re.compile(r"BALANCE SHEET|FINANCIAL POSITION|FINANCIAL CONDITION")
_CASH_RE = re.compile(r"CASH FLOW")
ACCESSION_PATTERN_RE = re.compile(r"\d{10}-\d{2}-\d{6}")


class SelectionError(ValueError):
    """A typed selection refusal (unknown issuer / accession not in D0)."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


class FetchFailure(RuntimeError):
    """A request that stayed failed after the bounded retry budget."""

    def __init__(self, message: str, *, status: Any) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class SelectedAccession:
    accession: str
    form: str
    filing_date: str
    period_of_report: str
    selection: str  # "admission_candidate" | "capture_only"


# capture_index ``admission`` for a capture-only row. It is a fixed marker,
# never an admission outcome: capture-only rows never reach D1.
CAPTURE_ONLY_ADMISSION = "not_admitted:capture_only"

# capture_index ``admission`` prefix for a planned accession that produced no
# row because the issuer's capture loop was interrupted; suffixed with the
# exception class name. Never an admission outcome.
CAPTURE_INCOMPLETE_PREFIX = "capture_incomplete"


# ---------------------------------------------------------------------------
# Pure selection over D0 rows.
# ---------------------------------------------------------------------------


def _by_filing_date_desc(rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (str(row.get("filing_date") or ""), str(row.get("accession") or "")),
        reverse=True,
    )


def _selected(row: Mapping[str, Any], selection: str) -> SelectedAccession:
    return SelectedAccession(
        accession=str(row["accession"]),
        form=str(row["form"]),
        filing_date=str(row["filing_date"]),
        period_of_report=str(row["period_of_report"]),
        selection=selection,
    )


def r5_admission_candidates(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[SelectedAccession, ...]:
    """The R5 admission-candidate set: the two latest 10-K and two latest 10-Q.

    Rule-only by construction: its sole input is the issuer's D0 rows, so no
    operator-supplied extra can reach it. ``select_issuer_accessions`` takes
    this set as fixed before it looks at any capture-only row.
    """
    tens = [row for row in rows if row.get("form") == "10-K"]
    tens_q = [row for row in rows if row.get("form") == "10-Q"]
    candidates = [
        _selected(row, "admission_candidate")
        for row in _by_filing_date_desc(tens)[:2] + _by_filing_date_desc(tens_q)[:2]
    ]
    return tuple(dict((item.accession, item) for item in candidates).values())


def _year_ago_comparable(
    rows: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    """The 10-Q whose period_of_report is the latest 10-Q's month, one year back."""
    tens_q = [row for row in rows if row.get("form") == "10-Q"]
    latest_ten_q = _by_filing_date_desc(tens_q)[:1]
    if not latest_ten_q:
        return None
    parts = str(latest_ten_q[0].get("period_of_report") or "").split("-")
    if not (len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit()):
        return None
    target = (int(parts[0]) - 1, int(parts[1]))
    for row in tens_q:
        q_parts = str(row.get("period_of_report") or "").split("-")
        if len(q_parts) == 3 and q_parts[0].isdigit() and q_parts[1].isdigit():
            if (int(q_parts[0]), int(q_parts[1])) == target:
                return row
    return None


def select_issuer_accessions(
    issuer_row: Mapping[str, Any],
    extra_accessions: Sequence[str] = (),
) -> list[SelectedAccession]:
    """R5 selection over one D0 issuer row. Pure; raises SelectionError.

    Admission candidates come from ``r5_admission_candidates`` alone. The
    year-ago comparable and every operator extra land in a separate
    capture-only set whose entries are built with ``selection="capture_only"``
    and never displace a candidate, so an extra cannot become an admission
    candidate: naming a candidate as an extra leaves the plan unchanged.
    """
    ticker = str(issuer_row.get("ticker") or "")
    rows = [
        row
        for row in issuer_row.get("accessions") or []
        if isinstance(row, Mapping)
    ]
    by_accession = {str(row.get("accession")): row for row in rows}
    for extra in extra_accessions:
        if extra not in by_accession:
            raise SelectionError(
                f"extra accession is not a D0 row of issuer {ticker}: {extra}",
                code="extra_accession_not_in_d0",
            )

    candidates = r5_admission_candidates(rows)
    candidate_ids = frozenset(item.accession for item in candidates)
    capture_only: dict[str, SelectedAccession] = {}
    comparable = _year_ago_comparable(rows)
    capture_rows = ([comparable] if comparable is not None else []) + [
        by_accession[extra] for extra in extra_accessions
    ]
    for row in capture_rows:
        accession = str(row["accession"])
        if accession in candidate_ids or accession in capture_only:
            continue
        capture_only[accession] = _selected(row, "capture_only")

    order = list(candidates) + list(capture_only.values())
    order.sort(key=lambda item: (item.filing_date, item.accession), reverse=True)
    order.sort(
        key=lambda item: (
            0 if item.selection == "admission_candidate" else 1,
            0 if item.form == "10-K" else 1,
        )
    )
    planned = tuple(item for item in order if item.selection == "admission_candidate")
    if {item.accession for item in planned} != candidate_ids:
        raise SelectionError(
            f"admission candidates of issuer {ticker} diverge from the R5 rule set",
            code="admission_candidates_not_rule_only",
        )
    return order


def load_contract(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != CONTRACT_SCHEMA:
        raise SelectionError(
            f"coverage contract schema mismatch: {path}", code="contract_schema_mismatch"
        )
    return payload


def contract_declared_reason(contract: Mapping[str, Any]) -> str:
    law = contract.get("retained_package_law")
    if isinstance(law, Mapping):
        reason = law.get("declared_reason")
        if isinstance(reason, str) and reason:
            return reason
    raise SelectionError(
        "coverage contract carries no retained_package_law.declared_reason",
        code="contract_declared_reason_missing",
    )


# ---------------------------------------------------------------------------
# Pure statement-role extraction.
# ---------------------------------------------------------------------------


def statement_titles_from_schema(schema_bytes: bytes) -> dict[str, str]:
    """roleURI -> statement title from ``<digits> - Statement - <title>`` roleTypes.

    Parenthetical statements are skipped. Roles whose definition does not
    carry the Statement prefix are not statement roles and never qualify.
    """
    root = ET.fromstring(schema_bytes)
    titles: dict[str, str] = {}
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag != "roleType":
            continue
        uri = el.get("roleURI")
        definition = None
        for child in el:
            if child.tag.rsplit("}", 1)[-1] == "definition":
                definition = (child.text or "").strip()
                break
        if not isinstance(uri, str) or not uri or not definition:
            continue
        match = _STATEMENT_DEFINITION_RE.match(definition)
        if match is None:
            continue
        title = match.group(1).strip()
        if "parenthetical" in title.lower():
            continue
        titles[uri] = title
    return titles


def presentation_link_roles(pre_bytes: bytes) -> list[str]:
    """Ordered, de-duplicated xlink:role values of presentationLink elements."""
    root = ET.fromstring(pre_bytes)
    seen: list[str] = []
    for el in root.iter():
        if el.tag.rsplit("}", 1)[-1] != "presentationLink":
            continue
        role = el.get(f"{{{XLINK}}}role")
        if isinstance(role, str) and role and role not in seen:
            seen.append(role)
    return seen


def _title_search(title: str) -> str:
    """One stated rule: drop a single trailing parenthesised suffix."""
    stripped = _TRAILING_PAREN_RE.sub("", title).strip()
    return stripped or title


def _kind_candidates(
    kind: str, titled: Sequence[tuple[str, str]]
) -> list[tuple[str, str]]:
    """Candidates carry the AS-FILED title; keyword matching is uppercased."""
    upper = [(uri, title, title.upper()) for uri, title in titled]
    if kind == "income_statement":
        plain = [
            (uri, title)
            for uri, title, folded in upper
            if _INCOME_RE.search(folded) and "COMPREHENSIVE" not in folded
        ]
        if plain:
            return plain
        return [
            (uri, title)
            for uri, title, folded in upper
            if _INCOME_RE.search(folded) and "COMPREHENSIVE" in folded
        ]
    if kind == "balance_sheet":
        pattern = _BALANCE_RE
    else:
        pattern = _CASH_RE
    return [(uri, title) for uri, title, folded in upper if pattern.search(folded)]


def classify_statement_roles(
    pre_bytes: bytes, schema_bytes: bytes
) -> tuple[dict[str, dict[str, str]] | None, str]:
    """Return (roles, state). roles is None with a typed state on ambiguity."""
    titles = statement_titles_from_schema(schema_bytes)
    titled = [
        (uri, titles[uri]) for uri in presentation_link_roles(pre_bytes) if uri in titles
    ]
    roles: dict[str, dict[str, str]] = {}
    failures: list[str] = []
    for kind in ("income_statement", "balance_sheet", "cash_flow"):
        candidates = _kind_candidates(kind, titled)
        if len(candidates) == 1:
            uri, title = candidates[0]
            roles[kind] = {
                "role_uri": uri,
                "title": title,
                "title_search": _title_search(title),
            }
        elif not candidates:
            failures.append(f"statement_roles_missing:{kind}")
        else:
            shown = " | ".join(title for _, title in candidates)
            failures.append(f"statement_roles_ambiguous:{kind}:{shown}")
    if failures:
        return None, "; ".join(failures)
    return roles, "extracted"


# ---------------------------------------------------------------------------
# Pure witness building.
# ---------------------------------------------------------------------------


def build_witness_bytes(witness: Mapping[str, Any]) -> bytes:
    """Exact 3a2 witness shape: indent=2, sort_keys, trailing newline."""
    missing = [field for field in WITNESS_FIELDS if field not in witness]
    if missing:
        raise ValueError(f"witness fields missing: {missing}")
    ordered = {field: witness[field] for field in WITNESS_FIELDS}
    return (json.dumps(ordered, indent=2, sort_keys=True) + "\n").encode("utf-8")


# ---------------------------------------------------------------------------
# Pure manifest assembly.
# ---------------------------------------------------------------------------


def _primary_stem(primary_document: str) -> str:
    head, _sep, _tail = primary_document.rpartition(".")
    return head if head else primary_document


def member_names_for_primary(primary_document: str) -> dict[str, str]:
    """Role -> member name: primary plus the five stem-sharing members."""
    stem = _primary_stem(primary_document)
    names: dict[str, str] = {}
    for role, suffix in MEMBER_SUFFIX_ROLES:
        names[role] = primary_document if suffix is None else stem + suffix
    return names


def build_package_manifest(
    *,
    issuer_row: Mapping[str, Any],
    cik10: str,
    accession: str,
    submissions_fields: Mapping[str, Any],
    index_bytes: bytes,
    index_last_modified: str | None,
    inventory_items: Sequence[Mapping[str, Any]],
    retained: Mapping[str, Mapping[str, Any]],
    declared_reason: str,
    statement_roles: Mapping[str, Any] | None,
    fixture_recorded_at: str,
    witness_bytes: bytes,
    witness_source_url: str,
) -> dict[str, Any]:
    binding = issuer_row.get("security_master_binding")
    if not isinstance(binding, Mapping):
        raise SelectionError(
            "issuer row carries no security_master_binding", code="contract_identity_missing"
        )
    members: list[dict[str, Any]] = []
    for item in inventory_items:
        name = str(item.get("name"))
        if name in retained:
            members.append(dict(retained[name]))
            continue
        members.append(
            {
                "name": name,
                "state": "not_requested",
                "role": "archive",
                "declared_reason": declared_reason,
                "index_size": item.get("size"),
                "index_type": item.get("type"),
                "archive_url": archive_document_url(cik10, accession, name),
            }
        )
    witness = {
        "path": "sec_submissions_witness.json",
        "source_url": witness_source_url,
        "content_sha256": hashlib.sha256(witness_bytes).hexdigest(),
        "byte_length": len(witness_bytes),
    }
    return {
        "schema": GOLDEN_PACKAGE_SCHEMA,
        "entity_id": binding["issuer_id"],
        "cik": cik10,
        "security_id": binding["security_id"],
        "listing_key": binding["listing_key"],
        "legal_name": issuer_row["legal_name"],
        "accession": accession,
        "form": submissions_fields["form"],
        "primary_document": submissions_fields["primaryDocument"],
        "period_of_report": submissions_fields["reportDate"],
        "filing_date": submissions_fields["filingDate"],
        "source_accepted_at": submissions_fields["acceptanceDateTime"],
        "fixture_recorded_at": fixture_recorded_at,
        "acceptance_witness": witness,
        "archive_index_url": archive_index_url(cik10, accession),
        "index_sha256": hashlib.sha256(index_bytes).hexdigest(),
        "index_byte_length": len(index_bytes),
        "index_http_last_modified": index_last_modified,
        "member_count": len(inventory_items),
        "retained_count": len(retained),
        "statement_roles": dict(statement_roles) if statement_roles else None,
        "members": members,
    }


# ---------------------------------------------------------------------------
# Request logging + paced fetching.
# ---------------------------------------------------------------------------


def _utc_stamp(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


class IssuerRequestLog:
    """One JSON line per request attempt, per issuer, under the fixture root."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._seq = 0
        self._handle = None

    def open(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self._path.open("w", encoding="utf-8")

    def record(
        self,
        *,
        url: str,
        status: Any,
        body: bytes,
        started_at: str,
        elapsed_ms: int,
        attempt: int,
    ) -> None:
        if self._handle is None:
            raise RuntimeError("request log is not open")
        self._seq += 1
        line = {
            "seq": self._seq,
            "url": url,
            "status": status,
            "byte_length": len(body),
            "content_sha256": hashlib.sha256(body).hexdigest(),
            "started_at_utc": started_at,
            "elapsed_ms": elapsed_ms,
            "attempt": attempt,
        }
        self._handle.write(json.dumps(line) + "\n")
        self._handle.flush()

    @property
    def count(self) -> int:
        return self._seq

    def close(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None


class PacedFetcher:
    """urllib GET under the shared pacer with bounded retry, logged per attempt."""

    def __init__(
        self,
        pacer: SecRequestPacer,
        user_agent: str,
        log: IssuerRequestLog,
        timeout_seconds: int = HTTP_TIMEOUT_SECONDS,
    ) -> None:
        self._pacer = pacer
        self._user_agent = user_agent
        self._log = log
        self._timeout_seconds = timeout_seconds

    def get(self, url: str) -> tuple[bytes, str | None]:
        attempt = 0
        while True:
            attempt += 1
            self._pacer.acquire()
            started = datetime.now(timezone.utc)
            began = time.monotonic()
            failure: str | None = None
            status: Any = "error"
            last_modified: str | None = None
            body = b""
            try:
                request = urllib.request.Request(
                    url,
                    headers={"User-Agent": self._user_agent, "Accept": "*/*"},
                )
                with urllib.request.urlopen(request, timeout=self._timeout_seconds) as resp:
                    body = resp.read()
                    last_modified = resp.headers.get("Last-Modified")
                    status = int(getattr(resp, "status", 200) or 200)
            except urllib.error.HTTPError as exc:
                status = int(exc.code)
                failure = f"http_{exc.code}"
            except (TimeoutError, socket.timeout) as exc:
                status = "timeout"
                failure = f"timeout:{type(exc).__name__}"
            except urllib.error.URLError as exc:
                # No HTTP status (DNS failure, refused/reset connection, a
                # connect-phase timeout wrapped by urllib): retried within the
                # same bound and logged as ``url_error``.
                reason = exc.reason
                kind = type(reason).__name__ if isinstance(reason, BaseException) else "URLError"
                status = "url_error"
                failure = f"url_error:{kind}"
            elapsed_ms = int((time.monotonic() - began) * 1000)
            self._log.record(
                url=url,
                status=status,
                body=body,
                started_at=_utc_stamp(started),
                elapsed_ms=elapsed_ms,
                attempt=attempt,
            )
            if failure is None:
                return body, last_modified
            retryable = status in ("timeout", "url_error") or (
                isinstance(status, int) and status in RETRY_STATUS_CODES
            )
            if not retryable or attempt >= MAX_ATTEMPTS:
                raise FetchFailure(
                    f"request failed after {attempt} attempt(s): {url}: {failure}",
                    status=status,
                )
            backoff = RETRY_BACKOFF_SECONDS[min(attempt - 1, len(RETRY_BACKOFF_SECONDS) - 1)]
            time.sleep(backoff)


# ---------------------------------------------------------------------------
# Submissions index (one per issuer, paged per the SEC files[] walk).
# ---------------------------------------------------------------------------


def _rows_from_submissions_page(
    page: Mapping[str, Any]
) -> list[dict[str, str]]:
    """Rows from the primary submissions JSON (``filings.recent`` block) OR
    from an older-files shard, whose parallel arrays sit at the TOP level
    (the incumbent collector's ``edgar_earnings_8k`` shard convention)."""
    filings = page.get("filings")
    block: Mapping[str, Any] = page
    if isinstance(filings, Mapping) and isinstance(filings.get("recent"), Mapping):
        block = filings["recent"]
    keys = (
        "accessionNumber",
        "form",
        "filingDate",
        "reportDate",
        "acceptanceDateTime",
        "primaryDocument",
    )
    length = len(block.get("accessionNumber", []))
    rows: list[dict[str, str]] = []
    for i in range(length):
        row = {key: block[key][i] for key in keys}
        rows.append(row)
    return rows


def build_submissions_index(
    fetch: PacedFetcher,
    cik10: str,
    wanted: set[str],
) -> dict[str, dict[str, Any]]:
    """accession -> {fields, source_url, source_path}; pages walked until found."""
    submissions_url = f"{SUBMISSIONS_ORIGIN}/CIK{cik10}.json"
    raw, _last_modified = fetch.get(submissions_url)
    payload = json.loads(raw.decode("utf-8"))
    index: dict[str, dict[str, Any]] = {}
    for row in _rows_from_submissions_page(payload):
        index[row["accessionNumber"]] = {
            "fields": row,
            "source_url": submissions_url,
            "source_path": f"filings.recent[accessionNumber={row['accessionNumber']}]",
        }
    files = payload.get("filings", {}).get("files") or []
    for page_info in files:
        if wanted and set(wanted).issubset(index):
            break
        name = str(page_info.get("name") or "")
        if not name:
            continue
        page_url = f"{SUBMISSIONS_ORIGIN}/{name}"
        page_raw, _page_last_modified = fetch.get(page_url)
        page_payload = json.loads(page_raw.decode("utf-8"))
        for row in _rows_from_submissions_page(page_payload):
            index.setdefault(
                row["accessionNumber"],
                {
                    "fields": row,
                    "source_url": page_url,
                    "source_path": (
                        f"filings.files[{name}][accessionNumber={row['accessionNumber']}]"
                    ),
                },
            )
    return index


# ---------------------------------------------------------------------------
# Package capture.
# ---------------------------------------------------------------------------


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def capture_package(
    *,
    fetch: PacedFetcher,
    issuer_row: Mapping[str, Any],
    selected: SelectedAccession,
    submissions_entry: Mapping[str, Any] | None,
    stage_root: Path,
    out_issuer_dir: Path,
    fixture_recorded_at: str,
    declared_reason: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Capture one package. Returns (capture_index row, report detail)."""
    cik10 = canonical_cik(issuer_row["cik"])
    accession = selected.accession
    stage_dir = stage_root / cik10 / accession
    detail: dict[str, Any] = {
        "issuer": issuer_row["ticker"],
        "accession": accession,
        "form": selected.form,
        "period_of_report": selected.period_of_report,
        "selection": selected.selection,
        "members_stored": 0,
        "total_bytes": 0,
        "admission": None,
        "admission_message": None,
        "statement_roles_state": None,
        "statement_roles": None,
        "d0_note": None,
    }

    def finish(
        admission: str, *, manifest: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        detail["admission"] = admission
        manifest_sha: str | None = None
        if manifest is not None:
            out_dir = out_issuer_dir / accession
            payload = (json.dumps(manifest, indent=2, sort_keys=False) + "\n").encode("utf-8")
            _write_bytes(out_dir / "package_manifest.json", payload)
            manifest_sha = hashlib.sha256(payload).hexdigest()
        detail["manifest_sha256"] = manifest_sha
        row = {
            "accession": accession,
            "form": selected.form,
            "period_of_report": selected.period_of_report,
            "selection": selected.selection,
            "manifest_sha256": manifest_sha,
            "admission": admission,
            "statement_roles_state": detail["statement_roles_state"],
        }
        return row, detail

    if submissions_entry is None:
        detail["admission_message"] = "accession absent from SEC submissions pages"
        return finish(f"submissions_row_missing:{accession}")

    fields = submissions_entry["fields"]
    if fields.get("form") != selected.form:
        detail["admission_message"] = (
            f"D0 form={selected.form} submissions form={fields.get('form')}"
        )
        return finish("d0_mismatch:form")
    if fields.get("reportDate") != selected.period_of_report:
        detail["admission_message"] = (
            f"D0 period={selected.period_of_report} "
            f"submissions reportDate={fields.get('reportDate')}"
        )
        return finish("d0_mismatch:period_of_report")
    if fields.get("filingDate") != selected.filing_date:
        detail["d0_note"] = (
            f"filing_date differs: D0={selected.filing_date} "
            f"submissions={fields.get('filingDate')} (recorded, not a refusal)"
        )

    index_url = archive_index_url(cik10, accession)
    try:
        index_bytes, index_last_modified = fetch.get(index_url)
    except FetchFailure as exc:
        detail["admission_message"] = str(exc)
        return finish(f"fetch_failed:index.json")
    if len(index_bytes) > HARD_MAX_ARCHIVE_DOCUMENT_BYTES:
        detail["admission_message"] = (
            f"index exceeds the document byte bound: {len(index_bytes)}"
        )
        return finish(f"member_oversize:index.json:{len(index_bytes)}")
    _write_bytes(stage_dir / "index.json", index_bytes)
    try:
        index_payload = json.loads(index_bytes.decode("utf-8"))
        items = index_payload["directory"]["item"]
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        detail["admission_message"] = f"archive index is malformed: {exc}"
        return finish("index_malformed")
    inventory = [str(item.get("name") or "") for item in items]
    if any(not name for name in inventory) or len(inventory) != len(set(inventory)):
        detail["admission_message"] = "archive index names are not unique/complete"
        return finish("index_malformed")
    index_lookup = {str(item.get("name")): item for item in items}

    primary_document = str(fields["primaryDocument"])
    role_names = member_names_for_primary(primary_document)
    retained: dict[str, dict[str, Any]] = {}
    retained_bytes: dict[str, bytes] = {}
    for role, name in role_names.items():
        if name not in index_lookup:
            detail["admission_message"] = f"required member absent from archive index: {name}"
            return finish(f"member_missing:{role}")
        try:
            content, last_modified = fetch.get(archive_document_url(cik10, accession, name))
        except FetchFailure as exc:
            detail["admission_message"] = str(exc)
            return finish(f"fetch_failed:{name}")
        if len(content) > HARD_MAX_ARCHIVE_DOCUMENT_BYTES:
            detail["admission_message"] = (
                f"archive member exceeds the document byte bound: {name}"
            )
            return finish(f"member_oversize:{name}:{len(content)}")
        _write_bytes(stage_dir / "members" / name, content)
        retained[name] = {
            "name": name,
            "state": "stored",
            "role": role,
            "content_sha256": hashlib.sha256(content).hexdigest(),
            "byte_length": len(content),
            "path": f"members/{name}",
            "archive_url": archive_document_url(cik10, accession, name),
            "http_last_modified": last_modified,
        }
        retained_bytes[name] = content
    detail["members_stored"] = len(retained)
    detail["total_bytes"] = len(index_bytes) + sum(len(b) for b in retained_bytes.values())

    roles, roles_state = classify_statement_roles(
        retained_bytes[role_names["presentation"]], retained_bytes[role_names["schema"]]
    )
    detail["statement_roles_state"] = roles_state
    detail["statement_roles"] = roles

    witness = {
        "source_url": submissions_entry["source_url"],
        "source_path": submissions_entry["source_path"],
        "accessionNumber": accession,
        "form": fields["form"],
        "filingDate": fields["filingDate"],
        "reportDate": fields["reportDate"],
        "acceptanceDateTime": fields["acceptanceDateTime"],
        "primaryDocument": primary_document,
    }
    witness_bytes = build_witness_bytes(witness)
    _write_bytes(stage_dir / "sec_submissions_witness.json", witness_bytes)

    manifest = build_package_manifest(
        issuer_row=issuer_row,
        cik10=cik10,
        accession=accession,
        submissions_fields=fields,
        index_bytes=index_bytes,
        index_last_modified=index_last_modified,
        inventory_items=items,
        retained=retained,
        declared_reason=declared_reason,
        statement_roles=roles,
        fixture_recorded_at=fixture_recorded_at,
        witness_bytes=witness_bytes,
        witness_source_url=str(submissions_entry["source_url"]),
    )
    if selected.selection == "capture_only":
        detail["admission_message"] = (
            "capture-only row: retained and flagged, never admitted"
        )
        return finish(CAPTURE_ONLY_ADMISSION, manifest=manifest)
    if roles is None:
        detail["admission_message"] = roles_state
        return finish(roles_state, manifest=manifest)

    try:
        admit_retained_filing_package(
            index_bytes=index_bytes,
            manifest=manifest,
            members=retained_bytes,
            witness_bytes=witness_bytes,
            capture_recorded_at=fixture_recorded_at,
        )
    except AdmittedFilingPackageError as exc:
        detail["admission_message"] = f"{exc.code}: {exc}"
        return finish(str(exc.code), manifest=manifest)
    return finish("ADMITTED", manifest=manifest)


# ---------------------------------------------------------------------------
# CLI edge.
# ---------------------------------------------------------------------------


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--contract",
        default=str(_ROOT / "config" / "fundamental_forensics" / "coverage" / "five_issuer_v1.json"),
        help="D0 coverage contract path (the only source of issuers/accessions)",
    )
    parser.add_argument(
        "--issuer",
        action="append",
        default=[],
        required=True,
        help="D0 ticker to capture (repeatable)",
    )
    parser.add_argument(
        "--extra-accession",
        action="append",
        default=[],
        help="additional D0 accession of a selected issuer (repeatable, capture-only)",
    )
    parser.add_argument(
        "--captured-at",
        default=None,
        help="REQUIRED aware ISO-8601 UTC capture clock (no wall-clock fallback)",
    )
    parser.add_argument(
        "--stage-root",
        default="~/lanes/stage/fif-gsrc",
        help="lane-local retained-bytes stage root (outside git)",
    )
    parser.add_argument(
        "--out-root",
        default=None,
        help="fixture output root for manifests/capture_index/request_log "
        "(default: tests/fixtures/fundamental_forensics/g_src under the repo root)",
    )
    parser.add_argument(
        "--min-interval",
        type=float,
        default=MIN_INTERVAL_FLOOR_SECONDS,
        help="minimum seconds between SEC requests (floor 1.0, this lane's share)",
    )
    return parser.parse_args(argv)


def _capture_clock(value: str | None) -> datetime:
    if value is None:
        raise SystemExit("gsrc_refusal: captured_at_required")
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise SystemExit(f"gsrc_refusal: captured_at_unparseable: {value}") from exc
    if parsed.tzinfo is None:
        raise SystemExit(f"gsrc_refusal: captured_at_not_utc_aware: {value}")
    return parsed.astimezone(timezone.utc)


def _resolve_sec_user_agent() -> str:
    """The FIF-family canonical SEC user agent (``config.yml`` ``edgar.user_agent``).

    Imported here, at the CLI edge, because ``collectors.edgar_forensics``
    pulls pandas/requests at import time; the capture module itself and its
    hermetic tests stay stdlib-only.
    """
    from collectors.edgar_forensics import _user_agent

    return _user_agent(_ROOT)


def _sec_user_agent_refusal_types() -> tuple[type[BaseException], ...]:
    """Errors that make the SEC user agent unavailable, as one typed refusal.

    ``yaml.YAMLError`` covers a malformed ``config.yml``. PyYAML is imported
    only here, when a resolution has already failed, so the capture module
    stays stdlib-only at import time.
    """
    kinds: list[type[BaseException]] = [ImportError, OSError, ValueError]
    try:
        import yaml
    except ImportError:
        return tuple(kinds)
    kinds.append(yaml.YAMLError)
    return tuple(kinds)


def admission_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """One issuer's admitted/refused tally, exactly as the capture report prints it.

    Refusals are keyed by the admission code up to its first ``:``, so
    ``not_admitted:capture_only`` tallies as ``not_admitted``. The committed
    G-SRC verdict pin is checked against this same rule.
    """
    refusals: dict[str, int] = {}
    for row in rows:
        if row["admission"] != "ADMITTED":
            key = row["admission"].split(":", 1)[0]
            refusals[key] = refusals.get(key, 0) + 1
    return {
        "packages": len(rows),
        "admitted": sum(1 for r in rows if r["admission"] == "ADMITTED"),
        "refusals": refusals,
    }


def _submissions_failure_rows(
    ticker: str, plan_items: Sequence[SelectedAccession], note: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []
    for item in plan_items:
        rows.append(
            {
                "accession": item.accession,
                "form": item.form,
                "period_of_report": item.period_of_report,
                "selection": item.selection,
                "manifest_sha256": None,
                "admission": "fetch_failed:submissions",
                "statement_roles_state": None,
            }
        )
        details.append(
            {
                "issuer": ticker,
                "accession": item.accession,
                "form": item.form,
                "period_of_report": item.period_of_report,
                "selection": item.selection,
                "members_stored": 0,
                "total_bytes": 0,
                "admission": "fetch_failed:submissions",
                "admission_message": note,
                "statement_roles_state": None,
                "statement_roles": None,
                "manifest_sha256": None,
                "d0_note": None,
            }
        )
    return rows, details


def _incomplete_rows(
    plan_items: Sequence[SelectedAccession], rows: Sequence[Mapping[str, Any]], cause: str
) -> list[dict[str, Any]]:
    """Typed rows for every planned accession that produced no row."""
    done = {row["accession"] for row in rows}
    return [
        {
            "accession": item.accession,
            "form": item.form,
            "period_of_report": item.period_of_report,
            "selection": item.selection,
            "manifest_sha256": None,
            "admission": f"{CAPTURE_INCOMPLETE_PREFIX}:{cause}",
            "statement_roles_state": None,
        }
        for item in plan_items
        if item.accession not in done
    ]


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.min_interval < MIN_INTERVAL_FLOOR_SECONDS:
        print(
            f"gsrc_refusal: min_interval_below_floor: {args.min_interval} < "
            f"{MIN_INTERVAL_FLOOR_SECONDS}"
        )
        return 2
    if args.captured_at is None:
        print("gsrc_refusal: captured_at_required: pass --captured-at <aware ISO-8601 UTC>")
        return 2
    clock = _capture_clock(args.captured_at)
    fixture_recorded_at = mint_fixture_recorded_at(clock)

    contract_path = Path(args.contract)
    try:
        contract = load_contract(contract_path)
        declared_reason = contract_declared_reason(contract)
        # Z0 A52: source rights are a release control — a hold refuses ONLY
        # this contract's dependent capture, before any issuer row is read
        # and before any pacer/fetcher is constructed. Independent work on
        # other contracts proceeds; the hold names only the provider.
        rights = read_source_rights(contract)
        hold = rights_hold(rights)
        if hold is not None:
            print(f"gsrc_refusal: {hold.code}: {hold.provider}")
            return 2
    except SelectionError as exc:
        print(f"gsrc_refusal: {exc.code}: {exc}")
        return 2
    except SourceRightsError as exc:
        print(f"gsrc_refusal: {exc.code}: {contract_path}")
        return 2
    except (OSError, json.JSONDecodeError) as exc:
        print(f"gsrc_refusal: contract_unreadable: {contract_path}: {exc}")
        return 2

    issuer_rows: dict[str, Mapping[str, Any]] = {}
    for row in contract.get("issuers") or []:
        if isinstance(row, Mapping) and row.get("ticker"):
            issuer_rows[str(row["ticker"])] = row
    unknown = [ticker for ticker in args.issuer if ticker not in issuer_rows]
    if unknown:
        print(f"gsrc_refusal: unknown_issuer: {', '.join(unknown)}")
        return 2
    known_extras = {
        str(accession_row.get("accession"))
        for issuer_row in issuer_rows.values()
        for accession_row in (issuer_row.get("accessions") or [])
        if isinstance(accession_row, Mapping)
    }
    for extra in args.extra_accession:
        if extra not in known_extras:
            print(f"gsrc_refusal: extra_accession_not_in_d0: {extra}")
            return 2

    stage_root = Path(args.stage_root).expanduser()
    out_root = (
        Path(args.out_root).expanduser()
        if args.out_root
        else _ROOT / "tests" / "fixtures" / "fundamental_forensics" / "g_src"
    )
    pacer = SecRequestPacer(min_interval_seconds=args.min_interval)

    plan: dict[str, list[SelectedAccession]] = {}
    claimed: set[str] = set()
    for ticker in args.issuer:
        extras = []
        for extra in args.extra_accession:
            if extra in {str(r.get("accession")) for r in issuer_rows[ticker].get("accessions") or []}:
                extras.append(extra)
        plan[ticker] = select_issuer_accessions(issuer_rows[ticker], extras)
        claimed.update(item.accession for item in plan[ticker])
    unclaimed = [extra for extra in args.extra_accession if extra not in claimed]
    if unclaimed:
        print(
            "gsrc_refusal: extra_accession_issuer_not_selected: "
            f"{', '.join(unclaimed)}"
        )
        return 2

    try:
        user_agent = _resolve_sec_user_agent()
    except _sec_user_agent_refusal_types() as exc:
        print(f"gsrc_refusal: sec_user_agent_unavailable: {type(exc).__name__}: {exc}")
        return 2

    summary: dict[str, Any] = {
        "fixture_recorded_at": fixture_recorded_at,
        "stage_root": str(stage_root),
        "issuers": {},
        "totals": {"packages": 0, "admitted": 0, "refusals": {}, "requests": 0},
    }
    for ticker in args.issuer:
        issuer_row = issuer_rows[ticker]
        cik10 = canonical_cik(issuer_row["cik"])
        out_issuer_dir = out_root / cik10
        log = IssuerRequestLog(out_issuer_dir / "request_log.jsonl")
        log.open()
        fetch = PacedFetcher(pacer, user_agent, log)
        started_wall = datetime.now(timezone.utc)
        rows: list[dict[str, Any]] = []
        details: list[dict[str, Any]] = []
        interrupted: str | None = None
        try:
            wanted = {item.accession for item in plan[ticker]}
            # Only the submissions walk maps to ``fetch_failed:submissions``;
            # anything raised while capturing a package is NOT relabelled here.
            try:
                submissions_index = build_submissions_index(fetch, cik10, wanted)
            except (FetchFailure, KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
                submissions_index = None
                failed_rows, failed_details = _submissions_failure_rows(
                    ticker,
                    plan[ticker],
                    f"submissions fetch unusable for issuer {ticker}: {exc}",
                )
                rows.extend(failed_rows)
                details.extend(failed_details)
            for item in plan[ticker] if submissions_index is not None else ():
                row, detail = capture_package(
                    fetch=fetch,
                    issuer_row=issuer_row,
                    selected=item,
                    submissions_entry=submissions_index.get(item.accession),
                    stage_root=stage_root,
                    out_issuer_dir=out_issuer_dir,
                    fixture_recorded_at=fixture_recorded_at,
                    declared_reason=declared_reason,
                )
                rows.append(row)
                details.append(detail)
        except BaseException as exc:
            interrupted = type(exc).__name__
            raise
        finally:
            if interrupted is not None:
                rows.extend(_incomplete_rows(plan[ticker], rows, interrupted))
            capture_index_payload = json.dumps(rows, indent=2) + "\n"
            _write_bytes(
                out_issuer_dir / "capture_index.json", capture_index_payload.encode("utf-8")
            )
            log.close()
        wall_seconds = (datetime.now(timezone.utc) - started_wall).total_seconds()
        counts = admission_counts(rows)
        refusals = counts["refusals"]
        summary["issuers"][ticker] = {
            "cik": cik10,
            "packages": counts["packages"],
            "admitted": counts["admitted"],
            "refusals": refusals,
            "requests": log.count,
            "wall_seconds": round(wall_seconds, 1),
            "rows": rows,
            "details": details,
        }
        summary["totals"]["packages"] += len(rows)
        summary["totals"]["admitted"] += counts["admitted"]
        for key, count in refusals.items():
            summary["totals"]["refusals"][key] = (
                summary["totals"]["refusals"].get(key, 0) + count
            )
        summary["totals"]["requests"] += log.count

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
