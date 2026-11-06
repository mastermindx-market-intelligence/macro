"""FIF P2 fixture-backed browser evidence capture wrapper.

WHY THIS EXISTS
---------------
The P2 UI PR must carry POPULATED-state crops, but the product's populated
states live behind authenticated private APIs. This wrapper wraps the
repository's existing page-evidence capture tool (``scripts/capture_page_evidence.py``)
so a real Chromium, pointed at the capture tool's own local static server for
``site/``, receives its ``/api/forensics/*`` answers from the REAL FIF kernel
running in-process in golden mode (AAPL golden) through ``app.forensics.router``
— never from hand-written JSON.

HOW IT WORKS
------------
* The page is loaded from ``http://fif-evidence.localhost:<port>/`` instead of
  ``http://127.0.0.1:<port>/``. Same scheme, port, path and query — only the
  host is rewritten, so the page's ``IS_LOOPBACK`` regex is false and the page
  takes its PRODUCTION data path (``/api/forensics/state``, health,
  attested-history, financial query/statements POSTs). Chromium resolves
  ``*.localhost`` to the loopback interface, so the capture tool's static
  server still serves the document and assets.
* A Playwright ``context.route("**/*", ...)`` handler installed by this wrapper
  (through proxies around the real driver) classifies every request:
  local ``/api/forensics/*`` is forwarded to an in-process
  ``fastapi.testclient.TestClient`` over ``FastAPI()`` with
  ``app.forensics.router`` included; other local ``/api/*`` is aborted; other
  local paths continue to the static server; every other host is aborted
  (``blockedbyclient``) and its name recorded.
* Populated mode satisfies the entitlement with the repository's existing
  router-test dependency override
  (``app.dependency_overrides[forensics_api.require_site_full_user]``). No
  browser cookie, localStorage session, token or Authorization header is ever
  synthesized. Anonymous mode runs the REAL ``require_site_full_user`` with no
  Authorization header and records the real 401.
* Populated mode first builds the private state into a TEMP root (outside the
  repo) that symlinks ONLY the six read-only kernel inputs, calls
  ``scripts.build_fundamental_forensics.compose_state``, and copies the
  produced gzip object to the tree's gitignored
  ``data/fundamental_forensics/private/state.json.gz``.
* Unavailable mode (entitled through the same override) sets the tree's local
  private state aside for the run, so the REAL loader finds no object: the REAL
  ``/api/forensics/state`` answers 503 and the REAL health route reports
  ``unavailable``. Both answers are verified before any capture.
* Degraded mode builds the golden state into a temp root WITHOUT installing it,
  primes the REAL loader's in-process cache through a temporary ``LocalStore``
  (``RESEARCH_LOCAL_STORE``, removed again before capture), then serves with the
  store unreachable: the REAL loader answers ``last_good`` and the REAL health
  route reports ``degraded`` (``LAST_GOOD_STALE``; ``--generated-at`` must be
  older than the engine's freshness budget). Verified before any capture.
* ``--force-state NAME:[data-ff-evidence-interaction=<interaction>]`` never
  writes that attribute: the page proxy intercepts the capture tool's attribute
  force and performs a REAL browser interaction instead (``drawer_open`` = a
  pointer click on the primary-finding control; ``tab_keys`` = Tab presses to
  the selected tab, then ArrowRight; ``drawer_trap`` = Tab presses to the
  primary-finding control, Enter, then Tab through the open drawer). The force
  is reported applied only when a post-interaction DOM probe confirms it, and
  every receipt lands in ``interactions.json``.
* A43 Z1 repair: after the drawer_trap trail (and after that cell's screenshot,
  which must still show the open drawer) a real Escape press closes the drawer
  and the receipt records ``facts.closed`` — ``focus_restored`` is True only
  when the drawer is closed AND focus returned to the product's restore target
  (the trigger, or the selected finding's own button — see the probe script),
  and it is folded into ``verified``. Keyboard receipts also carry
  ``facts.disabled_controls``, the None-state record of ``#ff-export-btn`` /
  ``#ff-saved-save`` (real ``disabled`` property, per-locale visible text,
  labels, tip); populated-set rest cells get the same record as a
  ``disabled_controls`` receipt kind in ``interactions.json``.
* An interaction cell whose screenshot would be taken while the page's modal is
  open (``body.ff-modal-open``) is captured as the first VIEWPORT instead of the
  full page: Chromium's full-page capture resizes the surface and drops or
  under-paints the fixed modal layer, so a full-page PNG of an open drawer can
  show no drawer at all. The receipt records the scope in ``capture``; every
  other cell keeps the capture tool's full-page shot unchanged.
* Every exchange is appended to ``network_log.json`` (metadata + digests only;
  response bodies are never stored), and ``--fold-selector`` measures named
  selectors' fold position at screenshot time into ``fold_measurement.json``.
* Render guard (P2 r3 repair d): before any browser import/launch the served
  page must be a fresh render of this tree's template — any unrendered Jinja
  marker, or any literal template ``id="ff-…"`` missing from the served html,
  is refused with exit code 5 and the render/restore commands on stderr.

USAGE
-----
    python3 -m tests.tools.fif_p2_evidence_capture --mode populated \
        --out-dir /tmp/fif-evidence --as-of 2026-10-12T00:00:00Z \
        --generated-at 2026-10-12T00:00:00Z \
        --fold-selector nav=nav.site-nav --fold-selector lead=.ff-context-card

This module lives under ``tests/tools/`` on purpose: it is evidence tooling,
never product code. It originates no signal, score or escalation (A7).

SEAT FENCES (P2 evidence ruling, 2026-10-12)
--------------------------------------------
1. Every target origin must be loopback or ``*.localhost``: a non-local
   ``--base-url`` or absolute ``--route`` makes ``main`` exit non-zero BEFORE the
   env scrub, the kernel build or any capture (``refuse_non_local_targets``).
2. ``app/`` and ``engine/`` never import this module (asserted by its unit test).
3. The ``require_site_full_user`` override is installed only on the
   ``FastAPI()`` instance ``build_router_app`` creates for this run's TestClient,
   never on a module-level app a real server could share.
4. Populated manifests state ``ENTITLED_CROPS_FENCE`` verbatim; the PR body and
   DEVIATIONS repeat it. A45 entitled-browser proof stays with A0.
5. Environment variables are recorded by NAME only, never by value.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import ipaddress
import json
import os
import re
import shlex
import shutil
import sys
import tempfile
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence
from urllib.parse import urlparse, urlunparse

TOOL_MODULE_REF = "tests/tools/fif_p2_evidence_capture.py"
WRAPPED_MODULE_REF = "scripts/capture_page_evidence.py"
KERNEL_BUILDER_REF = "scripts.build_fundamental_forensics.compose_state"

# The page must NOT see a loopback hostname, or it reads the builder artifact
# instead of the production API. *.localhost resolves to loopback in Chromium
# while failing the page's IS_LOOPBACK regex.
EVIDENCE_HOST = "fif-evidence.localhost"
SOURCE_HOST = "127.0.0.1"
LOCAL_HOSTS = frozenset({EVIDENCE_HOST, SOURCE_HOST})
HOST_REWRITE = "127.0.0.1 -> fif-evidence.localhost"
# Seat fence 4: stated verbatim in every populated manifest, the PR body and DEVIATIONS.
ENTITLED_CROPS_FENCE = (
    "entitled crops = fixture-backed golden, local, entitlement satisfied by test "
    "dependency override; not production entitlement proof"
)

FORENSICS_PREFIX = "/api/forensics/"
FINANCIAL_POST_PREFIX = "/api/forensics/v1/financial/"
FORWARDED_REQUEST_HEADERS = ("content-type", "accept", "authorization")
DROPPED_RESPONSE_HEADERS = ("content-length", "content-encoding", "transfer-encoding")

CATEGORY_FORENSICS_FORWARDED = "forensics_forwarded"
CATEGORY_OTHER_LOCAL_API_ABORTED = "other_local_api_aborted"
CATEGORY_STATIC_CONTINUED = "static_continued"
CATEGORY_EXTERNAL_ABORTED = "external_aborted"
CATEGORY_FORENSICS_FORWARD_FAILED = "forensics_forward_failed"

# Names only, never values: the scrub exists so the in-process kernel answers
# from the golden corpus and the local state copy, not from any live store.
SCRUB_ENV_PREFIXES = ("R2_", "FF_ATTESTED_", "AWS_")
SCRUB_ENV_NAMES = ("RESEARCH_LOCAL_STORE", "FIF_FINANCIAL_DATASET_MODE")

# Exactly the six read-only kernel inputs symlinked into the temp build root.
# The committed issuer master is the builder's entity-id join
# (ISSUER_MASTER_RELATIVE); without it every company carries entity_id=None
# and no saved view can ever pass the page's issuer-identity check.
KERNEL_INPUTS: tuple[str, ...] = (
    "data/edgar/statements_quarterly.parquet",
    "data/edgar/statements.parquet",
    "data/edgar/fundamentals.parquet",
    "data/universe/membership.parquet",
    "data/breadth/ticker_sectors.parquet",
    "data/reference/issuer_master.parquet",
)
# A REAL directory in the temp root (never a symlink): the builder writes the
# public summary + private state under here, and none of that may reach through
# a symlink into the tree's tracked files.
KERNEL_OUTPUT_DIR = "data/fundamental_forensics"
LOCAL_STATE_RELATIVE = "data/fundamental_forensics/private/state.json.gz"

MODE_POPULATED = "populated"
MODE_ANONYMOUS = "anonymous"
MODE_UNAVAILABLE = "unavailable"
MODE_DEGRADED = "degraded"
ENTITLED_MODES = (MODE_POPULATED, MODE_UNAVAILABLE, MODE_DEGRADED)
ALL_MODES = (MODE_POPULATED, MODE_ANONYMOUS, MODE_UNAVAILABLE, MODE_DEGRADED)

POPULATED_LABEL = "fixture-backed (golden), local"
ANONYMOUS_LABEL = "anonymous-unavailable, local (real 401 from require_site_full_user)"
POPULATED_ACCESS = "fixture_backed_golden_local"
POPULATED_HONESTY = (
    "fixture-backed (golden), local: private-API responses produced in-process by the "
    "real FIF kernel in golden mode (AAPL golden) through app.forensics.router; "
    "entitlement satisfied by the repository's router-test dependency override, no "
    "credential entered, stored or synthesized; not a production capture"
)
POPULATED_ENTITLEMENT = (
    'app.dependency_overrides[app.forensics.require_site_full_user] = lambda: {"id": '
    '"fif-evidence-local"} — the repository router-test convention; no credential'
)
ANONYMOUS_ENTITLEMENT = (
    "none: the real app.forensics.require_site_full_user ran with no Authorization "
    "header and produced the real 401"
)

UNAVAILABLE_LABEL = (
    "entitled-unavailable, local (real 503 from /api/forensics/state: no private "
    "state object reachable)"
)
DEGRADED_LABEL = (
    "fixture-backed (golden), local, served as last-good after the private store "
    "became unreachable (real health: degraded)"
)
UNAVAILABLE_ACCESS = "entitled_test_override_state_missing_local"
DEGRADED_ACCESS = "fixture_backed_golden_last_good_local"
UNAVAILABLE_HONESTY = (
    "entitled-unavailable, local: entitlement satisfied by the repository's router-test "
    "dependency override, no credential entered, stored or synthesized; the tree's local "
    "private state was set aside and no private store was reachable, so the real "
    "/api/forensics/state answered 503 and the real health route reported unavailable; "
    "not a production capture"
)
DEGRADED_HONESTY = (
    "fixture-backed (golden), local, last-good: the real FIF kernel built the golden "
    "state, the real private-state loader cached it from a temporary local store that "
    "was then removed, so every capture request was served from the loader's last-good "
    "copy and the real health route reported degraded; entitlement satisfied by the "
    "repository's router-test dependency override, no credential entered, stored or "
    "synthesized; not a production capture"
)
MODE_LABELS = {
    MODE_POPULATED: POPULATED_LABEL,
    MODE_ANONYMOUS: ANONYMOUS_LABEL,
    MODE_UNAVAILABLE: UNAVAILABLE_LABEL,
    MODE_DEGRADED: DEGRADED_LABEL,
}
MODE_ACCESS = {
    MODE_POPULATED: POPULATED_ACCESS,
    MODE_ANONYMOUS: "anonymous",
    MODE_UNAVAILABLE: UNAVAILABLE_ACCESS,
    MODE_DEGRADED: DEGRADED_ACCESS,
}
MODE_HONESTY = {
    MODE_POPULATED: POPULATED_HONESTY,
    MODE_UNAVAILABLE: UNAVAILABLE_HONESTY,
    MODE_DEGRADED: DEGRADED_HONESTY,
}
CELL_ID_ACCESS_NOTE = (
    "cell_id strings carry the capture tool's fixed 'anonymous' access token; the "
    "per-state 'access' field and axes.access carry this run's real access mode"
)
DEGRADED_STATE_DELIVERY = (
    "real private-state loader last-good cache (temporary local store removed after "
    "priming); never installed in the tree"
)
# Mirrors engine.fundamental_forensics.health.FRESHNESS_BUDGET_SECONDS (pinned equal
# by the unit test) so the degraded clock pre-check runs before any import or scrub.
FRESHNESS_BUDGET_SECONDS = 4 * 24 * 60 * 60

INTERACTION_ATTRIBUTE = "data-ff-evidence-interaction"
INTERACTION_DRAWER_OPEN = "drawer_open"
INTERACTION_TAB_KEYS = "tab_keys"
INTERACTION_DRAWER_TRAP = "drawer_trap"
INTERACTION_SAVED_RESTORE_PINNED = "saved_restore_pinned"
INTERACTION_SAVED_OPEN_UNAVAILABLE = "saved_open_unavailable"
INTERACTION_SAVED_WRITE_FAILURE = "saved_write_failure"
# A43 Z1 repair: the disabled/unavailable control-text probe. NOT a force-state
# interaction — a receipt kind this wrapper appends itself for rest cells; it
# never enters ``_INTERACTIONS`` (``run_interaction`` refuses it as a force).
INTERACTION_DISABLED_CONTROLS = "disabled_controls"
# The two keyboard interactions whose receipts carry the None-state probe as
# ``facts.disabled_controls`` (keeping keyboard interactions.json at 24 rows).
KEYBOARD_INTERACTIONS = (INTERACTION_TAB_KEYS, INTERACTION_DRAWER_TRAP)
# templates/fundamental_forensics.html.j2:87-90 and :119-122: the two disabled
# desk controls masterplan row A43 names.
DISABLED_CONTROL_SELECTORS = ("#ff-export-btn", "#ff-saved-save")
DISABLED_CONTROLS_PROBE_INPUT = (
    "probe: rest-state disabled/unavailable record for #ff-export-btn and "
    "#ff-saved-save (real disabled property, per-locale visible text, "
    "data-label-en/zh, data-tip-<locale>, aria-disabled)"
)
INTERACTION_INPUTS = {
    INTERACTION_DRAWER_OPEN: "pointer: real click on [data-open-primary-finding]",
    INTERACTION_TAB_KEYS: "keyboard: real Tab presses to the selected tab, then ArrowRight",
    INTERACTION_DRAWER_TRAP: (
        "keyboard: real Tab presses to [data-open-primary-finding], Enter, then Tab "
        "through the open drawer"
    ),
    INTERACTION_SAVED_RESTORE_PINNED: (
        "select: real #ff-saved-select change to the pinned seed row "
        "(CDEFGHIJKLMNOPQRSTUVWX)"
    ),
    INTERACTION_SAVED_OPEN_UNAVAILABLE: (
        "select: real #ff-saved-select change to the drift seed row "
        "(EFGHIJKLMNOPQRSTUVWXYZ)"
    ),
    INTERACTION_SAVED_WRITE_FAILURE: (
        "Restore the pinned saved view, make this capture page's browser refuse the "
        "next write to the saved-views key (localStorage.setItem raises "
        "QuotaExceededError for that one key only), type the name 'Apple write check' "
        "and click Rename on the restored view. Shows the write-failure notice; the "
        "stored saved views and the row's name are unchanged."
    ),
}

# X2-s r1 (H2): the saved-views desk selectors and the seed rows the two
# interactions drive (evidence_briefcase_seed.json rows 1 and 3).
SAVED_SELECT_SELECTOR = "#ff-saved-select"
SAVED_BADGE_SELECTOR = "#ff-saved-badge"
SAVED_NOTICE_SELECTOR = "#ff-saved-notice"
SAVED_NAME_SELECTOR = "#ff-saved-name"
# X2-s r2 (C4): the write-failure capture drives Rename on the restored row.
# The fixture-served capture page never reaches Save's 'ready' phase (no
# queryable financial payload), so Save stays disabled in every capture flow;
# Rename writes through the same briefcase store and the same write-failure
# notice path, and is enabled whenever a saved view is active.
SAVED_RENAME_SELECTOR = "#ff-saved-rename"
SAVED_PINNED_ROW_ID = "CDEFGHIJKLMNOPQRSTUVWX"
SAVED_DRIFT_ROW_ID = "EFGHIJKLMNOPQRSTUVWXYZ"

# X2-s r2 (C1): the setItem patch is KEY-SCOPED — it throws QuotaExceededError
# only for the one storage key it is handed and delegates every other key to
# the original untouched, so the refusal can never leak to another feature.
_SAVED_WRITE_FAILURE_SETITEM_PATCH = (
    "(key) => { const original = Storage.prototype.setItem; Storage.prototype.setItem"
    " = function (k, v) { if (k === key) { throw new DOMException('storage refused in"
    " capture', 'QuotaExceededError'); } return original.call(this, k, v); }; }"
)
_SAVED_STORED_BYTES_SCRIPT = "(key) => localStorage.getItem(key)"
_SAVED_SELECTED_LABEL_SCRIPT = (
    "(sel) => { const s = document.querySelector(sel); const o = s && s.selectedOptions"
    " && s.selectedOptions[0]; return o ? String(o.textContent || '') : null; }"
)

# X2-s r1 (H1): the device-local briefcase key the seed init script plants.
BRIEFCASE_STORAGE_KEY = "mastermind.filing_forensics.saved_research.v1"

# A0-SE additive hook (SAFE-ENV), opened only by --dataset-store/--state-store;
# existing modes are unchanged without them.
PRODUCTION_CAPTURE_ENV_NAMES = (
    "FIF_FINANCIAL_DATASET_MODE",
    "FIF_PRODUCTION_DATASET_LOCAL_STORE",
    "RESEARCH_LOCAL_STORE",
)


def install_state_into_local_store(store_dir: str | Path, blob: bytes) -> Path:
    """Write the built state object into a LOCAL store at the loader's key."""
    from engine.fundamental_forensics import private_state  # noqa: PLC0415

    target = Path(store_dir) / private_state.STATE_KEY
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(blob)
    return target


