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
import sys
import stat
import tempfile

# File-path invocation must resolve this checkout before ambient repo packages.
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

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


def _save_receipt(path, receipt, *, initial=False, expected=None):
    """Exclusive job-local custody; never replay/overwrite a foreign receipt."""
    raw = json.dumps(receipt, sort_keys=True).encode("utf-8")
    _need(len(raw) <= 16 * 1024 * 1024, "receipt too large")
    if initial:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    else:
        old = path.lstat()
        _need(stat.S_ISREG(old.st_mode) and old.st_nlink == 1
              and old.st_uid == os.getuid(), "receipt custody differs")
        _need(type(expected) is str and re.fullmatch("[0-9a-f]{64}", expected), "receipt preimage missing")
        fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
        current = os.fstat(fd)
        if (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns) != (
                old.st_dev, old.st_ino, old.st_size, old.st_mtime_ns):
            os.close(fd)
            raise DurablePublicationError("receipt changed before checkpoint")
    try:
        if not initial:
            with os.fdopen(fd, "rb", closefd=False) as previous:
                _need(sha256(previous.read(16 * 1024 * 1024 + 1)).hexdigest() == expected,
                      "receipt preimage changed; preserve original operation")
            os.lseek(fd, 0, os.SEEK_SET)
        # No replace/delete: a crash may leave a partial, explicitly unusable
        # original receipt, never an old success that a new attempt may adopt.
        os.ftruncate(fd, 0)
        with os.fdopen(fd, "wb", closefd=False) as out:
            out.write(raw); out.flush(); os.fsync(fd)
    finally:
        os.close(fd)
    return sha256(raw).hexdigest()


def _action_tokens(root, receipt):
    """Bind actual serialized anchors, including every qualified public field."""
    from html.parser import HTMLParser
    from urllib.parse import parse_qs, urlsplit
    from lib.intl_generation_publication import read_generation_publication
    from lib.intl_investigation_action import build_intl_investigation_action
    publication = read_generation_publication(data_root=root / "data")
    contract = json.loads(publication["artifact_bytes"])
    tokens = []
    class Links(HTMLParser):
        def handle_starttag(self, tag, attributes):
            if tag != "a" or not any(k == "data-im-investigate" for k, _ in attributes):
                return
            attrs = dict(attributes)
            _need(len(attrs) == len(attributes), "duplicate action attribute")
            href = attrs.get("data-im-investigation-href", "")
            query = parse_qs(urlsplit(href).query, keep_blank_values=True, strict_parsing=True)
            _need(len(query.get("intl_return", [])) == 1, "action return missing")
            field = attrs.get("data-im-investigation-field")
            expected = build_intl_investigation_action(
                contract=contract, descriptor=receipt["descriptor"],
                context_id=attrs.get("data-im-investigation-context"),
                selected_measure_ids=[field], return_url=query["intl_return"][0])
            _need(expected is not None and expected["href"] == href
                  and attrs.get("href") == "https://app.mastermind-x.com" + href
                  and attrs.get("data-im-investigation-generation") == expected["generation"]
                  and attrs.get("data-im-investigation-fingerprint") == expected["fingerprint"],
                  "action differs from exact public generation")
            tokens.append([self.page, field, expected["context_id"], href])
    parser = Links()
    for page in ("site/intl.html", "site/intl_stocks.html"):
        parser.page = page
        parser.feed((root / page).read_text(encoding="utf-8"))
    parser.close()
    _need({t[1] for t in tokens} == set(receipt["public_delivery"]["spec"]["fields"])
          and tokens, "qualified action fields missing or substituted")
    return sorted(tokens)




