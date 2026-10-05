#!/usr/bin/env python3
"""Replay the two valuation panel fixtures through the canonical capture tool.

Run from the repository root with Python 3.12, jinja2, pytest and Playwright
installed, and Chromium installed by ``python3 -m playwright install chromium``:

    PATH="/Library/Frameworks/Python.framework/Versions/3.12/bin:$PATH" python3 \
        mockups/evidence/valuation_scenario/_recapture.py

The original disposable wrapper is gone. This reconstructs its documented
normal/all-null AAPL fixture matrix, using the current committed ticker CSS and
translation macro instead of inventing panel styling. Crops cover the panel,
not the surrounding stock page. Synthetic fixtures are not live SEC evidence.
All temporary files stay inside this worktree. One browser captures sequentially.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
REL = HERE.relative_to(ROOT).as_posix()
WRAPPER = f"{REL}/_recapture.py"
ROUTES = ("/stocks/AAPL.html", "/stocks-null/AAPL.html")
GAPS = (
    "Local synthetic normal/all-null AAPL panel crops only; no live deployment, "
    "authentication or real SEC-data freshness proof. Thin-margin and one-case "
    "near/below/above branches are tests-only, not captured in this 16-cell matrix."
)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> int:
    if sys.version_info[:2] != (3, 12) or Path.cwd().resolve() != ROOT:
        raise SystemExit("Run from this worktree's root with Python 3.12.")
    sys.path.insert(0, str(ROOT))
    import jinja2
    from scripts import capture_page_evidence as capture
    from engine import valuation_scenario

    code_head = git("log", "-1", "--format=%H", "HEAD", "--", ".", f":(exclude){REL}")
    # All rendered inputs and imports must still be the code head's bytes.
    for path in git("diff", "--name-only", code_head).splitlines():
        if not path.startswith(REL + "/"):
            raise SystemExit(f"Code differs from CODE_HEAD: {path}")
    fixture = runpy.run_path(str(ROOT / "tests/test_valuation_scenario.py"))["FIXTURE_ROW"]
    ticker = (ROOT / "templates/ticker.html.j2").read_text()
    macro = re.search(r"\{%- macro t\(.*?\{%- endmacro -%\}", ticker, re.S).group(0)
    css = re.search(r"<style>(.*?)</style>", ticker, re.S).group(1)
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(ROOT / "templates"))
    document = env.from_string(
        macro + '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<link rel="stylesheet" href="../theme.css"><style>' + css + '</style>'
        '</head><body>{% include "_valuation_scenario.html.j2" %}</body></html>'
    )

    class PanelDriver:
        """Reuse the canonical browser setup/state probes; crop the actual DOM."""

        def __init__(self, **kwargs):
            self.driver = capture.playwright_page_driver(**kwargs)

        def close(self):
            self.driver.close()

        def capture(self, *, url, cell, timeout_s):
            context = self.driver._browser.new_context(
                viewport={"width": cell.width, "height": cell.height},
                user_agent=self.driver._user_agent, device_scale_factor=1,
                locale="zh-CN" if cell.locale == "zh" else "en-US",
                color_scheme=cell.theme,
            )
            state = {"theme": cell.theme, "locale": cell.locale}
            context.add_init_script(capture.state_seed_source(state))
            page = context.new_page()
            errors, failures = [], []
            page.on("console", lambda msg: errors.append({
                "text": msg.text, "source_url": (msg.location or {}).get("url"),
            }) if msg.type == "error" else None)
            page.on("pageerror", lambda error: errors.append({"text": str(error), "source_url": None}))
            page.on("response", lambda response: failures.append({
                "url": response.url, "status": response.status,
            }) if response.status >= 400 else None)
            try:
                response = page.goto(url, wait_until="load", timeout=timeout_s * 1000)
                if response is None or not response.ok:
                    raise RuntimeError(f"Route failed to load: {url}")
                applied = page.evaluate(capture._APPLY_STATE_SCRIPT, state)
                page.evaluate("document.fonts.ready")
                page.wait_for_timeout(self.driver._settle_ms)
                observed = page.evaluate(capture._OBSERVER_SCRIPT, self.driver._observer_config)
                png = page.locator("#valuation-scenario").screenshot(animations="disabled")
                return capture.CellObservation(
                    cell_id=cell.cell_id, loaded=True, screenshot_png=png,
                    observed=observed, console_errors=tuple(errors),
                    failed_responses=tuple(failures),
                    applied_theme=applied.get("theme"), applied_locale=applied.get("locale"),
                )
            except Exception as exc:
                return capture.CellObservation(
                    cell_id=cell.cell_id, loaded=False, error=str(exc),
                    console_errors=tuple(errors), failed_responses=tuple(failures),
                )
            finally:
                context.close()

    # Stage the complete capture before replacing any historical receipts.
    with tempfile.TemporaryDirectory(prefix=".recapture-", dir=HERE) as directory:
        work = Path(directory)
        site, output = work / "site", work / "output"
        site.mkdir()
        for asset in ("theme.css", "product-nav-icons.css"):
            shutil.copyfile(ROOT / "templates" / asset, site / asset)
        shutil.copytree(ROOT / "templates/fonts", site / "fonts")
        for route, row in zip(ROUTES, (fixture, {**fixture, "ni": None})):
            blob = valuation_scenario.compute(
                [row], price=319.97 if row["ni"] is not None else None,
                asof="2026-09-05", ticker="AAPL",
            )
            path = site / route.lstrip("/")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(document.render(valuation_scenario=blob, deep_ids=[]))
        status = capture.main([
            "--site-dir", str(site), "--routes", ",".join(ROUTES),
            "--registry", str(work / "no-registry.json"),
            "--viewports", "desktop,mobile", "--themes", "dark,light",
            "--locales", "en,zh", "--max-pages", "2",
            "--output-dir", str(output), "--manifest", str(output / "manifest.json"),
            "--smells", str(output / "smells.json"), "--emit-md", str(output / "smells.md"),
        ], driver_factory=PanelDriver)
        if status:
            return status
        manifest = json.loads((output / "manifest.json").read_text())
        assert manifest["totals"] == {"pages": 2, "states_attempted": 16, "states_captured": 16}
        assert all(not p["console_errors"] and not p["failed_responses"] for p in manifest["pages"])
        assert all(not p["gaps"] or all(g["dimension"] in ("access", "page_state") for g in p["gaps"]) for p in manifest["pages"])
        manifest["target"].update({
            "resolved_sha_or_none": code_head,
            "resolved_sha_source": "CODE_HEAD; clean committed render inputs verified by _recapture.py",
            "site_dir": "temporary fixture site inside this worktree (removed after capture)",
        })
        manifest["selection"]["registry"] = "none; explicit fixture routes"
        manifest["tool"]["module_ref"] = f"scripts/capture_page_evidence.py via {WRAPPER}"
        manifest["tool"]["wrapper_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        manifest["honesty"]["gaps"] = GAPS
        manifest["honesty"]["force_states"] = (
            "The historical axes.force_states list was empty. --force-state adds CSS "
            "presentation cells; it does not synthesize scenario data. These two routes "
            "use explicit synthetic input fixtures and no CSS forcing (16 rest cells)."
        )
        manifest["honesty"]["metrics"] = "Panel DOM observations; request/payload byte counters are not instrumented by this crop driver."
        for page in manifest["pages"]:
            page["metrics"].pop("request_count", None)
            page["metrics"].pop("payload_bytes_total", None)
        (output / "manifest.json").write_bytes(capture.canonical_json_bytes(manifest))
        smells = json.loads((output / "smells.json").read_text())
        smells["tool"]["module_ref"] = manifest["tool"]["module_ref"]
        smells["target"] = dict(manifest["target"])
        for page in smells["pages"]:
            page["metrics"].pop("request_count", None)
            page["metrics"].pop("payload_bytes_total", None)
        (output / "smells.json").write_bytes(capture.canonical_json_bytes(smells))
        notes = f"""
