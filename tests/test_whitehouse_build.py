"""scripts/build_whitehouse.py + scripts/inject_wh_banner.py tests — banner expiry,
idempotent writes, ledger supersede, page render (no network/LLM), and banner
injection idempotency.

Run: python -m tests.test_whitehouse_build
"""
from __future__ import annotations

import json
import sys
import tempfile
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import config  # noqa: E402
from scripts import build_whitehouse as bw  # noqa: E402
from scripts import inject_wh_banner as inj  # noqa: E402


def _rec(rid, pub_days_ago, banner_days, importance, activated=True):
    pub = datetime.now(timezone.utc) - timedelta(days=pub_days_ago)
    return {
        "schema": "wh_alert.v1", "id": rid, "activated": activated,
        "source_title": rid, "source_url": "https://wh/x", "section": "news",
        "published": pub.isoformat(), "generated_at": pub.isoformat(),
        "importance": importance, "banner_days": banner_days, "tone": "tailwind",
        "banner_title": f"title {rid}", "banner_title_zh": None,
        "summary": "s", "summary_zh": None, "analysis": "p1\np2",
        "sectors": [{"name": "Tech", "impact": "tailwind", "rationale": "r"}],
        "tickers": [{"symbol": "NVDA", "direction": "benefit", "rationale": "r", "chg_pct": 1.5},
                    {"symbol": "INTC", "direction": "hurt", "rationale": "r", "chg_pct": -2.0}],
        "confidence": "high",
    }


def test_banner_payload_filters_expired_and_sorts() -> None:
    now = datetime.now(timezone.utc)
    rows = [
        _rec("wh-live-low", 1, 5, 65),     # live, expires in 4d
        _rec("wh-live-high", 0, 7, 90),    # live, most important
        _rec("wh-expired", 10, 3, 80),     # published 10d ago, 3d banner → expired
    ]
    payload = bw._banner_payload(rows, now)
    ids = [a["id"] for a in payload["alerts"]]
    assert "wh-expired" not in ids
    assert ids == ["wh-live-high", "wh-live-low"]   # importance desc
    a = payload["alerts"][0]
    assert a["href"] == "whitehouse.html#wh-live-high"
    assert a["tickers"][0]["symbol"] == "NVDA"
    assert "expires_at" in a and a["schema"] if "schema" in a else True
    assert payload["schema"] == "wh_banner.v1"


def test_expires_at_math() -> None:
    r = _rec("wh-x", 2, 5, 70)
    exp = bw._expires_at(r)
    gen = datetime.fromisoformat(r["generated_at"])
    assert exp == gen + timedelta(days=5)               # anchored on generated_at
    assert bw._expires_at({"published": "", "banner_days": 0}) is None


def test_expiry_anchored_on_activation_not_stale_publish() -> None:
    # an item PUBLISHED 4 days ago but only just ACTIVATED (generated_at=now) with a
    # short 1-day banner must still be LIVE — anchoring on published would mis-expire it
    now = datetime.now(timezone.utc)
    r = _rec("wh-stale-pub", 4, 1, 80)
    r["generated_at"] = now.isoformat()                 # activated just now
    exp = bw._expires_at(r)
    assert exp > now                                     # not born-expired
    payload = bw._banner_payload([r], now)
    assert [a["id"] for a in payload["alerts"]] == ["wh-stale-pub"]


def test_parse_dt_is_tz_aware_and_compares() -> None:
    naive = bw._parse_dt("2026-06-23")                  # date-only → naive source
    assert naive is not None and naive.tzinfo is not None
    # comparing against an aware now must not raise
    assert (datetime.now(timezone.utc) > naive) in (True, False)
    assert bw._parse_dt(None) is None and bw._parse_dt("garbage") is None


def test_banner_payload_caps_to_max() -> None:
    now = datetime.now(timezone.utc)
    rows = [_rec(f"wh-{i}", 0, 7, 60 + i) for i in range(10)]  # 10 live, distinct importance
    payload = bw._banner_payload(rows, now, max_alerts=6)
    assert len(payload["alerts"]) == 6
    # kept the most important (importance 69..64), dropped the lowest
    assert payload["alerts"][0]["importance"] == 69
    assert min(a["importance"] for a in payload["alerts"]) == 64


