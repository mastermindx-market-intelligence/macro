"""Read-only observation adapter for the incumbent unified Capacity Fabric router.

The installed gateway owns every request, credential, route, retry and response.
This adapter observes its validated input, exact forwarder calls and sent bytes.
It performs no inference, provider call, replay, scheduling or credential copying.
"""
from __future__ import annotations

import asyncio
from collections import deque
from contextlib import asynccontextmanager, suppress
from contextvars import ContextVar
import functools
import hashlib
import hmac
import importlib
import inspect
import ipaddress
import json
import os
from pathlib import Path
import re
import time
import uuid

from .capacity_fabric_schema import (
    SCHEMA, MAX_ACTIVE, MAX_RECENT, MAX_BYTES, MAX_ATTEMPTS, TOKEN_FIELDS,
    CLIENTS, clean_snapshot, label, number,
)

_CONTEXT = ContextVar("capacity_observation", default=None)
_FRAME_LIMIT = 128 * 1024
_FORWARDERS = ("_forward_anthropic", "_forward_openai", "_forward_responses")


def _opaque(value):
    if not isinstance(value, str) or not value or len(value) > 1024:
        return None
    return hashlib.sha256(value.encode()).hexdigest()[:24]


def _client(value):
    lowered = str(value or "").lower()
    exact = {v.lower(): v for v in CLIENTS}
    if lowered in exact:
        return exact[lowered]
    for needle, name in (("claude", "Claude SDK"), ("hermes", "Hermes"),
                         ("openai", "OpenAI SDK"), ("python", "Python client")):
        if needle in lowered:
            return name
    return "Unknown client"


def _observe_peak(app):
    """Read the router's own peak-gate scalars; never recompute the window here."""
    try:
        cfg = app.state.settings
        gateway = importlib.import_module(__package__ + ".gateway")
        active = bool(gateway._peak_active(cfg))
        next_at = getattr(gateway, "_PEAK_GATE_NEXT", {}).get("at", 0)
        return {"active": active, "tz": cfg.peak_tz, "start": cfg.peak_start, "end": cfg.peak_end,
                "wait_s": cfg.peak_wait_s, "next_send_in_s": max(0.0, next_at - time.time())}
    except Exception:
        return None


def _observe_overflow(app):
    """The policy's own overflow snapshot, plus configured ladder targets.

    Read-only: the policy computes state on its own clock; this copies scalars.
    """
    try:
        policy = app.state.model_policy
        snap = policy.snapshot()
        overflow = snap.get("overflow")
        if not isinstance(overflow, dict):
            return None
        result = {k: overflow.get(k) for k in ("enabled", "version", "diverted_requests",
            "diversion_share", "diverted_sessions", "diverted_inflight", "keys", "recent")}
        families = {}
        cfg_families = (policy.overflow.config().get("families") if getattr(policy, "overflow", None) else {}) or {}
        for name, fam in (overflow.get("families") or {}).items():
            fam = dict(fam) if isinstance(fam, dict) else {}
            target_cfg = cfg_families.get(name) or {}
            targets = target_cfg.get("targets") or ([target_cfg["target"]] if target_cfg.get("target") else [])
            fam["targets"] = list(targets)
            families[name] = fam
        result["families"] = families
        return result
    except Exception:
        return None


