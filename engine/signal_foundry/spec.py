"""engine.signal_foundry.spec — declarative spec schema, validation, and hashing.

The spec is the LLM's ONLY output surface: it names data paths, transform
pipelines, targets, and pre-registered gates.  The machine picks inputs; it
can never touch the battery ruler (SF-R2).

Key rules enforced here:
  SF-R4  — gates are pre-registered and immutable once filed (gate-freeze hash).
  SF-R7  — data paths must be git-tracked (gitignored stores refused).
  SF-R8  — construction_hash stable over canonical JSON.
  SF-R9  — target.kind in closed vocabulary.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Whitelisted transform vocabulary (must mirror transforms.TRANSFORMS registry)
# ---------------------------------------------------------------------------
ALLOWED_TRANSFORMS = frozenset({
    "zscore", "pctile_rank", "diff", "pct_change", "sma", "ema",
    "lag", "sign", "clip", "rolling_vol", "rolling_corr",
    "ratio", "spread", "drawdown",
})

ALLOWED_TARGET_KINDS = frozenset({
    "excess_return", "absolute_return", "drawdown_onset", "forward_vol",
})

ALLOWED_HORIZONS = frozenset({5, 10, 21, 63, 126})

ALLOWED_BASELINES = frozenset({
    "buy_and_hold", "sma_200", "flat",
})

# Regex: id must match SF-\d{4}
_ID_RE = re.compile(r"^SF-\d{4}$")

# Required top-level keys in a spec
_REQUIRED_KEYS = {
    "id", "name", "market", "thesis", "data", "feature",
    "target", "gates", "registered_at",
}

# Required gate sub-keys
_REQUIRED_GATES = {"min_t_hac", "fdr_q", "dsr"}

# Required target sub-keys
_REQUIRED_TARGET = {"path", "kind", "horizon_d"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _canonical_json(obj: Any) -> str:
    """Stable, sort-keyed, compact JSON for hashing."""
    return json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))


def _git_tracked(path_str: str, repo_root: Path) -> bool:
    """Return True iff path is tracked by git (not gitignored, not absent).

    Uses 'git ls-files --error-unmatch' which exits non-zero for any
    untracked or gitignored file.  We resolve relative to repo_root.
    """
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", path_str],
            cwd=str(repo_root),
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

EXCESS_TARGET_VERSION = "sf-excess-target-2"


class TargetContractError(ValueError):
    """The declared target cannot unambiguously identify the intended labels."""


def excess_return_contract(spec: dict, repo_root: Path | None = None) -> dict:
    """Describe one explicit asset-minus-price-benchmark target; no implicit baseline.

    A construction declaration is not a point-in-time, rights or trading approval.
    Price-benchmark returns are buy-and-hold simple returns, not strategy returns.
    """
    target = spec.get("target")
    if not isinstance(target, dict) or target.get("kind") != "excess_return":
        raise TargetContractError("expected an excess_return target")
    unknown = set(target) - {"path", "column", "kind", "horizon_d", "benchmark"}
    if unknown:
        raise TargetContractError("unsupported excess_return target fields: " + str(sorted(unknown)))
    horizon = target.get("horizon_d")
    if type(horizon) is not int or horizon not in ALLOWED_HORIZONS:
        raise TargetContractError("excess_return horizon_d must be an allowed integer target-bar horizon")
    benchmark = target.get("benchmark")
    if not isinstance(benchmark, dict) or set(benchmark) != {"path", "column"}:
        raise TargetContractError("excess_return requires explicit target.benchmark {path, column}; no baseline inference")

    def price_ref(entry: dict, label: str) -> dict:
        from pathlib import PurePosixPath
        raw, column = entry.get("path"), entry.get("column")
        if not isinstance(raw, str) or not raw or raw != raw.strip() or any(c in raw for c in '\\*?[]\n\r\0'):
            raise TargetContractError(label + " path must be a literal repository-relative file")
        path = PurePosixPath(raw)
        if path.is_absolute() or '..' in path.parts or str(path) != raw or raw.startswith(('-', ':')):
            raise TargetContractError(label + " path must be canonical and repository-relative")
        if path.suffix.lower() not in {'.parquet', '.csv', '.tsv'}:
            raise TargetContractError(label + " path has no supported price-file format")
        if not isinstance(column, str) or not column.strip() or column != column.strip():
            raise TargetContractError(label + " requires an explicit nonempty column")
        if repo_root is not None:
            root = Path(repo_root).resolve()
            resolved = (root / raw).resolve()
            if not resolved.is_relative_to(root):
                raise TargetContractError(label + " resolves outside repository")
            if resolved.is_dir() or not _git_tracked(raw, root):
                raise TargetContractError(label + " must be a git-tracked file (SF-R7)")
        return {"path": raw, "column": column}

    asset = price_ref(target, "asset")
    comparison = price_ref(benchmark, "benchmark")
    same = asset['path'] == comparison['path']
    if repo_root is not None:
        root = Path(repo_root).resolve()
        same = (root / asset['path']).resolve() == (root / comparison['path']).resolve()
    if same and asset['column'] == comparison['column']:
        raise TargetContractError("asset and benchmark must not name the identical price series")
    return {"version": EXCESS_TARGET_VERSION, "status": "declared", "kind": "excess_return",
            "metric": "asset_simple_return_minus_benchmark_simple_return",
            "clock": "target_price_bars", "horizon_bars": horizon,
            "asset": asset, "benchmark": comparison, "benchmark_policy": "buy_and_hold",
            "units": "simple_return_difference", "trading_authority": False}


def load_spec(path: str | Path) -> dict:
    """Load a JSON spec file from disk.  Raises FileNotFoundError / json.JSONDecodeError
    on missing/malformed file.  Does NOT validate — call validate_spec() separately."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def validate_spec(spec: dict, repo_root: str | Path = ".") -> tuple[bool, list[str]]:
    """Validate a spec dict against the SF schema.

    Returns (ok: bool, errors: list[str]).  ok=True means the spec is
    admissible for filing; ok=False means errors is non-empty.

    Checks (in order):
      1. Required top-level keys present.
      2. id matches ^SF-\\d{4}$.
      3. feature.pipeline uses only whitelisted transforms with valid params.
      4. Every data[].path is git-tracked (gitignored/absent → error).
      5. target.kind in allowed set.
      6. target.horizon_d in allowed set.
      7. gates dict has required keys with numeric values.
      8. registered_at is a valid ISO date string.
      9. Gate-freeze: if gates_hash present, it must match recomputed hash.
    """
    repo_root = Path(repo_root)
    errors: list[str] = []

    # 1. Required keys
    missing = _REQUIRED_KEYS - set(spec.keys())
    if missing:
        errors.append(f"missing required keys: {sorted(missing)}")

    # 2. id format
    sid = spec.get("id", "")
    if not _ID_RE.match(str(sid)):
        errors.append(f"id '{sid}' does not match ^SF-\\d{{4}}$")

    # 3. feature.pipeline transform whitelist
    feature = spec.get("feature", {})
    pipeline = feature.get("pipeline", [])
    if not isinstance(pipeline, list):
        errors.append("feature.pipeline must be a list")
    else:
        for i, step in enumerate(pipeline):
            if not isinstance(step, (list, tuple)) or len(step) < 1:
                errors.append(f"pipeline[{i}] must be a list [name, {{params}}]")
                continue
            name = step[0]
            if name not in ALLOWED_TRANSFORMS:
                errors.append(
                    f"pipeline[{i}] transform '{name}' is not in the whitelisted "
                    f"vocabulary: {sorted(ALLOWED_TRANSFORMS)}"
                )
            # Validate params if present
            params = step[1] if len(step) > 1 else {}
            if not isinstance(params, dict):
                errors.append(f"pipeline[{i}] params must be a dict, got {type(params)}")
                continue
            # lag(n) must be >= 0
            if name == "lag" and "n" in params:
                n = params["n"]
                if not isinstance(n, int) or n < 0:
                    errors.append(f"pipeline[{i}] lag(n={n!r}) must be int >= 0")
            # window/span must be positive int
            for win_key in ("window", "span"):
                if win_key in params:
                    v = params[win_key]
                    if not isinstance(v, int) or v <= 0:
                        errors.append(
                            f"pipeline[{i}] {name}({win_key}={v!r}) must be a positive int"
                        )

    # 4. data[].path git-tracked
    data_entries = spec.get("data", [])
    if not isinstance(data_entries, list) or len(data_entries) == 0:
        errors.append("data must be a non-empty list of {path, column, pit} dicts")
    else:
        for j, entry in enumerate(data_entries):
            if not isinstance(entry, dict):
                errors.append(f"data[{j}] must be a dict")
                continue
            p = entry.get("path", "")
            if not p:
                errors.append(f"data[{j}].path is empty")
                continue
            if not _git_tracked(str(p), repo_root):
                errors.append(
                    f"data[{j}].path '{p}' is not a git-tracked file "
                    "(gitignored or runner-local stores are refused — SF-R7)"
                )
            if "column" not in entry:
                errors.append(f"data[{j}] missing 'column' key")
            if "pit" not in entry:
                errors.append(f"data[{j}] missing 'pit' key")

    # 5. target.kind
    target = spec.get("target", {})
    if not isinstance(target, dict):
        errors.append("target must be a dict")
    else:
        missing_t = _REQUIRED_TARGET - set(target.keys())
        if missing_t:
            errors.append(f"target missing required keys: {sorted(missing_t)}")
        kind = target.get("kind")
        if kind not in ALLOWED_TARGET_KINDS:
            errors.append(
                f"target.kind '{kind}' not in allowed set: {sorted(ALLOWED_TARGET_KINDS)}"
            )
        # 6. horizon_d
        h = target.get("horizon_d")
        if h not in ALLOWED_HORIZONS:
            errors.append(
                f"target.horizon_d {h!r} not in allowed set: {sorted(ALLOWED_HORIZONS)}"
            )
        # target data path also must be tracked
        tp = target.get("path", "")
        if tp and not _git_tracked(str(tp), repo_root):
            errors.append(
                f"target.path '{tp}' is not a git-tracked file (SF-R7)"
            )

    # 7. gates
    gates = spec.get("gates", {})
    if not isinstance(gates, dict):
        errors.append("gates must be a dict")
    else:
        missing_g = _REQUIRED_GATES - set(gates.keys())
        if missing_g:
            errors.append(f"gates missing required keys: {sorted(missing_g)}")
        for gk in _REQUIRED_GATES:
            if gk in gates and not isinstance(gates[gk], (int, float)):
                errors.append(f"gates.{gk} must be numeric, got {type(gates[gk])}")

    # 8. registered_at
    ra = spec.get("registered_at", "")
    if ra:
        try:
            from datetime import date
            date.fromisoformat(str(ra))
        except (ValueError, TypeError):
            errors.append(f"registered_at '{ra}' is not a valid ISO date string")
    else:
        errors.append("registered_at is required")

    # 9. Gate-freeze check
    stored_gates_hash = spec.get("gates_hash")
    if stored_gates_hash is not None:
        computed = _compute_gates_hash(gates)
        if computed != stored_gates_hash:
            errors.append(
                f"gates have changed after registration "
                f"(stored hash {stored_gates_hash!r} != computed {computed!r}). "
                "Harness refuses runs on modified gates (SF-R4)."
            )

    if isinstance(target, dict) and target.get("kind") == "excess_return":
        try:
            excess_return_contract(spec, repo_root)
        except (TargetContractError, OSError) as exc:
            errors.append(str(exc))

    ok = len(errors) == 0
    return ok, errors


