"""GMI explorer presentation-foundation assets (lane ORCH-UI-W1A, 2026-10-22).

Pins the port of the frozen specimen (mockups/refs/gmi_explorer, SPECS.md) into
production assets:

- templates/theme.css carries ONE additive GMI token block at the very end of the
  file: SPECS §5 section B verbatim plus the port-round token table (dark values in
  a second ``:root``, the three light overrides in a second ``html[data-theme="light"]``).
- templates/gmi.css is specimen sections C..O with only the production-law rewrites:
  section-A primitive values as ``var()`` fallbacks, colour/radius/custom-property
  literals swapped for the theme tokens, and ``:is()`` wraps where the checker's
  custom-property regex would otherwise misread a BEM selector as a declaration.
- templates/gmi.js carries the specimen behaviours (lens, tabs, jump nav, index
  collapse, aria/placeholder language swap) and the SPECS §10 state enum.

Pure file tests: no network, no rendering, well under 5 s.  Tests that read
``mockups/`` (specimen + SPECS) or the paired ``site/`` copies are marked
``needs_full_checkout`` — those directories are omitted from a sparse tree.
"""
import re
from pathlib import Path

import pytest

from scripts.check_design_system import ADDED_BLOCKING_RULES, scan_text

ROOT = Path(__file__).resolve().parents[1]

THEME = (ROOT / "templates/theme.css").read_text(encoding="utf-8")
GMI_CSS = (ROOT / "templates/gmi.css").read_text(encoding="utf-8")
GMI_JS = (ROOT / "templates/gmi.js").read_text(encoding="utf-8")

OPEN_MARK = (
    "/* ===== GMI explorer extension (SPECS §5; additive; consumed only by gmi.css) ===== */"
)
CLOSE_MARK = "/* ===== end GMI explorer extension ===== */"
BLOCK = THEME.split(OPEN_MARK, 1)[1].split(CLOSE_MARK, 1)[0]


def _norm(s: str) -> str:
    return " ".join(s.split())


def _read_mockups(name: str) -> str:
    return (ROOT / "mockups/refs/gmi_explorer" / name).read_text(encoding="utf-8")


def _decls(block: str) -> dict:
    """name -> value for every custom-property declaration in a CSS block."""
    return {m.group(1): _norm(m.group(2))
            for m in re.finditer(r"(--[A-Za-z0-9-]+)\s*:\s*([^;]+);", block)}


def _root_blocks() -> list:
    return re.findall(r"(?<![\w-]):root\s*\{([^}]*)\}", BLOCK, re.S)


def _light_blocks() -> list:
    return re.findall(r'html\[data-theme="light"\]\s*\{([^}]*)\}', BLOCK, re.S)


# --- STEP-1 port-round token table: name -> (dark value, light value or None) ---
NEW_TOKENS = {
    "--gmi-btn-lift": ("none", "0 1px 2px rgba(20,30,50,.06)"),
    "--gmi-rail": ("color-mix(in srgb, var(--text) 10%, transparent)", None),
    "--gmi-hist-bar": ("color-mix(in srgb, var(--text) 26%, transparent)",
                       "color-mix(in srgb, var(--text) 18%, var(--panel))"),
    "--gmi-hist-glow": ("0 0 18px -6px color-mix(in srgb, var(--text) 60%, transparent)",
                        "none"),
    "--gmi-track": ("color-mix(in srgb, var(--text) 7%, transparent)", None),
    "--gmi-stack-2": ("color-mix(in srgb, var(--text) 22%, transparent)", None),
    "--gmi-ladder-1": ("color-mix(in srgb, var(--text) 48%, transparent)", None),
    "--gmi-ladder-2": ("color-mix(in srgb, var(--text) 34%, transparent)", None),
    "--gmi-ladder-3": ("color-mix(in srgb, var(--text) 22%, transparent)", None),
    "--gmi-ladder-ink-theme": ("color-mix(in srgb, var(--text) 82%, transparent)", None),
    "--gmi-ladder-ink-cat": ("color-mix(in srgb, var(--text) 62%, transparent)", None),
    "--r-gmi-focus": ("4px", None),
    "--r-gmi-xs": ("1px", None),
    "--r-gmi-sm": ("2px", None),
    "--r-gmi-md": ("3px", None),
    "--r-gmi-kbd": ("5px", None),
    "--r-gmi-tag": ("6px", None),
    "--r-gmi-dot": ("50%", None),
    "--r-gmi-bar-top": ("3px 3px 0 0", None),
    "--gmi-cell-key": ("12px", None),
    "--gmi-cell-xl": ("20px", None),
    "--gmi-cell-strip": ("6px", None),
    "--gmi-chain-slot": ("24px", None),
    "--gmi-chain-edge-none": ("0px", None),
    "--gmi-chain-rail": ("22px", None),
    "--gmi-chain-edge": ("40px", None),
    "--gmi-pip": ("12px", None),
    "--gmi-pip-anchor": ("22px", None),
    "--gmi-pip-void": ("10px", None),
    "--gmi-pip-cat": ("9px", None),
}