class ObservationStore:
    def __init__(self, known_models=()):
        self.known_models = frozenset(known_models)
        self.epoch = uuid.uuid4().hex
        self.started_at = time.time()
        self.sequence = 0
        self.active = {}
        self.recent = deque(maxlen=MAX_RECENT)
        self.buckets = {}
        self.totals = {k: 0 for k in ("started", "completed", "failed", "cancelled",
            "usage_known", "attributed", "overflow_active", "dropped_requests", "observer_errors", *TOKEN_FIELDS)}
        self._claude_cache = None

    def begin(self, headers):
        self.totals["started"] += 1
        if len(self.active) >= MAX_ACTIVE:
            self.totals["overflow_active"] += 1
            self.totals["dropped_requests"] += 1
            return None
        rid = uuid.uuid4().hex
        now = time.time()
        r = {"id": rid, "started_at": now, "ended_at": None, "last_activity_at": now,
            "first_content_at": None, "state": "routing", "status_code": None,
            "requested_model": "unknown", "served_model": "", "wire_model": "", "route_id": "", "provider": "",
            "lane": "direct", "client": _client(headers.get("x-fabric-client") or headers.get("user-agent")),
            "session_id": None, "agent_id": None, "parent_agent_id": None, "project_id": None,
            "identity_source": "unattributed", "usage": {k: None for k in TOKEN_FIELDS},
            "usage_source": "unavailable", "usage_final": False, "streaming": False,
            "content_events": 0, "attempts": [], "observation_errors": 0}
        for key in ("session_id", "agent_id", "parent_agent_id", "project_id"):
            r[key] = _opaque(headers.get("x-fabric-" + key.replace("_", "-")))
        if r["session_id"] or r["agent_id"]:
            r["identity_source"] = "caller_reported"
        self.active[rid] = r
        return rid

    def input(self, rid, payload):
        r = self.active.get(rid)
        if r is None:
            return
        raw_model = payload.get("model")
        model = label(raw_model) if isinstance(raw_model, str) and raw_model in self.known_models else "unknown"
        r["requested_model"] = model
        r["lane"] = model if model.startswith("fabric/") else "direct"
        r["streaming"] = payload.get("stream") is True
        metadata = payload.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        fabric = metadata.get("fabric")
        fabric = fabric if isinstance(fabric, dict) else {}
        for key in ("session_id", "agent_id", "parent_agent_id", "project_id"):
            if r[key] is None:
                r[key] = _opaque(fabric.get(key))
        if fabric.get("client") in CLIENTS:
            r["client"] = fabric["client"]
        if r["agent_id"] or r["session_id"]:
            r["identity_source"] = "caller_reported"
        elif isinstance(metadata.get("user_id"), str) and len(metadata["user_id"]) <= 1024:
            value = metadata["user_id"]
            # SDK user_id is sometimes a JSON object. Retain only its session ID.
            if value.startswith("{"):
                try:
                    decoded = json.loads(value)
                    value = decoded.get("session_id", "") if isinstance(decoded, dict) else ""
                except ValueError:
                    value = ""
            else:
                match = re.search(r"(?:^|_)session_([a-fA-F0-9-]{16,64})$", value)
                value = match.group(1) if match else ""
            r["session_id"] = _opaque(value)
            if r["session_id"]:
                r["identity_source"] = "sdk_session"

    def attempt(self, rid, route, payload):
        r = self.active.get(rid)
        if r is None:
            return None
        wire_model = label(payload.get("model"))
        public = wire_model
        for candidate in getattr(route, "models", ()):
            if route.wire_model(candidate) == payload.get("model"):
                public = label(candidate)
                if candidate == r["requested_model"]:
                    break
        r.update(route_id=label(route.route_id), provider=label(getattr(route, "pool", "") or route.route_id.split("-", 1)[0]),
                 served_model=public, wire_model=wire_model, state="waiting")
        r.update(usage={k: None for k in TOKEN_FIELDS}, usage_source="unavailable", usage_final=False)
        a = {"route_id": r["route_id"], "model": public, "started_at": time.time(),
             "ended_at": None, "state": "waiting", "reason": "", "status_code": None}
        if len(r["attempts"]) < MAX_ATTEMPTS:
            r["attempts"].append(a)
        else:
            r["observation_errors"] += 1
        return a

    def usage(self, rid, value):
        r = self.active.get(rid)
        if r is None or not isinstance(value, dict):
            return
        mapping = {"input_tokens": "input_tokens", "prompt_tokens": "input_tokens",
                   "output_tokens": "output_tokens", "completion_tokens": "output_tokens",
                   "cache_read_input_tokens": "cache_read_tokens",
                   "cache_creation_input_tokens": "cache_write_tokens"}
        for incoming, target in mapping.items():
            v = number(value.get(incoming))
            if v is not None:
                # Providers report cumulative totals, not incremental event deltas.
                r["usage"][target] = int(v)
                r["usage_source"] = "provider_reported"
        detail = value.get("prompt_tokens_details") or value.get("input_tokens_details")
        if isinstance(detail, dict) and number(detail.get("cached_tokens")) is not None:
            r["usage"]["cache_read_tokens"] = int(detail["cached_tokens"])

    def event(self, rid, event):
        r = self.active.get(rid)
        if r is None or not isinstance(event, dict):
            return
        # Translated wires may synthesize zero usage. Their original provider
        # payload is observed separately, before the incumbent translation.
        if not r.get("_translated_usage"):
            self.usage(rid, event.get("usage"))
            message = event.get("message") or event.get("response")
            if isinstance(message, dict):
                self.usage(rid, message.get("usage"))
        typ = event.get("type")
        delta = event.get("delta")
        content = False
        if typ == "content_block_delta" and isinstance(delta, dict):
            content = any(bool(delta.get(k)) for k in ("text", "thinking", "partial_json"))
        elif typ in {"response.output_text.delta", "response.function_call_arguments.delta", "response.reasoning_summary_text.delta"}:
            content = bool(delta)
        elif typ == "content_block_start":
            block = event.get("content_block")
            content = isinstance(block, dict) and bool(block.get("text") or block.get("thinking"))
        elif isinstance(event.get("content"), list):
            content = bool(event["content"])
        if content:
            now = time.time()
            r["first_content_at"] = r["first_content_at"] or now
            r["last_activity_at"] = now
            r["content_events"] += 1
            r["state"] = "streaming"
        if typ in {"message_stop", "response.completed"}:
            r["usage_final"] = r["usage_source"] == "provider_reported"
        if typ in {"error", "response.failed", "response.incomplete"} or "error" in event:
            r["state"] = "failed"

    def finish(self, rid, state=None):
        if rid is None:
            self.totals["overflow_active"] = max(0, self.totals["overflow_active"] - 1)
            return
        r = self.active.pop(rid, None)
        if r is None:
            return
        now = time.time()
        if state is None:
            if r["state"] == "failed" or (r["status_code"] or 0) >= 400:
                state = "failed"
            elif r["streaming"] and not r.pop("_stream_stopped", False):
                state = "interrupted"
            else:
                state = "completed"
        r.update(state=state, ended_at=now)
        r.pop("_stream_stopped", None)
        r.pop("_translated_usage", None)
        if not r["streaming"] and state == "completed":
            r["usage_final"] = r["usage_source"] == "provider_reported"
        if r["attempts"] and r["attempts"][-1]["state"] != "failed":
            r["attempts"][-1].update(state=state, ended_at=now)
        elif r["attempts"] and r["attempts"][-1]["ended_at"] is None:
            r["attempts"][-1]["ended_at"] = now
        self.recent.appendleft(r)
        key = "completed" if state == "completed" else "cancelled" if state == "cancelled" else "failed"
        self.totals[key] += 1
        if r["session_id"] or r["agent_id"]:
            self.totals["attributed"] += 1
        at = int(now // 60) * 60
        b = self.buckets.setdefault(at, {k: 0 for k in ("completed", "failed", "usage_known", *TOKEN_FIELDS,
                                     *(field + "_known" for field in TOKEN_FIELDS))})
        b["completed" if state == "completed" else "failed"] += 1
        if r["usage"]["output_tokens"] is not None:
            self.totals["usage_known"] += 1
            b["usage_known"] += 1
        for k in TOKEN_FIELDS:
            self.totals[k] += r["usage"][k] or 0
            b[k] += r["usage"][k] or 0
            b[k + "_known"] += r["usage"][k] is not None
        for old in list(self.buckets):
            if old < at - 119 * 60:
                del self.buckets[old]

    def snapshot(self, app):
        cfg, state = app.state.settings, app.state.router_state
        now_mono = time.monotonic()
        routes = []
        for route in cfg.routes:
            counts = state.per_route.get(route.route_id, {})
            routes.append({"id": route.route_id, "provider": getattr(route, "pool", "") or route.route_id.split("-", 1)[0],
                "wire": route.wire, "models": list(route.models), "priority": route.priority, "weight": route.weight,
                "cooling": not state.routes.available(route.route_id, now_mono), "cooldown_s": None,
                "consecutive_failures": state.routes.consecutive_failures.get(route.route_id, 0),
                "served": counts.get("served", 0), "attempt_failed": counts.get("attempt_failed", 0),
                "refused": counts.get("refused", 0)})
        self.sequence += 1
        totals = dict(self.totals)
        for field, source in (("router_served", "served"), ("router_refused", "refused"),
                              ("router_attempts", "attempts"), ("router_failovers", "failovers")):
            totals[field] = getattr(state, source, 0)
        return clean_snapshot({"schema": SCHEMA, "epoch": self.epoch, "sequence": self.sequence,
            "started_at": self.started_at, "generated_at": time.time(), "routes": routes,
            "aliases": {key: list(values) for key, values in cfg.aliases},
            "active": list(self.active.values()), "recent": list(self.recent),
            "series": [dict(at=k, **v) for k, v in sorted(self.buckets.items())], "totals": totals,
            "peak": _observe_peak(app), "overflow": _observe_overflow(app),
            "claude": self.claude_view()})

    def claude_view(self):
        """Latest cached gateway lane observation; never blocks the snapshot path."""
        view = self._claude_cache
        if view is None:
            return None
        return dict(view, observed_at=view.get("observed_at"))


class StreamObserver:
    """Bounded SSE/JSON parser. It never produces or changes response bytes."""
    def __init__(self, store, rid, streaming):
        self.store, self.rid, self.streaming = store, rid, streaming
        self.buffer = bytearray()
        self.data = []
        self.data_size = 0
        self.discard_line = False
        self.discard_event = False
        self.disabled = False

    def _error(self):
        self.store.totals["observer_errors"] += 1
        r = self.store.active.get(self.rid)
        if r:
            r["observation_errors"] += 1

    def _parse(self, data):
        if data.strip() == b"[DONE]":
            r = self.store.active.get(self.rid)
            if r:
                r["_stream_stopped"] = True
            return
        try:
            event = json.loads(data)
            self.store.event(self.rid, event)
            if isinstance(event, dict) and event.get("type") in {"message_stop", "response.completed"}:
                r = self.store.active.get(self.rid)
                if r:
                    r["_stream_stopped"] = True
        except (ValueError, UnicodeError):
            self._error()

    def feed(self, body, final=False):
        if self.disabled:
            return
        if not self.streaming:
            if len(self.buffer) + len(body) > _FRAME_LIMIT:
                self.buffer.clear()
                self.disabled = True
                self._error()
                return
            self.buffer.extend(body)
            if final:
                self._parse(bytes(self.buffer))
                self.buffer.clear()
            return
        # Process complete lines without retaining arbitrarily large ASGI chunks.
        pos = 0
        while pos < len(body):
            end = body.find(b"\n", pos)
            newline = end >= 0
            end = end + 1 if newline else len(body)
            part = memoryview(body)[pos:end]
            pos = end
            if self.discard_line:
                if newline:
                    self.discard_line = False
                continue
            if len(self.buffer) + len(part) > _FRAME_LIMIT:
                self.buffer.clear()
                self.data.clear()
                self.data_size = 0
                self.discard_event = True
                self.discard_line = not newline
                self._error()
                continue
            self.buffer.extend(part)
            if not newline:
                continue
            line = bytes(self.buffer).rstrip(b"\r\n")
            self.buffer.clear()
            if not line:
                if self.data and not self.discard_event:
                    self._parse(b"\n".join(self.data))
                self.data.clear()
                self.data_size = 0
                self.discard_event = False
            elif line.startswith(b"data:") and not self.discard_event:
                value = line[5:].lstrip(b" ")
                self.data_size += len(value)
                if self.data_size > _FRAME_LIMIT:
                    self.data.clear()
                    self.discard_event = True
                    self._error()
                else:
                    self.data.append(value)
        if final:
            # An unterminated event is not proof of completion.
            self.buffer.clear()
            self.data.clear()


class ObserveASGI:
    def __init__(self, app, store, settings):
        self.app, self.store, self.settings = app, store, settings

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path") != "/v1/messages" or scope.get("method") != "POST":
            return await self.app(scope, receive, send)
        headers = {k.decode("latin1").lower(): v.decode("latin1") for k, v in scope.get("headers", [])}
        candidate = headers.get("authorization", "")
        token = candidate[7:] if candidate.lower().startswith("bearer ") else ""
        api_key = headers.get("x-api-key", "")
        try:
            local = ipaddress.ip_address((scope.get("client") or ("",))[0]).is_loopback
        except ValueError:
            local = False
        valid = (bool(token) and hmac.compare_digest(token.encode("latin1"), self.settings.proxy_token.encode())) or (
                 bool(api_key) and hmac.compare_digest(api_key.encode("latin1"), self.settings.proxy_token.encode()))
        if not local or not valid:
            return await self.app(scope, receive, send)
        try:
            rid = self.store.begin(headers)
        except Exception:
            return await self.app(scope, receive, send)
        context = _CONTEXT.set((self.store, rid))
        parser = None
        terminal = None

        async def observed_send(message):
            nonlocal parser
            # Timings describe bytes successfully handed to the actual ASGI sender.
            await send(message)
            if rid is None:
                return
            try:
                r = self.store.active.get(rid)
                if r is None:
                    return
                if message["type"] == "http.response.start":
                    r["status_code"] = message["status"]
                    response_headers = dict(message.get("headers", []))
                    streaming = b"text/event-stream" in response_headers.get(b"content-type", b"")
                    r["streaming"] = streaming
                    parser = StreamObserver(self.store, rid, streaming)
                elif message["type"] == "http.response.body" and parser:
                    parser.feed(message.get("body", b""), not message.get("more_body", False))
            except Exception:
                self.store.totals["observer_errors"] += 1

        try:
            await self.app(scope, receive, observed_send)
        except asyncio.CancelledError:
            terminal = "cancelled"
            raise
        except BaseException:
            terminal = "failed"
            raise
        finally:
            _CONTEXT.reset(context)
            try:
                self.store.finish(rid, terminal)
            except Exception:
                self.store.totals["observer_errors"] += 1


def _wrap_forwarder(original, name, reasons):
    sig = inspect.signature(original)

    @functools.wraps(original)
    async def observed(*args, **kwargs):
        context = _CONTEXT.get()
        attempt = None
        if context and context[1] is not None:
            try:
                bound = sig.bind(*args, **kwargs).arguments
                attempt = context[0].attempt(context[1], bound["route"], bound["payload"])
                context[0].active[context[1]]["_translated_usage"] = name != "_forward_anthropic"
            except Exception:
                context[0].totals["observer_errors"] += 1
        try:
            response = await original(*args, **kwargs)
        except BaseException as exc:
            if attempt is not None:
                reason = getattr(exc, "reason", "")
                safe = reason if isinstance(reason, str) and (reason in reasons or re.fullmatch(r"FABRIC_ROUTE_HTTP_[1-5][0-9]{2}", reason)) else "provider_error"
                attempt.update(state="failed", ended_at=time.time(), reason=safe)
            raise
        if attempt is not None:
            status = getattr(response, "status_code", None)
            attempt.update(state="failed" if status and status >= 400 else "streaming", status_code=status)
        return response
    return observed


def _provider_usage(value):
    context = _CONTEXT.get()
    if not context or context[1] is None or not isinstance(value, dict):
        return
    try:
        context[0].usage(context[1], value.get("usage"))
        response = value.get("response")
        if isinstance(response, dict):
            context[0].usage(context[1], response.get("usage"))
    except Exception:
        context[0].totals["observer_errors"] += 1


def _usage_function(original):
    @functools.wraps(original)
    def wrapped(payload, *args, **kwargs):
        result = original(payload, *args, **kwargs)
        _provider_usage(payload)
        return result
    wrapped._capacity_observed = True
    return wrapped


def _usage_translator(original):
    class ObservedTranslator(original):
        _capacity_observed = True

        def feed(self, chunk, *args, **kwargs):
            result = super().feed(chunk, *args, **kwargs)
            _provider_usage(chunk)
            return result
    return ObservedTranslator


def instrument_app(app, gateway, *, export_config=None):
    """Wrap only the already-discovered endpoint closure; fail before partial install."""
    if hasattr(app.state, "capacity_observer"):
        return app
    endpoint = next((r.endpoint for r in app.routes if getattr(r, "path", None) == "/v1/messages"), None)
    cells = dict(zip(endpoint.__code__.co_freevars, endpoint.__closure__ or [])) if endpoint else {}
    for name in _FORWARDERS:
        if name not in cells or not inspect.iscoroutinefunction(cells[name].cell_contents):
            raise RuntimeError("incumbent forwarder contract changed")
        if not {"route", "payload"} <= set(inspect.signature(cells[name].cell_contents).parameters):
            raise RuntimeError("incumbent forwarder signature changed")
    candidate_fn = gateway._model_candidates
    cfg = app.state.settings
    store = ObservationStore([m for r in cfg.routes for m in r.models] + [a for a, _ in cfg.aliases])
    if not getattr(candidate_fn, "_capacity_observed", False):
        @functools.wraps(candidate_fn)
        def candidates(payload, aliases):
            result = candidate_fn(payload, aliases)
            context = _CONTEXT.get()
            if context and context[1] is not None:
                try:
                    context[0].input(context[1], payload)
                except Exception:
                    context[0].totals["observer_errors"] += 1
            return result
        candidates._capacity_observed = True
        gateway._model_candidates = candidates
    reasons = frozenset(getattr(gateway, "_PUBLIC_REFUSAL_CODES", ())) | {
        "FABRIC_OAUTH_ACCOUNTS_EXHAUSTED", "FABRIC_OAUTH_ACCOUNT_LIMIT", "FABRIC_OAUTH_UPSTREAM_5XX", "FABRIC_OAUTH_NO_ACCOUNT"}
    for name in _FORWARDERS:
        cells[name].cell_contents = _wrap_forwarder(cells[name].cell_contents, name, reasons)
    for name, wrapper in (("openai_to_anthropic", _usage_function), ("responses_to_anthropic", _usage_function),
                          ("OpenAIStreamTranslator", _usage_translator), ("ResponsesStreamTranslator", _usage_translator)):
        original = getattr(gateway, name, None)
        if original is not None and not getattr(original, "_capacity_observed", False):
            setattr(gateway, name, wrapper(original))
    app.state.capacity_observer = store
    app.add_middleware(ObserveASGI, store=store, settings=app.state.settings)
    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(instance):
        async with original_lifespan(instance):
            task = asyncio.create_task(publish_snapshots(instance, store, export_config)) if export_config else None
            lanes = asyncio.create_task(poll_claude_lanes(store, export_config)) if export_config else None
            try:
                yield
            finally:
                for running in (task, lanes):
                    if running:
                        running.cancel()
                        with suppress(asyncio.CancelledError, TimeoutError):
                            await asyncio.wait_for(running, 2)
    app.router.lifespan_context = lifespan
    return app


def serialize_snapshot(snapshot):
    """Keep live observations deliverable when optional detail exceeds the budget."""
    def encode():
        return json.dumps(snapshot, separators=(",", ":"), allow_nan=False).encode() + b"\n"
    body = encode()
    while len(body) > MAX_BYTES and snapshot["recent"]:
        keep = len(snapshot["recent"]) // 2
        snapshot["truncated"]["recent"] += len(snapshot["recent"]) - keep
        del snapshot["recent"][keep:]
        body = encode()
    if len(body) > MAX_BYTES:
        for r in snapshot["active"]:
            snapshot["truncated"]["attempts"] += max(0, len(r["attempts"]) - 2)
            r["attempts"] = r["attempts"][-2:]
        body = encode()
    if len(body) > MAX_BYTES:
        for route in snapshot["routes"]:
            snapshot["truncated"]["models"] += max(0, len(route["models"]) - 8)
            route["models"] = route["models"][:8]
        body = encode()
    if len(body) > MAX_BYTES:
        raise ValueError("observation exceeded compact bound")
    return body


_CLAUDE_LANE_FIELDS = ("used_weekly", "budget_weekly", "remaining_weekly", "pressure",
                       "cooldown_until", "weekly_resets_at", "weekly_reset_source", "expiring_soon")
_CLAUDE_ACCOUNT_FIELDS = ("id", "label", "used_5h", "budget_5h", "remaining_5h",
                          "inflight", "last_status", "drain", "cooldown_until")


async def poll_claude_lanes(store, config):
    """Cache the incumbent gateway's lane budgets on a slow loopback read.

    The gateway owns the accounts and tokens; this reads its existing status
    surface with the operator-configured loopback token and keeps only bounded
    content-free scalars. A failed read leaves the previous observation in place
    with its original timestamp; it never invents capacity.
    """
    url = (config or {}).get("claude_status_url")
    token_env = (config or {}).get("claude_token_env")
    if not isinstance(url, str) or not url.startswith("http://127.0.0.1:"):
        return
    token = os.environ.get(token_env) if isinstance(token_env, str) else None
    if not token:
        return
    import urllib.request
    while True:
        try:
            def read():
                request = urllib.request.Request(url, headers={"x-api-key": token})
                with urllib.request.urlopen(request, timeout=5) as response:
                    return json.loads(response.read(512 * 1024))
            payload = await asyncio.to_thread(read)
            # The gateway reports accounts plus a flat (account, family) lane
            # list; join them here into the bounded per-account shape.
            now = time.time()
            horizon = payload.get("expiry_horizon_s")
            lanes_by_account = {}
            for lane in (payload.get("families") or [])[:128]:
                if not isinstance(lane, dict):
                    continue
                row = {k: lane.get(k) for k in _CLAUDE_LANE_FIELDS}
                resets = lane.get("weekly_resets_at")
                row["expiring_soon"] = bool(resets and horizon and (resets - now) <= horizon)
                lanes_by_account.setdefault(lane.get("account"), {})[lane.get("family")] = row
            accounts = []
            for account in (payload.get("accounts") or [])[:16]:
                if not isinstance(account, dict):
                    continue
                row = {k: account.get(k) for k in _CLAUDE_ACCOUNT_FIELDS}
                row["id"] = account.get("account")
                row["families"] = lanes_by_account.get(account.get("account"), {})
                accounts.append(row)
            store._claude_cache = {
                "reachable": True, "observed_at": time.time(),
                "stranded_family": payload.get("stranded_family"),
                "preferences": payload.get("preferences") or [],
                "accounts": accounts,
            }
        except asyncio.CancelledError:
            raise
        except Exception:
            pass  # keep the last good observation; staleness is visible downstream
        await asyncio.sleep(30)


async def publish_snapshots(app, store, config):
    """One latest-value SSH stream; no backlog and no work on inference's path."""
    alias = config.get("ssh_alias")
    if not isinstance(alias, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", alias):
        return
    process = None
    delay = 2
    try:
        while True:
            try:
                if process is None or process.returncode is not None:
                    process = await asyncio.create_subprocess_exec(
                        "ssh", "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
                        "-o", "ConnectTimeout=8", "-o", "ServerAliveInterval=10", "-o", "ServerAliveCountMax=2",
                        alias, "cd /opt/macro && exec /opt/macro/.venv/bin/python -m admin.capacity_ingest",
                        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                # Snapshot copies bounded scalar structures before off-thread encoding.
                snapshot = store.snapshot(app)
                body = await asyncio.to_thread(serialize_snapshot, snapshot)
                process.stdin.write(body)
                await asyncio.wait_for(process.stdin.drain(), 3)
                delay = 2
                await asyncio.sleep(2)
            except asyncio.CancelledError:
                raise
            except Exception:
                store.totals["observer_errors"] += 1
                if process and process.returncode is None:
                    process.kill()
                    await process.wait()
                process = None
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30)
    finally:
        if process and process.returncode is None:
            process.kill()
            with suppress(Exception):
                await process.wait()


def create_app():
    gateway = importlib.import_module(__package__ + ".gateway")
    config_path = Path(__file__).with_name("observatory-export.json")
    config = json.loads(config_path.read_text()) if config_path.is_file() else None
    return instrument_app(gateway.create_app(), gateway, export_config=config)