def test_bad_row_skipped_not_fatal() -> None:
    now = datetime.now(timezone.utc)
    good = _rec("wh-good", 0, 5, 70)
    bad = {"id": "wh-bad", "banner_days": 5, "published": None, "generated_at": None}
    payload = bw._banner_payload([good, bad], now)      # must not raise
    assert [a["id"] for a in payload["alerts"]] == ["wh-good"]


def test_write_if_changed_idempotent() -> None:
    d = Path(tempfile.mkdtemp())
    p = d / "x.json"
    assert bw._write_if_changed(p, "hello") is True       # first write
    assert bw._write_if_changed(p, "hello") is False      # identical → no write
    assert bw._write_if_changed(p, "world") is True       # changed → write


def test_ledger_append_load_supersede() -> None:
    d = Path(tempfile.mkdtemp())
    bw._append_ledger(d, _rec("wh-a", 1, 5, 70))
    bw._append_ledger(d, _rec("wh-b", 0, 5, 80))
    bw._append_ledger(d, {**_rec("wh-a", 1, 5, 99), "tone": "headwind"})  # supersede wh-a
    rows = bw._load_ledger(d)
    ids = sorted(r["id"] for r in rows)
    assert ids == ["wh-a", "wh-b"]                        # deduped by id
    a = next(r for r in rows if r["id"] == "wh-a")
    assert a["importance"] == 99 and a["tone"] == "headwind"   # latest row wins
    # inactive rows are excluded
    bw._append_ledger(d, _rec("wh-c", 0, 5, 50, activated=False))
    assert "wh-c" not in {r["id"] for r in bw._load_ledger(d)}


def test_render_page_escapes_and_links() -> None:
    # render against the real templates dir; inject a hostile title to prove escaping
    rows = [_rec("wh-xss", 0, 5, 80)]
    rows[0]["banner_title"] = "<script>alert(1)</script> tariffs"
    html = bw._render_page(config.ROOT, rows)
    assert 'id="wh-xss"' in html
    assert "<script>alert(1)</script> tariffs" not in html          # raw not present
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html          # escaped
    assert "whitehouse.gov" not in html or "wh/x" in html
    assert inj._MARKER in html                                       # self-includes banner


def test_render_empty_page_ok() -> None:
    html = bw._render_page(config.ROOT, [])
    assert "White House" in html
    assert inj._MARKER in html


def test_render_page_emits_current_asset_stamps() -> None:
    # The hourly sentinel (whitehouse-sentinel.yml) commits this page straight to
    # main with NO post-render optimize_assets pass, so the render itself must
    # carry the ?v= stamps: before 2026-07-29 every alert update regressed the
    # page to bare refs — the edge re-validated theme.css & co on every nav, and
    # the page sat dirty under `python -m scripts.optimize_assets` in every clean
    # checkout. Asserted against the real site/ tree, same as the render tests
    # above use the real templates/ dir.
    import re
    html = bw._render_page(config.ROOT, [_rec("wh-stamp", 0, 5, 80)])
    for asset in ("theme.css", "theme.js", "wh_banner.js"):
        assert re.search(re.escape(asset) + r"\?v=[0-9a-f]{8}", html), (
            f"{asset} rendered without a ?v= stamp — the sentinel would commit it bare")


def test_render_page_is_a_fixpoint_of_the_sitewide_sweep() -> None:
    # Builder-side stamping and the render lanes' site-wide sweep must produce
    # the SAME bytes, or the two lanes rewrite each other's output and
    # site/whitehouse.html oscillates on main (hourly sentinel vs daily sweep).
    # NOTE deliberately NOT a fixpoint test over the COMMITTED page: committed
    # stamps go legitimately stale whenever a shared asset changes in a PR that
    # doesn't re-render this page (the sweep lanes re-hash them post-merge), so
    # that variant reds unrelated PRs. The render-time contract is the invariant.
    from scripts.optimize_assets import make_optimizer
    site = config.ROOT / "site"
    html = bw._render_page(config.ROOT, [_rec("wh-fix", 0, 5, 80)])
    assert make_optimizer(site)(html, site) == html


def test_sector_mixed_not_rendered_as_headwind() -> None:
    # a sector normalised to 'mixed' (or any non-binary impact) must show a neutral
    # label, NOT a red Headwind that misrepresents the read
    r = _rec("wh-mix", 0, 5, 80)
    r["sectors"] = [{"name": "Banks", "impact": "mixed", "rationale": "ambiguous"}]
    html = bw._render_page(config.ROOT, [r])
    assert "wh-dir neutral" in html
    # the Banks row must not be tagged hurt/Headwind
    import re
    row = re.search(r"Banks.*?</tr>", html, re.S).group(0)
    assert "Headwind" not in row and "wh-dir hurt" not in row


