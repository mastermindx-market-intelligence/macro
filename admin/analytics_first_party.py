"""First-party analytics reader — the self-hosted alternative to Umami/GA4.

Reads the shared Supabase analytics tables (analytics_events, search_events, ip_geo — created by
the Terminal repo's supabase/migrations/0004_analytics.sql + 0003_search_events.sql) through the
Management API SQL endpoint, exactly like users.py: a read-only SELECT with the sbp_… PAT, no
service_role JWT stored, nothing exposed to the browser. All SQL is static text authored here; the
only interpolated values are int-clamped (days/limit) or allowlist-validated ids (session/visitor),
so there is no injection surface.

Surfaces (all return the {ok, …} / {ok:False, reason} envelope the SPA expects):
  overview   headline counts + by-site split + daily series
  pages      top pages/paths by views + unique visitors
  geo        visitor map — by country and by city (lat/lon for plotting)
  sessions   recent VISITS (per-tab/per-origin session_ids stitched — see _visit_break)
  session    the ordered event path of ONE visit (the 1:1 replay)
  flow       navigation patterns — from→to path-pair counts (window over each session)
  terminal   Terminal usage — top tickers SEARCHED (search_events) and VIEWED (ticker_view)
  visitor    identity stitch — one visitor's sessions/IPs/fingerprints + linked visitor_ids
  realtime   distinct visitors/sessions active in the last 5 minutes
  geo_enrich_now  on-demand IPLocate backfill (subprocesses scripts/geo_enrich.py)
"""
from __future__ import annotations

import contextvars
import json
import os
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from . import settings, users

try:
    from zoneinfo import ZoneInfo
except Exception:  # noqa: BLE001 — py<3.9 / missing tzdata
    ZoneInfo = None  # type: ignore

try:
    import requests
except Exception:  # noqa: BLE001
    requests = None  # type: ignore

_API = "https://api.supabase.com/v1"
_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")  # session_id / visitor_id shape (uuid or 's-…')

# ── Display timezone ───────────────────────────────────────────────────────────
# analytics_events.created_at is timestamptz and Postgres renders it in the SESSION zone
# (UTC on Supabase), so every panel timestamp used to read as UTC while the operator reads
# it as a wall clock. All formatting now goes through _lt(): an `at time zone` conversion to
# the operator's zone. A named zone (not a fixed -08:00) so PST/PDT switch on their own —
# `America/Los_Angeles` IS "PST time" in the sense meant, correct year-round. Day buckets in
# the overview series are truncated AFTER the conversion, so a "day" is a local midnight-to-
# midnight day. Env-overridable for a future operator in another zone.
_TZ = os.environ.get("ANALYTICS_TZ", "America/Los_Angeles")
_TZ_SQL = "'" + re.sub(r"[^A-Za-z0-9_/+-]", "", _TZ) + "'"

# ── Visit stitching ────────────────────────────────────────────────────────────
# The tracker's session_id lives in sessionStorage, so it is per TAB *and* per ORIGIN: one
# person reading macro, hopping to the Terminal (app.mastermind-x.com — a different origin,
# hence a different sessionStorage) and coming back files THREE session rows for what is
# plainly one sitting. A visit re-joins them: order a person's events (login-merged identity
# where known, else the mm_aid cookie) and start a new visit only after _VISIT_GAP_MIN of
# silence — the same 30-minute idle rule GA/Plausible use, and the same one the client-side
# sid rotation already uses, just applied across tabs and origins instead of within one.
_VISIT_GAP_MIN = 30


def _tz_label() -> str:
    """Short zone abbreviation for the UI ('PST' / 'PDT'); falls back to the zone name."""
    if ZoneInfo is None:
        return _TZ
    try:
        return datetime.now(ZoneInfo(_TZ)).strftime("%Z") or _TZ
    except Exception:  # noqa: BLE001
        return _TZ


def _lt(col: str) -> str:
    """`col` (a timestamptz expression) rendered in the operator's display timezone."""
    return f"({col} at time zone {_TZ_SQL})"


def _gap(v, default: int = _VISIT_GAP_MIN) -> int:
    """Idle minutes that end a visit, clamped to [1 minute, 12 hours]."""
    try:
        return max(1, min(720, int(v)))
    except (TypeError, ValueError):
        return default


def _visit_break(gap: int, part: str | None = "canon") -> str:
    """SQL: 1 on the FIRST event of a visit — no predecessor, or `gap`+ minutes of silence.
    Flagging each person's very first row too means `count(*) filter (where b = 1)` is exactly
    the visit count, with no separate "+1 per person" correction. `part=None` for a query
    already narrowed to one person. Both callers wrap the source in a subquery first, so
    `canon` is a real column here (a window function cannot see a sibling SELECT alias)."""
    over = f"over ({f'partition by {part} ' if part else ''}order by created_at, id)"
    return (f"case when lag(created_at) {over} is null "
            f"or created_at - lag(created_at) {over} > interval '{int(gap)} minutes' "
            "then 1 else 0 end")


def _visit_no(part: str | None = "canon") -> str:
    """SQL: running visit number within a person — a running sum of _visit_break's flag."""
    return (f"sum(b) over ({f'partition by {part} ' if part else ''}"
            "order by created_at, id rows unbounded preceding)")

# Canonical-identity CTE — built by `_cte(include_ident=True)`. Maps each mm_aid cookie to the
# Supabase user uuid it belongs to, EXCLUDING cookies signed into by 2+ accounts (ambiguous
# shared/kiosk devices — never merged). Prepend to a query that aliases analytics_events as `e`
# and left-joins `ident i`; then _CANON_VISITORS counts PEOPLE (a signed-in user's devices
# collapse to one), so the headline counts reconcile with the merged 'Frequent visitors' list.
_CANON_VISITORS = "count(distinct coalesce(i.uid, e.visitor_id))::int as visitors"

# ── Operator self-exclusion ────────────────────────────────────────────────────
# Hide the operator's own sessions/visitors from every analytics surface. Driven by
# admin/analytics_exclusions.json (registered emails, home locations, IPs, cookie ids)
# PLUS a baked-in loopback rule (below). See that file's _comment. All matching is done in SQL via the `excluded` CTE (below); the config values
# are the ONLY interpolated strings and every one goes through _sql_str (quotes doubled)
# on top of a JSON-typed load, so there is no injection surface.
# Path is env-overridable (same idiom as site_gate's SITE_GATE_STATE) so the operator can
# keep the hide-list in an untracked server file (e.g. /var/lib/macro-admin/…) instead of
# the committed default, keeping personal emails out of git history.
_EXCL_PATH = Path(os.environ.get(
    "ANALYTICS_EXCLUSIONS",
    str(Path(__file__).resolve().parent / "analytics_exclusions.json")))
# Non-identifying IPs — never used to LINK cookies (loopback/tunnel traffic is shared by
# many unrelated visitors, so linking on it would falsely merge/over-hide them).
_NON_ID_IPS = ("'unknown'", "'::1'", "'127.0.0.1'", "'localhost'")
# Loopback specifically. Both collectors resolve the client IP from the CDN/proxy headers and
# fall back to the socket peer (app/main.py:_mm_client_ip, terminal lib/rateLimit.ts:clientIp),
# and every public request arrives through Caddy with X-Forwarded-For set — so a loopback IP
# can ONLY be a request made ON the box: a `npm run dev` browser, a curl, an agent driving the
# app over a tunnel. That is never a visitor, so it is seeded into `excluded` by default (and
# from there its device-fingerprint siblings are hidden too). Distinct from _NON_ID_IPS: this
# HIDES on a loopback IP, that refuses to LINK on one — a shared 127.0.0.1 must not merge two
# unrelated dev machines, so linking still goes through the fingerprint only.
_LOOPBACK_IPS = ("'::1'", "'127.0.0.1'", "'localhost'")

# ── Crawler / bot detection (default-on; config can extend the patterns) ────────
# A visitor is a bot if ANY holds: its user-agent matches _DEFAULT_BOT_UA, its IP sits in a
# datacenter that is NOT a consumer VPN (is_hosting and not is_vpn — keeps real VPN users),
# the IP's network org matches _DEFAULT_BOT_ORG, the IP's ASN matches _DEFAULT_BOT_ASN, the IP
# is in the config bots.ips list, or its device fingerprint is a FARM fingerprint (see
# _FP_FANOUT).
# Bots are hidden from every surface by default but stay REVEALABLE (include_bots=1) and are
# counted, so detection is transparent and false positives are catchable. Behavioural signals
# (short dwell / bounce) are deliberately NOT used — real humans bounce too.
_DEFAULT_BOT_UA = (
    r"bot|crawl|spider|slurp|scrape|Googlebot|bingbot|DuckDuckBot|Baiduspider|YandexBot|"
    r"facebookexternalhit|meta-externalagent|Applebot|PetalBot|Bytespider|GPTBot|ClaudeBot|"
    r"Claude-Web|anthropic-ai|OAI-SearchBot|CCBot|Amazonbot|SemrushBot|AhrefsBot|DotBot|"
    r"MJ12bot|DataForSeo|python-requests|Go-http-client|node-fetch|axios|libwww|curl/|wget|"
    r"Scrapy|HeadlessChrome|PhantomJS"
)
_DEFAULT_BOT_ORG = (
    r"googlebot|google llc|google cloud|meta platforms|facebook|amazon|amazonaws|aws|"
    r"microsoft|azure|openai|anthropic|bytedance|censys|shodan|internet.?archive|"
    r"digitalocean|linode|hetzner|ovh|scaleway"
)
# ASN match is a belt-and-braces companion to _DEFAULT_BOT_ORG: some crawler/hosting IPs geolocate
# with an org string that doesn't literally contain the vendor name (proxy resellers, regional
# RIR records, etc.), but the ASN never lies. 15169 = Google LLC (Googlebot's home network),
# 396982 = Google Cloud Platform (GCP-hosted crawlers/services — confirmed against a batch of
# "visitor" IPs that were plain GCP traffic recurring in the admin Visitors list, 2026-08-02).
# `g.asn` is stored as returned by IPLocate (e.g. "AS396982" or "396982" depending on vendor
# response shape) so this matches on substring, not an exact cast, to be robust to either.
_DEFAULT_BOT_ASN = r"15169|396982"
# ── Fingerprint-farm detection ─────────────────────────────────────────────────
# A residential-proxy scraper defeats every signal above: it rotates through real consumer
# ISPs (Comcast, BT, Cox — is_hosting false, org clean) and sends an ordinary Chrome UA. What
# it CANNOT hide is that every request comes off the same headless image, so one fingerprint
# turns up under many cookies AND many IPs at once. Requiring BOTH counts is what makes the
# rule safe: a household or office behind one NAT gives many cookies on ONE IP; a roaming
# phone gives ONE cookie across many IPs; only a farm is wide on both axes. On this dataset
# the split is unambiguous — one fp at 74 cookies / 74 IPs across 8 countries (Oxylabs,
# code200, Latitude.sh …, 1 pageview + 1 click each, no dwell), and no real visitor above 1
# cookie. Farms land in `bots`, not `excluded`: hidden from every surface by default, but
# still counted and revealable via 'show bots', so the detection stays auditable.
_FP_FANOUT = 12

