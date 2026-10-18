"""Critical HTML compatibility checks: placement, depth, fragments and upgrades."""
import pytest

from lib.shared_shell import DOCUMENT_VERSION, inject_shared_shell_text


def render(text, prefix="", version="a1b2c3d4"):
    return inject_shared_shell_text(text, prefix, version=version)


def test_bridge_runs_before_all_existing_page_scripts():
    source = '<!doctype html><html><head><meta charset="utf-8"><script>history.pushState({}, "", "?a=1")</script></head><body><h1>Data</h1></body></html>'
    result = render(source)
    assert result.index("shared_shell_bridge.js") < result.index("history.pushState")
    assert '<script data-sync ' in result
    assert '<meta name="mmx-shell-document" content="' + DOCUMENT_VERSION + '">' in result
    assert result.endswith(source[source.index('<meta charset'):])
    assert render(result) == result


def test_depth_and_content_version_update_without_changing_content():
    source = '<!DOCTYPE html>\n<HTML lang="zh">\n<HEAD data-x="a">\n<title>原始页面</title></HEAD><body>company</body></HTML>'
    first = render(source, "../../")
    assert 'src="../../shared_shell_bridge.js?v=a1b2c3d4"' in first
    second = render(first, "../../", "12345678")
    assert second.count("shared_shell_bridge.js") == 1
    assert "a1b2c3d4" not in second
    assert second.replace("12345678", "a1b2c3d4") == first
    assert render(second, "../../", "12345678") == second


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