PRIMARY_FINDING_SELECTOR = "[data-open-primary-finding]"
SELECTED_TAB_SELECTOR = '.ff-tab[aria-selected="true"]'
EVIDENCE_SELECTOR = "#ff-evidence"
# Browser-truth focusables, declared here rather than read from the page, so the
# drawer_trap probe checks the page's own focus-trap list instead of trusting it.
FOCUSABLE_PROBE_SELECTOR = (
    'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), '
    'textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"])'
)
TAB_WALK_CAP = 160
POINTER_PARK = (1, 1)
MODAL_OPEN_BODY_CLASS = "ff-modal-open"
_MODAL_OPEN_PROBE_SCRIPT = (
    "() => document.body.classList.contains('" + MODAL_OPEN_BODY_CLASS + "')"
)
CAPTURE_SCOPE_FULL_PAGE = "full_page"
CAPTURE_SCOPE_MODAL_VIEWPORT = (
    "viewport: modal open; Chromium's full-page capture drops or under-paints the "
    "fixed modal layer, so this cell is the first viewport only"
)
INTERACTION_SETTLE_MS = 350
INTERACTION_TIMEOUT_MS = 4000

EVIDENCE_RECEIPT_SCHEMA = "mastermind.page_evidence_receipt.v1"

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_PARTIAL = 3
EXIT_MODE_UNAVAILABLE = 4
# P2 r3 repair d: the served page is unrendered or stale (render guard).
EXIT_STALE_PAGE = 5


class FifEvidenceError(RuntimeError):
    """A typed wrapper failure. Never downgraded into a fake capture."""


class ModeUnavailable(FifEvidenceError):
    """The requested mode cannot run honestly (e.g. the real 401 path broke)."""


# ---------------------------------------------------------------------------
# URL host rewrite
# ---------------------------------------------------------------------------


def rewrite_evidence_host(url: str) -> str:
    """Rewrite ``127.0.0.1`` -> ``fif-evidence.localhost``, keeping everything else."""
    parsed = urlparse(url)
    if (parsed.hostname or "").lower() != SOURCE_HOST:
        return url
    netloc = EVIDENCE_HOST if parsed.port is None else f"{EVIDENCE_HOST}:{parsed.port}"
    return urlunparse(parsed._replace(netloc=netloc))


def is_local_origin_host(host: str) -> bool:
    """Seat fence 1: ``localhost``, ``*.localhost`` or a loopback IP literal only."""
    name = (host or "").strip().lower().rstrip(".")
    if not name:
        return False
    if name == "localhost" or name.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(name.strip("[]")).is_loopback
    except ValueError:
        return False


def refuse_non_local_targets(*, base_url: str | None, route: str) -> list[str]:
    """Seat fence 1: every origin this run could load; a non-empty answer = refuse to start.

    The default origin is the wrapped tool's own ``127.0.0.1`` static server
    (rewritten to ``fif-evidence.localhost``), which is local by construction; an
    explicit ``--base-url`` and an absolute ``--route`` are the only other origins
    the wrapped tool would navigate to, so both are checked here.
    """
    targets: list[tuple[str, str]] = []
    if base_url is not None:
        targets.append(("--base-url", base_url))
    if "://" in route:
        targets.append(("--route", route))
    refusals: list[str] = []
    for flag, url in targets:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not is_local_origin_host(parsed.hostname or ""):
            refusals.append(f"{flag} {url!r} is not a loopback or *.localhost origin")
    return refusals


# ---------------------------------------------------------------------------
# render guard (P2 r3 repair d): refuse an unrendered or stale served page
# ---------------------------------------------------------------------------

# The one-liner that renders this tree's template into site/ (the same command
# the ORCH-B capture recipe runs) and the step that puts the render output back
# afterwards. Both are printed in --help and in every refusal message.
RENDER_COMMAND = (
    "python3 -c \"from pathlib import Path; "
    "from scripts.build_fundamental_forensics import render_shell; "
    "render_shell(Path('.').resolve())\""
)
RESTORE_COMMAND = "git checkout -- site/fundamental_forensics.html"
PAGE_RELATIVE = "fundamental_forensics.html"
TEMPLATE_RELATIVE = "templates/fundamental_forensics.html.j2"
JINJA_MARKERS = ("{{", "{%")
STALE_ID_REPORT_CAP = 10
REFUSAL_PREFIX = "refusing to capture"


def served_page_problems(html: str, template: str) -> list[str]:
    """Why this served page must not be captured, or ``[]``.

    Two checks, both required: (i) any unrendered Jinja marker means the served
    file is the raw template; (ii) STALE RENDER — every literal ``id="ff-…"``
    in the template must appear verbatim in the served html. Check (i) alone is
    vacuous here: the stale committed ``site/fundamental_forensics.html`` and a
    fresh render both contain zero Jinja markers, so only the id census tells
    them apart (measured: 18 template ids missing from the stale page).
    """
    problems: list[str] = []
    present = [
        (html.find(marker), marker) for marker in JINJA_MARKERS if html.find(marker) >= 0
    ]
    if present:
        index, marker = min(present)
        excerpt = html[max(0, index - 12) : index + 28].replace("\n", " ").replace("\r", " ")
        problems.append(f"unrendered Jinja marker {marker} at byte {index}: …{excerpt}…")
    template_ids = sorted(
        {value for value in re.findall(r'id="(ff-[^"]*)"', template) if "{" not in value}
    )
    missing = [value for value in template_ids if f'id="{value}"' not in html]
    if missing:
        shown = ", ".join(missing[:STALE_ID_REPORT_CAP])
        extra = len(missing) - STALE_ID_REPORT_CAP
        suffix = f" (+{extra} more)" if extra > 0 else ""
        problems.append(
            f"stale render: {len(missing)} template id(s) missing from the served page: "
            f"{shown}{suffix}"
        )
    return problems