def _compute_gates_hash(gates: dict) -> str:
    """SHA1 over canonical JSON of the gates dict."""
    canon = _canonical_json(gates)
    return hashlib.sha1(canon.encode("utf-8")).hexdigest()[:16]


def construction_hash(spec: dict) -> str:
    """Stable dedup hash over {market, feature.pipeline, target(path,kind,horizon_d), universe}.

    Used for SF-R8 dedup against prior specs and REGISTRY/CANDIDATES.
    Changing any of these four dimensions produces a different hash; renaming
    a signal ('name' field) does not.
    """
    target = spec.get("target", {})
    canonical = {
        "market": spec.get("market", ""),
        "pipeline": spec.get("feature", {}).get("pipeline", []),
        "target_path": target.get("path", ""),
        "target_kind": target.get("kind", ""),
        "target_horizon_d": target.get("horizon_d"),
        "universe": spec.get("universe", ""),
    }
    canon = _canonical_json(canonical)
    return hashlib.sha1(canon.encode("utf-8")).hexdigest()[:20]


def stamp_gates_hash(spec: dict) -> dict:
    """Return a copy of the spec with gates_hash stamped (for first registration).

    Call this once at registration time.  The harness then checks it on every run.
    """
    s = dict(spec)
    s["gates_hash"] = _compute_gates_hash(spec.get("gates", {}))
    return s
