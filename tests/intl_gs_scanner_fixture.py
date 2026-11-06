#!/usr/bin/env python3
"""INTL-GS-W2A (IM13) fixture + evidence CLI: production, abstain-all and
specimen variants of the real intl.html through the REAL scanner/coverage
builders and templates.

CLI:
    python3 tests/intl_gs_scanner_fixture.py --out <dir>
    python3 tests/intl_gs_scanner_fixture.py --print-html
    python3 tests/intl_gs_scanner_fixture.py --print-abstain
    python3 tests/intl_gs_scanner_fixture.py --print-specimen

``--out`` writes the foundation site first (tests/intl_gs_fixture_site.py
write_site, NO --stub-coverage), then OVERWRITES intl.html with the
PRODUCTION variant (attach_surveillance over a synthetic admitted observation
set built exactly the way tests/test_intl_gs_foundation.py builds one: two
source_snapshot calls, build_return_records, qualify per basis, through
lib.intl_gs_observations.build_observation_set — every number reaches the page
through the Wave 1 contract), writes intl-abstain.html (observations=None) and
intl-gs-scanner-specimen.html (the spec §10.1 specimen rows inside the
specimen chip, layout acceptance only). Specimen values NEVER leave this
module: no production code path can set the specimen flag.
"""
import argparse
import importlib.util
import json
import re
from html.parser import HTMLParser
from functools import lru_cache
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


site = _load("intl_gs_fixture_site", "tests/intl_gs_fixture_site.py")  # noqa: E402

EVALUATED_AT = "2026-10-09T20:30:00+00:00"
CHECKED_AT = "2026-10-09T15:00:00+00:00"
W2A_GRANT = {
    "status": "confirmed",
    "scope": "intl-index-fx-eod-user-facing-v1",
    "decision_ref": "chairman:2026-10-09:user-facing-redistribution-confirmed",
}


def synthetic_closes(tmp_path):
    """The W2FX synthetic frame recipe (tests/test_intl_gs_foundation.py),
    verbatim in shape: 280 business days ending 2026-10-07, one strictly
    positive monotone series per configured index/fx symbol."""
    import pandas as pd
    from engine import intl_inputs
    dates = pd.bdate_range(end="2026-10-07", periods=280)
    series = []
    for cc, market in intl_inputs.countries().items():
        for symbol in (market["index"], market["fx"]):
            if symbol not in series:
                series.append(symbol)
    cols = {}
    for slot, symbol in enumerate(series):
        if symbol == "^AXJO":
            # R-03 (review r2): one admitted declining series, so a QUALIFIED
            # negative observation exists and the sign -> direction ink is
            # pinnable on the production variant (every other series rises).
            value = [float(200 - 0.0625 * i) for i in range(len(dates))]
        else:
            value = [float(100 + slot * 4 + 0.125 * i) for i in range(len(dates))]
        cols[symbol] = pd.Series(value, index=dates)
        path = tmp_path / "intl" / (
            symbol.replace("^", "_").replace("=", "_").replace("/", "_") + ".parquet")
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"close": value}, index=dates).to_parquet(path)
    return pd.DataFrame(cols).sort_index(), series


def _run_status(tmp_path):
    (tmp_path / "run_status.json").write_text(json.dumps({"sources": {"intl_prices": {
        "source": "intl_prices", "status": "ok", "checked_at": CHECKED_AT,
        "last_date": "2026-10-07"}}}), encoding="utf-8")


def observation_set(tmp_path):
    """PRODUCTION VARIANT: an admitted X2 set over the synthetic closes (some
    markets qualify on every horizon, so the scanner rows are real)."""
    from lib.intl_eod_publication import build_eod_inputs
    from lib.intl_gs_observations import build_observation_set
    frame, _series = synthetic_closes(tmp_path)
    _run_status(tmp_path)
    selected, inputs = build_eod_inputs(
        frame, data_root=tmp_path, evaluated_at=EVALUATED_AT, rights=W2A_GRANT)
    return build_observation_set(
        selected, publication_inputs=inputs, evaluated_at=EVALUATED_AT,
        data_root=tmp_path, rights=W2A_GRANT)