# ── Classifier-set cache (farm fingerprints, operator-excluded cookies) ─────────
# Two classifiers are properties of the WHOLE history, change slowly, and were being
# recomputed inside every panel statement on a small, shared instance:
#
#   fp_farm   "how many cookies and IPs share this fingerprint, ever" — a handful of shared
#             fingerprints carry most of the store (one alone: 82,680 events / 30,346
#             cookies), so the group-by was ~3s of a ~5s 24h Visitors fold.
#   excluded  the operator's own cookies + their fingerprint/IP-linked siblings — 2,152 ids,
#             ~1-4s standalone and up to 6.3s of the 7-day Sessions fold.
#
# (production 2026-11-12). The background warmer recomputes both once per pass and the
# panels inline the result as a literal. Row-identical to the live CTEs: `bots` only tests
# the fingerprints of in-window identities, and a global farm set restricted to those IS the
# windowed set; the global `excluded` set is a superset of the focused one whose extra
# members have no in-window event, so they cannot change an in-window row (the argument
# _cte(focus_excluded=) already rests on). Each entry is keyed on the exact live SQL it
# replaces, so an exclusions-config edit misses the cache instead of serving the old set.
# A miss, or an entry older than _CLASSIFIER_MAX_AGE_S (a local run, a fresh process, a
# stalled warmer), falls back to the live CTE: a stale cache costs speed, never more than
# one warm interval of lag.
_CLASSIFIER_MAX_AGE_S = float(os.environ.get("ANALYTICS_CLASSIFIER_MAX_AGE_S") or 900)
_CLASSIFIER_MAX_VALUES = 20000
_SET_VALUE_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_CLASSIFIER_LOCK = threading.Lock()
_CLASSIFIER_CACHE: dict = {}   # name -> {"key": str, "values": tuple, "at": float}


def _cached_set(name: str, key: str):
    """The cached value tuple for `name` computed from SQL `key`, or None when unusable."""
    with _CLASSIFIER_LOCK:
        c = _CLASSIFIER_CACHE.get(name)
    if not c or c["key"] != key or time.monotonic() - c["at"] > _CLASSIFIER_MAX_AGE_S:
        return None
    return c["values"]


def _refresh_set(name: str, key: str, sql: str, col: str) -> None:
    rows = _query(sql)
    if rows is None:
        return
    values = tuple(sorted({str(r.get(col)) for r in rows if r.get(col) is not None}))
    # Never cache a set that is not row-identical to the live CTE: an unexpected value shape
    # or an oversized literal leaves the live-CTE fallback in place (drop any old entry).
    if len(values) > _CLASSIFIER_MAX_VALUES or not all(_SET_VALUE_RE.match(v) for v in values):
        with _CLASSIFIER_LOCK:
            _CLASSIFIER_CACHE.pop(name, None)
        return
    with _CLASSIFIER_LOCK:
        _CLASSIFIER_CACHE[name] = {"key": key, "values": values, "at": time.monotonic()}


def _text_set_sql(values, col: str) -> str:
    if not values:
        return f"select null::text as {col} where false"
    return f"select unnest(array[{','.join(_sql_str(v) for v in values)}]::text[]) as {col}"


def _farm_fanout() -> int:
    try:
        return int(_load_exclusions()["bots"].get("fp_fanout", _FP_FANOUT))
    except (TypeError, ValueError):
        return _FP_FANOUT


def _farm_body_sql(fanout: int, where: str = "where fp is not null") -> str:
    return (f"select fp from public.analytics_events {where} group by fp "
            f"having count(distinct visitor_id) >= {fanout} and count(distinct ip) >= {fanout}")


def refresh_classifier_cache() -> None:
    """Recompute the cached global classifier sets (full-store; warmer only — nobody waits
    on it). Each set refreshes independently, so one failing leaves the other usable."""
    fanout = _farm_fanout()
    if fanout >= 2:
        try:
            body = _farm_body_sql(fanout)
            _refresh_set("farm", body, body, "fp")
        except Exception:  # noqa: BLE001 — a failed refresh leaves the live-CTE fallback
            pass
    try:
        ctes = _excluded_cte(live=True)
        _refresh_set("excluded", ctes, f"with {ctes} select visitor_id from excluded",
                     "visitor_id")
    except Exception:  # noqa: BLE001
        pass


def _sql_str(s) -> str:
    """A single-quoted SQL string literal with embedded quotes doubled (raw-SQL endpoint)."""
    return "'" + str(s).replace("'", "''") + "'"


def _routable(col: str) -> str:
    """SQL predicate: `col` is a real, identifying IP (not null, not loopback/unknown)."""
    return f"{col} is not null and {col} not in ({','.join(_NON_ID_IPS)})"


def _sanitize_q(v, maxlen: int = 64) -> str:
    """Free-text table filter → a safe fragment. Allows only letters, digits and the
    characters that appear in emails / UUIDs / IPs (@ . - : space). Strips quotes, `%`
    and `_` so the value is safe to inline inside an ILIKE pattern (no injection, no
    stray wildcards). Returns '' when nothing usable remains."""
    return re.sub(r"[^A-Za-z0-9@.\-: ]", "", str(v or ""))[:maxlen].strip()


def _clean_ips(seq) -> list:
    """Keep only plausible IP literals (digits, dots, colons, hex) — belt-and-braces before
    they are single-quoted into SQL. Blanks/garbage dropped."""
    out = []
    for v in (seq or []):
        s = re.sub(r"[^0-9a-fA-F.:]", "", str(v or ""))
        if s:
            out.append(s)
    return out


def _load_exclusions() -> dict:
    """Read the analytics-filter config. Missing/malformed → empty (nothing hidden/relabelled).

    Keys: emails[], locations[{city,region,country_code}], ips[], visitor_ids[] (operator
    self-exclusion); bots{ips[],ua_pattern,org_pattern,asn_pattern} (crawler filter — patterns
    EXTEND the baked-in defaults); geo_overrides[{ip_prefix,city,region,country_code,country}]
    (display relabel by IP prefix)."""
    empty = {"emails": [], "locations": [], "ips": [], "visitor_ids": [],
             "bots": {}, "geo_overrides": []}
    try:
        cfg = json.loads(_EXCL_PATH.read_text())
    except Exception:  # noqa: BLE001 — never break analytics on a bad config file
        return empty
    emails = [str(e).strip().lower() for e in (cfg.get("emails") or []) if str(e).strip()]
    locations = [l for l in (cfg.get("locations") or []) if isinstance(l, dict)]
    ips = _clean_ips(cfg.get("ips"))
    # Cookie ids to hide outright. Validated against the same shape the read endpoints
    # allowlist, so a typo'd entry is dropped rather than smuggled into SQL.
    vids = [str(v).strip() for v in (cfg.get("visitor_ids") or []) if _ID_RE.match(str(v).strip())]
    bots = cfg.get("bots") if isinstance(cfg.get("bots"), dict) else {}
    geo = [o for o in (cfg.get("geo_overrides") or [])
           if isinstance(o, dict) and str(o.get("ip_prefix") or "").strip()]
    return {"emails": emails, "locations": locations, "ips": ips, "visitor_ids": vids,
            "bots": bots, "geo_overrides": geo}