def fetch_served_page(base_url: str, route: str) -> str:
    """Fetch the route's html ONCE from the already loopback-checked origin.

    Module-level hook on purpose: tests replace it instead of touching a
    network. Errors are the caller's refusal, never a capture.
    """
    import urllib.request  # noqa: PLC0415

    url = route if "://" in route else base_url.rstrip("/") + "/" + route.lstrip("/")
    with urllib.request.urlopen(url, timeout=15) as response:
        return response.read().decode("utf-8", errors="replace")


def render_guard_refusals(
    *,
    tree_root: Path,
    site_dir: Path | None,
    base_url: str | None,
    route: str,
) -> list[str]:
    """Pre-flight: the served page must be a fresh render of this tree's template.

    Runs before any browser import/launch and before the kernel build. Reading
    the page is injectable through the plain module hooks (``fetch_served_page``
    here; ``--site-dir`` mode reads the file directly), so tests run without
    rendering — the committed ``site/fundamental_forensics.html`` is stale in CI.
    """
    if base_url is not None:
        try:
            html = fetch_served_page(base_url, route)
        except Exception as exc:  # noqa: BLE001 - a fetch failure is a refusal, never a capture
            return [f"could not fetch the served page from {base_url}: {type(exc).__name__}: {exc}"]
    else:
        directory = Path(site_dir) if site_dir is not None else tree_root / "site"
        page = directory / PAGE_RELATIVE
        if not page.is_file():
            return [f"served page missing: {page}"]
        html = page.read_text(encoding="utf-8", errors="replace")
    template_path = tree_root / TEMPLATE_RELATIVE
    if not template_path.is_file():
        return [f"template missing: {template_path}"]
    template = template_path.read_text(encoding="utf-8", errors="replace")
    return served_page_problems(html, template)


def print_render_refusal(problems: Sequence[str]) -> None:
    print(
        f"{REFUSAL_PREFIX}: {'; '.join(problems)}; "
        f"render first with: {RENDER_COMMAND}; "
        f"restore afterwards with: {RESTORE_COMMAND}",
        file=sys.stderr,
    )


# ---------------------------------------------------------------------------
# env scrub (names recorded, values never)
# ---------------------------------------------------------------------------


@dataclass
class EnvScrub:
    scrubbed_names: list[str]
    saved: dict[str, str] = field(default_factory=dict)


def scrub_process_env() -> EnvScrub:
    """Remove store/mode env vars so the kernel answers golden + local only."""
    saved: dict[str, str] = {}
    names: list[str] = []
    for name in sorted(os.environ):
        if name.startswith(SCRUB_ENV_PREFIXES) or name in SCRUB_ENV_NAMES:
            saved[name] = os.environ.pop(name)
            names.append(name)
    return EnvScrub(scrubbed_names=names, saved=saved)


def restore_process_env(scrub: EnvScrub) -> None:
    for name, value in scrub.saved.items():
        os.environ[name] = value


# ---------------------------------------------------------------------------
# network log
# ---------------------------------------------------------------------------