def render_production_page(tmp_path=None):
    """intl.html with attach_surveillance over the synthetic admitted set."""
    from lib.intl_surveillance_mount import attach_surveillance
    from lib.intl_library_mount import render_international_pages
    own_tmp = tmp_path is None
    tmp_path = Path(tempfile.mkdtemp(prefix="intl-gs-w2a-obs-")) if own_tmp else Path(tmp_path)
    try:
        observations = observation_set(tmp_path)
        vm = site._vm()
        vm["intl_workspace"] = attach_surveillance(vm["intl_workspace"],
                                                   observations=observations)
        catalogue = json.loads((ROOT / "config/intl_library_catalogue.json").read_text(encoding="utf-8"))
        pages = render_international_pages(site._env().get_template("intl.html.j2"), vm,
                                           catalogue=catalogue)
        return pages[0]
    finally:
        if own_tmp:
            import shutil
            shutil.rmtree(tmp_path, ignore_errors=True)


def render_page_with_observations(observations):
    """intl.html with attach_surveillance over a caller-built observation set."""
    import json as _json
    from lib.intl_surveillance_mount import attach_surveillance
    from lib.intl_library_mount import render_international_pages
    vm = site._vm()
    vm["intl_workspace"] = attach_surveillance(vm["intl_workspace"], observations=observations)
    catalogue = _json.loads((ROOT / "config/intl_library_catalogue.json").read_text(encoding="utf-8"))
    pages = render_international_pages(site._env().get_template("intl.html.j2"), vm,
                                       catalogue=catalogue)
    return pages[0]


def render_abstain_page():
    """observations=None — the foundation's own production variant."""
    return site.render_intl_page(include_surveillance=True, stub_coverage=False)