def intl_public_objects(descriptor, *, composed=None):
    """Derive and qualify a closed public closure BEFORE obtaining write capability."""
    from scripts.publish_r2 import _INTL_ORIGIN, _intl_need
    from scripts.build_intl import _native_policy_document_sha256
    from lib import config
    from lib.intl_generation_publication import (read_generation_publication, _parse_json, CURRENT_NAME,
        _intl_disclosure, _intl_points, _INTL_PUBLIC)
    from lib.intl_durable_publication import capture_inputs, validate_unchanged
    root = config.ROOT.resolve()
    _intl_need(Path(config.data_dir()).resolve() == root / 'data'
                and (root / config.load()['storage']['site_dir']).resolve() == root / 'site', 'noncanonical publication roots')
    publication = read_generation_publication(data_root=root / 'data')
    _intl_need(publication['status'] == 'ready' and publication['descriptor'] == descriptor,
                'no exact ready generation to publish')
    c = _parse_json(publication['artifact_bytes'])
    settings = config.load()
    decisions = {sid: {'owner_ref': 'scripts/build_intl.py',
        'policy_ref': 'docs/INTERNATIONAL_MACRO_DATA_CONTRACT.md#' + ref} for sid, ref in _INTL_PUBLIC.items()}
    decisions['mapping'] = {'owner_ref': 'scripts/build_intl.py',
        'policy_ref': 'docs/INTERNATIONAL_MACRO_DATA_CONTRACT.md#official-ecb-boe-policy-comparison'}
    documents = _native_policy_document_sha256(decisions)
    fields = _intl_disclosure(c, settings, documents)
    _intl_need(fields, 'no admitted public action fields')
    directory = 'data/intl/publication/generations/'
    current = (root / directory / CURRENT_NAME).read_bytes()
    names = [descriptor['artifact_name'], 'intl_generation_descriptor_' + sha256(current).hexdigest() + '.json', CURRENT_NAME]
    if c.get('policy_points_ref') is not None:
        names.insert(0, c['policy_points_ref']['artifact_name'])
    paths = [directory + name for name in names]
    if composed is None:
        feeds = root / 'site/feeds'
        paths += ['site/feeds/' + name for name in names]
    else:
        feeds = Path(composed)
        _intl_need(feeds.is_absolute() and feeds.resolve(strict=True) == feeds
                    and feeds.is_dir() and not feeds.is_symlink()
                    and feeds.stat().st_uid == os.getuid() and feeds.stat().st_mode & 0o077 == 0,
                    'full composition destination is not private owned scratch')
    snapshot = capture_inputs(root, paths); blobs = {}
    for name in names:
        raw = (root / directory / name).read_bytes()
        from lib.intl_macro_publication import _read_stable_once
        _intl_need(raw == _read_stable_once(feeds / name, 8 * 1024 * 1024), 'feed/producer bytes differ')
        blobs[name] = raw
    if c.get('policy_points_ref') is not None:
        _intl_points(c, blobs[c['policy_points_ref']['artifact_name']], settings, documents)
    validate_unchanged(root, snapshot)
    origin = (config.load().get('r2_data_plane') or {}).get('public_base')
    _intl_need(origin == _INTL_ORIGIN, 'configured public origin differs from native consumer')
    return {'origin': origin, 'generation': c['generation'], 'fields': fields,
            'audience': 'public-international-generation-v1', 'descriptor_sha256': sha256(current).hexdigest(),
            'objects': [{'name': n, 'sha256': sha256(blobs[n]).hexdigest(), 'bytes': len(blobs[n])} for n in names]}, blobs, snapshot


def verify_intl_publication(descriptor, delivery):
    from lib.intl_durable_publication import validate_unchanged
    from scripts.publish_r2 import _intl_need, _verify_intl_transport
    from lib import config
    spec, blobs, snapshot = intl_public_objects(descriptor)
    _intl_need(type(delivery) is dict and delivery.get('state') == 'verified'
                and delivery.get('spec') == spec, 'publication is not verified for this exact closure')
    _verify_intl_transport(spec, blobs)
    validate_unchanged(config.ROOT.resolve(), snapshot)
    return spec


def _validate_delivery(root, receipt):
    _need(receipt.get("action_html_state") == "activated", "native actions not activated")
    verify_intl_publication(receipt["descriptor"], receipt.get("public_delivery"))
    _need(_action_tokens(root, receipt) == receipt.get("action_tokens"), "native actions changed")