def _excluded_cte(*, focus_visitors: bool = False, live: bool = False) -> str:
    """CTE bodies (excl_users, excl_geo_ips, excl_ips, excl_vids, excl_seed, excl_link,
    excluded) — always syntactically valid regardless of config. `excluded` is the set of
    visitor_id cookies to hide: the operator's own (via registered email, a home-location IP,
    a listed IP, a listed cookie id, or a loopback IP — see _LOOPBACK_IPS) PLUS the cookies
    linked to them by shared device fingerprint or routable IP.

    When the warmer holds a fresh global `excluded` set for this exact config, `excluded`
    is that literal (see _CLASSIFIER_CACHE); excl_seed/excl_link are then unreferenced and
    Postgres never executes them. `live=True` forces the computed form (the warmer's own
    refresh, and the cache key)."""
    if not live:
        global_sql = _excluded_cte(live=True)
        cached = _cached_set("excluded", global_sql)
        if cached is not None:
            head = global_sql[:global_sql.index("excluded as (")]
            return head + f"excluded as ({_text_set_sql(cached, 'visitor_id')})"
    cfg = _load_exclusions()
    # Only pages projects OUTPUT IDs; global seeds/anchors/customer history stay intact.
    target_focus = " and e2.visitor_id in (select visitor_id from focus_visitors)" if focus_visitors else ""
    seed_focus = " where visitor_id in (select visitor_id from focus_visitors)" if focus_visitors else ""
    # The site administrator is the operator, not a customer. Always suppress the
    # exact registered admin identity and its linked cookies from visitor analytics.
    # Preserve the private exclusion config for additional operator identities.
    operator_emails = set(cfg["emails"]) | {"admin@mastermind-x.com"}
    if operator_emails:
        emails = ",".join(_sql_str(e) for e in sorted(operator_emails))
        users_body = f"select id from auth.users where lower(email) in ({emails})"
    else:
        users_body = "select id from auth.users where false"
    preds = []
    for loc in cfg["locations"]:
        terms = []
        if loc.get("city"):
            terms.append(f"lower(g.city) = lower({_sql_str(loc['city'])})")
        if loc.get("region"):
            terms.append(f"lower(g.region) = lower({_sql_str(loc['region'])})")
        if loc.get("country_code"):
            terms.append(f"upper(g.country_code) = upper({_sql_str(loc['country_code'])})")
        if terms:
            preds.append("(" + " and ".join(terms) + ")")
    geo_body = (f"select ip from public.ip_geo g where {' or '.join(preds)}"
                if preds else "select ip from public.ip_geo where false")
    ips_body = (f"select unnest(array[{','.join(_sql_str(i) for i in cfg['ips'])}]::text[]) as ip"
                if cfg["ips"] else "select null::text as ip where false")
    vids_body = (
        f"select unnest(array[{','.join(_sql_str(v) for v in cfg['visitor_ids'])}]::text[]) as visitor_id"
        if cfg["visitor_ids"] else "select null::text as visitor_id where false")
    return (
        f"excl_users as ({users_body}), "
        f"excl_geo_ips as ({geo_body}), "
        f"excl_ips as ({ips_body}), "
        f"excl_vids as ({vids_body}), "
        # The seed is the same shape as `excl_link` below, and had the same defect: an OR
        # across FIVE different columns is not a join Postgres can hash or merge on, so it
        # planned the only thing left — one seq scan of the entire store evaluating four
        # hashed subplans per row. Measured on production 2026-11-09 (302,456 rows / 192 MB)
        # this CTE alone was 7,056ms, the largest remaining term in the Visitors fold after
        # `ident` got its index. `a or b` over a set we only read as DISTINCT visitor_id is
        # `a` UNION `b`, and each arm on its own is a plain membership test that an index can
        # drive (visitor_user / ip / visitor / ip respectively), so the same rows now come
        # back from five short index probes. Same rows: both forms read the same predicate
        # over the same table, and UNION de-duplicates exactly as `select distinct` did.
        "excl_seed as ("
        "  select e.visitor_id from public.analytics_events e "
        "    where e.user_id in (select id from excl_users) and e.visitor_id is not null "
        "  union "
        "  select e.visitor_id from public.analytics_events e "
        "    where e.ip in (select ip from excl_geo_ips) and e.visitor_id is not null "
        "  union "
        "  select e.visitor_id from public.analytics_events e "
        "    where e.ip in (select ip from excl_ips) and e.visitor_id is not null "
        "  union "
        "  select e.visitor_id from public.analytics_events e "
        "    where e.visitor_id in (select visitor_id from excl_vids) "
        "  union "
        "  select e.visitor_id from public.analytics_events e "
        f"    where e.ip in ({','.join(_LOOPBACK_IPS)}) and e.visitor_id is not null), "
        # An OR across two DIFFERENT join keys is not a join Postgres can hash or merge,
        # so it planned the only thing left: a nested loop evaluating the predicate for
        # every (event x anchor) pair. Measured on production 2026-08-26 — 58,702 rows
        # against 271 anchors = 15.9M filter evaluations, 3.75s of this CTE's 3.9s, on a
        # 58k-row / 40MB table. `excluded` is embedded in EVERY statement of EVERY
        # analytics tab, so that nested loop was the floor under the whole surface.
        #
        # `a or b` over a set we only read as DISTINCT visitor_id is `a` UNION `b`, and
        # each arm on its own is a plain equi-join the planner hashes. Same rows —
        # both definitions evaluated in ONE statement against the live table, symmetric
        # difference 0 (a count match would not have been proof, and a two-round-trip
        # comparison could not tell a real difference from an event landing between
        # them). 2.79s -> 0.58s, of which ~0.34s is the API round trip itself.
        "excl_link as ("
        "  select e2.visitor_id from public.analytics_events e2 "
        "    join (select distinct fp from public.analytics_events "
        "          where visitor_id in (select visitor_id from excl_seed) "
        "            and fp is not null) kf on kf.fp = e2.fp "
        f"  where e2.visitor_id is not null and e2.fp is not null{target_focus} "
        "  union "
        "  select e2.visitor_id from public.analytics_events e2 "
        "    join (select distinct ip from public.analytics_events "
        "          where visitor_id in (select visitor_id from excl_seed) "
        f"            and {_routable('ip')}) ki on ki.ip = e2.ip "
        f"  where e2.visitor_id is not null and {_routable('e2.ip')}{target_focus}), "
        # Implicit fingerprint/IP linkage must never hide a *different, verified*
        # account merely because that customer shares a VPN exit or household IP
        # with the operator. Preserve explicit exclusion seeds (e.g. configured
        # IPs, cookies and registered operator accounts) without this restriction.
        f"excluded as (select visitor_id from excl_seed{seed_focus} "
        "             union select l.visitor_id from excl_link l "
        "               where not exists (select 1 from public.analytics_events e3 "
        "                 where e3.visitor_id = l.visitor_id "
        "                   and e3.user_id is not null "
        "                   and e3.user_id not in (select id from excl_users)))"
    )


def _bot_cte(window_minutes: int | None = None, *, include_search: bool = False) -> str:
    """CTE bodies (bot_ips, fp_farm, bots) — the visitor_ids that look like crawlers/automation.
    Signals: config bot IPs, a bot user-agent, a datacenter-but-not-VPN IP, a known crawler
    network org, a known crawler network ASN, or a farm fingerprint. Patterns come from the
    baked-in defaults, EXTENDED by config; the farm threshold is `bots.fp_fanout` (default
    _FP_FANOUT, <2 disables)."""
    cfg = _load_exclusions()
    bots_cfg = cfg["bots"]
    ua = _DEFAULT_BOT_UA + (f"|{bots_cfg['ua_pattern']}" if bots_cfg.get("ua_pattern") else "")
    org = _DEFAULT_BOT_ORG + (f"|{bots_cfg['org_pattern']}" if bots_cfg.get("org_pattern") else "")
    asn = _DEFAULT_BOT_ASN + (f"|{bots_cfg['asn_pattern']}" if bots_cfg.get("asn_pattern") else "")
    bot_ips = _clean_ips(bots_cfg.get("ips"))
    ips_body = (f"select unnest(array[{','.join(_sql_str(i) for i in bot_ips)}]::text[]) as ip"
                if bot_ips else "select null::text as ip where false")
    fanout = _farm_fanout()
    focus = ""
    focus_prefix = ""
    if window_minutes:
        minutes = int(window_minutes)
        focus_parts = [
            "select distinct visitor_id from public.analytics_events "
            f"where visitor_id is not null and created_at > now() - interval '{minutes} minutes'"
        ]
        if include_search:
            focus_parts.append(
                "select distinct anon_id as visitor_id from public.search_events "
                f"where anon_id is not null and created_at > now() - interval '{minutes} minutes'"
            )
        focus_prefix = (
            "focus_visitors as (" + " union ".join(focus_parts) + "), "
            "focus_fp as (select distinct e.fp from public.analytics_events e "
            "where e.visitor_id in (select visitor_id from focus_visitors) and e.fp is not null), ")
        focus = " and visitor_id in (select visitor_id from focus_visitors)"
    farm_where = "where fp is not null"
    if window_minutes:
        farm_where += " and fp in (select fp from focus_fp)"
    cached = _cached_set("farm", _farm_body_sql(fanout)) if fanout >= 2 else None
    if fanout < 2:
        farm_body = "select null::text as fp where false"
    elif cached is not None:
        farm_body = _text_set_sql(cached, "fp")
    else:
        farm_body = _farm_body_sql(fanout, farm_where)
    # A prefix the operator manually relabelled (geo_overrides) is a curated REAL user —
    # never let the datacenter/org heuristic auto-flag it as a bot (e.g. a residential-VPN
    # exit read as datacenter).
    keep = [str(o.get("ip_prefix")) for o in cfg["geo_overrides"] if o.get("ip_prefix")]
    keep_clause = (" and not (" + " or ".join(f"e.ip like {_sql_str(p + '%')}" for p in keep) + ")"
                   if keep else "")
    return (
        focus_prefix +
        f"bot_ips as ({ips_body}), "
        f"fp_farm as ({farm_body}), "
        # Each signal is a function of ONE column, so classify that column's small set of
        # distinct values once, then test events against the classified sets by hashed
        # membership. The 40-branch case-insensitive UA regex runs once per distinct
        # user-agent (not per event, nor per (visitor, ua, ip, fp) tuple), and the network
        # rules run once per ip_geo row. The previous form distincted every wide
        # (visitor_id, ua, ip, fp) tuple first; on the 7-day window that was 136k rows into
        # 37k groups and 5.7s of a 10.7s Visitors fold (production 2026-11-12). Same set:
        # `ip_geo.ip` is the primary key, so the old left join contributed at most one geo
        # row per ip — exactly `e.ip in bot_net`; `ua in bot_ua` is `ua is not null and ua ~*`;
        # and the keep-prefix guard still applies to the same event's ip.
        # MATERIALIZED is load-bearing: without the fence the planner pushes the regex
        # below the DISTINCT and evaluates it on every event row — 253k evaluations,
        # 26s on the 7-day window (production 2026-11-12) — instead of ~330 distinct UAs.
        "ua_seen as materialized (select distinct ua from public.analytics_events "
        f"  where visitor_id is not null and ua is not null{focus}), "
        f"bot_ua as (select ua from ua_seen where ua ~* {_sql_str(ua)}), "
        "bot_net as (select ip from bot_ips union "
        "  select g.ip from public.ip_geo g where "
        "    (g.is_hosting is true and coalesce(g.is_vpn, false) = false) "
        f"    or (g.org is not null and g.org ~* {_sql_str(org)}) "
        f"    or (g.asn is not null and g.asn::text ~* {_sql_str(asn)})), "
        # MATERIALIZED: computed once per statement. Inlined, the planner emitted it as two
        # separate subplans in the Visitors/Sessions folds (the full-history fp_farm group-by
        # twice) — measured 3.3s + 2.1s on the 24h Visitors statement, production 2026-11-12.
        "bots as materialized (select distinct e.visitor_id from public.analytics_events e "
        f"  where e.visitor_id is not null{focus} and ("
        "    e.ip in (select ip from bot_net) "
        "    or e.ua in (select ua from bot_ua) "
        "    or e.fp in (select fp from fp_farm))"
        f"{keep_clause})"
    )


_IDENT_CTE = (
    "ident as (select visitor_id, max(user_id::text) as uid "
    "from public.analytics_events where visitor_id is not null and user_id is not null "
    "group by visitor_id having count(distinct user_id) = 1)")