def _specimen_panel():
    """The spec §10.1 specimen rows as a scanner panel payload. Layout
    acceptance only (§16.3 S1/S2); fabricated specimen numbers live in THIS
    function and never in lib/ or templates/. Abstain copy strings come from
    the foundation vocabulary (imported, never copied)."""
    from lib.intl_gs_display import horizon_label, reason_copy

    def _abstain(token):
        return {"token": token, "reason": reason_copy(token)}
    en, zh = horizon_label("1m")

    def leg(value):
        return {"state": "complete", "pct": value, "reasons": [], "specimen": True}

    rows = [
        {"id": "BR", "name_en": "Brazil", "name_zh": "巴西", "selected": True,
         "local": leg(-4.2), "fx": leg(-2.8), "usd": leg(-6.9), "common": 18,
         "divz": -2.6, "spark": [12, 11, 13, 12, 10, 9, 11, 12, 14, 13, 11, 10, 12, 13, 12, 10, 9, 11, 12, 11],
         "tier": {"kind": "specimen", "label": ("T1", "T1"), "note": ("Delayed 15m", "延迟15分钟"),
                  "state": "complete"}, "stance": "get_ready",
         "market_sub": {"index_id": "B3", "currency": "BRL", "clock": {"datetime": "2026-10-21", "en": "21 Oct 2026", "zh": "2026年10月21日"}}},
        {"id": "TW", "name_en": "Taiwan", "name_zh": "台湾", "selected": False,
         "local": leg(2.4), "fx": leg(0.3), "usd": leg(2.7), "common": 48,
         "divz": 1.9, "spark": [8, 9, 10, 9, 11, 12, 11, 10, 12, 13, 12, 11, 13, 14, 13, 12, 13, 14, 13, 14],
         "tier": {"kind": "specimen", "label": ("Proxy", "代理"), "note": None, "state": "complete"},
         "stance": "watch", "market_sub": {"index_id": "TWSE", "currency": "TWD", "clock": {"datetime": "2026-10-21", "en": "21 Oct 2026", "zh": "2026年10月21日"}}},
        {"id": "KR", "name_en": "Korea", "name_zh": "韩国", "selected": False,
         "local": leg(-1.1), "fx": leg(-0.6), "usd": leg(-1.7), "common": 71,
         "divz": -0.6, "spark": [10, 11, 10, 12, 11, 12, 13, 12, 11, 10, 11, 12, 11, 10, 11, 12, 13, 12, 11, 10],
         "tier": {"kind": "specimen", "label": ("T2", "T2"), "note": None, "state": "complete"},
         "stance": "watch", "market_sub": {"index_id": "KRX", "currency": "KRW", "clock": {"datetime": "2026-10-21", "en": "21 Oct 2026", "zh": "2026年10月21日"}}},
        {"id": "MX", "name_en": "Mexico", "name_zh": "墨西哥", "selected": False,
         "local": leg(-0.7), "fx": leg(-1.5), "usd": leg(-2.2), "common": 41,
         "divz": -1.1, "spark": [13, 12, 13, 11, 12, 11, 10, 11, 12, 11, 10, 9, 10, 11, 10, 11, 12, 11, 10, 9],
         "tier": {"kind": "specimen", "label": ("T3", "T3"), "note": ("Delayed 15m", "延迟15分钟"),
                  "state": "complete"}, "stance": "watch",
         "market_sub": {"index_id": "BMV", "currency": "MXN", "clock": {"datetime": "2026-10-21", "en": "20 Oct 2026", "zh": "2026年10月20日"}}},
        {"id": "JP", "name_en": "Japan", "name_zh": "日本", "selected": False,
         "local": leg(1.8), "fx": leg(-0.9), "usd": leg(0.9), "common": 62,
         "divz": 0.4, "spark": [11, 12, 11, 12, 13, 12, 13, 14, 13, 12, 13, 12, 13, 14, 13, 12, 13, 14, 13, 12],
         "tier": {"kind": "specimen", "label": ("Full · Licensed", "完整 · 已授权"), "note": None,
                  "state": "complete"}, "stance": "watch",
         "market_sub": {"index_id": "JPX", "currency": "JPY", "clock": {"datetime": "2026-10-21", "en": "21 Oct 2026", "zh": "2026年10月21日"}}},
        {"id": "AU", "name_en": "Australia", "name_zh": "澳大利亚", "selected": False,
         "local": leg(0.6), "fx": leg(0.2), "usd": leg(0.8), "common": 55,
         "divz": 0.3, "spark": [12, 12, 13, 12, 11, 12, 13, 12, 11, 12, 13, 12, 11, 12, 13, 12, 11, 12, 11, 12],
         "tier": {"kind": "specimen", "label": ("Full · Licensed", "完整 · 已授权"), "note": None,
                  "state": "complete"}, "stance": "stand_aside",
         "market_sub": {"index_id": "ASX", "currency": "AUD", "clock": {"datetime": "2026-10-21", "en": "21 Oct 2026", "zh": "2026年10月21日"}}},
        {"id": "IN", "name_en": "India", "name_zh": "印度", "selected": False,
         "local": {"state": "qualified", "pct": 0.4, "reasons": [], "specimen": True},
         "fx": {"state": "qualified", "pct": -0.2, "reasons": [], "specimen": True},
         "usd": {"state": "qualified", "pct": 0.2, "reasons": [], "specimen": True},
         "common": 22, "divz": 0.2,
         "spark": [11, 11, 12, 11, 12, 11, 12, 11, 12, 11, 12, 11, 10, 11, 12, 11, 12, 11, 12, 11],
         "tier": {"kind": "specimen", "label": ("Qualified", "有条件"), "note": None, "state": "qualified"},
         "stance": "stand_aside", "market_sub": {"index_id": "NSE", "currency": "INR", "clock": {"datetime": "2026-10-21", "en": "21 Oct 2026", "zh": "2026年10月21日"}}},
        {"id": "ZA", "name_en": "South Africa", "name_zh": "南非", "selected": False,
         "local": {"state": "stale", "pct": 0.3, "reasons": [], "specimen": True},
         "fx": {"state": "stale", "pct": -0.4, "reasons": [], "specimen": True},
         "usd": {"state": "stale", "pct": -0.1, "reasons": [], "specimen": True},
         "common": 35, "divz": 0.1,
         "spark": [12, 11, 12, 13, 12, 11, 10, 11, 10, 9, 10, 11, 10, 9, 8, 9, 10, 9, 8, 9],
         "tier": {"kind": "specimen", "label": ("Stale · 2d", "过期 · 2天"), "note": None, "state": "stale"},
         "stance": "stand_aside", "market_sub": {"index_id": "JSE", "currency": "ZAR", "clock": {"datetime": "2026-10-21", "en": "20 Oct 2026", "zh": "2026年10月20日"}}},
        {"id": "PL", "name_en": "Poland", "name_zh": "波兰", "selected": False,
         "local": {"state": "abstain", "pct": None, "reasons": [], "specimen": True,
                   "specimen_reason": ("Unscored · insufficient history", "未评分 · 历史数据不足")},
         "fx": {"state": "abstain", "pct": None, "reasons": [], "specimen": True,
                "specimen_reason": ("Unscored · insufficient history", "未评分 · 历史数据不足")},
         "usd": {"state": "abstain", "pct": None, "reasons": [], "specimen": True,
                 "specimen_reason": ("Unscored · insufficient history", "未评分 · 历史数据不足")},
         "common": None, "divz": None, "spark": None,
         "tier": {"kind": "specimen", "label": ("Abstain", "弃权"), "note": None, "state": "abstain"},
         "stance": "stand_aside",
         "market_sub": {"index_id": "GPW", "currency": "PLN", "clock": {"datetime": "2026-10-21", "en": "20 Oct 2026", "zh": "2026年10月20日"}}},
    ]
    payload = {
        "specimen": True,
        "horizon": {"id": "1m", "en": en, "zh": zh},
        "basis": {"id": "usd_unhedged"},
        "counts": {"rows": 9, "qualified": 7, "abstain": 2, "nodata": 0, "up": 4},
        "kpi": [
            {"id": "breadth", "kind": "breadth", "up": 4, "qualified": 7,
             "sub": ("20D · baseline 50% breadth", "20日 · 基线50%广度"),
             "clock": ("as of 06:44 UTC", "截至 06:44 UTC"),
             "tier": {"kind": "specimen", "label": ("Full · Licensed", "完整 · 已授权"), "note": None,
                      "state": "complete"}},
            {"id": "largest", "kind": "move", "pct": -6.9, "ink": "down",
             "market": ("BR Ibovespa", "巴西 Ibovespa"),
             "local_pct": -4.2, "fx_pct": -2.8,
             "sub": ("B3 close 21 Oct", "B3 10月21日收盘"),
             "clock": ("21 Oct 08:00 UTC", "10月21日 08:00 UTC"),
             "tier": {"kind": "specimen", "label": ("Full · Licensed", "完整 · 已授权"), "note": None,
                      "state": "complete"}},
            {"id": "common_factor", "kind": "abstain", "token": "common_factor_unadmitted",
             "reason": reason_copy("common_factor_unadmitted")},
            {"id": "spread", "kind": "abstain", "token": "credit_funding_unadmitted",
             "reason": reason_copy("credit_funding_unadmitted")},
        ],
        "rows": rows,
        "nodata": {"count": 0, "markets": []},
        "session_copy": reason_copy("session_calendar_unadmitted"),
        "abstain": {
            "common": _abstain("common_factor_unadmitted"),
            "divergence": _abstain("divergence_unadmitted"),
            "series": _abstain("series_unadmitted"),
            "stance": _abstain("stance_unadmitted"),
            "attention": _abstain("attention_unadmitted"),
            "bands": [{"q": q, **_abstain(token)}
                      for q, token in ((3, "credit_funding_unadmitted"),
                                       (4, "transmission_unadmitted"),
                                       (5, "us_corroboration_unadmitted"),
                                       (6, "thesis_unadmitted"))],
        },
        "market_scope": [],
        "footnote": {"source": None,
                     "withheld_copy": ("Specimen values · not live", "示例数值 · 非实时"),
                     "delay": None},
    }
    return dict(view="scanner", context_id="im-gs-scanner-specimen",
                context={"horizon": "1m", "currency_basis": "usd_unhedged",
                         "return_basis": "price", "source_reference": None},
                generation=None, payload=payload)