def _copy_selected_feed(root, relative, raw):
    # Exact admitted namespace only; no sibling restore/delete or symlink escape.
    _check_output_path(GEN_DIR + Path(relative).name)
    _need(relative == "site/feeds/" + Path(relative).name, "invalid selected feed path")
    before = capture_inputs(root, [relative])[0]
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_NOFOLLOW | os.O_CREAT
    if not before["exists"]:
        flags |= os.O_EXCL
    fd = os.open(path, flags, 0o644)
    try:
        identity = os.fstat(fd)
        _need(stat.S_ISREG(identity.st_mode) and identity.st_nlink == 1
              and identity.st_uid == os.getuid(), "selected feed custody differs")
        if before["exists"]:
            validate_unchanged(root, [before])
            _need(identity.st_ino == before["identity"]["ino"]
                  and identity.st_dev == before["identity"]["dev"], "selected feed changed before write")
        os.ftruncate(fd, 0)
        with os.fdopen(fd, "wb", closefd=False) as out:
            out.write(raw); out.flush(); os.fsync(fd)
    finally:
        os.close(fd)
    _need(path.read_bytes() == raw, "selected feed write/readback differs")


def build(root, expected_source, receipt_path):
    _need(not os.path.lexists(receipt_path), "original receipt already exists; no replay")
    _need(os.environ.get("GITHUB_RUN_ATTEMPT", "1") == "1",
          "durable publication rerun refused; reconcile original operation first")
    _need(os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
          and os.environ.get("INTL_DURABLE_MODE") == "true"
          and os.environ.get("INTL_RENDER_SCOPE") == "intl", "manual intl opt-in required")
    _need(os.environ.get("COLLECT_LANE", "") in ("", "render")
          and os.environ.get("US_LANE", "") in ("", "render")
          and os.environ.get("RENDER_NO_DRIP") == "1", "render-only environment required")
    head = _git(root, "rev-parse", "HEAD").decode().strip()
    _need(head == expected_source, "render source changed before build")
    receipt = {"schema": SCHEMA, "invocation": _invocation(), "source_sha": head,
               "source_entries": _source_entries(root, head)}
    _check_source(root, receipt, head)
    _need(not _git(root, "diff", "--name-only", "HEAD", "--", "site/", "templates/"),
          "preexisting managed output changes")
    receipt["preimages"] = capture_inputs(root, [RISK, CURRENT])
    inputs = {r["path"]: r for r in capture_inputs(root, _extra_inputs(root))}
    from lib import config
    _need((root / config.load()["storage"]["site_dir"]).resolve() == root / "site",
          "noncanonical site root")
    from scripts import publish_r2
    from lib.intl_generation_publication import _validate_descriptor, _parse_json
    target = publish_r2._capture_intl_target()
    if target['body'] is not None:
        _validate_descriptor(_parse_json(target['body']))
    receipt['public_preimage'] = target['prior']
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
    # SAME full composer in an owned temporary destination. Unrelated siblings
    # and the global feed metadata never become this selected delivery's writes.
    with tempfile.TemporaryDirectory(prefix="intl-full-feeds-", dir=receipt_path.parent) as scratch:
        out = Path(scratch)
        calendar = root / "site/feeds/event_calendar.json"
        if calendar.exists():
            (out / calendar.name).write_bytes(calendar.read_bytes())
        with _observe_store(root, inputs):
            _need(type(build_feeds.build(render_only=True, output_dir=out)) is dict,
                  "full feed composition failed")
        _need(paths == _closure(root, result["descriptor"]), "feed composition changed generation")
        _spec, admitted, _snapshot = intl_public_objects(result["descriptor"], composed=out)
        for path in paths:
            raw = admitted[Path(path).name]
            _need(raw == (root / path).read_bytes(), "full-composer generation differs from native producer")
            _copy_selected_feed(root, "site/feeds/" + Path(path).name, raw)
    receipt.update(inputs=sorted(inputs.values(), key=lambda r: r["path"]),
                   produced_data=capture_inputs(root, [RISK, *paths]),
                   descriptor=result["descriptor"], risk_sha256=publication.artifact_sha256)
    validate_unchanged(root, receipt["inputs"])
    validate_at_ref(root, head, receipt["inputs"])
    _check_source(root, receipt, head)
    receipt["public_delivery"] = {}
    receipt["action_html_state"] = "unavailable"
    previous_receipt = None
    def checkpoint():
        nonlocal previous_receipt
        previous_receipt = _save_receipt(receipt_path, receipt,
            initial=previous_receipt is None, expected=previous_receipt)
    checkpoint()
    from scripts import publish_r2
    publish_r2._publish_intl(
        authorize=lambda: intl_public_objects(receipt["descriptor"]), state=receipt["public_delivery"],
        checkpoint=checkpoint,
        fence=lambda: _validate_producer(root, receipt), target=target)
    _need(callable(result.get("activate_pages")), "same-call action renderer absent")
    pages = result["activate_pages"](receipt["public_delivery"])
    _need(type(pages) is dict and set(pages) == {"site/intl.html", "site/intl_stocks.html"}
          and all(sha256((root / p).read_bytes()).hexdigest() == h for p, h in pages.items()),
          "activated pages differ from same-call write")
    receipt["action_tokens"] = _action_tokens(root, receipt)
    receipt["action_html_state"] = "activated"
    _validate_producer(root, receipt)
    _validate_delivery(root, receipt)
    checkpoint()


