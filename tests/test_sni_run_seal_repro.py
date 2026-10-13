"""Recompute every uncovered recorded digest of the four sealed SNI runs.

SNI-local DRAFT contract tests. They consume owner-supplied opaque identity
ids, owner-sealed run artifacts, and owner TrialLedger hashing. They do not
feed a ranker, gate, sizer, signal, escalation, or trade path. Every
authority flag stays false; a caller that tries to set one true is refused.

A recorded digest is a content hash written into a sealed run's top-level
JSON / JSONL (membership_sha256, graded_membership_sha256, prereg_digest_*,
git blob pins, trial-ledger config_hash). Identity keys such as episode_key
and commit ids (input_ref, base, seal_commit_sha) are not content digests of
a file, spec, or ledger and are out of this inventory.

Recompute rules (never common.sni_seal):
  S1 canonical JSON  -> residual.s1_prereg.canonical_json
  S2 canonical JSON  -> event_response.s2_seal.canonical_json
  membership/graded  -> sha256 of that split's committed manifest lines
  git blob pins      -> git blob SHA-1 at the run's input_ref; when
                       input_ref is absent (depth-1 CI), working-tree
                       git blob SHA-1 of the pinned path if those bytes
                       equal the pin. Tests never fetch.
  config_hash        -> engine.trial_ledger._hash of the committed row
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "research/single_name_intelligence/residual"))
sys.path.insert(0, str(REPO / "research/single_name_intelligence/event_response"))

from engine import trial_ledger as _trial_ledger  # noqa: E402

RUNS_REL = Path("research/single_name_intelligence/runs")
RUN_IDS = (
    "s1_residual",
    "s1_residual_v1_1",
    "s2_event_response",
    "s2_event_response_v1_1",
)
RUN_DIRS = {name: REPO / RUNS_REL / name for name in RUN_IDS}

AUTHORITY_FLAGS = {
    "rank_authority": False,
    "gate_authority": False,
    "size_authority": False,
    "signal_authority": False,
    "escalation_authority": False,
    "trade_authority": False,
}

EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
S2_MEMBERSHIP_WIDTH = 27  # 3 protocols x 3 horizons x 3 splits
EXPECTED_DIGEST_COUNT = 931

# v1 trees keep this pointer to the v1.1 reprint; it is not a v1.1 artifact.
SUPERSEDED_POINTER = "SUPERSEDED_BY_V1_1.md"
SUPERSEDED_REASON = (
    "frozen v1 tree keeps a pointer to the v1.1 reprint; v1.1 trees carry "
    "VERSION_RECORD.json instead of this file"
)

S1_V1_TOP = frozenset({
    "CHALLENGER_UNIVERSE.json",
    "INPUT_MANIFEST.json",
    "LANE_MANIFEST.json",
    "PREREG_SPEC.json",
    "REPORT.md",
    "SEAL_AND_BUDGET.json",
    "SEAL_AND_BUDGET.md",
    SUPERSEDED_POINTER,
    "trial_ledger.jsonl",
    "manifests",
    "observations",
    "results",
})
S1_V11_TOP = frozenset({
    "CHALLENGER_UNIVERSE.json",
    "INPUT_MANIFEST.json",
    "LANE_MANIFEST.json",
    "PREREG_SPEC.json",
    "REPORT.md",
    "SEAL_AND_BUDGET.json",
    "SEAL_AND_BUDGET.md",
    "VERSION_RECORD.json",
    "trial_ledger.jsonl",
    "manifests",
    "observations",
    "results",
})
S2_V1_TOP = frozenset({
    "EVENT_CENSUS.json",
    "E_COVERAGE_CENSUS.json",
    "INPUT_MANIFEST.json",
    "LANE_MANIFEST.json",
    "PREREG_SPEC.json",
    "REPORT.md",
    "SEAL_AND_BUDGET.json",
    "SEAL_AND_BUDGET.md",
    SUPERSEDED_POINTER,
    "trial_ledger.jsonl",
    "manifests",
    "observations",
    "results",
})
S2_V11_TOP = frozenset({
    "EVENT_CENSUS.json",
    "E_COVERAGE_CENSUS.json",
    "INPUT_MANIFEST.json",
    "LANE_MANIFEST.json",
    "PREREG_SPEC.json",
    "REPORT.md",
    "SEAL_AND_BUDGET.json",
    "SEAL_AND_BUDGET.md",
    "VERSION_RECORD.json",
    "trial_ledger.jsonl",
    "manifests",
    "observations",
    "results",
})
PINNED_TOP_LEVEL = {
    "s1_residual": S1_V1_TOP,
    "s1_residual_v1_1": S1_V11_TOP,
    "s2_event_response": S2_V1_TOP,
    "s2_event_response_v1_1": S2_V11_TOP,
}

# v1 and v1.1 share input_ref 5ef7a7f3. VERSION_RECORD.json of each v1.1
# run names report/lead/membership-column repairs; none of those repairs
# change a repository-path pin. Named exceptions stay empty (do not
# exclude whole files).
CROSS_VERSION_PIN_EXCEPTIONS: dict[tuple[str, str], frozenset[str]] = {
    ("s1_residual", "s1_residual_v1_1"): frozenset(),
    ("s2_event_response", "s2_event_response_v1_1"): frozenset(),
}
STUDY_VERSION_PAIRS = (
    ("s1_residual", "s1_residual_v1_1"),
    ("s2_event_response", "s2_event_response_v1_1"),
)
PIN_BEARING_JSON = (
    "INPUT_MANIFEST.json",
    "SEAL_AND_BUDGET.json",
    "PREREG_SPEC.json",
    "CHALLENGER_UNIVERSE.json",
)
SKIP_NEEDS_INPUT_REF = (
    "changed since input_ref; exact check needs input_ref "
    "(never fetched in tests)"
)


def refuse_nonfalse_authority(flags=None) -> None:
    """Refuse any authority flag that is not literal False."""
    mapping = AUTHORITY_FLAGS if flags is None else flags
    if not isinstance(mapping, dict):
        raise ValueError(
            f"authority flags must be a dict (got {type(mapping).__name__})"
        )
    for key in (
        "rank_authority",
        "gate_authority",
        "size_authority",
        "signal_authority",
        "escalation_authority",
        "trade_authority",
    ):
        if key in mapping and mapping[key] is not False:
            raise ValueError(
                f"authority flag {key!r} is not literal False (got {mapping[key]!r})"
            )
    for key, value in mapping.items():
        name = str(key).strip().casefold()
        if name.endswith("_authority") or name in {
            "rank", "gate", "size", "signal", "escalation", "trade",
        }:
            if value is not False:
                raise ValueError(
                    f"authority flag {key!r} is not literal False (got {value!r})"
                )


refuse_nonfalse_authority(AUTHORITY_FLAGS)


def git_blob_sha1(data: bytes) -> str:
    """Git blob SHA-1 of raw bytes (`git hash-object --no-filters`)."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _working_tree_git_blob(path: str) -> str | None:
    """Git blob SHA-1 of working-tree bytes, or None if the file is absent."""
    fp = REPO / path
    if not fp.is_file():
        return None
    return git_blob_sha1(fp.read_bytes())