def render_specimen_page():
    """The §10.1 specimen panel through the SAME scanner template, wrapped in
    the specimen chip (spec §16.3 S1/S2 layout acceptance only)."""
    from copy import deepcopy
    from lib.intl_gs_display import horizon_label, snapshot_display
    from lib.intl_library_mount import render_international_pages
    vm = site._vm()
    workspace = deepcopy(vm["intl_workspace"])
    raw = {"clocks": {"observation": "2026-10-07",
                      "source_publication": "2026-10-09T15:00:00+00:00",
                      "ingestion": "2026-10-09T15:00:00+00:00",
                      "computation": "2026-10-09T20:30:00+00:00"},
           "qualified": 35, "total": 35}
    withheld = {"clocks": {"observation": None, "source_publication": None,
                           "ingestion": None, "computation": None}, "qualified": 0, "total": 35}
    workspace["surveillance"] = {
        "views": {view: {"status": "available" if view == "scanner" else "not_built"}
                  for view in ("scanner", "dislocations", "transmission", "dossier",
                               "scenario", "replay", "coverage")},
        "universe": {},
        "observations": {"status": None, "source_reference": None, "counts": {}},
        "snapshot": snapshot_display({"local": raw, "usd_unhedged": dict(raw),
                                      "usd_hedged": withheld}),
        "horizon_labels": {
            horizon: {"en": en, "zh": zh}
            for horizon, (en, zh) in ((h, horizon_label(h))
                                      for h in workspace["config"]["horizons"])},
    }
    workspace["surveillance_panels"] = [_specimen_panel()]
    vm["intl_workspace"] = workspace
    catalogue = json.loads((ROOT / "config/intl_library_catalogue.json").read_text(encoding="utf-8"))
    pages = render_international_pages(site._env().get_template("intl.html.j2"), vm,
                                       catalogue=catalogue)
    return pages[0]


