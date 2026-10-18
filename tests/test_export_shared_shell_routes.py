"""Finite route projection: prove access/coverage boundaries, not implementation spelling."""
import copy

import pytest

from scripts.export_shared_shell_routes import derive_projection, is_html_document, navigation_labels, normalized_path

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
