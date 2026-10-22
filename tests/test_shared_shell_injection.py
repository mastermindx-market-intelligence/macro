"""Critical HTML compatibility checks: placement, depth, fragments and upgrades."""
import hashlib
import re

import pytest

from lib.shared_shell import DOCUMENT_VERSION, inject_shared_shell_text


def render(text, prefix="", version="a1b2c3d4", css_version="eeff0011"):
    return inject_shared_shell_text(text, prefix, version=version, css_version=css_version)


def test_bridge_runs_before_all_existing_page_scripts():
    source = '<!doctype html><html><head><meta charset="utf-8"><script>history.pushState({}, "", "?a=1")</script></head><body><h1>Data</h1></body></html>'
    result = render(source)
    assert result.index('rel="stylesheet"') < result.index("shared_shell_bridge.js")
    assert result.index("shared_shell_bridge.js") < result.index("history.pushState")
    assert '<script data-sync ' in result
    assert '<meta name="mmx-shell-document" content="' + DOCUMENT_VERSION + '">' in result
    assert result.endswith(source[source.index('<meta charset'):])
    assert render(result) == result


def test_depth_and_content_version_update_without_changing_content():
    source = '<!DOCTYPE html>\n<HTML lang="zh">\n<HEAD data-x="a">\n<title>原始页面</title></HEAD><body>company</body></HTML>'
    first = render(source, "../../")
    assert 'src="../../shared_shell_bridge.js?v=a1b2c3d4"' in first
    assert 'href="../../shared_shell.css?v=eeff0011"' in first
    second = render(first, "../../", "12345678")
    assert second.count("shared_shell_bridge.js") == 1
    assert "a1b2c3d4" not in second
    assert second.replace("12345678", "a1b2c3d4") == first
    assert render(second, "../../", "12345678") == second


def test_stylesheet_digest_is_independent_and_the_old_owned_block_upgrades_in_place():
    source = ('<html><head><!-- mmx-shared-shell:start -->'
              '<meta name="mmx-shell-document" content="20261018.1">'
              '<meta name="mmx-shell-response" content="content">'
              '<script data-sync data-mmx-shared-shell-bridge="20261018.1" '
              'src="shared_shell_bridge.js?v=a1b2c3d4"></script>'
              '<!-- mmx-shared-shell:end --><title>Original</title></head><body>Body</body></html>')
    first = render(source)
    second = render(first, css_version="aabbccdd")
    assert second == first.replace("eeff0011", "aabbccdd")
    assert second.count("shared_shell.css") == second.count("shared_shell_bridge.js") == 1
    assert second.count("<!-- mmx-shared-shell:start -->") == 1
    assert '<title>Original</title></head><body>Body</body></html>' in second
    assert render(second, css_version="aabbccdd") == second


@pytest.mark.parametrize("version", ["latest", "a" * 40, "", 'abc" onload="x'])
def test_stylesheet_digest_shape_is_required(version):
    with pytest.raises(ValueError, match="stylesheet version"):
        render("<html><head></head></html>", css_version=version)


def test_both_assets_publish_through_the_canonical_copy_owner_with_independent_digests(tmp_path, monkeypatch):
    from lib import shared_shell as owner

    templates = tmp_path / "templates"
    templates.mkdir()
    site = tmp_path / "site"
    site.mkdir()
    for name, text in ((owner.ASSET_NAME, "// bridge\n"), (owner.STYLESHEET_NAME, "html { --proof: 1; }\n")):
        (templates / name).write_text(text)
        (site / name).write_text("old bytes\n")
    monkeypatch.setattr(owner, "ROOT", tmp_path)
    old_js, old_css = owner.asset_version(site), owner.stylesheet_version(site)
    owner.copy_shared_shell_asset(site)
    js_version, css_version = owner.asset_version(site), owner.stylesheet_version(site)
    for name, version in ((owner.ASSET_NAME, js_version), (owner.STYLESHEET_NAME, css_version)):
        assert (site / name).read_bytes() == (templates / name).read_bytes()
        assert version == hashlib.sha256((site / name).read_bytes()).hexdigest()[:8]
    assert js_version != old_js and css_version != old_css
    (templates / owner.STYLESHEET_NAME).write_text("html { --proof: 2; }\n")
    owner.copy_shared_shell_asset(site)
    assert owner.asset_version(site) == js_version
    assert owner.stylesheet_version(site) != css_version


def test_about_public_nav_css_publishes_and_restamps_only_the_owned_block(tmp_path):
    from lib import shared_shell as owner

    source = (owner.ROOT / "templates" / "about.html").read_text(encoding="utf-8")
    # This global marketing component is separate from the page's own landmarks.
    assert re.search(r'<body>\s*<nav class="nav" aria-label="Main">', source)
    assert '<nav class="ab-crumb" aria-label="Breadcrumb">' in source
    assert '<main class="ab-main">' in source
    assert '<header class="ab-sec ab-mast">' in source

    owner.copy_shared_shell_asset(tmp_path)
    css = (tmp_path / owner.STYLESHEET_NAME).read_bytes()
    assert css == (owner.ROOT / "templates" / owner.STYLESHEET_NAME).read_bytes()
    assert b'html[data-mmx-shared-shell="1"] body > nav.nav[aria-label="Main"],' in css
    js_version, css_version = owner.asset_version(tmp_path), owner.stylesheet_version(tmp_path)
    assert css_version == hashlib.sha256(css).hexdigest()[:8]
    prior = inject_shared_shell_text(source, version=js_version, css_version="00000000")
    result = inject_shared_shell_text(prior, site_dir=tmp_path)
    assert result == prior.replace('href="shared_shell.css?v=00000000"',
                                   'href="shared_shell.css?v=' + css_version + '"')
    assert owner.BLOCK.sub("", result, count=1) == owner.BLOCK.sub("", source, count=1)
    assert result.index("shared_shell.css") < result.index("shared_shell_bridge.js")
    assert inject_shared_shell_text(result, site_dir=tmp_path) == result


