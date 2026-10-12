"""Served-route matrix for the Risk Radar pullback section on macro.html and china.html.

Pure checks (cell list, measurement evaluation, receipt) do not import a browser.
The driver loads its library inside run_matrix.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA = "risk_radar_pullback_matrix.v1"
EXPECTED_HEADING = {"en": "Estimate unavailable", "zh": "估计暂不可用"}
VIEWPORTS = (("desktop", 1440, 900), ("mobile", 375, 812))

# Served-page contract. Line numbers are the template sources the selectors come from.
# US opener #mx5BtnRisk: templates/dashboard.html.j2:8357 and :8372, onclick mx5OpenDlg('dlg-risk').
# US dialog #dlg-risk: templates/dashboard.html.j2:12846. Open CSS .mx5-dlg.open at :5100.
# US trap _trapTab/_tabStop/_focusFirst: templates/dashboard.html.j2:15207, :15215, :15225.
# CN opener card: templates/china.html.j2:2223. Always-present fallback a[href="#cnx-dlg-risk"]: :2143.
# CN dialog #cnx-dlg-risk: templates/_risk_radar_dlg.html.j2:95. Open CSS .cnx-dlg.open at china.html.j2:1139.
# CN trap _riskTrapTab/_riskTabStop: templates/china.html.j2:4646 and :4657.
# section.pbx, time[datetime], .rrp-forecast h3, .rrp-forecast-row:
# templates/_risk_radar_pullback_depth.html.j2:54, :65, :116, :118.
PAGE_CONTRACT = {
    "us": {
        "dialog": "#dlg-risk",
        "openers": ("#mx5BtnRisk",),
    },
    "cn": {
        "dialog": "#cnx-dlg-risk",
        "openers": (
            'div.cnx-card[role="button"][onclick*="cnx-dlg-risk"]',
            'a[href="#cnx-dlg-risk"]',
        ),
    },
}


class SetupError(RuntimeError):
    """Browser, path, or page-load failure. Maps to exit code 2."""


def parse_pages(spec: str) -> list[tuple[str, str]]:
    pages = []
    for part in (spec or "").split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"page spec {part!r} is not name=file")
        name, filename = (piece.strip() for piece in part.split("=", 1))
        if name not in PAGE_CONTRACT:
            raise ValueError(f"unknown page {name!r}")
        if not filename or "/" in filename or filename.startswith("."):
            raise ValueError(f"page file {filename!r} is not a single filename")
        pages.append((name, filename))
    if not pages:
        raise ValueError("no pages")
    return pages


def _cell(name, filename, lang, theme, viewport, width, height, motion, javascript) -> dict:
    return {
        "page": name,
        "file": filename,
        "lang": lang,
        "theme": theme,
        "viewport": viewport,
        "width": width,
        "height": height,
        "motion": motion,
        "javascript": javascript,
    }


def enumerate_cells(pages: list[tuple[str, str]]) -> list[dict]:
    """page × lang × theme × viewport, then reduced-motion and JS-off per page."""
    cells = []
    for name, filename in pages:
        if name not in PAGE_CONTRACT:
            raise ValueError(f"unknown page {name!r}")
        for lang in ("en", "zh"):
            for theme in ("dark", "light"):
                for viewport, width, height in VIEWPORTS:
                    cells.append(_cell(
                        name, filename, lang, theme, viewport, width, height,
                        "no-preference", True,
                    ))
        cells.append(_cell(name, filename, "en", "dark", "desktop", 1440, 900, "reduce", True))
        cells.append(_cell(
            name, filename, "en", "dark", "desktop", 1440, 900, "no-preference", False,
        ))
    return cells


def _within(scroll, limit) -> bool:
    try:
        return int(scroll) <= int(limit) + 1
    except (TypeError, ValueError):
        return False


def _rows_have_no_digit(text: str, count) -> bool:
    try:
        n = int(count)
    except (TypeError, ValueError):
        n = 0
    if n < 1:
        return False
    return not any(ch in "0123456789" for ch in (text or ""))


def evaluate_cell(cell: dict, measured: dict) -> dict:
    """Turn one raw measurement dict into checks, failures, and pass/fail.

    JavaScript-off cells pass only when section.pbx is in the DOM with a
    non-empty time[datetime] receipt. Whether the dialog opened is recorded
    and does not decide the cell.
    """
    measured = measured or {}
    javascript = bool(cell.get("javascript", True))
    lang = cell.get("lang") or "en"
    phase = measured.get("phase") or ""
    tab_escapes = measured.get("tab_escapes")
    if not javascript:
        present = bool(measured.get("pbx_present"))
        receipt = str(measured.get("time_datetime") or "").strip()
        dialog_visible = bool(measured.get("dialog_visible"))
        checks = {
            "pbx_present": present,
            "time_receipt_present": bool(receipt),
            "time_datetime": receipt,
            "dialog_without_js": "cannot open" if not dialog_visible else "opened",
        }
        failures = []
        if not present:
            failures.append("pbx_present")
        if not receipt:
            failures.append("time_receipt_present")
        return {
            "phase": phase,
            "checks": checks,
            "tab_escapes": tab_escapes,
            "failures": failures,
            "passed": not failures,
        }

    heading = " ".join(str(measured.get("forecast_heading_text") or "").split())
    row_text = str(measured.get("forecast_row_text") or "")
    row_count = measured.get("forecast_row_count")
    if row_count is None:
        row_count = 1 if row_text.strip() else 0
    dialog_visible = bool(measured.get("dialog_visible"))
    checks = {
        "dialog_visible": dialog_visible,
        "pbx_present": bool(measured.get("pbx_present")),
        "forecast_heading_text": heading,
        "forecast_heading_ok": heading == EXPECTED_HEADING.get(lang, ""),
        "forecast_rows_have_no_digit": _rows_have_no_digit(row_text, row_count),
        "no_page_overflow": _within(measured.get("page_scroll_width"), measured.get("page_inner_width")),
        "no_dialog_overflow": _within(measured.get("dialog_scroll_width"), measured.get("dialog_client_width")),
        "escape_closes": bool(measured.get("escape_closes")),
        "focus_returns_to_opener": bool(measured.get("focus_returns_to_opener")),
    }
    if "data_lang" in measured:
        checks["lang_applied"] = (measured.get("data_lang") or "en") == lang
    if "data_theme" in measured:
        checks["theme_applied"] = (measured.get("data_theme") or "dark") == (cell.get("theme") or "dark")
    required = (
        "dialog_visible", "pbx_present", "forecast_heading_ok", "forecast_rows_have_no_digit",
        "no_page_overflow", "no_dialog_overflow", "escape_closes", "focus_returns_to_opener",
        "lang_applied", "theme_applied",
    )
    failures = [name for name in required if name in checks and checks[name] is not True]
    if tab_escapes != 0:
        failures.append("tab_escapes")
    return {
        "phase": phase,
        "checks": checks,
        "tab_escapes": tab_escapes,
        "failures": failures,
        "passed": not failures,
    }


def cell_record(cell: dict, evaluation: dict, screens=None, applied_via="", opener="", open_note="") -> dict:
    record = {
        "page": cell["page"],
        "file": cell["file"],
        "lang": cell["lang"],
        "theme": cell["theme"],
        "viewport": cell["viewport"],
        "width": cell["width"],
        "height": cell["height"],
        "motion": cell["motion"],
        "javascript": bool(cell["javascript"]),
        "phase": evaluation.get("phase") or "",
        "checks": evaluation["checks"],
        "tab_escapes": evaluation.get("tab_escapes"),
        "screens": screens or {},
        "applied_via": applied_via,
        "opener": opener,
        "failures": list(evaluation.get("failures") or []),
        "pass": bool(evaluation["passed"]),
    }
    if open_note:
        record["open_note"] = open_note
    return record


def assemble_receipt(base: str, started_utc: str, browser_version: str, cells: list[dict]) -> dict:
    return {
        "schema": SCHEMA,
        "base": base,
        "started_utc": started_utc,
        "browser_version": browser_version,
        "cells": cells,
        "pass": bool(cells) and all(bool(cell.get("pass")) for cell in cells),
    }


def page_target(base: str, filename: str) -> str:
    if base.startswith("http://") or base.startswith("https://"):
        return base.rstrip("/") + "/" + filename.lstrip("/")
    root = Path(base)
    if not root.is_dir():
        raise SetupError(f"base is not an http(s) URL or a directory: {base}")
    target = root / filename
    if not target.is_file():
        raise SetupError(f"missing page {target}")
    return target.resolve().as_uri()


def cell_slug(cell: dict) -> str:
    js = "js" if cell["javascript"] else "nojs"
    return f"{cell['page']}-{cell['lang']}-{cell['theme']}-{cell['viewport']}-{cell['motion']}-{js}"


def _sha256(path: Path) -> dict:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"file": path.name, "sha256": digest}


def _pbx_from_html(html: str) -> tuple[bool, str, str]:
    """SSR fallback for a JavaScript-disabled document. Returns present, datetime, phase."""
    start = -1
    for match in re.finditer(r"<section\b[^>]*>", html):
        classes = re.search(r'class="([^"]*)"', match.group(0))
        if classes and {"rrp", "pbx"} <= set(classes.group(1).split()):
            start = match.start()
            break
    if start < 0:
        return False, "", ""
    end = html.find("</section>", start)
    block = html[start:end if end > start else start + 12000]
    phase_match = re.search(r'data-pb-phase="([^"]*)"', block)
    time_match = re.search(r"<time\b[^>]*\bdatetime=\"([^\"]+)\"", block)
    phase = phase_match.group(1) if phase_match else ""
    receipt = time_match.group(1).strip() if time_match else ""
    return True, receipt, phase


def _dialog_is_open(html: str, dialog_id: str) -> bool:
    token = f'id="{dialog_id}"'
    at = html.find(token)
    if at < 0:
        return False
    tag_start = html.rfind("<", 0, at)
    tag_end = html.find(">", at)
    if tag_start < 0 or tag_end < 0:
        return False
    classes = re.search(r'class="([^"]*)"', html[tag_start:tag_end])
    return bool(classes and "open" in classes.group(1).split())


def _static_measurement(html: str, page_name: str) -> dict:
    present, receipt, phase = _pbx_from_html(html)
    dialog_id = PAGE_CONTRACT[page_name]["dialog"].lstrip("#")
    return {
        "dialog_visible": _dialog_is_open(html, dialog_id),
        "pbx_present": present,
        "phase": phase,
        "forecast_heading_text": "",
        "forecast_row_text": "",
        "forecast_row_count": 0,
        "page_scroll_width": 0,
        "page_inner_width": 0,
        "dialog_scroll_width": 0,
        "dialog_client_width": 0,
        "time_datetime": receipt,
        "anon_gate": False,
        "tab_escapes": None,
        "data_lang": "",
        "data_theme": "",
    }


def _boot_source(theme: str, lang: str) -> str:
    """Statement the page head already runs: localStorage.theme / localStorage.lang."""
    return (
        "try{localStorage.setItem('theme',%s);localStorage.setItem('lang',%s);"
        "localStorage.removeItem('themeAuto');}catch(e){}"
        % (json.dumps(theme), json.dumps(lang))
    )

# Head boot reads localStorage.theme / localStorage.lang into html[data-theme] / html[data-lang]
# (dashboard.html.j2:302, china.html.j2:81). Toggles call the same writers
# (theme.js setTheme :522 writes localStorage.theme :525; setLang :634 writes localStorage.lang :638).
_APPLY_JS = """([theme, lang]) => {
  const root = document.documentElement;
  const langNow = () => root.getAttribute('data-lang') || 'en';
  const themeNow = () => root.getAttribute('data-theme') || 'dark';
  const matched = () => themeNow() === theme && langNow() === lang;
  const snap = (via) => ({via: via, data_lang: langNow(), data_theme: themeNow()});
  if (matched()) return snap('localStorage.theme,localStorage.lang');
  const themeBtn = document.getElementById('set-theme-' + theme);
  const langToggle = document.querySelector('.lang-toggle');
  const legacyTheme = document.querySelector('.theme-switch, .theme-btn');
  if (themeBtn || langToggle || legacyTheme) {
    if (themeBtn) themeBtn.click();
    else if (typeof window.setTheme === 'function' && themeNow() !== theme) window.setTheme(theme);
    else if (legacyTheme && themeNow() !== theme) legacyTheme.click();
    if (langToggle && langNow() !== lang) langToggle.click();
    else if (typeof window.setLang === 'function' && langNow() !== lang) window.setLang(lang);
    const close = document.querySelector('#settings-pop.open .settings-close');
    if (close) close.click();
    if (matched()) return snap('toggle:#set-theme-' + theme + ',.lang-toggle');
  }
  if (typeof window.setTheme === 'function' && typeof window.setLang === 'function') {
    window.setTheme(theme);
    window.setLang(lang);
    if (matched()) return snap('window.setTheme,window.setLang');
  }
  try {
    localStorage.setItem('theme', theme);
    localStorage.setItem('lang', lang);
    localStorage.removeItem('themeAuto');
  } catch (e) {}
  root.setAttribute('data-theme', theme);
  root.setAttribute('data-lang', lang);
  return snap('localStorage.theme,localStorage.lang+html[data-theme],html[data-lang]');
}"""

_MEASURE_JS = """(args) => {
  const dlg = document.querySelector(args.dialog);
  const open = !!(dlg && dlg.classList.contains('open') && getComputedStyle(dlg).display !== 'none');
  const pbx = args.javascript
    ? (dlg ? dlg.querySelector('section.pbx') : null)
    : document.querySelector('section.pbx');
  const heading = pbx ? pbx.querySelector('.rrp-forecast h3') : null;
  const rows = pbx ? Array.from(pbx.querySelectorAll('.rrp-forecast-row')) : [];
  const time = pbx ? pbx.querySelector('time[datetime]') : null;
  const anonGate = !!(document.body && document.body.classList.contains('page-macro') &&
    (!window.MMXAccessPreview || (window.MMXAccessPreview.isAnon && window.MMXAccessPreview.isAnon())));
  return {
    dialog_visible: open,
    pbx_present: !!pbx,
    phase: pbx ? (pbx.getAttribute('data-pb-phase') || '') : '',
    forecast_heading_text: heading ? (heading.innerText || '') : '',
    forecast_row_text: rows.map((el) => el.innerText || '').join('\\n'),
    forecast_row_count: rows.length,
    page_scroll_width: document.documentElement.scrollWidth,
    page_inner_width: window.innerWidth,
    dialog_scroll_width: dlg ? dlg.scrollWidth : null,
    dialog_client_width: dlg ? dlg.clientWidth : null,
    time_datetime: time ? (time.getAttribute('datetime') || '') : '',
    anon_gate: anonGate,
    data_lang: document.documentElement.getAttribute('data-lang') || '',
    data_theme: document.documentElement.getAttribute('data-theme') || ''
  };
}"""

_OUTSIDE_JS = """(sel) => {
  const dlg = document.querySelector(sel);
  const active = document.activeElement;
  if (!dlg || !active) return true;
  return !dlg.contains(active);
}"""


def _fence(base: str):
    file_mode = not (base.startswith("http://") or base.startswith("https://"))
    host = "" if file_mode else urlsplit(base).netloc

    def allow(route):
        url = route.request.url
        if url.startswith("data:") or url.startswith("blob:"):
            route.continue_()
            return
        if file_mode:
            if url.startswith("file:"):
                route.continue_()
            else:
                route.abort()
            return
        if urlsplit(url).netloc == host:
            route.continue_()
        else:
            route.abort()

    return allow


def _resolve_opener(page, selectors: tuple[str, ...]) -> str:
    for selector in selectors:
        locator = page.locator(selector)
        try:
            count = locator.count()
        except Exception:
            count = 0
        if count < 1:
            continue
        try:
            if locator.first.is_visible():
                return selector
        except Exception:
            continue
    for selector in selectors:
        if page.locator(selector).count():
            return selector
    return ""


def _wait(page, script: str, arg, timeout: int) -> bool:
    try:
        page.wait_for_function(script, arg=arg, timeout=timeout)
        return True
    except Exception:
        return False


def _shoot(page, path: Path, selector: str = "") -> dict | None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if selector:
        page.locator(selector).screenshot(path=str(path))
    else:
        page.screenshot(path=str(path), full_page=False)
    return _sha256(path)


def _count_tab_escapes(page, dialog: str) -> int:
    escapes = 0
    for combo in ("Tab",) * 40 + ("Shift+Tab",) * 40:
        page.keyboard.press(combo)
        if page.evaluate(_OUTSIDE_JS, dialog):
            escapes += 1
    return escapes


def _drive_cell(page, base: str, cell: dict, out_dir: Path) -> dict:
    contract = PAGE_CONTRACT[cell["page"]]
    url = page_target(base, cell["file"])
    response = page.goto(url, wait_until="load", timeout=60000)
    if response is not None and response.status >= 400:
        raise SetupError(f"{url} returned HTTP {response.status}")
    applied = "javascript disabled; theme.css shows .l-en and the dark palette without data-lang/data-theme"
    if cell["javascript"]:
        applied_state = page.evaluate(_APPLY_JS, [cell["theme"], cell["lang"]]) or {}
        applied = applied_state.get("via") or applied
    opener = ""
    click_error = ""
    if cell["javascript"]:
        opener = _resolve_opener(page, contract["openers"])
        if opener:
            try:
                locator = page.locator(opener).first
                locator.scroll_into_view_if_needed(timeout=5000)
                locator.click(timeout=8000)
            except Exception as exc:
                click_error = str(exc).splitlines()[0][:240]
        opened = _wait(
            page,
            """(sel) => {
              const dlg = document.querySelector(sel);
              if (!dlg || !dlg.classList.contains('open')) return false;
              const style = getComputedStyle(dlg);
              return style.display !== 'none' && style.visibility !== 'hidden';
            }""",
            contract["dialog"],
            2000,
        )
        if opened:
            _wait(
                page,
                """(sel) => {
                  const dlg = document.querySelector(sel);
                  if (!dlg) return false;
                  if (dlg.classList.contains('mx5-dlg-in') || dlg.classList.contains('cnx-in')) return true;
                  return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
                }""",
                contract["dialog"],
                1200,
            )
            _wait(
                page,
                """(sel) => {
                  const dlg = document.querySelector(sel);
                  const active = document.activeElement;
                  return !!(dlg && active && dlg.contains(active));
                }""",
                contract["dialog"],
                2000,
            )
    else:
        try:
            opener = _resolve_opener(page, contract["openers"])
        except Exception:
            opener = ""
        if opener:
            try:
                page.locator(opener).first.click(timeout=4000, force=True)
            except Exception as exc:
                click_error = str(exc).splitlines()[0][:240]
    if cell["javascript"]:
        measured = page.evaluate(
            _MEASURE_JS,
            {"dialog": contract["dialog"], "javascript": True},
        )
    else:
        try:
            measured = page.evaluate(
                _MEASURE_JS,
                {"dialog": contract["dialog"], "javascript": False},
            )
        except Exception:
            measured = _static_measurement(page.content(), cell["page"])
        if not measured.get("dialog_visible"):
            click_error = click_error or "dialog cannot open without javascript"
    screens: dict = {}
    screens_ok = True
    slug = cell_slug(cell)
    try:
        shot = _shoot(page, out_dir / f"{slug}-page.png")
        if shot:
            screens["page"] = shot
    except Exception:
        screens_ok = False
        screens["page"] = None
    if cell["javascript"] and measured.get("dialog_visible"):
        try:
            shot = _shoot(page, out_dir / f"{slug}-dialog.png", contract["dialog"])
            screens["dialog"] = shot
        except Exception:
            screens_ok = False
            screens["dialog"] = None
        try:
            measured["tab_escapes"] = _count_tab_escapes(page, contract["dialog"])
        except Exception as exc:
            raise SetupError(f"keyboard probe failed on {cell['page']}: {exc}") from exc
        page.keyboard.press("Escape")
        measured["escape_closes"] = _wait(
            page,
            """(sel) => {
              const dlg = document.querySelector(sel);
              return !dlg || !dlg.classList.contains('open');
            }""",
            contract["dialog"],
            2000,
        )
        if opener:
            measured["focus_returns_to_opener"] = bool(page.evaluate(
                """(sel) => {
                  const el = document.querySelector(sel);
                  const active = document.activeElement;
                  return !!(el && active && (active === el || el.contains(active)));
                }""",
                opener,
            ))
        else:
            measured["focus_returns_to_opener"] = False
    else:
        screens["dialog"] = None
        if cell["javascript"]:
            measured["tab_escapes"] = None
            measured["escape_closes"] = False
            measured["focus_returns_to_opener"] = False
    if not screens.get("page"):
        screens_ok = False
    if cell["javascript"] and measured.get("dialog_visible") and not screens.get("dialog"):
        screens_ok = False
    evaluation = evaluate_cell(cell, measured)
    if not screens_ok:
        evaluation["checks"]["screenshots_saved"] = False
        evaluation["failures"] = list(evaluation["failures"]) + ["screenshots_saved"]
        evaluation["passed"] = False
    else:
        evaluation["checks"]["screenshots_saved"] = True
    open_note = ""
    if not cell["javascript"]:
        open_note = (
            "dialog cannot open without javascript"
            if not measured.get("dialog_visible")
            else "dialog markup was already open without javascript"
        )
    elif cell["javascript"] and not measured.get("dialog_visible"):
        if measured.get("anon_gate"):
            open_note = (
                "opener click did not open the dialog; body.page-macro anon gate "
                "in mx5OpenDlg returns before the dialog is shown"
            )
        elif click_error:
            open_note = click_error
        elif not opener:
            open_note = "opener control was not in the page"
    return cell_record(cell, evaluation, screens, applied, opener, open_note)


def run_matrix(base: str, pages: list[tuple[str, str]], out_dir: Path, chrome: str | None = None) -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise SetupError(f"browser library is not available ({exc})") from exc
    out_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cells = enumerate_cells(pages)
    records = []
    version = ""
    with sync_playwright() as manager:
        kwargs = {"headless": True}
        if chrome:
            kwargs["executable_path"] = chrome
        else:
            kwargs["channel"] = "chrome"
        try:
            browser = manager.chromium.launch(**kwargs)
        except Exception as exc:
            raise SetupError(f"could not launch the browser ({exc})") from exc
        try:
            version = f"{browser.browser_type.name} {browser.version}"
            for cell in cells:
                context = browser.new_context(
                    viewport={"width": cell["width"], "height": cell["height"]},
                    java_script_enabled=bool(cell["javascript"]),
                    reduced_motion="reduce" if cell["motion"] == "reduce" else "no-preference",
                )
                context.route("**/*", _fence(base))
                if cell["javascript"]:
                    context.add_init_script(_boot_source(cell["theme"], cell["lang"]))
                page = context.new_page()
                try:
                    records.append(_drive_cell(page, base, cell, out_dir))
                finally:
                    context.close()
        finally:
            browser.close()
    return assemble_receipt(base, started, version, records)


def write_receipt(path: Path, receipt: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="http(s) origin directory or a local directory")
    parser.add_argument("--pages", required=True, help="us=macro.html,cn=china.html")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--chrome", default=None, help="browser executable; otherwise the chrome channel")
    args = parser.parse_args(argv)
    try:
        pages = parse_pages(args.pages)
        receipt = run_matrix(args.base, pages, args.out, args.chrome)
    except (SetupError, ValueError) as exc:
        print(f"setup: {exc}", file=sys.stderr)
        return 2
    write_receipt(args.out / "matrix_receipt.json", receipt)
    passed = sum(1 for cell in receipt["cells"] if cell.get("pass"))
    print(f"{passed}/{len(receipt['cells'])} route cells passed")
    return 0 if receipt["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