def write_site(out_dir):
    """Foundation site (no stub) + the three W2A variants."""
    copied = site.write_site(out_dir)  # intl.html (abstain), states page, assets
    out = Path(out_dir)
    (out / "intl.html").write_text(render_production_page(), encoding="utf-8")
    (out / "intl-abstain.html").write_text(render_abstain_page(), encoding="utf-8")
    (out / "intl-gs-scanner-specimen.html").write_text(render_specimen_page(), encoding="utf-8")
    return copied


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", help="write the W2A fixture site (production + abstain + specimen)")
    parser.add_argument("--print-html", action="store_true", help="print the production intl.html")
    parser.add_argument("--print-abstain", action="store_true", help="print the abstain-all intl.html")
    parser.add_argument("--print-specimen", action="store_true", help="print the specimen page")
    args = parser.parse_args(argv)
    if args.print_html:
        sys.stdout.write(render_production_page())
    if args.print_abstain:
        sys.stdout.write(render_abstain_page())
    if args.print_specimen:
        sys.stdout.write(render_specimen_page())
    if args.out:
        copied = write_site(args.out)
        print(f"wrote intl.html (production), intl-abstain.html, "
              f"intl-gs-scanner-specimen.html + {copied} assets", file=sys.stderr)
    if not (args.out or args.print_html or args.print_abstain or args.print_specimen):
        parser.error("nothing to do: pass --out and/or a --print-* flag")


# Test-only inspection of the existing deferred transport. No runtime loader,
# renderer, sanitizer, model or browser-parity claim is introduced here.
DEFERRED_SCHEMA = 'intl-gs-deferred.v1'
DEFERRED_MARKET_SCHEMA = 'intl-gs-market.v1'
DEFERRED_MAX_BYTES = 8388608
DEFERRED_PAYLOAD_KEYS = (
    'schema', 'view', 'context_id', 'horizon', 'basis', 'generation',
    'markets', 'markup',
)
DEFERRED_MARKET_KEYS = ('schema', 'market_id', 'default', 'markup')
DEFERRED_VIEWS = ('dossier', 'coverage')
# Canonical nesting is carrier -> panel -> market -> article.  The cap only
# guards against pathological input; it is far above the real depth.
MAX_DECODE_DEPTH = 8

_CARRIER_SUFFIX = '-carrier'
_MARKET_ID = re.compile(r'^[A-Z]{2}$')
_VOID_ELEMENTS = frozenset((
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
    'meta', 'param', 'source', 'track', 'wbr',
))


def _refuse(reason):
    """Mirror the runtime's deferredFailure() as a test-visible ValueError."""
    return ValueError(
        'International workspace deferred payload refused: ' + reason)


def _js_optional_generation(value):
    # Match JavaScript's `value || ''`: empty arrays/objects are truthy,
    # unlike Python. They must not become an absent generation identity.
    if value is None or value is False or value == '' or (
            type(value) in (int, float) and value == 0):
        return ''
    return value


class _DuplicateKey(Exception):
    """Raised by the JSON object hook for repeated key names."""


def _unique_object(pairs):
    names = {}
    for name, value in pairs:
        if name in names:
            raise _DuplicateKey(name)
        names[name] = value
    return names


def _attribute_map(attrs):
    """First-occurrence-wins name map, matching DOM getAttribute semantics."""
    names = {}
    for name, value in attrs:
        if name not in names:
            names[name] = '' if value is None else value
    return names


def _market_domains(raw):
    """``data-im-deferred-markets`` -> ordered domain list (marketList)."""
    if not raw:
        return []
    ids = raw.split(',')
    if len(ids) > 256 or len(set(ids)) != len(ids):
        raise _refuse('market domain')
    for market_id in ids:
        if not _MARKET_ID.fullmatch(market_id):
            raise _refuse('market domain')
    return ids


