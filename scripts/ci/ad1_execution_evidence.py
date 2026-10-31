"""AD-1T2 execution evidence — bind run -> host -> store -> receipt -> digest.

Why this exists rather than a host fingerprint in ``receipt_id``: the producer
deliberately keeps absolute paths OUT of that hash (see the ``m5`` comment in
``scripts/build_options_intel_brief.build``) so a host/path migration with
identical logical inputs does not churn the semantic receipt. The machine that
produced an artifact is therefore recorded as execution evidence against the
existing receipt and output digest, through the existing step-summary/run-log
facility. No new ledger and no new store.

The one rule this file must not break: it has to distinguish "this run produced
this artifact" from "this file was already sitting on disk". Printing a complete,
plausible receipt for the frozen artifact after a failed producer would be the
same green-looking-proof-of-a-stale-artifact shape the AD-1T2 lane exists to
eliminate, reproduced in miniature.

The same honesty applies to the revision. ``GITHUB_SHA`` is the revision that
*triggered* the run, not necessarily the code this script executed: workflows
check out a default branch or pull after the trigger, so the checked-out HEAD
can move on from ``GITHUB_SHA``. ``code_revision`` therefore records the actual
Git HEAD of the repository that contains *this script*, resolved locally from
the script's own path (never the caller's cwd), while ``trigger_revision``
retains the raw trigger value. When HEAD cannot be resolved, ``code_revision``
is null with a status reason — it never falls back to the trigger SHA, which
would describe code the run did not execute.

Reads ``PRODUCER_OUTCOME`` (the producer step's ``outcome``) and ``SKIP_REASON``
from the environment. Always exits 0: evidence must never cost the night.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess

BRIEF = pathlib.Path("site/options_intel_brief.json")

_GIT_TIMEOUT_S = 10


def _first_line(text: str | None, limit: int = 160) -> str:
    lines = (text or "").strip().splitlines()
    return (lines[0].strip() if lines else "")[:limit]


def _git_env() -> dict[str, str]:
    # Bind discovery to this script's own repository: an inherited GIT_DIR /
    # GIT_WORK_TREE / GIT_CEILING_DIRECTORIES could resolve HEAD in whatever
    # repository the *caller* pointed at instead of the code being executed.
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["LC_ALL"] = "C"
    return env


def resolve_source_head() -> tuple[str | None, str]:
    """Return the actual HEAD of the repository containing this script.

    The root comes from this file's own location, never the caller's cwd, so an
    unrelated working directory still binds the executed code. Any failure
    yields ``(None, "unavailable: <reason>")`` — fail-soft, and never a
    substitution of the trigger SHA.
    """
    script_dir = pathlib.Path(__file__).resolve().parent
    try:
        proc = subprocess.run(
            ["git", "-C", str(script_dir), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_S,
            env=_git_env(),
            check=False,
        )
    except FileNotFoundError:
        return None, "unavailable: git executable not found"
    except subprocess.TimeoutExpired:
        return None, f"unavailable: git timed out after {_GIT_TIMEOUT_S}s"
    except OSError as exc:  # pragma: no cover — exotic exec failures only
        return None, f"unavailable: {type(exc).__name__}"

    if proc.returncode != 0:
        detail = _first_line(proc.stderr) or f"exit {proc.returncode}"
        return None, f"unavailable: git rev-parse failed: {detail}"

    # 40 hex = SHA-1 object id; SHA-256 repositories emit 64.
    sha = (proc.stdout or "").strip().lower()
    if len(sha) in (40, 64) and all(c in "0123456789abcdef" for c in sha):
        return sha, "resolved"
    return None, "unavailable: git returned no plausible object id"


def main() -> int:
    outcome = os.environ.get("PRODUCER_OUTCOME") or "not-run"
    skip = os.environ.get("SKIP_REASON") or ""
    produced_by_this_run = outcome == "success" and not skip

    code_revision, code_revision_status = resolve_source_head()
    trigger_revision = os.environ.get("GITHUB_SHA")

    rec: dict[str, object] = {
        "produced_by_this_run": produced_by_this_run,
        "producer_outcome": outcome,
        "skip_reason": skip or None,
        "code_revision": code_revision,
        "code_revision_status": code_revision_status,
        "trigger_revision": trigger_revision,
        "workflow_run": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "runner_name": os.environ.get("RUNNER_NAME"),
    }

    if BRIEF.exists():
        raw = BRIEF.read_bytes()
        rec["output_sha256"] = hashlib.sha256(raw).hexdigest()
        try:
            d = json.loads(raw)
        except Exception as exc:  # noqa: BLE001 — evidence must not crash the night
            rec["artifact"] = f"UNREADABLE: {exc}"
            d = {}
        if d:
            elig = d.get("eligibility") if isinstance(d.get("eligibility"), dict) else {}
            rec.update({
                "as_of_session": d.get("as_of_session"),
                "oi_counted_date": d.get("oi_counted_date"),
                "board_state": d.get("board_state"),
                "receipt_id": d.get("receipt_id"),
                "eligible": elig.get("eligible"),
                "source_coverage_pct": elig.get("source_coverage_pct"),
                "store_resolution": (d.get("_run") or {}).get("store_resolution"),
            })
    else:
        rec["artifact"] = "ABSENT"

    if not produced_by_this_run:
        # Say it at line start, where GitHub parses it — the fields below describe
        # whatever was already committed, NOT a publish by this run.
        print("::warning title=ad1-evidence::this run did not produce the artifact "
              f"(producer_outcome={outcome}, skip_reason={skip or 'none'}); the "
              "record below describes the PRE-EXISTING committed brief.")
    elif rec.get("eligible") == 0:
        # A healthy source with genuinely no qualifying opportunity is a valid
        # NO_SIGNAL, not a failure — but an empty board published over a
        # previously-populated one is worth an operator's eyes either way.
        print("::warning title=ad1-evidence::published board has eligible=0 "
              f"(board_state={rec.get('board_state')}, "
              f"coverage={rec.get('source_coverage_pct')}).")

    if code_revision is None:
        # Same line-start convention: provenance could not be bound to the code
        # that executed. Report it and keep the trigger separate — never cost
        # the run, and never paper over the gap with the trigger SHA.
        print("::warning title=ad1-evidence::could not resolve source code revision "
              f"({code_revision_status}); code_revision=null, "
              f"trigger_revision={trigger_revision or 'none'}.")

    print("### AD-1 execution evidence\n")
    print("```json")
    print(json.dumps(rec, indent=2, sort_keys=True))
    print("```")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
