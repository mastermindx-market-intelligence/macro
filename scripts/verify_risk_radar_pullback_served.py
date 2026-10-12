"""Machine-check a built or served Risk Radar page for the pullback popup contract.

Reads the bytes of one HTML file or one http(s) URL and writes a JSON receipt.
Stdlib only. One fetch, no retries, and no non-http(s) scheme is followed.
Synthetic pages and this receipt are the whole product of the tool: it does not
score a market or publish a downside estimate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path

SCHEMA = "risk_radar_pullback_served.v1"
DIALOG_ID = {"us": "dlg-risk", "cn": "cnx-dlg-risk"}
# CN's shared shell always sets aria-labelledby. The US #dlg-risk shell
# (templates/dashboard.html.j2) ships role + aria-modal and a visible title,
# without aria-labelledby. Absence fails only where the shell is required to
# name itself that way; a present attribute must resolve on either market.
LABEL_REQUIRED = {"us": False, "cn": True}
PHASES = frozenset({
    "monitoring", "developing", "underway", "stabilizing",
    "recovering", "repaired", "unavailable",
})
ACTIVE_PHASES = frozenset({"underway", "stabilizing", "recovering"})
VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})
EM_DASH = "\u2014"
CURRENT_METRIC_RE = re.compile("^\u2212?\\d+\\.\\d%$")
OTHER_PERCENT_RE = re.compile("^[+\u2212-]?\\d+\\.\\d%$")
PERCENT_ANY_RE = re.compile(r"\d+(?:\.\d+)?%")
ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
VALID_UNTIL_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})(\.\d+)?(Z|[+-]\d{2}:\d{2}|[+-]\d{4})\Z"
)
VENDOR_RE = re.compile(
    r"(?i)(?<!<)(?<![A-Za-z0-9])"
    r"(?:yfinance|yahoo|tushare|polygon|massive)"
    r"(?![A-Za-z0-9])"
)


class InputError(Exception):
    """The page bytes could not be read. Exit 2, not a contract failure."""


class Node:
    def __init__(self, tag: str, attrs: dict[str, str]):
        self.tag = tag
        self.attrs = attrs
        self.children: list = []
        self.parent: Node | None = None
        self.start: int | None = None
        self.end: int | None = None


class _PageParser(HTMLParser):
    """Build a parent map and source spans. Script and style stay raw text."""

    def __init__(self, html: str):
        super().__init__(convert_charrefs=True)
        self.html = html
        self.root = Node("#document", {})
        self.root.start = 0
        self.root.end = len(html)
        self.stack = [self.root]
        self.ids: dict[str, Node] = {}
        self._line_starts = [0]
        for index, char in enumerate(html):
            if char == "\n":
                self._line_starts.append(index + 1)

    def _abs(self) -> int:
        line, offset = self.getpos()
        if line < 1 or line - 1 >= len(self._line_starts):
            return 0
        return self._line_starts[line - 1] + offset

    def _tag_end(self, start: int) -> int:
        end = self.html.find(">", start)
        return len(self.html) if end < 0 else end + 1

    def _begin(self, tag: str, attrs: list[tuple[str, str | None]]) -> Node:
        node = Node(tag, {key: ("" if value is None else value) for key, value in attrs})
        node.start = self._abs()
        node.parent = self.stack[-1]
        self.stack[-1].children.append(node)
        element_id = node.attrs.get("id")
        if element_id and element_id not in self.ids:
            self.ids[element_id] = node
        return node

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = self._begin(tag, attrs)
        if tag in VOID_TAGS:
            node.end = self._tag_end(node.start or 0)
            return
        self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = self._begin(tag, attrs)
        node.end = self._tag_end(node.start or 0)

    def handle_endtag(self, tag: str) -> None:
        pos = self._abs()
        end = self._tag_end(pos)
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag != tag:
                continue
            for nested in self.stack[index + 1:]:
                if nested.end is None:
                    nested.end = pos
            self.stack[index].end = end
            del self.stack[index:]
            return

    def handle_data(self, data: str) -> None:
        if data:
            self.stack[-1].children.append(data)

    def handle_comment(self, data: str) -> None:
        self.stack[-1].children.append(data)

    def close(self) -> None:
        super().close()
        end = len(self.html)
        for node in self.stack:
            if node.end is None:
                node.end = end


class _HttpOnlyRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        scheme = urllib.parse.urlsplit(newurl).scheme.lower()
        if scheme not in ("http", "https"):
            raise urllib.error.URLError(f"refusing non-http(s) redirect ({scheme or 'none'})")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify the Risk Radar pullback popup on a built or served page."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--html", help="Path to a built HTML page")
    source.add_argument("--url", help="http(s) URL of a served page")
    parser.add_argument("--market", required=True, choices=sorted(DIALOG_ID))
    parser.add_argument(
        "--require-active",
        action="store_true",
        help="Fail unless the phase is underway, stabilizing, or recovering",
    )
    parser.add_argument("--out", help="Write the JSON receipt to this path")
    return parser


def _fetch(url: str) -> bytes:
    parts = urllib.parse.urlsplit(url)
    scheme = parts.scheme.lower()
    if scheme not in ("http", "https") or not parts.netloc:
        raise InputError(f"refusing non-http(s) url: {url}")
    opener = urllib.request.build_opener(_HttpOnlyRedirect)
    request = urllib.request.Request(url, method="GET", headers={"User-Agent": "pullback-popup-verifier"})
    try:
        with opener.open(request, timeout=20) as response:
            final = urllib.parse.urlsplit(response.geturl()).scheme.lower()
            if final not in ("http", "https"):
                raise InputError(f"refusing non-http(s) response url ({final or 'none'})")
            return response.read()
    except InputError:
        raise
    except Exception as exc:
        raise InputError(f"fetch failed: {exc}") from exc


def _load(args: argparse.Namespace) -> tuple[bytes, dict[str, str]]:
    if args.url:
        return _fetch(args.url), {"url": args.url}
    path = args.html
    file = Path(path)
    if not file.is_file():
        raise InputError(f"html file not found: {path}")
    try:
        return file.read_bytes(), {"file": path}
    except OSError as exc:
        raise InputError(f"cannot read html: {exc}") from exc


def _descendants(node: Node):
    """Element descendants in document (pre-)order."""
    stack = [child for child in reversed(node.children) if isinstance(child, Node)]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(child for child in reversed(current.children) if isinstance(child, Node))


def _has_class(node: Node, token: str) -> bool:
    return token in node.attrs.get("class", "").split()


def _text(node: Node) -> str:
    parts: list[str] = []

    def walk(current: Node) -> None:
        for child in current.children:
            if isinstance(child, str):
                parts.append(child)
            else:
                walk(child)

    walk(node)
    return "".join(parts)


def _norm(node: Node) -> str:
    return re.sub(r"\s+", " ", _text(node)).strip()


def _outer(node: Node, html: str) -> str:
    if node.start is None or node.end is None or node.end < node.start:
        return _norm(node)
    return html[node.start:node.end]


def _is_iso_date(value: str) -> bool:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def _parse_valid_until(value: str) -> datetime | None:
    match = VALID_UNTIL_RE.fullmatch(value)
    if match is None:
        return None
    date_s, time_s, frac, offset = match.groups()
    try:
        parsed = datetime.strptime(f"{date_s}T{time_s}", "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None
    if frac:
        digits = frac[1:7].ljust(6, "0")
        try:
            parsed = parsed.replace(microsecond=int(digits))
        except ValueError:
            return None
    if offset == "Z":
        tz = timezone.utc
    else:
        sign = 1 if offset[0] == "+" else -1
        clock = offset[1:].replace(":", "")
        hours, minutes = int(clock[:2]), int(clock[2:])
        if hours > 23 or minutes > 59:
            return None
        tz = timezone(sign * timedelta(hours=hours, minutes=minutes))
    return parsed.replace(tzinfo=tz)


def _is_unavailable_label(text: str) -> bool:
    compact = re.sub(r"\s+", "", text)
    if not compact:
        return False
    rest = re.sub(r"(?i)unavailable", "", compact).replace("暂无", "")
    return rest == "" and rest != compact


def _magnitude(text: str) -> float:
    body = text[:-1].replace("\u2212", "-")
    return abs(float(body))


def _sections(dialog: Node) -> list[Node]:
    return [node for node in _descendants(dialog) if node.tag == "section" and _has_class(node, "pbx")]


def _metric_nodes(section: Node, name: str) -> list[Node]:
    return [node for node in _descendants(section) if node.attrs.get("data-metric") == name]


def _check_c1(dialog: Node | None, sections: list[Node], ids: dict[str, Node], market: str) -> tuple[bool, str]:
    dialog_id = DIALOG_ID[market]
    problems: list[str] = []
    if dialog is None:
        problems.append(f"#{dialog_id} not found")
    else:
        if dialog.attrs.get("role", "").strip() != "dialog":
            problems.append('role is not "dialog"')
        if dialog.attrs.get("aria-modal", "").strip() != "true":
            problems.append('aria-modal is not "true"')
        labelled = dialog.attrs.get("aria-labelledby")
        if labelled is None:
            if LABEL_REQUIRED[market]:
                problems.append("aria-labelledby is missing")
        else:
            tokens = labelled.split()
            missing = [token for token in tokens if token not in ids]
            if not tokens or missing:
                problems.append(
                    "aria-labelledby does not resolve"
                    + (f" ({' '.join(missing)})" if missing else "")
                )
        if len(sections) != 1:
            problems.append(f"found {len(sections)} section.pbx, expected 1")
    if problems:
        return False, "; ".join(problems)
    labelled = dialog.attrs.get("aria-labelledby") if dialog is not None else None
    label = f"aria-labelledby={labelled}" if labelled else "aria-labelledby absent"
    return True, f"one section.pbx in #{dialog_id}; role=dialog; aria-modal=true; {label}"


def _check_c2(sections: list[Node]) -> tuple[bool, str]:
    if not sections:
        return False, "no section.pbx"
    bad = []
    for section in sections:
        phase = section.attrs.get("data-pb-phase", "").strip()
        if phase not in PHASES:
            bad.append(phase or "<missing>")
    if bad:
        return False, "phase not in the allowed set: " + ", ".join(bad)
    phases = [section.attrs.get("data-pb-phase", "").strip() for section in sections]
    return True, "phase " + ", ".join(phases)


def _c3_problems(section: Node) -> list[str]:
    phase = section.attrs.get("data-pb-phase", "").strip()
    if phase == "unavailable":
        return []
    problems: list[str] = []
    asof = section.attrs.get("data-pb-asof", "").strip()
    valid_until = section.attrs.get("data-pb-valid-until", "").strip()
    if not _is_iso_date(asof):
        problems.append(f"data-pb-asof is not an ISO date ({asof or '<missing>'})")
    parsed_until = _parse_valid_until(valid_until)
    if parsed_until is None:
        problems.append("data-pb-valid-until lacks an explicit UTC offset")
    elif _is_iso_date(asof):
        asof_dt = datetime.strptime(asof, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if not parsed_until > asof_dt:
            problems.append("valid_until is not after asof")
    stamps = [node for node in _descendants(section) if _has_class(node, "rrp-stamp")]
    times = [node for stamp in stamps for node in _descendants(stamp) if node.tag == "time"]
    # The stamp carries the settled-close date, then optionally the zoned
    # "current until" deadline; each must equal its section attribute.
    if len(times) not in (1, 2):
        problems.append(f"expected one or two times in .rrp-stamp, found {len(times)}")
    elif times[0].attrs.get("datetime", "").strip() != asof:
        problems.append("time datetime does not equal data-pb-asof")
    elif len(times) == 2 and times[1].attrs.get("datetime", "").strip() != valid_until:
        problems.append("second time datetime does not equal data-pb-valid-until")
    return problems


def _check_c3(sections: list[Node]) -> tuple[bool, str]:
    if not sections:
        return False, "no section.pbx"
    problems = [item for section in sections for item in _c3_problems(section)]
    if problems:
        return False, "; ".join(problems)
    phases = {section.attrs.get("data-pb-phase", "").strip() for section in sections}
    if phases == {"unavailable"}:
        return True, "not applicable (phase unavailable)"
    return True, "asof, offset valid_until, and .rrp-stamp time agree"


def _c4_problems(section: Node) -> list[str]:
    phase = section.attrs.get("data-pb-phase", "").strip()
    if phase not in ACTIVE_PHASES:
        return []
    problems: list[str] = []
    current_nodes = _metric_nodes(section, "current")
    worst_nodes = _metric_nodes(section, "worst")
    rebound_nodes = _metric_nodes(section, "rebound")
    current = _norm(current_nodes[0]) if len(current_nodes) == 1 else ""
    worst = _norm(worst_nodes[0]) if len(worst_nodes) == 1 else ""
    rebound = _norm(rebound_nodes[0]) if len(rebound_nodes) == 1 else ""
    if len(current_nodes) != 1 or CURRENT_METRIC_RE.fullmatch(current) is None:
        problems.append(f"current does not match the percent contract ({current or '<missing>'})")
    if len(worst_nodes) != 1 or not (OTHER_PERCENT_RE.fullmatch(worst) or _is_unavailable_label(worst)):
        problems.append(f"worst is not a percent or Unavailable ({worst or '<missing>'})")
    if len(rebound_nodes) != 1 or not (OTHER_PERCENT_RE.fullmatch(rebound) or _is_unavailable_label(rebound)):
        problems.append(f"rebound is not a percent or Unavailable ({rebound or '<missing>'})")
    notes = [
        node for node in _descendants(section)
        if _has_class(node, "rrp-note") and "Reference high" in _norm(node)
    ]
    if not any(_is_iso_date(match) for note in notes for match in ISO_DATE_RE.findall(_norm(note))):
        problems.append("Reference high date is missing")
    if (
        CURRENT_METRIC_RE.fullmatch(current)
        and OTHER_PERCENT_RE.fullmatch(worst)
        and _magnitude(worst) + 1e-6 < _magnitude(current)
    ):
        problems.append("worst magnitude is below current")
    return problems


def _check_c4(sections: list[Node]) -> tuple[bool, str]:
    if not sections:
        return False, "no section.pbx"
    problems = [item for section in sections for item in _c4_problems(section)]
    if problems:
        return False, "; ".join(problems)
    phases = {section.attrs.get("data-pb-phase", "").strip() for section in sections}
    if not phases & ACTIVE_PHASES:
        return True, "not applicable for phase " + ", ".join(sorted(phases))
    return True, "current, worst, rebound, and Reference high satisfy the active contract"


def _c5_problems(section: Node, html: str) -> list[str]:
    blocks = [node for node in _descendants(section) if _has_class(node, "rrp-forecast")]
    if len(blocks) != 1:
        return [f"expected one .rrp-forecast, found {len(blocks)}"]
    block = blocks[0]
    problems: list[str] = []
    if block.attrs.get("data-forecast-status", "").strip() != "unavailable":
        problems.append('data-forecast-status is not "unavailable"')
    text = _norm(block)
    if "Estimate unavailable" not in text:
        problems.append('missing "Estimate unavailable"')
    if "估计暂不可用" not in text:
        problems.append('missing "估计暂不可用"')
    rows = [node for node in _descendants(block) if _has_class(node, "rrp-forecast-row")]
    strongs = [node for row in rows for node in _descendants(row) if node.tag == "strong"]
    if len(rows) != 2 or len(strongs) != 2:
        problems.append(f"expected two forecast-row values, found {len(strongs)}")
    else:
        for strong in strongs:
            value = _norm(strong)
            if value != EM_DASH or re.search(r"\d", value):
                problems.append(f"forecast value is not an em dash ({value})")
    # A runaway end offset must not pull the legacy odds copy into this block.
    parts = [text, *[value for node in _descendants(block) for value in node.attrs.values()]]
    if (
        block.start is not None and block.end is not None
        and section.start is not None and section.end is not None
        and section.start <= block.start <= block.end <= section.end
    ):
        parts.append(html[block.start:block.end])
    if PERCENT_ANY_RE.search("\n".join(parts)):
        problems.append("forecast block contains a percent")
    return problems


def _check_c5(sections: list[Node], html: str) -> tuple[bool, str]:
    if not sections:
        return False, "no section.pbx"
    problems = [item for section in sections for item in _c5_problems(section, html)]
    if problems:
        return False, "; ".join(problems)
    return True, "forecast status unavailable; both values are em dashes; no percent"


def _check_c6(dialog: Node | None, html: str) -> tuple[bool, str]:
    page_hits = len(VENDOR_RE.findall(html))
    if dialog is None:
        return False, f"dialog missing; whole_page_count={page_hits}"
    dialog_hits = VENDOR_RE.findall(_outer(dialog, html))
    detail = f"dialog_hits={len(dialog_hits)}; whole_page_count={page_hits}"
    if dialog_hits:
        names = ", ".join(sorted({hit.lower() for hit in dialog_hits}))
        return False, f"{detail}; names={names}"
    return True, detail


def _check_c7(phase: str | None, require_active: bool) -> tuple[bool, str]:
    if not require_active:
        return True, "require-active not set"
    if phase in ACTIVE_PHASES:
        return True, f"phase {phase} is active"
    return False, f"phase {phase or '<missing>'} is not underway|stabilizing|recovering"


def _first_metric(section: Node | None, name: str) -> str | None:
    if section is None:
        return None
    nodes = _metric_nodes(section, name)
    if not nodes:
        return None
    return _norm(nodes[0])


def _evaluate(html: str, market: str, require_active: bool, ids: dict[str, Node], root: Node) -> list[dict]:
    dialogs = [node for node in _descendants(root) if node.attrs.get("id") == DIALOG_ID[market]]
    dialog = dialogs[0] if len(dialogs) == 1 else None
    sections = _sections(dialogs[0]) if dialogs else []
    phase = sections[0].attrs.get("data-pb-phase", "").strip() if sections else None
    if len(dialogs) == 1:
        c1 = _check_c1(dialog, sections, ids, market)
    elif len(dialogs) == 0:
        c1 = (False, f"#{DIALOG_ID[market]} not found")
    else:
        c1 = (False, f"found {len(dialogs)} #{DIALOG_ID[market]}, expected 1")
    pairs = [
        ("C1", c1),
        ("C2", _check_c2(sections)),
        ("C3", _check_c3(sections)),
        ("C4", _check_c4(sections)),
        ("C5", _check_c5(sections, html)),
        ("C6", _check_c6(dialogs[0] if dialogs else None, html)),
        ("C7", _check_c7(phase, require_active)),
    ]
    return [{"id": check_id, "pass": ok, "detail": detail} for check_id, (ok, detail) in pairs]


def verify_html(raw: bytes, source: dict[str, str], market: str, require_active: bool) -> dict:
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        html = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InputError(f"html is not utf-8: {exc}") from exc
    parser = _PageParser(html)
    parser.feed(html)
    parser.close()
    dialogs = [node for node in _descendants(parser.root) if node.attrs.get("id") == DIALOG_ID[market]]
    primary = _sections(dialogs[0])[0] if dialogs and _sections(dialogs[0]) else None
    checks = _evaluate(html, market, require_active, parser.ids, parser.root)
    return {
        "schema": SCHEMA,
        "source": source,
        "fetched_at_utc": fetched_at,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "market": market,
        "phase": primary.attrs.get("data-pb-phase", "").strip() if primary is not None else None,
        "asof": primary.attrs.get("data-pb-asof", "").strip() if primary is not None else None,
        "valid_until": primary.attrs.get("data-pb-valid-until", "").strip() if primary is not None else None,
        "source_digest": primary.attrs.get("data-pb-digest", "").strip() if primary is not None else None,
        "metrics": {
            "current": _first_metric(primary, "current"),
            "worst": _first_metric(primary, "worst"),
            "rebound": _first_metric(primary, "rebound"),
            "age": _first_metric(primary, "age"),
        },
        "checks": checks,
        "pass": all(item["pass"] for item in checks),
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        raw, source = _load(args)
        receipt = verify_html(raw, source, args.market, args.require_active)
    except InputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    payload = json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        try:
            Path(args.out).write_text(payload, encoding="utf-8")
        except OSError as exc:
            print(f"error: cannot write receipt: {exc}", file=sys.stderr)
            return 2
    sys.stdout.write(payload)
    return 0 if receipt["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