def test_inject_text_idempotent() -> None:
    base = "<html><body><h1>hi</h1></body></html>"
    once = inj.inject_text(base, "")
    assert inj._MARKER in once and once.count("wh_banner.js") == 1
    twice = inj.inject_text(once, "")
    assert twice == once                                  # idempotent
    deep = inj.inject_text(base, "../")
    assert 'src="../wh_banner.js"' in deep and 'data-root="../"' in deep


def test_inject_no_body_appends() -> None:
    out = inj.inject_text("<div>no body tag</div>", "")
    assert inj._MARKER in out


def _run() -> None:
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")


if __name__ == "__main__":
    _run()
    print("all whitehouse_build tests passed")


# Source retention is host-local evidence, outside the public repository.
@pytest.fixture(autouse=True)
def isolated_source_store(tmp_path, monkeypatch):
    from engine import whitehouse_feed as wf
    directory = tmp_path.parent / (tmp_path.name + '-sources')
    monkeypatch.setattr(wf, 'SOURCE_DOCUMENT_ROOT', directory)
    return directory

def _source_item(body='Original government source text.'):
    from engine import whitehouse_feed as wf
    xml = (f'<rss xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><item>'
           f'<title>Science announcement</title><link>https://www.whitehouse.gov/fact-sheets/2026/10/science/</link>'
           f'<guid>science-1</guid><pubDate>Thu, 08 Oct 2026 15:05:06 +0000</pubDate>'
           f'<content:encoded><![CDATA[<p>{body}</p>]]></content:encoded></item></channel></rss>')
    return wf._parse(xml.encode(), 'fact-sheets')[0]


def test_source_capture_is_immutable_and_private(tmp_path):
    import hashlib
    from engine import whitehouse_feed as wf
    item = _source_item()
    ref = wf.retain_source_document(tmp_path, item)
    path = tmp_path / ref['path']
    raw = path.read_bytes()
    obj = json.loads(raw)
    assert hashlib.sha256(raw).hexdigest() == ref['sha256']
    assert obj['body'] == item['body']
    assert obj['body_sha256'] == hashlib.sha256(item['body'].encode()).hexdigest()
    assert obj['body_origin'] == 'content_encoded'
    assert obj['body_truncated'] is False
    assert obj['rights_status'] == 'unqualified'
    assert obj['allow_stage'] is False and obj['allow_emit'] is False
    before = path.stat().st_mtime_ns
    assert wf.retain_source_document(tmp_path, item) == ref
    assert path.stat().st_mtime_ns == before
    assert not (tmp_path / 'site').exists()
    assert not (tmp_path / 'data/whitehouse/processed.json').exists()


def test_source_correction_keeps_both_versions(tmp_path):
    from engine import whitehouse_feed as wf
    old = wf.retain_source_document(tmp_path, _source_item())
    new = wf.retain_source_document(tmp_path, _source_item('Corrected source text.'))
    assert old['path'] != new['path']
    assert (tmp_path / old['path']).exists() and (tmp_path / new['path']).exists()


def test_source_capture_refuses_to_replace_corruption(tmp_path):
    import pytest
    from engine import whitehouse_feed as wf
    item = _source_item()
    ref = wf.retain_source_document(tmp_path, item)
    path = tmp_path / ref['path']
    path.write_text('damaged retained evidence')
    with pytest.raises(ValueError, match='existing source document'):
        wf.retain_source_document(tmp_path, item)
    assert path.read_text() == 'damaged retained evidence'


def test_source_capture_does_not_promote_excerpt_or_truncated_text(tmp_path):
    from engine import whitehouse_feed as wf
    long = _source_item('x' * 12001)
    assert len(long['body']) == 12000 and long['body_truncated'] is True
    doc = json.loads((tmp_path / wf.retain_source_document(tmp_path, long)['path']).read_text())
    assert doc['body_truncated'] is True and doc['allow_stage'] is False
    xml = b'<rss><channel><item><title>Excerpt</title><link>https://www.whitehouse.gov/news/x/</link><pubDate>Thu, 08 Oct 2026 15:05:06 +0000</pubDate><description>Summary only.</description></item></channel></rss>'
    excerpt = wf._parse(xml, 'news')[0]
    assert excerpt['body_origin'] == 'description'
    doc = json.loads((tmp_path / wf.retain_source_document(tmp_path, excerpt)['path']).read_text())
    assert doc['body_origin'] == 'description' and doc['allow_emit'] is False