class _EventScanner(HTMLParser):
    """Records the absolute source position of every markup event.

    Positions are converted from the parser's (line, offset) pairs back to
    absolute indexes into the exact input string, so every tag's source span
    is byte-exact regardless of attribute quoting, entities, comments or
    Unicode.
    """

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self._line_starts = [0]
        position = text.find('\n')
        while position != -1:
            self._line_starts.append(position + 1)
            position = text.find('\n', position + 1)
        self.events = []

    def _mark(self, kind, tag=None, attrs=None):
        line, offset = self.getpos()
        self.events.append({
            'kind': kind,
            'start': self._line_starts[line - 1] + offset,
            'tag': tag,
            'attrs': attrs,
        })

    def handle_starttag(self, tag, attrs):
        self._mark('start', tag, attrs)

    def handle_startendtag(self, tag, attrs):
        self._mark('startend', tag, attrs)

    def handle_endtag(self, tag):
        self._mark('end', tag)

    def handle_data(self, data):
        self._mark('data')

    def handle_entityref(self, name):
        self._mark('ref')

    def handle_charref(self, name):
        self._mark('ref')

    def handle_comment(self, data):
        self._mark('comment')

    def handle_decl(self, decl):
        self._mark('decl')

    def handle_pi(self, data):
        self._mark('pi')

    def unknown_decl(self, data):
        self._mark('decl')


def _scan(text):
    """Parse *text* and return events annotated with exact source spans."""
    scanner = _EventScanner(text)
    try:
        scanner.feed(text)
        scanner.close()
    except Exception as error:  # html.parser is lenient; still fail closed
        raise _refuse('carrier scan (%s)' % type(error).__name__) from None
    events = scanner.events
    total = len(text)
    for index, event in enumerate(events):
        if index + 1 < len(events):
            event['end'] = events[index + 1]['start']
        else:
            event['end'] = total
    return events


def _matching_end(events, start_index):
    """Index of the end-tag event closing the element at *start_index*."""
    tag = events[start_index]['tag']
    depth = 0
    for index in range(start_index + 1, len(events)):
        event = events[index]
        if event['kind'] == 'start' and event['tag'] == tag:
            depth += 1
        elif event['kind'] == 'end' and event['tag'] == tag:
            if depth == 0:
                return index
            depth -= 1
    return None


def _script_raw(text, events, start_index):
    """Exact raw text of a <script> element ('' for self-closing forms)."""
    if events[start_index]['kind'] == 'startend':
        return ''
    end_index = _matching_end(events, start_index)
    if end_index is None:
        return None
    return text[events[start_index]['end']:events[end_index]['start']]


def _load_payload(raw, kind):
    """JSON.parse plus plain-object, duplicate-key and closed-key checks."""
    try:
        data = json.loads(raw, object_pairs_hook=_unique_object)
    except _DuplicateKey:
        raise _refuse(kind + ' keys') from None
    except ValueError:
        raise _refuse(kind + ' json') from None
    if not isinstance(data, dict):
        raise _refuse(kind + ' shape')
    keys = DEFERRED_PAYLOAD_KEYS if kind == 'carrier' else DEFERRED_MARKET_KEYS
    if len(data) != len(keys) or set(data) != set(keys):
        raise _refuse(kind + ' keys')
    return data


def _check_panel(markup, entry_id, view, horizon, basis, generation, source):
    """Mirror deferredPanel() over the payload markup's static shape."""
    events = _scan(markup)
    depth = 0
    roots = 0
    first_root = None
    panels = []
    for event in events:
        kind = event['kind']
        if kind not in ('start', 'startend'):
            if kind == 'end' and event['tag'] not in _VOID_ELEMENTS:
                depth = max(0, depth - 1)
            continue
        attrs = _attribute_map(event['attrs'])
        if 'data-im-panel' in attrs:
            panels.append((event, attrs))
        if depth == 0:
            roots += 1
            if first_root is None:
                first_root = event
        if kind == 'start' and event['tag'] not in _VOID_ELEMENTS:
            depth += 1
    if roots != 1 or len(panels) != 1:
        raise _refuse('panel shape')
    event, attrs = panels[0]
    if first_root is not event:
        raise _refuse('panel context')
    if attrs.get('id', '') != entry_id or 'data-gs-panel' not in attrs:
        raise _refuse('panel context')
    if attrs.get('data-view', '') != view:
        raise _refuse('panel view')
    if attrs.get('data-horizon', '') != horizon:
        raise _refuse('panel horizon')
    if attrs.get('data-basis', '') != basis:
        raise _refuse('panel basis')
    if (attrs.get('data-im-generation', '') or '') != (generation or ''):
        raise _refuse('panel generation')
    if (attrs.get('data-source', '') or '') != (source or ''):
        raise _refuse('panel source')