@dataclass
class NetworkLog:
    """Metadata + digests for every exchange. Response bodies are never stored."""

    entries: list[dict[str, Any]] = field(default_factory=list)
    aborted_hosts: set[str] = field(default_factory=set)

    def _next_seq(self) -> int:
        return len(self.entries) + 1

    def record(
        self,
        *,
        cell_id: str | None,
        method: str,
        path: str,
        query: str,
        category: str,
        status: int | None = None,
        request_body: bytes | None = None,
        response_content: bytes | None = None,
        response_content_type: str | None = None,
    ) -> dict[str, Any]:
        body = request_body if request_body is not None else b""
        request_body_json: Any = None
        if method == "POST" and path.startswith(FINANCIAL_POST_PREFIX) and request_body:
            try:
                request_body_json = json.loads(request_body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                request_body_json = None
        entry = {
            "seq": self._next_seq(),
            "cell_id": cell_id,
            "method": method,
            "path": path,
            "query": query,
            "category": category,
            "status": status,
            "request_body_bytes": len(request_body) if request_body is not None else None,
            "request_body_sha256": (
                hashlib.sha256(request_body).hexdigest() if request_body is not None else None
            ),
            "request_body_json": request_body_json,
            "response_bytes": len(response_content) if response_content is not None else None,
            "response_sha256": (
                hashlib.sha256(response_content).hexdigest() if response_content is not None else None
            ),
            "response_content_type": response_content_type,
        }
        self.entries.append(entry)
        return entry

    def as_payload(self) -> list[dict[str, Any]]:
        return [dict(entry) for entry in self.entries]


# ---------------------------------------------------------------------------
# route handler (one function, unit-testable with fake route/request objects)
# ---------------------------------------------------------------------------


def handle_exchange(
    route: Any,
    request: Any,
    *,
    client: Any,
    network_log: NetworkLog,
    cell_id: str | None,
) -> None:
    """Classify one intercepted request and answer it."""
    parsed = urlparse(request.url)
    host = (parsed.hostname or "").lower()
    path = parsed.path or "/"
    query = parsed.query or ""
    method = str(request.method or "GET").upper()

    if host in LOCAL_HOSTS:
        if path.startswith(FORENSICS_PREFIX):
            _forward_to_kernel(
                route,
                request,
                client=client,
                network_log=network_log,
                cell_id=cell_id,
                method=method,
                path=path,
                query=query,
            )
            return
        if path.startswith("/api/"):
            route.abort()
            network_log.record(
                cell_id=cell_id,
                method=method,
                path=path,
                query=query,
                category=CATEGORY_OTHER_LOCAL_API_ABORTED,
            )
            return
        route.continue_()
        network_log.record(
            cell_id=cell_id,
            method=method,
            path=path,
            query=query,
            category=CATEGORY_STATIC_CONTINUED,
        )
        return

    route.abort("blockedbyclient")
    network_log.aborted_hosts.add(host)
    network_log.record(
        cell_id=cell_id,
        method=method,
        path=path,
        query=query,
        category=CATEGORY_EXTERNAL_ABORTED,
    )


def _forward_to_kernel(
    route: Any,
    request: Any,
    *,
    client: Any,
    network_log: NetworkLog,
    cell_id: str | None,
    method: str,
    path: str,
    query: str,
) -> None:
    body = getattr(request, "post_data_buffer", None)
    forwarded_headers = {
        str(name): str(value)
        for name, value in dict(request.headers or {}).items()
        if str(name).lower() in FORWARDED_REQUEST_HEADERS
    }
    url = path + (f"?{query}" if query else "")
    try:
        response = client.request(
            method,
            url,
            content=body if body else None,
            headers=forwarded_headers,
        )
    except Exception as exc:  # noqa: BLE001 - typed, names-only refusal
        route.abort()
        network_log.record(
            cell_id=cell_id,
            method=method,
            path=path,
            query=query,
            category=CATEGORY_FORENSICS_FORWARD_FAILED,
        )
        raise FifEvidenceError(
            f"forwarding {method} {path} to the in-process kernel failed: {type(exc).__name__}"
        ) from exc
    out_headers = {
        str(name): str(value)
        for name, value in response.headers.items()
        if str(name).lower() not in DROPPED_RESPONSE_HEADERS
    }
    route.fulfill(status=response.status_code, headers=out_headers, body=response.content)
    network_log.record(
        cell_id=cell_id,
        method=method,
        path=path,
        query=query,
        category=CATEGORY_FORENSICS_FORWARDED,
        status=int(response.status_code),
        request_body=body,
        response_content=response.content,
        response_content_type=response.headers.get("content-type"),
    )


def make_route_handler(
    client: Any,
    network_log: NetworkLog,
    get_cell: Callable[[], Any],
) -> Callable[[Any, Any], None]:
    """Bind the handler to a cell slot so every exchange carries its cell_id."""

    def handler(route: Any, request: Any) -> None:
        cell = get_cell()
        handle_exchange(
            route,
            request,
            client=client,
            network_log=network_log,
            cell_id=None if cell is None else cell.cell_id,
        )

    return handler


# ---------------------------------------------------------------------------
# fold measurement (AM5) — measurement only, no judgement field
# ---------------------------------------------------------------------------

_FOLD_MEASURE_SCRIPT = """
(selectors) => {
  const scrollY = window.scrollY || 0;
  const scrollX = window.scrollX || 0;
  const viewportHeight = window.innerHeight;
  const measurements = [];
  for (const item of selectors) {
    const entry = {
      name: item.name,
      selector: item.selector,
      found: false,
      top: null,
      bottom: null,
      left: null,
      right: null,
      height: null,
      viewport_height: viewportHeight,
      rendered: false,
      within_first_viewport: false
    };
    try {
      const el = document.querySelector(item.selector);
      if (el) {
        const rect = el.getBoundingClientRect();
        entry.found = true;
        entry.top = rect.top + scrollY;
        entry.bottom = rect.bottom + scrollY;
        entry.left = rect.left + scrollX;
        entry.right = rect.right + scrollX;
        entry.height = rect.height;
        // A display:none element is found but has no box: its zero rect sits
        // at y=0, which must not read as "above the fold".
        entry.rendered = el.getClientRects().length > 0;
        entry.within_first_viewport = entry.rendered && entry.bottom <= viewportHeight;
      }
    } catch (e) {}
    measurements.push(entry);
  }
  return { viewport_height: viewportHeight, measurements: measurements };
}
"""


def measure_fold(
    page: Any,
    cell: Any,
    *,
    selectors: Sequence[tuple[str, str]],
    mode: str,
    sink: list[dict[str, Any]],
) -> None:
    """Record the fold position of each named selector at screenshot time."""
    row: dict[str, Any] = {
        "cell_id": cell.cell_id,
        "viewport": cell.viewport,
        "locale": cell.locale,
        "theme": cell.theme,
        "force_state": None if cell.force_state is None else cell.force_state.name,
        "mode": mode,
        "measurements": [
            {
                "name": name,
                "selector": selector,
                "found": False,
                "top": None,
                "bottom": None,
                "left": None,
                "right": None,
                "height": None,
                "viewport_height": None,
                "rendered": False,
                "within_first_viewport": False,
            }
            for name, selector in selectors
        ],
    }
    if selectors:
        try:
            result = page.evaluate(
                _FOLD_MEASURE_SCRIPT,
                [{"name": name, "selector": selector} for name, selector in selectors],
            ) or {}
            measurements = result.get("measurements")
            if isinstance(measurements, list) and len(measurements) == len(selectors):
                row["measurements"] = measurements
        except Exception as exc:  # noqa: BLE001 - the shot still happens
            row["measure_error"] = f"{type(exc).__name__}: {exc}"
    sink.append(row)


# ---------------------------------------------------------------------------
# real browser interactions (force-state interception)
# ---------------------------------------------------------------------------


_NO_ARG = object()

_ACTIVE_PROBE_SCRIPT = """
(selector) => {
  const active = document.activeElement;
  const real = !!(active && active !== document.body && active.matches);
  return {
    matches: real ? active.matches(selector) : false,
    tag: active ? active.tagName.toLowerCase() : null,
    id: active && active.id ? active.id : null,
    tab: real ? active.getAttribute('data-tab') : null,
  };
}
"""

_DRAWER_PROBE_SCRIPT = """
(config) => {
  const evidence = document.querySelector(config.evidence);
  const active = document.activeElement;
  if (!evidence) {
    return {present: false, open: false, modal: false, focus_inside: false,
            focus_id: null, focus_tag: null, focus_index: -1, focusable: 0};
  }
  const list = Array.prototype.slice.call(evidence.querySelectorAll(config.focusable))
    .filter(function (node) { return node.offsetParent !== null; });
  const inside = !!(active && evidence.contains(active));
  return {
    present: true,
    open: evidence.classList.contains('is-open'),
    modal: evidence.getAttribute('aria-modal') === 'true',
    focus_inside: inside,
    focus_id: active && active.id ? active.id : null,
    focus_tag: active ? active.tagName.toLowerCase() : null,
    focus_index: inside ? list.indexOf(active) : -1,
    focusable: list.length,
  };
}
"""

_TABLIST_PROBE_SCRIPT = """
() => {
  const active = document.activeElement;
  const isTab = !!(active && active.classList && active.classList.contains('ff-tab'));
  const selected = Array.prototype.slice.call(
    document.querySelectorAll('.ff-tab[aria-selected="true"]')
  ).map(function (node) { return node.getAttribute('data-tab'); });
  return {
    focus_is_tab: isTab,
    focus_tab: isTab ? active.getAttribute('data-tab') : null,
    selected: selected,
  };
}
"""

# A43 Z1 repair: the Escape half of the drawer_trap receipt. A real Escape
# press must close the drawer and restore focus per the product's own contract
# (templates/fundamental_forensics.js closeEvidence(restoreFocus) focuses
# state.lastFocus). For a drawer opened from the primary-finding CTA the
# recorded target — measured on the live page — is the SELECTED finding's own
# evidence button (openAnalysisDrawer -> selectedEvidenceButton(), rendered as
# button.ff-finding[data-finding-id][aria-current="true"]); the CTA itself is
# the fallback when no finding button matched at open time.
_DRAWER_CLOSED_PROBE_SCRIPT = """
(config) => {
  const evidence = document.querySelector(config.evidence);
  const active = document.activeElement;
  const onTrigger = !!(active && active.matches && active.matches(config.trigger));
  const onFindingButton = !!(active && active.matches && active.matches(
    'button[data-finding-id][aria-current="true"]'));
  const open = !!evidence && evidence.classList.contains('is-open');
  return {
    open: open,
    modal: !!evidence && evidence.getAttribute('aria-modal') === 'true',
    focus_restored: !open && (onTrigger || onFindingButton),
    focus_matches_trigger: onTrigger,
    focus_on_finding_button: onFindingButton,
    focus_id: active && active.id ? active.id : null,
    focus_tag: active ? active.tagName.toLowerCase() : null,
  };
}
"""

# A43 Z1 repair: the disabled/unavailable control-text probe. ``visible_text``
# is the applied locale's own text: a rendered control's innerText already
# shows exactly its .l-<locale> span, but a control behind the closed
# Desk-tools disclosure has no layout box and innerText falls back to
# textContent (BOTH locale spans concatenated), so the probe reads that
# locale's span directly in that case.
_DISABLED_CONTROLS_SCRIPT = """
(config) => config.selectors.map(function (selector) {
  const el = document.querySelector(selector);
  if (!el) {
    return {selector: selector, present: false, disabled: null, visible_text: null,
            label_en: null, label_zh: null, tip: null, aria_disabled: null};
  }
  const rendered = el.getClientRects().length > 0;
  const inner = String(el.innerText || '').trim();
  const span = el.querySelector('.l-' + config.locale);
  const visible = rendered && inner !== ''
    ? inner
    : (span ? String(span.textContent || '').trim() : inner);
  return {
    selector: selector,
    present: true,
    disabled: el.disabled === true,
    visible_text: visible,
    label_en: el.getAttribute('data-label-en'),
    label_zh: el.getAttribute('data-label-zh'),
    tip: el.getAttribute('data-tip-' + config.locale),
    aria_disabled: el.getAttribute('aria-disabled'),
  };
})
"""

_FOCUS_RESET_SCRIPT = """
() => {
  const active = document.activeElement;
  if (active && active !== document.body && active.blur) {
    active.blur();
  }
  window.scrollTo(0, 0);
  return true;
}
"""


def is_interaction_payload(arg: Any) -> bool:
    """The capture tool's attribute-force payload naming this wrapper's attribute."""
    return (
        isinstance(arg, Mapping)
        and arg.get("kind") == "attribute"
        and arg.get("attribute") == INTERACTION_ATTRIBUTE
    )


# ---------------------------------------------------------------------------
# briefcase seed (X2-s r1, H1)
# ---------------------------------------------------------------------------


def build_briefcase_seed_init_script(raw_file_text: str) -> str:
    """The ONE init script that plants the seed container verbatim.

    Exact shape (frozen by the unit test): the raw file TEXT rides as a JSON
    string literal, so the stored bytes equal the fixture bytes exactly, and
    the try/catch keeps a hostile storage implementation from breaking the
    page load. Only this one key is ever written.
    """
    return (
        "(()=>{try{window.localStorage.setItem(\"" + BRIEFCASE_STORAGE_KEY + "\", "
        + json.dumps(raw_file_text) + ")}catch(e){}})();"
    )


def resolve_briefcase_seed(raw: str, tree_root: Path) -> dict[str, str]:
    """Resolve ``--briefcase-seed``: a JSON object under ``<tree>/tests/fixtures``.

    Returns the sidecar fields (repo-relative ``path``, ``sha256`` of the file
    bytes, ``storage_key``) plus the built ``init_script``. Raises
    :class:`ValueError` with a plain message otherwise; ``main`` turns that
    into ``EXIT_USAGE`` before any browser, scrub or kernel work.
    """
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    resolved = candidate.resolve()
    fixtures_root = (tree_root / "tests" / "fixtures").resolve()
    if fixtures_root != resolved and fixtures_root not in resolved.parents:
        raise ValueError(
            f"--briefcase-seed must resolve under {fixtures_root}; got {resolved}"
        )
    if not resolved.is_file():
        raise ValueError(f"--briefcase-seed is not a file: {resolved}")
    raw_text = resolved.read_text(encoding="utf-8")
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"--briefcase-seed is not parseable JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"--briefcase-seed must be a JSON object, not {type(parsed).__name__}")
    return {
        "path": resolved.relative_to(tree_root).as_posix(),
        "sha256": hashlib.sha256(resolved.read_bytes()).hexdigest(),
        "storage_key": BRIEFCASE_STORAGE_KEY,
        "init_script": build_briefcase_seed_init_script(raw_text),
    }


def _settle(page: Any) -> None:
    try:
        page.wait_for_timeout(INTERACTION_SETTLE_MS)
    except Exception:  # noqa: BLE001 - the probe after the wait decides, never the wait
        pass


def _drawer_probe(page: Any) -> dict[str, Any]:
    config = {"evidence": EVIDENCE_SELECTOR, "focusable": FOCUSABLE_PROBE_SELECTOR}
    return dict(page.evaluate(_DRAWER_PROBE_SCRIPT.strip(), config) or {})


def close_drawer_and_probe_restore(page: Any) -> dict[str, Any]:
    """Press Escape, settle, then probe: closed drawer + focus on the trigger."""
    page.keyboard.press("Escape")
    _settle(page)
    config = {"evidence": EVIDENCE_SELECTOR, "trigger": PRIMARY_FINDING_SELECTOR}
    return dict(page.evaluate(_DRAWER_CLOSED_PROBE_SCRIPT.strip(), config) or {})


def fold_closed_into_verified(receipt: dict[str, Any], closed: Mapping[str, Any]) -> None:
    """Record the ``closed`` fact; a lost focus restore voids the receipt.

    Fail-closed only: a restored close can never un-fail a receipt whose trap
    verification already failed.
    """
    facts = receipt.setdefault("facts", {})
    facts["closed"] = dict(closed)
    receipt["verified"] = bool(receipt.get("verified")) and bool(closed.get("focus_restored"))


def probe_disabled_controls(page: Any, locale: str | None) -> list[dict[str, Any]]:
    """The two desk controls' disabled/unavailable record for ``locale``."""
    config = {"selectors": list(DISABLED_CONTROL_SELECTORS), "locale": str(locale or "en")}
    values = page.evaluate(_DISABLED_CONTROLS_SCRIPT.strip(), config) or []
    return [dict(value) for value in values if isinstance(value, dict)]


def record_disabled_controls(page: Any, cell: Any) -> dict[str, Any]:
    """A ``disabled_controls`` receipt for one rest cell; probe failure = gap."""
    receipt: dict[str, Any] = {
        "cell_id": getattr(cell, "cell_id", None),
        "viewport": getattr(cell, "viewport", None),
        "locale": getattr(cell, "locale", None),
        "theme": getattr(cell, "theme", None),
        "force_state": None,
        "interaction": INTERACTION_DISABLED_CONTROLS,
        "input": DISABLED_CONTROLS_PROBE_INPUT,
        "verified": False,
        "facts": {"controls": []},
    }
    try:
        receipt["facts"]["controls"] = probe_disabled_controls(
            page, getattr(cell, "locale", None)
        )
    except Exception as exc:  # noqa: BLE001 - a failed probe is a recorded gap
        receipt["error"] = f"{type(exc).__name__}: {exc}"
        return receipt
    controls = receipt["facts"]["controls"]
    seen_selectors = {entry.get("selector") for entry in controls}
    receipt["verified"] = bool(controls) and seen_selectors == set(
        DISABLED_CONTROL_SELECTORS
    ) and all(
        entry.get("present") and entry.get("disabled") is True and entry.get("visible_text")
        for entry in controls
    )
    return receipt


def rest_disabled_controls_probe_wanted(mode: str, force_states: Sequence[str]) -> bool:
    """Rest-cell ``disabled_controls`` receipts: the populated set only.

    The keyboard set is captured in mode=populated too, but its None-state
    cells are probed through their own tab_keys/drawer_trap receipts
    (``facts.disabled_controls``), keeping keyboard interactions.json at
    3 viewports x 2 interactions x 2 locales x 2 themes = 24 receipts.
    """
    if mode != MODE_POPULATED:
        return False
    return not any(
        spec.split(":", 1)[0] in KEYBOARD_INTERACTIONS for spec in force_states
    )


def tab_walk_to(page: Any, selector: str, *, cap: int = TAB_WALK_CAP) -> dict[str, Any]:
    """Press the REAL Tab key until ``selector`` holds focus (at most ``cap`` presses)."""
    page.evaluate(_FOCUS_RESET_SCRIPT.strip())
    focus: dict[str, Any] = {}
    for presses in range(1, cap + 1):
        page.keyboard.press("Tab")
        focus = dict(page.evaluate(_ACTIVE_PROBE_SCRIPT.strip(), selector) or {})
        if focus.get("matches"):
            return {"reached": True, "tab_presses": presses, "focus": focus}
    return {"reached": False, "tab_presses": cap, "focus": focus}


def _interact_drawer_open(page: Any) -> tuple[bool, dict[str, Any]]:
    before = _drawer_probe(page)
    page.locator(PRIMARY_FINDING_SELECTOR).first.click(timeout=INTERACTION_TIMEOUT_MS)
    # Park the pointer on the scrim corner: left where the click landed, it hovers
    # whichever drawer row now sits under it and the shot shows a hover state.
    mouse = getattr(page, "mouse", None)
    if mouse is not None:
        mouse.move(*POINTER_PARK)
    _settle(page)
    after = _drawer_probe(page)
    verified = bool(not before.get("open") and after.get("open") and after.get("modal"))
    parked = list(POINTER_PARK) if mouse is not None else None
    return verified, {"before": before, "after": after, "pointer_parked": parked}


def _interact_tab_keys(page: Any) -> tuple[bool, dict[str, Any]]:
    walk = tab_walk_to(page, SELECTED_TAB_SELECTOR)
    facts: dict[str, Any] = {"walk": walk}
    if not walk["reached"]:
        return False, facts
    before = dict(page.evaluate(_TABLIST_PROBE_SCRIPT.strip()) or {})
    page.keyboard.press("ArrowRight")
    _settle(page)
    after = dict(page.evaluate(_TABLIST_PROBE_SCRIPT.strip()) or {})
    facts.update(before=before, after=after, key="ArrowRight")
    moved = after.get("focus_tab")
    verified = bool(
        before.get("focus_is_tab")
        and after.get("focus_is_tab")
        and moved
        and moved != before.get("focus_tab")
        and after.get("selected") == [moved]
    )
    return verified, facts


def _interact_drawer_trap(page: Any) -> tuple[bool, dict[str, Any]]:
    walk = tab_walk_to(page, PRIMARY_FINDING_SELECTOR)
    facts: dict[str, Any] = {"walk": walk}
    if not walk["reached"]:
        return False, facts
    page.keyboard.press("Enter")
    _settle(page)
    opened = _drawer_probe(page)
    facts["opened"] = opened
    count = int(opened.get("focusable") or 0)
    if not (opened.get("open") and opened.get("modal") and opened.get("focus_inside") and count >= 1):
        return False, facts
    trail: list[dict[str, Any]] = []
    for _ in range(count + 2):
        page.keyboard.press("Tab")
        probe = _drawer_probe(page)
        trail.append(
            {
                "focus_index": probe.get("focus_index"),
                "inside": bool(probe.get("focus_inside")),
                "focus_id": probe.get("focus_id"),
                "focus_tag": probe.get("focus_tag"),
            }
        )
    indices = [opened.get("focus_index")] + [step["focus_index"] for step in trail]
    wrapped = any(
        first == count - 1 and second == 0 for first, second in zip(indices, indices[1:])
    )
    visited = {index for index in indices if isinstance(index, int) and 0 <= index < count}
    escaped = sum(1 for step in trail if not step["inside"])
    facts.update(
        trail=trail,
        focusable=count,
        tab_presses_inside=len(trail),
        wrapped=wrapped,
        visited=len(visited),
        escaped=escaped,
    )
    verified = bool(escaped == 0 and wrapped and visited == set(range(count)))
    return verified, facts


_SAVED_PROBE_SCRIPT = """
() => {
  const select = document.querySelector('#ff-saved-select');
  const badge = document.querySelector('#ff-saved-badge');
  const notice = document.querySelector('#ff-saved-notice');
  const visible = (node) => !!(node && node.offsetParent !== null);
  // X2-s r2 (C2): a read-only measurement of the selected option's text width
  // against the select's inner width — canvas 2d, the select's computed font
  // (fallback font string when the shorthand computes empty) plus the
  // computed left+right padding. Nothing is styled and no style is injected;
  // the fact is recorded for every saved interaction and gates nothing.
  let selected_text_fits = null;
  let selected_text_px = null;
  let select_inner_px = null;
  if (select) {
    const styles = window.getComputedStyle(select);
    const font = styles.font || (styles.fontWeight + ' ' + styles.fontSize + ' ' + styles.fontFamily);
    select_inner_px = select.clientWidth;
    const option = select.selectedOptions && select.selectedOptions[0];
    const context = document.createElement('canvas').getContext('2d');
    if (option && context) {
      context.font = font;
      selected_text_px = context.measureText(String(option.textContent || '')).width +
        parseFloat(styles.paddingLeft || '0') + parseFloat(styles.paddingRight || '0');
      selected_text_fits = selected_text_px <= select_inner_px + 0.5;
    }
  }
  return {
    value: select ? select.value : null,
    options: select ? Array.prototype.map.call(select.options, (o) => o.textContent) : [],
    badge_visible: visible(badge) && !!badge.textContent.trim(),
    notice_visible: visible(notice),
    notice_has_strong: !!(notice && notice.querySelector('strong')),
    notice_newer_generation: !!(notice && notice.querySelector('[data-saved-reresolve]')),
    notice_text: notice ? String(notice.textContent || '') : '',
    selected_text_fits: selected_text_fits,
    selected_text_px: selected_text_px,
    select_inner_px: select_inner_px,
  };
}
"""


def _saved_select(page: Any, row_id: str) -> None:
    """A REAL select change on the saved-views list, then pointer parked."""
    page.select_option(SAVED_SELECT_SELECTOR, row_id, timeout=INTERACTION_TIMEOUT_MS)
    _settle(page)
    mouse = getattr(page, "mouse", None)
    if mouse is not None:
        mouse.move(*POINTER_PARK)


def _interact_saved_restore_pinned(page: Any) -> tuple[bool, dict[str, Any]]:
    _saved_select(page, SAVED_PINNED_ROW_ID)
    probe = dict(page.evaluate(_SAVED_PROBE_SCRIPT.strip()) or {})
    notice_state = (
        "hidden"
        if not probe.get("notice_visible")
        else "newer_generation"
        if probe.get("notice_newer_generation")
        else "other"
    )
    facts: dict[str, Any] = {**probe, "notice_state": notice_state}
    verified = bool(probe.get("value") == SAVED_PINNED_ROW_ID and probe.get("badge_visible"))
    return verified, facts


def _interact_saved_open_unavailable(page: Any) -> tuple[bool, dict[str, Any]]:
    _saved_select(page, SAVED_DRIFT_ROW_ID)
    probe = dict(page.evaluate(_SAVED_PROBE_SCRIPT.strip()) or {})
    verified = bool(
        probe.get("notice_visible")
        and probe.get("notice_has_strong")
        and not probe.get("badge_visible")
    )
    return verified, dict(probe)


def _interact_saved_write_failure(page: Any) -> tuple[bool, dict[str, Any]]:
    _saved_select(page, SAVED_PINNED_ROW_ID)
    # Refuse the NEXT write to the saved-views key only, then drive a real
    # write through the briefcase store: Rename on the restored row (C4 — the
    # capture page never enables Save). The stored bytes and the row label are
    # read right before the click; the post-click probe plus a second read
    # prove the refusal left the bytes byte-identical and the name unchanged.
    page.evaluate(_SAVED_WRITE_FAILURE_SETITEM_PATCH, BRIEFCASE_STORAGE_KEY)
    page.fill(SAVED_NAME_SELECTOR, "Apple write check", timeout=INTERACTION_TIMEOUT_MS)
    before = page.evaluate(_SAVED_STORED_BYTES_SCRIPT, BRIEFCASE_STORAGE_KEY)
    label_before = page.evaluate(_SAVED_SELECTED_LABEL_SCRIPT, SAVED_SELECT_SELECTOR)
    page.click(SAVED_RENAME_SELECTOR, timeout=INTERACTION_TIMEOUT_MS)
    _settle(page)
    mouse = getattr(page, "mouse", None)
    if mouse is not None:
        mouse.move(*POINTER_PARK)
    after = page.evaluate(_SAVED_STORED_BYTES_SCRIPT, BRIEFCASE_STORAGE_KEY)
    label_after = page.evaluate(_SAVED_SELECTED_LABEL_SCRIPT, SAVED_SELECT_SELECTOR)
    probe = dict(page.evaluate(_SAVED_PROBE_SCRIPT.strip()) or {})
    before_sha = hashlib.sha256(str(before or "").encode("utf-8")).hexdigest()
    after_sha = hashlib.sha256(str(after or "").encode("utf-8")).hexdigest()
    notice_text = str(probe.get("notice_text") or "")
    verified = bool(
        probe.get("notice_visible")
        and not probe.get("notice_has_strong")
        and ("did not save this change" in notice_text or "浏览器未保存此更改" in notice_text)
        and probe.get("value") == SAVED_PINNED_ROW_ID
        and probe.get("badge_visible")
        and before is not None
        and after == before
        and before_sha == after_sha
        and label_before is not None
        and label_after == label_before
        and "Apple write check" not in str(label_after or "")
    )
    facts: dict[str, Any] = {
        **probe,
        "write_control": SAVED_RENAME_SELECTOR,
        "selected_label_before_click": label_before,
        "selected_label_after": label_after,
        "stored_sha256_before_click": before_sha,
        "stored_sha256_after": after_sha,
        "stored_unchanged": after == before,
    }
    return verified, facts


_INTERACTIONS: dict[str, Callable[[Any], tuple[bool, dict[str, Any]]]] = {
    INTERACTION_DRAWER_OPEN: _interact_drawer_open,
    INTERACTION_TAB_KEYS: _interact_tab_keys,
    INTERACTION_DRAWER_TRAP: _interact_drawer_trap,
    INTERACTION_SAVED_RESTORE_PINNED: _interact_saved_restore_pinned,
    INTERACTION_SAVED_OPEN_UNAVAILABLE: _interact_saved_open_unavailable,
    INTERACTION_SAVED_WRITE_FAILURE: _interact_saved_write_failure,
}


def run_interaction(page: Any, payload: Mapping[str, Any], cell: Any) -> dict[str, Any]:
    """Perform the REAL interaction an interception payload names; never raises.

    ``verified`` is True only when the post-interaction DOM probe confirms the
    state, and the capture tool is told the force applied only in that case.
    """
    name = str(payload.get("value") or "")
    receipt: dict[str, Any] = {
        "cell_id": getattr(cell, "cell_id", None),
        "viewport": getattr(cell, "viewport", None),
        "locale": getattr(cell, "locale", None),
        "theme": getattr(cell, "theme", None),
        "force_state": payload.get("name"),
        "interaction": name,
        "input": INTERACTION_INPUTS.get(name),
        "verified": False,
        "facts": {},
    }
    action = _INTERACTIONS.get(name)
    if action is None:
        receipt["error"] = f"unknown interaction {name!r}; known: {sorted(_INTERACTIONS)}"
        return receipt
    try:
        pre_facts: dict[str, Any] = {}
        if name in KEYBOARD_INTERACTIONS:
            # A43 Z1 repair: this cell's None-state disabled controls, probed
            # before the walk moves anything (a probe failure is a recorded
            # gap for the whole receipt — fail closed, like every interaction).
            pre_facts["disabled_controls"] = probe_disabled_controls(
                page, getattr(cell, "locale", None)
            )
        verified, facts = action(page)
    except Exception as exc:  # noqa: BLE001 - a failed interaction is a recorded gap
        receipt["error"] = f"{type(exc).__name__}: {exc}"
        return receipt
    if pre_facts:
        facts = {**pre_facts, **facts}
    receipt["verified"] = bool(verified)
    receipt["facts"] = facts
    return receipt


# ---------------------------------------------------------------------------
# driver proxies
# ---------------------------------------------------------------------------


class DriverProxy:
    """Wrap the real playwright driver: rewrite the host, install routing.

    Everything the capture tool calls (``capture``/``close``) delegates to the
    real driver; only the URL host is rewritten and, before the first capture,
    the real driver's ``_browser`` is swapped for a :class:`BrowserProxy`.
    """

    def __init__(
        self,
        real_driver: Any,
        *,
        route_handler_factory: Callable[[], Callable[[Any, Any], None]],
        fold_recorder: Callable[[Any, Any], None],
        interaction_runner: Callable[[Any, Mapping[str, Any], Any], Any] | None = None,
        init_scripts: Sequence[str] = (),
        rest_probe: Callable[[Any, Any], Any] | None = None,
    ) -> None:
        self._real = real_driver
        self._route_handler_factory = route_handler_factory
        self._fold_recorder = fold_recorder
        self._interaction_runner = interaction_runner
        self._init_scripts = tuple(init_scripts)
        self._rest_probe = rest_probe
        self._current_cell: Any = None
        self._wrapped = False

    @property
    def current_cell(self) -> Any:
        return self._current_cell

    def capture(self, *, url: str, cell: Any, timeout_s: float) -> Any:
        self._current_cell = cell
        if not self._wrapped:
            self._real._browser = BrowserProxy(
                self._real._browser,
                handler=self._route_handler_factory(),
                fold_recorder=self._fold_recorder,
                get_cell=lambda: self._current_cell,
                interaction_runner=self._interaction_runner,
                init_scripts=self._init_scripts,
                rest_probe=self._rest_probe,
            )
            self._wrapped = True
        return self._real.capture(url=rewrite_evidence_host(url), cell=cell, timeout_s=timeout_s)

    def close(self) -> None:
        self._real.close()


class BrowserProxy:
    """Install the route handler on every context the real browser mints."""

    def __init__(
        self,
        real_browser: Any,
        *,
        handler: Callable[[Any, Any], None],
        fold_recorder: Callable[[Any, Any], None],
        get_cell: Callable[[], Any],
        interaction_runner: Callable[[Any, Mapping[str, Any], Any], Any] | None = None,
        init_scripts: Sequence[str] = (),
        rest_probe: Callable[[Any, Any], Any] | None = None,
    ) -> None:
        self._real = real_browser
        self._handler = handler
        self._fold_recorder = fold_recorder
        self._get_cell = get_cell
        self._interaction_runner = interaction_runner
        self._init_scripts = tuple(init_scripts)
        self._rest_probe = rest_probe

    def new_context(self, **kwargs: Any) -> Any:
        real_context = self._real.new_context(**kwargs)
        real_context.route("**/*", self._handler)
        # X2-s r1 (H1): init scripts run in every page of the context BEFORE
        # any page script — installed after routing so a routed request can
        # never race the seed.
        for script in self._init_scripts:
            real_context.add_init_script(script=script)
        return ContextProxy(
            real_context,
            fold_recorder=self._fold_recorder,
            get_cell=self._get_cell,
            interaction_runner=self._interaction_runner,
            rest_probe=self._rest_probe,
        )

    def close(self) -> None:
        self._real.close()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real, name)


