"""International destination must contain its risk-desk grid on narrow screens."""
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import urlsplit

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Render-sync externalizes the template's inline CSS into content-addressed
# local assets: "assets/css/<8 lowercase hex>.css", optionally cache-busted with
# "?v=<same hex>". The hex is the SHA-256 prefix of the asset's raw bytes.
CANONICAL_ASSET = re.compile(r"^assets/css/(?P<digest>[0-9a-f]{8})\.css$")


class _PublishedStyles(HTMLParser):
    """Collect a page's own inline <style> text and its stylesheet <link> hrefs."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.inline_css = []
        self.stylesheet_hrefs = []
        self._in_style = False

    def handle_starttag(self, tag, attrs):
        if tag == "style":
            self._in_style = True
        elif tag == "link":
            attributes = {key.lower(): (value or "") for key, value in attrs}
            if "stylesheet" in attributes.get("rel", "").lower().split():
                href = attributes.get("href", "").strip()
                if href:
                    self.stylesheet_hrefs.append(href)

    def handle_endtag(self, tag):
        if tag == "style":
            self._in_style = False

    def handle_data(self, data):
        if self._in_style:
            self.inline_css.append(data)

    def handle_entityref(self, name):
        if self._in_style:
            self.inline_css.append("&" + name + ";")

    def handle_charref(self, name):
        if self._in_style:
            self.inline_css.append("&#" + name + ";")


def _is_asset_css_path(path):
    """True when a link path points into the page-owned externalizer's directory."""
    segments = path.split("/")
    return any(segments[i] == "assets" and segments[i + 1] == "css" for i in range(len(segments) - 1))


def _canonical_digest(href):
    """Return the content address of a canonical local stylesheet link.

    Returns None for stylesheets this page does not own (theme, shared shell,
    CDN). A link that points into assets/css/ but is not canonical is a
    publication defect, so it is reported instead of being silently skipped.
    """
    parts = urlsplit(href)
    path = parts.path
    if not _is_asset_css_path(path):
        return None
    match = CANONICAL_ASSET.match(path)
    digest = None
    if match and not parts.scheme and not parts.netloc and not parts.fragment:
        digest = match.group("digest")
        if parts.query and parts.query != "v=" + digest:
            digest = None
    if digest is None:
        raise AssertionError("Malformed local stylesheet candidate: %r" % (href,))
    return digest


def _read_canonical_asset(site, digest):
    """Read a published stylesheet asset after proving it is the one that was published."""
    asset = site.joinpath("assets", "css", digest + ".css")
    if asset.is_symlink():
        raise AssertionError("Published stylesheet asset must not be a symlink: %s" % asset)
    try:
        resolved = asset.resolve(strict=True)
    except OSError:
        raise AssertionError("Published stylesheet asset is missing: %s" % asset)
    try:
        resolved.relative_to(site.resolve())
    except ValueError:
        raise AssertionError("Published stylesheet asset escapes the site root: %s" % asset)
    raw = asset.read_bytes()
    if not sha256(raw).hexdigest().startswith(digest):
        raise AssertionError("Published stylesheet asset %s does not match its content address" % digest)
    return raw.decode("utf-8")


def _published_mobile_css(site, html):
    """Return the CSS the published page actually serves.

    Only two sources count: the page's own inline <style> blocks and the
    content-addressed assets it links locally. The template and the global
    theme stylesheets are never consulted.
    """
    parser = _PublishedStyles()
    parser.feed(html)
    parser.close()
    chunks = ["\n".join(parser.inline_css)]
    seen = set()
    for href in parser.stylesheet_hrefs:
        digest = _canonical_digest(href)
        if digest is None or digest in seen:
            continue
        seen.add(digest)
        chunks.append(_read_canonical_asset(site, digest))
    return "\n".join(chunks)


def _assert_mobile_containment(css):
    """Assert the international page's narrow-screen containment and wrapping rules."""
    rule = re.search(r"body\.page-intl \.ird-twocol\s*>\s*\*\s*\{([^}]+)\}", css)
    assert rule, "International grid children retain an overflowing automatic minimum"
    assert re.search(r"min-width\s*:\s*0\s*[;}]", rule.group(1) + "}"), rule.group(1)
    assert "overflow" not in rule.group(1), "Contain the grid; do not hide dashboard content"

    assert re.search(
        r"body\.page-intl \.te-strip\s*\{\s*grid-template-columns\s*:\s*minmax\(0,\s*1fr\)", css
    ), "The inherited 340px event minimum overflows a 320px viewport"

    for selector in ("body.page-intl .seg", "body.page-intl .ird-tx-row"):
        assert re.search(re.escape(selector) + r"\s*\{[^}]*flex-wrap\s*:\s*wrap", css), selector
    assert re.search(r"body\.page-intl \.rf-s\s*\{[^}]*overflow-wrap\s*:\s*anywhere", css)