def _read_receipt(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        _need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
              and before.st_uid == os.getuid() and before.st_size <= 16 * 1024 * 1024,
              "receipt custody/size differs")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(16 * 1024 * 1024 + 1)
        after = os.fstat(fd)
        _need((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
              (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
              and len(raw) == before.st_size, "receipt changed during read")
        return raw
    finally:
        os.close(fd)


def _load(path):
    value = json.loads(_read_receipt(path))
    _need(type(value) is dict and value.get("schema") == SCHEMA, "wrong render receipt")
    return value


def _validate_producer(root, receipt):
    validate_unchanged(root, receipt["produced_data"])
    validate_unchanged(root, receipt["inputs"])
    _need(sha256((root / RISK).read_bytes()).hexdigest() == receipt["risk_sha256"], "Risk changed")
    _closure(root, receipt["descriptor"])
    _check_source(root, receipt, receipt["source_sha"])


def finalize(root, receipt_path):
    original_receipt = sha256(_read_receipt(receipt_path)).hexdigest()
    receipt = _load(receipt_path)
    _validate_producer(root, receipt)
    _validate_delivery(root, receipt)
    changes = _git(root, "diff", "--name-only", "-z", receipt["source_sha"], "--", "site/", "templates/")
    untracked = _git(root, "ls-files", "--others", "--exclude-standard", "-z", "--", "site/", "templates/")
    library = _git(root, "ls-files", "--others", "--ignored", "--exclude-standard", "-z", "--",
                   "site/intlstockdata/", "site/intlohlc/", "site/factordata/intl_setups.json")
    paths = {p.decode() for p in (changes + untracked + library).split(b"\0") if p}
    templates = sorted(p for p in paths if p.startswith("templates/"))
    _need(all(p.endswith(".html") for p in templates), "unexpected template source mutation")
    selected_feeds = {"site/feeds/" + Path(p).name for p in _closure(root, receipt["descriptor"])}
    site = sorted(p for p in paths if p.startswith("site/")
                  and (not p.startswith("site/feeds/") or p in selected_feeds))
    removed = [p for p in site if not (root / p).exists()]
    output = [r["path"] for r in receipt["produced_data"]]
    output += [p for p in site if p not in removed]
    output += ["site/intl.html", "site/intl_stocks.html"]
    receipt["manifest"] = build_manifest(root, receipt["source_sha"], receipt["inputs"], sorted(set(output)))
    receipt["managed_templates"] = capture_inputs(root, templates)
    receipt["removed_site"] = capture_inputs(root, removed)
    _save_receipt(receipt_path, receipt, expected=original_receipt)


def verify(root, receipt_path, target_ref=None, candidate_ref=None):
    receipt = _load(receipt_path)
    _validate_producer(root, receipt)
    _validate_delivery(root, receipt)
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


def _invocation():
    result = {}
    for key in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"):
        value = os.environ.get(key)
        _need(value is None or (type(value) is str and re.fullmatch(r"[1-9][0-9]{0,19}", value)),
              "invalid workflow invocation")
        result[key] = value
    return result


def metadata(receipt_path):
    """Narrow retention of this original attempt, never a ready/admission token.

    No input inventory, receipt bodies, Risk payload, environment, exception
    prose or raw SDK config is copied. Missing/corrupt/foreign data produces a
    fixed unavailable result; it cannot be misreported as completed publication.
    """
    unavailable = {"schema": "intl.durable_attempt_summary.v1", "state": "unavailable"}
    try:
        receipt = _load(receipt_path)
        _need(receipt.get("invocation") == _invocation(), "different original invocation")
        source = receipt["source_sha"]
        _need(type(source) is str and re.fullmatch(r"[0-9a-f]{40}", source), "invalid source identity")
        delivery = receipt["public_delivery"]
        _need(type(delivery) is dict and delivery.get("schema") == "intl.public-delivery.v1"
              and delivery.get("state") in {"prepared", "put_inflight", "refused", "unknown",
                  "uploaded", "readback_unavailable", "verified"}, "unavailable delivery state")
        spec = delivery["spec"]
        from scripts.publish_r2 import _INTL_ORIGIN
        from lib.intl_generation_publication import _INTL_PUBLIC
        _need(spec["origin"] == _INTL_ORIGIN and spec["audience"] == "public-international-generation-v1"
              and type(spec["generation"]) is str and re.fullmatch(
                  r"im-workspace-generation:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", spec["generation"])
              and type(spec["fields"]) is list and spec["fields"]
              and set(spec["fields"]) <= set(_INTL_PUBLIC), "unavailable public scope")
        objects = spec["objects"]
        _need(type(objects) is list and 3 <= len(objects) <= 4, "unavailable closure")
        safe = []
        for obj in objects:
            _check_output_path(GEN_DIR + obj["name"])
            _need(re.fullmatch(r"[0-9a-f]{64}", obj["sha256"])
                  and type(obj["bytes"]) is int and 0 < obj["bytes"] <= 8 * 1024 * 1024,
                  "invalid public object identity")
            safe.append({k: obj[k] for k in ("name", "sha256", "bytes")})
        transport = delivery.get("transport")
        _need(type(transport) is dict and set(transport) == {
              "boto3", "botocore", "service", "operation", "conditions", "total_max_attempts", "body"}
              and all(type(transport[k]) is str and re.fullmatch(r"[0-9]{1,5}(?:\.[0-9]{1,5}){2}", transport[k])
                      for k in ("boto3", "botocore"))
              and transport["service"] == "s3" and transport["operation"] == "PutObject"
              and transport["conditions"] == ["If-Match", "If-None-Match"]
              and transport["total_max_attempts"] == 1
              and transport["body"] == "identity-json; public read compared after content decoding",
              "unavailable transport facts")
        names = {obj["name"] for obj in safe}
        _need(type(delivery["completed"]) is list and set(delivery["completed"]) <= names,
              "unavailable completion facts")
        key = delivery.get("key")
        _need(key is None or key in {"feeds/" + name for name in names}, "invalid active key")
        return {"schema": "intl.durable_attempt_summary.v1", "state": delivery["state"],
                "source_sha": source, "invocation": receipt["invocation"],
                "generation": spec["generation"], "objects": safe, "transport": transport,
                "completed": delivery["completed"], "key": key,
                "action_html_state": "activated" if receipt.get("action_html_state") == "activated" else "unavailable",
                "scope": "original-publication-attempt-only; not current rights or consumer readiness"}
    except Exception:
        return unavailable


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "finalize", "verify", "stage", "metadata"))
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--expected-source")
    parser.add_argument("--target-ref")
    parser.add_argument("--candidate-ref")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.action == "metadata":
        print(json.dumps(metadata(args.receipt), sort_keys=True))
    elif args.action == "build":
        build(root, args.expected_source, args.receipt)
    elif args.action == "finalize":
        finalize(root, args.receipt)
    elif args.action == "stage":
        stage(root, args.receipt)
    else:
        verify(root, args.receipt, args.target_ref, args.candidate_ref)


if __name__ == "__main__":
    main()
