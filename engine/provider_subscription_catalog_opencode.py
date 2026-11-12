"""Public Go offer observations for Shared Provider Control; never route authority.

The global model list is NOT account entitlement. Advertised model-equivalent
allowances are NOT independent balances. This module acquires/decodes public
metadata and proposes changes to existing model-economics/plan owners. It owns
no registry, credentials, timer, worker, retry, account allocation or persistence.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from typing import Callable, Mapping, Optional

MODELS_URL = "https://opencode.ai/zen/go/v1/models"
DOCS_URL = "https://opencode.ai/docs/go/"
MAX_BYTES = 2 * 1024 * 1024
MODEL_TTL_SECONDS = 3600
TERMS_TTL_SECONDS = 21600
_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
_PATHS = {
    "https://opencode.ai/zen/go/v1/chat/completions": "openai-chat",
    "https://opencode.ai/zen/go/v1/responses": "responses",
    "https://opencode.ai/zen/go/v1/messages": "anthropic",
}
_HORIZONS = ("five_hour", "weekly", "monthly")


class GoCatalogError(ValueError):
    """Sanitized, bounded metadata refusal; never implies empty/free capacity."""


def _time(value: str) -> datetime:
    try:
        at = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        raise GoCatalogError("INVALID_OBSERVATION_TIME") from None
    if at.tzinfo is None:
        raise GoCatalogError("INVALID_OBSERVATION_TIME")
    return at.astimezone(timezone.utc)


def _digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def _plain(value: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]*>", " ", value)).replace("**", "").replace("`", "").split())


def _name(value: str) -> str:
    # Only harmless display separators are equivalent; versions are never erased.
    return re.sub(r"[\s-]", "", _plain(value).casefold())


def _money(value: str, *, nullable: bool = False) -> Optional[str]:
    value = _plain(value)
    if nullable and value == "-":
        return None
    if not re.fullmatch(r"\$[0-9]{1,8}(?:\.[0-9]{1,9})?", value):
        raise GoCatalogError("UNRECOGNIZED_PRICE")
    return str(Decimal(value[1:]).normalize())


def _table(section: str, expected: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
    lines = section.splitlines()
    tables = []
    for i, line in enumerate(lines):
        cells = tuple(_plain(c.strip()) for c in line.strip().strip("|").split("|"))
        if cells != expected:
            continue
        if i + 1 >= len(lines) or not re.fullmatch(r"[\s|:-]+", lines[i + 1]):
            raise GoCatalogError("TABLE_SEPARATOR_CHANGED")
        rows = []
        for raw in lines[i + 2:]:
            if not raw.lstrip().startswith("|"):
                break
            row = tuple(c.strip() for c in raw.strip().strip("|").split("|"))
            if len(row) != len(expected):
                raise GoCatalogError("TABLE_ROW_SHAPE_CHANGED")
            rows.append(row)
        tables.append(tuple(rows))
    if len(tables) != 1 or not tables[0]:
        raise GoCatalogError("REQUIRED_TABLE_MISSING_OR_AMBIGUOUS")
    return tables[0]


def _section(document: str, name: str) -> str:
    hits = list(re.finditer(r"^## " + re.escape(name) + r"\s*$", document, re.M))
    if len(hits) != 1:
        raise GoCatalogError("REQUIRED_SECTION_MISSING_OR_AMBIGUOUS")
    tail = document[hits[0].end():]
    return re.split(r"^## ", tail, maxsplit=1, flags=re.M)[0]


@dataclass(frozen=True)
class Inventory:
    model_ids: tuple[str, ...]
    observed_at: str
    source_digest: str
    semantic_digest: str


@dataclass(frozen=True)
class AdvertisedRate:
    qualifier: str
    input: str
    output: str
    cached_input: Optional[str]
    cache_write: Optional[str]
    monthly_equivalent_usd: str
    baseline_equivalent_usd: Optional[str]
    promotion_note: Optional[str]


@dataclass(frozen=True)
class AdvertisedModel:
    model_id: str
    protocol: str
    rates: tuple[AdvertisedRate, ...]
    training: Optional[bool]
    retention_text: Optional[str]


@dataclass(frozen=True)
class Terms:
    models: tuple[AdvertisedModel, ...]
    horizon_fractions: tuple[str, str, str]
    observed_at: str
    source_digest: str
    economic_conditions_digest: str
    policy_digest: str
    semantic_digest: str


@dataclass(frozen=True)
class Metadata:
    inventory: Inventory
    terms: Terms


def parse_models(payload: Mapping[str, object], *, observed_at: str) -> Inventory:
    _time(observed_at)
    if not isinstance(payload, Mapping) or set(payload) != {"object", "data"} or payload["object"] != "list":
        raise GoCatalogError("MODEL_LIST_SCHEMA_CHANGED")
    rows = payload["data"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= 512:
        raise GoCatalogError("MODEL_LIST_EMPTY_OR_OVERSIZED")
    ids = []
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != {"id", "object", "created", "owned_by"}:
            raise GoCatalogError("MODEL_METADATA_SCHEMA_CHANGED")
        model = row["id"]
        if not isinstance(model, str) or not _ID.fullmatch(model) or row["object"] != "model" or row["owned_by"] != "opencode":
            raise GoCatalogError("MODEL_IDENTITY_INVALID")
        if type(row["created"]) is not int or row["created"] < 0:
            raise GoCatalogError("MODEL_METADATA_INVALID")
        ids.append(model)
    if len(ids) != len(set(ids)):
        raise GoCatalogError("DUPLICATE_MODEL_ID")
    names = tuple(sorted(ids))
    # created is Date.now(), NOT release time. Array order is not significance.
    return Inventory(names, observed_at, _digest(payload), _digest(names))


def parse_terms(document: str, *, observed_at: str) -> Terms:
    """Decode documented offer facts. This does not promote them into routing law."""
    _time(observed_at)
    if not isinstance(document, str) or len(document.encode()) > MAX_BYTES:
        raise GoCatalogError("DOCUMENT_TOO_LARGE_OR_INVALID")
    usage = _section(document, "Usage limits").split("### Estimated requests")[0]
    endpoints = _section(document, "Endpoints")
    privacy = _section(document, "Privacy")
    flat = " ".join(usage.split())
    if "Token prices are per 1M tokens." not in flat:
        raise GoCatalogError("PRICE_UNIT_UNKNOWN")
    fractions = re.findall(
        r"5-hour\s*[-\u2014]\s*([0-9.]+)%(?: of the monthly limit)?;\s*weekly\s*[-\u2014]\s*([0-9.]+)%;\s*and monthly\s*[-\u2014]\s*([0-9.]+)%",
        flat,
    )
    if len(fractions) != 1:
        raise GoCatalogError("WINDOW_FRACTIONS_UNKNOWN")
    try:
        numbers = tuple(Decimal(x) / 100 for x in fractions[0])
    except InvalidOperation:
        raise GoCatalogError("WINDOW_FRACTIONS_INVALID") from None
    if not all(n.is_finite() and 0 < n <= 1 for n in numbers) or numbers[-1] != 1:
        raise GoCatalogError("WINDOW_FRACTIONS_INVALID")
    fractions_out = tuple(str(x.normalize()) for x in numbers)
    by_name = {}
    protocols = {}
    for display, model, endpoint, _package in _table(endpoints, ("Model", "Model ID", "Endpoint", "AI SDK Package")):
        key, model, endpoint = _name(display), _plain(model), _plain(endpoint)
        if not _ID.fullmatch(model) or endpoint not in _PATHS or key in by_name or model in protocols:
            raise GoCatalogError("ENDPOINT_IDENTITY_AMBIGUOUS_OR_UNSUPPORTED")
        by_name[key] = model
        protocols[model] = _PATHS[endpoint]
    rates = {m: [] for m in protocols}
    for display, inp, out, cached, write, limit in _table(usage, ("Model", "Input", "Output", "Cached Read", "Cached Write", "Monthly limit")):
        match = re.fullmatch(r"(.+?)(?: \(([^()]*)\))?", _plain(display))
        if match is None or _name(match[1]) not in by_name:
            raise GoCatalogError("PRICE_WITHOUT_EXACT_ENDPOINT_ID")
        model = by_name[_name(match[1])]
        qualifier = match[2] or "standard"
        limit_text = _plain(limit)
        promo = re.fullmatch(r"~~(\$[0-9.]+)~~\s*(\$[0-9.]+)\s+(.+)", limit_text)
        if promo:
            baseline, monthly, note = _money(promo[1]), _money(promo[2]), promo[3]
        else:
            baseline, monthly, note = None, _money(limit_text), None
        if Decimal(monthly) <= 0:
            raise GoCatalogError("NONPOSITIVE_MODEL_ALLOWANCE")
        if any(r.qualifier == qualifier for r in rates[model]):
            raise GoCatalogError("DUPLICATE_RATE_VARIANT")
        rates[model].append(AdvertisedRate(qualifier, _money(inp), _money(out), _money(cached, nullable=True), _money(write, nullable=True), monthly, baseline, note))
    policies = {}
    for display, training, retention in _table(privacy, ("Model", "Model training", "Data retention")):
        key = _name(display)
        if key not in by_name or by_name[key] in policies:
            raise GoCatalogError("POLICY_IDENTITY_AMBIGUOUS")
        text = _plain(training)
        policies[by_name[key]] = ({"Not used": False, "Yes": True}.get(text), _plain(retention))
    models = tuple(AdvertisedModel(m, protocols[m], tuple(sorted(rates[m], key=lambda r: r.qualifier)), *policies.get(m, (None, None))) for m in sorted(protocols))
    # Include conditions/footnotes, not only tables. Unknown prose is never executed.
    conditions = _digest(" ".join(line.strip() for line in usage.splitlines() if not line.lstrip().startswith("|")))
    policy_digest = _digest(" ".join(privacy.split()))
    semantic = _digest({"models": [asdict(m) for m in models], "fractions": fractions_out, "conditions": conditions, "policy": policy_digest})
    return Terms(models, fractions_out, observed_at, hashlib.sha256(document.encode()).hexdigest(), conditions, policy_digest, semantic)


class _DocsHTML(HTMLParser):
    """Extract only headings, paragraphs, list text and tables from published docs."""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lines = []
        self.tag = None
        self.text = []
        self.row = []
        self.first_row = True
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.skip += 1
        if self.skip:
            return
        if tag == "table":
            self.first_row = True
        if tag == "tr":
            self.row = []
        if tag in {"h2", "h3", "p", "li", "th", "td"}:
            self.tag, self.text = tag, []
        elif tag in {"del", "s"} and self.tag:
            self.text.append("~~")
        elif tag in {"br"} and self.tag:
            self.text.append(" ")

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.skip:
            self.skip -= 1
            return
        if self.skip:
            return
        if tag in {"del", "s"} and self.tag:
            self.text.append("~~")
        if tag == self.tag:
            text = " ".join("".join(self.text).split())
            if tag in {"th", "td"}:
                self.row.append(text)
            else:
                prefix = {"h2": "## ", "h3": "### ", "li": "- "}.get(tag, "")
                self.lines.extend((prefix + text, ""))
            self.tag = None
        if tag == "tr" and self.row:
            self.lines.append("| " + " | ".join(self.row) + " |")
            if self.first_row:
                self.lines.append("| " + " | ".join("---" for _ in self.row) + " |")
                self.first_row = False
        if tag == "table":
            self.lines.append("")

    def handle_data(self, data):
        if self.tag and not self.skip:
            self.text.append(data)


def parse_published_terms(page: bytes, *, observed_at: str) -> Terms:
    if not isinstance(page, bytes) or len(page) > MAX_BYTES:
        raise GoCatalogError("DOCUMENT_TOO_LARGE_OR_INVALID")
    try:
        parser = _DocsHTML()
        parser.feed(page.decode("utf-8"))
        parser.close()
        terms = parse_terms("\n".join(parser.lines), observed_at=observed_at)
    except (UnicodeError, GoCatalogError):
        raise GoCatalogError("PUBLISHED_DOCUMENT_CONTRACT_CHANGED") from None
    from dataclasses import replace
    return replace(terms, source_digest=hashlib.sha256(page).hexdigest())


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise GoCatalogError("PUBLIC_METADATA_REDIRECT_REFUSED")


def _get_public(url: str) -> bytes:
    if url not in {MODELS_URL, DOCS_URL}:
        raise GoCatalogError("PUBLIC_METADATA_URL_REFUSED")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    request = urllib.request.Request(url, headers={"User-Agent": "mastermind-provider-control/1.0", "Accept": "application/json" if url == MODELS_URL else "text/html"})
    try:
        with opener.open(request, timeout=10) as response:
            if response.status != 200:
                raise GoCatalogError("PUBLIC_METADATA_HTTP_ERROR")
            raw = response.read(MAX_BYTES + 1)
    except Exception:
        raise GoCatalogError("PUBLIC_METADATA_ACQUISITION_FAILED") from None
    if len(raw) > MAX_BYTES:
        raise GoCatalogError("PUBLIC_METADATA_RESPONSE_TOO_LARGE")
    return raw


def acquire_metadata(*, getter: Callable[[str], bytes] = _get_public, clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> Metadata:
    """One bounded, read-only acquisition. Caller schedules/caches using its owner."""
    try:
        raw_models = getter(MODELS_URL)
        if not isinstance(raw_models, bytes) or len(raw_models) > MAX_BYTES:
            raise GoCatalogError("MODEL_LIST_OVERSIZED")
        inv = parse_models(json.loads(raw_models), observed_at=clock().isoformat())
        page = getter(DOCS_URL)
        terms = parse_published_terms(page, observed_at=clock().isoformat())
        return Metadata(inv, terms)
    except GoCatalogError:
        raise
    except Exception:
        raise GoCatalogError("PUBLIC_METADATA_ACQUISITION_FAILED") from None


def metadata_changes(previous: Metadata, current: Metadata) -> tuple[dict, ...]:
    """Propose changes, never apply routes or refresh any account quota."""
    for old, new in ((previous.inventory, current.inventory), (previous.terms, current.terms)):
        if _time(new.observed_at) < _time(old.observed_at):
            raise GoCatalogError("OUT_OF_ORDER_METADATA")
    old_ids, new_ids = set(previous.inventory.model_ids), set(current.inventory.model_ids)
    changes = [{"model_id": m, "action": "DISCOVER_ONLY"} for m in sorted(new_ids - old_ids)]
    changes += [{"model_id": m, "action": "STOP_NEW_REQUESTS"} for m in sorted(old_ids - new_ids)]
    old = {m.model_id: m for m in previous.terms.models}
    new = {m.model_id: m for m in current.terms.models}
    for model in sorted(new_ids & old_ids):
        if model not in new or not new[model].rates:
            if model in old and old[model].rates:
                changes.append({"model_id": model, "action": "HOLD_MISSING_TERMS"})
        elif model not in old or not old[model].rates:
            changes.append({"model_id": model, "action": "REVIEW_NEW_TERMS"})
        else:
            if old[model].protocol != new[model].protocol:
                changes.append({"model_id": model, "action": "REVALIDATE_HARNESS"})
            if old[model].rates != new[model].rates or previous.terms.horizon_fractions != current.terms.horizon_fractions or previous.terms.economic_conditions_digest != current.terms.economic_conditions_digest:
                changes.append({"model_id": model, "action": "REQUOTE_AND_REOBSERVE_USAGE"})
    if previous.terms.policy_digest != current.terms.policy_digest:
        changes.append({"model_id": None, "action": "HOLD_POLICY_REVIEW"})
    return tuple(changes)


def catalog_preview(metadata: Metadata, *, now: str) -> dict:
    """Machine-readable consumer; complete advertised terms still grant no route."""
    at = _time(now)
    issues = []
    for name, item, ttl in (("inventory", metadata.inventory, MODEL_TTL_SECONDS), ("terms", metadata.terms, TERMS_TTL_SECONDS)):
        age = (at - _time(item.observed_at)).total_seconds()
        if age < 0 or age >= ttl:
            issues.append(name.upper() + "_NOT_FRESH")
    offers = {m.model_id: m for m in metadata.terms.models}
    rows = []
    for model in metadata.inventory.model_ids:
        offer = offers.get(model)
        reasons = list(issues)
        if offer is None or not offer.rates:
            reasons.append("OFFER_TERMS_UNKNOWN")
        if offer is None or offer.training is None or offer.retention_text is None:
            reasons.append("DATA_POLICY_UNKNOWN")
        elif offer.training:
            reasons.append("TRAINING_CONSENT_REQUIRED")
        if offer is not None:
            if any(r.qualifier != "standard" for r in offer.rates):
                reasons.append("RATE_VARIANT_MATCH_REQUIRED")
            if any(r.promotion_note for r in offer.rates):
                reasons.append("PROMOTION_REVALIDATION_REQUIRED")
            if offer.retention_text and "*" in offer.retention_text:
                reasons.append("CONDITIONAL_RETENTION_REVALIDATION_REQUIRED")
        facts = asdict(offer) if offer else None
        if facts is not None:
            for rate in facts["rates"]:
                rate["window_equivalent_usd"] = {h: str((Decimal(rate["monthly_equivalent_usd"]) * Decimal(f)).normalize()) for h, f in zip(_HORIZONS, metadata.terms.horizon_fractions)}
        rows.append({"model_id": model, "advertised_protocol": offer.protocol if offer else None, "offer": facts, "metadata_issues": reasons, "routing_authorized": False})
    return {"provider": "opencode", "product": "go", "scope": "public_offers_not_account_entitlement", "inventory_generation": metadata.inventory.semantic_digest, "terms_generation": metadata.terms.semantic_digest, "horizon_fractions": dict(zip(_HORIZONS, metadata.terms.horizon_fractions)), "models": rows, "documented_not_listed": sorted(set(offers) - set(metadata.inventory.model_ids)), "production_armed": False}


def estimate_quota_debit(*, quoted_usage_usd: str, monthly_equivalent_usd: str, horizon_fractions: tuple[str, str, str]) -> dict[str, str]:
    """Translate an existing model-economics quote into ESTIMATED percentage points.

    No token calculator or quota ledger lives here. The caller must select a fresh,
    reviewed time/context/promotion rate, and acquire actual usage independently.
    """
    if not isinstance(horizon_fractions, tuple) or len(horizon_fractions) != 3:
        raise GoCatalogError("INVALID_QUOTA_ESTIMATE_INPUT")
    if any(not isinstance(x, str) or len(x) > 32 for x in (quoted_usage_usd, monthly_equivalent_usd, *horizon_fractions)):
        raise GoCatalogError("INVALID_QUOTA_ESTIMATE_INPUT")
    try:
        spend, cap = Decimal(quoted_usage_usd), Decimal(monthly_equivalent_usd)
        fractions = tuple(Decimal(x) for x in horizon_fractions)
    except (InvalidOperation, TypeError, ValueError):
        raise GoCatalogError("INVALID_QUOTA_ESTIMATE_INPUT") from None
    if not spend.is_finite() or spend < 0 or not cap.is_finite() or cap <= 0 or len(fractions) != 3 or not all(x.is_finite() and 0 < x <= 1 for x in fractions) or fractions[2] != 1:
        raise GoCatalogError("INVALID_QUOTA_ESTIMATE_INPUT")
    if spend > Decimal("1e12") or (spend and spend < Decimal("1e-18")) or not Decimal("1e-9") <= cap <= Decimal("1e12") or any(f < Decimal("1e-9") for f in fractions):
        raise GoCatalogError("INVALID_QUOTA_ESTIMATE_INPUT")
    return {h: str((100 * spend / (cap * f)).normalize()) for h, f in zip(_HORIZONS, fractions)}