@pytest.mark.parametrize("missing", ["shared_shell.css", "shared_shell_bridge.js"])
def test_standalone_ensure_fills_only_the_missing_asset(tmp_path, missing):
    from lib import shared_shell as owner

    existing = owner.ASSET_NAME if missing == owner.STYLESHEET_NAME else owner.STYLESHEET_NAME
    preserved = b"existing tracked asset belongs to its publisher\n"
    (tmp_path / existing).write_bytes(preserved)
    owner.ensure_shared_shell_asset(tmp_path)
    assert (tmp_path / existing).read_bytes() == preserved
    assert (tmp_path / missing).read_bytes() == (owner.ROOT / "templates" / missing).read_bytes()


@pytest.mark.parametrize("fault", ["missing", "drift"])
def test_publication_check_refuses_absent_or_drifted_css(tmp_path, fault):
    from lib.shared_shell import copy_shared_shell_asset
    from scripts.inject_shared_shell import run

    copy_shared_shell_asset(tmp_path)
    assert run(tmp_path, check=True)["changed"] == 0
    css = tmp_path / "shared_shell.css"
    if fault == "missing":
        css.unlink()
    else:
        css.write_text("/* stale stylesheet */\n")
    with pytest.raises(ValueError, match=r"shared_shell\.css"):
        run(tmp_path, check=True)


def test_asset_optimizer_keeps_css_before_blocking_bridge_and_stamps_each_asset(tmp_path):
    from lib.pages import optimize_assets_text
    from lib.shared_shell import copy_shared_shell_asset

    copy_shared_shell_asset(tmp_path)
    source = render('<html><head><script>pageBoot()</script></head></html>')
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:8] for p in tmp_path.iterdir()}
    result = optimize_assets_text(source, hashes.get)
    assert 'href="shared_shell.css?v=' + hashes["shared_shell.css"] + '"' in result
    assert 'src="shared_shell_bridge.js?v=' + hashes["shared_shell_bridge.js"] + '"' in result
    assert result.index("shared_shell.css") < result.index("shared_shell_bridge.js") < result.index("pageBoot()")
    assert "defer" not in result and "async" not in result
    assert optimize_assets_text(result, hashes.get) == result


@pytest.mark.parametrize("source", [
    '<section><h1>Fragment</h1></section>',
    '<script>var sample = "<html><head></head></html>";</script>',
    '<!-- <html><head></head></html> --><nav>Navigation fragment</nav>',
    '{"html":"<head>"}',
])
def test_fragments_and_non_markup_head_mentions_are_untouched(source):
    assert render(source) == source


def test_implicit_html_document_is_supported():
    assert "shared_shell_bridge.js" in render('<!doctype html><head><title>Page</title></head><body>Body</body>')


@pytest.mark.parametrize("prefix", ["../assets/", "https://example.test/", "../\" bad", "a/../"])
def test_asset_prefix_is_never_an_external_or_injected_url(prefix):
    with pytest.raises(ValueError):
        render('<html><head></head><body></body></html>', prefix)


@pytest.mark.parametrize("version", ["latest", "a" * 40, "", "abc\" onload=\"x"])
def test_content_digest_shape_is_required(version):
    with pytest.raises(ValueError):
        render('<html><head></head><body></body></html>', version=version)


@pytest.mark.parametrize("source", [
    '<html><head><!-- mmx-shared-shell:start --></head></html>',
    '<html><head><meta name="mmx-shell-document" content="unknown"></head></html>',
    '<html><head><!-- mmx-shared-shell:end --><!-- mmx-shared-shell:start --></head></html>',
])
def test_ambiguous_or_unowned_capability_markers_stop_the_bake(source):
    with pytest.raises(ValueError):
        render(source)


def test_existing_head_whitespace_is_preserved_on_repeated_writes():
    source = "<html><head>\n\n<title>Title</title></head><body>Body</body></html>"
    first = render(source)
    assert render(first) == first
    assert "\n\n<title>" in first


def test_response_classification_comes_from_the_document_producer():
    source = "<html><head></head><body>Product</body></html>"
    product = render(source)
    assert '<meta name="mmx-shell-response" content="content">' in product
    gate = inject_shared_shell_text(product, "/", version="a1b2c3d4", response_kind="coming_soon")
    assert '<meta name="mmx-shell-response" content="coming_soon">' in gate
    assert 'src="/shared_shell_bridge.js?v=a1b2c3d4"' in gate
    assert 'content="content"' not in gate
    assert inject_shared_shell_text(gate, "/", version="a1b2c3d4", response_kind="coming_soon") == gate


def test_missing_or_unknown_response_ownership_is_not_invented():
    with pytest.raises(ValueError):
        inject_shared_shell_text("<html><head></head></html>", version="a1b2c3d4", response_kind="approved")
    with pytest.raises(ValueError):
        render('<html><head><meta name="mmx-shell-response" content="content"></head></html>')


def test_region_gate_marks_the_body_actually_returned(monkeypatch):
    from app import gate
    monkeypatch.setattr(gate, "_load_page", lambda: "<html><head><title>Region gate</title></head><body>Restricted</body></html>")
    result = gate.coming_soon_page()
    assert '<meta name="mmx-shell-response" content="coming_soon">' in result
    assert 'src="/shared_shell_bridge.js?v=' in result
    assert "<body>Restricted</body>" in result