def _check_article(markup, market_id, default):
    """Mirror deferredMarketArticle() over the market payload's shape."""
    events = _scan(markup)
    depth = 0
    roots = 0
    first_root = None
    articles = []
    for event in events:
        kind = event['kind']
        if kind not in ('start', 'startend'):
            if kind == 'end' and event['tag'] not in _VOID_ELEMENTS:
                depth = max(0, depth - 1)
            continue
        attrs = _attribute_map(event['attrs'])
        if 'data-gs-market' in attrs:
            articles.append((event, attrs))
        if depth == 0:
            roots += 1
            if first_root is None:
                first_root = event
        if kind == 'start' and event['tag'] not in _VOID_ELEMENTS:
            depth += 1
    if roots != 1 or len(articles) != 1:
        raise _refuse('market shape')
    event, attrs = articles[0]
    if first_root is not event or event['tag'] != 'article':
        raise _refuse('market identity')
    if attrs.get('data-gs-market', '') != market_id:
        raise _refuse('market identity')
    if ('data-gs-market-default' in attrs) != default:
        raise _refuse('market identity')


def _carrier(text, events, index, attrs):
    """Validate one outer deferred carrier; return its replacement span."""
    if attrs.get('data-im-deferred') != 'v1' or 'data-im-panel' not in attrs:
        raise _refuse('carrier binding')
    if events[index]['kind'] == 'startend':
        # A self-closed carrier element has no payload script child; it is
        # refused rather than silently skipped.
        raise _refuse('carrier missing')
    identity = attrs.get('id', '')
    if not identity.endswith(_CARRIER_SUFFIX):
        raise _refuse('carrier binding')
    entry_id = identity[:-len(_CARRIER_SUFFIX)]
    if not entry_id:
        raise _refuse('carrier binding')
    view = attrs.get('data-view', '')
    if view not in DEFERRED_VIEWS:
        raise _refuse('carrier binding')
    horizon = attrs.get('data-horizon', '')
    basis = attrs.get('data-basis', '')
    if not horizon or not basis:
        raise _refuse('carrier binding')
    source = attrs.get('data-source', '')
    generation = attrs.get('data-im-generation', '')
    markets = _market_domains(attrs.get('data-im-deferred-markets'))

    end_index = _matching_end(events, index)
    if end_index is None:
        raise _refuse('carrier unclosed')
    payload_scripts = []
    for probe in range(index + 1, end_index):
        event = events[probe]
        if event['kind'] not in ('start', 'startend') or event['tag'] != 'script':
            continue
        script_attrs = _attribute_map(event['attrs'])
        if 'data-im-deferred-payload' in script_attrs:
            payload_scripts.append((probe, script_attrs))
    if len(payload_scripts) != 1:
        raise _refuse('carrier missing')
    probe, script_attrs = payload_scripts[0]
    if script_attrs.get('type', '') != 'application/json':
        raise _refuse('carrier missing')
    raw = _script_raw(text, events, probe)
    if raw is None or len(raw) == 0 or len(raw) > DEFERRED_MAX_BYTES:
        raise _refuse('carrier size')

    payload = _load_payload(raw, 'carrier')
    if payload['schema'] != DEFERRED_SCHEMA:
        raise _refuse('carrier schema')
    if (payload['view'] != view or payload['horizon'] != horizon
            or payload['basis'] != basis):
        raise _refuse('carrier identity')
    if _js_optional_generation(payload['generation']) != (generation or ''):
        raise _refuse('carrier generation')
    if not isinstance(payload['markets'], list) or payload['markets'] != markets:
        raise _refuse('carrier markets')
    context_id = payload['context_id']
    if not isinstance(context_id, str) or context_id + '-' + view != entry_id:
        raise _refuse('carrier context')
    markup = payload['markup']
    if not isinstance(markup, str) or len(markup) == 0:
        raise _refuse('carrier markup')
    if len(markup) > DEFERRED_MAX_BYTES:
        raise _refuse('carrier markup')

    _check_panel(markup, entry_id, view, horizon, basis, generation, source)
    replacement = _decode_markets(markup, 1)
    return {
        'start': events[index]['start'],
        'end': events[end_index]['end'],
        'replacement': replacement,
    }