# Specimen section-A primitive values (gmi_explorer.css lines 16-19).
PRIMITIVE_FALLBACKS = {
    "--sp-1": "4px", "--sp-2": "8px", "--sp-3": "12px", "--sp-4": "16px",
    "--sp-5": "20px", "--sp-6": "24px", "--sp-7": "32px", "--sp-8": "44px",
    "--r-ctl": "8px", "--r-btn": "10px", "--r-card": "12px", "--r-panel": "14px",
    "--r-pill": "999px",
    "--t-fast": ".16s", "--t-med": ".2s", "--t-slow": ".55s",
    "--ease-std": "cubic-bezier(.2,0,0,1)", "--ease-lift": "cubic-bezier(.2,.7,.3,1)",
}


def test_theme_block_carries_section_b_verbatim():
    """Every --gmi-* declaration in the SPECS §5 ```css fence appears in the
    theme.css GMI block with the same whitespace-normalised value."""
    specs = _read_mockups("SPECS.md")
    section5 = specs.split("## 5.", 1)[1].split("## 6.", 1)[0]
    fence = re.search(r"```css\n(.*?)```", section5, re.S).group(1)
    fence_decls = _decls(fence)
    assert "--gmi-mark" in fence_decls and "--gmi-tray" in fence_decls
    block_decls = {}
    for block in _root_blocks() + _light_blocks():
        block_decls.update(_decls(block))
    missing = [(name, value) for name, value in fence_decls.items()
               if block_decls.get(name) != value]
    assert not missing, f"section-B declarations not carried verbatim: {missing}"


def test_theme_block_new_tokens():
    """The port-round token table is pinned exactly: dark values in the second
    :root, exactly the three listed light overrides in the second light block."""
    roots, lights = _root_blocks(), _light_blocks()
    # :root blocks in file order: section B, the §5 @media 640px cell override, tokens.
    assert len(roots) == 3, "expected section-B :root, its @media :root, and the token :root"
    assert len(lights) == 2, "expected section-B light block plus the token light block"
    token_root, token_light = _decls(roots[2]), _decls(lights[1])
    assert set(token_root) == set(NEW_TOKENS), (
        f"token :root mismatch: extra={set(token_root) - set(NEW_TOKENS)} "
        f"missing={set(NEW_TOKENS) - set(token_root)}")
    assert set(token_light) == {"--gmi-btn-lift", "--gmi-hist-bar", "--gmi-hist-glow"}
    for name, (dark, light) in NEW_TOKENS.items():
        assert token_root[name] == _norm(dark), name
        if light is None:
            assert name not in token_light, name
        else:
            assert token_light[name] == _norm(light), name


def test_theme_block_is_last_and_marked():
    """The GMI block is opened and closed exactly once and nothing follows it."""
    assert THEME.count(OPEN_MARK) == 1
    assert THEME.count(CLOSE_MARK) == 1
    assert THEME.index(OPEN_MARK) < THEME.index(CLOSE_MARK)
    assert THEME[THEME.index(CLOSE_MARK) + len(CLOSE_MARK):].strip() == ""


