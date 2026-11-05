"""Opt-in transaction checks inside the incumbent manual International render.

This is not a collector, engine replacement, publisher or rights grant. Build
uses the normal International builder and full feed composer. Finalize runs
after the normal asset transforms; verify fences the existing commit/push path.
The receipt lives in RUNNER_TEMP and is never a second durable registry.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess

from lib.intl_durable_publication import (
    DurablePublicationError, build_manifest, capture_inputs,
    validate_at_ref, validate_manifest, validate_unchanged, _check_output_path,
)

SCHEMA = "intl.durable_render.v1"
RISK = "data/intl_risk/latest.json"
CURRENT = "data/intl/publication/generations/intl_generation_current.json"
GEN_DIR = "data/intl/publication/generations/"
SOURCE_ROOTS = ("engine/", "lib/", "scripts/", "collectors/", "config/", "contracts/", "templates/")
SOURCE_FILES = {"config.yml", "pyproject.toml", "setup.cfg", "uv.lock", "poetry.lock",
                ".github/workflows/render.yml", "docs/INTERNATIONAL_MACRO_DATA_CONTRACT.md"}


def _need(condition, message):
    if not condition:
        raise DurablePublicationError(message)


def _git(root, *args):
    env = dict(os.environ, GIT_NO_LAZY_FETCH="1")
    return subprocess.check_output(["git", "-C", str(root), *args], env=env)


def _tree(root, ref):
    _need(type(ref) is str and re.fullmatch(r"[0-9a-f]{40}", ref), "exact source SHA required")
    records = {}
    for raw in _git(root, "ls-tree", "-rz", "--full-tree", ref).split(b"\0"):
        if raw:
            meta, path = raw.split(b"\t", 1)
            mode, kind, blob = meta.decode().split()
            records[path.decode("utf-8")] = (mode, kind, blob)
    return records


def _source_entries(root, ref):
    # The canonical optimizer may re-stamp the two plain-copy HTML templates.
    # They are managed output, while Jinja/code/CSS/JS remain source inputs.
    return {p: list(v) for p, v in _tree(root, ref).items()
            if (p.startswith(SOURCE_ROOTS) and not
                (p.startswith("templates/") and p.endswith(".html")))
            or p in SOURCE_FILES or ("/" not in p and p.startswith("requirements"))}


def _check_source(root, receipt, ref):
    _need(_source_entries(root, ref) == receipt["source_entries"],
          "source/dependency changed; recompute from the qualified source")
    paths = list(receipt["source_entries"])
    # No cat-file/hydration: compare the actual checkout/index against its
    # source tree through ordinary Git, before and after computation.
    for offset in range(0, len(paths), 200):
        chunk = paths[offset:offset + 200]
        _need(not _git(root, "diff", "--name-only", receipt["source_sha"], "--", *chunk),
              "dirty source input")
    added = _git(root, "ls-files", "--others", "--exclude-standard", "-z", "--",
                 "engine/", "lib/", "scripts/", "collectors/", "config/", "contracts/", "templates/")
    _need(not added, "untracked source dependency")


def _extra_inputs(root):
    # Native materialization owners already validate their receipt/body/series
    # contracts. Bind those exact retained files as inputs as well. No new data
    # directory or provider capability is created here.
    tree = _tree(root, _git(root, "rev-parse", "HEAD").decode().strip())
    paths = {p for p in tree if p.startswith(("data/intl_macro/", "data/imf_weo/"))}
    paths.update(("data/forex/latest.json", "data/rates_command/latest.json",
                  "data/intl_search/closes.parquet", "data/intl_search/members.parquet",
                  "data/intl_search/coverage.parquet", "data/regime/latest.json",
                  "data/froth_fragility/log.jsonl", "data/dislocation/state_log.parquet",
                  "data/group_flow/validation_meta.json", "data/breadth/sector_breadth.parquet",
                  "data/neuralweb/world_state.json", "data/neuralweb/mastermind_context.json",
                  "site/marketdata/subsector_rotation.json", "site/feeds/event_calendar.json",
                  "site/macrodata/global_regime_fragment.json"))
    # Present global-regime evidence is used by the incumbent page composer.
    paths.update(p for p in tree if p.startswith("site/") and "global_regime" in p)
    return sorted(paths)


@contextmanager
def _observe_store(root, records):
    """Observe incumbent store AND direct native IO without replacing parsers.

    Every actual read, including a missing optional series, is bound to the
    checkout version. A swallowed engine exception cannot swallow a failed
    consistency check: the sticky failure is raised when leaving this scope.
    """
    from lib import config, store
    from lib.intl_macro_publication import observe_native_reads
    original = store.read
    failures = []

    def before_read(path):
        _need(not failures, "input observation already failed; no further read")
        try:
            relative = Path(path).absolute().relative_to(root).as_posix()
            if relative.startswith(GEN_DIR):
                # The generation owner shares this IO leaf for its own output
                # readback. These exact managed filenames are NOT old source
                # inputs: _closure/produced_data bind the current invocation's
                # bytes, and preimages fence newer upstream selectors. Never
                # exempt other data or arbitrary files in the directory.
                _check_output_path(relative)
                return
            if relative in records:
                validate_unchanged(root, [records[relative]])
            else:
                # Observe absence too, BEFORE a reader's lstat/exists shortcut.
                # Selected receipt/source/artifact paths need not be Git-present
                # to be observed; validate_at_ref later refuses uncommitted input.
                records[relative] = capture_inputs(root, [relative])[0]
        except Exception:
            failures.append(str(path))
            raise

    def observed(group, name):
        try:
            path = store._path(group, name)
            relative = path.absolute().relative_to(root).as_posix()
            before_read(path)
            result = original(group, name)
            validate_unchanged(root, [records[relative]])
            return result
        except Exception:
            failures.append((group, name))
            raise

    _need(Path(config.data_dir()).resolve() == root / "data", "noncanonical data root")
    store.read = observed
    try:
        with observe_native_reads(before_read):
            yield
    finally:
        store.read = original
    _need(not failures, "store input read/consistency failed; no durable publication")
    validate_unchanged(root, list(records.values()))


def _closure(root, descriptor):
    from lib.intl_generation_publication import read_generation_publication
    publication = read_generation_publication(data_root=root / "data")
    _need(publication["status"] in ("ready", "unavailable"), "generation is not verifiable")
    _need(publication["descriptor"] == descriptor, "different/old generation selector")
    current = (root / CURRENT).read_bytes()
    paths = [CURRENT, GEN_DIR + "intl_generation_descriptor_" + sha256(current).hexdigest() + ".json"]
    if publication["status"] == "ready":
        paths.append(GEN_DIR + descriptor["artifact_name"])
        contract = json.loads(publication["artifact_bytes"])
        if contract.get("policy_points_ref") is not None:
            paths.append(GEN_DIR + contract["policy_points_ref"]["artifact_name"])
    return paths


def build(root, expected_source, receipt_path):
    _need(os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
          and os.environ.get("INTL_DURABLE_MODE") == "true"
          and os.environ.get("INTL_RENDER_SCOPE") == "intl", "manual intl opt-in required")
    _need(os.environ.get("COLLECT_LANE", "") in ("", "render")
          and os.environ.get("US_LANE", "") in ("", "render")
          and os.environ.get("RENDER_NO_DRIP") == "1", "render-only environment required")
    head = _git(root, "rev-parse", "HEAD").decode().strip()
    _need(head == expected_source, "render source changed before build")
    receipt = {"schema": SCHEMA, "source_sha": head,
               "source_entries": _source_entries(root, head)}
    _check_source(root, receipt, head)
    _need(not _git(root, "diff", "--name-only", "HEAD", "--", "site/", "templates/"),
          "preexisting managed output changes")
    receipt["preimages"] = capture_inputs(root, [RISK, CURRENT])
    inputs = {r["path"]: r for r in capture_inputs(root, _extra_inputs(root))}
    from lib import config
    _need((root / config.load()["storage"]["site_dir"]).resolve() == root / "site",
          "noncanonical site root")
    from scripts import build_intl, build_feeds
    from lib.intl_risk_publication import RiskPublication
    result = {}
    with _observe_store(root, inputs):
        rc = build_intl.main(publication_result=result)
    publication = result.get("risk_publication")
    _need(rc == 0 and isinstance(publication, RiskPublication)
          and publication.path.resolve() == root / RISK,
          "this invocation did not successfully publish Risk")
    _need(sha256((root / RISK).read_bytes()).hexdigest() == publication.artifact_sha256,
          "Risk payload differs from this invocation's readback")
    _need(type(result.get("descriptor")) is dict, "this invocation did not publish a generation")
    for path, digest in result.get("pages", {}).items():
        _need(sha256((root / path).read_bytes()).hexdigest() == digest,
              "published page differs from the normal builder's write")
    _need(set(result.get("pages", {})) == {"site/intl.html", "site/intl_stocks.html"},
          "both normal International pages are required")
    paths = _closure(root, result["descriptor"])
    # Full incumbent feed composition; never substitute a one-family manifest.
    with _observe_store(root, inputs):
        _need(type(build_feeds.build(render_only=True)) is dict, "full feed composition failed")
    _need(paths == _closure(root, result["descriptor"]), "feed composition changed generation")
    for path in paths:
        _need((root / "site/feeds" / Path(path).name).read_bytes() == (root / path).read_bytes(),
              "native generation feed differs from its producer")
    receipt.update(inputs=sorted(inputs.values(), key=lambda r: r["path"]),
                   produced_data=capture_inputs(root, [RISK, *paths]),
                   descriptor=result["descriptor"], risk_sha256=publication.artifact_sha256)
    validate_unchanged(root, receipt["inputs"])
    validate_at_ref(root, head, receipt["inputs"])
    _check_source(root, receipt, head)
    receipt_path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")


def _load(path):
    # RUNNER_TEMP is the existing job's exclusive receipt custody. Source-only
    # metadata is bounded and never printed with secrets or provider bodies.
    _need(path.stat().st_size <= 16 * 1024 * 1024, "receipt too large")
    value = json.loads(path.read_text(encoding="utf-8"))
    _need(type(value) is dict and value.get("schema") == SCHEMA, "wrong render receipt")
    return value


def _validate_producer(root, receipt):
    validate_unchanged(root, receipt["produced_data"])
    validate_unchanged(root, receipt["inputs"])
    _need(sha256((root / RISK).read_bytes()).hexdigest() == receipt["risk_sha256"], "Risk changed")
    _closure(root, receipt["descriptor"])
    _check_source(root, receipt, receipt["source_sha"])


def finalize(root, receipt_path):
    receipt = _load(receipt_path)
    _validate_producer(root, receipt)
    changes = _git(root, "diff", "--name-only", "-z", receipt["source_sha"], "--", "site/", "templates/")
    untracked = _git(root, "ls-files", "--others", "--exclude-standard", "-z", "--", "site/", "templates/")
    library = _git(root, "ls-files", "--others", "--ignored", "--exclude-standard", "-z", "--",
                   "site/intlstockdata/", "site/intlohlc/", "site/factordata/intl_setups.json")
    paths = {p.decode() for p in (changes + untracked + library).split(b"\0") if p}
    templates = sorted(p for p in paths if p.startswith("templates/"))
    _need(all(p.endswith(".html") for p in templates), "unexpected template source mutation")
    site = sorted(p for p in paths if p.startswith("site/"))
    removed = [p for p in site if not (root / p).exists()]
    output = [r["path"] for r in receipt["produced_data"]]
    output += [p for p in site if p not in removed]
    output += ["site/intl.html", "site/intl_stocks.html"]
    receipt["manifest"] = build_manifest(root, receipt["source_sha"], receipt["inputs"], sorted(set(output)))
    receipt["managed_templates"] = capture_inputs(root, templates)
    receipt["removed_site"] = capture_inputs(root, removed)
    receipt_path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")


def verify(root, receipt_path, target_ref=None, candidate_ref=None):
    receipt = _load(receipt_path)
    _validate_producer(root, receipt)
    manifest = receipt["manifest"]
    _need(all(r["path"].startswith("templates/") and r["path"].endswith(".html")
              for r in receipt["managed_templates"]), "invalid managed template output")
    _need(all(r["path"].startswith("site/") and r["exists"] is False
              for r in receipt["removed_site"]), "invalid managed deletion")
    validate_manifest(root, manifest)
    validate_unchanged(root, receipt["managed_templates"])
    validate_unchanged(root, receipt["removed_site"])
    if target_ref:
        target = _git(root, "rev-parse", target_ref + "^{commit}").decode().strip()
        _check_source(root, receipt, target)
        validate_at_ref(root, target, receipt["inputs"])
        # An output written by another invocation is not ours to overwrite,
        # even when that invocation used the same source or an older asof.
        validate_at_ref(root, target, receipt["preimages"])
    if candidate_ref:
        candidate = _git(root, "rev-parse", candidate_ref + "^{commit}").decode().strip()
        validate_at_ref(root, candidate, manifest["outputs"])
        validate_at_ref(root, candidate, receipt["managed_templates"])
        validate_at_ref(root, candidate, receipt["removed_site"])
    return receipt


def stage(root, receipt_path):
    receipt = verify(root, receipt_path)
    paths = {r["path"] for r in receipt["manifest"]["outputs"]}
    paths.update(r["path"] for key in ("managed_templates", "removed_site") for r in receipt[key])
    _need(not _git(root, "diff", "--cached", "--name-only"), "preexisting staged changes")
    _git(root, "add", "-f", "--", *sorted(paths))
    staged = set(_git(root, "diff", "--cached", "--name-only", "-z").decode().split("\0")) - {""}
    _need(staged <= paths, "unmanifested staged output")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "finalize", "verify", "stage"))
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--expected-source")
    parser.add_argument("--target-ref")
    parser.add_argument("--candidate-ref")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.action == "build":
        build(root, args.expected_source, args.receipt)
    elif args.action == "finalize":
        finalize(root, args.receipt)
    elif args.action == "stage":
        stage(root, args.receipt)
    else:
        verify(root, args.receipt, args.target_ref, args.candidate_ref)


if __name__ == "__main__":
    main()