def _candidate_cte(window_minutes: int | None = None) -> str:
    """CTE (`uanchor`, `cand_fp`, `cand_ip`, `cand`) that links an ANONYMOUS cookie to the
    registered user it MOST LIKELY belongs to, via a device fingerprint or routable IP it shares
    with that user's login-attributed events.

    This is SOFT attribution — a heuristic suggestion, never a merge: `cand` is only left-joined at
    read time to annotate a row, and the PEOPLE/session/event counts are never computed from it. A
    cookie is linked to a uid only when the shared anchor maps to EXACTLY ONE registered user
    (count(distinct uid)=1); a fingerprint/IP shared by two accounts is ambiguous and dropped,
    mirroring the `ident` 2+-accounts rule so one person's activity is never mis-attributed. A
    fingerprint match ('device') is stronger than an IP match ('ip') and wins when both exist; IPs
    are used only when routable (loopback/tunnel/unknown never link — same `_routable` guard the
    operator-exclusion linker uses). Requires the `ident` CTE to precede it in the `with` chain.

    `window_minutes` bounds every analytics_events scan here to the same period the calling surface
    shows (via the created_at index), so this linkage never adds an unbounded full-table scan to
    the panel query — matching is within the displayed window on BOTH the cookie and anchor sides."""
    win = (f" and e.created_at > now() - interval '{int(window_minutes)} minutes'"
           if window_minutes else "")
    wwin = (f" where e.created_at > now() - interval '{int(window_minutes)} minutes'"
            if window_minutes else "")
    return (
        # Anchors: the distinct (uid, fp, ip) points where a KNOWN user has been seen (their
        # stitched events). `distinct` keeps the fan-out into the two joins below bounded.
        "uanchor as (select distinct i.uid, e.fp, e.ip from public.analytics_events e "
        f"  join ident i on i.visitor_id = e.visitor_id{wwin}), "
        # A cookie sharing a fingerprint with exactly one user → that user (device-strength link).
        "cand_fp as (select e.visitor_id, min(a.uid) as uid "
        "  from public.analytics_events e join uanchor a on a.fp = e.fp and e.fp is not null "
        f"  where e.visitor_id is not null{win} "
        "  group by e.visitor_id having count(distinct a.uid) = 1), "
        # A cookie sharing a routable IP with exactly one user → that user (IP-strength link).
        "cand_ip as (select e.visitor_id, min(a.uid) as uid "
        f"  from public.analytics_events e join uanchor a on a.ip = e.ip "
        f"    and {_routable('e.ip')} and {_routable('a.ip')} "
        f"  where e.visitor_id is not null{win} "
        "  group by e.visitor_id having count(distinct a.uid) = 1), "
        # Collapse to one candidate per cookie: fingerprint wins over IP; carry the basis for display.
        "cand as (select v.visitor_id, coalesce(f.uid, p.uid) as uid, "
        "    case when f.uid is not null then 'device' else 'ip' end as basis "
        "  from (select visitor_id from cand_fp union select visitor_id from cand_ip) v "
        "  left join cand_fp f on f.visitor_id = v.visitor_id "
        "  left join cand_ip p on p.visitor_id = v.visitor_id)"
    )


def _cte(include_ident: bool = False, include_candidate: bool = False,
         candidate_window: int | None = None, bot_window: int | None = None,
         bot_include_search: bool = False, focus_excluded: bool = False) -> str:
    """Full `with …` prefix: the excluded-visitor + bot chains, optionally preceded by `ident`
    and followed by the soft candidate-identity chain (which requires `ident`). `candidate_window`
    (minutes) bounds the candidate scans to the surface's window.

    `focus_excluded` bounds the `excluded` chain to the surface's window, the same shape
    `_pages_cte` already uses. It requires `bot_window`, because the bot chain is what
    declares `focus_visitors` and the bounded exclusion reads it — so the bot chain is
    emitted FIRST. Row-identical for every surface that passes it: those surfaces only
    ever read in-window events, so an excluded cookie with no in-window event cannot
    change a row. Measured on production 2026-11-10, the unbounded `excl_link` arm was
    1,452ms / 81,810 buffers scanning 123,819 rows across the WHOLE store; bounding it
    to the window took the full Visitors fold 3.31s -> 2.23s and 318,790 -> 253,016
    buffers, with the payload byte-identical."""
    parts = []
    if include_ident or include_candidate:
        parts.append(_IDENT_CTE)
    if focus_excluded:
        if not bot_window:
            raise ValueError("focus_excluded requires bot_window (it declares focus_visitors)")
        parts.append(_bot_cte(bot_window, include_search=bot_include_search))
        parts.append(_excluded_cte(focus_visitors=True))
    else:
        parts.append(_excluded_cte())
        parts.append(_bot_cte(bot_window, include_search=bot_include_search))
    if include_candidate:
        parts.append(_candidate_cte(candidate_window))
    return "with " + ", ".join(parts) + " "


def _not_a_bot(alias: str = "e") -> str:
    """WHERE fragment that drops crawler/automation cookies. Null visitor_id is KEPT."""
    if alias:
        return _not_member(f"{alias}.visitor_id", "bots")
    return "(visitor_id is null or visitor_id not in (select visitor_id from bots))"


def _not_member(col: str, cte: str) -> str:
    """`col` is NOT one of the visitor_ids in `cte` — as an anti-join, not `not in`.

    `x not in (select ...)` can only be hashed when the planner believes the whole set fits
    in hash memory; otherwise it re-scans the set once PER OUTER ROW. On the 30-day Sessions
    fold the planner over-estimated `excluded` at 287k rows (actual: 797), chose the linear
    form, and re-scanned it 210,022 times — 37s of a 67s statement (production 2026-11-12).
    `not exists` plans as a hash anti-join regardless of that estimate. Row-identical here:
    neither set ever holds a NULL visitor_id (every arm filters it), and a NULL `col` matches
    nothing, so it is kept exactly as the `col is null or ...` guard kept it. Needs a
    qualified `col`; an unaliased caller keeps the `not in` form."""
    return f"not exists (select 1 from {cte} nx where nx.visitor_id = {col})"


def _apply_geo_overrides(rows, ip_key: str = "ip"):
    """Relabel the displayed location of rows whose IP starts with a configured prefix
    (fixes IPs geolocated to the wrong place — e.g. an HK VPN read as Frankfurt). Applied at
    read time in Python so a single stale ip_geo row can't misfile a whole prefix. Mutates
    and returns `rows`."""
    ovr = _load_exclusions()["geo_overrides"]
    if not ovr or not rows:
        return rows
    for r in rows:
        ip = str(r.get(ip_key) or "")
        if not ip:
            continue
        for o in ovr:
            if ip.startswith(str(o.get("ip_prefix"))):
                for fld in ("city", "region", "country_code", "country"):
                    if o.get(fld):
                        r[fld] = o[fld]
                break
    return rows


def _not_excluded(alias: str = "e") -> str:
    """WHERE fragment that drops the operator's hidden cookies. `alias` = table alias
    holding visitor_id ('' for an unaliased table). Null visitor_id is KEPT (it can't be a
    hidden cookie, and a bare `not in` would drop it via SQL three-valued logic)."""
    if alias:
        return _not_member(f"{alias}.visitor_id", "excluded")
    return "(visitor_id is null or visitor_id not in (select visitor_id from excluded))"


def _not_excluded_search() -> str:
    """WHERE fragment for public.search_events (no visitor_id column): drop the operator's
    rows by anon cookie (which already carries the hidden-cookie-id and loopback seeds through
    `excluded`), registered user, home-location IP, listed IP, or loopback IP — searches fired
    from a dev server have no cookie the beacon ever saw. Each arm keeps NULLs."""
    return ("(anon_id is null or anon_id not in (select visitor_id from excluded)) "
            "and (user_id is null or user_id not in (select id from excl_users)) "
            "and (ip is null or ip not in (select ip from excl_geo_ips)) "
            "and (ip is null or ip not in (select ip from excl_ips)) "
            f"and (ip is null or ip not in ({','.join(_LOOPBACK_IPS)}))")


def status() -> dict:
    pat = settings.supabase_pat()
    configured = bool(pat and requests)
    reason = None
    if not configured:
        reason = ("requests not installed" if not requests else
                  "SUPABASE_ACCESS_TOKEN (sbp_… personal access token) not set")
    return {
        "configured": configured,
        "project_ref": settings.supabase_project_ref(),
        "reason": reason,
        "setup_steps": [
            "Apply supabase/migrations/0004_analytics.sql (+ 0003) to the Supabase project.",
            "Set SUPABASE_ACCESS_TOKEN (sbp_… PAT) in the admin service env.",
            "Add the tracker: templates/theme.js beacon (macro) + the Terminal <Tracker/> ship live.",
        ],
    }


_QUERY_TIMEOUT_S = 9
_OVERVIEW_ALLTIME_TIMEOUT_S = 0.75

# Sort/hash memory for one analytics statement. This instance ships OLTP defaults —
# work_mem is 2MB — while the visit fold sorts ~19k wide rows per statement, so every one
# of those sorts spilled to disk. That cost was invisible to EXPLAIN: it is not a bad plan,
# it is a sort that cannot fit, and no index reaches a window fold. Measured on production
# 2026-11-09 through this endpoint (24h, median of 2, same statements):
#     default 2MB   13,848ms      SET LOCAL 8MB   4,329ms      SET LOCAL 16MB   6,580ms
# work_mem is an UPPER BOUND that a node only allocates when it actually sorts or hashes,
# so the prelude is inert for the small panels. 16MB rather than 8MB because Sessions (the
# wider fold) still measured 9.7s at 8MB against 6.1s at 16MB. The panel fans out at most
# 6 statements at once, so the worst case is ~192MB of transient sort memory on a box with
# 224MB of shared_buffers; it is set per statement, not per session, and does not leak.
_QUERY_PRELUDE = "set local work_mem = '16MB'; "

# Server-side cancellation. The HTTP read timeout below only stops THIS process waiting;
# Postgres keeps executing the statement until the role's own statement_timeout (2min on
# this project). Measured on production 2026-11-12: six abandoned Visitors/Sessions folds
# were still running 46s-1m53s after their panels had already reported the 9s timeout,
# each retry and warm pass stacking another on a small instance — so a bare
# `select count(*)` on the analytics table took 11.9s and every panel stayed cold and
# slow. Bounding the statement to the same budget the caller waits for makes an
# abandoned query die with its request instead of starving the next one.
def _statement_timeout_sql(timeout_s: float) -> str:
    return f"set local statement_timeout = '{max(500, int(timeout_s * 1000))}ms'; "

# Whole-surface budget. Every panel here is a chain of round trips to the Supabase
# Management API, and admin.mastermind-x.com is served THROUGH a CDN edge (see the
# admin block in app/deploy/Caddyfile) — so an endpoint that outruns the edge's
# origin-pull timeout does not fail as this module's {ok:False,...} envelope. It
# fails as the EDGE's error response, which reaches app.js as a body that is not
# JSON at all. That is the "bad json" the console was reporting: not a serialization
# bug in here, a request that never got to finish.
#
# Bounding the whole surface below the edge's patience is what makes the failure
# legible: whatever else goes wrong, the operator gets a JSON error naming the
# timeout instead of a gateway page the SPA can only describe as malformed.
#
# 22.0 was NOT below it. Measured on production 2026-08-26: `overview` folded in
# 14.9s at the origin and the admin journal recorded BrokenPipeError writing the
# response — the edge had already hung up and answered the browser 524 with an
# empty body, which is exactly the panel error the operator was looking at. So the
# budget has to sit under the edge's real patience, and the evidence says that is
# somewhere below 15s. The edge's exact configured origin-pull timeout is NOT
# measured here (it is EdgeOne zone config, not repo state; 15s is its documented
# default and matches what we observed) — 10s is chosen to be under it with room
# to spare, and to stay far above what these panels now actually cost: after the
# `excluded`/`bots` rewrites above, the slowest surface folds in ~2s.
#
# If a panel ever does hit this, the answer the operator gets is the honest one —
# a JSON error naming the budget — not a gateway page.
_REQUEST_BUDGET_S = 10.0
_DEADLINE: contextvars.ContextVar[float | None] = contextvars.ContextVar(
    "fp_deadline", default=None)