class ContextProxy:
    """Attribute delegation; ``new_page`` returns a measuring PageProxy."""

    def __init__(
        self,
        real_context: Any,
        *,
        fold_recorder: Callable[[Any, Any], None],
        get_cell: Callable[[], Any],
        interaction_runner: Callable[[Any, Mapping[str, Any], Any], Any] | None = None,
        rest_probe: Callable[[Any, Any], Any] | None = None,
    ) -> None:
        self._real = real_context
        self._fold_recorder = fold_recorder
        self._get_cell = get_cell
        self._interaction_runner = interaction_runner
        self._rest_probe = rest_probe

    def new_page(self) -> Any:
        return PageProxy(
            self._real.new_page(),
            fold_recorder=self._fold_recorder,
            get_cell=self._get_cell,
            interaction_runner=self._interaction_runner,
            rest_probe=self._rest_probe,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real, name)


class PageProxy:
    """Measure the fold before the screenshot; turn interaction forces into REAL input.

    An ``evaluate`` whose argument is the capture tool's attribute-force payload
    for ``INTERACTION_ATTRIBUTE`` is intercepted on the payload SHAPE alone: the
    attribute is never written; the interaction runner drives the real page and
    the tool is told the force applied only when the runner verified it. With no
    runner the force fails closed (``applied: None``). Everything else delegates.
    """

    def __init__(
        self,
        real_page: Any,
        *,
        fold_recorder: Callable[[Any, Any], None],
        get_cell: Callable[[], Any],
        interaction_runner: Callable[[Any, Mapping[str, Any], Any], Any] | None = None,
        rest_probe: Callable[[Any, Any], Any] | None = None,
    ) -> None:
        self._real = real_page
        self._fold_recorder = fold_recorder
        self._get_cell = get_cell
        self._interaction_runner = interaction_runner
        self._rest_probe = rest_probe
        # (cell id at interaction time, the receipt dict the runner returned): the
        # same object the run appended to interaction_rows, so annotating it here
        # lands in interactions.json.
        self._last_receipt: tuple[Any, dict[str, Any]] | None = None

    def evaluate(self, expression: Any, arg: Any = _NO_ARG, *args: Any, **kwargs: Any) -> Any:
        if is_interaction_payload(arg):
            return self._intercept_interaction(arg)
        if arg is _NO_ARG:
            return self._real.evaluate(expression, *args, **kwargs)
        return self._real.evaluate(expression, arg, *args, **kwargs)

    def _intercept_interaction(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        runner = self._interaction_runner
        if runner is None:
            return {"applied": None}
        cell = self._get_cell()
        try:
            receipt = runner(self._real, payload, cell)
        except Exception:  # noqa: BLE001 - an unverified interaction is a gap, never a pass
            return {"applied": None}
        if isinstance(receipt, dict):
            self._last_receipt = (getattr(cell, "cell_id", None), receipt)
        verified = isinstance(receipt, Mapping) and bool(receipt.get("verified"))
        return {"applied": payload.get("name") if verified else None}

    def screenshot(self, **kwargs: Any) -> Any:
        cell = self._get_cell()
        if cell is not None:
            try:
                self._fold_recorder(self._real, cell)
            except Exception:  # noqa: BLE001 - measurement must never kill the shot
                pass
            if self._rest_probe is not None and getattr(cell, "force_state", None) is None:
                # A43 Z1 repair: one disabled_controls receipt per rest cell
                # (the recorder builds the receipt and appends it to this run's
                # interaction rows; it records its own gap on probe failure).
                try:
                    self._rest_probe(self._real, cell)
                except Exception:  # noqa: BLE001 - the shot still happens
                    pass
        receipt = self._receipt_for(cell)
        if receipt is not None and kwargs.get("full_page"):
            if self._modal_open():
                kwargs = {**kwargs, "full_page": False}
                receipt["capture"] = CAPTURE_SCOPE_MODAL_VIEWPORT
            else:
                receipt["capture"] = CAPTURE_SCOPE_FULL_PAGE
        shot = self._real.screenshot(**kwargs)
        self._close_drawer_after_the_shot(receipt)
        return shot

    def _close_drawer_after_the_shot(self, receipt: dict[str, Any] | None) -> None:
        """A43 Z1 repair: the drawer_trap receipt's Escape half, AFTER the shot.

        The drawer_trap screenshot must still show the open, trapped drawer, so
        the real Escape press (close + focus restore, closeEvidence(restoreFocus))
        follows the screenshot; the receipt is annotated in place and a failed
        focus restore voids ``verified``. Once per receipt.
        """
        if receipt is None or receipt.get("interaction") != INTERACTION_DRAWER_TRAP:
            return
        facts = receipt.get("facts")
        if isinstance(facts, Mapping) and "closed" in facts:
            return
        try:
            closed = close_drawer_and_probe_restore(self._real)
        except Exception as exc:  # noqa: BLE001 - fail closed, never kill the shot path
            closed = {
                "open": None,
                "focus_restored": False,
                "probe_error": f"{type(exc).__name__}: {exc}",
            }
        fold_closed_into_verified(receipt, closed)

    def _receipt_for(self, cell: Any) -> dict[str, Any] | None:
        """The interaction receipt of THIS cell, or None (non-interaction cells)."""
        if self._last_receipt is None or cell is None:
            return None
        cell_id, receipt = self._last_receipt
        return receipt if cell_id == getattr(cell, "cell_id", None) else None

    def _modal_open(self) -> bool:
        try:
            return self._real.evaluate(_MODAL_OPEN_PROBE_SCRIPT) is True
        except Exception:  # noqa: BLE001 - an unreadable probe keeps the full-page shot
            return False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real, name)