def test_international_desk_children_can_shrink_without_clipping_the_page():
    css = (ROOT / "templates/intl.html.j2").read_text()
    rule = re.search(r"body\.page-intl \.ird-twocol\s*>\s*\*\s*\{([^}]+)\}", css)
    assert rule, "International grid children retain an overflowing automatic minimum"
    assert re.search(r"min-width\s*:\s*0\s*[;}]", rule.group(1) + "}"), rule.group(1)
    assert "overflow" not in rule.group(1), "Contain the grid; do not hide dashboard content"


def test_international_mobile_events_use_a_shrinkable_track():
    css = (ROOT / "templates/intl.html.j2").read_text()
    assert re.search(r"body\.page-intl \.te-strip\s*\{\s*grid-template-columns\s*:\s*minmax\(0,\s*1fr\)", css), (
        "The inherited 340px event minimum overflows a 320px viewport"
    )


def test_international_mobile_controls_and_risk_labels_can_wrap():
    css = (ROOT / "templates/intl.html.j2").read_text()
    for selector in ("body.page-intl .seg", "body.page-intl .ird-tx-row"):
        assert re.search(re.escape(selector) + r"\s*\{[^}]*flex-wrap\s*:\s*wrap", css), selector
    assert re.search(r"body\.page-intl \.rf-s\s*\{[^}]*overflow-wrap\s*:\s*anywhere", css)


def test_committed_international_projection_carries_mobile_containment():
    site = ROOT / "site"
    html = (site / "intl.html").read_text(encoding="utf-8")
    _assert_mobile_containment(_published_mobile_css(site, html))


_MOBILE_RULES = """
body.page-intl .ird-twocol > * {min-width:0;}
body.page-intl .te-strip {grid-template-columns:minmax(0,1fr);}
body.page-intl .seg {flex-wrap:wrap;}
body.page-intl .ird-tx-row {flex-wrap:wrap;}
body.page-intl .rf-s {overflow-wrap:anywhere;}
"""


def _published_fixture(site, css=_MOBILE_RULES):
    digest = sha256(css.encode()).hexdigest()[:8]
    asset = site / 'assets' / 'css' / (digest + '.css')
    asset.parent.mkdir(parents=True, exist_ok=True)
    asset.write_text(css)
    return asset, "<link href='assets/css/" + digest + ".css?v=" + digest + "' rel='stylesheet'>"


def test_publication_guard_accepts_actual_inline_and_externalized_rules(tmp_path):
    _assert_mobile_containment(_published_mobile_css(tmp_path, '<style>' + _MOBILE_RULES + '</style>'))
    _, html = _published_fixture(tmp_path)
    _assert_mobile_containment(_published_mobile_css(tmp_path, html))


def test_publication_guard_rejects_missing_or_changed_linked_asset(tmp_path):
    asset, html = _published_fixture(tmp_path)
    asset.unlink()
    with pytest.raises(AssertionError, match='missing'):
        _published_mobile_css(tmp_path, html)
    asset.write_text(_MOBILE_RULES + '\n/* changed */')
    with pytest.raises(AssertionError, match='content address'):
        _published_mobile_css(tmp_path, html)


@pytest.mark.parametrize('missing', [
    'min-width:0;', 'grid-template-columns:minmax(0,1fr);', 'flex-wrap:wrap;', 'overflow-wrap:anywhere;',
])
def test_correctly_hashed_publication_still_needs_each_mobile_rule(tmp_path, missing):
    _, html = _published_fixture(tmp_path, _MOBILE_RULES.replace(missing, '', 1))
    # Existing valid template rules cannot substitute for missing published CSS.
    with pytest.raises(AssertionError):
        _assert_mobile_containment(_published_mobile_css(tmp_path, html))


@pytest.mark.parametrize('href', [
    'https://example.test/assets/css/01234567.css', '/assets/css/01234567.css',
    '../assets/css/01234567.css', 'assets/css/../../01234567.css',
    'assets/css/01234567.css?v=76543210', 'assets/css/01234567.css#other',
])
def test_noncanonical_externalizer_candidate_is_rejected_before_read(tmp_path, monkeypatch, href):
    def unexpected_read(path):
        pytest.fail('Malformed publication candidate caused a filesystem read: ' + str(path))
    monkeypatch.setattr(Path, 'read_bytes', unexpected_read)
    with pytest.raises(AssertionError, match='Malformed'):
        _published_mobile_css(tmp_path, '<link rel="stylesheet" href="' + href + '">')


def test_publication_guard_refuses_symlinked_asset(tmp_path):
    asset, html = _published_fixture(tmp_path)
    original = asset.read_bytes(); asset.unlink()
    target = tmp_path / 'other.css'; target.write_bytes(original); asset.symlink_to(target)
    with pytest.raises(AssertionError, match='symlink'):
        _published_mobile_css(tmp_path, html)