## Re-capture notes (Heal h3_7117, 2026-09-19)

CODE_HEAD: `{code_head}`. Replay: `{WRAPPER}`.
The lost disposable wrapper was reconstructed using the existing AAPL test fixture,
the production translation macro and ticker styles, and the unchanged valuation
partial. Both routes are local panel fixtures; they are not full live stock pages.
Dark/light × EN/ZH × desktop 1440/mobile 390 × normal/all-null = 16/16 crops.
The historic manifest has no CSS-forced states; no --force-state flag is used.

The current thin-margin ruler label is `Margin too thin to run / 利润率过低，无法计算`.
That label and `Today's price sits near the case we could run. / 当前股价接近唯一已算出的情景。`
are **tests-only, not captured** in the normal/all-null matrix. The one/two-case
below/above copy is likewise tests-only. Null panels capture missing reported
earnings; they do not stand in for the distinct thin-margin case.

{GAPS}
The 21-test suite passed; deliberately wrong near expectations produced
`2 failed, 19 passed` before restoration. No current template string needed repair.
"""
        (output / "smells.md").write_text(capture.render_markdown(smells) + notes)
        # Delete only PNGs named by the prior manifest, after complete success.
        previous = json.loads((HERE / "manifest.json").read_text())
        new_names = {s["file"] for p in manifest["pages"] for s in p["states"]}
        old_names = {s["file"] for p in previous["pages"] for s in p["states"] if s.get("file")}
        for name in old_names - new_names:
            if re.fullmatch(r"[0-9a-f]{16}\.png", name):
                (HERE / name).unlink(missing_ok=True)
        for source in output.iterdir():
            shutil.copyfile(source, HERE / source.name)
        (HERE / "EVIDENCE.yml").write_text(
            f"# CODE_HEAD: {code_head}\n"
            "schema: mastermind.page_evidence_receipt.v1\nchanged_paths:\n"
            "  - templates/_valuation_scenario.html.j2\n"
            f"manifest: {REL}/manifest.json\n"
        )
        print(f"CODE_HEAD: {code_head}; 16/16 captured; wrapper: {WRAPPER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