# ---------------------------------------------------------------------------
# kernel state (populated mode)
# ---------------------------------------------------------------------------


@dataclass
class KernelStateReceipt:
    generated_at: str
    sha256: str
    bytes: int
    input_symlinks: tuple[str, ...]
    state_path: Path | None
    blob: bytes | None = field(default=None, repr=False)


def prepare_kernel_temp_root(tree_root: Path, temp_root: Path) -> list[str]:
    """Symlink ONLY the six read-only inputs; make the output dir a real dir."""
    created: list[str] = []
    for relative in KERNEL_INPUTS:
        source = tree_root / relative
        if not source.is_file():
            raise FifEvidenceError(f"kernel input missing from tree: {relative}")
        destination = temp_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(source.resolve())
        created.append(relative)
    output_dir = temp_root / KERNEL_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    if output_dir.is_symlink():
        raise FifEvidenceError(f"temp kernel output dir must be a real directory: {output_dir}")
    return created


def build_kernel_state(
    tree_root: Path, *, generated_at: str, install: bool = True
) -> KernelStateReceipt:
    """Build the private state into a temp root; copy the gzip object into the tree.

    ``install=False`` (degraded mode) keeps the object OUT of the tree: the
    receipt carries the bytes for the loader prime and ``state_path`` is None.
    """
    import scripts.build_fundamental_forensics as builder  # noqa: PLC0415 - heavy (pandas)

    temp_root = Path(tempfile.mkdtemp(prefix="fif-evidence-kernel-"))
    try:
        created = prepare_kernel_temp_root(tree_root, temp_root)
        state = builder.compose_state(temp_root, generated_at=generated_at)
        blob_path = temp_root / LOCAL_STATE_RELATIVE
        builder._write_state_atomic(blob_path, state)
        blob = blob_path.read_bytes()
        destination: Path | None = None
        if install:
            destination = tree_root / LOCAL_STATE_RELATIVE
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(blob_path, destination)
        return KernelStateReceipt(
            generated_at=str(generated_at),
            sha256=hashlib.sha256(blob).hexdigest(),
            bytes=len(blob),
            input_symlinks=tuple(created),
            state_path=destination,
            blob=blob,
        )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


# ---------------------------------------------------------------------------
# router app + mode verification
# ---------------------------------------------------------------------------


def load_forensics_module() -> Any:
    """Import app.forensics AFTER the env scrub, so REPO reads the scrubbed env."""
    import app.forensics as forensics_api  # noqa: PLC0415

    return forensics_api


def build_router_app(forensics_api: Any, *, populated: bool) -> Any:
    """FastAPI() with app.forensics.router; populated adds the router-test override.

    Seat fence 3: the override lands on the fresh instance created HERE for this
    run's in-process TestClient, never on ``app.main.app`` or any other
    module-level app a real server could share.
    """
    from fastapi import FastAPI  # noqa: PLC0415

    app = FastAPI()
    app.include_router(forensics_api.router)
    if populated:
        app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {
            "id": "fif-evidence-local"
        }
    return app


