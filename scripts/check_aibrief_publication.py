"""Prove scoped China/HK AI Brief modals match the exact publication input.

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
    def __init__(self, dialog_id=None):
        super().__init__(convert_charrefs=True)
        self.dialog_id = dialog_id
        self.stack = []
        self.dialog_depth = self.component_depth = self.footer_depth = None
        self.found = self.closed = 0
        self.tokens = []

    def handle_starttag(self, tag, pairs):
        attrs = dict(pairs)
        classes = set((attrs.get("class") or "").split())
        depth = len(self.stack)
        if self.dialog_id and attrs.get("id") == self.dialog_id:
            self.dialog_depth = depth
        inside_dialog = self.dialog_id is None or self.dialog_depth is not None
        if (inside_dialog and self.component_depth is None
                and "aib2" in classes and attrs.get("data-lens") == "china"):
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


def component_tokens(html, dialog_id=None):
    parsed = _Component(dialog_id)
    parsed.feed(html)
    parsed.close()
    if (parsed.found, parsed.closed) != (1, 1):
        raise PublicationError("expected exactly one complete China-lens brief component")
    return parsed.tokens


def expected_component(payload, template):
    if not isinstance(payload, dict) or not payload.get("state_asof"):
        raise PublicationError("China brief must have an honest source date")
    if payload.get("lens", "china") != "china":
        raise PublicationError("China brief input has the wrong lens")
    if not any(payload.get(k) for k in ("summary", "tldr", "regime_read")):
        raise PublicationError("China brief has no rendered narrative")
    # Match the existing page builders: the imported macro uses no global i18n.
    env = jinja2.Environment(loader=jinja2.DictLoader({"body": template}))
    return env.get_template("body").module.aibrief_body(payload, "china", False)


def _read(root, path, candidate_ref):
    if candidate_ref:
        result = subprocess.run(["git", "-C", str(root), "show", f"{candidate_ref}:{path}"],
                                capture_output=True, text=True)
        if result.returncode:
            raise PublicationError(f"cannot read {path} from publication candidate")
        return result.stdout
    return (root / path).read_text(encoding="utf-8")


def check(root=ROOT, scope="all", candidate_ref=None):
    regions = set(PAGES) if scope == "all" else set(scope.split("+")) & set(PAGES)
    if not regions:
        return []
    try:
        payload = json.loads(_read(root, "site/china_brief.json", candidate_ref))
        template = _read(root, "templates/_aibrief_body.html.j2", candidate_ref)
        expected = component_tokens(expected_component(payload, template))
        for region in sorted(regions):
            page, dialog = PAGES[region]
            actual = component_tokens(_read(root, page, candidate_ref), dialog)
            if actual != expected:
                raise PublicationError(f"{page}: modal does not match the candidate China brief")
    except (OSError, ValueError, jinja2.TemplateError) as exc:
        raise PublicationError(f"cannot prove AI Brief publication: {exc}") from exc
    return sorted(regions)


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