def test_source_capture_rejects_unknown_provenance_and_foreign_origin(tmp_path):
    import pytest
    from engine import whitehouse_feed as wf
    item = _source_item()
    for bad in ({**item, 'url': 'https://whitehouse.gov.attacker.invalid/story'},
                {**item, 'url': 'https://user@www.whitehouse.gov/story'},
                {**item, 'published': ''},
                {k:v for k,v in item.items() if k != 'body_origin'}):
        with pytest.raises(ValueError):
            wf.retain_source_document(tmp_path, bad)
    assert not (tmp_path / 'data').exists()


def test_source_capture_publish_failure_leaves_no_partial_document(tmp_path, monkeypatch):
    import pytest
    from engine import whitehouse_feed as wf
    def failed_link(*args, **kwargs):
        raise OSError('simulated atomic-link failure')
    monkeypatch.setattr(wf.os, 'link', failed_link)
    with pytest.raises(OSError, match='atomic-link failure'):
        wf.retain_source_document(tmp_path, _source_item())
    assert not list(bw.wf.SOURCE_DOCUMENT_ROOT.iterdir())


def _stub_source_build(monkeypatch, tmp_path, item):
    from engine import whitehouse_feed as wf
    monkeypatch.setattr(config, 'ROOT', tmp_path)
    monkeypatch.setattr(config, 'load', lambda: {})
    monkeypatch.setattr(bw.wb, '_cfg', lambda: {})
    monkeypatch.setattr(wf, 'collect', lambda: [item])
    monkeypatch.setattr(bw, '_refresh_tga', lambda *_: None)
    from engine import treasury_watch
    monkeypatch.setattr(treasury_watch, 'detect_events', lambda *_: [])
    monkeypatch.setattr(bw, '_write_treasury_watch', lambda *_: None)
    monkeypatch.setattr(bw, '_rebuild_artifacts', lambda *_: 0)
    monkeypatch.setattr(bw.wb, 'provider_label', lambda *_: '')
    monkeypatch.setattr(bw.wb, 'enabled', lambda: False)
    monkeypatch.setattr(bw.wb, 'evaluate', lambda *_: (_ for _ in ()).throw(AssertionError('unexpected provider call')))


def test_sentinel_retains_sources_without_enabling_brain(tmp_path, monkeypatch):
    item = _source_item()
    _stub_source_build(monkeypatch, tmp_path, item)
    assert bw.build() == 0
    files = list(bw.wf.SOURCE_DOCUMENT_ROOT.glob('*.json'))
    assert len(files) == 1
    assert json.loads(files[0].read_text())['body'] == item['body']
    assert not (tmp_path / 'data/whitehouse/alerts.jsonl').exists()
    assert not (tmp_path / 'site').exists()


def test_page_only_never_collects_or_retains_sources(tmp_path, monkeypatch):
    _stub_source_build(monkeypatch, tmp_path, _source_item())
    monkeypatch.setattr(bw.wf, 'collect', lambda: (_ for _ in ()).throw(AssertionError('unexpected poll')))
    assert bw.build(page_only=True) == 0
    assert not (tmp_path / 'data').exists()


def test_capture_failure_does_not_replay_or_change_desk_decisions(tmp_path, monkeypatch):
    _stub_source_build(monkeypatch, tmp_path, _source_item())
    monkeypatch.setattr(bw.wf, 'retain_source_document', lambda *_: (_ for _ in ()).throw(OSError('disk refusal')))
    assert bw.build() == 0
    assert not (tmp_path / 'data/whitehouse/alerts.jsonl').exists()


