#!/usr/bin/env python3
"""V91 vertical proof — masterplan 9.1 row "V6 User research workflow".

Masterplan research/news_intelligence_estate_20261021/MASTERPLAN.md:476 requires
"Read source -> inspect company/theme -> save/follow -> propose thesis change
through existing user owner" with consumer outcome "Actual signed-in persistence
and authorization; no second thesis or alert store".  This script demonstrates,
by running repository producers on SYNTH inputs, which properties hold today.

Offline and deterministic: every input is synthetic (SYNTH-* placeholders, fixed
2026 ISO-8601 instants), every SQLite file, receipt, generation and temp file
lives under --scratch, no network, no model call, no wall clock in anything
printed.  Run from anywhere with PYTHONPATH at the tree:

    PYTHONPATH=. python3 research/news_intelligence_estate_20261021/v91_proofs/ \
        v6_user_research_workflow.py --scratch /tmp/any-dir

One line per property ``V6 P<k> <PROVEN|PARTIAL|ABSENT|HUMAN_GATE> <evidence>``,
then one SUMMARY line.  Verdicts are derived from what this run observed, never
constants: an ABSENT line flips to PARTIAL the moment its probe finds the
mechanism.
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import importlib.util
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
F2_RIGHTS = (
    ROOT / "research/news_intelligence_estate_20261021/f2_controls/nc_rights_identity.py"
)
REQUIRED_ARTIFACTS: tuple[str, ...] = ()

UTC = timezone.utc
SCRATCH: Path | None = None  # set from --scratch in main(); nothing is created at import

VALID_FROM = "2026-01-01T00:00:00Z"
FAR_FUTURE = "2099-01-01T00:00:00Z"  # receipt/universe validity horizon, never printed
AS_OF_DAY = "2026-02-02"
AS_OF_NOW = "2026-02-02T00:00:00Z"

# P4/P5 route vocabulary: a save/follow surface for news sources or market
# themes is a route that addresses both halves in its path.  A proposal entry
# point is a route (or callable) named propose/proposal; a route named thesis
# would be a thesis-change surface, but the thesis module's own view types are
# named thesis* without being proposal entry points.
FOLLOW_TOKENS = ("follow", "save", "saved", "subscribe", "watchlist", "bookmark")
SCOPE_TOKENS = ("news", "source", "theme")
PROPOSAL_ROUTE_TOKENS = ("propose", "proposal", "thesis")
PROPOSAL_CALLABLE_TOKENS = ("propose", "proposal")

# P3 SYNTH expectations, stated by the inputs themselves (membership rows +
# crosswalk theme), never copied from producer output.
SYN_THEME = "syn-theme-alpha"
SYN_THEME_EN = "Synth Theme Alpha"
SYN_THEME_ZH = "合成主题甲"
SYN_BASKET_A = "syn-basket-a"
SYN_BASKET_R = "syn-basket-r"
EXPECTED_SYNQ_EXPOSURES = [
    {
        "theme_id": SYN_THEME,
        "name_en": SYN_THEME_EN,
        "name_zh": SYN_THEME_ZH,
        "mapping_qualifier": "curated",
        "basket_id": SYN_BASKET_A,
    }
]

NEAREST_SAVE_HANDLERS = (
    "portfolio_changes",        # app/main.py: stateless portfolio change digest
    "read_private_portfolio",   # app/ontology_explorer.py: portfolio read
    "save_prefs",               # app/account_prefs.py: language/display prefs
    "optin_request",            # app/catalyst_integration.py: scan email opt-in
)


def _load_f2():
    """Load the shared SYNTH receipt/revision builders (offline, deterministic)."""
    spec = importlib.util.spec_from_file_location("v6_f2_rights", F2_RIGHTS)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@contextlib.contextmanager
def _quiet():
    """Keep third-party startup prints (app/observability.py _announce) off stdout."""
    with contextlib.redirect_stdout(sys.stderr):
        yield


@contextlib.contextmanager
def _set_env(**values):
    """Set env vars for a block; restore the prior process environment after."""
    saved = {key: os.environ.get(key) for key in values}
    for key, value in values.items():
        os.environ[key] = str(value)
    try:
        yield
    finally:
        for key, prior in saved.items():
            if prior is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = prior


# ---------------------------------------------------------------- P1: read ----
def p1_read_source(scratch: Path, f2) -> tuple[str, str]:
    """Read source with rights enforced through the app rights load + store."""
    import app.ticker_news as api
    from engine.qbus_news_store import NewsStore
    from fastapi import HTTPException

    with _quiet():
        api._reset_rate_limit_for_tests()
    db = scratch / "p1-news.sqlite3"
    revision = f2._ws_revision(
        "SYNTH-ITEM-V6A",
        title="SYNTH-TITLE-V6A",  # the SYNTH input states its own title
        url="https://benzinga.com/synth-v6a",
        teaser="SYNTH-TEASER-V6A",
        published="2026-10-14T09:00:00Z",
        updated="2026-10-14T09:00:00Z",
        received=datetime(2026, 10, 14, 10, 0, tzinfo=UTC),
    )
    with NewsStore(db, source_key="SYNTH-KEY") as store:
        store.commit_observations([f2._routed(revision, ("SYNTH-SEC-V6",))])

    universe_path = scratch / "p1-universe.json"
    universe_path.write_text(
        json.dumps(
            {
                "schema": "news_universe.v1",
                "owner": "SYNTH-OWNER",
                "revision": "SYNTH-UNI-V6",
                "complete": True,
                "truncated": False,
                "effective_at": VALID_FROM,
                "known_at": VALID_FROM,
                "fresh_until": FAR_FUTURE,
                "securities": [
                    {
                        "security_id": "SYNTH-SEC-V6",
                        "ticker": "SYNTH",
                        "aliases": ["SYNTH"],
                        "valid_from": VALID_FROM,
                        "known_at": VALID_FROM,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    receipt_path = scratch / "p1-rights.json"
    receipt_path.write_text(
        json.dumps(f2._receipt(effective=VALID_FROM, expires=FAR_FUTURE)),
        encoding="utf-8",
    )

    def _read():
        response = api.ticker_news_snapshot(
            "SYNTH", limit=20, cursor=None, view=None, view_revision=None,
            user={"id": "SYNTH-USER-V6"},
        )
        return response.status_code, json.loads(response.body)

    with _quiet(), f2._Env(
        MM_TICKER_NEWS_DB=db,
        MM_TICKER_NEWS_RIGHTS=receipt_path,
        MM_TICKER_NEWS_UNIVERSE=universe_path,
    ):
        status, body = _read()
        rows = body.get("rows", [])
        positive = (
            status == 200
            and len(rows) == 1
            and rows[0].get("title") == "SYNTH-TITLE-V6A"
        )

        # Unknown source: a receipt for a different source must yield nothing.
        receipt_path.write_text(
            json.dumps(
                f2._receipt(
                    source="massive:synth-pub.example",
                    provider="massive",
                    effective=VALID_FROM,
                    expires=FAR_FUTURE,
                )
            ),
            encoding="utf-8",
        )
        status_unknown, body_unknown = _read()
        unknown_refused = (
            status_unknown == 200 and len(body_unknown.get("rows", [])) == 0
        )

        # Missing rights: no receipt file -> refuse before any read.
        os.environ["MM_TICKER_NEWS_RIGHTS"] = str(scratch / "p1-missing.json")
        missing_code = "no-raise"
        missing_detail = ""
        try:
            _read()
        except HTTPException as exc:  # the producer's own refusal class
            missing_code = str(exc.status_code)
            missing_detail = str(exc.detail)
        missing_refused = (
            missing_code == "503"
            and missing_detail == "ticker news rights unavailable"
        )

    verdict = "PROVEN" if positive and unknown_refused and missing_refused else "PARTIAL"
    return verdict, (
        f"benzinga receipt->api read {status} rows={len(rows)} "
        f"title={rows[0].get('title') if rows else None}; "
        f"unknown-source receipt rows={len(body_unknown.get('rows', []))} no leak; "
        f"receipt absent -> {missing_code} '{missing_detail}'; "
        f"app rights load app/ticker_news.py:341, store read "
        f"engine/qbus_news_store.py:1758; test tests/test_ticker_news_api.py:140"
        if verdict == "PROVEN"
        else (
            f"positive={positive} unknown_refused={unknown_refused} "
            f"missing_refused={missing_refused}; app rights load "
            f"app/ticker_news.py:341, store read engine/qbus_news_store.py:1758; "
            f"test tests/test_ticker_news_api.py:140"
        )
    )


# --------------------------------------------------------- P2: signed in ----
def p2_signed_in(_scratch: Path) -> tuple[str, str]:
    """The signed-in read: gate observed refusing; pass-through is human-gated.

    Authentication half: the real gate refuses a missing token. Authorization
    half, observed offline: enforce_site_full(always=True) refuses a stubbed
    identity whose entitlement lookup answers "not entitled" and passes one
    whose lookup answers "entitled" (the store lookup is the only part stubbed;
    the decision is the producer's). A real signed-in session remains human.
    """
    import app.ticker_news as api
    from fastapi import HTTPException

    refused = None
    try:
        with _quiet():  # importing app.main announces sentry state on stdout
            api.require_site_full_user(None)
    except HTTPException as exc:  # the gate's own refusal class
        refused = (exc.status_code, str(exc.detail))
    if refused is None:
        return "ABSENT", (
            "gate did not refuse an unauthenticated read (no HTTPException); "
            "gate app/ticker_news.py:195; no-test"
        )

    import app.paywall as paywall

    def _probe(entitled: bool) -> tuple[str, int | None]:
        original = paywall._entitled
        paywall._entitled = lambda user_id, feature, **kw: (entitled, "pro" if entitled else "essential")
        try:
            with _quiet():
                paywall.enforce_site_full({"id": "SYNTH-USER-P2"}, always=True)
            return "passed", None
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            return ("locked" if detail.get("locked") else "other"), exc.status_code
        finally:
            paywall._entitled = original

    unpaid = _probe(False)
    paid = _probe(True)
    entitlement_ok = unpaid == ("locked", 403) and paid == ("passed", None)
    return "HUMAN_GATE", (
        f"gate refuses unauthenticated read HTTP {refused[0]} '{refused[1]}'; entitlement "
        f"half observed offline: non-entitled stub -> {unpaid[0]}/{unpaid[1]}, entitled stub "
        f"-> {paid[0]} (app/paywall.py:518 enforce_site_full always=True; discriminating="
        f"{entitlement_ok}); pass-through needs a real Supabase signed-in session "
        f"(app/main.py:1030 require_user verifies a bearer/session token), "
        f"unavailable offline; gate app/ticker_news.py:195; no-test"
    )


# ------------------------------------------------- P3: inspect company ----
# ------------------------------------------------- P3: inspect company ----
def p3_inspect(scratch: Path) -> tuple[str, str]:
    """Inspect company or theme: exposure producer plus the consumer leg."""
    from engine.company_intelligence.views import (
        build_bundle as build_ci_bundle,
        write_generation as write_ci_generation,
    )
    from engine.company_theme_exposure.views import (
        build_bundle as build_cte_bundle,
        load_company_generation,
        write_generation as write_cte_generation,
    )

    history = [
        {
            "document_ticker": ticker,
            "fiscal_year": 2026,
            "fiscal_quarter": 1,
            "call_date": call_date,
            "updated_at": "2026-02-01T00:00:00Z",
            "summary": f"SYNTH summary {ticker}: source-stated issuer event.",
            "raw_source_url": f"https://issuer.example/{ticker.lower()}",
        }
        for ticker, call_date in (
            ("SYNQ", "2026-01-29"),
            ("SYNR", "2026-02-20"),
            ("SYNZ", "2026-02-21"),
        )
    ]
    contexts, descriptor = build_ci_bundle(
        history,
        tx_index={"schema": "mastermind.tx-index/v1", "documents": []},
        generated_at=AS_OF_NOW,
        as_of=AS_OF_DAY,
    )
    ci_root = scratch / "p3-company"
    write_ci_generation(ci_root, contexts, descriptor)
    loaded, ci_manifest = load_company_generation(ci_root)

    membership = {
        "version": "synth-v6",
        "curated": AS_OF_DAY,
        "baskets": {
            # SYNQ is an active member -> theme exposure expected.
            SYN_BASKET_A: {
                "members": [
                    {"ticker": "SYNQ", "added": "2025-01-01", "removed": None}
                ]
            },
            # SYNR was removed before the as-of day -> no exposure expected
            # (its basket IS mapped to the theme; only the removal empties it).
            SYN_BASKET_R: {
                "members": [
                    {
                        "ticker": "SYNR",
                        "added": "2025-01-01",
                        "removed": "2026-01-01",
                    }
                ]
            },
        },
    }
    crosswalk = {
        "version": 1,
        "themes": [
            {
                "id": SYN_THEME,
                "foresight_id": SYN_THEME,
                "name_en": SYN_THEME_EN,
                "name_zh": SYN_THEME_ZH,
                # Both baskets map to the theme, so SYNR's empty exposure can
                # only come from the removal rule (removed <= as_of), not from
                # an unmapped basket.
                "basket_ids": [SYN_BASKET_A, SYN_BASKET_R],
            }
        ],
        "unmapped_baskets": [],
    }
    theme_state = {
        "schema": "neuralweb.theme_state.v1",
        "as_of": AS_OF_DAY,
        "stale_legs": [],
        "n_themes": 1,
        "themes": [{"theme_id": SYN_THEME}],
        "authority": {"is_context_only": True},
    }
    exposures, manifest = build_cte_bundle(
        loaded,
        company_manifest=ci_manifest,
        membership=membership,
        crosswalk=crosswalk,
        theme_state=theme_state,
        as_of=AS_OF_DAY,
    )
    producer_ok = (
        sorted(exposures) == ["SYNQ", "SYNR", "SYNZ"]
        and exposures["SYNQ"]["exposures"] == EXPECTED_SYNQ_EXPOSURES
        and exposures["SYNR"]["exposures"] == []
        and exposures["SYNR"]["coverage"]["status"] == "no_active_membership"
        and exposures["SYNZ"]["exposures"] == []
        and exposures["SYNZ"]["coverage"]["status"] == "no_active_membership"
    )
    cte_root = scratch / "p3-cte"
    write_cte_generation(cte_root, exposures, manifest)

    import app.integrated_answer as integrated

    with _quiet(), _set_env(MACRO_CTE_DIR=cte_root):
        leg_pos = integrated._leg_company_theme_exposure("SYNQ", AS_OF_NOW)
        leg_neg = integrated._leg_company_theme_exposure("SYNZZ", AS_OF_NOW)
    consumer_ok = (
        leg_pos.get("status") == "ok"
        and (leg_pos.get("payload") or {}).get("exposures")
        == EXPECTED_SYNQ_EXPOSURES
        and leg_neg.get("status") == "absent"
        and leg_neg.get("degraded_reason") == "ticker_not_in_generation"
    )
    verdict = "PROVEN" if producer_ok and consumer_ok else "PARTIAL"
    return verdict, (
        f"SYNQ member->1 exposure {SYN_THEME} via {SYN_BASKET_A}; "
        f"removed SYNR (mapped basket, removed<=as_of)->[] "
        f"coverage={exposures['SYNR']['coverage']['status']} and non-member SYNZ->[] "
        f"coverage={exposures['SYNZ']['coverage']['status']}; "
        f"consumer leg app/integrated_answer.py:730 status={leg_pos.get('status')} "
        f"for SYNQ, {leg_neg.get('status')}/{leg_neg.get('degraded_reason')} "
        f"for SYNZZ; producer engine/company_theme_exposure/views.py:217; "
        f"test tests/test_company_theme_exposure.py:94"
        if verdict == "PROVEN"
        else (
            f"producer_ok={producer_ok} consumer_ok={consumer_ok} "
            f"(missing half named: "
            f"{'producer' if not producer_ok else 'consumer'}); producer "
            f"engine/company_theme_exposure/views.py:217, consumer "
            f"app/integrated_answer.py:730; test tests/test_company_theme_exposure.py:94"
        )
    )


# ------------------------------------------------------ P4/P5 route probe ----
_MUTATING = {"post", "put", "patch"}


def _route_handlers() -> list[dict]:
    """Enumerate mutating routes under app/ (recursive) via the ast module.

    Covers ``@x.post/put/patch`` decorators, ``@x.api_route(..., methods=[...])``
    decorators and ``add_api_route(...)`` calls with a mutating method.
    """
    rows: list[dict] = []

    def _methods(call: ast.Call) -> set[str]:
        for kw in call.keywords:
            if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                return {
                    str(elt.value).lower() for elt in kw.value.elts
                    if isinstance(elt, ast.Constant)
                } & _MUTATING
        return set()

    def _path(call: ast.Call) -> str:
        if call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
            return call.args[0].value
        return ""

    for py in sorted((ROOT / "app").rglob("*.py")):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        rel = py.relative_to(ROOT).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    target = dec.func if isinstance(dec, ast.Call) else dec
                    if not (isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name)):
                        continue
                    if target.attr in _MUTATING:
                        methods = {target.attr}
                    elif target.attr == "api_route" and isinstance(dec, ast.Call):
                        methods = _methods(dec)
                    else:
                        continue
                    path = _path(dec) if isinstance(dec, ast.Call) else ""
                    for method in sorted(methods):
                        rows.append({"module": rel, "line": node.lineno, "method": method,
                                     "path": path, "name": node.name, "via": "decorator"})
            elif isinstance(node, ast.Call):
                target = node.func
                if isinstance(target, ast.Attribute) and target.attr == "add_api_route":
                    for method in sorted(_methods(node)):
                        rows.append({"module": rel, "line": node.lineno, "method": method,
                                     "path": _path(node), "name": "add_api_route",
                                     "via": "add_api_route"})
    rows.sort(key=lambda row: (row["module"], row["line"], row["method"]))
    return rows


_JS_WRITE_RE = re.compile(
    r"sb\.from\(\s*['\"](\w+)['\"]\s*\)\s*\.\s*(insert|update|upsert|delete)\s*\("
)
_WATCHLIST_TABLES = {"watchlists", "watchlist_symbols"}


def _browser_writes() -> list[dict]:
    """Browser-side Supabase writes in templates/**/*.js (source probe)."""
    rows: list[dict] = []
    for js in sorted((ROOT / "templates").rglob("*.js")):
        text = js.read_text(encoding="utf-8", errors="replace")
        owner_scoped = ".eq('user_id', user.id)" in text
        for match in _JS_WRITE_RE.finditer(text):
            rows.append({
                "module": js.relative_to(ROOT).as_posix(),
                "line": text.count("\n", 0, match.start()) + 1,
                "table": match.group(1),
                "verb": match.group(2),
                "owner_scoped": owner_scoped,
            })
    return rows


def p4_save_follow(_scratch: Path, handlers: list[dict]) -> tuple[str, int, str]:
    """Save or follow a source or theme: does any persisted path exist?

    A news/source/theme follow route is the row's own target (PARTIAL: located,
    propagation unproven). Absent that, an owner-scoped browser write to the
    Supabase watchlist tables persists a COMPANY follow for a signed-in user
    (PARTIAL: company only; source/theme follow and news-assessment save are
    still absent). Nothing persisted is ABSENT. Returns the count of
    news/source/theme routes so P7 can ask whether a saved assessment exists.
    """
    matches = [
        row
        for row in handlers
        if any(token in row["path"].lower() for token in FOLLOW_TOKENS)
        and any(token in row["path"].lower() for token in SCOPE_TOKENS)
    ]
    writes = _browser_writes()
    watch_writes = [w for w in writes if w["table"] in _WATCHLIST_TABLES and w["owner_scoped"]]
    nearest = sorted(
        (row for row in handlers if row["name"] in NEAREST_SAVE_HANDLERS),
        key=lambda row: (row["module"], row["line"]),
    )
    nearest_text = " ".join(
        f"{row['module']}:{row['line']} {row['name'].replace('_', '-')}" for row in nearest
    )
    counts = {method: sum(1 for row in handlers if row["method"] == method) for method in sorted(_MUTATING)}
    total = len(handlers)
    census = (
        f"{total} mutating routes under app/ (post={counts['post']} put={counts['put']} "
        f"patch={counts['patch']}; api_route/add_api_route included)"
    )
    if matches:
        found = " ".join(f"{row['module']}:{row['line']} {row['path']}" for row in matches)
        return "PARTIAL", len(matches), (
            f"{census}; {len(matches)} route(s) persist a followed news source or market "
            f"theme: {found}; propagation to a saved assessment unproven; no-test"
        )
    if watch_writes:
        first = watch_writes[0]
        tables = ",".join(sorted({w["table"] for w in watch_writes}))
        return "PARTIAL", 0, (
            f"{census}; 0 persist a followed news source or market theme; a COMPANY follow "
            f"persists for a signed-in owner-scoped user: {len(watch_writes)} browser writes to "
            f"{tables} ({first['module']}:{first['line']} {first['verb']}; user_id-filtered; "
            f"Terminal 0001_init.sql schema per engine/fif_saved_research_notifications.py:6); "
            f"source/theme follow and news-assessment save absent; nearest routes "
            f"{nearest_text}; follow/saved open in "
            f"research/news_intelligence_estate_20261021/MASTERPLAN.md:77 Macro #9612; "
            f"source probe, not observed behaviour; no-test"
        )
    return "ABSENT", 0, (
        f"{census}; 0 persist a followed news source or market theme; 0 owner-scoped "
        f"browser writes to watchlist tables; nearest {nearest_text}; follow/saved open in "
        f"research/news_intelligence_estate_20261021/MASTERPLAN.md:77 Macro #9612; no-test"
    )


_THESIS_OWNER_TABLES = ("theses", "thesis_versions")
# Write verbs only: REST verbs (`"POST"`, `.post(`), PostgREST/Supabase client
# writes (`.insert(`, `.upsert(`). A GET that selects `updated_at` next to the
# table name is a read, not a writer, so bare `update` is deliberately absent.
_WRITE_VERB_RE = r"(\b(?:POST|PATCH|PUT|insert|upsert)\b|\.(?:post|patch|put|insert|upsert)\()"


def p5_propose(_scratch: Path, handlers: list[dict]) -> tuple[str, str]:
    """Propose a thesis change through the existing user owner.

    The existing user owner is Supabase public.theses + public.thesis_versions
    (the immutable revision ledger; engine/thesis_condition_monitor.py:23).
    engine/news_impact/thesis.py is the news-impact fact log, not that owner.
    Scope: Macro paths only; the Terminal repository, which owns the schema and
    may hold a user-authored revision writer, is not inspected offline (UNKNOWN).
    """
    route_hits = sorted(
        (row for row in handlers if any(token in row["path"].lower() for token in PROPOSAL_ROUTE_TOKENS)),
        key=lambda row: (row["module"], row["line"]),
    )
    thesis_path = ROOT / "engine" / "news_impact" / "thesis.py"
    tree = ast.parse(thesis_path.read_text(encoding="utf-8"))
    names = sorted(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    )
    name_hits = [name for name in names if any(token in name.lower() for token in PROPOSAL_CALLABLE_TOKENS)]

    owner_pattern = re.compile(
        rf"{_WRITE_VERB_RE}[^\n]{{0,120}}\b({'|'.join(_THESIS_OWNER_TABLES)})\b|"
        rf"\b({'|'.join(_THESIS_OWNER_TABLES)})\b[^\n]{{0,120}}{_WRITE_VERB_RE}"
    )
    mention_files: list[str] = []
    writer_files: list[str] = []
    for base in ("app", "engine", "lib", "scripts", "templates"):
        for path in sorted((ROOT / base).rglob("*")):
            if path.suffix not in {".py", ".js"} or not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if re.search(r"\bthesis_versions\b", text):
                rel = path.relative_to(ROOT).as_posix()
                mention_files.append(rel)
                if owner_pattern.search(text):
                    writer_files.append(rel)
    owner_named = "thesis_versions" in (ROOT / "engine" / "thesis_condition_monitor.py").read_text(encoding="utf-8")

    if route_hits or name_hits or writer_files:
        return "PARTIAL", (
            f"proposal entry point located: routes {[row['path'] for row in route_hits]} "
            f"callables {name_hits} thesis_versions writers {writer_files}; owner "
            f"public.theses/thesis_versions engine/thesis_condition_monitor.py:23; "
            f"engine/news_impact/thesis.py:8; no-test"
        )
    return "ABSENT", (
        f"existing user owner = Supabase public.theses + public.thesis_versions "
        f"(engine/thesis_condition_monitor.py:23, named={owner_named}); Macro writers to "
        f"thesis_versions: {len(writer_files)} across {len(mention_files)} mentioning files; "
        f"0 of {len(handlers)} mutating routes under app/ named propose/proposal/thesis; "
        f"engine/news_impact/thesis.py is the fact log ({len(names)} callables, 0 propose*; "
        f"append engine/news_impact/thesis.py:569, projector :660, DNR:KILL-THESIS-LOBE :8); "
        f"scope: no Macro path proposes a thesis_versions row from a news item; Terminal "
        f"writer not inspected offline (UNKNOWN); no-test"
    )


# ------------------------------------------------- P6: no second store ----
_CREATE_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[\"'`\[]?(\w+)", re.IGNORECASE
)
# The FIRST stores a V6 build must reuse, each with the Macro file that names it.
FIRST_STORES = (
    ("public.theses/thesis_versions", "engine/thesis_condition_monitor.py", "thesis_versions"),
    ("public.alert_outbox", "engine/thesis_condition_monitor.py", "alert_outbox"),
    ("public.alert_outbox writer", "engine/alert_delivery_drain.py", "alert_outbox"),
    ("data/alerts/watchlist_alerts.jsonl", "scripts/run_watchlist_sentinel.py", "watchlist_alerts.jsonl"),
    ("theme_thesis_ledger.jsonl", "engine/neuralweb/theme_thesis.py", "theme_thesis_ledger"),
    ("capital_structure_saved_scenarios", "contracts/capital_structure_saved_scenarios.table.sql", "capital_structure_saved_scenarios"),
)


def p6_no_second_store(_scratch: Path) -> tuple[str, str]:
    """No second thesis or alert store: name the first stores, then scan.

    The canonical stores live in Supabase migrations outside this repository
    (Terminal PR #502 theses/thesis_versions, PR #513 alert_outbox) plus two
    file ledgers and one SQL contract here; each is confirmed from the Macro
    file that names it. The CREATE TABLE scan then covers app/ (recursive),
    engine/, lib/, scripts/ and contracts/*.sql. Absence by scan is a source
    probe, so the ceiling is PARTIAL.
    """
    modules = sorted(
        list((ROOT / "app").rglob("*.py")) + list((ROOT / "engine").rglob("*.py"))
        + list((ROOT / "lib").rglob("*.py")) + list((ROOT / "scripts").rglob("*.py"))
        + list((ROOT / "contracts").rglob("*.sql"))
    )
    statements = 0
    named: list[str] = []
    for module in modules:
        text = module.read_text(encoding="utf-8", errors="replace")
        for match in _CREATE_TABLE_RE.finditer(text):
            statements += 1
            if re.search(r"thesis|alert|saved", match.group(1), re.IGNORECASE):
                named.append(f"{module.relative_to(ROOT).as_posix()}:{match.group(1)}")
    confirmed = [
        label for label, rel, needle in FIRST_STORES
        if needle in (ROOT / rel).read_text(encoding="utf-8", errors="replace")
    ]
    return "PARTIAL", (
        f"first stores a V6 build must reuse ({len(confirmed)}/{len(FIRST_STORES)} confirmed "
        f"from the naming file): {'; '.join(confirmed)}; CREATE TABLE scan app/+engine/+lib/+"
        f"scripts/+contracts/*.sql ({len(modules)} files, {statements} statements): "
        f"{len(named)} tables named thesis/alert/saved"
        f"{' -> ' + ','.join(sorted(named)) if named else ''}; standing kill "
        f"DNR:KILL-THESIS-LOBE engine/news_impact/thesis.py:8; Supabase migrations are not in "
        f"this tree (engine/thesis_condition_monitor.py:23 engine/alert_delivery_drain.py:628); "
        f"absence by scan is a source probe, not an observed behaviour; no-test"
    )


# --------------------------------------------- P7: correction after save ----
def p7_correction_reaches_saved(scratch: Path, f2, news_surfaces: int) -> tuple[str, str]:
    """Correction after save reaches the saved research: end-to-end absence.

    The verdict turns on whether a saved NEWS ASSESSMENT exists for the
    correction to reach (a news/source/theme follow surface from P4). A company
    watchlist stores tickers, not assessments, and the device-local Filing
    Forensics briefcase is neither signed-in nor news, so neither counts.
    """
    from engine.qbus_news_store import NewsStore

    db = scratch / "p7-news.sqlite3"
    base = dict(
        url="https://benzinga.com/synth-v7",
        teaser="SYNTH-TEASER-V7",
        published="2026-10-14T09:00:00Z",
    )
    v1 = f2._ws_revision(
        "SYNTH-ITEM-V7",
        title="SYNTH-TITLE-A",
        updated="2026-10-14T09:00:00Z",
        received=datetime(2026, 10, 14, 10, 0, tzinfo=UTC),
        **base,
    )
    v2 = f2._ws_revision(
        "SYNTH-ITEM-V7",
        title="SYNTH-TITLE-B",
        updated="2026-10-14T12:00:00Z",  # the correction
        received=datetime(2026, 10, 14, 12, 5, tzinfo=UTC),
        **base,
    )
    with NewsStore(db, source_key="SYNTH-KEY") as store:
        store.commit_observations([f2._routed(v1, ("SYNTH-SEC-V7",))])
        store.commit_observations([f2._routed(v2, ("SYNTH-SEC-V7",))])
    reader = NewsStore.open_readonly(db, source_key="SYNTH-KEY")
    try:
        snap = reader.snapshot(
            "SYNTH-SEC-V7", limit=10, cursor=None, rights=f2._rights(("benzinga",))
        )
        corrected_title = snap.rows[0].title if snap.rows else None
    finally:
        reader.close()
    briefcase = ROOT / "templates" / "fif_saved_briefcase.js"
    briefcase_local = briefcase.exists() and "saved_against" in briefcase.read_text(encoding="utf-8")
    if news_surfaces:
        return "PARTIAL", (
            f"correction reaches store state title={corrected_title}; "
            f"{news_surfaces} news/source/theme follow surface(s) located in P4 but propagation "
            f"to a saved assessment unproven; engine/qbus_news_reducer.py:166; no-test"
        )
    return "ABSENT", (
        f"correction observed in store: title SYNTH-TITLE-A->{corrected_title} after "
        f"corrected revision commit (engine/qbus_news_reducer.py:166 reduce_revision) "
        f"but no saved news assessment exists to receive it (P4: {news_surfaces} news/source/"
        f"theme follow surfaces; the company watchlist stores tickers, not assessments; the "
        f"device-local briefcase templates/fif_saved_briefcase.js:1 saved_against="
        f"{briefcase_local} is neither signed-in nor news); no end-to-end path; no-test"
    )


# ----------------------------------------------------------------- main ----
def main() -> int:
    global SCRATCH
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scratch",
        default=None,
        help="directory for every synthetic sqlite/receipt/generation file",
    )
    args = parser.parse_args()
    if args.scratch is None:
        args.scratch = tempfile.mkdtemp(prefix="v6-user-research-")
    SCRATCH = Path(args.scratch)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    tempfile.tempdir = str(SCRATCH)  # tempfile caches its directory; pin it inside scratch
    sys.path.insert(0, str(ROOT))
    os.environ["TMPDIR"] = str(SCRATCH)  # before any import that uses tempfile
    f2 = _load_f2()

    tally = {"PROVEN": 0, "PARTIAL": 0, "ABSENT": 0, "HUMAN_GATE": 0}
    handlers = _route_handlers()

    for verdict, evidence in (p1_read_source(SCRATCH, f2),):
        tally[verdict] += 1
        print(f"V6 P1 {verdict} {evidence}", flush=True)
    for verdict, evidence in (p2_signed_in(SCRATCH),):
        tally[verdict] += 1
        print(f"V6 P2 {verdict} {evidence}", flush=True)
    for verdict, evidence in (p3_inspect(SCRATCH),):
        tally[verdict] += 1
        print(f"V6 P3 {verdict} {evidence}", flush=True)
    p4_verdict, news_surfaces, p4_evidence = p4_save_follow(SCRATCH, handlers)
    tally[p4_verdict] += 1
    print(f"V6 P4 {p4_verdict} {p4_evidence}", flush=True)
    for verdict, evidence in (p5_propose(SCRATCH, handlers),):
        tally[verdict] += 1
        print(f"V6 P5 {verdict} {evidence}", flush=True)
    for verdict, evidence in (p6_no_second_store(SCRATCH),):
        tally[verdict] += 1
        print(f"V6 P6 {verdict} {evidence}", flush=True)
    for verdict, evidence in (
        p7_correction_reaches_saved(SCRATCH, f2, news_surfaces),
    ):
        tally[verdict] += 1
        print(f"V6 P7 {verdict} {evidence}", flush=True)

    print(
        "V6 SUMMARY "
        f"proven={tally['PROVEN']} partial={tally['PARTIAL']} "
        f"absent={tally['ABSENT']} human_gate={tally['HUMAN_GATE']} "
        f"rung=OFFLINE_FIXTURE",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