# Per-query and per-surface overrides, set only by the background warmer (below). They
# exist because the warmer is the one caller nobody waits on, so it may exceed the panel
# budget that protects the operator's request. Context-local, so a warm pass can never
# widen the budget of a concurrent operator request.
_BASE_TIMEOUT: contextvars.ContextVar[float | None] = contextvars.ContextVar(
    "fp_base_timeout", default=None)
_BUDGET_OVERRIDE: contextvars.ContextVar[float | None] = contextvars.ContextVar(
    "fp_budget_override", default=None)

# The management endpoint is one shared upstream; a handful of concurrent statements
# per surface is the point, a stampede is not.
_FANOUT_MAX_WORKERS = 6


def _remaining_budget() -> float | None:
    """Seconds left in this surface's budget, or None when no deadline is set."""
    deadline = _DEADLINE.get()
    return None if deadline is None else deadline - time.monotonic()


def _parallel(**thunks):
    """Run INDEPENDENT _query thunks concurrently, returning {name: result}.

    Every caller below was written as a straight-line sequence of `_query(...)`
    assignments, which meant a panel paid the SUM of its round trips: the default
    Analytics tab alone fired six, so a half-second statement became a three-second
    page. None of these statements consumes another's result (checked per call site),
    so the sum was never necessary — the wall time is now the slowest single query.

    Each thunk runs in a fresh copy of the calling context so the deadline set by
    _guard is visible inside the worker threads; ThreadPoolExecutor does not
    propagate contextvars on its own, and one Context cannot be entered by two
    threads at once, hence a copy per thunk rather than a shared one.

    Exceptions propagate out of .result() to _guard, which is what turns a failed
    statement into the {ok: False, error: ...} envelope the SPA renders.
    """
    if len(thunks) <= 1:
        return {name: fn() for name, fn in thunks.items()}
    with ThreadPoolExecutor(max_workers=min(len(thunks), _FANOUT_MAX_WORKERS),
                            thread_name_prefix="fp-analytics") as pool:
        futures = {name: pool.submit(contextvars.copy_context().run, fn)
                   for name, fn in thunks.items()}
        return {name: fut.result() for name, fut in futures.items()}


def _query(sql: str, timeout_cap_s: float | None = None):
    pat = settings.supabase_pat()
    if not (pat and requests):
        return None
    ref = settings.supabase_project_ref()
    base = _BASE_TIMEOUT.get() or _QUERY_TIMEOUT_S
    timeout = base
    remaining = _remaining_budget()
    if remaining is not None:
        if remaining <= 0:
            raise TimeoutError(
                f"analytics query budget exhausted ({_REQUEST_BUDGET_S:.0f}s) — "
                "narrow the time window and retry")
        timeout = max(1.0, min(float(base), remaining))
    if timeout_cap_s is not None:
        timeout = min(timeout, max(0.5, float(timeout_cap_s)))
    try:
        r = requests.post(
            f"{_API}/projects/{ref}/database/query",
            headers={"Authorization": f"Bearer {pat}", "Content-Type": "application/json"},
            json={"query": _statement_timeout_sql(timeout) + _QUERY_PRELUDE + sql},
            timeout=timeout + 1.0)
    except requests.exceptions.Timeout:
        # urllib3's own wording ("HTTPSConnectionPool(host='api.supabase.com', port=443):
        # Read timed out. (read timeout=9.0)") was reaching the operator verbatim. It names
        # the TRANSPORT, which is the wrong place to look: measured on production 2026-11-09,
        # a bare `select 1` through this endpoint answers in 1.4s while one full-store scan
        # takes 9-31s — so a read timeout here is the STATEMENT outrunning the budget, not the
        # network. Say that, and say which budget.
        raise TimeoutError(
            f"analytics query did not finish within {timeout:.1f}s "
            "(Supabase Management API) — a full-store scan outran the panel budget; "
            "narrow the window and retry") from None
    if not (200 <= r.status_code < 300):   # the query endpoint answers 201 on success
        if "57014" in r.text or "statement timeout" in r.text:
            # The server-side statement_timeout above fired: same budget, same honest message.
            raise TimeoutError(
                f"analytics query did not finish within {timeout:.1f}s "
                "(Supabase Management API) — a full-store scan outran the panel budget; "
                "narrow the window and retry")
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
    return r.json()


def _optional_query(sql: str, *, timeout_cap_s: float, default):
    """Best-effort secondary metric. Core panel queries must still fail truthfully."""
    try:
        return _query(sql, timeout_cap_s=timeout_cap_s)
    except Exception:  # noqa: BLE001 — secondary metric must not blank the whole panel
        return default


def _days(v, default: int = 7) -> int:
    try:
        return max(1, min(365, int(v)))
    except (TypeError, ValueError):
        return default


def _minutes(v, default_min: int) -> int:
    """Window in MINUTES, clamped to [1 minute, 365 days]. Powers the sub-day time presets."""
    try:
        return max(1, min(365 * 1440, int(float(v))))
    except (TypeError, ValueError):
        return default_min


def _win(minutes, days, default_min: int) -> int:
    """Effective window in MINUTES. `minutes` wins (sub-day presets); else the legacy `days`
    param (x 1440); else `default_min`. Lets old ?days= callers and new ?minutes= callers coexist."""
    if minutes is not None and str(minutes).strip() != "":
        return _minutes(minutes, default_min)
    if days is not None and str(days).strip() != "":
        return _days(days) * 1440
    return default_min


def _bucket(m: int) -> tuple:
    """(date_trunc unit, to_char fmt) for a time series over an m-minute window — chosen so the
    chart has a readable point count. Unit is whitelisted (minute/hour/day) so it's injection-safe."""
    if m <= 180:
        return ("minute", "HH24:MI")      # <= 3h
    if m <= 4320:
        return ("hour", "MM-DD HH24:MI")  # <= 3d
    return ("day", "YYYY-MM-DD")


def _limit(v, default: int = 50, hi: int = 500) -> int:
    try:
        return max(1, min(hi, int(v)))
    except (TypeError, ValueError):
        return default


def _guard(fn):
    if not status()["configured"]:
        return {"ok": False, **status()}
    # Open the surface's budget here, so every _query underneath it — including the
    # ones _parallel runs on worker threads — shares one deadline rather than each
    # getting its own independent 20s.
    budget = _BUDGET_OVERRIDE.get() or _REQUEST_BUDGET_S
    token = _DEADLINE.set(time.monotonic() + budget)
    try:
        return {"ok": True, **fn()}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}
    finally:
        _DEADLINE.reset(token)


# ── Background warm ────────────────────────────────────────────────────────────
# The two heaviest panels fold a 216MB table against a 224MB shared_buffers, so their
# pages do not stay resident between visits. Measured on production 2026-11-10: the
# Visitors fold is 2.2s warm and 23.4s cold, and the panel budget is 9s (the edge proxy
# hangs up below 15s, so the budget cannot simply be raised). A cold panel therefore
# fails before it can warm itself, and every retry starts cold again — the deadlock the
# operator sees as "Couldn't load this panel". This loop breaks it: it re-runs the two
# panels on a timer so their pages stay hot, and it is the only caller allowed to exceed
# the panel budget, because nobody is waiting on it. Set ANALYTICS_WARM_INTERVAL_S=0 to
# disable; the interval is the only knob that costs the shared store anything.
_WARM_INTERVAL_S = float(os.environ.get("ANALYTICS_WARM_INTERVAL_S") or 120)
_WARM_QUERY_TIMEOUT_S = float(os.environ.get("ANALYTICS_WARM_QUERY_TIMEOUT_S") or 60)
_WARM_BUDGET_S = float(os.environ.get("ANALYTICS_WARM_BUDGET_S") or 90)


def warm_panels() -> None:
    """One warm pass over the two heaviest panels. Never raises."""
    try:
        if not status()["configured"]:
            return
    except Exception:  # noqa: BLE001 — a warm pass must never take the server down
        return
    t_base = _BASE_TIMEOUT.set(_WARM_QUERY_TIMEOUT_S)
    t_budget = _BUDGET_OVERRIDE.set(_WARM_BUDGET_S)
    try:
        refresh_classifier_cache()   # first, so the panel warms below already use it
        for fn in (visitors, sessions):
            try:
                fn(limit=100, minutes=1440)
            except Exception:  # noqa: BLE001 — one panel failing must not stop the other
                pass
    finally:
        _BUDGET_OVERRIDE.reset(t_budget)
        _BASE_TIMEOUT.reset(t_base)


def start_warmer() -> threading.Thread | None:
    """Start the daemon warm loop. Returns the thread, or None when disabled."""
    if _WARM_INTERVAL_S <= 0:
        return None

    def loop():
        while True:
            warm_panels()
            time.sleep(_WARM_INTERVAL_S)

    thread = threading.Thread(target=loop, name="fp-analytics-warm", daemon=True)
    thread.start()
    return thread