def verify_real_anonymous_denial(forensics_api: Any) -> None:
    """Anonymous mode requires the REAL dependency to produce the REAL 401.

    If importing/running it fails, the exception text is reported verbatim and
    the mode stops — a hand-made 401 is never substituted.
    """
    from fastapi import HTTPException  # noqa: PLC0415

    try:
        forensics_api.require_site_full_user(None)
    except HTTPException as exc:
        if exc.status_code != 401:
            raise ModeUnavailable(
                f"real require_site_full_user denied with HTTP {exc.status_code}, not 401: "
                f"{exc.detail!r}"
            ) from exc
        return
    except Exception as exc:  # noqa: BLE001 - verbatim report, never a substitute
        raise ModeUnavailable(
            "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        ) from exc
    raise ModeUnavailable(
        "real require_site_full_user returned success without a credential; refusing to "
        "continue anonymous mode"
    )


# ---------------------------------------------------------------------------
# unavailable / degraded modes (real loader, real routes, verified first)
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def local_state_set_aside(tree_root: Path) -> Iterator[dict[str, Any]]:
    """Move the tree's local private state out of the loader's reach for the run.

    The holding directory is created in the SAME directory as the object, so the
    ``os.replace`` both ways never crosses a filesystem; the object goes back in
    ``finally``, on success and on error alike.
    """
    local = tree_root / LOCAL_STATE_RELATIVE
    if local.is_symlink() or (local.exists() and not local.is_file()):
        raise FifEvidenceError(
            f"refusing to set aside a non-regular local state path: {LOCAL_STATE_RELATIVE}"
        )
    if not local.exists():
        yield {"set_aside": False, "sha256": None}
        return
    digest = hashlib.sha256(local.read_bytes()).hexdigest()
    holding = Path(tempfile.mkdtemp(prefix=".fif-evidence-setaside-", dir=local.parent))
    parked = holding / local.name
    os.replace(local, parked)
    try:
        yield {"set_aside": True, "sha256": digest}
    finally:
        os.replace(parked, local)
        shutil.rmtree(holding, ignore_errors=True)


def clear_private_state_cache() -> None:
    from engine.fundamental_forensics.private_state import clear_state_cache  # noqa: PLC0415

    clear_state_cache()


def prime_last_good_state(tree_root: Path, blob: bytes | None) -> dict[str, Any]:
    """Make the REAL loader hold ``blob`` as its last-good copy, then prove it.

    A temporary ``LocalStore`` (``RESEARCH_LOCAL_STORE``) serves the object for one
    zero-TTL read; the store and the env name are removed again, so the next read
    finds no store and the real loader answers ``last_good``. No loader code is
    patched and no cache entry is written by hand.
    """
    from engine.fundamental_forensics import private_state  # noqa: PLC0415

    if not blob:
        raise FifEvidenceError("degraded mode needs the built state bytes to prime the loader")
    local = tree_root / LOCAL_STATE_RELATIVE
    if local.exists() or local.is_symlink():
        raise FifEvidenceError(
            "degraded mode refuses to prime while a local private state is installed "
            "(the loader would answer 'local', not 'last_good')"
        )
    private_state.clear_state_cache()
    store_root = Path(tempfile.mkdtemp(prefix="fif-evidence-store-")).resolve()
    prior = os.environ.get("RESEARCH_LOCAL_STORE")
    try:
        target = store_root / private_state.STATE_KEY
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
        os.environ["RESEARCH_LOCAL_STORE"] = str(store_root)
        primed = private_state.load_state_record(tree_root, cache_seconds=0)
    finally:
        if prior is None:
            os.environ.pop("RESEARCH_LOCAL_STORE", None)
        else:
            os.environ["RESEARCH_LOCAL_STORE"] = prior
        shutil.rmtree(store_root, ignore_errors=True)
    if primed.origin != private_state.ORIGIN_R2 or primed.blob != blob:
        raise ModeUnavailable(
            f"real loader did not read the primed object (origin={primed.origin!r})"
        )
    served = private_state.load_state_record(tree_root)
    if served.origin != private_state.ORIGIN_LAST_GOOD or served.blob != blob:
        raise ModeUnavailable(
            "real loader did not fall back to its last-good copy once the store was "
            f"removed (origin={served.origin!r})"
        )
    return {
        "primed_origin": primed.origin,
        "served_origin": served.origin,
        "sha256": hashlib.sha256(blob).hexdigest(),
        "store": "temporary LocalStore via RESEARCH_LOCAL_STORE, removed before capture",
    }


def _json_or_empty(response: Any) -> dict[str, Any]:
    try:
        payload = response.json()
    except Exception:  # noqa: BLE001 - a non-JSON answer is a recorded fact, not a crash
        return {}
    return payload if isinstance(payload, dict) else {}


def verify_real_state_unavailable(client: Any) -> dict[str, Any]:
    """The REAL routes must answer 503 (state) and ``unavailable`` (health)."""
    state = client.get("/api/forensics/state")
    health = client.get("/api/forensics/health")
    payload = _json_or_empty(health)
    private_object = payload.get("private_object") or {}
    facts = {
        "state_status": state.status_code,
        "health_status": health.status_code,
        "health_state": payload.get("status"),
        "health_reason_code": payload.get("reason_code"),
        "private_object_origin": private_object.get("origin"),
    }
    if not (
        state.status_code == 503
        and health.status_code == 200
        and facts["health_state"] == "unavailable"
    ):
        raise ModeUnavailable(f"real routes did not report the unavailable state: {facts}")
    return facts


def verify_real_degraded_health(client: Any, *, expected_sha256: str) -> dict[str, Any]:
    """The REAL routes must serve the last-good object and report ``degraded``."""
    state = client.get("/api/forensics/state")
    health = client.get("/api/forensics/health")
    payload = _json_or_empty(health)
    private_object = payload.get("private_object") or {}
    facts = {
        "state_status": state.status_code,
        "state_sha256": hashlib.sha256(state.content).hexdigest() if state.status_code == 200 else None,
        "health_status": health.status_code,
        "health_state": payload.get("status"),
        "health_reason_code": payload.get("reason_code"),
        "age_seconds": payload.get("age_seconds"),
        "freshness_budget_seconds": payload.get("freshness_budget_seconds"),
        "private_object_origin": private_object.get("origin"),
    }
    if not (
        state.status_code == 200
        and facts["state_sha256"] == expected_sha256
        and health.status_code == 200
        and facts["health_state"] == "degraded"
        and facts["private_object_origin"] == "last_good"
    ):
        raise ModeUnavailable(f"real routes did not report the degraded state: {facts}")
    return facts


def degraded_clock_problem(generated_at: str | None, *, now: datetime) -> str | None:
    """Why ``generated_at`` cannot yield a degraded health answer, or None."""
    if not generated_at:
        return "--generated-at is required in degraded mode (kernel state clock)"
    try:
        parsed = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
    except ValueError:
        return f"--generated-at is not an ISO-8601 instant: {generated_at!r}"
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    age = (now - parsed).total_seconds()
    if age <= FRESHNESS_BUDGET_SECONDS:
        return (
            "degraded mode needs --generated-at older than the engine freshness budget "
            f"({FRESHNESS_BUDGET_SECONDS}s); {generated_at} is {int(age)}s old, so health "
            "would report current, not degraded"
        )
    return None


# ---------------------------------------------------------------------------
# manifest post-process
# ---------------------------------------------------------------------------


def postprocess_manifest(
    manifest: dict[str, Any],
    *,
    mode: str,
    generator_command: str,
    wrapper_module_sha256: str,
    scrubbed_env_names: Sequence[str],
    aborted_hosts: Sequence[str],
    state_receipt: KernelStateReceipt | None,
    interactions: str | None = None,
    mode_verification: Mapping[str, Any] | None = None,
    briefcase_seed: str | None = None,
) -> None:
    """Keep everything the capture tool wrote; add the fixture-backed provenance.

    Entitled modes also correct the per-state ``access`` field (and the page's
    ``metrics.measured_in.access``): the capture tool stamps its fixed
    ``anonymous`` token on every row, which is false for an entitled crop.
    """
    entitled = mode in ENTITLED_MODES
    label = MODE_LABELS[mode]
    access = MODE_ACCESS[mode]
    for page in manifest.get("pages", []):
        for state_row in page.get("states", []):
            state_row["evidence_label"] = label
            if entitled:
                state_row["access"] = access
        measured_in = (page.get("metrics") or {}).get("measured_in")
        if entitled and isinstance(measured_in, dict) and "access" in measured_in:
            measured_in["access"] = access
    if entitled:
        manifest.setdefault("axes", {})["access"] = [access]
        honesty = manifest.setdefault("honesty", {})
        honesty["access"] = MODE_HONESTY[mode]
        honesty["entitlement"] = ENTITLED_CROPS_FENCE
        honesty["cell_id_access"] = CELL_ID_ACCESS_NOTE
    evidence_source: dict[str, Any] = {
        "label": label,
        "mode": mode,
        "generator_command": generator_command,
        "wrapper_module": TOOL_MODULE_REF,
        "wrapper_module_sha256": wrapper_module_sha256,
        "entitlement": POPULATED_ENTITLEMENT if entitled else ANONYMOUS_ENTITLEMENT,
        "host_rewrite": HOST_REWRITE,
    }
    if mode in (MODE_POPULATED, MODE_DEGRADED) and state_receipt is not None:
        state: dict[str, Any] = {
            "builder": KERNEL_BUILDER_REF,
            "generated_at": state_receipt.generated_at,
            "sha256": state_receipt.sha256,
            "bytes": state_receipt.bytes,
        }
        if mode == MODE_DEGRADED:
            state["delivery"] = DEGRADED_STATE_DELIVERY
        evidence_source["state"] = state
    if entitled:
        evidence_source["entitlement_fence"] = ENTITLED_CROPS_FENCE
    evidence_source["financial_dataset_mode"] = "golden"
    evidence_source["scrubbed_env_names"] = sorted(scrubbed_env_names)
    evidence_source["aborted_hosts"] = sorted(set(aborted_hosts))
    evidence_source["network_log"] = "network_log.json"
    evidence_source["fold_measurement"] = "fold_measurement.json"
    if interactions:
        evidence_source["interactions"] = interactions
    if briefcase_seed:
        # X2-s r1 (H1): names the sidecar (path/sha256/storage_key) planted
        # by this run's seed init script; absent without --briefcase-seed.
        evidence_source["briefcase_seed"] = briefcase_seed
    if mode_verification is not None:
        evidence_source["mode_verification"] = dict(mode_verification)
    manifest["evidence_source"] = evidence_source


def rest_cell_misses(manifest: Mapping[str, Any]) -> list[str]:
    """Every rest (unforced) state row that did not capture, by cell."""
    misses: list[str] = []
    for page in manifest.get("pages", []):
        for state_row in page.get("states", []):
            if state_row.get("force_state") is not None:
                continue
            if not state_row.get("captured"):
                misses.append(str(state_row.get("reason") or "captured: false"))
    return misses


# ---------------------------------------------------------------------------
# EVIDENCE.yml receipt
# ---------------------------------------------------------------------------


def write_evidence_yml(
    path: Path,
    *,
    changed_paths: Sequence[str],
    manifest_relative: str,
) -> None:
    """Exactly three keys: schema, changed_paths, manifest."""
    lines = [f"schema: {EVIDENCE_RECEIPT_SCHEMA}", "changed_paths:"]
    for changed in changed_paths:
        lines.append(f"  - {json.dumps(changed)}")
    lines.append(f"manifest: {json.dumps(manifest_relative)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_fold_selectors(raw_values: Sequence[str]) -> list[tuple[str, str]]:
    selectors: list[tuple[str, str]] = []
    for raw in raw_values:
        if "=" not in raw:
            raise argparse.ArgumentTypeError(
                f"--fold-selector expects NAME=CSS, got {raw!r}"
            )
        name, selector = raw.split("=", 1)
        name, selector = name.strip(), selector.strip()
        if not name or not selector:
            raise argparse.ArgumentTypeError(
                f"--fold-selector expects NAME=CSS, got {raw!r}"
            )
        selectors.append((name, selector))
    return selectors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "render guard (P2 r3):\n"
            "  The served page must be a fresh render of this tree's template. An\n"
            "  unrendered or stale page is refused BEFORE any browser launch.\n"
            f"    render first with: {RENDER_COMMAND}\n"
            f"    restore afterwards with: {RESTORE_COMMAND}\n"
        ),
    )
    parser.add_argument("--mode", required=True, choices=ALL_MODES)
    parser.add_argument("--route", default="/fundamental_forensics.html?symbol=AAPL")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument(
        "--base-url",
        default=None,
        help="optional LOCAL origin already serving site/ (loopback or *.localhost only; "
        "anything else is refused before capture). Default: the wrapped tool's own "
        "127.0.0.1 server for site/",
    )
    parser.add_argument(
        "--site-dir",
        default=None,
        metavar="DIR",
        dest="site_dir",
        help="optional site/ directory to capture instead of <tree>/site; its "
        f"{PAGE_RELATIVE} must be a fresh render (the render guard reads it before "
        "any browser launches)",
    )
    parser.add_argument("--as-of", help="pin the capture tool's generated_at (ISO)")
    parser.add_argument("--generated-at", help="kernel state clock for compose_state (ISO)")
    parser.add_argument(
        "--force-state",
        action="append",
        default=[],
        metavar="NAME:TARGET",
        dest="force_state",
        help="repeatable; passed through to the wrapped capture tool",
    )
    parser.add_argument(
        "--fold-selector",
        action="append",
        default=[],
        metavar="NAME=CSS",
        dest="fold_selector",
        help="repeatable; measure this selector's fold position at screenshot time",
    )
    parser.add_argument(
        "--changed-path",
        action="append",
        default=[],
        metavar="P",
        dest="changed_path",
        help="repeatable; emit EVIDENCE.yml naming these paths",
    )
    parser.add_argument("--viewports", default="desktop,mobile")
    parser.add_argument("--locales", default="en,zh")
    parser.add_argument("--themes", default="dark,light")
    parser.add_argument(
        "--briefcase-seed",
        default=None,
        metavar="PATH",
        dest="briefcase_seed",
        help="optional JSON-object fixture under <repo>/tests/fixtures planted as "
        "the device-local saved-views briefcase (one localStorage key) before any "
        "page script; a briefcase_seed.json sidecar records path/sha256/storage_key",
    )
    parser.add_argument(
        "--dataset-store", default=None, metavar="DIR", dest="dataset_store",
        help="A0-SE SAFE-ENV hook: production mode over this LOCAL fixture store",
    )
    parser.add_argument(
        "--state-store", default=None, metavar="DIR", dest="state_store",
        help="A0-SE SAFE-ENV hook: keep the built private state in this LOCAL store",
    )
    return parser


