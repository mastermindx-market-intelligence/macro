"""Admission chain (§26.9): six refusals in cost order, before a browser is spent.

The stages are not a checklist. They are ordered by what a mistake costs. Stages
1-5 are bookkeeping — a shortfall there costs a line of text and a rerun. Stage 6
allocates a browser on a named box, which is the expensive link and the only one
whose failure is half-observable from inside the run. So every cheap refusal has
to be able to fire first, and this module makes that structural rather than
conventional: each stage consumes the previous stage's artifact and refuses when
it is absent, and every artifact carries its parent's digest, so a chain that
skipped a link cannot be reassembled later and presented as complete.

Two consequences are worth stating, because both are easy to undo by accident.

*The chain allocates nothing.* Its only success value is a ``SlotGrant`` — the
single thing a caller may hand to a driver. A cohort that was never admitted has
no token to start a browser with, so "refuse before allocation" is a property of
the return type rather than a comment asking for discipline.

*The browser ceiling comes from a measurement of the box, not from the number the
spec intends.* §26.3 says six light profiles per box; a box that measures four has
four. ``Box.effective_ceiling`` takes the minimum of the declared ceiling and what
memory and process headroom actually support, and the stage-6 artifact records
which of those bound it. Entering six because the spec says six is exactly how a
box degrades silently instead of refusing.

Both heads are checked because either can bind first, and neither may be taken on
trust. Memory arrives as a *named basis* — a counter, not a percentage — because
"58% free" from a memory-pressure gauge can sit on top of 299 MiB of unused pages
and a multi-gigabyte compressor, and a gate fed that number reports health while
the box swaps. Process count arrives as a *measured* per-instance cost, because the
helper count varies per profile class; a remembered constant calibrates the guard
against a machine nobody measured. Both figures are recorded in the stage-6 receipt,
so a wrong input is visible in the evidence instead of in a degraded box.

*A box is enumerated before it is ceiled.* Stage 6 also consumes an observer
snapshot — injected, never fetched — and refuses a box that was never counted
(``enumeration_not_collected``), counted on another host (``enumeration_wrong_box``),
counted too long ago (``enumeration_stale``), or counted and found holding a port
neither the registry nor the resource plane declared (``undeclared_port``). The
census runs before the ceiling: a number computed over unknown occupants describes
a box nobody looked at. The snapshot parses strictly — schema pinned, ports
integers, completeness stated — and the receipt gives every observed port the
word that cleared it, ``declared`` or ``baseline``.

Nothing here reads a credential, a network endpoint or a browser. The whole chain
runs on records, which is what lets the suite in ``tests/test_admission.py``
exercise it on a laptop that has never run a child.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Sequence

from . import net
from .persona import Persona

# The order is the contract. Reordering these lines changes which refusal a
# caller sees first, which is the whole point of the module.
STAGES = ("domain", "identity", "custody", "proxy", "account", "slot")
STAGE_INDEX = {name: i for i, name in enumerate(STAGES, start=1)}

# A measurement is not a constant. Fifteen minutes is long enough to cover a
# pre-flight and short enough that a box which lost 3 GB to another app in the
# meantime does not inherit yesterday's ceiling.
DEFAULT_MAX_AGE = 900.0

# Clocks drift. A stamp slightly ahead of this gate's own clock is skew to
# absorb; a stamp minutes ahead is a clock that was never set, and a
# measurement dated after the moment it is used is not a measurement of
# anything. The gate refuses rather than guess which clock lied.
FUTURE_TOLERANCE = 60.0

# The observer snapshot schemas this gate parses. A snapshot from a newer
# revision may have moved a field, and parsing it as if it were understood is
# the quietest way to admit a box nobody actually censused.
SUPPORTED_SNAPSHOT_SCHEMA = (1,)

# The counters a memory figure may come from. Anything else — a gauge
# percentage, a rounded "free memory" display — refuses, because it cannot be
# reconciled with the page counters the rest of this module reports.
MEMORY_BASES = ("free_inactive_speculative", "free_pages", "vm_stat_reclaimable")

# Candidate ceilings, in the order a tie is reported. A tie is broken toward the
# earlier name so two runs on the same box never disagree about what bound them.
_CEILING_ORDER = ("declared", "memory", "process")


class AdmissionRefused(RuntimeError):
    """A fail-closed verdict. Raised, never returned — it cannot be ignored."""

    def __init__(self, stage: str, code: str, detail: str, remedy: str = "") -> None:
        self.stage = stage
        # A refusal may name something that is not one of the six stages (the
        # chain-level refusals do). Index 0 marks "outside the six"; it must
        # never be a KeyError, because a refusal that crashes is not a verdict.
        self.stage_index = STAGE_INDEX.get(stage, 0)
        self.code = code
        self.detail = detail
        self.remedy = remedy
        if self.stage_index:
            message = f"refused at stage {self.stage_index}/6 ({stage}): {detail}"
        else:
            message = f"refused outside the six stages ({stage}): {detail}"
        if remedy:
            message += f" — {remedy}"
        super().__init__(message)

    def public(self) -> dict:
        """Loggable verdict. No record, address or endpoint travels with it."""
        return {
            "ok": False,
            "stage": self.stage,
            "stage_index": self.stage_index,
            "code": self.code,
            "detail": self.detail,
            "remedy": self.remedy,
        }


# ---------------------------------------------------------------------------
# Artifacts: what one stage hands the next one
# ---------------------------------------------------------------------------

def _digest(stage: str, subject: str, parent: str, facts: Mapping) -> str:
    body = json.dumps(
        {"stage": stage, "subject": subject, "parent": parent, "facts": facts},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(body.encode()).hexdigest()


@dataclass(frozen=True)
class Artifact:
    """One stage's receipt. ``parent`` is the previous receipt's digest."""

    stage: str
    subject: str
    parent: str
    facts: dict
    digest: str

    def public(self) -> dict:
        return {
            "stage": self.stage,
            "subject": self.subject,
            "parent": self.parent,
            "digest": self.digest,
            "facts": self.facts,
        }


def _artifact(stage: str, subject: str, parent: str, facts: dict) -> Artifact:
    return Artifact(stage, subject, parent, dict(facts),
                    _digest(stage, subject, parent, facts))


# ---------------------------------------------------------------------------
# Stage records. Every default is the refusing one, so a half-built record
# cannot be mistaken for a satisfied stage.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DomainRecord:
    domain: str
    handle: str
    verified: bool = False
    expires_at: float = 0.0


@dataclass(frozen=True)
class Identity:
    handle: str
    address: str
    domain: str
    recovery_owner: str = ""
    verified: bool = False


@dataclass(frozen=True)
class Custody:
    handle: str
    totp_enrolled: bool = False
    recovery_custodian: str = ""
    recovery_codes_held: bool = False


@dataclass(frozen=True)
class Account:
    handle: str
    account_id: str = ""
    admitted: bool = False


# ---------------------------------------------------------------------------
# The box, and the readings that are allowed to bound it
# ---------------------------------------------------------------------------

def _refuse_schema(detail: str, remedy: str) -> AdmissionRefused:
    return AdmissionRefused("slot", "schema_unsupported", detail, remedy)


def _parse_taken_at(raw: object) -> float:
    """The moment the census was taken, as epoch seconds. Refuses anything else."""
    if raw is None or isinstance(raw, bool):
        raw_repr = repr(raw)
        raise _refuse_schema(
            f"snapshot taken_at is {raw_repr}",
            "the observer must stamp the sweep; a snapshot with no moment is not evidence of when",
        )
    if isinstance(raw, (int, float)):
        stamp = float(raw)
        if not math.isfinite(stamp):
            raise _refuse_schema(
                f"snapshot taken_at is {raw!r}, which is not a finite moment",
                "fix the observer clock; a census the gate cannot date is not a census",
            )
        return stamp
    if isinstance(raw, str):
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            pass
        else:
            # A naive stamp dates the sweep to no moment in particular: this
            # gate would have to guess a timezone, and a guessed clock is how
            # a stale census passes as fresh. An offset is part of the date.
            if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
                raise _refuse_schema(
                    "taken_at must carry a UTC offset",
                    "the observer stamps UTC; a stamp with no offset dates nothing",
                )
            return parsed.timestamp()
    raise _refuse_schema(
        f"snapshot taken_at {raw!r} is neither an ISO-8601 stamp nor an epoch number",
        "fix the observer clock; a timestamp this gate cannot read is a snapshot it cannot date",
    )


@dataclass(frozen=True)
class Enumeration:
    """What the observer saw on a box, at a stated moment, under one schema pin.

    Parsed from a snapshot the caller injects — the gate never fetches, executes
    or trusts a live probe. ``observed_ports`` is the union of the listener
    ports and the Chrome CDP ports, nulls dropped: everything on the box that
    held a TCP socket the census could see. Parsing is strict because a
    snapshot whose shape is not understood is not a census, and a collection
    that did not finish is not a count; both refuse rather than parse to
    something smaller and more confident.
    """

    schema_version: int
    host: str
    taken_at: float
    collection_status: str
    observed_ports: frozenset[int]
    tool_sha256: str = ""

    @classmethod
    def from_snapshot(cls, snapshot: Mapping) -> "Enumeration":
        """Parse one observer snapshot, shape-strict, or refuse with a code."""
        if not isinstance(snapshot, Mapping):
            raise _refuse_schema(
                f"snapshot is {type(snapshot).__name__}, not a mapping",
                "inject the observer payload as parsed; a shape this gate cannot "
                "read is not a census",
            )
        version = snapshot.get("schema_version")
        # Exact int, not a value comparison: `1.0 in (1,)` is True, and a float
        # schema version is a revision this gate did not ship.
        if type(version) is not int or version not in SUPPORTED_SNAPSHOT_SCHEMA:
            raise _refuse_schema(
                f"snapshot schema_version is {version!r}; this gate parses "
                f"{list(SUPPORTED_SNAPSHOT_SCHEMA)} only",
                "re-run the observer at a supported schema; a newer revision may "
                "have moved a field",
            )
        host = snapshot.get("host")
        if not isinstance(host, str) or not host:
            raise _refuse_schema(
                f"snapshot host is {host!r}; a snapshot must name the box it censused",
                "fix the observer; an enumeration is pinned to a host, or it pins nothing",
            )
        taken_at = _parse_taken_at(snapshot.get("taken_at"))

        listeners = snapshot.get("listeners")
        chrome = snapshot.get("chrome")
        if not isinstance(listeners, list) or not isinstance(chrome, list):
            raise _refuse_schema(
                f"listeners/chrome missing or not arrays "
                f"(listeners {type(listeners).__name__}, chrome {type(chrome).__name__})",
                "re-run the observer; both arrays travel even when they are empty",
            )
        ports: set[int] = set()
        for row in listeners:
            port = row.get("port") if isinstance(row, Mapping) else None
            if isinstance(port, bool) or not isinstance(port, int):
                raise _refuse_schema(
                    f"listener port {port!r} is not an integer — a string port is "
                    f"a shape the contract forbids",
                    "fix the observer; ports are always integers",
                )
            if not 1 <= port <= 65535:
                raise _refuse_schema(
                    f"listener port {port} is outside 1..65535",
                    "fix the observer; a port is a TCP port, not any integer",
                )
            ports.add(port)
        for row in chrome:
            # Chrome rows parse under the same law as listener rows: a row that
            # is not a mapping is not a row the census took, and dropping it
            # would shrink the observed set without saying so.
            if not isinstance(row, Mapping):
                raise _refuse_schema(
                    f"chrome row {row!r} is not a mapping — a shape the contract forbids",
                    "fix the observer; chrome rows are objects, like listener rows",
                )
            port = row.get("cdp_port")
            if port is None:
                continue
            if isinstance(port, bool) or not isinstance(port, int):
                raise _refuse_schema(
                    f"chrome cdp_port {port!r} is not an integer or null",
                    "fix the observer; ports are always integers",
                )
            if not 1 <= port <= 65535:
                raise _refuse_schema(
                    f"chrome cdp_port {port} is outside 1..65535",
                    "fix the observer; a port is a TCP port, not any integer",
                )
            ports.add(port)

        # `collection_status` lives at the top level of the shipped payload; the
        # older `collected.` position is accepted for the same reason, and a
        # snapshot stating neither is simply not "complete".
        collected = snapshot.get("collected")
        status = snapshot.get("collection_status")
        if status is None and isinstance(collected, Mapping):
            status = collected.get("collection_status")
        if status != "complete":
            raise AdmissionRefused(
                "slot", "enumeration_incomplete",
                f"collection_status is {status!r}, not 'complete'",
                "re-run the sweep; an incomplete collection counted a box nobody "
                "can vouch for",
            )
        provenance = snapshot.get("provenance")
        tool_sha256 = provenance.get("script_sha256", "") if isinstance(provenance, Mapping) else ""
        if not isinstance(tool_sha256, str):
            tool_sha256 = ""
        return cls(
            schema_version=version,
            host=host,
            taken_at=taken_at,
            collection_status=status,
            observed_ports=frozenset(ports),
            tool_sha256=tool_sha256,
        )


@dataclass(frozen=True)
class Headroom:
    """What the box actually has, measured, at a stated moment.

    ``memory_basis`` names the counter the available figure came from, and is
    refused unless it is one of ``MEMORY_BASES``. A percentage from a
    memory-pressure gauge is not a free-page count: on a box with 299 MiB of
    unused pages and a 4 GiB compressor it can still print 58% free, and a gate
    that trusts it admits a browser into swap. Naming the basis is the cheapest
    way to stop that, because the wrong reader cannot name a real counter.

    ``browser_resident_bytes`` and ``browser_processes`` are per browser
    instance, measured on this box for this profile class — not a constant
    remembered from another machine. Both matter: memory can be plentiful while
    the process table binds, and vice versa.
    """

    measured_at: float
    memory_total_bytes: int
    memory_available_bytes: int
    browser_resident_bytes: int
    process_limit: int
    process_in_use: int
    browser_processes: int
    memory_basis: str = ""
    reserve_bytes: int = 0
    compressor_bytes: int = 0
    pageouts: int = 0

    def memory_capacity(self) -> int:
        if self.browser_resident_bytes <= 0:
            raise ValueError("browser_resident_bytes must be positive")
        free = self.memory_available_bytes - self.reserve_bytes
        return max(free, 0) // self.browser_resident_bytes

    def process_capacity(self) -> int:
        if self.browser_processes <= 0:
            raise ValueError("browser_processes must be positive")
        return max(self.process_limit - self.process_in_use, 0) // self.browser_processes


@dataclass(frozen=True)
class Ceiling:
    """The number the cohort is actually bounded by, and what bounded it."""

    box: str
    declared: int
    memory: int
    process: int
    effective: int
    binding: str
    measured_at: float
    basis: str = ""
    compressor_bytes: int = 0
    pageouts: int = 0

    @property
    def over_claim(self) -> bool:
        """True when the deployment asked for more than the box can seat."""
        return self.declared > self.effective

    def public(self) -> dict:
        return {
            "box": self.box,
            "declared": self.declared,
            "memory_capacity": self.memory,
            "process_capacity": self.process,
            "effective": self.effective,
            "binding": self.binding,
            "over_claim": self.over_claim,
            "measured_at": self.measured_at,
            "memory_basis": self.basis,
            # Page evidence travels with the verdict so a reader can tell a
            # healthy reading from a pressure gauge wearing its clothes.
            "compressor_bytes": self.compressor_bytes,
            "pageouts": self.pageouts,
        }


@dataclass(frozen=True)
class Box:
    """One box, the ceiling it is meant to run, and the measurements that bound it.

    ``enumeration``, ``declared_ports`` and ``baseline_ports`` are injected by
    the caller, like ``headroom``: the gate never parses the registry document,
    the resource-plane declarations or the baseline file. ``declared_ports`` is
    the union of the registry persona bindings (``binding.cdp_port``) and the
    resource-plane tool declarations (``{id, host, port}`` — a chrome-automation
    bridge on 9223 is tooling declared in the resource plane, not a persona
    minted for it); ``baseline_ports`` is the versioned stock-macOS allowlist,
    ARDAgent's 3283 among them.
    """

    box: str
    ceiling: int
    headroom: Headroom | None = None
    max_age_seconds: float = DEFAULT_MAX_AGE
    enumeration: Enumeration | None = None
    declared_ports: frozenset[int] = frozenset()
    baseline_ports: frozenset[int] = frozenset()

    def effective_ceiling(self, now: float) -> Ceiling:
        """The measured ceiling. Never the declared number on its own."""
        if self.headroom is None:
            raise AdmissionRefused(
                "slot", "ceiling_unmeasured",
                f"{self.box}: no measurement for the box, only a declared ceiling of {self.ceiling}",
                "pass a Headroom from the box readback; the spec's number is not evidence of headroom",
            )
        measured_at = self.headroom.measured_at
        # Freshness defaults before the staleness comparison, because the
        # comparison itself is fail-open on a bad stamp: `nan > limit` is
        # False, so a NaN measurement would have sailed through as fresh. A
        # stamp the gate cannot date is not a measurement, and a stamp minutes
        # ahead of this clock measured a box that does not exist yet.
        if not math.isfinite(measured_at):
            raise AdmissionRefused(
                "slot", "measurement_unstated",
                f"{self.box}: the headroom measurement is stamped {measured_at!r}, "
                f"which is not a finite moment",
                "re-read the box; a reading the gate cannot date is not a reading",
            )
        ahead = measured_at - now
        if ahead > FUTURE_TOLERANCE:
            raise AdmissionRefused(
                "slot", "measurement_from_future",
                f"{self.box}: headroom is stamped {ahead:.0f}s ahead of now, beyond "
                f"the {FUTURE_TOLERANCE:.0f}s clock tolerance",
                "fix the box clock; a measurement dated after it is used measured nothing",
            )
        age = now - measured_at
        if age >= self.max_age_seconds:
            raise AdmissionRefused(
                "slot", "ceiling_stale",
                f"{self.box}: headroom was measured {age:.0f}s ago, at or past the "
                f"{self.max_age_seconds:.0f}s limit",
                "re-read the box; a stale measurement describes a box that may no longer exist",
            )
        if self.ceiling < 0:
            raise AdmissionRefused(
                "slot", "measurement_incoherent",
                f"{self.box}: declared ceiling is negative ({self.ceiling})",
                "fix the box descriptor",
            )
        # A reading that contradicts itself is not a reading of any box.
        # Available pages cannot exceed the total they are part of, a process
        # count cannot be negative or run past its own limit, and a total of
        # zero measured nothing — computing a ceiling from a contradiction is
        # how a gate reports a number it invented.
        head = self.headroom
        if head.memory_total_bytes <= 0:
            raise AdmissionRefused(
                "slot", "measurement_incoherent",
                f"{self.box}: memory_total_bytes is {head.memory_total_bytes}; a "
                f"total that small is not a measurement of any box",
                "re-read the box; the total is part of the measurement",
            )
        if head.memory_available_bytes > head.memory_total_bytes:
            raise AdmissionRefused(
                "slot", "measurement_incoherent",
                f"{self.box}: memory_available_bytes ({head.memory_available_bytes}) "
                f"exceeds memory_total_bytes ({head.memory_total_bytes})",
                "re-read the box; available memory cannot exceed the total it is part of",
            )
        if head.process_in_use < 0:
            raise AdmissionRefused(
                "slot", "measurement_incoherent",
                f"{self.box}: process_in_use is {head.process_in_use}, which is negative",
                "re-read the process table; a negative count is not a count",
            )
        if head.process_limit <= 0:
            raise AdmissionRefused(
                "slot", "measurement_incoherent",
                f"{self.box}: process_limit is {head.process_limit}; a box with no "
                f"process limit measured nothing",
                "re-read the process table; the limit is part of the measurement",
            )
        if head.process_in_use > head.process_limit:
            raise AdmissionRefused(
                "slot", "measurement_incoherent",
                f"{self.box}: process_in_use ({head.process_in_use}) exceeds "
                f"process_limit ({head.process_limit})",
                "re-read the process table; use cannot exceed the limit it is measured against",
            )
        if self.headroom.memory_basis not in MEMORY_BASES:
            raise AdmissionRefused(
                "slot", "measurement_basis_unstated",
                f"{self.box}: memory headroom came from "
                f"{self.headroom.memory_basis or 'no stated counter'!r}, not one of "
                f"{', '.join(MEMORY_BASES)}",
                "re-read the page counters; a pressure-gauge percentage is not free "
                "memory, whatever it prints",
            )
        try:
            memory = self.headroom.memory_capacity()
            process = self.headroom.process_capacity()
        except ValueError as exc:
            raise AdmissionRefused(
                "slot", "measurement_incoherent",
                f"{self.box}: {exc}",
                "measure per-instance cost; zero is not a measurement",
            ) from None

        candidates = {"declared": self.ceiling, "memory": memory, "process": process}
        effective = min(candidates.values())
        binding = next(k for k in _CEILING_ORDER if candidates[k] == effective)
        return Ceiling(self.box, self.ceiling, memory, process, effective,
                       binding, self.headroom.measured_at,
                       basis=self.headroom.memory_basis,
                       compressor_bytes=self.headroom.compressor_bytes,
                       pageouts=self.headroom.pageouts)


# ---------------------------------------------------------------------------
# What success looks like
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SlotGrant:
    """The one thing a driver may be started with.

    Minted only by ``preflight``. Caller-side code should treat it as opaque: it
    carries slot *names*, never endpoints, because a grant reaches a log line far
    more often than a slot does. ``enumeration_digest`` pins the grant to the
    census that cleared the box — a different observed set is a different grant.
    Python cannot make a dataclass unforgeable, so
    this is a convention with a narrow constructor and one call site rather than
    a security boundary — the boundary that matters is that a refused preflight
    returns no grant at all.
    """

    box: str
    declared_ceiling: int
    effective_ceiling: int
    binding: str
    handles: tuple[str, ...]
    slots: Mapping[str, str]
    chain_digest: str
    enumeration_digest: str = ""

    def public(self) -> dict:
        return {
            "box": self.box,
            "declared_ceiling": self.declared_ceiling,
            "effective_ceiling": self.effective_ceiling,
            "binding": self.binding,
            "handles": list(self.handles),
            "slots": dict(self.slots),
            "chain_digest": self.chain_digest,
            "enumeration_digest": self.enumeration_digest,
        }


@dataclass(frozen=True)
class Admission:
    """A complete six-link chain and the grant it earned."""

    artifacts: tuple[Artifact, ...]
    grant: SlotGrant

    @property
    def stage_digests(self) -> dict[str, str]:
        return {a.stage: a.digest for a in self.artifacts}

    def public(self) -> dict:
        return {
            "ok": True,
            "grant": self.grant.public(),
            "chain": [a.public() for a in self.artifacts],
        }


# ---------------------------------------------------------------------------
# Re-checking a stored chain
# ---------------------------------------------------------------------------

def verify_chain(artifacts: Sequence[Artifact]) -> None:
    """Re-check a chain somebody kept. Raises on a missing, reordered, altered
    or misnamed link.

    ``preflight`` builds a chain in order, so this exists for the other direction:
    a receipt set read back from disk, a CI artifact or a previous run's output.
    A chain with a stage removed must not verify, or the ordering rule is only as
    good as the last person who edited the file.
    """
    given = list(artifacts)
    # A link naming a stage the gate does not have is not a chain in any order.
    # It refuses here, before the per-stage walk can turn it into a KeyError —
    # an unknown stage must produce a verdict, not a crash.
    for art in given:
        if art.stage not in STAGE_INDEX:
            raise AdmissionRefused(
                "chain", "chain_unknown_stage",
                f"link stage {art.stage!r} is not one of the six",
                "a receipt that names a stage this gate does not have is not a chain",
            )
    for i, stage in enumerate(STAGES):
        if i >= len(given):
            last = given[-1].stage if given else "nothing"
            raise AdmissionRefused(
                stage, "chain_incomplete",
                f"chain ends at {last}; stage {i + 1}/6 ({stage}) is absent",
                "run preflight again; a partial chain admits nothing",
            )
        if given[i].stage != stage:
            if stage not in [a.stage for a in given[i:]]:
                raise AdmissionRefused(
                    stage, "chain_incomplete",
                    f"stage {i + 1}/6 ({stage}) is absent; link {i + 1} is {given[i].stage!r}",
                    "run preflight again; a chain with a hole admits nothing",
                )
            raise AdmissionRefused(
                given[i].stage, "chain_out_of_order",
                f"link {i + 1}/6 is {given[i].stage!r}, expected {stage!r}",
                "the chain is ordered by cost; rebuild it in stage order",
            )
    if len(given) > len(STAGES):
        raise AdmissionRefused(
            "slot", "chain_out_of_order",
            f"{len(given)} links for {len(STAGES)} stages",
            "one artifact per stage",
        )

    parent = ""
    for art in given:
        if art.parent != parent:
            raise AdmissionRefused(
                art.stage, "chain_tampered",
                f"{art.stage}: parent {art.parent[:12] or '(none)'} is not the digest "
                f"of the stage before it ({parent[:12] or '(none)'})",
                "rebuild that link; do not patch one artifact into another chain",
            )
        if _digest(art.stage, art.subject, art.parent, art.facts) != art.digest:
            raise AdmissionRefused(
                art.stage, "chain_tampered",
                f"{art.stage}: facts do not hash to the recorded digest",
                "a hand-edited receipt is not evidence",
            )
        parent = art.digest


# ---------------------------------------------------------------------------
# The chain itself
# ---------------------------------------------------------------------------

def _index(records: Sequence, stage: str) -> dict:
    out: dict = {}
    for record in records:
        if record.handle in out:
            raise AdmissionRefused(
                stage, "duplicate_record",
                f"{stage}: two records for handle {record.handle!r}",
                "one record per handle; refuse the ambiguity rather than pick one",
            )
        out[record.handle] = record
    return out


def preflight(
    *,
    handles: Sequence[str],
    domains: Sequence[DomainRecord],
    identities: Sequence[Identity],
    custody: Sequence[Custody],
    slots: Sequence[net.Slot],
    accounts: Sequence[Account],
    box: Box,
    personas: Mapping[str, Persona] | None = None,
    now: float | None = None,
) -> Admission:
    """Walk the six stages in cost order and return the chain plus its one grant.

    ``handles`` is the cohort *for this box*: a child in two cells is a bug the
    cohort argument cannot express, so when ``personas`` is supplied each row's
    ``cell`` must name ``box.box`` and the mismatch refuses at stage 2 — before a
    proxy or a browser is spent on a child that belongs somewhere else.

    Raises ``AdmissionRefused``; there is no partial-success return.
    """
    now = time.time() if now is None else now
    cohort = list(handles)
    subject = box.box
    artifacts: list[Artifact] = []
    parent = ""

    # --- 1. domain ---------------------------------------------------------
    if not cohort:
        raise AdmissionRefused(
            "domain", "cohort_empty",
            f"{box.box}: the cohort is empty, so there is nothing to admit",
            "pass at least one handle; an empty success would mint a grant for no child",
        )
    duplicates = sorted({h for h in cohort if cohort.count(h) > 1})
    if duplicates:
        raise AdmissionRefused(
            "domain", "duplicate_handle",
            f"duplicate handles in the cohort: {', '.join(duplicates)}",
            "one child per handle",
        )
    domain_rows = _index(domains, "domain")
    for handle in cohort:
        record = domain_rows.get(handle)
        if record is None:
            raise AdmissionRefused(
                "domain", "no_domain_record",
                f"{handle}: no domain record",
                "register the domain before the identity that lives on it",
            )
        if not record.verified:
            raise AdmissionRefused(
                "domain", "domain_unverified",
                f"{handle}: domain {record.domain} is not verified",
                "verify control of the domain, then re-run",
            )
        # The refusing default. `expires_at=0.0` is the dataclass default, so it
        # is what a half-built record carries — and "never stated" is not
        # "never expires"; it is a field nobody filled in.
        if record.expires_at <= 0:
            raise AdmissionRefused(
                "domain", "domain_expiry_unstated",
                f"{handle}: domain {record.domain} states no expiry",
                "state when the registration expires; a default of 0 is not a date",
            )
        if record.expires_at <= now:
            raise AdmissionRefused(
                "domain", "domain_expired",
                f"{handle}: domain {record.domain} expired at {record.expires_at:.0f}",
                "renew before the identity on it is worth anything",
            )
    artifacts.append(_artifact("domain", subject, parent, {
        "cohort": len(cohort),
        "records": [{"handle": h,
                     "domain": domain_rows[h].domain,
                     "expires_at": domain_rows[h].expires_at} for h in cohort],
    }))
    parent = artifacts[-1].digest

    # --- 2. identity + recovery owner --------------------------------------
    # Cheap and legible first: a cohort larger than the admitted identity pool
    # refuses here, at stage 2, long before stage 6 could hand out a browser.
    # Reporting "7 children, 5 identities" also beats reporting the 6th handle
    # that happened to be missing.
    identity_rows = _index(identities, "identity")
    pooled = [r for r in identities if r.verified]
    if len(cohort) > len(pooled):
        raise AdmissionRefused(
            "identity", "identity_shortfall",
            f"{len(cohort)} children in the cohort but {len(pooled)} admitted identities "
            f"— refused before any browser is allocated",
            "enrol an identity per child, or shrink the cohort to the admitted count",
        )
    for handle in cohort:
        identity = identity_rows.get(handle)
        if identity is None:
            raise AdmissionRefused(
                "identity", "no_identity",
                f"{handle}: no email identity",
                "the mailbox is the account; there is no child without one",
            )
        if not identity.verified:
            raise AdmissionRefused(
                "identity", "identity_unverified",
                # The handle, never the mailbox address: a refusal is a verdict,
                # and verdicts travel further than records do.
                f"{handle}: identity is not verified",
                "complete verification, then re-run",
            )
        if not identity.recovery_owner:
            raise AdmissionRefused(
                "identity", "no_recovery_owner",
                f"{handle}: identity has no named recovery owner",
                "name the human accountable for recovering this account",
            )
        if identity.domain != domain_rows[handle].domain:
            raise AdmissionRefused(
                "identity", "identity_off_domain",
                f"{handle}: identity is on {identity.domain}, domain record is "
                f"{domain_rows[handle].domain}",
                "an identity off its own domain is not recoverable under that domain",
            )
        if personas is not None:
            persona = personas.get(handle)
            if persona is None:
                raise AdmissionRefused(
                    "identity", "no_persona",
                    f"{handle}: no persona row, so no cell to seat it in",
                    "add the persona row before enrolling the child",
                )
            if persona.cell != box.box:
                raise AdmissionRefused(
                    "identity", "cohort_off_box",
                    f"{handle}: persona cell is {persona.cell}, box is {box.box}",
                    "one child in one cell; split the cohort by box",
                )
    artifacts.append(_artifact("identity", subject, parent, {
        "cohort": len(cohort),
        "admitted_pool": len(pooled),
        "identities": [{"handle": h,
                        "domain": identity_rows[h].domain,
                        "recovery_owner": identity_rows[h].recovery_owner}
                       for h in cohort],
    }))
    parent = artifacts[-1].digest

    # --- 3. TOTP / recovery custody ----------------------------------------
    custody_rows = _index(custody, "custody")
    for handle in cohort:
        held = custody_rows.get(handle)
        if held is None:
            raise AdmissionRefused(
                "custody", "no_custody",
                f"{handle}: no TOTP/recovery custody record",
                "record who holds the second factor before the account is touched",
            )
        if not held.totp_enrolled:
            raise AdmissionRefused(
                "custody", "totp_not_enrolled",
                f"{handle}: no TOTP enrolled",
                "enrol the second factor; a password-only account is not an admitted account",
            )
        if not held.recovery_codes_held:
            raise AdmissionRefused(
                "custody", "recovery_codes_missing",
                f"{handle}: recovery codes are not held by anyone",
                "generate and custody the codes, or the account is unrecoverable",
            )
        if not held.recovery_custodian:
            raise AdmissionRefused(
                "custody", "no_recovery_custodian",
                f"{handle}: no named recovery custodian",
                "name who physically holds the codes",
            )
    artifacts.append(_artifact("custody", subject, parent, {
        "handles": len(cohort),
        "custodians": sorted({custody_rows[h].recovery_custodian for h in cohort}),
    }))
    parent = artifacts[-1].digest

    # --- 4. pinned proxy ---------------------------------------------------
    try:
        bound = net.bind(list(slots), cohort)
    except ValueError as exc:
        raise AdmissionRefused(
            "proxy", "proxy_shortfall",
            f"{len(cohort)} children on {len(slots)} proxy slots: {exc}",
            "slots are exclusive for the life of the account; add slots or shrink the cohort",
        ) from None
    artifacts.append(_artifact("proxy", subject, parent, {
        "handles": len(cohort),
        "pool": len(slots),
        # Names only. A stage-4 receipt is read by more people than the command
        # that binds a child, so it never carries an endpoint or a password.
        "slots": {h: bound[h].name for h in sorted(cohort)},
        # Ownership is ASSERTED from the pool record, never discovered by
        # walking a process tree: browsers launched detached (`open -na`) are
        # reparented to pid 1, so parentage carries no slot information at all.
        "ownership": "pool_record",
    }))
    parent = artifacts[-1].digest

    # --- 5. admitted account ----------------------------------------------
    account_rows = _index(accounts, "account")
    for handle in cohort:
        account = account_rows.get(handle)
        if account is None:
            raise AdmissionRefused(
                "account", "no_account",
                f"{handle}: no account record",
                "an identity is not an account; admit one explicitly",
            )
        if not account.account_id:
            raise AdmissionRefused(
                "account", "account_not_admitted",
                f"{handle}: account record has no account id",
                "record the admitted account id",
            )
        if not account.admitted:
            raise AdmissionRefused(
                "account", "account_not_admitted",
                f"{handle}: account {account.account_id} is not admitted",
                "admission is explicit; absence of a refusal is not admission",
            )
    artifacts.append(_artifact("account", subject, parent, {
        "handles": len(cohort),
        "accounts": [{"handle": h, "account_id": account_rows[h].account_id}
                     for h in cohort],
    }))
    parent = artifacts[-1].digest

    # --- 6. browser slot: the box is enumerated, then bounded by measurement -
    # The census runs before the ceiling. A ceiling computed over unknown
    # occupants is a number about a box nobody looked at: seats can be free
    # while something undeclared already holds them.
    enum = box.enumeration
    if enum is None:
        raise AdmissionRefused(
            "slot", "enumeration_not_collected",
            f"{box.box}: no enumeration of the box, only a declared ceiling of {box.ceiling}",
            "inject an observer snapshot; an unobserved box is not admissible, "
            "whatever its descriptor claims",
        )
    if enum.host != box.box:
        raise AdmissionRefused(
            "slot", "enumeration_wrong_box",
            f"{box.box}: the enumeration describes {enum.host}",
            "re-run the observer against this box; another box's census says "
            "nothing about this one",
        )
    # A census the gate cannot date, or one dated after the moment it is used,
    # is not a census of the box now — and the staleness comparison below is
    # fail-open on a bad stamp (`nan > limit` is False), so these refuse first.
    if not math.isfinite(enum.taken_at):
        raise AdmissionRefused(
            "slot", "measurement_unstated",
            f"{box.box}: the enumeration is stamped {enum.taken_at!r}, which is "
            f"not a finite moment",
            "re-run the sweep; a census the gate cannot date is not a census",
        )
    ahead = enum.taken_at - now
    if ahead > FUTURE_TOLERANCE:
        raise AdmissionRefused(
            "slot", "measurement_from_future",
            f"{box.box}: the enumeration is stamped {ahead:.0f}s ahead of now, "
            f"beyond the {FUTURE_TOLERANCE:.0f}s clock tolerance",
            "fix the box clock; a census dated after it is used counted nothing",
        )
    age = now - enum.taken_at
    if age >= box.max_age_seconds:
        raise AdmissionRefused(
            "slot", "enumeration_stale",
            f"{box.box}: the enumeration was taken {age:.0f}s ago, at or past the "
            f"{box.max_age_seconds:.0f}s limit",
            "re-run the sweep; a stale census describes a box that may no longer exist",
        )
    undeclared = sorted(enum.observed_ports - box.declared_ports - box.baseline_ports)
    if undeclared:
        raise AdmissionRefused(
            "slot", "undeclared_port",
            f"{box.box}: port(s) {', '.join(str(p) for p in undeclared)} observed but "
            f"neither declared ({sorted(box.declared_ports)}) nor baseline "
            f"({sorted(box.baseline_ports)})",
            "declare it in the registry or the resource plane, add it to the baseline "
            "allowlist, or stop it; an undeclared port is an undeclared identity",
        )
    ceiling = box.effective_ceiling(now)
    if len(cohort) > ceiling.effective:
        raise AdmissionRefused(
            "slot", "ceiling_exhausted",
            f"{len(cohort)} children for {box.box}, whose measured ceiling is "
            f"{ceiling.effective} (declared {ceiling.declared}, memory supports "
            f"{ceiling.memory}, processes support {ceiling.process}, bound by {ceiling.binding})",
            "shrink the cohort or free the box; a browser past the measured ceiling "
            "degrades the box instead of refusing",
        )
    # Every observed port gets exactly one verdict word. Declared wins when a
    # port is in both sets: a persona binding is a stronger claim than the
    # stock baseline. `undeclared` never appears in a receipt — it refused above.
    enumeration_fact = {
        "schema_version": enum.schema_version,
        "host": enum.host,
        "taken_at": enum.taken_at,
        "collection_status": enum.collection_status,
        "tool_sha256": enum.tool_sha256,
        "observed": sorted(enum.observed_ports),
        "verdicts": {str(p): "declared" if p in box.declared_ports else "baseline"
                     for p in sorted(enum.observed_ports)},
    }
    enumeration_digest = hashlib.sha256(json.dumps(
        enumeration_fact, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    artifacts.append(_artifact("slot", subject, parent, {
        "handles": len(cohort),
        "enumeration": enumeration_fact,
        "ceiling": ceiling.public(),
        "granted": sorted(cohort),
    }))
    chain = tuple(artifacts)

    grant = SlotGrant(
        box=box.box,
        declared_ceiling=ceiling.declared,
        effective_ceiling=ceiling.effective,
        binding=ceiling.binding,
        handles=tuple(sorted(cohort)),
        slots={h: bound[h].name for h in sorted(cohort)},
        chain_digest=chain[-1].digest,
        enumeration_digest=enumeration_digest,
    )
    return Admission(chain, grant)