# ---------- surfaces ----------
def overview(days=7, minutes=None, gap=None) -> dict:
    m = _win(minutes, days, 10080)
    g = _gap(gap)
    trunc, fmt = _bucket(m)
    # The five live-window projections share the same identity/exclusion/bot population.
    # Compute that population ONCE inside one SQL statement instead of paying for the same
    # classifier in five concurrent Management-API requests. On production's 106k-row
    # analytics table this cut the 24h core fold from ~2.5-3.2s to ~1.0s.
    dt = f"date_trunc('{trunc}', {_lt('created_at')})"
    def run():
        human = f"and {_not_excluded('e')} and {_not_a_bot('e')}"
        core_sql = (
            _cte(include_ident=True, bot_window=m)
            + ", he as (select e.*, i.uid, coalesce(i.uid,e.visitor_id) as canon "
              "from public.analytics_events e left join ident i on i.visitor_id=e.visitor_id "
            + f"where e.created_at > now() - interval '{m} minutes' {human}), "
            + "vb as (select canon,created_at,id,"
            + _visit_break(g)
            + " as b from he where visitor_id is not null) "
            + "select "
            + "(select json_build_object("
              "'events',count(*)::int,"
              "'visitors',count(distinct canon)::int,"
              "'pageviews',count(*) filter (where type in ('pageview','route'))::int,"
              "'ticker_views',count(*) filter (where type='ticker_view')::int,"
              "'searches',count(*) filter (where type='search')::int"
              ") from he) as win, "
            + "(select count(*) filter (where b=1)::int from vb) as sessions, "
            + "(select coalesce(json_agg(row_to_json(x)),'[]'::json) from ("
              "select site,count(*)::int as events,count(distinct canon)::int as visitors "
              "from he group by site order by events desc,site) x) as by_site, "
            + "(select coalesce(json_agg(row_to_json(x)),'[]'::json) from ("
            + f"select to_char({dt},'{fmt}') as day,"
              "count(distinct canon)::int as visitors,count(*)::int as events "
            + f"from he group by {dt} order by {dt}) x) as daily, "
            + "(select json_build_object("
              "'visitors',count(distinct e.visitor_id)::int,"
              "'events',count(*)::int) "
              "from public.analytics_events e "
            + f"where e.created_at > now() - interval '{m} minutes' "
              f"and {_not_excluded('e')} "
              "and e.visitor_id in (select visitor_id from bots)) as bots"
        )
        core = (_query(core_sql) or [{}])[0] or {}
        # The all-time count runs AFTER the core fold, never beside it. It is a full-history
        # scan of a 192MB table against a 224MB shared_buffers, capped at 0.75s — so it is
        # cancelled part-way through after having pulled most of the store through the cache
        # and evicted the pages the MANDATORY statement was about to read. Run concurrently it
        # made the panel it decorates slower: measured on production 2026-11-09, overview
        # returned in 3.55s on a warm pool and then failed its 9s budget on five consecutive
        # calls once this probe had run, and the next Visitors/Sessions statements came back
        # at 9.1s instead of 3.3s. It is explicitly "context, not a render dependency", so it
        # may not cost the number the operator actually opens the panel for.
        alltime = (_optional_query(
            _cte(include_ident=True)
            + f"select count(*)::int as events, {_CANON_VISITORS} "
              "from public.analytics_events e left join ident i on i.visitor_id = e.visitor_id "
              f"where {_not_excluded('e')} and {_not_a_bot('e')}",
            timeout_cap_s=_OVERVIEW_ALLTIME_TIMEOUT_S,
            default=[],
        ) or [{}])[0]
        win = core.get("win") or {}
        win["sessions"] = core.get("sessions")
        return {
            "days": round(m / 1440, 2),
            "minutes": m,
            "window": win,
            "alltime": alltime,
            "bots": core.get("bots") or {},
            "by_site": core.get("by_site") or [],
            "daily": core.get("daily") or [],
            "tz": _TZ,
            "tz_label": _tz_label(),
            "visit_gap_min": g,
        }
    return _guard(run)


# Every ranked list below carries its grouping key as a FINAL sort key. Ranking by a
# count alone is a partial order, so rows that tie came back in whatever sequence the
# plan happened to produce — and where the ranking is paired with a LIMIT, that decides
# MEMBERSHIP, not just position: two cities tied on 4 visitors at the cut, and only one
# of them is on the panel. It was invisible only because the plan was stable; changing
# the exclusion CTEs above changed it, and Guangzhou and Singapore (both 4 visitors)
# swapped places on the Map tab with no data behind the move. Found 2026-08-26 while
# verifying that rewrite; the instability predates it.
def _pages_cte(minutes: int) -> str:
    """Reuse the native bot focus while projecting exclusion OUTPUT only.

    Preserve configuration-read order and every global historical classifier.
    SQL declares focus before its pages-only exclusion consumers.
    """
    excluded = _excluded_cte(focus_visitors=True)
    bots = _bot_cte(minutes)
    return "with " + bots + ", " + excluded + " "


def pages(days=7, limit=25, minutes=None) -> dict:
    m, n = _win(minutes, days, 10080), _limit(limit, 25)
    def run():
        rows = _query(_pages_cte(m) +
            "select e.site, coalesce(e.path,'(none)') as path, "
            "count(*) filter (where e.type in ('pageview','route'))::int as views, "
            "count(distinct e.visitor_id)::int as visitors, "
            "round(avg(e.dwell_ms) filter (where e.dwell_ms is not null))::int as avg_dwell_ms "
            f"from public.analytics_events e where e.created_at > now() - interval '{m} minutes' "
            # Both native membership sets exclude NULL IDs. Anti-membership therefore
            # keeps the same NULL-visitor rows without an OR-wrapped NOT IN subplan.
            # Keep all historical classifier evidence and every event type for dwell.
            "and not exists (select 1 from excluded x where x.visitor_id = e.visitor_id) "
            "and not exists (select 1 from bots b where b.visitor_id = e.visitor_id) "
            "group by 1,2 order by views desc nulls last, 1, 2 "
            f"limit {n}") or []
        return {"days": round(m / 1440, 2), "minutes": m, "pages": rows}
    return _guard(run)


def geo(days=30, limit=200, minutes=None) -> dict:
    m, n = _win(minutes, days, 43200), _limit(limit, 200)
    def run():
        r = _parallel(
            countries=lambda: _query(_cte(bot_window=m) +
                "select coalesce(g.country,'(unknown)') as country, g.country_code, "
                "count(distinct e.visitor_id)::int as visitors, count(*)::int as events "
                "from public.analytics_events e left join public.ip_geo g on g.ip = e.ip "
                f"where e.created_at > now() - interval '{m} minutes' and {_not_excluded('e')} and {_not_a_bot('e')} "
                "group by 1,2 order by visitors desc nulls last, 1, 2") or [],
            cities=lambda: _query(_cte(bot_window=m) +
                "select g.city, g.region, g.country_code, g.lat, g.lon, "
                "count(distinct e.visitor_id)::int as visitors "
                "from public.analytics_events e join public.ip_geo g on g.ip = e.ip "
                f"where e.created_at > now() - interval '{m} minutes' and g.city is not null "
                f"and {_not_excluded('e')} and {_not_a_bot('e')} "
                "group by 1,2,3,4,5 order by visitors desc, 1, 2, 3 "
                f"limit {n}") or [],
        )
        return {"days": round(m / 1440, 2), "minutes": m,
                "countries": r["countries"], "cities": r["cities"]}
    return _guard(run)


def sessions(limit=100, q="", include_bots=False, minutes=None, days=None, gap=None) -> dict:
    """Recent VISITS — one row per continuous sitting, not per raw session_id.

    Rows still ship under the `sessions` key and still carry a `session_id` (the FIRST raw
    session of the visit, which the replay resolves back to the whole visit), so the SPA's
    shape is unchanged. New per-row fields: `tab_sessions` (how many raw sessions merged)
    and `sites` (the origins touched, in the order they were first hit — `site` is that list
    joined with an arrow, so one macro → terminal → macro sitting reads as the trip it was)."""
    n = _limit(limit, 100, 2000)
    m = _win(minutes, days, 43200)
    g = _gap(gap)
    qq = _sanitize_q(q)
    # Filter clauses, applied AFTER the user+geo joins and BEFORE the limit so they see full
    # history — name/email identify the login-attributed user of the visit's cookie;
    # candidate_name/candidate_email are the soft device/IP guess, so the operator can
    # search Sessions by either. Site matching runs over the whole visit's site list.
    conds = []
    if qq:
        cols = ("s.visitor_id", "s.ip", "array_to_string(sn.sites,' ')",
                "g.city", "g.region", "g.country_code",
                "hu.email", users.display_name_sql("hu"),
                "cu.email", users.display_name_sql("cu"))
        conds.append("(" + " or ".join(f"{c} ilike '%{qq}%'" for c in cols) + ")")
    if not include_bots:
        conds.append("s.is_bot = 0")          # crawlers hidden unless explicitly revealed
    where = ("where " + " and ".join(conds) + " ") if conds else ""
    def run():
        rows = _query(_cte(include_ident=True, include_candidate=True, candidate_window=m,
                           bot_window=m, focus_excluded=True) +
            # ev: in-window, non-hidden events tagged with their canonical person, so a
            # signed-in visitor's separate macro/terminal cookies stitch into one visit.
            ", ev as (select e.id, e.session_id, e.visitor_id, e.site, e.ip, e.type, e.created_at, "
            "    coalesce(i.uid, e.visitor_id) as canon "
            "  from public.analytics_events e left join ident i on i.visitor_id = e.visitor_id "
            f"  where e.session_id is not null and e.visitor_id is not null and {_not_excluded('e')} "
            f"    and e.created_at > now() - interval '{m} minutes'), "
            f"brk as (select ev.*, {_visit_break(g)} as b from ev), "
            f"vis as (select brk.*, {_visit_no()} as vn from brk), "
            # Sites in first-touch order — aggregated per (visit, site) first so the array is
            # one entry per origin however many events it holds.
            "sv as (select canon, vn, site, min(created_at) as t0 from vis "
            "  where site is not null group by 1,2,3), "
            "sn as (select canon, vn, array_agg(site order by t0) as sites from sv group by 1,2), "
            "s as (select canon, vn, "
            "    (array_agg(session_id order by created_at, id))[1] as session_id, "
            "    (array_agg(visitor_id order by created_at, id))[1] as visitor_id, "
            "    count(distinct session_id)::int as tab_sessions, count(*)::int as events, "
            "    count(*) filter (where type in ('pageview','route'))::int as pages, "
            "    min(created_at) as started, max(created_at) as ended, "
            "    (array_agg(ip order by created_at, id))[1] as ip, "
            "    max(case when visitor_id in (select visitor_id from bots) then 1 else 0 end) as is_bot "
            "  from vis group by 1,2) "
            "select s.session_id, s.visitor_id, hi.uid as user_id, "
            "  array_to_string(sn.sites,' → ') as site, sn.sites, s.tab_sessions, "
            "  s.events, s.pages, "
            f"  to_char({_lt('s.started')},'YYYY-MM-DD HH24:MI') as started, "
            "  round(extract(epoch from (s.ended - s.started)))::int as duration_s, "
            "  s.ip, s.is_bot, g.city, g.region, g.country_code, "
            # hard: the verified user this visit's cookie is stitched to.
            f"  hu.email as email, {users.display_name_sql('hu')} as name, "
            # soft: the registered user this anonymous cookie most likely belongs to (device/IP).
            f"  cu.email as candidate_email, {users.display_name_sql('cu')} as candidate_name, "
            "  c.basis as candidate_basis "
            "from s "
            "left join sn on sn.canon = s.canon and sn.vn = s.vn "
            "left join public.ip_geo g on g.ip = s.ip "
            "left join ident hi on hi.visitor_id = s.visitor_id "
            "left join auth.users hu on hu.id::text = hi.uid "
            "left join cand c on c.visitor_id = s.visitor_id "
            "left join auth.users cu on cu.id::text = c.uid "
            f"{where}"
            f"order by s.started desc, s.session_id limit {n}") or []
        return {"sessions": _apply_geo_overrides(rows), "q": qq, "include_bots": include_bots,
                "tz": _TZ, "tz_label": _tz_label(), "visit_gap_min": g}
    return _guard(run)


