"""Prove scoped standalone/China/HK AI Brief UI matches exact publication inputs.

Read-only: reuse the shared Jinja component, never regenerate a brief or alter a
page. Candidate-ref checks cover private-index replay and post-rebase healing.
"""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess

import jinja2

ROOT = Path(__file__).resolve().parents[1]
PAGES = {"china": ("site/china.html", "cnx-dlg-aibrief"),
         "hk": ("site/hk.html", "hkx-dlg-aibrief")}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}


class PublicationError(RuntimeError):
    """The candidate has not proved adoption of its published brief."""


class _Component(HTMLParser):
    def __init__(self, dialog_id=None, lens="china"):
        super().__init__(convert_charrefs=True)
        self.dialog_id = dialog_id
        self.lens = lens
        self.stack = []
        self.dialog_depth = self.component_depth = self.footer_depth = None
        self.found = self.closed = self.dialog_count = 0
        self.tokens = []

    def handle_starttag(self, tag, pairs):
        attrs = dict(pairs)
        classes = set((attrs.get("class") or "").split())
        depth = len(self.stack)
        if self.dialog_id and attrs.get("id") == self.dialog_id:
            self.dialog_count += 1
            self.dialog_depth = depth
        inside_dialog = self.dialog_id is None or self.dialog_depth is not None
        if (inside_dialog and self.component_depth is None
                and "aib2" in classes and attrs.get("data-lens") == self.lens):
            self.component_depth = depth
            self.found += 1
        if self.component_depth is not None:
            if self.footer_depth is None and classes & {"cnx-receipt", "hkx-receipt"}:
                self.footer_depth = depth
            if self.footer_depth is None:
                # Asset normalization can add CSS utility classes. Preserve the
                # component's semantic classes, data/ARIA attributes and structure.
                kept = {k: v for k, v in attrs.items()
                        if k.startswith(("data-", "aria-")) or k == "role"}
                semantic = sorted(c for c in classes
                                  if c.startswith("aib2") or c in {"l-en", "l-zh", "num"})
                if semantic:
                    kept["class"] = " ".join(semantic)
                self.tokens.append(("void" if tag in VOID else "start", tag,
                                    tuple(sorted(kept.items()))))
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag not in self.stack:
            return
        depth = len(self.stack) - 1 - self.stack[::-1].index(tag)
        if (self.component_depth is not None and depth >= self.component_depth
                and self.footer_depth is None):
            self.tokens.append(("end", tag))
        if self.footer_depth is not None and depth <= self.footer_depth:
            self.footer_depth = None
        if self.component_depth is not None and depth == self.component_depth:
            self.closed += 1
            self.component_depth = None
        if self.dialog_depth is not None and depth <= self.dialog_depth:
            self.dialog_depth = None
        del self.stack[depth:]

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_data(self, value):
        if self.component_depth is not None and self.footer_depth is None:
            normalized = " ".join(value.split())
            if normalized:
                self.tokens.append(("text", normalized))


def component_tokens(html, dialog_id=None, lens="china"):
    parsed = _Component(dialog_id, lens)
    parsed.feed(html)
    parsed.close()
    if dialog_id is not None and parsed.dialog_count != 1:
        raise PublicationError("expected exactly one target AI Brief dialog")
    if (parsed.found, parsed.closed) != (1, 1):
        raise PublicationError(f"expected exactly one complete {lens}-lens brief component")
    return parsed.tokens


def expected_component(payload, template, lens="china"):
    if not isinstance(payload, dict) or not payload.get("state_asof"):
        raise PublicationError(f"{lens} brief must have an honest source date")
    if payload.get("lens", lens) != lens:
        raise PublicationError(f"{lens} brief input has the wrong lens")
    if not any(payload.get(k) for k in ("summary", "tldr", "regime_read")):
        raise PublicationError(f"{lens} brief has no rendered narrative")
    # Match the existing page builders: the imported macro uses no global i18n.
    env = jinja2.Environment(loader=jinja2.DictLoader({"body": template}))
    return env.get_template("body").module.aibrief_body(payload, lens, lens == "macro")


def _read(root, path, candidate_ref):
    if candidate_ref:
        result = subprocess.run(["git", "-C", str(root), "show", f"{candidate_ref}:{path}"],
                                capture_output=True, text=True)
        if result.returncode:
            raise PublicationError(f"cannot read {path} from publication candidate")
        return result.stdout
    return (root / path).read_text(encoding="utf-8")


def check(root=ROOT, scope="all", candidate_ref=None):
    requested = set(PAGES) | {"macro"} if scope == "all" else set(scope.split("+"))
    regions = requested & set(PAGES)
    standalone = "macro" in requested
    if not regions and not standalone:
        return []
    try:
        template = _read(root, "templates/_aibrief_body.html.j2", candidate_ref)
        if standalone:
            # The macro scope publishes the US/China/BTC standalone page.
            # Its page builder is fail-open, so stale HTML must not earn a new
            # region watermark merely because another macro builder succeeded.
            html = _read(root, "site/aibrief.html", candidate_ref)
            for lens, name in (
                ("macro", "master_brief.json"),
                ("china", "china_brief.json"),
                ("btc", "btc_brief.json"),
            ):
                payload = json.loads(_read(root, f"site/{name}", candidate_ref))
                expected = component_tokens(expected_component(payload, template, lens), lens=lens)
                actual = component_tokens(html, lens=lens)
                if actual != expected:
                    raise PublicationError(
                        f"site/aibrief.html: {lens} panel does not match the candidate brief"
                    )
        if regions:
            payload = json.loads(_read(root, "site/china_brief.json", candidate_ref))
            expected = component_tokens(expected_component(payload, template))
            for region in sorted(regions):
                page, dialog = PAGES[region]
                actual = component_tokens(_read(root, page, candidate_ref), dialog)
                if actual != expected:
                    raise PublicationError(f"{page}: modal does not match the candidate China brief")
    except (OSError, ValueError, jinja2.TemplateError) as exc:
        raise PublicationError(f"cannot prove AI Brief publication: {exc}") from exc
    return sorted(regions | ({"macro"} if standalone else set()))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--scope", default="all")
    parser.add_argument("--candidate-ref")
    args = parser.parse_args(argv)
    try:
        checked = check(args.root, args.scope, args.candidate_ref)
    except PublicationError as exc:
        print(f"::error title=AI Brief publication withheld::{exc}")
        return 1
    print("AI_BRIEF_PUBLICATION_OK " + ",".join(checked))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