def test_concurrent_source_capture_publishes_one_complete_document(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from engine import whitehouse_feed as wf
    item = _source_item()
    with ThreadPoolExecutor(max_workers=4) as pool:
        refs = list(pool.map(lambda _: wf.retain_source_document(tmp_path, item), range(8)))
    assert all(ref == refs[0] for ref in refs)
    files = list(bw.wf.SOURCE_DOCUMENT_ROOT.iterdir())
    assert len(files) == 1 and files[0].suffix == '.json'
    assert json.loads(files[0].read_text())['body'] == item['body']


def test_seen_source_is_retained_without_replaying_brain(tmp_path, monkeypatch):
    item = _source_item()
    _stub_source_build(monkeypatch, tmp_path, item)
    state = {'seen': {}}
    bw.wf.mark_seen(state, item, activated=False, importance=1)
    bw.wf.save_processed(tmp_path, state)
    monkeypatch.setattr(bw.wb, 'enabled', lambda: True)
    monkeypatch.setattr(bw.wb, 'provider_label', lambda *_: 'test-provider')
    assert bw.build() == 0
    assert len(list(bw.wf.SOURCE_DOCUMENT_ROOT.glob('*.json'))) == 1
    assert bw.wf.load_processed(tmp_path) == state


def test_capture_failure_keeps_single_existing_brain_evaluation(tmp_path, monkeypatch):
    item = _source_item()
    _stub_source_build(monkeypatch, tmp_path, item)
    monkeypatch.setattr(bw.wf, 'retain_source_document', lambda *_: (_ for _ in ()).throw(OSError('disk refusal')))
    monkeypatch.setattr(bw.wb, 'enabled', lambda: True)
    monkeypatch.setattr(bw.wb, 'provider_label', lambda *_: 'test-provider')
    calls = []
    def evaluate(item, *_):
        calls.append(item['id'])
        return {'id': item['id'], 'activated': False, 'importance': 1}
    monkeypatch.setattr(bw.wb, 'evaluate', evaluate)
    assert bw.build() == 0
    assert calls == [item['id']]
    assert item['guid'] in bw.wf.load_processed(tmp_path)['seen']


def test_source_capture_never_enters_sentinel_git_publication(tmp_path):
    import subprocess
    from engine import whitehouse_feed as wf
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    ledger = tmp_path / 'data/whitehouse/processed.json'
    ledger.parent.mkdir(parents=True)
    ledger.write_text('{}')
    ref = wf.retain_source_document(tmp_path, _source_item())
    subprocess.run(['git', '-C', str(tmp_path), 'add', 'data/whitehouse'], check=True)
    staged = subprocess.check_output(['git', '-C', str(tmp_path), 'diff', '--cached', '--name-only'], text=True)
    assert staged.splitlines() == ['data/whitehouse/processed.json']
    assert not Path(ref['path']).is_relative_to(tmp_path)
    assert Path(ref['path']).stat().st_mode & 0o777 == 0o600
    assert Path(ref['path']).parent.stat().st_mode & 0o777 == 0o700
    assert not (tmp_path / 'data/whitehouse/source_documents').exists()


def test_source_capture_refuses_repository_local_and_symlinked_output(tmp_path):
    from engine import whitehouse_feed as wf
    public = tmp_path / 'site'
    public.mkdir()
    alias = tmp_path.parent / (tmp_path.name + '-alias')
    alias.symlink_to(public, target_is_directory=True)
    for directory in (public, alias):
        with pytest.raises(ValueError, match='outside all Git checkouts'):
            wf.retain_source_document(tmp_path, _source_item(), capture_dir=directory)
    assert not list(public.iterdir())


def test_source_capture_refuses_other_git_checkout(tmp_path):
    from engine import whitehouse_feed as wf
    other = tmp_path.parent / (tmp_path.name + '-other-repo')
    other.mkdir()
    (other / '.git').write_text('gitdir: /unrelated/shared/store')
    with pytest.raises(ValueError, match='outside all Git checkouts'):
        wf.retain_source_document(tmp_path, _source_item(), capture_dir=other / 'data')
    assert not (other / 'data').exists()


def test_source_capture_refuses_permissive_existing_directory(tmp_path):
    from engine import whitehouse_feed as wf
    directory = wf.SOURCE_DOCUMENT_ROOT
    directory.mkdir(mode=0o755)
    with pytest.raises(ValueError, match='mode 0700'):
        wf.retain_source_document(tmp_path, _source_item())
    assert not list(directory.iterdir())
    assert directory.stat().st_mode & 0o777 == 0o755


def test_source_capture_refuses_publicly_readable_existing_document(tmp_path):
    from engine import whitehouse_feed as wf
    ref = wf.retain_source_document(tmp_path, _source_item())
    path = Path(ref['path'])
    path.chmod(0o644)
    with pytest.raises(ValueError, match='existing source document'):
        wf.retain_source_document(tmp_path, _source_item())
    assert path.stat().st_mode & 0o777 == 0o644
