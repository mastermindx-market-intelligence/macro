"""Offline transaction/race controls; inputs are explicitly non-economic fixtures."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from scripts import render_intl_durable as durable


def test_file_path_help_resolves_own_lib_before_hostile_pythonpath(tmp_path):
    decoy = tmp_path / "decoy"
    foreign_lib = decoy / "lib"
    foreign_lib.mkdir(parents=True)
    (foreign_lib / "__init__.py").write_text(
        'raise RuntimeError("FOREIGN_LIB_IMPORTED")\n', encoding="utf-8"
    )
    result = subprocess.run(
        [sys.executable, str(Path(durable.__file__).resolve()), "--help"],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(decoy), "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert "{build,finalize,verify,stage,metadata}" in result.stdout
    assert "FOREIGN_LIB_IMPORTED" not in result.stderr
    assert set(tmp_path.iterdir()) == {decoy}


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args]).decode().strip()


def put(root, path, body):
    p = root / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)
    return p


@pytest.fixture
def transaction(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.name", "controlled test")
    git(root, "config", "user.email", "test@example.invalid")
    put(root, "scripts/source.py", "# synthetic non-economic fixture\n")
    put(root, "data/fred/FIXTURE.parquet", "fixture retained input")
    put(root, durable.RISK, '{"old":true}')
    put(root, "site/intl.html", "old synthetic page")
    put(root, "site/obsolete.css", "old synthetic asset")
    git(root, "add", ".")
    git(root, "commit", "-qm", "controlled initial source")
    # Existing race controls now also traverse a real finite public closure,
    # still using only controlled IO and a synthetic test publication.
    from tests.test_intl_public_delivery import REAL_ROOT, REAL_SETTINGS, controlled_contract, FakeClient
    from copy import deepcopy
    from scripts.build_intl import _native_policy_document_sha256
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs/INTERNATIONAL_MACRO_DATA_CONTRACT.md").write_bytes(
        (REAL_ROOT / "docs/INTERNATIONAL_MACRO_DATA_CONTRACT.md").read_bytes())
    git(root, "add", "docs")
    git(root, "commit", "-qm", "controlled current source policy")
    source = git(root, "rev-parse", "HEAD")
    receipt = tmp_path / "receipt.json"
    from lib import config, store
    monkeypatch.setattr(config, "ROOT", root)
    monkeypatch.setattr(config, "load", lambda: deepcopy(REAL_SETTINGS))
    monkeypatch.setattr(config, "data_dir", lambda: root / "data")
    monkeypatch.setattr(store, "_path", lambda group, name: root / "data" / group / (name + ".parquet"))
    monkeypatch.setattr(store, "read", lambda group, name: (root / "data" / group / (name + ".parquet")).read_bytes())
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    monkeypatch.setenv("INTL_DURABLE_MODE", "true")
    monkeypatch.setenv("INTL_RENDER_SCOPE", "intl")
    monkeypatch.setenv("RENDER_NO_DRIP", "1")
    monkeypatch.delenv("COLLECT_LANE", raising=False)
    monkeypatch.delenv("US_LANE", raising=False)
    from lib.intl_generation_publication import publish_generation
    from lib.intl_risk_publication import publish_risk_snapshot
    calls = []
    from scripts import publish_r2
    import importlib.metadata
    monkeypatch.setattr(importlib.metadata, "version", lambda key: "1.43.126")
    public = {}; client = FakeClient(public)
    monkeypatch.setenv("R2_BUCKET", "controlled-public-only")
    monkeypatch.setenv("R2_ENDPOINT", "https://"+"0"*32+".r2.cloudflarestorage.com")
    monkeypatch.setattr(publish_r2, "_client", lambda *a, **k: client)
    def public_get(origin, name, limit, *, absent=False):
        raw = public.get("feeds/" + name)
        if raw is None and not absent:
            raise publish_r2.IntlPublicationError("controlled public missing")
        return raw
    monkeypatch.setattr(publish_r2, "_intl_public_get", public_get)
    from tests.intl_investigation_page_fixture import page_fixture, render
    from lib.intl_investigation_action import build_intl_investigation_action
    from urllib.parse import parse_qs, urlsplit
    def activate(descriptor, contract):
        def write(delivery):
            durable.verify_intl_publication(descriptor, delivery)
            ws, _, _ = page_fixture()
            for panel in ws["macros"] + ws["risks"]:
                panel["generation"] = contract["generation"]
                for sid, old in list(panel["investigation_actions"].items()):
                    back = parse_qs(urlsplit(old["href"]).query)["intl_return"][0]
                    panel["investigation_actions"][sid] = build_intl_investigation_action(
                        contract=contract, descriptor=descriptor, context_id=old["context_id"],
                        selected_measure_ids=[sid], return_url=back)
            return {p: sha256(put(root, p, render(ws)).read_bytes()).hexdigest()
                    for p in ("site/intl.html", "site/intl_stocks.html")}
        return write

    def builder(*, publication_result):
        calls.append("builder")
        store.read("fred", "FIXTURE")
        pub = publish_risk_snapshot(root / durable.RISK, {"fixture": "non-economic"})
        contract = controlled_contract()
        desc = publish_generation(data_root=root / "data", contract=contract)
        pages = {p: sha256(put(root, p, "non-economic synthetic page").read_bytes()).hexdigest()
                 for p in ("site/intl.html", "site/intl_stocks.html")}
        publication_result.update(risk_publication=pub, descriptor=desc, pages=pages,
                                  activate_pages=activate(desc, contract))
        return 0

    def feeds(*, render_only, output_dir):
        assert render_only is True
        calls.append("full-feeds")
        desc = json.loads((root / durable.CURRENT).read_bytes())
        for p in durable._closure(root, desc):
            (output_dir / Path(p).name).write_bytes((root / p).read_bytes())
        (output_dir / "feeds_meta.json").write_text('{"fixture":"full incumbent mock"}')
        (output_dir / "private-sibling.json").write_text('{"fixture":"never stage or publish"}')
        return {}

    import scripts
    builder_module = SimpleNamespace(main=builder, _native_policy_document_sha256=_native_policy_document_sha256)
    feed_module = SimpleNamespace(build=feeds)
    monkeypatch.setitem(sys.modules, "scripts.build_intl", builder_module)
    monkeypatch.setitem(sys.modules, "scripts.build_feeds", feed_module)
    monkeypatch.setattr(scripts, "build_intl", builder_module, raising=False)
    monkeypatch.setattr(scripts, "build_feeds", feed_module, raising=False)
    return SimpleNamespace(root=root, source=source, receipt=receipt, calls=calls,
                           builder=builder_module, feeds=feed_module, public=public, client=client)


def build(t):
    durable.build(t.root, t.source, t.receipt)


def finish(t):
    build(t)
    # Canonical normalization is allowed between producer receipt and sealing.
    with (t.root / "site/intl.html").open("a") as out:
        out.write(" canonical asset transform")
    durable.finalize(t.root, t.receipt)


def test_same_invocation_partial_generation_bounded_stage_and_candidate(transaction):
    t = transaction
    finish(t)
    put(t.root, "data/run_status.json", "must not publish")
    put(t.root, "data/unrelated/private.json", "must not publish")
    durable.stage(t.root, t.receipt)
    paths = set(git(t.root, "diff", "--cached", "--name-only").splitlines())
    assert durable.RISK in paths
    assert durable.CURRENT in paths
    assert "site/feeds/feeds_meta.json" not in paths
    assert "site/feeds/private-sibling.json" not in paths
    assert "site/intl.html" in paths
    assert not {"data/run_status.json", "data/unrelated/private.json"} & paths
    assert not any(p.endswith(".parquet") for p in paths)
    git(t.root, "commit", "-qm", "controlled produced closure")
    durable.verify(t.root, t.receipt, target_ref=t.source, candidate_ref="HEAD")
    assert t.calls == ["builder", "full-feeds"]


@pytest.mark.parametrize("key,value", [
    ("GITHUB_EVENT_NAME", "push"), ("INTL_DURABLE_MODE", "false"),
    ("INTL_RENDER_SCOPE", "all"), ("INTL_RENDER_SCOPE", "intl+macro"),
    ("COLLECT_LANE", "nightly"), ("US_LANE", "nightly"),
    ("RENDER_NO_DRIP", "0"),
])
def test_unadmitted_modes_refuse_before_builder(transaction, monkeypatch, key, value):
    t = transaction
    monkeypatch.setenv(key, value)
    with pytest.raises(durable.DurablePublicationError):
        build(t)
    assert t.calls == []


def test_resilient_exit_zero_and_identical_old_file_never_supply_success(transaction):
    t = transaction
    old = (t.root / durable.RISK).read_bytes()
    t.builder.main = lambda **kwargs: 0
    with pytest.raises(durable.DurablePublicationError, match="this invocation"):
        build(t)
    assert (t.root / durable.RISK).read_bytes() == old
    assert not t.receipt.exists()


def test_failed_identical_write_has_no_success_receipt(transaction, monkeypatch):
    t = transaction
    from lib.intl_risk_publication import publish_risk_snapshot
    payload = {"fixture": "non-economic"}
    publish_risk_snapshot(t.root / durable.RISK, payload)
    git(t.root, "add", durable.RISK)
    git(t.root, "commit", "-qm", "controlled identical previous payload")
    t.source = git(t.root, "rev-parse", "HEAD")
    original = Path.write_text

    def fail(path, *args, **kwargs):
        if path == t.root / durable.RISK:
            raise OSError("controlled failed write")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail)
    builder = t.builder.main

    def resilient(**kwargs):
        try:
            return builder(**kwargs)
        except OSError:
            return 0

    t.builder.main = resilient
    with pytest.raises(durable.DurablePublicationError, match="this invocation"):
        build(t)
    assert not t.receipt.exists()


@pytest.mark.parametrize("kind", ["risk", "input", "source", "selector", "page"])
def test_changed_inputs_outputs_or_source_refuse_before_staging(transaction, kind):
    t = transaction
    finish(t)
    path = {"risk": durable.RISK, "input": "data/fred/FIXTURE.parquet",
            "source": "scripts/source.py", "selector": durable.CURRENT,
            "page": "site/intl.html"}[kind]
    put(t.root, path, "changed bounded fixture")
    with pytest.raises(durable.DurablePublicationError):
        durable.stage(t.root, t.receipt)
    assert not git(t.root, "diff", "--cached", "--name-only")


@pytest.mark.parametrize("path", [durable.RISK, durable.CURRENT, "data/fred/FIXTURE.parquet", "scripts/source.py"])
def test_newer_upstream_result_input_or_source_refuses(transaction, path):
    t = transaction
    finish(t)
    # Build a distinct immutable upstream tree without altering our produced
    # worktree. A temporary index is only a controlled local test fixture.
    parent = git(t.root, "rev-parse", "HEAD")
    blob = subprocess.check_output(["git", "-C", str(t.root), "hash-object", "-w", "--stdin"], input=b"newer fixture").decode().strip()
    import os
    env = dict(os.environ, GIT_INDEX_FILE=str(t.receipt.parent / "upstream.index"))
    subprocess.run(["git", "-C", str(t.root), "read-tree", parent], env=env, check=True)
    subprocess.run(["git", "-C", str(t.root), "update-index", "--add", "--cacheinfo", "100644," + blob + "," + path], env=env, check=True)
    tree = subprocess.check_output(["git", "-C", str(t.root), "write-tree"], env=env).decode().strip()
    ref = git(t.root, "commit-tree", tree, "-p", parent, "-m", "newer fixture")
    with pytest.raises(durable.DurablePublicationError):
        durable.verify(t.root, t.receipt, target_ref=ref)


def test_removed_managed_asset_is_manifest_bound(transaction):
    t = transaction
    build(t)
    (t.root / "site/obsolete.css").unlink()
    durable.finalize(t.root, t.receipt)
    durable.stage(t.root, t.receipt)
    assert "site/obsolete.css" in git(t.root, "diff", "--cached", "--name-only")
    put(t.root, "site/obsolete.css", "reappeared")
    with pytest.raises(durable.DurablePublicationError):
        durable.verify(t.root, t.receipt)


@pytest.mark.parametrize("mode", ["120000", "100755"])
def test_same_blob_with_changed_git_file_mode_refuses(transaction, mode):
    t = transaction
    records = durable.capture_inputs(t.root, ["data/fred/FIXTURE.parquet"])
    import os
    env = dict(os.environ, GIT_INDEX_FILE=str(t.receipt.parent / "mode.index"))
    subprocess.run(["git", "-C", str(t.root), "read-tree", t.source], env=env, check=True)
    subprocess.run(["git", "-C", str(t.root), "update-index", "--cacheinfo",
                    mode + "," + records[0]["git_blob"] + ",data/fred/FIXTURE.parquet"], env=env, check=True)
    tree = subprocess.check_output(["git", "-C", str(t.root), "write-tree"], env=env).decode().strip()
    ref = git(t.root, "commit-tree", tree, "-p", t.source, "-m", "same bytes changed file mode")
    with pytest.raises(durable.DurablePublicationError, match="mode mismatch"):
        durable.validate_at_ref(t.root, ref, records)


@pytest.mark.parametrize("retained", [True, False])
def test_full_feed_render_mode_preserves_calendar_without_provider_calls(tmp_path, monkeypatch, retained):
    # Import the real incumbent feed composer, not the transaction's synthetic
    # feed stub. Only retained temporary inputs are present here.
    import importlib.util
    source = Path(__file__).resolve().parents[1] / "scripts/build_feeds.py"
    spec = importlib.util.spec_from_file_location("controlled_full_feed", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    from lib import config
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setattr(config, "load", lambda: {"storage": {"site_dir": "site"}})
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path / "data")
    from engine import event_calendar, risk_radar_intl

    def prohibited(*args, **kwargs):
        pytest.fail("render-only feed must not acquire calendar inputs")

    monkeypatch.setattr(event_calendar, "us_macro_events", prohibited)
    monkeypatch.setattr(event_calendar, "high_impact_strip", prohibited)
    monkeypatch.setattr(event_calendar, "commodity_events", prohibited)
    monkeypatch.setattr(risk_radar_intl, "snapshot", lambda profile: None)
    import socket
    monkeypatch.setattr(socket.socket, "connect", prohibited)
    old = '{"asof":"2000-01-01","fixture":"non-economic retained calendar"}'
    if retained:
        put(tmp_path, "site/feeds/event_calendar.json", old)
    put(tmp_path, "data/neuralweb/world_state.json", '{"asof":"2000-01-02"}')
    result = module.build(render_only=True)
    if retained:
        assert (tmp_path / "site/feeds/event_calendar.json").read_text() == old
        assert result["event_calendar.json"] == "2000-01-01"
    else:
        assert not (tmp_path / "site/feeds/event_calendar.json").exists()
        assert "event_calendar.json" not in result
    assert result["world_state.json"] == "2000-01-02"
    manifest = json.loads((tmp_path / "site/feeds/feeds_meta.json").read_text())
    assert {"world_state.json", "intl_generation_current.json"} <= set(manifest["artifacts"])
    if retained:
        assert manifest["artifacts"]["event_calendar.json"]["source"] == "engine/event_calendar.py"
    # Default callers still execute all three incumbent calendar operations.
    calls = []
    for name in ("us_macro_events", "high_impact_strip", "commodity_events"):
        monkeypatch.setattr(event_calendar, name, lambda *args, _name=name: calls.append(_name) or [])
    module.build()
    assert calls == ["us_macro_events", "high_impact_strip", "commodity_events"]
    assert json.loads((tmp_path / "site/feeds/event_calendar.json").read_text())["asof"] != "2000-01-01"


def test_workflow_default_off_and_existing_guards_survive():
    import yaml
    path = Path(__file__).resolve().parents[1] / ".github/workflows/render.yml"
    text = path.read_text()
    workflow = yaml.safe_load(text)
    triggers = workflow.get("on", workflow.get(True))
    assert triggers["workflow_dispatch"]["inputs"]["durable_intl"]["default"] is False
    assert "github.event_name == 'workflow_dispatch' && inputs.durable_intl == true" in text
    assert 'if [ "$INTL_DURABLE_MODE" = true ]; then' in text
    assert '--target-ref origin/main --candidate-ref "$PUBLISH_COMMIT"' in text
    assert text.index("defer and recompute, never rebase stale evidence") < text.index("git rebase --autostash")
    for guard in ("check_site_asset_refs", "check_commodity_publication", "inject_shared_shell.py --check", "push_retry_init"):
        assert guard in text
    for job in workflow["jobs"].values():
        for step in job.get("steps", []):
            if isinstance(step.get("run"), str):
                import re
                shell = re.sub(r"\$\{\{.*?\}\}", "controlled", step["run"])
                subprocess.run(["bash", "-n"], input=shell.encode(), check=True)


def test_original_receipt_and_rerun_never_replay_even_after_unknown(transaction, monkeypatch):
    t=transaction
    t.receipt.write_text('{"public_delivery":{"state":"unknown"}}')
    before=t.receipt.read_bytes()
    with pytest.raises(durable.DurablePublicationError,match='no replay'):build(t)
    assert t.receipt.read_bytes()==before and t.calls==[]
    t.receipt.unlink()
    monkeypatch.setenv('GITHUB_RUN_ATTEMPT','2')
    with pytest.raises(durable.DurablePublicationError,match='rerun'):build(t)
    assert t.calls==[]


def test_receipt_exclusive_custody_and_exact_checkpoint_preimage(tmp_path):
    path=tmp_path/'receipt.json';receipt={'schema':durable.SCHEMA}
    digest=durable._save_receipt(path,receipt,initial=True)
    with pytest.raises(FileExistsError):durable._save_receipt(path,receipt,initial=True)
    path.write_text('foreign owned file changed')
    original=path.read_bytes()
    with pytest.raises(durable.DurablePublicationError,match='preimage'):durable._save_receipt(path,receipt,expected=digest)
    assert path.read_bytes()==original
    linked=tmp_path/'linked';os.link(path,linked)
    with pytest.raises(durable.DurablePublicationError,match='custody'):durable._save_receipt(path,receipt,expected=digest)
    assert linked.read_bytes()==original
    symbolic=tmp_path/'symbolic';symbolic.symlink_to(path)
    assert durable.metadata(symbolic)=={'schema':'intl.durable_attempt_summary.v1','state':'unavailable'}
    assert path.read_bytes()==original


@pytest.mark.parametrize('mutation',['unknown','foreign-invocation','foreign-key','arbitrary-extra','corrupt'])
def test_retained_attempt_is_narrow_and_partial_never_claims_success(transaction, mutation):
    t=transaction;build(t);r=json.loads(t.receipt.read_text())
    if mutation=='unknown':r['public_delivery']['state']='unknown';r['action_html_state']='unavailable'
    elif mutation=='foreign-invocation':r['invocation']={'GITHUB_RUN_ID':'999','GITHUB_RUN_ATTEMPT':'1'}
    elif mutation=='foreign-key':r['public_delivery']['key']='private/secret-customer'
    elif mutation=='arbitrary-extra':
        r['error']='secret message';r['private']='private payload';r['public_delivery']['error']='private stack'
    else:
        t.receipt.write_text('broken secret body')
        assert durable.metadata(t.receipt)=={'schema':'intl.durable_attempt_summary.v1','state':'unavailable'}
        return
    t.receipt.write_text(json.dumps(r))
    summary=durable.metadata(t.receipt)
    raw=json.dumps(summary)
    assert not any(text in raw for text in ('secret','private payload','private stack','source_entries','risk_sha256','inputs'))
    if mutation in ('foreign-invocation','foreign-key'):assert summary['state']=='unavailable'
    elif mutation=='unknown':assert summary['state']=='unknown' and summary['action_html_state']=='unavailable'
    else:assert summary['state']=='verified'


def test_finalization_rejects_changed_or_removed_actual_action(transaction):
    t=transaction;build(t)
    page=t.root/'site/intl.html'
    page.write_text(page.read_text().replace('data-im-investigation-generation="im-workspace-generation:',
                                           'data-im-investigation-generation="foreign:'))
    with pytest.raises(durable.DurablePublicationError,match='action'):durable.finalize(t.root,t.receipt)


def test_workflow_retains_only_safe_original_attempt_even_on_failure():
    import yaml
    text=(Path(__file__).resolve().parents[1]/'.github/workflows/render.yml').read_text()
    steps=[step for job in yaml.safe_load(text)['jobs'].values() for step in job.get('steps',[])]
    prepare=next(s for s in steps if s.get('id')=='intl_durable_evidence')
    upload=next(s for s in steps if s.get('name')=='Upload original durable International attempt facts')
    assert 'always()' in prepare['if'] and "inputs.durable_intl == true" in prepare['if']
    assert 'metadata --receipt' in prepare['run'] and 'intl-durable-attempt.json' in prepare['run']
    assert "steps.intl_durable_evidence.outcome == 'success'" in upload['if']
    assert upload['with']['path']=='${{ runner.temp }}/intl-durable-attempt.json'
    assert upload['with']['if-no-files-found']=='error'
    assert "python -m pip install 'boto3==1.40.0' 'botocore==1.40.0' || exit 1" in text


def test_original_public_selector_is_not_the_git_preimage(transaction):
    t=transaction
    from tests.intl_investigation_page_fixture import FIXTURE
    original=(FIXTURE/'intl_generation_current.json').read_bytes()
    t.public['feeds/intl_generation_current.json']=original
    assert not (t.root/durable.CURRENT).exists()
    build(t)
    receipt=json.loads(t.receipt.read_bytes())
    assert next(r for r in receipt['preimages'] if r['path']==durable.CURRENT)['exists'] is False
    assert receipt['public_preimage']['sha256']==sha256(original).hexdigest()
    assert t.client.puts[-1]['IfMatch']=='"'+sha256(original).hexdigest()+'"'
    assert receipt['action_html_state']=='activated'


def test_new_public_selector_during_computation_never_becomes_original(transaction):
    t=transaction;normal=t.builder.main
    def concurrent(**kwargs):
        rc=normal(**kwargs)
        t.public['feeds/intl_generation_current.json']=b'newer committed public selector'
        return rc
    t.builder.main=concurrent
    with pytest.raises(Exception,match='original public/bucket current changed'):build(t)
    assert t.client.puts==[]
    receipt=json.loads(t.receipt.read_bytes())
    assert receipt['public_preimage']['exists'] is False
    assert receipt['action_html_state']=='unavailable'


def test_full_composition_preserves_existing_unrelated_feed_bytes_and_clean_stage(transaction):
    t=transaction
    paths={'site/feeds/feeds_meta.json':'original full metadata','site/feeds/private-sibling.json':'original sibling'}
    for p,body in paths.items():put(t.root,p,body)
    git(t.root,'add','site/feeds');git(t.root,'commit','-qm','controlled retained siblings')
    t.source=git(t.root,'rev-parse','HEAD')
    finish(t);durable.stage(t.root,t.receipt)
    for p,body in paths.items():assert (t.root/p).read_text()==body
    assert set(git(t.root,'diff','--name-only').splitlines())==set()
    staged=set(git(t.root,'diff','--cached','--name-only').splitlines())
    assert not staged.intersection(paths)


@pytest.mark.parametrize('kind',['relative','symlink','hardlink'])
def test_selected_feed_copy_never_escapes_or_overwrites_linked_files(tmp_path,kind):
    root=tmp_path/'repo';root.mkdir();external=tmp_path/'foreign';external.write_bytes(b'unchanged')
    target='site/feeds/intl_generation_current.json'
    (root/'site/feeds').mkdir(parents=True)
    if kind=='relative':target='../site/feeds/intl_generation_current.json'
    elif kind=='symlink':(root/target).symlink_to(external)
    else:os.link(external,root/target)
    with pytest.raises((durable.DurablePublicationError,OSError)):
        durable._copy_selected_feed(root,target,b'changed')
    assert external.read_bytes()==b'unchanged'


def test_full_composer_optional_destination_preserves_default_bytes_and_input_provenance(tmp_path,monkeypatch):
    import importlib.util,shutil
    from datetime import datetime,timezone
    source=Path(__file__).resolve().parents[1]/'scripts/build_feeds.py'
    spec=importlib.util.spec_from_file_location('controlled_destination_feeds',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    from lib import config
    monkeypatch.setattr(config,'ROOT',tmp_path)
    monkeypatch.setattr(config,'load',lambda:{'storage':{'site_dir':'site'}})
    monkeypatch.setattr(config,'data_dir',lambda:tmp_path/'data')
    class Clock:
        @staticmethod
        def now(zone):return datetime(2000,1,2,tzinfo=timezone.utc)
    monkeypatch.setattr(module,'datetime',Clock)
    from engine import event_calendar,risk_radar_intl
    def prohibited(*a,**k):pytest.fail('no provider/calendar acquisition')
    for fn in ('us_macro_events','high_impact_strip','commodity_events'):
        monkeypatch.setattr(event_calendar,fn,prohibited)
    monkeypatch.setattr(risk_radar_intl,'snapshot',lambda profile:None)
    retained=put(tmp_path,'site/feeds/event_calendar.json','{"asof":"2000-01-01","fixture":"retained original"}')
    default=module.build(render_only=True)
    baseline={p.name:p.read_bytes() for p in retained.parent.iterdir()}
    out=tmp_path/'owned-output';out.mkdir();shutil.copyfile(retained,out/retained.name)
    redirected=module.build(render_only=True,output_dir=out)
    assert redirected==default
    assert {p.name:p.read_bytes() for p in out.iterdir()}==baseline
    assert {p.name:p.read_bytes() for p in retained.parent.iterdir()}==baseline


def test_attempt_retention_rejects_arbitrary_transport_values(transaction):
    t=transaction;build(t);r=json.loads(t.receipt.read_bytes())
    r['public_delivery']['transport']['boto3']='private arbitrary error text'
    t.receipt.write_text(json.dumps(r))
    assert durable.metadata(t.receipt)=={'schema':'intl.durable_attempt_summary.v1','state':'unavailable'}