def visitors(limit=250, q="", include_bots=False, minutes=None, days=None, gap=None) -> dict:
    """One row per PERSON — the 'Frequent Visitors' list.

    Identity resolution: any anonymous cookie (mm_aid) that ever appears on a signed-in
    event is merged under that user, so all of one person's cookies/devices collapse into
    a single row keyed by their Supabase user id and labelled with their name when available
    (otherwise email). Purely anonymous visitors stay keyed by their mm_aid. `identities` =
    how many cookies merged.

    `sessions` counts VISITS on the same rule the Sessions tab uses (see _visit_break), so the
    two tabs agree; `tab_sessions` keeps the raw per-tab/per-origin count alongside it.
    Ordered by visit count."""
    n = _limit(limit, 250, 2000)
    m = _win(minutes, days, 43200)
    g = _gap(gap)
    qq = _sanitize_q(q)
    # Filters, applied AFTER the user+geo joins and BEFORE the limit so they see the whole roster.
    conds = []
    if qq:
        cols = ("u.email", users.display_name_sql("u"),
                "cu.email", users.display_name_sql("cu"),
                "v.canon", "v.last_ip", "g.city", "g.region", "g.country", "g.country_code")
        conds.append("(" + " or ".join(f"{c} ilike '%{qq}%'" for c in cols) + ")")
    if not include_bots:
        conds.append("v.is_bot = 0")           # crawlers hidden unless explicitly revealed
    where = ("where " + " and ".join(conds) + " ") if conds else ""
    def run():
        rows = _query(
            # ident: each mm_aid -> the user uuid it belongs to (if ever authenticated).
            # A cookie signed into by 2+ DIFFERENT accounts (shared/kiosk device) is
            # AMBIGUOUS — excluded from the auto-merge so one person's activity is never
            # silently reassigned to another; those events stay under the cookie.
            _cte(include_ident=True, include_candidate=True, candidate_window=m,
                 bot_window=m, focus_excluded=True) +
            # ev: every (non-hidden) event tagged with its canonical identity (uid if known, else mm_aid)
            ", ev0 as ("
            "  select e.id, e.session_id, e.ip, e.created_at, e.visitor_id, i.uid, "
            "    coalesce(i.uid, e.visitor_id) as canon "
            "  from public.analytics_events e "
            "  left join ident i on i.visitor_id = e.visitor_id "
            f"  where e.visitor_id is not null and {_not_excluded('e')} "
            f"    and e.created_at > now() - interval '{m} minutes'"
            "), "
            # ev: the same events with a visit number, so `sessions` below counts sittings
            # (macro → terminal → macro = 1) rather than per-tab/per-origin session_ids.
            f"ev1 as (select ev0.*, {_visit_break(g)} as b from ev0), "
            f"ev as (select ev1.*, {_visit_no()} as vn from ev1) "
            "select v.canon as visitor_id, (v.uid is not null) as is_user, u.email, "
            f"  {users.display_name_sql('u')} as name, "
            # candidate: for an ANONYMOUS row (canon is a cookie, not a uid), the registered user
            # it most likely belongs to via a shared device/IP — a suggestion, never merged.
            f"  cu.email as candidate_email, {users.display_name_sql('cu')} as candidate_name, "
            "  c.basis as candidate_basis, "
            "  v.events, v.sessions, v.tab_sessions, v.identities, v.ips, v.last_ip, v.is_bot, "
            f"  to_char({_lt('v.first_seen')},'YYYY-MM-DD HH24:MI') as first_seen, "
            f"  to_char({_lt('v.last_seen')},'YYYY-MM-DD HH24:MI') as last_seen, "
            "  g.city, g.region, g.country, g.country_code, g.is_vpn "
            "from (select canon, max(uid) as uid, count(*)::int as events, "
            "  count(distinct vn)::int as sessions, "
            "  count(distinct session_id)::int as tab_sessions, "
            "  count(distinct visitor_id)::int as identities, count(distinct ip)::int as ips, "
            "  min(created_at) as first_seen, max(created_at) as last_seen, "
            "  (array_agg(ip order by created_at desc))[1] as last_ip, "
            "  max(case when visitor_id in (select visitor_id from bots) then 1 else 0 end) as is_bot "
            "  from ev group by canon) v "
            "left join auth.users u on u.id::text = v.uid "
            "left join cand c on c.visitor_id = v.canon "
            "left join auth.users cu on cu.id::text = c.uid "
            "left join public.ip_geo g on g.ip = v.last_ip "
            f"{where}"
            f"order by v.sessions desc, v.last_seen desc, v.canon limit {n}") or []
        return {"visitors": _apply_geo_overrides(rows, "last_ip"), "q": qq,
                "include_bots": include_bots, "tz": _TZ, "tz_label": _tz_label(),
                "visit_gap_min": g}
    return _guard(run)


def session(session_id: str, gap=None) -> dict:
    """The ordered event path of the VISIT containing `session_id` (the 1:1 replay).

    Because sessions() stitches per-tab/per-origin session_ids into visits, the replay has to
    stitch too — otherwise clicking through from a merged row would show only the first tab.
    So: resolve the seed session's person to all their cookies, re-split their events on the
    same idle rule, and return the visit the seed falls in. Each event carries its own `site`
    and `session_id`, so the origin hops and tab boundaries stay visible inside the timeline.

    The scan is bounded to ±12h around the seed session so it never walks the person's whole
    history — a visit is by construction a chain of <= `gap`-minute hops, and the gap ceiling
    is 12h, so a visit cannot reach beyond that bound without the seed itself spanning it."""
    if not session_id or not _ID_RE.match(session_id):
        return {"ok": False, "reason": "invalid session id"}
    g = _gap(gap)
    sid = session_id   # _ID_RE-allowlisted ([A-Za-z0-9._:-]{1,64}) — safe to interpolate
    def run():
        cte = (
            "with " + _IDENT_CTE + ", "
            "seed as (select max(visitor_id) as vid, min(created_at) as t0, max(created_at) as t1 "
            f"  from public.analytics_events where session_id = '{sid}'), "
            # The seed cookie's owner (if it ever signed in) → all of that person's cookies,
            # so a macro cookie and a terminal cookie of one logged-in visitor stitch together.
            "seeduid as (select uid from ident where visitor_id = (select vid from seed)), "
            "myaids as (select visitor_id from ident where uid in (select uid from seeduid) "
            "           union select vid from seed), "
            # visitor_id-indexed + time-bounded, so this never degrades into a full scan.
            "win as (select e.* from public.analytics_events e "
            "  where e.visitor_id in (select visitor_id from myaids) "
            "    and e.created_at >= (select t0 from seed) - interval '12 hours' "
            "    and e.created_at <= (select t1 from seed) + interval '12 hours'), "
            f"brk as (select win.*, {_visit_break(g, part=None)} as b from win), "
            f"vis as (select brk.*, {_visit_no(part=None)} as vn from brk), "
            f"cur as (select vn from vis where session_id = '{sid}' order by created_at, id limit 1) "
        )
        r = _parallel(
            path=lambda: _query(cte +
                "select type, coalesce(path,'') as path, ticker, dwell_ms, scroll, site, session_id, "
                f"to_char({_lt('created_at')},'HH24:MI:SS') as t, meta "
                "from vis where vn = (select vn from cur) order by created_at, id limit 2000") or [],
            head=lambda: (_query(cte +
            "select s.*, u.email, "
            f"{users.display_name_sql('u')} as name from ("
            "select (array_agg(visitor_id order by created_at, id))[1] as visitor_id, "
            "max(user_id::text) as user_id, "
            "count(distinct session_id)::int as tab_sessions, "
            f"to_char(min({_lt('created_at')}),'YYYY-MM-DD HH24:MI') as started, "
            f"to_char(max({_lt('created_at')}),'HH24:MI') as ended, "
            "round(extract(epoch from (max(created_at) - min(created_at))))::int as duration_s, "
                "(array_agg(ip order by created_at, id))[1] as ip, "
                "(array_agg(fp) filter (where fp is not null))[1] as fp "
                "from vis where vn = (select vn from cur)) s "
                "left join auth.users u on u.id::text = s.user_id") or [{}])[0],
        )
        path, head = r["path"], r["head"]
        # Origins in first-touch order — derived from the already-ordered path rather than a
        # third round trip.
        sites = list(dict.fromkeys([e.get("site") for e in path if e.get("site")]))
        head["site"] = " → ".join(sites)
        return {"session_id": sid, "head": head, "path": path, "sites": sites,
                "tz": _TZ, "tz_label": _tz_label(), "visit_gap_min": g}
    return _guard(run)


def flow(days=7, limit=40, minutes=None) -> dict:
    m, n = _win(minutes, days, 10080), _limit(limit, 40, 200)
    def run():
        rows = _query(
            "with " + _excluded_cte() + ", " + _bot_cte(m) + ", ev as (select session_id, path, "
            "  lag(path) over (partition by session_id order by id) as prev "
            "  from public.analytics_events "
            f"  where type in ('pageview','route') and path is not null and {_not_excluded('')} and {_not_a_bot('')} "
            f"    and created_at > now() - interval '{m} minutes') "
            "select prev as from_path, path as to_path, count(*)::int as n "
            "from ev where prev is not null and prev <> path "
            "group by 1,2 order by n desc, 1, 2 "
            f"limit {n}") or []
        return {"days": round(m / 1440, 2), "minutes": m, "edges": rows}
    return _guard(run)


def terminal(days=7, limit=25, minutes=None) -> dict:
    m, n = _win(minutes, days, 10080), _limit(limit, 25)
    def run():
        no_bot_search = "(anon_id is null or anon_id not in (select visitor_id from bots))"
        r = _parallel(
            searches=lambda: _query(_cte(bot_window=m, bot_include_search=True) +
                "select symbol as ticker, count(*)::int as searches, "
                "count(distinct coalesce(user_id::text, anon_id, ip))::int as visitors "
                f"from public.search_events where created_at > now() - interval '{m} minutes' "
                f"and {_not_excluded_search()} and {no_bot_search} "
                f"group by 1 order by searches desc, 1 limit {n}") or [],
            views=lambda: _query(_cte(bot_window=m, bot_include_search=True) +
                "select ticker, count(*)::int as views, count(distinct visitor_id)::int as visitors "
                "from public.analytics_events where type='ticker_view' and ticker is not null "
                f"and created_at > now() - interval '{m} minutes' and {_not_excluded('')} and {_not_a_bot('')} "
                f"group by 1 order by views desc, 1 limit {n}") or [],
            totals=lambda: (_query(_cte(bot_window=m, bot_include_search=True) +
                "select (select count(*)::int from public.search_events "
                f"  where created_at > now() - interval '{m} minutes' and {_not_excluded_search()} and {no_bot_search}) as search_total, "
                "(select count(*)::int from public.analytics_events where type='ticker_view' "
                f"  and created_at > now() - interval '{m} minutes' and {_not_excluded('')} and {_not_a_bot('')}) as view_total") or [{}])[0],
        )
        return {"days": round(m / 1440, 2), "minutes": m, "top_searches": r["searches"],
                "top_views": r["views"], "totals": r["totals"]}
    return _guard(run)