def _s2_v1_membership_covered() -> dict[tuple[str, str, str], str]:
    target = "tests/test_sni_s2_seal_integrity.py::test_committed_seal_verifies"
    out = {
        ("s2_event_response", "SEAL_AND_BUDGET.json", "prereg_digest_sha256"): target,
    }
    for i in range(S2_MEMBERSHIP_WIDTH):
        out[("s2_event_response", "SEAL_AND_BUDGET.json",
             f"membership_table[{i}].membership_sha256")] = target
    return out


# Mirrors the coverage table: only tests that recompute a recorded value and
# assert equality. Presence/format checks are not coverage.
COVERED_ELSEWHERE: dict[tuple[str, str, str], str] = {
    ("s1_residual_v1_1", "VERSION_RECORD.json", "prereg_digest_v1"):
        "tests/test_sni_s1_v1_1_hardening.py::test_h1_x1_report_language_and_digest",
    ("s1_residual_v1_1", "VERSION_RECORD.json", "prereg_digest_v1_1"):
        "tests/test_sni_s1_v1_1_hardening.py::test_h1_x1_report_language_and_digest",
    **_s2_v1_membership_covered(),
}


def sha256_file(path: Path) -> str:
    """Raw-file digest helper (committed bytes, never canonical JSON)."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _family(run: str) -> str:
    return "s1" if run.startswith("s1") else "s2"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_json(family: str, obj) -> str:
    if family == "s1":
        from s1_prereg import canonical_json
        return canonical_json(obj)
    from s2_seal import canonical_json
    return canonical_json(obj)


def _split_lines_sha256(rows: list[dict]) -> dict[str, str]:
    """S1 membership_sha256: sha256 of each split's canonical JSONL lines."""
    ordered = sorted(rows, key=lambda r: (r["horizon"], r["episode_key"]))
    by_split: dict[str, list[str]] = {}
    for row in ordered:
        line = json.dumps(row, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False) + "\n"
        by_split.setdefault(row["split"], []).append(line)
    return {
        split: hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()
        for split, lines in by_split.items()
    }


