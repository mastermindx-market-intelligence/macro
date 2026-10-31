"""Read retained Schedule 13D assertions without publishing owner semantics.

The operator supplies an already qualified local acquisition bundle and native
repository. Hashes bind the read to those records; they do not independently
authenticate the acquisition clocks or grant source-use rights. This is not an
HTTP input boundary, canonical alias publisher, vehicle registry or K2C adapter.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
from urllib.parse import urlsplit

from lib.dataos.identity import VendorAliasTable
from lib.dataos.sec_cusip_binding import build_sec13d_cusip_alias
from lib.dataos.sec_schedule13d import parse_schedule13d_evidence
from lib.evidence_foundation import ALL_FALSE_AUTHORITY

SCHEMA = "dataos.retained_sec13d_research.v1"
_MASTER_PATH = "data/reference/security_master.parquet"
_HEX = re.compile(r"[0-9a-f]{64}")
_SEC_PATH = re.compile(r"/Archives/edgar/data/([0-9]{1,10})/([0-9]{18})/([A-Za-z0-9_.-]+)")
_UTC = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|\+00:00)")


class RetainedResearchRefusal(ValueError):
    """A retained input cannot support this research read."""


def _clock(value):
    if not isinstance(value, str) or not _UTC.fullmatch(value):
        raise RetainedResearchRefusal("explicit UTC clock required")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RetainedResearchRefusal("invalid UTC clock") from exc
    if result.utcoffset() != timedelta(0):
        raise RetainedResearchRefusal("UTC clock required")
    return result


def _read(root, name, maximum):
    if Path(name).name != name or name in {".", ".."}:
        raise RetainedResearchRefusal("retained filename required")
    try:
        fd = os.open(Path(root) / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= maximum:
                raise RetainedResearchRefusal("retained regular file outside read bound")
            raw = stream.read(maximum + 1)
            after = os.fstat(stream.fileno())
        if len(raw) != before.st_size or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise RetainedResearchRefusal("retained file changed during read")
        return raw
    except OSError as exc:
        raise RetainedResearchRefusal("retained file unavailable") from exc


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RetainedResearchRefusal("duplicate acquisition field")
        result[key] = value
    return result


def _record(root, name):
    try:
        value = json.loads(_read(root, name, 16384), object_pairs_hook=_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(RetainedResearchRefusal("nonfinite acquisition value")))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RetainedResearchRefusal("invalid acquisition record") from exc
    if type(value) is not dict:
        raise RetainedResearchRefusal("acquisition object required")
    digest = value.get("sha256")
    if not isinstance(digest, str) or not _HEX.fullmatch(digest):
        raise RetainedResearchRefusal("acquisition digest required")
    _clock(value.get("retained_at"))
    return value


def _sec_input(root, record, maximum):
    value = record.get("source_url")
    if not isinstance(value, str):
        raise RetainedResearchRefusal("SEC source URL required")
    url = urlsplit(value)
    match = _SEC_PATH.fullmatch(url.path)
    if (url.scheme != "https" or url.netloc != "www.sec.gov" or url.query or url.fragment or not match
            or type(record.get("status")) is not int or record["status"] != 200
            or type(record.get("bytes")) is not int or not 0 < record["bytes"] <= maximum):
        raise RetainedResearchRefusal("qualified SEC acquisition required")
    if _clock(record.get("request_started_at")) > _clock(record["retained_at"]):
        raise RetainedResearchRefusal("acquisition clocks reversed")
    raw = _read(root, match[3], maximum)
    if len(raw) != record["bytes"] or hashlib.sha256(raw).hexdigest() != record["sha256"]:
        raise RetainedResearchRefusal("retained bytes do not match acquisition")
    return raw, match


def _master_input(root, repository, record):
    commit = record.get("commit")
    if (not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit)
            or record.get("path") != _MASTER_PATH):
        raise RetainedResearchRefusal("pinned native master identity required")
    raw = _read(root, "security_master.parquet", 16 * 1024 * 1024)
    if hashlib.sha256(raw).hexdigest() != record["sha256"]:
        raise RetainedResearchRefusal("retained master digest mismatch")
    env = {**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0"}
    def git(*args):
        return subprocess.check_output(["git", "-C", str(repository), *args],
                                       env=env, stderr=subprocess.DEVNULL, timeout=30)
    try:
        identity = commit + ":" + _MASTER_PATH
        size = int(git("cat-file", "-s", identity).strip())
        if size != len(raw):
            raise RetainedResearchRefusal("native master size mismatch")
        if git("cat-file", "blob", identity) != raw:
            raise RetainedResearchRefusal("retained master differs from pinned native blob")
        # Repository dates are mutable: reject a contradiction, not attest a clock.
        committed = int(git("log", "-1", "--format=%ct", commit).strip())
        if datetime.fromtimestamp(committed, timezone.utc) > _clock(record["retained_at"]):
            raise RetainedResearchRefusal("native master commit follows claimed retention")
    except RetainedResearchRefusal:
        raise
    except (subprocess.SubprocessError, OSError, ValueError) as exc:
        raise RetainedResearchRefusal("pinned native master unavailable or inconsistent") from exc
    return raw


def read_retained_sec13d_research(bundle_root, repository, *, decision_cutoff, security_on):
    """Read local retained assertions and an unpublished assertion-day alias.

    The local operator owns acquisition qualification and repository custody.
    Matching records is integrity evidence, never independent clock attestation.
    No caller-supplied facts, semantic epochs, source-use grants or URLs are used
    as executable operations; only fixed local filenames and native Git reads.
    """
    cutoff = _clock(decision_cutoff)
    if not ALL_FALSE_AUTHORITY or any(value is not False for value in ALL_FALSE_AUTHORITY.values()):
        raise RetainedResearchRefusal("research authority contract changed")
    try:
        if not isinstance(security_on, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", security_on):
            raise ValueError("ISO date required")
        on = date.fromisoformat(security_on)
    except ValueError as exc:
        raise RetainedResearchRefusal("security validity date required") from exc
    out = {
        "schema": SCHEMA, "state": "UNAVAILABLE", "decision_cutoff": decision_cutoff,
        "requested_security_on": security_on, "refusals": [], "assertions": None,
        "security_binding": {"state": "UNAVAILABLE", "canonical_security_id": None},
        "source_references": [], "custody": {
            "state": "LOCAL_OPERATOR_QUALIFIED_RECORDS",
            "clock_authentication": "NOT_INDEPENDENTLY_ATTESTED_BY_THIS_READER",
            "canonical_owner_adoption": False,
        },
        "qualifications": {"ownership_continuity": "UNKNOWN", "economic_vehicle_class": None,
                           "decision_mode": None, "purpose_source_use": "UNKNOWN"},
        "authority": dict(ALL_FALSE_AUTHORITY), "k2c_admissible": False,
        "k3e_admissible": False, "recipe": None, "compiled": None, "persistence": "none",
    }
    filing_record = _record(bundle_root, "acquisition.json")
    if _clock(filing_record["retained_at"]) > cutoff:
        out["refusals"] = ["FILING_NOT_AVAILABLE_AT_CUTOFF"]
        return out
    filing_raw, filing_url = _sec_input(bundle_root, filing_record, 2 * 1024 * 1024)
    evidence = parse_schedule13d_evidence(filing_raw, expected_sha256=filing_record["sha256"],
                                         retained_at=_clock(filing_record["retained_at"]))
    if (int(filing_url[1]) != int(evidence.issuer_cik)
            or filing_url[2] != evidence.accession.replace("-", "")
            or filing_url[3] != evidence.accession + ".txt"):
        raise RetainedResearchRefusal("SEC acquisition identity conflicts with filing")
    out["state"] = "AVAILABLE_UNQUALIFIED"
    out["assertions"] = {
        "accession": evidence.accession, "form_type": evidence.form_type,
        "amendment_no": evidence.amendment_no, "previous_accession": evidence.previous_accession,
        "issuer_cik": evidence.issuer_cik, "issuer_name": evidence.issuer_name,
        "share_class": evidence.share_class, "reported_cusip": evidence.cusip,
        "event_on": evidence.event_on.isoformat(), "accepted_at": evidence.accepted_at.isoformat(),
        "retained_at": evidence.retained_at.isoformat(), "known_at": evidence.known_at.isoformat(),
        "assertion_scope": "AS_REPORTED_IN_THIS_FILING_NOT_CONTINUOUS_OWNERSHIP",
        "reporting_persons": [asdict(person) for person in evidence.reporting_persons],
        "control_statement": {"state": "VERBATIM_SOURCE_ASSERTION", "field": "item2.principalJob",
                              "text": evidence.item2_principal_job, "effective_interval": None},
        "position_statement": {"state": "VERBATIM_SOURCE_ASSERTION", "field": "item5.percentageOfClassSecurities",
                               "text": evidence.item5_percentage_of_class,
                               "consumer_performed_quantity_aggregation": False,
                               "source_cover_amounts_may_include_convertibles": True},
    }
    out["source_references"] = [{"role": "filing", **{key: filing_record[key] for key in
        ("source_url", "sha256", "bytes", "request_started_at", "retained_at")}}]
    registration = _record(bundle_root, "registration-acquisition.json")
    master = _record(bundle_root, "master-source.json")
    if max(_clock(registration["retained_at"]), _clock(master["retained_at"])) > cutoff:
        out["security_binding"]["reason"] = "IDENTITY_INPUT_NOT_AVAILABLE_AT_CUTOFF"
        return out
    registration_raw, registration_url = _sec_input(bundle_root, registration, 8 * 1024 * 1024)
    if int(registration_url[1]) != int(evidence.issuer_cik):
        raise RetainedResearchRefusal("SEC registration acquisition issuer mismatch")
    master_raw = _master_input(bundle_root, repository, master)
    alias = build_sec13d_cusip_alias(
        filing_raw, filing_sha256=filing_record["sha256"], filing_retained_at=_clock(filing_record["retained_at"]),
        registration_raw=registration_raw, registration_sha256=registration["sha256"],
        registration_retained_at=_clock(registration["retained_at"]),
        master_raw=master_raw, master_sha256=master["sha256"], master_retained_at=_clock(master["retained_at"]))
    identity = VendorAliasTable([alias]).resolve(alias.vendor, alias.vendor_symbol, on, decision_at=cutoff)
    out["security_binding"] = {
        "state": "ASSERTION_DAY_MATCHED_UNPUBLISHED" if identity else "UNAVAILABLE",
        "canonical_security_id": identity, "reason": None if identity else "VALID_DATE_NOT_SUPPORTED",
        "valid_from": alias.valid_from.isoformat(), "valid_to": alias.valid_to.isoformat(),
        "known_at": alias.known_at.isoformat(), "alias_published": False,
    }
    out["source_references"] += [
        {"role": "registration", **{key: registration[key] for key in
            ("source_url", "sha256", "bytes", "request_started_at", "retained_at")}},
        {"role": "native_master", **{key: master[key] for key in ("commit", "path", "sha256", "retained_at")}},
    ]
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--decision-cutoff", required=True)
    parser.add_argument("--security-on", required=True)
    args = parser.parse_args(argv)
    try:
        result = read_retained_sec13d_research(args.bundle_root, args.repository,
            decision_cutoff=args.decision_cutoff, security_on=args.security_on)
    except (ValueError, TypeError) as exc:
        parser.exit(2, "retained SEC research refused: " + str(exc) + "\n")
    print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))


if __name__ == "__main__":
    main()