def _market(text, events, index, attrs, depth):
    """Validate one nested market script carrier; return its replacement."""
    if depth > MAX_DECODE_DEPTH:
        raise _refuse('carrier depth')
    script_id = attrs.get('data-im-gs-market-id')
    if attrs.get('type', '') != 'application/json':
        raise _refuse('market carrier type')
    raw = _script_raw(text, events, index)
    if raw is None or len(raw) == 0 or len(raw) > DEFERRED_MAX_BYTES:
        raise _refuse('market carrier size')
    payload = _load_payload(raw, 'market carrier')
    if payload['schema'] != DEFERRED_MARKET_SCHEMA:
        raise _refuse('market carrier schema')
    market_id = payload['market_id']
    if (not isinstance(market_id, str) or not _MARKET_ID.fullmatch(market_id)
            or market_id != script_id):
        raise _refuse('market carrier identity')
    default = payload['default']
    if not isinstance(default, bool):
        raise _refuse('market default')
    if default != ('data-im-gs-market-default' in attrs):
        raise _refuse('market default')
    article = payload['markup']
    if not isinstance(article, str) or len(article) == 0:
        raise _refuse('market carrier markup')
    if len(article) > DEFERRED_MAX_BYTES:
        raise _refuse('market carrier markup')
    _check_article(article, market_id, default)
    replacement = _decode_markets(article, depth + 1)
    if events[index]['kind'] == 'startend':
        end = events[index]['end']
    else:
        end_index = _matching_end(events, index)
        if end_index is None:
            raise _refuse('market carrier unclosed')
        end = events[end_index]['end']
    return {'start': events[index]['start'], 'end': end,
            'replacement': replacement}


def _decode_markets(markup, depth):
    """Replace canonical market script carriers inside *markup*.

    Unrelated script JSON (no ``data-im-gs-market-id`` attribute) is machine
    data: it stays byte-identical and is never decoded or made visible.
    """
    if depth > MAX_DECODE_DEPTH:
        raise _refuse('carrier depth')
    events = _scan(markup)
    found = []
    for index, event in enumerate(events):
        if event['kind'] not in ('start', 'startend') or event['tag'] != 'script':
            continue
        attrs = _attribute_map(event['attrs'])
        if 'data-im-gs-market-id' in attrs:
            found.append(_market(markup, events, index, attrs, depth))
    if not found:
        return markup
    found.sort(key=lambda span: span['start'])
    pieces = []
    cursor = 0
    for span in found:
        pieces.append(markup[cursor:span['start']])
        pieces.append(span['replacement'])
        cursor = span['end']
    pieces.append(markup[cursor:])
    return ''.join(pieces)


# At most two invocation-local immutable HTML strings/results are retained;
# observation and payload builders remain uncached and run for each assertion.
@lru_cache(maxsize=2)
def expand_deferred_for_assertions(html):
    """Return *html* with each validated deferred carrier replaced by its
    canonical markup.

    Legacy markup without any ``data-im-deferred`` carrier is returned
    unchanged, byte for byte.  A ``data-im-deferred`` element whose payload
    is missing, duplicated, malformed, foreign, or whose panel root does not
    match the carrier identity raises ``ValueError``; nothing is silently
    skipped and no assertion material (cells, rows, source text, clocks,
    numeric values) is discarded.
    """
    if not isinstance(html, str):
        raise TypeError('html must be str')
    if 'data-im-deferred' not in html:
        return html
    text = html
    events = _scan(text)
    carriers = []
    for index, event in enumerate(events):
        if event['kind'] not in ('start', 'startend'):
            continue
        attrs = _attribute_map(event['attrs'])
        if 'data-im-deferred' in attrs:
            carriers.append(_carrier(text, events, index, attrs))
    if not carriers:
        return text
    carriers.sort(key=lambda span: span['start'])
    pieces = []
    cursor = 0
    replaced_to = None
    for span in carriers:
        if replaced_to is not None and span['end'] <= replaced_to:
            # A carrier nested inside an already-replaced carrier span
            # disappears together with the outer replacement.
            continue
        pieces.append(text[cursor:span['start']])
        pieces.append(span['replacement'])
        cursor = span['end']
        replaced_to = span['end']
    pieces.append(text[cursor:])
    return ''.join(pieces)


if __name__ == "__main__":
    main()