def _wrapped_driver_factory(
    *,
    client: Any,
    network_log: NetworkLog,
    fold_rows: list[dict[str, Any]],
    fold_selectors: Sequence[tuple[str, str]],
    mode: str,
    interaction_rows: list[dict[str, Any]] | None = None,
    init_scripts: Sequence[str] = (),
    rest_probe_enabled: bool = False,
) -> Callable[..., DriverProxy]:
    from scripts.capture_page_evidence import playwright_page_driver  # noqa: PLC0415

    # The route handler must read the CURRENT cell off the exact proxy this
    # factory returns, so the proxy registers itself through this slot.
    slot: list[DriverProxy | None] = [None]

    def interaction_runner(page: Any, payload: Mapping[str, Any], cell: Any) -> dict[str, Any]:
        receipt = run_interaction(page, payload, cell)
        if interaction_rows is not None:
            interaction_rows.append(receipt)
        return receipt

    def rest_probe(page: Any, cell: Any) -> dict[str, Any]:
        # A43 Z1 repair: one disabled_controls receipt per rest cell.
        receipt = record_disabled_controls(page, cell)
        if interaction_rows is not None:
            interaction_rows.append(receipt)
        return receipt

    def factory(**kwargs: Any) -> DriverProxy:
        real_driver = playwright_page_driver(**kwargs)
        proxy = DriverProxy(
            real_driver,
            route_handler_factory=lambda: make_route_handler(
                client,
                network_log,
                lambda: slot[0].current_cell if slot[0] is not None else None,
            ),
            fold_recorder=lambda page, cell: measure_fold(
                page, cell, selectors=fold_selectors, mode=mode, sink=fold_rows
            ),
            interaction_runner=interaction_runner,
            init_scripts=init_scripts,
            rest_probe=rest_probe if rest_probe_enabled else None,
        )
        slot[0] = proxy
        return proxy

    return factory


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    refusals = refuse_non_local_targets(base_url=args.base_url, route=args.route)
    if refusals:
        for refusal in refusals:
            print(f"error: refusing to start (seat fence 1): {refusal}", file=sys.stderr)
        return EXIT_USAGE
    invoked = list(sys.argv[1:] if argv is None else argv)
    generator_command = shlex.join(
        ["python3", "-m", "tests.tools.fif_p2_evidence_capture", *invoked]
    )

    tree_root = Path(__file__).resolve().parents[2]
    out_dir = Path(args.out_dir).expanduser().resolve()
    mode = args.mode
    entitled = mode in ENTITLED_MODES
    if mode in (MODE_POPULATED, MODE_DEGRADED) and not args.generated_at:
        print(
            f"error: --generated-at is required in {mode} mode (kernel state clock)",
            file=sys.stderr,
        )
        return EXIT_USAGE
    if mode == MODE_DEGRADED:
        problem = degraded_clock_problem(args.generated_at, now=datetime.now(timezone.utc))
        if problem is not None:
            print(f"error: {problem}", file=sys.stderr)
            return EXIT_USAGE

    # X2-s r1 (H1): resolve --briefcase-seed BEFORE the render guard, the env
    # scrub, the kernel build and any browser launch — a bad seed is a usage
    # error, not a capture failure.
    seed_info: dict[str, str] | None = None
    if args.briefcase_seed:
        try:
            seed_info = resolve_briefcase_seed(args.briefcase_seed, tree_root)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return EXIT_USAGE

    try:
        fold_selectors = parse_fold_selectors(args.fold_selector)
    except argparse.ArgumentTypeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE

    # P2 r3 repair d: the served page must be a fresh render of this tree's
    # template — refuse BEFORE the env scrub, the kernel build and any browser
    # import/launch. The committed site html is stale in CI on purpose.
    stale_page = render_guard_refusals(
        tree_root=tree_root,
        site_dir=getattr(args, "site_dir", None),
        base_url=args.base_url,
        route=args.route,
    )
    if stale_page:
        print_render_refusal(stale_page)
        return EXIT_STALE_PAGE

    scrub = scrub_process_env()
    prior_macro_repo = os.environ.get("MACRO_REPO")
    # A0-SE SAFE-ENV hook: opened only by the explicit flags below.
    prior_production_capture_env = {
        name: os.environ.get(name) for name in PRODUCTION_CAPTURE_ENV_NAMES
    }
    if args.dataset_store is not None:
        os.environ["FIF_FINANCIAL_DATASET_MODE"] = "production"
        os.environ["FIF_PRODUCTION_DATASET_LOCAL_STORE"] = str(Path(args.dataset_store).expanduser().resolve())
    if args.state_store is not None:
        os.environ["RESEARCH_LOCAL_STORE"] = str(Path(args.state_store).expanduser().resolve())
    try:
        os.environ["MACRO_REPO"] = str(tree_root)
        forensics_api = load_forensics_module()
        prior_repo = forensics_api.REPO
        forensics_api.REPO = tree_root
        stack = contextlib.ExitStack()
        try:
            state_receipt: KernelStateReceipt | None = None
            mode_verification: dict[str, Any] | None = None
            interaction_rows: list[dict[str, Any]] = []
            if mode in (MODE_UNAVAILABLE, MODE_DEGRADED):
                set_aside = stack.enter_context(local_state_set_aside(tree_root))
                clear_private_state_cache()
                stack.callback(clear_private_state_cache)
                mode_verification = {"local_state_set_aside": set_aside}
            if mode == MODE_POPULATED:
                into_local_store = args.state_store is not None
                state_receipt = build_kernel_state(
                    tree_root,
                    generated_at=args.generated_at,
                    install=not into_local_store,
                )
                if into_local_store:
                    destination = install_state_into_local_store(
                        args.state_store, state_receipt.blob
                    )
                else:
                    destination = tree_root / LOCAL_STATE_RELATIVE
                print(
                    f"kernel state: {state_receipt.bytes} bytes "
                    f"sha256={state_receipt.sha256[:16]} -> {destination}"
                )
            elif mode == MODE_DEGRADED:
                state_receipt = build_kernel_state(
                    tree_root, generated_at=args.generated_at, install=False
                )
                mode_verification["loader_prime"] = prime_last_good_state(
                    tree_root, state_receipt.blob
                )
                print(
                    f"kernel state: {state_receipt.bytes} bytes sha256={state_receipt.sha256[:16]} "
                    "-> real loader last-good cache only (not installed)"
                )
            elif mode == MODE_ANONYMOUS:
                verify_real_anonymous_denial(forensics_api)

            network_log = NetworkLog()
            fold_rows: list[dict[str, Any]] = []
            router_app = build_router_app(forensics_api, populated=entitled)
            from fastapi.testclient import TestClient  # noqa: PLC0415

            with TestClient(router_app, raise_server_exceptions=False) as client:
                if mode == MODE_UNAVAILABLE:
                    mode_verification["routes"] = verify_real_state_unavailable(client)
                elif mode == MODE_DEGRADED:
                    mode_verification["routes"] = verify_real_degraded_health(
                        client, expected_sha256=state_receipt.sha256
                    )
                if mode_verification is not None:
                    print(f"mode verification: {json.dumps(mode_verification.get('routes'), sort_keys=True)}")
                capture_rc = _run_wrapped_capture(
                    args,
                    tree_root=tree_root,
                    out_dir=out_dir,
                    client=client,
                    network_log=network_log,
                    fold_rows=fold_rows,
                    fold_selectors=fold_selectors,
                    interaction_rows=interaction_rows,
                    init_scripts=(seed_info["init_script"],) if seed_info else (),
                )
        finally:
            try:
                stack.close()
            finally:
                forensics_api.REPO = prior_repo
    except ModeUnavailable as exc:
        print(
            f"::error title=fif-p2-evidence::{args.mode} mode unavailable; reporting the "
            "failure verbatim (never substituting a hand-made answer)",
            flush=True,
        )
        print(str(exc), file=sys.stderr)
        return EXIT_MODE_UNAVAILABLE
    except FifEvidenceError as exc:
        print(f"::error title=fif-p2-evidence::{type(exc).__name__}: {exc}", flush=True)
        return EXIT_MODE_UNAVAILABLE
    finally:
        if prior_macro_repo is None:
            os.environ.pop("MACRO_REPO", None)
        else:
            os.environ["MACRO_REPO"] = prior_macro_repo
        restore_process_env(scrub)
        for name, old in prior_production_capture_env.items():
            if old is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = old

    if capture_rc != 0 and not (out_dir / "manifest.json").is_file():
        print(f"error: wrapped capture failed with exit {capture_rc}; no manifest written")
        return capture_rc or EXIT_PARTIAL

    from scripts.capture_page_evidence import canonical_json_bytes  # noqa: PLC0415

    manifest_path = out_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    wrapper_sha256 = hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest()
    postprocess_manifest(
        manifest,
        mode=args.mode,
        generator_command=generator_command,
        wrapper_module_sha256=wrapper_sha256,
        scrubbed_env_names=scrub.scrubbed_names,
        aborted_hosts=sorted(network_log.aborted_hosts),
        state_receipt=state_receipt,
        interactions="interactions.json" if interaction_rows else None,
        mode_verification=mode_verification,
        briefcase_seed="briefcase_seed.json" if seed_info else None,
    )
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    (out_dir / "network_log.json").write_bytes(canonical_json_bytes(network_log.as_payload()))
    (out_dir / "fold_measurement.json").write_bytes(canonical_json_bytes(fold_rows))
    if interaction_rows:
        (out_dir / "interactions.json").write_bytes(canonical_json_bytes(interaction_rows))
    if seed_info:
        # X2-s r1 (H1): the sidecar proves exactly which fixture bytes this
        # run's contexts were seeded with, and under which storage key.
        (out_dir / "briefcase_seed.json").write_bytes(
            canonical_json_bytes(
                {
                    "path": seed_info["path"],
                    "sha256": seed_info["sha256"],
                    "storage_key": seed_info["storage_key"],
                }
            )
        )

    if args.changed_path:
        manifest_relative = (
            Path(os.path.relpath(out_dir, tree_root)) / "manifest.json"
        ).as_posix()
        write_evidence_yml(
            out_dir / "EVIDENCE.yml",
            changed_paths=args.changed_path,
            manifest_relative=manifest_relative,
        )

    misses = rest_cell_misses(manifest)
    totals = manifest.get("totals", {})
    print(f"mode: {args.mode}")
    print(
        f"rest cells: {totals.get('states_captured', 0)}/{totals.get('states_attempted', 0)} "
        f"captured (forced cells included in totals)"
    )
    print(f"forensics exchanges: {sum(1 for e in network_log.entries if e['category'] == CATEGORY_FORENSICS_FORWARDED)}")
    print(f"aborted hosts: {sorted(network_log.aborted_hosts)}")
    print(f"manifest: {manifest_path}")
    unverified = [str(row.get("cell_id")) for row in interaction_rows if not row.get("verified")]
    if interaction_rows:
        print(
            f"interactions: {len(interaction_rows) - len(unverified)}/{len(interaction_rows)} "
            "verified"
        )
    if unverified:
        print(
            "::warning title=fif-p2-evidence::interactions not verified: "
            + "; ".join(unverified[:5]),
            flush=True,
        )
    if misses:
        print(
            "::warning title=fif-p2-evidence::rest cells not captured: "
            + "; ".join(misses[:5]),
            flush=True,
        )
    if misses or unverified:
        return EXIT_PARTIAL
    return EXIT_OK


def _run_wrapped_capture(
    args: argparse.Namespace,
    *,
    tree_root: Path,
    out_dir: Path,
    client: Any,
    network_log: NetworkLog,
    fold_rows: list[dict[str, Any]],
    fold_selectors: Sequence[tuple[str, str]],
    interaction_rows: list[dict[str, Any]] | None = None,
    init_scripts: Sequence[str] = (),
) -> int:
    from scripts.capture_page_evidence import main as capture_main  # noqa: PLC0415

    base_url = getattr(args, "base_url", None)
    site_dir = getattr(args, "site_dir", None)
    capture_site_dir = Path(site_dir) if site_dir else tree_root / "site"
    origin_argv = ["--base-url", base_url] if base_url else ["--site-dir", str(capture_site_dir)]
    capture_argv: list[str] = [
        *origin_argv,
        "--routes",
        args.route,
        "--output-dir",
        str(out_dir),
        "--manifest",
        str(out_dir / "manifest.json"),
        "--smells",
        str(out_dir / "smells.json"),
        "--viewports",
        args.viewports,
        "--locales",
        args.locales,
        "--themes",
        args.themes,
    ]
    if args.as_of:
        capture_argv += ["--as-of", args.as_of]
    for force_state in args.force_state:
        capture_argv += ["--force-state", force_state]

    factory = _wrapped_driver_factory(
        client=client,
        network_log=network_log,
        fold_rows=fold_rows,
        fold_selectors=fold_selectors,
        mode=args.mode,
        interaction_rows=interaction_rows,
        init_scripts=init_scripts,
        rest_probe_enabled=rest_disabled_controls_probe_wanted(args.mode, args.force_state),
    )
    return capture_main(capture_argv, driver_factory=factory)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