def membership_sha256_from_manifest(path: Path, split: str, family: str) -> str:
    """Recompute one split digest from a committed (or copied) manifest."""
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if family == "s1":
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        return _split_lines_sha256(rows).get(split, EMPTY_SHA256)
    lines: list[str] = []
    for line in text.splitlines():
        if line.strip():
            lines.append(line + "\n")
    payload = "".join(
        line for line in lines if json.loads(line).get("split") == split
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest() if payload else EMPTY_SHA256


@lru_cache(maxsize=None)
def _git_tree_blobs(ref: str) -> dict[str, str] | None:
    proc = subprocess.run(
        ["git", "ls-tree", "-r", ref],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    out: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        meta, path = line.split("\t", 1)
        out[path] = meta.split()[2]
    return out


@lru_cache(maxsize=None)
def _run_state(run: str) -> dict:
    root = RUN_DIRS[run]
    family = _family(run)
    seal = _load_json(root / "SEAL_AND_BUDGET.json")
    lane = _load_json(root / "LANE_MANIFEST.json")
    spec = _load_json(root / "PREREG_SPEC.json")
    input_manifest = _load_json(root / "INPUT_MANIFEST.json")
    version = None
    version_path = root / "VERSION_RECORD.json"
    if version_path.exists():
        version = _load_json(version_path)
    ledger_rows = []
    for line in (root / "trial_ledger.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            ledger_rows.append(json.loads(line))
    prereg = hashlib.sha256(
        _canonical_json(family, spec).encode("utf-8")
    ).hexdigest()
    input_ref = seal.get("input_ref") or seal.get("base") or lane.get("input_ref")
    membership: dict[tuple, str] = {}
    graded: dict[tuple, str] = {}
    if family == "s1":
        for path in sorted((root / "manifests").glob("*.jsonl")):
            stem = path.stem
            parts = stem.split("_")
            protocol_id = parts[0]
            horizon = int(parts[-1])
            subject = "_".join(parts[1:-1])
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                    if line.strip()]
            for split, digest in _split_lines_sha256(rows).items():
                membership[(protocol_id, subject, horizon, split)] = digest
    else:
        for protocol_id in ("P04", "P05", "P06"):
            for horizon in (5, 21, 63):
                path = root / "manifests" / f"{protocol_id}_h{horizon}.jsonl"
                text = path.read_text(encoding="utf-8") if path.exists() else ""
                lines = [line + "\n" for line in text.splitlines() if line.strip()]
                by_split: dict[str, list[str]] = {
                    "TRAIN": [], "TUNE": [], "QUARANTINE": [],
                }
                graded_by: dict[str, list[str]] = {
                    "TRAIN": [], "TUNE": [], "QUARANTINE": [],
                }
                for line in lines:
                    obj = json.loads(line)
                    split = obj["split"]
                    by_split.setdefault(split, []).append(line)
                    if not obj.get("flags", {}).get("census_only"):
                        graded_by.setdefault(split, []).append(line)
                for split in ("TRAIN", "TUNE", "QUARANTINE"):
                    payload = "".join(by_split.get(split, []))
                    membership[(protocol_id, horizon, split)] = (
                        hashlib.sha256(payload.encode("utf-8")).hexdigest()
                        if payload else EMPTY_SHA256
                    )
                    gpay = "".join(graded_by.get(split, []))
                    graded[(protocol_id, horizon, split)] = hashlib.sha256(
                        gpay.encode("utf-8")
                    ).hexdigest()
    return {
        "root": root,
        "family": family,
        "seal": seal,
        "lane": lane,
        "spec": spec,
        "input_manifest": input_manifest,
        "version": version,
        "ledger_rows": ledger_rows,
        "prereg": prereg,
        "input_ref": input_ref,
        "membership": membership,
        "graded": graded,
    }


def _s1_retirement_sha(state: dict, protocol_id: str) -> str:
    parts = []
    for horizon in (5, 21, 63):
        digest = state["membership"].get((protocol_id, "adr_baba", horizon, "TUNE"))
        if digest:
            parts.append(f"h={horizon}:{digest}")
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _s2_retirement_sha(state: dict, protocol_id: str) -> str:
    tune = [state["membership"][(protocol_id, horizon, "TUNE")]
            for horizon in (5, 21, 63)]
    return hashlib.sha256("|".join(tune).encode("utf-8")).hexdigest()


def _iter_recorded_digests() -> list[tuple[str, str, str, str, object]]:
    """(run, recording_file, key_path, kind, extra) for every recorded digest."""
    out: list[tuple[str, str, str, str, object]] = []
    for run in RUN_IDS:
        root = RUN_DIRS[run]
        family = _family(run)
        seal = _load_json(root / "SEAL_AND_BUDGET.json")
        lane = _load_json(root / "LANE_MANIFEST.json")
        spec = _load_json(root / "PREREG_SPEC.json")
        im = _load_json(root / "INPUT_MANIFEST.json")

        if family == "s1":
            for path, blob in (im.get("pins") or {}).items():
                out.append((run, "INPUT_MANIFEST.json", f"pins[{path}]", "git_blob", path))
            ident = im.get("identity_source") or {}
            if ident.get("blob"):
                out.append((run, "INPUT_MANIFEST.json", "identity_source.blob",
                            "git_blob", ident.get("path")))
            for key, rec in (im.get("s0_docs") or {}).items():
                out.append((run, "INPUT_MANIFEST.json", f"s0_docs.{key}.blob",
                            "git_blob", rec.get("path")))
        else:
            for path, rec in im.items():
                if isinstance(rec, dict) and "blob" in rec:
                    out.append((run, "INPUT_MANIFEST.json", f"[{path}].blob",
                                "git_blob", path))

        if "prereg_digest_sha256" in seal:
            out.append((run, "SEAL_AND_BUDGET.json", "prereg_digest_sha256",
                        "prereg", None))
        for i, row in enumerate(seal.get("membership_table") or []):
            out.append((run, "SEAL_AND_BUDGET.json",
                        f"membership_table[{i}].membership_sha256",
                        "membership", row))
            if "graded_membership_sha256" in row:
                out.append((run, "SEAL_AND_BUDGET.json",
                            f"membership_table[{i}].graded_membership_sha256",
                            "graded", row))
        for key, rec in (seal.get("s0_blob_ids") or {}).items():
            out.append((run, "SEAL_AND_BUDGET.json", f"s0_blob_ids.{key}.blob",
                        "git_blob", rec.get("path")))
        seal_im = seal.get("input_manifest")
        if isinstance(seal_im, dict):
            for path, blob in seal_im.items():
                if isinstance(blob, str) and len(blob) == 40:
                    out.append((run, "SEAL_AND_BUDGET.json",
                                f"input_manifest[{path}]", "git_blob", path))

        if "prereg_digest_sha256" in lane:
            out.append((run, "LANE_MANIFEST.json", "prereg_digest_sha256",
                        "prereg", None))
        for i, row in enumerate(lane.get("retirements") or []):
            if "membership_sha256" in row:
                out.append((run, "LANE_MANIFEST.json",
                            f"retirements[{i}].membership_sha256",
                            "s1_retirement", row))
        for i, row in enumerate(lane.get("info_leak") or []):
            if "membership_sha256" in row:
                out.append((run, "LANE_MANIFEST.json",
                            f"info_leak[{i}].membership_sha256",
                            "s2_retirement", row))

        for key, rec in (spec.get("s0_blob_ids") or {}).items():
            out.append((run, "PREREG_SPEC.json", f"s0_blob_ids.{key}.blob",
                        "git_blob", rec.get("path")))
        for key, rec in (spec.get("s0_sources") or {}).items():
            out.append((run, "PREREG_SPEC.json", f"s0_sources.{key}.blob",
                        "git_blob", rec.get("path")))
        for path, blob in (spec.get("input_pins") or {}).items():
            out.append((run, "PREREG_SPEC.json", f"input_pins[{path}]",
                        "git_blob", path))
        for i, row in enumerate(spec.get("membership_table") or []):
            out.append((run, "PREREG_SPEC.json",
                        f"membership_table[{i}].membership_sha256",
                        "membership", row))

        version_path = root / "VERSION_RECORD.json"
        if version_path.exists():
            version = _load_json(version_path)
            for key in ("prereg_digest_v1", "prereg_digest_v1_1"):
                if key in version:
                    out.append((run, "VERSION_RECORD.json", key, "prereg", None))

        challenger_path = root / "CHALLENGER_UNIVERSE.json"
        if challenger_path.exists():
            challenger = _load_json(challenger_path)
            for i, row in enumerate(challenger.get("admitted") or []):
                out.append((run, "CHALLENGER_UNIVERSE.json",
                            f"admitted[{i}].blob_sha256",
                            "git_blob", row.get("path")))

        for i, line in enumerate((root / "trial_ledger.jsonl").read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue
            row = json.loads(line)
            if "config_hash" in row:
                out.append((run, "trial_ledger.jsonl", f"L{i}.config_hash",
                            "config_hash", row))
            cfg = row.get("config") or {}
            if isinstance(cfg, dict) and "membership_sha256" in cfg:
                kind = "s1_retirement" if family == "s1" else "s2_retirement"
                out.append((run, "trial_ledger.jsonl",
                            f"L{i}.config.membership_sha256", kind, row))
    return out


def iter_path_pins(run_dir: Path) -> list[tuple[str, str, str, str]]:
    """(repository path, pinned value, digest kind, recording file).

    Reads only committed run JSON. No git, no data/.
    """
    out: list[tuple[str, str, str, str]] = []
    im_path = run_dir / "INPUT_MANIFEST.json"
    if im_path.is_file():
        im = _load_json(im_path)
        if any(k in im for k in ("pins", "s0_docs", "identity_source")):
            for path, blob in (im.get("pins") or {}).items():
                out.append((path, blob, "git_blob", "INPUT_MANIFEST.json"))
            ident = im.get("identity_source") or {}
            if ident.get("blob"):
                out.append((ident.get("path"), ident["blob"], "git_blob",
                            "INPUT_MANIFEST.json"))
            for rec in (im.get("s0_docs") or {}).values():
                out.append((rec.get("path"), rec.get("blob"), "git_blob",
                            "INPUT_MANIFEST.json"))
        else:
            for path, rec in im.items():
                if isinstance(rec, dict) and "blob" in rec:
                    out.append((path, rec["blob"], "git_blob",
                                "INPUT_MANIFEST.json"))
    seal_path = run_dir / "SEAL_AND_BUDGET.json"
    if seal_path.is_file():
        seal = _load_json(seal_path)
        for rec in (seal.get("s0_blob_ids") or {}).values():
            out.append((rec.get("path"), rec.get("blob"), "git_blob",
                        "SEAL_AND_BUDGET.json"))
        seal_im = seal.get("input_manifest")
        if isinstance(seal_im, dict):
            for path, blob in seal_im.items():
                if isinstance(blob, str) and len(blob) == 40:
                    out.append((path, blob, "git_blob", "SEAL_AND_BUDGET.json"))
    spec_path = run_dir / "PREREG_SPEC.json"
    if spec_path.is_file():
        spec = _load_json(spec_path)
        for rec in (spec.get("s0_blob_ids") or {}).values():
            out.append((rec.get("path"), rec.get("blob"), "git_blob",
                        "PREREG_SPEC.json"))
        for rec in (spec.get("s0_sources") or {}).values():
            out.append((rec.get("path"), rec.get("blob"), "git_blob",
                        "PREREG_SPEC.json"))
        for path, blob in (spec.get("input_pins") or {}).items():
            out.append((path, blob, "git_blob", "PREREG_SPEC.json"))
    ch_path = run_dir / "CHALLENGER_UNIVERSE.json"
    if ch_path.is_file():
        challenger = _load_json(ch_path)
        for row in challenger.get("admitted") or []:
            out.append((row.get("path"), row.get("blob_sha256"), "git_blob",
                        "CHALLENGER_UNIVERSE.json"))
    return out


def pin_disagreements(run_dir: Path) -> list[str]:
    """Paths pinned more than once with the same kind but different values."""
    groups: dict[tuple[str, str], set[str]] = defaultdict(set)
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for path, value, kind, _rec in iter_path_pins(run_dir):
        key = (path, kind)
        groups[key].add(value)
        counts[key] += 1
    disagreed = [
        path for (path, _kind), values in groups.items()
        if counts[(path, _kind)] > 1 and len(values) > 1
    ]
    return sorted(set(disagreed))


def multi_pinned_path_count(run_dir: Path) -> int:
    """How many repository paths are pinned more than once (same kind)."""
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for path, _value, kind, _rec in iter_path_pins(run_dir):
        counts[(path, kind)] += 1
    return sum(1 for n in counts.values() if n > 1)


def _uncovered_params():
    params = []
    for run, rec_file, key_path, kind, extra in _iter_recorded_digests():
        if (run, rec_file, key_path) in COVERED_ELSEWHERE:
            continue
        params.append(pytest.param(run, rec_file, key_path, kind, extra,
                                   id=f"{run}/{rec_file}/{key_path}"))
    return params


def _recorded_value(run: str, rec_file: str, key_path: str, extra) -> str:
    """Read the recorded hex from the committed file (or the already-parsed extra)."""
    if rec_file == "trial_ledger.jsonl":
        if key_path.endswith("config_hash"):
            return extra["config_hash"]
        return extra["config"]["membership_sha256"]
    if key_path.endswith("membership_sha256") and "graded" not in key_path:
        if isinstance(extra, dict) and "membership_sha256" in extra:
            return extra["membership_sha256"]
    if key_path.endswith("graded_membership_sha256"):
        return extra["graded_membership_sha256"]
    root = RUN_DIRS[run]
    if rec_file == "CHALLENGER_UNIVERSE.json":
        idx = int(key_path.split("[")[1].split("]")[0])
        return _load_json(root / rec_file)["admitted"][idx]["blob_sha256"]
    # walk dotted / bracketed path from the recording JSON
    obj = _load_json(root / rec_file)
    path = key_path
    # pins[path], input_pins[path], input_manifest[path], [path].blob
    if path.startswith("pins[") and path.endswith("]"):
        return obj["pins"][path[5:-1]]
    if path.startswith("input_pins[") and path.endswith("]"):
        return obj["input_pins"][path[len("input_pins["):-1]]
    if path.startswith("input_manifest[") and path.endswith("]"):
        return obj["input_manifest"][path[len("input_manifest["):-1]]
    if path.startswith("[") and path.endswith("].blob"):
        return obj[path[1:-6]]["blob"]
    cur = obj
    token = ""
    i = 0
    while i < len(path):
        ch = path[i]
        if ch == ".":
            if token:
                cur = cur[token]
                token = ""
            i += 1
            continue
        if ch == "[":
            if token:
                cur = cur[token]
                token = ""
            j = path.index("]", i)
            cur = cur[int(path[i + 1:j])]
            i = j + 1
            continue
        token += ch
        i += 1
    if token:
        cur = cur[token]
    return cur


def _recompute(run: str, rec_file: str, key_path: str, kind: str, extra) -> str:
    state = _run_state(run)
    if kind == "prereg":
        return state["prereg"]
    if kind == "membership":
        row = extra
        if state["family"] == "s1":
            return state["membership"][(row["protocol_id"], row["subject"],
                                        int(row["h"]), row["split"])]
        return state["membership"][(row["protocol_id"], int(row["horizon"]),
                                    row["split"])]
    if kind == "graded":
        row = extra
        return state["graded"][(row["protocol_id"], int(row["horizon"]),
                                row["split"])]
    if kind == "s1_retirement":
        protocol_id = extra.get("protocol_id") or extra.get("config", {}).get("protocol_id")
        return _s1_retirement_sha(state, protocol_id)
    if kind == "s2_retirement":
        protocol_id = extra.get("protocol_id") or extra.get("config", {}).get("protocol_id")
        return _s2_retirement_sha(state, protocol_id)
    if kind == "git_blob":
        tree = _git_tree_blobs(state["input_ref"])
        path = extra
        if tree is not None:
            # Exact tree check. Fallback must never run when input_ref is present.
            if path not in tree:
                raise AssertionError(
                    f"git path {path!r} missing at input_ref {state['input_ref']}"
                )
            return tree[path]
        # Depth-1 CI: input_ref is absent. Never fetch (a timed-out fetch is
        # SIGKILLed and leaves .git/shallow.lock; even a clean depth-1 fetch
        # rewrites .git/shallow for later jobs — PR #8893). Recompute from
        # working-tree bytes when the pin names those exact bytes.
        got = _working_tree_git_blob(path)
        if got is None:
            pytest.skip(
                f"{path} {SKIP_NEEDS_INPUT_REF}"
            )
        recorded = _recorded_value(run, rec_file, key_path, extra)
        if got != recorded:
            pytest.skip(
                f"{path} {SKIP_NEEDS_INPUT_REF}"
            )
        return got
    if kind == "config_hash":
        row = extra
        family = row["family"]
        if row.get("kind") == "declared_budget":
            config = {"__declared_budget__": row["n"], "reason": row.get("reason")}
        else:
            config = row["config"]
        return _trial_ledger._hash(family, config)
    raise ValueError(f"unknown digest kind {kind!r}")


@pytest.mark.parametrize("run,rec_file,key_path,kind,extra", _uncovered_params())
def test_uncovered_digest_matches_committed_bytes(run, rec_file, key_path, kind, extra):
    recorded = _recorded_value(run, rec_file, key_path, extra)
    got = _recompute(run, rec_file, key_path, kind, extra)
    assert got == recorded, (
        f"{run}/{rec_file}/{key_path}: recorded {recorded} recomputed {got}"
    )


@pytest.mark.parametrize("run", RUN_IDS)
def test_sealed_run_top_level_file_set(run):
    names = {p.name for p in RUN_DIRS[run].iterdir()}
    pinned = PINNED_TOP_LEVEL[run]
    extra = names - pinned
    missing = pinned - names
    if SUPERSEDED_POINTER in pinned:
        assert SUPERSEDED_POINTER in names, SUPERSEDED_REASON
    assert extra == set() and missing == set(), (
        f"{run} top-level set drifted extra={sorted(extra)} missing={sorted(missing)}; "
        f"v1 sole extra vs v1.1 is {SUPERSEDED_POINTER} ({SUPERSEDED_REASON})"
    )


def test_superseded_pointer_is_v1_only():
    assert SUPERSEDED_POINTER in PINNED_TOP_LEVEL["s1_residual"]
    assert SUPERSEDED_POINTER in PINNED_TOP_LEVEL["s2_event_response"]
    assert SUPERSEDED_POINTER not in PINNED_TOP_LEVEL["s1_residual_v1_1"]
    assert SUPERSEDED_POINTER not in PINNED_TOP_LEVEL["s2_event_response_v1_1"]
    for run in ("s1_residual", "s2_event_response"):
        text = (RUN_DIRS[run] / SUPERSEDED_POINTER).read_text(encoding="utf-8")
        assert "v1.1" in text
        assert SUPERSEDED_REASON  # reason is documented on this test module


def test_positive_control_one_byte_flip_is_caught(tmp_path):
    src = RUN_DIRS["s2_event_response"] / "manifests" / "P04_h5.jsonl"
    dst = tmp_path / "P04_h5.jsonl"
    text = src.read_text(encoding="utf-8")
    needle = "alibaba"
    assert needle in text
    dst.write_text(text.replace(needle, "X" + needle[1:], 1), encoding="utf-8")
    seal = _load_json(RUN_DIRS["s2_event_response"] / "SEAL_AND_BUDGET.json")
    recorded = next(
        row["membership_sha256"]
        for row in seal["membership_table"]
        if row["protocol_id"] == "P04" and int(row["horizon"]) == 5 and row["split"] == "TUNE"
    )
    got = membership_sha256_from_manifest(dst, "TUNE", "s2")
    assert got != recorded
    assert membership_sha256_from_manifest(src, "TUNE", "s2") == recorded


def test_inventory_count_is_complete():
    recs = _iter_recorded_digests()
    assert len(recs) == EXPECTED_DIGEST_COUNT
    uncovered = [
        (run, rec, key) for run, rec, key, _kind, _extra in recs
        if (run, rec, key) not in COVERED_ELSEWHERE
    ]
    assert len(COVERED_ELSEWHERE) == 30
    assert len(uncovered) == EXPECTED_DIGEST_COUNT - 30


def test_covered_elsewhere_entries_are_real():
    discovered = {(run, rec, key) for run, rec, key, _k, _e in _iter_recorded_digests()}
    for key, ref in COVERED_ELSEWHERE.items():
        assert key in discovered, key
        path, func = ref.split("::")
        text = (REPO / path).read_text(encoding="utf-8")
        assert f"def {func}(" in text, ref
    seal = _load_json(RUN_DIRS["s2_event_response"] / "SEAL_AND_BUDGET.json")
    assert len(seal["membership_table"]) == S2_MEMBERSHIP_WIDTH


def test_refuse_nonfalse_authority():
    refuse_nonfalse_authority(dict(AUTHORITY_FLAGS))
    tainted = dict(AUTHORITY_FLAGS)
    tainted["trade_authority"] = True
    with pytest.raises(ValueError, match="trade_authority"):
        refuse_nonfalse_authority(tainted)


def test_rpr_01_blob_sha_matches_git(tmp_path):
    path = tmp_path / "tiny.txt"
    path.write_bytes(b"hello sni blob\n")
    got = git_blob_sha1(path.read_bytes())
    proc = subprocess.run(
        ["git", "hash-object", "--no-filters", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert got == proc.stdout.strip()


def test_rpr_02_fallback_never_masks_a_wrong_pin(monkeypatch):
    monkeypatch.setattr(sys.modules[__name__], "_git_tree_blobs", lambda _ref: None)
    path = "config/single_name_intelligence/coverage_profiles/alibaba.yml"
    assert (REPO / path).is_file()
    # Drive the same fallback `_recompute` uses when input_ref is absent.
    # A present tracked file must yield a working-tree blob, not skip.
    got = _recompute(
        "s1_residual",
        "INPUT_MANIFEST.json",
        f"pins[{path}]",
        "git_blob",
        path,
    )
    wrong = "0" * 40
    with pytest.raises(AssertionError):
        assert got == wrong, (
            f"{path}: fallback blob {got} != wrong pin {wrong}"
        )


def test_rpr_03_cross_file_pin_agreement():
    for run in RUN_IDS:
        disagreed = pin_disagreements(RUN_DIRS[run])
        assert disagreed == [], f"{run} pin disagreements: {disagreed}"


def test_rpr_04_cross_version_pin_agreement():
    for v1, v11 in STUDY_VERSION_PAIRS:
        seal_v1 = _load_json(RUN_DIRS[v1] / "SEAL_AND_BUDGET.json")
        seal_v11 = _load_json(RUN_DIRS[v11] / "SEAL_AND_BUDGET.json")
        ref_v1 = seal_v1.get("input_ref") or seal_v1.get("base")
        ref_v11 = seal_v11.get("input_ref") or seal_v11.get("base")
        assert str(ref_v1).startswith("5ef7a7f3")
        assert str(ref_v11).startswith("5ef7a7f3")
        pins_v1: dict[tuple[str, str], set[str]] = defaultdict(set)
        pins_v11: dict[tuple[str, str], set[str]] = defaultdict(set)
        for path, value, kind, _rec in iter_path_pins(RUN_DIRS[v1]):
            pins_v1[(path, kind)].add(value)
        for path, value, kind, _rec in iter_path_pins(RUN_DIRS[v11]):
            pins_v11[(path, kind)].add(value)
        common = set(pins_v1) & set(pins_v11)
        assert common, f"{v1}/{v11}: compared 0 cross-version pairs"
        exceptions = CROSS_VERSION_PIN_EXCEPTIONS[(v1, v11)]
        mismatches = []
        for path, kind in sorted(common, key=lambda x: (x[0] or "", x[1])):
            if path in exceptions:
                continue
            if pins_v1[(path, kind)] != pins_v11[(path, kind)]:
                mismatches.append((path, kind, pins_v1[(path, kind)],
                                   pins_v11[(path, kind)]))
        assert mismatches == [], f"{v1}/{v11} pin mismatches: {mismatches}"


def test_rpr_05_cross_file_detector_positive_control(tmp_path):
    src = RUN_DIRS["s2_event_response"]
    dst = tmp_path / "s2_event_response"
    dst.mkdir()
    for name in PIN_BEARING_JSON:
        src_file = src / name
        if src_file.is_file():
            (dst / name).write_text(src_file.read_text(encoding="utf-8"),
                                    encoding="utf-8")
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for path, _value, kind, _rec in iter_path_pins(dst):
        counts[(path, kind)] += 1
    dup_path = None
    for (path, kind), n in counts.items():
        if n > 1 and kind == "git_blob":
            dup_path = path
            break
    assert dup_path is not None
    target = dst / "INPUT_MANIFEST.json"
    obj = _load_json(target)
    blob = obj[dup_path]["blob"]
    flipped = ("0" if blob[0] != "0" else "1") + blob[1:]
    obj[dup_path]["blob"] = flipped
    target.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    found = pin_disagreements(dst)
    assert found == [dup_path]
