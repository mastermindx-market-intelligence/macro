"""A08 three-clock census of committed SNI artifacts (commission 8659).

SNI-local DRAFT contract. It CONSUMES owner-supplied timestamps and opaque
identity strings already stored on committed artifacts. It does not mint,
derive, or guess canonical HK/US issuer or security identifiers. It does
not re-implement Data OS identity, Company Event/Earnings, FIF, Capital
Structure, Stock Identity, Options, Research Vault, or qledger/Evaluation.

Nothing in this module feeds a ranker, gate, sizer, signal, escalation, or
trade path. rank_authority, gate_authority, size_authority, signal_authority,
escalation_authority and trade_authority stay literal false; bind_authority
raises if a caller tries to set any of them true.

This is a census of time-bearing field names and their clock class. It is
not the SNI three-clock VIEW (R1-gated, unbuilt). Session/holiday/DST
placement is owned by s2_clocklaw.py and the CLK lane; this file does not
re-test first_session_after.

Fixtures used by mutants are synthetic copies under tmp_path.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Optional, Sequence, Union

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover - keep a pure-python load path
    yaml = None


REPO_ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Authority: every flag stays literal false; setting one true is a hard refuse.
# ---------------------------------------------------------------------------

AUTHORITY_FLAG_KEYS = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)


class AuthorityRefusal(ValueError):
    """Caller tried to set an SNI authority flag true."""


def bind_authority(flags: Optional[Mapping[str, Any]] = None) -> dict[str, bool]:
    """Return the frozen-false authority map. Raise if any flag is not False."""
    bound = {k: False for k in AUTHORITY_FLAG_KEYS}
    if flags is None:
        return bound
    for key in AUTHORITY_FLAG_KEYS:
        if key in flags and flags[key] is not False:
            raise AuthorityRefusal(
                f"{key} must stay literal false; the TCK census does not "
                "feed a ranker, gate, sizer, signal, escalation, or trade path"
            )
    return bound


AUTHORITY_FLAGS = bind_authority()

# ---------------------------------------------------------------------------
# Clock vocabulary (s2_clocklaw.py): ECONOMIC / OWNER_KNOWN / PUBLICATION
# plus SESSION_ANCHOR (derived trading-session clock) and OTHER.
# ---------------------------------------------------------------------------

ECONOMIC = "ECONOMIC"
OWNER_KNOWN = "OWNER_KNOWN"
PUBLICATION = "PUBLICATION"
SESSION_ANCHOR = "SESSION_ANCHOR"
OTHER = "OTHER"
CLOCKS = (ECONOMIC, OWNER_KNOWN, PUBLICATION, SESSION_ANCHOR, OTHER)

# Field -> exactly one clock. One-line justification on each entry.
# Observed keys from the INPUTS walk plus vocabulary the mutant / later
# authors will hit. A new observed time-bearing key not listed here fails
# test_tck_01 (that is the ratchet).
CLOCK_MAP: dict[str, Union[str, Sequence[str]]] = {
    # --- observed on committed structured artifacts ---
    "anchor_session_date": SESSION_ANCHOR,  # S1 residual window origin session
    "coverage_date": SESSION_ANCHOR,  # S1 horizon-end session (null = no endpoint)
    "coverage_1.0": OTHER,  # Wilson/bootstrap statistical coverage, not a clock
    "coverage_1.96": OTHER,  # 1.96-sigma statistical coverage, not a clock
    "as_of": OWNER_KNOWN,  # snapshot date the profile/report was taken as-of
    "detected_at": OWNER_KNOWN,  # when this SNI run recorded contamination
    "observed_at_utc": OWNER_KNOWN,  # when the profile author observed the repo
    "opener_t_avail_utc": PUBLICATION,  # event t_avail (release/availability)
    "s_date": SESSION_ANCHOR,  # counting-clock first session s(c) after t_avail
    "s_hk": SESSION_ANCHOR,  # HK-clock first session s(HK)
    "s_us": SESSION_ANCHOR,  # US-clock first session s(US)
    "cluster_key": SESSION_ANCHOR,  # episode cluster dated by the session
    "valid_from": ECONOMIC,  # world-true start of a then-known identity fact
    "valid_to": ECONOMIC,  # world-true end of that fact; null = open-ended
    # --- vocabulary (clock law / mission / owner citations); mutant m2 uses event_date ---
    "event_date": ECONOMIC,  # calendar date the event was true in the world
    "period_end": ECONOMIC,  # fiscal/reporting period end
    "fiscal_period_end": ECONOMIC,  # fiscal period end (owner-supplied)
    "fiscal_year_end": ECONOMIC,  # fiscal year end (owner-supplied)
    "filed_at": PUBLICATION,  # filing timestamp
    "published_at": PUBLICATION,  # publication timestamp
    "released_at": PUBLICATION,  # release timestamp
    "announced_at": PUBLICATION,  # announcement timestamp
    "disclosure_date": PUBLICATION,  # DISCLOSURE_DATE anchor in s2_clocklaw
    "t_avail": PUBLICATION,  # availability instant (clock-law input)
    "t_avail_utc": PUBLICATION,  # availability instant in UTC
    "ingested_at": OWNER_KNOWN,  # when the owning store ingested the row
    "known_at": OWNER_KNOWN,  # when the owning system knew the fact
    "identity_resolved_as_of": OWNER_KNOWN,  # when identity was resolved
    "fetched_at": OWNER_KNOWN,  # when a fetch observed the source
    "generated_at": OWNER_KNOWN,  # when a derived artifact was generated
    "computed_at": OWNER_KNOWN,  # when a statistic was computed
    "master_generated_at": OWNER_KNOWN,  # when security_master was generated
    "effective_at": ECONOMIC,  # owner effective date (not a listing date)
    "hk_session_date": SESSION_ANCHOR,  # HK trading session date
    "session_date": SESSION_ANCHOR,  # generic trading session date
}

# Spec discovery: keys ending _at/_date/_time/_as_of, or named
# date/as_of/period_end/fiscal_*/anchor_*/coverage_*. Extra names are
# timestamps that do not match that regex but are observed as clocks.
_TIME_KEY_EXACT = frozenset({"date", "as_of", "period_end"})
_TIME_KEY_PREFIXES = ("fiscal_", "anchor_", "coverage_")
_TIME_KEY_SUFFIXES = ("_at", "_date", "_time", "_as_of")
_TIME_KEY_EXTRA = frozenset({
    "observed_at_utc",
    "opener_t_avail_utc",
    "t_avail",
    "t_avail_utc",
    "s_hk",
    "s_us",
    "valid_from",
    "valid_to",
    "cluster_key",
})

# Ordering-law pairs on the SAME dict (same fact row). SESSION_ANCHOR is
# not in these inequalities; CLK owns s(c) vs t_avail.
COMPARABLE_PAIRS: tuple[tuple[str, str], ...] = (
    (PUBLICATION, ECONOMIC),       # PUBLICATION >= ECONOMIC
    (OWNER_KNOWN, PUBLICATION),    # OWNER_KNOWN >= PUBLICATION
)


class ClockCensusFailure(AssertionError):
    """A three-clock census check failed."""


@dataclass(frozen=True)
class TimeHit:
    path: str
    row: str
    field: str
    value: Any
    family: str


@dataclass
class Census:
    hits: list[TimeHit] = field(default_factory=list)
    files_walked: list[str] = field(default_factory=list)
    dict_rows: list[tuple[str, dict]] = field(default_factory=list)
    then_known: list[dict] = field(default_factory=list)
    then_known_md_text: str = ""
    file_count_by_family: Counter = field(default_factory=Counter)

    def counts(self) -> dict[tuple[str, str], int]:
        c: dict[tuple[str, str], int] = Counter()
        for hit in self.hits:
            clock = primary_clock(hit.field)
            if clock is None:
                continue
            c[(hit.field, clock)] += 1
        return dict(c)


def primary_clock(
    field_name: str,
    clock_map: Mapping[str, Union[str, Sequence[str]]] = CLOCK_MAP,
) -> Optional[str]:
    raw = clock_map.get(field_name)
    if raw is None:
        return None
    if isinstance(raw, (list, tuple)):
        return str(raw[0]) if raw else None
    return str(raw)


def clocks_of(
    field_name: str,
    clock_map: Mapping[str, Union[str, Sequence[str]]] = CLOCK_MAP,
) -> list[str]:
    raw = clock_map.get(field_name)
    if raw is None:
        return []
    if isinstance(raw, (list, tuple, set)):
        return [str(c) for c in raw]
    return [str(raw)]


def is_time_bearing_key(key: Any) -> bool:
    if not isinstance(key, str):
        return False
    if key in _TIME_KEY_EXACT or key in _TIME_KEY_EXTRA:
        return True
    if key.startswith(_TIME_KEY_PREFIXES):
        return True
    return any(key.endswith(suf) for suf in _TIME_KEY_SUFFIXES)


def artifact_family(rel: str) -> str:
    posix = rel.replace("\\", "/")
    if "/runs/s1_residual_v1_1/manifests/" in posix:
        return "s1_residual_v1_1/manifests"
    if "/runs/s1_residual_v1_1/observations/" in posix:
        return "s1_residual_v1_1/observations"
    if "/runs/s1_residual_v1_1/results/" in posix:
        return "s1_residual_v1_1/results"
    if "/runs/s1_residual_v1_1/" in posix:
        return "s1_residual_v1_1/root"
    if "/runs/s2_event_response_v1_1/manifests/" in posix:
        return "s2_event_response_v1_1/manifests"
    if "/runs/s2_event_response_v1_1/observations/" in posix:
        return "s2_event_response_v1_1/observations"
    if "/runs/s2_event_response_v1_1/results/" in posix:
        return "s2_event_response_v1_1/results"
    if "/runs/s2_event_response_v1_1/" in posix:
        return "s2_event_response_v1_1/root"
    if "/evidence/Alibaba/" in posix:
        return "evidence/Alibaba"
    if "/evidence/Tencent/" in posix:
        return "evidence/Tencent"
    if "/us_stress/profiles/" in posix:
        return "us_stress/profiles"
    if posix.endswith("THEN_KNOWN_VERIFICATION.md"):
        return "us_stress/THEN_KNOWN_VERIFICATION"
    if "/coverage_profiles/" in posix:
        return "coverage_profiles"
    if posix.endswith("s2_clocklaw.py"):
        return "event_response/s2_clocklaw"
    return "other"


def iter_input_paths(root: Path) -> list[Path]:
    """Every INPUTS artifact. Missing trees yield an empty list (sparse)."""
    out: list[Path] = []
    runs = root / "research" / "single_name_intelligence" / "runs"
    if runs.is_dir():
        for run_dir in sorted(runs.glob("*_v1_1")):
            if not run_dir.is_dir():
                continue
            man = run_dir / "manifests"
            if man.is_dir():
                out.extend(sorted(man.glob("*.jsonl")))
            obs = run_dir / "observations"
            if obs.is_dir():
                out.extend(sorted(p for p in obs.iterdir() if p.is_file()))
            res = run_dir / "results"
            if res.is_dir():
                out.extend(sorted(res.glob("*.json")))
            out.extend(sorted(run_dir.glob("INPUT_MANIFEST*")))
            out.extend(sorted(run_dir.glob("VERSION_RECORD*")))
    evidence = root / "research" / "single_name_intelligence" / "evidence"
    for issuer in ("Alibaba", "Tencent"):
        folder = evidence / issuer
        if folder.is_dir():
            out.extend(sorted(p for p in folder.iterdir() if p.is_file()))
    profiles = (
        root / "research" / "single_name_intelligence" / "us_stress" / "profiles"
    )
    if profiles.is_dir():
        out.extend(sorted(p for p in profiles.iterdir() if p.is_file()))
    then_known = (
        root / "research" / "single_name_intelligence" / "us_stress"
        / "THEN_KNOWN_VERIFICATION.md"
    )
    if then_known.is_file():
        out.append(then_known)
    cov = root / "config" / "single_name_intelligence" / "coverage_profiles"
    if cov.is_dir():
        out.extend(sorted(cov.glob("*.yml")))
        out.extend(sorted(cov.glob("*.yaml")))
    clocklaw = (
        root / "research" / "single_name_intelligence" / "event_response"
        / "s2_clocklaw.py"
    )
    if clocklaw.is_file():
        out.append(clocklaw)
    # unique, stable order
    seen: set[Path] = set()
    uniq: list[Path] = []
    for p in out:
        if p in seen:
            continue
        seen.add(p)
        uniq.append(p)
    return uniq


def _fallback_yaml_pairs(text: str) -> list[tuple[str, Any]]:
    """Pure-python key/value scrape used when PyYAML is absent."""
    pairs: list[tuple[str, Any]] = []
    for match in re.finditer(
        r"^([A-Za-z0-9_.]+):\s*(.*)$", text, flags=re.MULTILINE
    ):
        key = match.group(1)
        raw = match.group(2).strip()
        if raw in {"|", ">", ""}:
            continue
        if raw in {"null", "~", "Null"}:
            val: Any = None
        else:
            val = raw.strip("\"'")
        pairs.append((key, val))
    return pairs


def load_structured(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix == ".json":
        return json.loads(text)
    if suffix == ".jsonl":
        rows = []
        for i, line in enumerate(text.splitlines()):
            if not line.strip():
                continue
            rows.append((i, json.loads(line)))
        return ("jsonl", rows)
    if suffix in {".yml", ".yaml"}:
        if yaml is not None:
            return yaml.safe_load(text)
        return ("yaml-fallback", _fallback_yaml_pairs(text))
    return ("text", text)


def iter_dicts(obj: Any, path: str) -> Iterator[tuple[str, dict]]:
    if isinstance(obj, dict):
        yield path, obj
        for key, val in obj.items():
            yield from iter_dicts(val, f"{path}.{key}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            yield from iter_dicts(item, f"{path}[{i}]")
    elif isinstance(obj, tuple) and obj and obj[0] == "jsonl":
        for i, row in obj[1]:
            yield from iter_dicts(row, f"{path}:{i}")
    elif isinstance(obj, tuple) and obj and obj[0] == "yaml-fallback":
        yield path, {k: v for k, v in obj[1]}


def parse_timestamp(value: Any) -> Optional[datetime]:
    """Parse a single stamp. Ranges (`..`) and non-stamps return None."""
    if value is None or value is False or value is True:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or ".." in text:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        year, month, day = (int(p) for p in text.split("-"))
        return datetime(year, month, day, tzinfo=timezone.utc)
    iso = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(iso)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def stamp_string(value: Any) -> Optional[str]:
    if value is None or isinstance(value, (dict, list)):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, str):
        text = value.strip()
        return text if text and parse_timestamp(text) is not None else None
    return None


def collect_hits_from_obj(
    obj: Any, rel: str, family: str, hits: list[TimeHit]
) -> None:
    if isinstance(obj, tuple) and obj and obj[0] == "jsonl":
        for i, row in obj[1]:
            collect_hits_from_obj(row, rel, family, hits)
            # row id is encoded in TimeHit.row via walk
            for hit_i, hit in enumerate(hits):
                if hit.path == rel and hit.row == "$":
                    hits[hit_i] = TimeHit(rel, f":{i}", hit.field, hit.value, family)
        return
    if isinstance(obj, tuple) and obj and obj[0] == "yaml-fallback":
        for key, val in obj[1]:
            if is_time_bearing_key(key):
                hits.append(TimeHit(rel, "$", key, val, family))
        return
    if isinstance(obj, tuple) and obj and obj[0] == "text":
        return
    for dpath, mapping in iter_dicts(obj, "$"):
        for key, val in mapping.items():
            if is_time_bearing_key(key):
                hits.append(TimeHit(rel, dpath, key, val, family))


def extract_then_known(obj: Any, rel: str) -> list[dict]:
    found: list[dict] = []
    as_of = None
    observed = None
    if isinstance(obj, dict):
        as_of = obj.get("as_of")
        obs = obj.get("observation")
        if isinstance(obs, dict):
            observed = obs.get("observed_at_utc")
        entries = obj.get("then_known")
        if isinstance(entries, list):
            for i, item in enumerate(entries):
                if not isinstance(item, dict):
                    continue
                rec = dict(item)
                rec["_profile_as_of"] = as_of
                rec["_profile_observed_at_utc"] = observed
                rec["_path"] = rel
                rec["_index"] = i
                found.append(rec)
    if isinstance(obj, tuple) and obj and obj[0] == "yaml-fallback":
        pairs = obj[1]
        as_ofs = [v for k, v in pairs if k == "as_of"]
        observed_s = [v for k, v in pairs if k == "observed_at_utc"]
        as_of = as_ofs[0] if as_ofs else None
        observed = observed_s[0] if observed_s else None
        # reconstruct items in order: each `field:` starts an entry
        current: Optional[dict] = None
        for key, val in pairs:
            if key == "field" and isinstance(val, str) and val in {
                "ticker", "listing", "share_class", "sector_etf",
            }:
                if current is not None:
                    found.append(current)
                current = {
                    "field": val,
                    "_profile_as_of": as_of,
                    "_profile_observed_at_utc": observed,
                    "_path": rel,
                    "_index": len(found),
                }
            elif current is not None and key in {
                "value", "valid_from", "valid_to", "source", "verified",
            }:
                if key == "verified":
                    current[key] = str(val).lower() in {"true", "yes"}
                else:
                    current[key] = val
        if current is not None:
            found.append(current)
    return found


def run_census(root: Path = REPO_ROOT) -> Census:
    census = Census()
    for path in iter_input_paths(root):
        rel = path.relative_to(root).as_posix()
        census.files_walked.append(rel)
        fam = artifact_family(rel)
        census.file_count_by_family[fam] += 1
        suffix = path.suffix.lower()
        if suffix in {".json", ".jsonl", ".yml", ".yaml"}:
            obj = load_structured(path)
            collect_hits_from_obj(obj, rel, fam, census.hits)
            for dpath, mapping in iter_dicts(obj, rel):
                census.dict_rows.append((f"{rel}:{dpath}", mapping))
            if fam == "us_stress/profiles":
                census.then_known.extend(extract_then_known(obj, rel))
        elif path.name == "THEN_KNOWN_VERIFICATION.md":
            census.then_known_md_text = path.read_text(encoding="utf-8")
        # .md evidence packs and s2_clocklaw.py are walked (listed) but are
        # prose / vocabulary, not structured rows.
    census.files_walked.sort()
    return census


def census_digest(census: Census) -> tuple[str, str]:
    counts = census.counts()
    lines = [
        f"{field}\t{clock}\t{n}"
        for (field, clock), n in sorted(counts.items())
    ]
    blob = "\n".join(lines) + "\n"
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return digest, blob


def check_tck_01(
    hits: Sequence[TimeHit],
    clock_map: Mapping[str, Union[str, Sequence[str]]] = CLOCK_MAP,
) -> list[str]:
    failures: list[str] = []
    seen: set[str] = set()
    for hit in hits:
        if hit.field in seen:
            continue
        seen.add(hit.field)
        if hit.field not in clock_map:
            failures.append(
                f"unclassified time-bearing field {hit.field!r} "
                f"(example {hit.path}:{hit.row})"
            )
    return failures


def check_tck_02(
    clock_map: Mapping[str, Union[str, Sequence[str]]] = CLOCK_MAP,
    hits: Optional[Sequence[TimeHit]] = None,
) -> list[str]:
    failures: list[str] = []
    inverted: dict[str, list[str]] = defaultdict(list)
    for field_name, raw in clock_map.items():
        clocks = clocks_of(field_name, {field_name: raw})
        inverted[field_name].extend(clocks)
    for field_name, clocks in sorted(inverted.items()):
        distinct = sorted(set(clocks))
        if len(distinct) > 1:
            failures.append(
                f"field {field_name!r} mapped to multiple clocks: {distinct}"
            )
        elif len(clocks) > 1:
            failures.append(
                f"field {field_name!r} listed under clock {clocks[0]!r} twice"
            )
    if hits:
        by_field: dict[str, set[str]] = defaultdict(set)
        for hit in hits:
            clock = primary_clock(hit.field, clock_map)
            if clock:
                by_field[hit.field].add(clock)
        for field_name, clocks in sorted(by_field.items()):
            if len(clocks) > 1:
                failures.append(
                    f"field {field_name!r} classified as {sorted(clocks)} "
                    "across artifacts"
                )
    return failures


def check_tck_03(
    dict_rows: Sequence[tuple[str, dict]],
    clock_map: Mapping[str, Union[str, Sequence[str]]] = CLOCK_MAP,
) -> list[str]:
    """PUBLICATION >= ECONOMIC and OWNER_KNOWN >= PUBLICATION on the same dict."""
    failures: list[str] = []
    for row_id, mapping in dict_rows:
        by_clock: dict[str, list[tuple[str, datetime]]] = defaultdict(list)
        for key, val in mapping.items():
            clock = primary_clock(key, clock_map)
            if clock is None:
                continue
            parsed = parse_timestamp(val)
            if parsed is None:
                continue
            by_clock[clock].append((key, parsed))
        for left_clock, right_clock in COMPARABLE_PAIRS:
            for lname, lstamp in by_clock.get(left_clock, []):
                for rname, rstamp in by_clock.get(right_clock, []):
                    if lstamp < rstamp:
                        failures.append(
                            f"{row_id}: {left_clock} {lname}={lstamp.isoformat()} "
                            f"< {right_clock} {rname}={rstamp.isoformat()}"
                        )
    return failures


def check_tck_04(
    dict_rows: Sequence[tuple[str, dict]],
    clock_map: Mapping[str, Union[str, Sequence[str]]] = CLOCK_MAP,
) -> list[str]:
    """Identical timestamp strings on ECONOMIC and OWNER_KNOWN of one dict."""
    findings: list[str] = []
    for row_id, mapping in dict_rows:
        econ = []
        known = []
        for key, val in mapping.items():
            clock = primary_clock(key, clock_map)
            stamp = stamp_string(val)
            if stamp is None or clock is None:
                continue
            if clock == ECONOMIC:
                econ.append((key, stamp))
            elif clock == OWNER_KNOWN:
                known.append((key, stamp))
        for ek, ev in econ:
            for ok, ov in known:
                if ev == ov:
                    findings.append(
                        f"{row_id}: ECONOMIC {ek} and OWNER_KNOWN {ok} "
                        f"share {ev!r}"
                    )
    return findings


_VERIFIED_TOTAL_RE = re.compile(
    r"0 verified\s*/\s*28 total", re.IGNORECASE
)
_UNVERIFIED_RULE_RE = re.compile(
    r"unverified date must not be treated as a then-known\s+fact",
    re.IGNORECASE,
)


def check_tck_05(
    then_known: Sequence[Mapping[str, Any]],
    md_text: str,
) -> list[str]:
    """Then-known facts: known/published <= use time; MD rule cross-check."""
    failures: list[str] = []
    if not _VERIFIED_TOTAL_RE.search(md_text):
        failures.append(
            "THEN_KNOWN_VERIFICATION.md does not state '0 verified / 28 total'"
        )
    if not _UNVERIFIED_RULE_RE.search(md_text):
        failures.append(
            "THEN_KNOWN_VERIFICATION.md missing fail-closed rule "
            "(unverified date must not be treated as a then-known fact)"
        )
    if len(then_known) != 28:
        failures.append(
            f"expected 28 then_known entries across 7 profiles, got {len(then_known)}"
        )
    verified_true = 0
    for rec in then_known:
        path = rec.get("_path", "?")
        idx = rec.get("_index", "?")
        loc = f"{path}:then_known[{idx}]"
        verified = rec.get("verified")
        use_raw = rec.get("_profile_as_of")
        use_ts = parse_timestamp(use_raw)
        if use_ts is None:
            failures.append(f"{loc}: profile as_of is not a parseable use time")
            continue
        if verified is True:
            verified_true += 1
            known_candidates = [
                rec.get("known_at"),
                rec.get("published_at"),
                rec.get("ingested_at"),
                rec.get("filed_at"),
            ]
            parsed_known = [parse_timestamp(v) for v in known_candidates]
            parsed_known = [p for p in parsed_known if p is not None]
            valid_from = parse_timestamp(rec.get("valid_from"))
            if not parsed_known and valid_from is None:
                failures.append(
                    f"{loc}: verified true but no known/published/valid_from "
                    "time to check against use time"
                )
                continue
            claim_ts = max(parsed_known) if parsed_known else valid_from
            if claim_ts is not None and claim_ts > use_ts:
                failures.append(
                    f"{loc}: then-known claim {claim_ts.isoformat()} > "
                    f"use as_of {use_ts.isoformat()}"
                )
        elif verified is False:
            # Fail-closed: unverified dates are not then-known facts.
            # Do not treat valid_from as owner-known / publication time.
            continue
        else:
            failures.append(f"{loc}: verified must be boolean, got {verified!r}")
    if verified_true != 0:
        failures.append(
            f"THEN_KNOWN_VERIFICATION.md says 0 verified; profiles have "
            f"{verified_true} verified:true"
        )
    return failures


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def census() -> Census:
    bind_authority(AUTHORITY_FLAGS)
    return run_census(REPO_ROOT)


def test_tck_01_every_time_field_is_classified(census: Census) -> None:
    failures = check_tck_01(census.hits, CLOCK_MAP)
    assert failures == [], "\n".join(failures)
    observed = sorted({hit.field for hit in census.hits})
    assert observed, "census walked no time-bearing keys"
    assert len(census.files_walked) >= 60


def test_tck_02_no_field_has_two_clocks(census: Census) -> None:
    failures = check_tck_02(CLOCK_MAP, census.hits)
    assert failures == [], "\n".join(failures)
    for field_name, raw in CLOCK_MAP.items():
        clocks = clocks_of(field_name, CLOCK_MAP)
        assert len(clocks) == 1, field_name
        assert clocks[0] in CLOCKS, f"{field_name} -> {clocks[0]}"


def test_tck_03_ordering_law(census: Census) -> None:
    failures = check_tck_03(census.dict_rows, CLOCK_MAP)
    # No committed row currently co-locates PUBLICATION with ECONOMIC, or
    # OWNER_KNOWN with PUBLICATION. Vacuous success is recorded; mutants
    # prove the checker fires (test_tck_07 m2).
    assert failures == [], "\n".join(failures)


def test_tck_04_no_same_value_reuse_across_clocks(census: Census) -> None:
    findings = check_tck_04(census.dict_rows, CLOCK_MAP)
    # Count is the result. Zero copy-through on committed same-dict rows.
    assert len(findings) == 0, (
        f"copy-through count {len(findings)}:\n" + "\n".join(findings)
    )


def test_tck_05_then_known_respected(census: Census) -> None:
    assert census.then_known_md_text, "THEN_KNOWN_VERIFICATION.md not walked"
    failures = check_tck_05(census.then_known, census.then_known_md_text)
    assert failures == [], "\n".join(failures)


def test_tck_06_census_is_stable(census: Census) -> None:
    digest_a, blob_a = census_digest(census)
    again = run_census(REPO_ROOT)
    digest_b, blob_b = census_digest(again)
    assert blob_a == blob_b
    assert digest_a == digest_b
    assert digest_a == hashlib.sha256(blob_a.encode("utf-8")).hexdigest()
    # Non-empty sorted digest: at least the high-count S1 session fields.
    assert "anchor_session_date\tSESSION_ANCHOR\t" in blob_a
    assert "opener_t_avail_utc\tPUBLICATION\t" in blob_a
    assert "valid_from\tECONOMIC\t" in blob_a
    assert "as_of\tOWNER_KNOWN\t" in blob_a


def _copied_s2_row(tmp_path: Path) -> dict:
    src = (
        REPO_ROOT
        / "research"
        / "single_name_intelligence"
        / "runs"
        / "s2_event_response_v1_1"
        / "manifests"
        / "P04_h5.jsonl"
    )
    dst = tmp_path / "P04_h5.copy.jsonl"
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    line = next(ln for ln in dst.read_text(encoding="utf-8").splitlines() if ln.strip())
    return json.loads(line)


def _copied_s1_row(tmp_path: Path) -> dict:
    src = (
        REPO_ROOT
        / "research"
        / "single_name_intelligence"
        / "runs"
        / "s1_residual_v1_1"
        / "manifests"
        / "P01_adr_baba_5.jsonl"
    )
    dst = tmp_path / "P01_adr_baba_5.copy.jsonl"
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    line = next(ln for ln in dst.read_text(encoding="utf-8").splitlines() if ln.strip())
    return json.loads(line)


@pytest.mark.parametrize("mutant_id", ["m1", "m2", "m3"])
def test_tck_07_mutants_are_caught(tmp_path: Path, mutant_id: str) -> None:
    """Positive controls: unclassified, pub<econ, dual-clock map each fail."""
    if mutant_id == "m1":
        row = _copied_s1_row(tmp_path)
        row["foo_at"] = "2020-01-01T00:00:00Z"
        hits = [
            TimeHit("mutant://m1", "0", key, val, "mutant")
            for key, val in row.items()
            if is_time_bearing_key(key)
        ]
        failures = check_tck_01(hits, CLOCK_MAP)
        assert any("foo_at" in f for f in failures), failures
        return
    if mutant_id == "m2":
        row = _copied_s2_row(tmp_path)
        row["opener_t_avail_utc"] = "2010-01-01T00:00:00+00:00"
        row["event_date"] = "2020-01-01"
        failures = check_tck_03([("mutant://m2:0", row)], CLOCK_MAP)
        assert failures, "m2 must fail tck_03 (publication before economic)"
        assert any("PUBLICATION" in f and "ECONOMIC" in f for f in failures)
        return
    if mutant_id == "m3":
        mutated = dict(CLOCK_MAP)
        mutated["as_of"] = [OWNER_KNOWN, ECONOMIC]
        failures = check_tck_02(mutated)
        assert failures, "m3 must fail tck_02 (one field, two clocks)"
        assert any("as_of" in f for f in failures)
        return
    raise AssertionError(f"unknown mutant {mutant_id}")