def visitor(visitor_id: str, gap=None) -> dict:
    """One person's profile. `visitor_id` is the canonical id from the visitors() list —
    either a Supabase user uuid (a registered person, whose every mm_aid cookie is merged)
    or a bare mm_aid (a purely anonymous visitor). All sub-queries resolve it to the full
    set of that person's cookies via the `myaids` CTE, so a signed-in user's activity across
    every device/cookie shows as one profile."""
    if not visitor_id or not _ID_RE.match(visitor_id):
        return {"ok": False, "reason": "invalid visitor id"}
    g = _gap(gap)
    v = visitor_id   # _ID_RE-allowlisted ([A-Za-z0-9._:-]{1,64}) — safe to interpolate
    # Prepended to every sub-query: map the canonical id to all mm_aid cookies of the person.
    # If v is a user uuid -> every mm_aid ever seen on one of that user's events; if v is an
    # mm_aid -> just itself (the `union select '{v}'` covers the anonymous case).
    # ident drops cookies signed into by 2+ accounts (ambiguous shared devices); the excluded +
    # bot chains ride along so the linked-visitor list below can drop crawler and hidden cookies
    # rather than reporting "50 linked identities" that are all one scraper's rotating cookies.
    cte = (
        "with " + _IDENT_CTE + ", " + _excluded_cte() + ", " + _bot_cte() +
        f", myaids as (select visitor_id from ident where uid = '{v}' union select '{v}') "
    )
    inaids = "visitor_id in (select visitor_id from myaids)"
    def run():
        # `sessions` counts VISITS (the Sessions-tab rule), so one person's numbers agree
        # across every surface; `tab_sessions` keeps the raw per-tab/per-origin count.
        # Seven independent statements in one wave. The candidate lookup below stays
        # sequential because it is genuinely dependent — it only runs when this profile
        # turned out to have no registered identity, and it feeds off its own result.
        r = _parallel(
            profile=lambda: (_query(cte +
                f"select to_char(min({_lt('created_at')}),'YYYY-MM-DD HH24:MI') as first_seen, "
                f"to_char(max({_lt('created_at')}),'YYYY-MM-DD HH24:MI') as last_seen, "
                "count(*)::int as events, count(distinct vn)::int as sessions, "
                "count(distinct session_id)::int as tab_sessions, "
                "count(distinct ip)::int as ips, count(distinct fp)::int as fingerprints, "
                "count(distinct visitor_id)::int as identities, max(user_id::text) as user_id "
                f"from (select w.*, {_visit_no(part=None)} as vn from ("
                f"  select x.*, {_visit_break(g, part=None)} as b "
                f"  from public.analytics_events x where {inaids}) w) z") or [{}])[0],
            er=lambda: _query(
                "select u.email, "
                f"{users.display_name_sql('u')} as name "
                f"from auth.users u where u.id::text = '{v}'") or [],
            ips=lambda: _apply_geo_overrides(_query(cte +
                "select e.ip, g.city, g.region, g.country_code, g.asn, g.org, "
                "g.is_vpn, g.is_proxy, g.is_hosting, count(*)::int as events "
                "from public.analytics_events e left join public.ip_geo g on g.ip = e.ip "
                f"where e.{inaids} group by 1,2,3,4,5,6,7,8,9 order by events desc") or []),
        # OTHER visitors sharing a fingerprint or IP with this person (not yet merged by login).
        # Each linked cookie is resolved to its registered email when it is itself login-stitched,
        # so a shared device/IP surfaces WHO the other identity is — not just an opaque cookie.
            linked=lambda: _query(cte +
                "select e2.visitor_id, max(li.uid) as user_id, count(*)::int as shared_events, "
                "max(case when e2.fp = k.e1fp then 1 else 0 end) as via_fp, "
                "max(case when e2.ip = k.e1ip then 1 else 0 end) as via_ip, "
                "max(lu.email) as email, "
                f"max({users.display_name_sql('lu')}) as name "
                "from public.analytics_events e2 "
                "join (select distinct fp as e1fp, ip as e1ip from public.analytics_events "
                f"      where {inaids}) k "
                "  on (e2.fp = k.e1fp and e2.fp is not null) "
                f"  or (e2.ip = k.e1ip and {_routable('e2.ip')}) "
                "left join ident li on li.visitor_id = e2.visitor_id "
                "left join auth.users lu on lu.id::text = li.uid "
                "where e2.visitor_id not in (select visitor_id from myaids) "
                f"  and {_not_a_bot('e2')} and {_not_excluded('e2')} "
                f"group by 1 order by coalesce(max({users.display_name_sql('lu')}), "
                "max(lu.email)) is null, shared_events desc limit 50") or [],
            recent=lambda: _query(cte +
                "select type, coalesce(path,'') as path, ticker, site, "
                f"to_char({_lt('created_at')},'YYYY-MM-DD HH24:MI') as t "
                f"from public.analytics_events where {inaids} order by id desc limit 40") or [],
            # tickers this person searched (search_events.anon_id = the mm_aid cookie, OR the
            # signed-in user_id directly — catches searches from a cookie with no beacon rows) + viewed
            searches=lambda: _query(cte +
                "select symbol as ticker, count(*)::int as n, "
                f"to_char(max({_lt('created_at')}),'YYYY-MM-DD HH24:MI') as last "
                "from public.search_events "
                f"where (anon_id in (select visitor_id from myaids) or user_id::text = '{v}') "
                "group by 1 order by n desc, last desc, 1 limit 50") or [],
            tickers_viewed=lambda: _query(cte +
                "select ticker, count(*)::int as n "
                f"from public.analytics_events where {inaids} and type='ticker_view' and ticker is not null "
                "group by 1 order by n desc, 1 limit 50") or [],
        )
        profile, ips, linked = r["profile"], r["ips"], r["linked"]
        recent, searches, tickers_viewed = r["recent"], r["searches"], r["tickers_viewed"]
        er = r["er"]
        email = er[0].get("email") if er else None
        name = er[0].get("name") if er else None
        # If THIS profile is an anonymous cookie, name the registered user it most likely belongs
        # to: the account owning a fingerprint/routable-IP it shares — but only when exactly one
        # account matches (ambiguous shared device/IP → no guess). Suggestion only, never a merge.
        candidate = None
        if not (name or email):
            crows = _query(cte +
                "select i2.uid, "
                "  max(case when e2.fp = k.e1fp and e2.fp is not null then 1 else 0 end) as via_fp, "
                f"  max(case when e2.ip = k.e1ip and {_routable('e2.ip')} then 1 else 0 end) as via_ip "
                "from public.analytics_events e2 "
                "join (select distinct fp as e1fp, ip as e1ip from public.analytics_events "
                f"      where {inaids}) k "
                "  on (e2.fp = k.e1fp and e2.fp is not null) "
                f"  or (e2.ip = k.e1ip and {_routable('e2.ip')} and {_routable('k.e1ip')}) "
                "join ident i2 on i2.visitor_id = e2.visitor_id "   # e2 is a KNOWN user's cookie
                f"where {_not_a_bot('e2')} and {_not_excluded('e2')} "
                "group by i2.uid") or []
            if len(crows) == 1 and crows[0].get("uid"):
                er2 = _query(
                    "select u.email, "
                    f"{users.display_name_sql('u')} as name "
                    f"from auth.users u where u.id::text = '{crows[0]['uid']}'") or []
                candidate = {"uid": crows[0]["uid"],
                             "email": (er2[0].get("email") if er2 else None),
                             "name": (er2[0].get("name") if er2 else None),
                             "via_fp": crows[0].get("via_fp"), "via_ip": crows[0].get("via_ip")}
        return {"visitor_id": v, "email": email, "name": name,
                "candidate": candidate, "profile": profile,
                "ips": ips, "linked": linked, "recent": recent, "searches": searches,
                "tickers_viewed": tickers_viewed,
                "tz": _TZ, "tz_label": _tz_label(), "visit_gap_min": g}
    return _guard(run)


def realtime() -> dict:
    def run():
        # This one is POLLED every 15s while the Analytics tab is open, so halving its
        # round trips halves a cost the console pays continuously, not just on open.
        r = _parallel(
            now=lambda: (_query(_cte(bot_window=5) +
                "select count(distinct visitor_id)::int as visitors, "
                "count(distinct session_id)::int as sessions, count(*)::int as events "
                "from public.analytics_events where created_at > now() - interval '5 minutes' "
                f"and {_not_excluded('')} and {_not_a_bot('')}") or [{}])[0],
            recent=lambda: _apply_geo_overrides(_query(_cte(bot_window=15) +
                "select e.type, e.site, coalesce(e.path,'') as path, e.ticker, e.ip, "
                f"to_char({_lt('e.created_at')},'HH24:MI:SS') as t, g.city, g.country_code "
                "from public.analytics_events e left join public.ip_geo g on g.ip = e.ip "
                f"where e.created_at > now() - interval '15 minutes' and {_not_excluded('e')} and {_not_a_bot('e')} "
                "order by e.id desc limit 30") or []),
        )
        return {"active": r["now"], "recent": r["recent"], "tz": _TZ, "tz_label": _tz_label()}
    return _guard(run)


def geo_enrich_now(budget: int = 300) -> dict:
    """On-demand IPLocate backfill: subprocess scripts/geo_enrich.py (needs IPLOCATE_API_KEY in the
    admin service env). Best-effort; the scheduled Action is the primary mechanism."""
    repo = Path(__file__).resolve().parent.parent   # /opt/macro
    script = repo / "scripts" / "geo_enrich.py"
    if not script.exists():
        return {"ok": False, "reason": "scripts/geo_enrich.py not found"}
    try:
        env = dict(os.environ)
        env["IPLOCATE_DAILY_BUDGET"] = str(max(1, min(1000, int(budget))))
        out = subprocess.run([sys.executable, str(script)], capture_output=True, text=True,
                             timeout=150, env=env)
        return {"ok": out.returncode == 0, "output": (out.stdout or out.stderr or "").strip()[-600:]}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": str(e)}