def test_gmi_css_design_clean():
    """scan_text reports no added-blocking finding on gmi.css, and no :root.

    The one permitted warn-tier finding is `card-class .gmi-band-card` — the
    class ships verbatim in specimen section E and the selector-parity test
    pins it; renames are not this lane's to make.
    """
    findings = scan_text("templates/gmi.css", GMI_CSS)
    blocking = [f for f in findings if f.rule in ADDED_BLOCKING_RULES]
    assert not blocking, [f.rule + " " + f.detail for f in blocking]
    assert all(f.rule == "card-class" for f in findings), [
        f"{f.rule}: {f.detail}" for f in findings if f.rule != "card-class"]
    assert ":root" not in GMI_CSS


def test_gmi_css_primitive_fallbacks():
    """Every specimen-primitive var() in gmi.css carries the section-A value."""
    pattern = re.compile(
        r"var\((--sp-[1-8]|--r-ctl|--r-btn|--r-card|--r-panel|--r-pill"
        r"|--t-fast|--t-med|--t-slow|--ease-std|--ease-lift)"
        r"\s*(?:,\s*((?:[^()]|\([^()]*\))+))?\)")  # fallback may hold one balanced (...) level
    hits = list(pattern.finditer(GMI_CSS))
    assert len(hits) >= 60, "primitive fallback sweep unexpectedly small"
    bad = [(m.group(0), PRIMITIVE_FALLBACKS[m.group(1)])
           for m in hits
           if m.group(2) is None or _norm(m.group(2)) != PRIMITIVE_FALLBACKS[m.group(1)]]
    assert not bad, f"wrong or missing primitive fallbacks: {bad}"


@pytest.mark.needs_full_checkout("mockups")
def test_gmi_css_selector_parity():
    """.gmi-* class sets: specimen section C..O == templates/gmi.css."""
    specimen = _read_mockups("gmi_explorer.css")
    start = specimen.index("/* ---------- C.")
    spec_classes = set(re.findall(r"\.gmi-[a-z0-9-]+", specimen[start:]))
    gmi_classes = set(re.findall(r"\.gmi-[a-z0-9-]+", GMI_CSS))
    assert gmi_classes == spec_classes, (
        f"only-in-specimen={sorted(spec_classes - gmi_classes)} "
        f"only-in-gmi.css={sorted(gmi_classes - spec_classes)} "
        f"(counts: gmi.css={len(gmi_classes)} specimen={len(spec_classes)})")


@pytest.mark.needs_full_checkout("mockups")
def test_gmi_js_states_match_specs():
    """GMI_STATES equals the §10 table keys, in table order."""
    specs = _read_mockups("SPECS.md")
    section10 = specs.split("## 10.", 1)[1].split("## 11.", 1)[0]
    keys = re.findall(r"^\| `([a-z_]+)` \|", section10, re.M)
    assert len(keys) == 10, keys
    m = re.search(r"GMI_STATES\s*=\s*Object\.freeze\(\[([^\]]*)\]\)", GMI_JS)
    assert m, "GMI_STATES literal not found in templates/gmi.js"
    js_keys = re.findall(r"'([a-z_]+)'", m.group(1))
    assert js_keys == keys


def test_gmi_js_no_style_injection():
    """None of the forbidden presentation-side-effect tokens occur in gmi.js."""
    forbidden = [
        "<style", "<link", "textContent", "innerHTML", "insertRule", "cssText",
        ".style", "setAttribute('style'", 'setAttribute("style"',
        "document.title", ".title", "fetch(", "XMLHttpRequest", "localStorage",
    ]
    present = [tok for tok in forbidden if tok in GMI_JS]
    assert not present, f"forbidden tokens in templates/gmi.js: {present}"


@pytest.mark.needs_full_checkout("site")
def test_pairs_byte_identical():
    """templates/{gmi.css,gmi.js,theme.css} are byte-identical to site/ copies."""
    for name in ("gmi.css", "gmi.js", "theme.css"):
        assert (ROOT / "templates" / name).read_bytes() == \
               (ROOT / "site" / name).read_bytes(), name
