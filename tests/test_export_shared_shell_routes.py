"""Finite route projection: prove access/coverage boundaries, not implementation spelling."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from scripts.export_shared_shell_routes import ROOT, derive_projection, document_heading_label, document_inventory, is_html_document, navigation_labels, normalized_path

PIN = "a" * 40


def row(route, *, repo="macro", lifecycle="live", access="anonymous",
        tier="public", kind="page", page_id=None):
    return {"repo": repo, "route": route, "page_id": page_id or repo + ":" + route,
            "route_kind": kind, "lifecycle": lifecycle, "access_shell": access,
            "payload_tier": tier, "nav_family": "site_nav.market",
            "primary_user_question": "Understand the market"}


def catalog(*rows):
    return {"schema": "mastermind.page_registry.v1", "generated_at": "2026-10-18T00:00:00Z",
            "sources": {"macro": {"sha": PIN}, "terminal": {"sha": "b" * 40},
                        "mastermind": {"sha": "c" * 40}}, "pages": list(rows)}


def project(doc, paths, deny=None, labels=None):
    return derive_projection(doc, paths, deny or {"exact": set(), "prefixes": ()},
                             labels or {}, registry_digest="digest", inventory_ref=PIN)


def test_families_expand_only_concrete_tracked_documents_and_keep_payload_gates():
    doc = catalog(row("/macro.html", tier="public_shell_premium_payload"),
                  row("/stocks/<id>.html", kind="family"),
                  row("/analysis", repo="terminal", access="signed_in"))
    p = project(doc, ["/stocks/AAPL.html", "/macro.html", "/stocks/NVDA.html"])
    assert p["legacyPaths"] == ["/macro.html", "/stocks/AAPL.html", "/stocks/NVDA.html"]
    assert "/stocks/NOT_PUBLISHED.html" not in p["legacyPaths"]
    assert all("<" not in path for path in p["legacyPaths"])
    assert p["nativePaths"] == ["/analysis"]
    assert next(r for r in p["directory"] if r["href"] == "/macro.html")["payloadTier"] == "public_shell_premium_payload"


def test_exact_deny_and_prefix_deny_win_over_live_family():
    doc = catalog(row("/stocks/<id>.html", kind="family"),
                  row("/research/<slug>.html", kind="family"))
    p = project(doc, ["/stocks/private.html", "/stocks/NVDA.html", "/research/secret.html"],
                {"exact": {"/stocks/private.html"}, "prefixes": ("/research/",)})
    assert p["legacyPaths"] == ["/stocks/NVDA.html"]
    assert {r["reason"] for r in p["coverage"]["excluded"]} == {"serving_policy_denied"}


def test_exact_lifecycle_row_wins_over_a_live_family():
    doc = catalog(row("/tools/<id>.html", kind="family"),
                  row("/tools/lab.html", lifecycle="lab"))
    p = project(doc, ["/tools/lab.html", "/tools/live.html"])
    assert p["legacyPaths"] == ["/tools/live.html"]
    assert p["coverage"]["excluded"] == [{"path": "/tools/lab.html", "reason": "lifecycle_lab"}]


def test_unknown_internal_and_non_document_paths_are_never_implicitly_admitted():
    doc = catalog(row("/internal.html", lifecycle="internal"),
                  row("/account.html", access="signed_in"))
    p = project(doc, ["/new.html", "/internal.html", "/account.html"])
    assert p["legacyPaths"] == []
    assert {x["reason"] for x in p["coverage"]["excluded"]} == {
        "unregistered", "lifecycle_internal", "not_a_public_document_shell"}
    with pytest.raises(ValueError, match="invalid concrete"):
        project(doc, ["/data/private.json"])


def test_native_admin_dev_dynamic_and_landing_keep_their_original_owners():
    doc = catalog(row("/", repo="terminal"), row("/admin", repo="terminal", access="admin"),
                  row("/dev/settings", repo="terminal", lifecycle="dev_only"),
                  row("/x/<slug>", repo="terminal", kind="family"),
                  row("/terminal", repo="terminal"), row("/login", repo="terminal"))
    p = project(doc, [])
    assert p["nativePaths"] == ["/login", "/terminal"]
    assert [x["href"] for x in p["directory"]] == ["/terminal"]
    assert len(p["coverage"]["nativeExcluded"]) == 4


def test_duplicate_or_ambiguous_registry_cannot_choose_an_owner_arbitrarily():
    with pytest.raises(ValueError, match="duplicate"):
        project(catalog(row("/macro.html"), row("/macro.html")), ["/macro.html"])
    with pytest.raises(ValueError, match="ambiguous"):
        project(catalog(row("/stocks/<id>.html", kind="family"),
                        row("/stocks/<slug>.html", kind="family")), ["/stocks/AAPL.html"])


def test_native_legacy_collision_fails_the_whole_projection():
    with pytest.raises(ValueError, match="collision"):
        project(catalog(row("/macro.html"), row("/macro.html", repo="terminal")), ["/macro.html"])


def test_root_landing_alias_uses_a_real_document_and_output_is_deterministic():
    doc = catalog(row("/"), row("/macro.html"))
    first = project(doc, ["/macro.html", "/index.html", "/macro.html"])
    assert first == project(copy.deepcopy(doc), ["/index.html", "/macro.html"])
    assert first["legacyPaths"] == ["/index.html", "/macro.html"]


def test_projection_cannot_claim_a_different_source_revision():
    doc = catalog(row("/macro.html"))
    doc["sources"]["macro"]["sha"] = "d" * 40
    with pytest.raises(ValueError, match="same Macro revision"):
        project(doc, ["/macro.html"])


@pytest.mark.parametrize("path", ["macro.html", "//evil.test/a.html", "/a/../b.html",
                                  "/a/./b.html", "/a\\b.html", "/macro.html?x=1",
                                  "/macro.html#x", "/a b.html", "/a\x00b.html"])
def test_concrete_inventory_is_a_normalized_path(path):
    assert not normalized_path(path)


def test_directory_names_come_from_the_existing_bilingual_navigation():
    source = """<a href="{{ nav_prefix }}macro.html">{{ t('Market &amp; economy', '市场与经济') }}</a>
                <a href="https://other.test/a.html">{{ t('Other', '其他') }}</a>"""
    labels = navigation_labels([source])
    assert labels == {"/macro.html": {"en": "Market & economy", "zh": "市场与经济"}}
    p = project(catalog(row("/macro.html")), ["/macro.html"], labels=labels)
    assert p["directory"][0]["title"] == labels["/macro.html"]


def test_document_heading_keeps_existing_bilingual_title_and_moved_identity():
    assert document_heading_label("<h1>{{ t('Narrative Rotation', '主题轮动') }} <span>{{ t(d.market_en, d.market_zh) }}</span></h1>") == {
        "en": "Narrative Rotation", "zh": "主题轮动"}
    assert document_heading_label("<h1>China Thematic Baskets now live in China Sector Intelligence · A股主题篮子已并入中国行业情报</h1>") == {
        "en": "China Thematic Baskets now live in China Sector Intelligence",
        "zh": "A股主题篮子已并入中国行业情报"}
    with pytest.raises(ValueError, match="not bilingual"):
        document_heading_label("<h1>Baskets China</h1>")


def test_recursive_members_match_canonical_directory_family_without_runtime_wildcards():
    doc = catalog(row("/stocks/<id>.html", kind="family"),
                  row("/learn/<id>.html", kind="family"))
    paths = ["/stocks/earnings/a-2026q2-call-record.html", "/learn/options/gamma.html"]
    assert project(doc, paths)["legacyPaths"] == sorted(paths)


def test_fragment_payloads_are_accounted_for_without_becoming_page_routes():
    doc = catalog(row("/macro/<id>.html", kind="family"))
    p = derive_projection(doc, ["/macro/fragments/credit.html"], {"exact": set(), "prefixes": ()},
                          {}, registry_digest="digest", inventory_ref=PIN, document_paths=set())
    assert p["legacyPaths"] == []
    assert p["coverage"]["excluded"] == [{"path": "/macro/fragments/credit.html", "reason": "html_fragment"}]
    assert is_html_document(b"<!doctype html><html><head>")
    assert is_html_document(b"<!-- comment --><html lang='en'>")
    assert not is_html_document(b"<script>const sample='<html><head>';</script><section>credit</section>")
    assert not is_html_document(b"<!-- <html> --> <div>payload</div>")


def test_canonical_internal_research_tools_never_enter_the_public_directory():
    from scripts import build_product_page_registry as registry_owner

    policy = registry_owner._load_site_access(Path(__file__).resolve().parents[1] / "config/site_access.yml")
    paths = ["/committee.html", "/measurement.html", "/crossasset.html",
             "/signal_lab.html", "/tech_lab.html", "/macro_signals.html", "/factors.html"]
    assert set(paths) <= policy["deny"]["exact"]
    result = project(catalog(*(row(path) for path in paths)), paths, policy["deny"])
    assert result["legacyPaths"] == []
    assert result["directory"] == []
    assert {item["reason"] for item in result["coverage"]["excluded"]} == {"serving_policy_denied"}


# ---------------------------------------------------------------------------
# Opt-in cross-revision inventory binding: the CLI boundary is what is proven,
# against a real temporary Macro repo, never a copied predicate.
# ---------------------------------------------------------------------------

from scripts import build_product_page_registry as registry_owner  # noqa: E402

REGISTRY_PATH_IN_REPO = "data/product_experience/page_registry.json"
FIXTURE_TEMPLATES = ("templates/_navlinks.html.j2", "templates/_public_nav.html.j2",
                     "templates/_public_footer.html.j2")
FIXTURE_NAV = "<a href=\"{{ nav_prefix }}macro.html\">{{ t('Macro & economy', 'Macro economy (zh)') }}</a>\n"
FIXTURE_DOCUMENT = ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
                    "<title>{stem}</title></head><body><h1>{stem}</h1></body></html>")
FIXTURE_GIT_ENV = {
    "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
    "GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.test",
    "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.test",
    "GIT_AUTHOR_DATE": "2026-10-22T00:00:00Z", "GIT_COMMITTER_DATE": "2026-10-22T00:00:00Z",
}


def fixture_registry_row(route, *, kind="page", page_id=None):
    """A registry row in full canonical field order, valid under the schema."""
    return {
        "page_id": page_id or "macro:" + route, "repo": "macro", "route": route,
        "route_kind": kind, "source_template": "site" + route, "builder": [],
        "data_sources": [], "access_shell": "anonymous", "payload_tier": "public",
        "nav_family": "public_nav.public", "archetype": "unclassified",
        "design_system": {"compliant": False},
        "primary_user_question": "How does this surface help?", "owner": "unknown",
        "lifecycle": "live", "priority": "unclassified", "generated": True,
        "bilingual": True, "themes": [], "locales": [], "known_contracts": [],
        "open_prs": [], "source_evidence": ["fixture:site" + route], "notes": [],
    }


def _git(repo, *args):
    done = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True,
                          env=dict(os.environ, **FIXTURE_GIT_ENV))
    assert done.returncode == 0, done.stderr
    return done.stdout


def _write(repo, rel, text):
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _commit(repo, message):
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "--allow-empty", "-m", message)
    return _git(repo, "rev-parse", "HEAD").strip()


def _blob(repo, ref, path):
    done = subprocess.run(["git", "show", ref + ":" + path], cwd=repo,
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    return done.stdout


def _tracked_html(repo, ref):
    files = _git(repo, "ls-tree", "-r", "--name-only", ref, "--", "site")
    return ["/" + f.removeprefix("site/") for f in files.splitlines()
            if f.startswith("site/") and f.endswith(".html")]


@pytest.fixture()
def inventory_fixture(tmp_path):
    """One real Macro fixture repo shared by the binding tests.

    Protected origin/main carries a later HTML inventory over the registry's
    own pin: C1 (registry Macro pin) -> C2 (registry committed) -> C3 (registry
    deleted) -> C4 (registry bytes changed) -> C5 (exact registry restored plus
    a stock-family104 member and an unregistered expectation_surface). A side
    commit off C1 never lands on origin/main.
    """
    repo = tmp_path / "macro-fixture"
    repo.mkdir()
    _git(repo, "init", "--quiet")
    default_branch = _git(repo, "symbolic-ref", "--short", "HEAD").strip()
    root = _commit(repo, "root")
    for rel, text in [
        ("config/site_access.yml", "deny:\n  exact: []\n  prefixes: []\n"),
        ("templates/_navlinks.html.j2", FIXTURE_NAV),
        ("templates/_public_nav.html.j2", ""),
        ("templates/_public_footer.html.j2", ""),
        ("templates/allocation.html.j2", "<h1>{{ t('Allocation', 'Allocation (zh)') }}</h1>\n"),
        ("templates/baskets_china.html.j2", "<h1>{{ t('China baskets', 'China baskets (zh)') }}</h1>\n"),
        ("site/macro.html", FIXTURE_DOCUMENT.format(stem="macro")),
        ("site/stocks/Alpha.html", FIXTURE_DOCUMENT.format(stem="Alpha")),
    ]:
        _write(repo, rel, text)
    pin = _commit(repo, "inventory base")
    registry = {
        "schema": registry_owner.SCHEMA, "generated_at": "2026-10-22T00:00:00Z",
        "sources": {"macro": {"sha": pin}, "terminal": {"sha": "b" * 40},
                    "mastermind": {"sha": "c" * 40}},
        "pages": [fixture_registry_row("/macro.html"),
                  fixture_registry_row("/stocks/<id>.html", kind="family",
                                       page_id="macro:stocks_family")],
    }
    registry_bytes = (json.dumps(registry, ensure_ascii=False, indent=2) + "\n").encode()
    caller_registry = tmp_path / "caller-registry.json"
    caller_registry.write_bytes(registry_bytes)
    _write(repo, REGISTRY_PATH_IN_REPO, registry_bytes.decode())
    _commit(repo, "registry committed")
    (repo / REGISTRY_PATH_IN_REPO).unlink()
    missing = _commit(repo, "registry deleted")
    _write(repo, REGISTRY_PATH_IN_REPO, registry_bytes.decode() + "\n")
    changed = _commit(repo, "registry bytes changed")
    _write(repo, REGISTRY_PATH_IN_REPO, registry_bytes.decode())
    for n in range(104):
        _write(repo, f"site/stocks/earnings/member-{n:03}.html",
               FIXTURE_DOCUMENT.format(stem=f"member-{n:03}"))
    _write(repo, "site/expectation_surface.html", FIXTURE_DOCUMENT.format(stem="expectation_surface"))
    tip = _commit(repo, "stock-family104 and unregistered expectation_surface")
    _git(repo, "update-ref", "refs/remotes/origin/main", tip)
    _git(repo, "checkout", "--quiet", "-b", "side", pin)
    _write(repo, "scratch/unprotected.txt", "never reaches origin/main\n")
    side = _commit(repo, "unprotected side commit")
    _git(repo, "checkout", "--quiet", default_branch)
    return SimpleNamespace(repo=repo, git_dir=repo / ".git", root=root, pin=pin,
                           missing=missing, changed=changed, tip=tip, side=side,
                           registry=registry, registry_bytes=registry_bytes,
                           registry_path=caller_registry)


def run_exporter(tmp_path, fx, *flags, registry=None):
    """Drive the canonical CLI as a subprocess with git aimed at the fixture."""
    output = tmp_path / "projection.json"
    done = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "export_shared_shell_routes.py"),
         "--registry", str(registry or fx.registry_path), "--output", str(output), *flags],
        capture_output=True, text=True, env=dict(os.environ, GIT_DIR=str(fx.git_dir)))
    return done, output


def expected_projection(fx, ref):
    """The pure projection for a revision, mirroring the canonical gathering."""
    policy = registry_owner._load_site_access(fx.repo / "config/site_access.yml")["deny"]
    labels = navigation_labels([_blob(fx.repo, ref, name) for name in FIXTURE_TEMPLATES])
    for path in ("allocation", "baskets_china"):
        labels.setdefault("/" + path + ".html", document_heading_label(
            _blob(fx.repo, ref, "templates/" + path + ".html.j2")))
    paths = _tracked_html(fx.repo, ref)
    return derive_projection(fx.registry, paths, policy, labels,
                             registry_digest=hashlib.sha256(fx.registry_bytes).hexdigest(),
                             inventory_ref=fx.pin,
                             document_paths=document_inventory(fx.repo, ref, paths))


def test_default_cli_output_is_unchanged_without_inventory(tmp_path, inventory_fixture):
    fx = inventory_fixture
    done, output = run_exporter(tmp_path, fx)
    assert done.returncode == 0, done.stderr
    default = json.loads(output.read_text())
    # The default run is exactly the pure projection at the registry's own pin:
    # identical sources, routes and coverage, and no inventory provenance key.
    assert default == expected_projection(fx, fx.pin)
    assert list(default["sources"]) == ["registrySha256", "macro", "terminal", "mastermind"]
    assert output.read_text() == json.dumps(default, ensure_ascii=False, indent=2) + "\n"


def test_opt_in_inventory_binds_exact_registry_and_enumerates_that_revision(
        tmp_path, inventory_fixture):
    fx = inventory_fixture
    done, output = run_exporter(tmp_path, fx, "--inventory-ref", fx.tip)
    assert done.returncode == 0, done.stderr
    doc = json.loads(output.read_text())
    expected = expected_projection(fx, fx.tip)
    expected["sources"]["inventory"] = fx.tip
    assert doc == expected
    # Provenance: the registry's own pins survive; sources.macro is not relabeled.
    assert list(doc["sources"]) == ["registrySha256", "macro", "terminal",
                                    "mastermind", "inventory"]
    assert doc["sources"]["registrySha256"] == hashlib.sha256(fx.registry_bytes).hexdigest()
    assert doc["sources"]["macro"] == fx.pin
    assert doc["sources"]["inventory"] == fx.tip
    assert doc["sources"]["terminal"] == "b" * 40
    assert doc["sources"]["mastermind"] == "c" * 40
    # Enumeration followed the inventory ref, not the registry's historical pin.
    assert "/stocks/earnings/member-000.html" in doc["legacyPaths"]
    assert "/stocks/earnings/member-000.html" not in expected_projection(fx, fx.pin)["legacyPaths"]


def test_stock_family_additions_admit_members_while_unregistered_surfaces_stay_excluded(
        tmp_path, inventory_fixture):
    fx = inventory_fixture
    done, output = run_exporter(tmp_path, fx, "--inventory-ref", fx.tip)
    assert done.returncode == 0, done.stderr
    doc = json.loads(output.read_text())
    added = set(doc["legacyPaths"]) - set(expected_projection(fx, fx.pin)["legacyPaths"])
    assert added == {f"/stocks/earnings/member-{n:03}.html" for n in range(104)}
    assert {"path": "/expectation_surface.html",
            "reason": "unregistered"} in doc["coverage"]["excluded"]
    default = expected_projection(fx, fx.pin)
    # Family members and excluded surfaces never move the directory or natives.
    assert doc["directory"] == default["directory"]
    assert doc["nativePaths"] == default["nativePaths"] == []
    assert [entry["href"] for entry in doc["directory"]] == ["/macro.html"]


@pytest.mark.parametrize("candidate", ["tuesday", "A" * 40, "a" * 39, "b" * 40])
def test_inventory_refuses_malformed_or_unknown_refs_before_output(
        tmp_path, inventory_fixture, candidate):
    fx = inventory_fixture
    done, output = run_exporter(tmp_path, fx, "--inventory-ref", candidate)
    assert done.returncode != 0
    assert "inventory must be" in done.stderr and "commit" in done.stderr
    assert not output.exists()


def test_inventory_outside_protected_origin_main_is_refused_before_output(
        tmp_path, inventory_fixture):
    fx = inventory_fixture
    done, output = run_exporter(tmp_path, fx, "--inventory-ref", fx.side)
    assert done.returncode != 0
    assert "not contained in protected origin/main" in done.stderr
    assert not output.exists()


def test_inventory_revision_without_committed_registry_is_refused_before_output(
        tmp_path, inventory_fixture):
    fx = inventory_fixture
    done, output = run_exporter(tmp_path, fx, "--inventory-ref", fx.root)
    assert done.returncode != 0
    assert "registry blob is missing at the inventory ref" in done.stderr
    assert not output.exists()


def test_inventory_missing_registry_blob_is_refused_before_output(
        tmp_path, inventory_fixture):
    fx = inventory_fixture
    done, output = run_exporter(tmp_path, fx, "--inventory-ref", fx.missing)
    assert done.returncode != 0
    assert "registry blob is missing at the inventory ref" in done.stderr
    assert not output.exists()


def test_inventory_with_changed_registry_bytes_is_refused_before_output(
        tmp_path, inventory_fixture):
    fx = inventory_fixture
    done, output = run_exporter(tmp_path, fx, "--inventory-ref", fx.changed)
    assert done.returncode != 0
    assert "differ from the canonical registry" in done.stderr
    assert not output.exists()


def test_inventory_without_a_registry_macro_pin_is_refused_before_output(
        tmp_path, inventory_fixture):
    fx = inventory_fixture
    broken = json.loads(fx.registry_bytes)
    del broken["sources"]["macro"]
    registry = tmp_path / "caller-registry.json"
    registry.write_bytes((json.dumps(broken, ensure_ascii=False, indent=2) + "\n").encode())
    done, output = run_exporter(tmp_path, fx, "--inventory-ref", fx.tip, registry=registry)
    assert done.returncode != 0
    assert "Macro source must be an immutable commit" in done.stderr
    assert not output.exists()


def test_bound_committed_registry_keeps_nonancestor_source_pin(tmp_path, inventory_fixture):
    fx = inventory_fixture
    historical = copy.deepcopy(fx.registry)
    historical["sources"]["macro"]["sha"] = fx.side
    raw = (json.dumps(historical, ensure_ascii=False, indent=2) + "\n").encode()
    _write(fx.repo, REGISTRY_PATH_IN_REPO, raw.decode())
    tip = _commit(fx.repo, "committed registry retains historical nonancestor source pin")
    _git(fx.repo, "update-ref", "refs/remotes/origin/main", tip)
    fx.registry_path.write_bytes(raw)
    done, output = run_exporter(tmp_path, fx, "--inventory-ref", tip)
    assert done.returncode == 0, done.stderr
    doc = json.loads(output.read_text())
    assert doc["sources"]["macro"] == fx.side
    assert doc["sources"]["inventory"] == tip
    assert doc["sources"]["registrySha256"] == hashlib.sha256(raw).hexdigest()


def test_inventory_tag_object_is_refused_before_output(tmp_path, inventory_fixture):
    fx = inventory_fixture
    _git(fx.repo, "tag", "-a", "inventory-label", "-m", "immutable tag object", fx.tip)
    tag_object = _git(fx.repo, "rev-parse", "inventory-label").strip()
    done, output = run_exporter(tmp_path, fx, "--inventory-ref", tag_object)
    assert done.returncode != 0
    assert "must identify a commit directly" in done.stderr
    assert not output.exists()
