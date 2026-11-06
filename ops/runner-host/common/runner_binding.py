#!/usr/bin/env python3
"""Fail-closed binding between a runner root path and its admission profile.

The M1 guard wrapper (``ops/runner-host/m1/run_guarded_runner.sh``) used to
derive the admission profile from the directory basename of the runner root,
so a launchd plist pointing at ``/Users/chriswong/actions-runner-2`` (whose
``.runner`` carries ``agentName="m1-nightly-2"``) silently fell through to
the canary default because the basename is ``actions-runner-2``.  The wrapper
now trusts the *configured* runner identity written into ``.runner`` by the
official ``config.sh`` registration, and refuses any binding that does not
match one of the production (canonical root, configured agentName) pairs.

The helper is split out so tests can drive the actual decision logic without
materialising a real ``/Users`` path or running ``plutil`` on CI; the wrapper
injects the production extractor (``/usr/bin/plutil -extract agentName ...``)
and tests inject a JSON reader or any other callable that returns the agentName.

Pre-image: AD-1T2 binding fix per the 2026-10-03 root integration ruling.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

#: Name of the GitHub Actions runner's identity file inside a runner root.
RUNNER_IDENTITY_FILE = ".runner"

#: Path to macOS's native plist extractor. The wrapper invokes this verbatim;
#: tests do not depend on its availability.
PLUTIL_BIN = "/usr/bin/plutil"


#: Production-shaped (canonical root, configured agentName) -> profile.  A
#: wrapper invocation whose (runner_root, agentName) does not match an entry
#: here is refused before the listener starts.  Adding a new canonical
#: binding is a deliberate operator act that MUST be reviewed alongside the
#: launchd plist and ``runner_admission.py`` allowlist.
#:
#: The M1 service canary owns three listeners; only m1-nightly-2 receives
#: the producer-lane profile.  m1-nightly-1 and m1-light-1 retain the
#: existing m1-canary profile so the listener launch contract is preserved.
CANONICAL_BINDINGS: dict[tuple[str, str], str] = {
    ("/Users/chriswong/actions-runner-2", "m1-nightly-2"): "m1-nightly-2",
    ("/Users/chriswong/actions-runner-1", "m1-nightly-1"): "m1-canary",
    ("/Users/chriswong/actions-runner-3", "m1-light-1"): "m1-canary",
}


class RunnerBindingRefused(Exception):
    """Raised when the runner root cannot be bound to a known profile.

    The wrapper maps this to exit code 78 (EX_CONFIG) before
    ``Runner.Listener`` starts, so launchd can retry after a real
    misconfiguration is fixed rather than launching a listener that has
    silently lost its admission surface.
    """


def resolve_profile(
    runner_root: str,
    *,
    isfile,
    isdir,
    extract_agent_name,
) -> tuple[str, str]:
    """Resolve the admission profile for a runner root.

    Args:
        runner_root: absolute path to the runner root (the directory that
            contains ``.runner``).  The wrapper passes the path LaunchAgent
            invokes it with; tests may pass a temp path.
        isfile: callable returning ``True`` for an existing file.  The
            wrapper injects ``os.path.isfile``; tests inject a fake.
        isdir: callable returning ``True`` for an existing directory.  The
            wrapper injects ``os.path.isdir``; tests inject a fake.
        extract_agent_name: callable reading a ``.runner`` file path and
            returning the configured ``agentName`` string.  The wrapper
            injects ``plutil``; tests inject a JSON/plist reader.

    Returns:
        Tuple of ``(profile_name, agent_name)``.

    Raises:
        RunnerBindingRefused: when the binding cannot be trusted.  Any of:

            * ``runner_root`` is missing / not absolute / not a directory
            * ``.runner`` is missing at the runner root
            * the extractor raised (malformed/unreadable ``.runner``)
            * the extractor returned something other than a non-empty
              ``agentName`` string
            * the (runner_root, agentName) pair is not in
              :data:`CANONICAL_BINDINGS` (covers "other root claiming
              m1-nightly-2", wrong root for a known agentName, and an
              unrecognised agentName on a recognised root)
    """
    if not isinstance(runner_root, str) or not runner_root:
        raise RunnerBindingRefused("runner_root is required")
    if not os.path.isabs(runner_root):
        raise RunnerBindingRefused(
            f"runner_root must be an absolute path: {runner_root!r}"
        )
    if not isdir(runner_root):
        raise RunnerBindingRefused(
            f"runner_root does not exist or is not a directory: {runner_root!r}"
        )
    runner_file = os.path.join(runner_root, RUNNER_IDENTITY_FILE)
    if not isfile(runner_file):
        raise RunnerBindingRefused(
            f"missing {RUNNER_IDENTITY_FILE} file at {runner_file}"
        )
    try:
        raw = extract_agent_name(runner_file)
    except Exception as exc:  # noqa: BLE001 — wrapper must refuse on ANY error
        raise RunnerBindingRefused(
            f"unreadable {RUNNER_IDENTITY_FILE} at {runner_file}: {exc}"
        ) from exc
    if not isinstance(raw, str):
        raise RunnerBindingRefused(
            f"{RUNNER_IDENTITY_FILE} at {runner_file} did not return a string"
        )
    agent_name = raw.strip()
    if not agent_name:
        raise RunnerBindingRefused(
            f"missing agentName in {RUNNER_IDENTITY_FILE} at {runner_file}"
        )
    profile = CANONICAL_BINDINGS.get((runner_root, agent_name))
    if profile is None:
        raise RunnerBindingRefused(
            "no canonical binding for "
            f"(root={runner_root!r}, agentName={agent_name!r}); "
            "refusing to launch a listener with an unverified identity"
        )
    return profile, agent_name


def _plutil_agent_name(runner_file: str) -> str:
    """Production extractor: ``/usr/bin/plutil -extract agentName ...``.

    Kept as a free function so tests can substitute a JSON reader without
    touching plutil's interface.  Raises ``subprocess.CalledProcessError``
    on malformed plist, ``FileNotFoundError`` when plutil is missing — the
    helper wraps every failure as ``RunnerBindingRefused``.
    """
    result = subprocess.run(
        [
            PLUTIL_BIN,
            "-extract",
            "agentName",
            "raw",
            "-o",
            "-",
            runner_file,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def main() -> int:
    # Sub-command: --extract-profile <binding-json-line> <key>
    # Lets the wrapper pull a single field out of a previously-emitted
    # RUNNER_BINDING=... line without depending on jq.  Kept inside this
    # module so the schema stays in one place.
    if len(sys.argv) >= 2 and sys.argv[1] == "--extract-profile":
        if len(sys.argv) != 4:
            print(
                "usage: runner_binding.py --extract-profile <binding-json-line> <key>",
                file=sys.stderr,
            )
            return 64
        binding_line = sys.argv[2]
        key = sys.argv[3]
        try:
            payload = json.loads(binding_line)
            value = payload[key]
        except Exception as exc:  # noqa: BLE001
            print(
                f"::error title=runner-binding::could not extract "
                f"{key!r} from {binding_line!r}: {exc}",
                flush=True,
            )
            return 78
        print(value, end="")
        return 0

    if len(sys.argv) != 2:
        print("usage: runner_binding.py <runner_root>", file=sys.stderr)
        return 64
    runner_root = sys.argv[1]
    try:
        profile, agent_name = resolve_profile(
            runner_root,
            isfile=os.path.isfile,
            isdir=os.path.isdir,
            extract_agent_name=_plutil_agent_name,
        )
    except RunnerBindingRefused as exc:
        print(
            "::error title=runner-binding::" + str(exc),
            flush=True,
        )
        return 78
    print(
        "RUNNER_BINDING="
        + json.dumps(
            {
                "schema": "runner.binding.v1",
                "runner_root": runner_root,
                "agent_name": agent_name,
                "profile": profile,
            },
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())