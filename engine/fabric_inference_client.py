"""Text/tool/SSE client for an already-admitted shared Fabric gateway.

This translates the incumbent consumers' Anthropic-shaped interface to the
gateway's existing /v1/chat/completions route. It does not select accounts,
authorize a workload, reserve worker capacity, or own a queue/quota ledger.
Only an explicit numeric loopback endpoint is accepted. Every intentional step
requires its original request_id; there is one POST, with no redirect, proxy,
automatic retry or model fallback. An uncertain request poisons this client,
which must be constructed fresh for each application turn.

Protocol reference: https://developers.openai.com/api/reference/resources/chat
Missing usage is None, including an interrupted stream without its usage chunk.
Closing a connection is never represented as proof of provider cancellation.
"""
from __future__ import annotations

import http.client
import hashlib
import json
import math
import re
import socket
import ssl
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from types import SimpleNamespace
from urllib.parse import urlsplit

MAX_REQUEST_BYTES = 1024 * 1024
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_SSE_LINE_BYTES = 1024 * 1024
MAX_SSE_EVENTS = 32768
MAX_STEPS = 256
MAX_TOOLS = 128
_ID = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z")
_NATIVE_ID = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
LEGACY_PROTOCOL = "openai_chat_v1"
NATIVE_PROTOCOL = "native_application_v1"
NATIVE_SCHEMA = "mastermind.fabric_application.v1"
AUTO_SCHEMA = "mastermind.fabric_application.v2"
AUTO_INSPECTION_SCHEMA = "mastermind.fabric_application_inspection.v2"
AUTO_BINDING_SCHEMA = "mastermind.fabric_application_binding.v2"
EXACT_INSPECTION_SCHEMA = "mastermind.fabric_application_inspection.v3"
EXACT_BINDING_SCHEMA = "mastermind.fabric_application_binding.v3"
AUTO_POOLS = frozenset({"go", "bailian", "codex-native", "claude-native",
                        "glm", "minimax", "grok", "cursor", "ocfree"})
MAX_NATIVE_TOKENS = 10 ** 12
_CALL_KEYS = frozenset({"model", "messages", "system", "tools", "tool_choice",
                        "max_tokens", "temperature", "stop_sequences", "request_id"})
_FINISH = {"stop": "end_turn", "length": "max_tokens", "tool_calls": "tool_use"}


class FabricInferenceError(RuntimeError):
    """Bounded failure metadata; never transport text, tokens, URLs or prompts."""

    def __init__(self, code: str, *, effect_unknown: bool = False, status_code=None,
                 disposition=None, request_id=None, observed_usage=None,
                 serving_model=None, application_observation=None):
        super().__init__(code)
        self.code = code
        self.effect_unknown = effect_unknown
        self.status_code = status_code
        self.disposition = disposition
        self.request_id = request_id
        self.observed_usage = observed_usage
        self.serving_model = serving_model
        self.application_observation = application_observation


@dataclass(frozen=True)
class TextBlock:
    text: str
    type: str = "text"

    def model_dump(self):
        return {"type": "text", "text": self.text}


@dataclass(frozen=True)
class ToolUseBlock:
    id: str
    name: str
    input: dict
    type: str = "tool_use"

    def model_dump(self):
        return {"type": "tool_use", "id": self.id, "name": self.name, "input": self.input}


@dataclass(frozen=True)
class Usage:
    input_tokens: int | None
    output_tokens: int | None


@dataclass(frozen=True)
class Message:
    model: str
    content: list
    stop_reason: str
    usage: Usage
    application_observation: ApplicationObservation | None = None


@dataclass(frozen=True)
class ApplicationObservation:
    """A validated immutable response observation; reading it performs no effect."""
    _encoded: str = field(repr=False)

    @property
    def document(self):
        return json.loads(self._encoded)


def _refuse(code="fabric_request_invalid", *, unknown=False):
    raise FabricInferenceError(code, effect_unknown=unknown)


def _safe_id(value):
    return isinstance(value, str) and _ID.fullmatch(value) is not None


def validate_native_operation_id(value):
    """Validate the original identity; never rewrite it or infer it from a step."""
    if not isinstance(value, str) or _NATIVE_ID.fullmatch(value) is None:
        _refuse("fabric_native_identity_invalid")


def _plain(value):
    if callable(getattr(value, "model_dump", None)):
        value = value.model_dump()
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def _json_bytes(value):
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False,
                          separators=(",", ":")).encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError):
        _refuse()


def _load_json(data, *, unknown=True):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError("duplicate key")
            out[key] = value
        return out

    def nonfinite(_):
        raise ValueError("nonfinite value")

    try:
        parsed = json.loads(data, object_pairs_hook=pairs, parse_constant=nonfinite)
        json.dumps(parsed, allow_nan=False)  # Reject overflowing finite literals.
        return parsed
    except (ValueError, TypeError, UnicodeError, RecursionError):
        _refuse("fabric_response_invalid", unknown=unknown)


def _text_content(value):
    if isinstance(value, str):
        return value
    if not isinstance(value, list):
        _refuse()
    parts = []
    for block in value:
        if (not isinstance(block, dict) or set(block) != {"type", "text"}
                or block["type"] != "text" or not isinstance(block["text"], str)):
            _refuse("fabric_content_unsupported")
        parts.append(block["text"])
    return "".join(parts)


def _messages(messages, system):
    if not isinstance(messages, list) or not messages or len(messages) > 1024:
        _refuse()
    out = []
    if system is not None:
        out.append({"role": "system", "content": _text_content(system)})
    pending = set()
    for message in messages:
        if (not isinstance(message, dict) or set(message) != {"role", "content"}
                or message["role"] not in {"user", "assistant"}):
            _refuse()
        role, content = message["role"], message["content"]
        if isinstance(content, str):
            if pending:
                _refuse("fabric_tool_history_invalid")
            out.append({"role": role, "content": content})
            continue
        if not isinstance(content, list):
            _refuse()
        if role == "assistant":
            if pending:
                _refuse("fabric_tool_history_invalid")
            text, calls = [], []
            for block in content:
                if not isinstance(block, dict):
                    _refuse()
                if block.get("type") == "text":
                    text.append(_text_content([block]))
                elif block.get("type") == "tool_use":
                    if (set(block) != {"type", "id", "name", "input"}
                            or not _safe_id(block["id"]) or not _safe_id(block["name"])
                            or not isinstance(block["input"], dict) or block["id"] in pending):
                        _refuse("fabric_tool_history_invalid")
                    pending.add(block["id"])
                    calls.append({"id": block["id"], "type": "function", "function": {
                        "name": block["name"], "arguments": _json_bytes(block["input"]).decode()}})
                else:
                    _refuse("fabric_content_unsupported")
            item = {"role": "assistant", "content": "".join(text) or None}
            if calls:
                item["tool_calls"] = calls
            out.append(item)
        else:
            text = []
            for block in content:
                if not isinstance(block, dict):
                    _refuse()
                if block.get("type") == "text":
                    if pending:
                        _refuse("fabric_tool_history_invalid")
                    text.append(_text_content([block]))
                elif block.get("type") == "tool_result":
                    if (set(block) - {"type", "tool_use_id", "content", "is_error"}
                            or not {"tool_use_id", "content"} <= set(block)
                            or block["tool_use_id"] not in pending
                            or ("is_error" in block and type(block["is_error"]) is not bool)):
                        _refuse("fabric_tool_history_invalid")
                    if text:
                        out.append({"role": "user", "content": "".join(text)})
                        text = []
                    value = _text_content(block["content"])
                    if block.get("is_error"):
                        value = "Tool error:\n" + value
                    out.append({"role": "tool", "tool_call_id": block["tool_use_id"], "content": value})
                    pending.remove(block["tool_use_id"])
                else:
                    _refuse("fabric_content_unsupported")
            if text:
                out.append({"role": "user", "content": "".join(text)})
    if pending:
        _refuse("fabric_tool_history_invalid")
    return out


def _request(kwargs, model, streaming, *, exact_scoped=False):
    allowed = _CALL_KEYS | ({"reasoning_effort", "stream"} if exact_scoped else set())
    if set(kwargs) - allowed or "model" not in kwargs or kwargs["model"] != model:
        _refuse()
    if "stream" in kwargs and (streaming or kwargs["stream"] is not False):
        _refuse("fabric_native_stream_unsupported")
    controlled = "reasoning_effort" in kwargs or (exact_scoped and model == "qwen3.8-flash" and "temperature" in kwargs)
    if controlled and (not exact_scoped or model != "qwen3.8-flash" or streaming
            or type(kwargs.get("temperature")) not in (int, float) or kwargs["temperature"] != 0
            or kwargs.get("reasoning_effort") != "none"
            or any(key in kwargs for key in ("tools", "tool_choice", "stop_sequences"))):
        _refuse("fabric_qwen_control_invalid")
    request_id = kwargs.get("request_id")
    if not _safe_id(request_id):
        _refuse("fabric_request_identity_invalid")
    maximum = kwargs.get("max_tokens")
    if type(maximum) is not int or not 1 <= maximum <= 32768:
        _refuse("fabric_token_budget_invalid")
    kw = _plain(kwargs)
    payload = {"model": model, "max_tokens": maximum, "stream": streaming,
               "messages": _messages(kw.get("messages"), kw.get("system"))}
    tools = kw.get("tools", [])
    if not isinstance(tools, list) or len(tools) > MAX_TOOLS:
        _refuse()
    names, functions = set(), []
    for tool in tools:
        if (not isinstance(tool, dict) or set(tool) - {"name", "description", "input_schema"}
                or not _safe_id(tool.get("name")) or tool["name"] in names
                or not isinstance(tool.get("input_schema"), dict)
                or ("description" in tool and not isinstance(tool["description"], str))):
            _refuse("fabric_tools_invalid")
        names.add(tool["name"])
        function = {"name": tool["name"], "parameters": tool["input_schema"]}
        if "description" in tool:
            function["description"] = tool["description"]
        functions.append({"type": "function", "function": function})
    if functions:
        payload["tools"] = functions
    if "tool_choice" in kw:
        choice = kw["tool_choice"]
        if not isinstance(choice, dict):
            _refuse()
        kind = choice.get("type")
        if set(choice) == {"type"} and kind in {"auto", "none", "any"}:
            if kind == "any" and not names:
                _refuse()
            payload["tool_choice"] = {"auto": "auto", "none": "none", "any": "required"}[kind]
        elif set(choice) == {"type", "name"} and kind == "tool" and choice["name"] in names:
            payload["tool_choice"] = {"type": "function", "function": {"name": choice["name"]}}
        else:
            _refuse()
    if "temperature" in kw:
        value = kw["temperature"]
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 2:
            _refuse()
        payload["temperature"] = value
    if controlled:
        payload["reasoning_effort"] = "none"
    if "stop_sequences" in kw:
        stops = kw["stop_sequences"]
        if not isinstance(stops, list) or len(stops) > 4 or not all(isinstance(x, str) for x in stops):
            _refuse()
        payload["stop"] = stops
    if streaming:
        payload["stream_options"] = {"include_usage": True}
    body = _json_bytes(payload)
    if len(body) > MAX_REQUEST_BYTES:
        _refuse("fabric_request_too_large")
    return request_id, body


def _usage(value):
    value = value if isinstance(value, dict) else {}
    def number(key):
        token = value.get(key)
        return token if type(token) is int and 0 <= token <= MAX_NATIVE_TOKENS else None
    return Usage(number("prompt_tokens"), number("completion_tokens"))


def _message(model, text, calls, finish, usage):
    if finish not in _FINISH or bool(calls) != (finish == "tool_calls"):
        _refuse("fabric_finish_reason_invalid", unknown=True)
    if not isinstance(text, str) or not isinstance(calls, list) or len(calls) > MAX_TOOLS:
        _refuse("fabric_response_invalid", unknown=True)
    blocks, ids = ([TextBlock(text)] if text else []), set()
    for call in calls:
        if (not isinstance(call, dict) or call.get("type") != "function"
                or not _safe_id(call.get("id")) or call["id"] in ids
                or not isinstance(call.get("function"), dict)):
            _refuse("fabric_tool_response_invalid", unknown=True)
        function = call["function"]
        if not _safe_id(function.get("name")) or not isinstance(function.get("arguments"), str):
            _refuse("fabric_tool_response_invalid", unknown=True)
        params = _load_json(function["arguments"])
        if not isinstance(params, dict):
            _refuse("fabric_tool_response_invalid", unknown=True)
        ids.add(call["id"])
        blocks.append(ToolUseBlock(call["id"], function["name"], params))
    return Message(model, blocks, _FINISH[finish], _usage(usage))


def _completion(payload, expected_model):
    if not isinstance(payload, dict) or payload.get("model") != expected_model:
        _refuse("fabric_response_model_mismatch", unknown=True)
    choices = payload.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        _refuse("fabric_response_invalid", unknown=True)
    choice = choices[0]
    msg = choice.get("message")
    if (type(choice.get("index")) is not int or choice["index"] != 0
            or not isinstance(msg, dict) or msg.get("role") != "assistant"
            or msg.get("refusal") or msg.get("function_call") or msg.get("audio")):
        _refuse("fabric_response_invalid", unknown=True)
    text = msg.get("content")
    if text is None:
        text = ""
    calls = msg.get("tool_calls")
    return _message(expected_model, text, [] if calls is None else calls,
                    choice.get("finish_reason"), payload.get("usage"))


class _Exchange:
    def __init__(self, client, connection, response, deadline):
        self.client, self.connection, self.response = client, connection, response
        self.deadline, self.bytes, self.closed = deadline, 0, False

    def read(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            _refuse("fabric_timeout", unknown=True)
        sock = self.connection.sock
        if sock is None:
            sock = getattr(getattr(self.response.fp, "raw", None), "_sock", None)
        if sock is not None:
            sock.settimeout(remaining)
        data = self.response.read1(min(65536, MAX_RESPONSE_BYTES + 1 - self.bytes))
        if not data and self.response.length not in (None, 0):
            _refuse("fabric_response_incomplete", unknown=True)
        self.bytes += len(data)
        if self.bytes > MAX_RESPONSE_BYTES:
            _refuse("fabric_response_too_large", unknown=True)
        return data

    def close(self):
        if not self.closed:
            self.closed = True
            # Closing this local descriptor cannot erase an observed response.
            try:
                self.response.close()
            except Exception:
                pass
            try:
                finish = getattr(self.connection, "finish", self.connection.close)
                finish()
            except Exception:
                pass

    def body(self):
        parts = []
        while part := self.read():
            parts.append(part)
        return b"".join(parts)


class _NativeConnection(http.client.HTTPConnection):
    """One numeric-loopback connection with one absolute socket deadline.

    The timer interrupts only this connection; it cannot create requests or
    retry them. Native transport needs no DNS, proxy or redirect discovery.
    """
    def __init__(self, host, port, *, deadline, tls=False):
        # Closed role aliases share the incumbent APPLICATION tunnel. They
        # never introduce DNS, a proxy, an arbitrary listener or a new broker.
        if (host not in {"127.0.0.1", "127.0.0.2", "127.0.0.3"}
                or host != "127.0.0.1" and (port != 50142 or tls)):
            _refuse("fabric_endpoint_invalid")
        super().__init__(host, port, timeout=max(0.001, deadline - time.monotonic()))
        self._deadline, self._tls = deadline, tls
        self._deadline_socket = None
        self._expired = threading.Event()
        self._timer = threading.Timer(max(0.0, deadline - time.monotonic()), self._abort)
        self._timer.daemon = True
        self._timer.start()

    def _remaining(self):
        remaining = self._deadline - time.monotonic()
        if self._expired.is_set() or remaining <= 0:
            raise TimeoutError("native transport deadline")
        return remaining

    def _abort(self):
        self._expired.set()
        sock = self._deadline_socket
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._deadline_socket = self.sock
        self.sock.settimeout(self._remaining())
        self.sock.connect((self.host, self.port))
        if self._tls:
            context = ssl.create_default_context()
            self.sock = context.wrap_socket(self.sock, server_hostname=self.host,
                                            do_handshake_on_connect=False)
            self._deadline_socket = self.sock
            self.sock.settimeout(self._remaining())
            self.sock.do_handshake()
        self._remaining()

    def send(self, data):
        self._remaining()
        return super().send(data)

    def finish(self):
        self._timer.cancel()
        self._timer.join(timeout=0.2)
        self.close()


def _native_header(response, name, expected):
    values = response.headers.get_all(name) or []
    if values != ([] if expected is None else [expected]):
        _refuse("fabric_native_correlation_invalid", unknown=True)


def _response_framing(response):
    lengths = response.headers.get_all("Content-Length") or []
    transfers = response.headers.get_all("Transfer-Encoding") or []
    if (len(lengths) > 1 or len(transfers) > 1 or lengths and transfers
            or transfers and transfers[0].strip().lower() != "chunked"):
        _refuse("fabric_response_framing_invalid", unknown=True)
    if lengths and (re.fullmatch(r"[0-9]{1,10}", lengths[0]) is None
                    or int(lengths[0]) > MAX_RESPONSE_BYTES):
        _refuse("fabric_response_framing_invalid", unknown=True)


def _native_envelope(response, payload, *, operation_id, request_id, closing=False):
    """Decode a correlated non-answer; status alone never proves no effect."""
    required = {"schema", "disposition", "turn_id", "request_id",
                "dispatch_permitted", "effect_unknown"}
    if (type(payload) is not dict or set(payload) - {"application", "error"}
            or type(payload.get("application")) is not dict):
        _refuse("fabric_native_envelope_invalid", unknown=True)
    state = payload["application"]
    if (not required <= set(state) or set(state) - required - {"usage", "serving_model"}
            or state["schema"] != NATIVE_SCHEMA or state["dispatch_permitted"] is not False
            or type(state["effect_unknown"]) is not bool):
        _refuse("fabric_native_envelope_invalid", unknown=True)
    disposition = state["disposition"]
    allowed = {"refused", "pending", "effect_unknown", "closed"} if closing else {
        "refused", "pending", "effect_unknown", "terminal", "terminal_receipt_only"}
    if (not isinstance(disposition, str) or disposition not in allowed
            or state["effect_unknown"] != (disposition in {"pending", "effect_unknown"})):
        _refuse("fabric_native_envelope_invalid", unknown=True)
    status = response.status
    if ((disposition == "refused" and not 400 <= status < 500)
            or (disposition == "terminal" and not 300 <= status <= 599)
            or (disposition == "terminal_receipt_only" and status != 409)
            or (disposition in {"pending", "effect_unknown"} and status not in {409, 503})
            or (disposition == "closed" and status != 200)):
        _refuse("fabric_native_envelope_invalid", unknown=True)
    error = payload.get("error")
    if "error" in payload and (type(error) is not dict or set(error) != {"type", "message"}
            or not isinstance(error["type"], str) or _NATIVE_ID.fullmatch(error["type"]) is None
            or not isinstance(error["message"], str) or len(error["message"]) > 256):
        _refuse("fabric_native_envelope_invalid", unknown=True)
    code = error.get("type") if error is not None else None
    preparse = disposition == "refused" and code in {
        "application_unauthorized", "application_route_unsupported",
        "application_request_invalid", "application_close_invalid"}
    if state["turn_id"] != operation_id and not (preparse and state["turn_id"] is None):
        _refuse("fabric_native_correlation_invalid", unknown=True)
    if state["request_id"] != request_id and not (preparse and state["request_id"] is None):
        _refuse("fabric_native_correlation_invalid", unknown=True)
    if (not closing and (state["turn_id"] is None or state["request_id"] is None)
            and not (preparse and state["turn_id"] is None and state["request_id"] is None)):
        _refuse("fabric_native_correlation_invalid", unknown=True)
    _native_header(response, "X-MM-Application-Disposition", disposition)
    _native_header(response, "X-MM-Application-Turn-ID", state["turn_id"])
    _native_header(response, "X-MM-Application-Request-ID", state["request_id"])
    observed = set(state) & {"usage", "serving_model"}
    usage, model = None, None
    if observed:
        if (observed != {"usage", "serving_model"} or closing
                or disposition not in {"terminal", "effect_unknown"}
                or type(state["usage"]) is not dict
                or set(state["usage"]) != {"input_tokens", "output_tokens"}):
            _refuse("fabric_native_envelope_invalid", unknown=True)
        usage = _usage({"prompt_tokens": state["usage"]["input_tokens"],
                        "completion_tokens": state["usage"]["output_tokens"]})
        value = state["serving_model"]
        model = value if _safe_id(value) else None
    return FabricInferenceError("fabric_native_" + disposition,
        effect_unknown=state["effect_unknown"], status_code=status,
        disposition=disposition, request_id=request_id,
        observed_usage=usage, serving_model=model)


def _canonical_auto(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False)
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError):
        _refuse("fabric_auto_document_invalid")


def validate_auto_route_scope(value):
    """Validate the wire restriction; A alone grants and selects actual routes."""
    if (type(value) is not dict or set(value) != {"schema", "pools"}
            or value["schema"] != "mastermind.application_route_scope.v1"):
        _refuse("fabric_auto_scope_invalid")
    pools = value["pools"]
    if (type(pools) is not list or not 1 <= len(pools) <= len(AUTO_POOLS)
            or any(type(pool) is not str or pool not in AUTO_POOLS for pool in pools)
            or pools != sorted(set(pools))):
        _refuse("fabric_auto_scope_invalid")
    encoded = _canonical_auto(value)
    return json.loads(encoded), hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def validate_auto_inspection(value):
    fields = {"schema", "requested_model", "route_scope", "route_scope_digest",
              "output_limit_mode", "cap_id", "capability_id", "workload_policy", "transport_identity"}
    if (type(value) is not dict or set(value) != fields
            or value["schema"] not in {AUTO_INSPECTION_SCHEMA, EXACT_INSPECTION_SCHEMA}
            or (value["schema"] == AUTO_INSPECTION_SCHEMA and value["requested_model"] is not None)
            or (value["schema"] == EXACT_INSPECTION_SCHEMA and not _safe_id(value["requested_model"]))
            or value["output_limit_mode"] != "hard_maximum"
            or not all(_safe_id(value[key]) for key in ("cap_id", "capability_id"))
            or type(value["workload_policy"]) is not dict):
        _refuse("fabric_auto_inspection_invalid")
    scope, digest = validate_auto_route_scope(value["route_scope"])
    if (value["route_scope_digest"] != digest or type(value["transport_identity"]) is not str
            or re.fullmatch(r"[0-9a-f]{64}", value["transport_identity"]) is None):
        _refuse("fabric_auto_inspection_invalid")
    encoded = _canonical_auto(value)
    if len(encoded.encode("utf-8")) > 32768:
        _refuse("fabric_auto_inspection_invalid")
    return json.loads(encoded)


def _auto_request_digest(payload):
    encoded = _canonical_auto({"path": "/v1/chat/completions", "payload": payload}).encode("utf-8")
    if len(encoded) > MAX_REQUEST_BYTES:
        _refuse("fabric_request_too_large")
    return hashlib.sha256(encoded).hexdigest()


def _auto_route_metadata(value, inspection, maximum):
    fields = {"schema", "requested_model", "route_scope", "route_scope_digest", "selection_digest",
              "request_digest", "routed_request_digest", "pool", "selected_model", "mode", "protocol",
              "driver", "profile", "source", "recipe_digest", "output_contract"}
    exact = inspection["schema"] == EXACT_INSPECTION_SCHEMA
    if (type(value) is not dict or set(value) != fields
            or value["schema"] != ("mastermind.fabric_application_route.v2" if exact
                                   else "mastermind.fabric_application_route.v1")
            or value["requested_model"] != inspection["requested_model"]
            or exact and value["selected_model"] != inspection["requested_model"]
            or value["route_scope"] != inspection["route_scope"]
            or value["route_scope_digest"] != inspection["route_scope_digest"]
            or value["pool"] not in inspection["route_scope"]["pools"]
            or not all(_safe_id(value[key]) for key in
                       ("selected_model", "mode", "driver", "profile", "source"))
            or type(value["protocol"]) is not str
            or value["protocol"] not in {"chat", "responses", "harness"}
            or value["output_contract"] != {"mode": "hard_maximum", "max_tokens": maximum}):
        _refuse("fabric_auto_route_invalid", unknown=True)
    if exact and value["routed_request_digest"] is not None:
        _refuse("fabric_auto_route_invalid", unknown=True)
    for key in (("selection_digest", "request_digest") if exact else
                ("selection_digest", "request_digest", "routed_request_digest")):
        if type(value[key]) is not str or re.fullmatch(r"[0-9a-f]{64}", value[key]) is None:
            _refuse("fabric_auto_route_invalid", unknown=True)
    recipe = value["recipe_digest"]
    if ((value["pool"] == "go" and (recipe is not None or value["protocol"] != "chat"))
            or value["pool"] != "go" and (type(recipe) is not str
                or re.fullmatch(r"[0-9a-f]{64}", recipe) is None)
            or value["pool"] == "bailian" and value["protocol"] != "responses"
            or value["pool"] not in {"go", "bailian"} and value["protocol"] != "harness"):
        _refuse("fabric_auto_route_invalid", unknown=True)
    return json.loads(_canonical_auto(value))


def _auto_route(value, inspection, original):
    if "model" not in original or original["model"] != inspection["requested_model"]:
        _refuse("fabric_auto_route_invalid", unknown=True)
    value = _auto_route_metadata(value, inspection, original["max_tokens"])
    routed = (None if inspection["schema"] == EXACT_INSPECTION_SCHEMA else
              _auto_request_digest(dict(original, model=value["selected_model"])))
    if (value["request_digest"] != _auto_request_digest(original)
            or value["routed_request_digest"] != routed):
        _refuse("fabric_auto_request_commitment_invalid", unknown=True)
    return value


def auto_route_identity(route):
    """Pure frozen turn identity from an already validated route."""
    value = {key: item for key, item in route.items()
             if key not in {"request_digest", "routed_request_digest", "output_contract"}}
    value["output_limit_mode"] = route["output_contract"]["mode"]
    return json.loads(_canonical_auto(value))


def validate_auto_observation(value, inspection, *, operation_id, request_id,
                              request_digest, routed_request_digest, max_tokens,
                              expected_route=None, require_success=False):
    """Validate an existing caller receipt without selection, admission or I/O.

    The caller retains commitments computed from the original translated
    request, beside the immutable transport observation, in its existing
    durable operation owner. Re-reading this evidence cannot send a request.
    """
    inspection = validate_auto_inspection(inspection)
    validate_native_operation_id(operation_id)
    validate_native_operation_id(request_id)
    fields = {"schema", "disposition", "effect_unknown", "turn_id", "request_id",
              "routing", "serving_model", "usage"}
    if (type(value) is not dict or set(value) != fields
            or value["schema"] != "mastermind.fabric_application_observation.v2"
            or value["turn_id"] != operation_id or value["request_id"] != request_id
            or type(value["disposition"]) is not str
            or value["disposition"] not in {"terminal", "effect_unknown"}
            or type(value["effect_unknown"]) is not bool
            or value["effect_unknown"] != (value["disposition"] == "effect_unknown")
            or type(max_tokens) is not int or not 1 <= max_tokens <= 32768
            or type(require_success) is not bool
            or (value["serving_model"] is not None and not _safe_id(value["serving_model"]))
            or type(value["usage"]) is not dict
            or set(value["usage"]) != {"input_tokens", "output_tokens"}
            or any(item is not None and (type(item) is not int or not 0 <= item <= MAX_NATIVE_TOKENS)
                   for item in value["usage"].values())):
        _refuse("fabric_auto_observation_invalid")
    route = _auto_route_metadata(value["routing"], inspection, max_tokens)
    if (route["request_digest"] != request_digest
            or route["routed_request_digest"] != routed_request_digest
            or expected_route is not None and auto_route_identity(route) != expected_route
            or require_success and (value["disposition"] != "terminal"
                or value["effect_unknown"] or value["serving_model"] != route["selected_model"])):
        _refuse("fabric_auto_observation_invalid")
    return json.loads(_canonical_auto(value))


class _StreamText:
    type = "text"

    def __init__(self, parts):
        self.parts = parts

    @property
    def text(self):
        return "".join(self.parts)

    def model_dump(self):
        return {"type": "text", "text": self.text}


class _Stream:
    def __init__(self, exchange):
        self.exchange = exchange
        self.parts, self.calls = [], {}
        self.model, self.finish, self.usage = None, None, None
        self.final = None
        self._events = self._event_data()

    @property
    def current_message_snapshot(self):
        # Tool inputs are deliberately unavailable until terminal JSON validation.
        return SimpleNamespace(content=[_StreamText(self.parts)] + [
            SimpleNamespace(type="tool_use", id=c["id"], name=c["name"], input=None)
            for c in self.calls.values()])

    def _event_data(self):
        pending, lines, count = b"", [], 0
        while True:
            chunk = self.exchange.read()
            if not chunk:
                _refuse("fabric_stream_incomplete", unknown=True)
            pending += chunk
            while b"\n" in pending:
                line, pending = pending.split(b"\n", 1)
                line = line.rstrip(b"\r")
                if len(line) > MAX_SSE_LINE_BYTES:
                    _refuse("fabric_stream_frame_too_large", unknown=True)
                if not line:
                    if lines:
                        count += 1
                        if count > MAX_SSE_EVENTS:
                            _refuse("fabric_stream_event_bound", unknown=True)
                        yield b"\n".join(lines)
                        lines = []
                elif line.startswith(b"data:"):
                    lines.append(line[5:].lstrip(b" "))
            if len(pending) > MAX_SSE_LINE_BYTES:
                _refuse("fabric_stream_frame_too_large", unknown=True)

    def _chunk(self, payload):
        if not isinstance(payload, dict) or payload.get("error"):
            _refuse("fabric_stream_invalid", unknown=True)
        model = payload.get("model")
        if model is not None:
            if model != self.exchange.client.model:
                _refuse("fabric_response_model_mismatch", unknown=True)
            self.model = model
        choices = payload.get("choices")
        if not isinstance(choices, list) or len(choices) > 1:
            _refuse("fabric_stream_invalid", unknown=True)
        if payload.get("usage") is not None:
            self.usage = payload["usage"]
        if not choices:
            return ""
        choice = choices[0]
        if (not isinstance(choice, dict) or type(choice.get("index")) is not int
                or choice["index"] != 0 or not isinstance(choice.get("delta"), dict)
                or self.model is None):
            _refuse("fabric_stream_invalid", unknown=True)
        delta = choice["delta"]
        if (delta.get("role", "assistant") != "assistant" or delta.get("refusal")
                or delta.get("function_call") or delta.get("audio")):
            _refuse("fabric_stream_invalid", unknown=True)
        text, tools = delta.get("content"), delta.get("tool_calls")
        if self.finish is not None and (text or tools or choice.get("finish_reason") is not None):
            _refuse("fabric_stream_after_finish", unknown=True)
        if text is not None and not isinstance(text, str):
            _refuse("fabric_stream_invalid", unknown=True)
        if text:
            self.parts.append(text)
        if tools is not None:
            if not isinstance(tools, list):
                _refuse("fabric_tool_response_invalid", unknown=True)
            for tool in tools:
                if (not isinstance(tool, dict) or type(tool.get("index")) is not int
                        or not 0 <= tool["index"] < MAX_TOOLS
                        or tool.get("type", "function") != "function"
                        or not isinstance(tool.get("function", {}), dict)):
                    _refuse("fabric_tool_response_invalid", unknown=True)
                entry = self.calls.setdefault(tool["index"], {"id": "", "name": "", "arguments": []})
                if "id" in tool:
                    if not _safe_id(tool["id"]) or (entry["id"] and entry["id"] != tool["id"]):
                        _refuse("fabric_tool_response_invalid", unknown=True)
                    entry["id"] = tool["id"]
                function = tool.get("function", {})
                if "name" in function:
                    if not isinstance(function["name"], str):
                        _refuse("fabric_tool_response_invalid", unknown=True)
                    entry["name"] += function["name"]
                if "arguments" in function:
                    if not isinstance(function["arguments"], str):
                        _refuse("fabric_tool_response_invalid", unknown=True)
                    entry["arguments"].append(function["arguments"])
        finish = choice.get("finish_reason")
        if finish is not None:
            if finish not in _FINISH:
                _refuse("fabric_finish_reason_invalid", unknown=True)
            self.finish = finish
        return text or ""

    @property
    def text_stream(self):
        if self.final is not None:
            return
        try:
            for data in self._events:
                if data == b"[DONE]":
                    if self.model is None or self.finish is None:
                        _refuse("fabric_stream_incomplete", unknown=True)
                    if sorted(self.calls) != list(range(len(self.calls))):
                        _refuse("fabric_tool_response_invalid", unknown=True)
                    calls = [{"id": c["id"], "type": "function", "function": {
                        "name": c["name"], "arguments": "".join(c["arguments"])}}
                        for _, c in sorted(self.calls.items())]
                    self.final = _message(self.model, "".join(self.parts), calls, self.finish, self.usage)
                    return
                text = self._chunk(_load_json(data))
                if text:
                    yield text
        except Exception as exc:
            raise self.exchange.client._failure(exc) from None

    def get_final_message(self):
        if self.final is None:
            for _ in self.text_stream:
                pass
        return self.final


@dataclass(frozen=True, repr=False)
class FabricPoolViewReader:
    """Startup-owned read capability; it cannot bind, infer, close or retry."""

    base_url: str
    proxy_token: str = field(repr=False)
    timeout_s: float = 2.0

    def __post_init__(self):
        try:
            url = urlsplit(self.base_url)
            valid = (url.scheme in {"http", "https"} and url.hostname == "127.0.0.1"
                and url.port is not None and 1 <= url.port <= 65535
                and url.netloc == f"127.0.0.1:{url.port}" and url.path == "/v1"
                and not url.query and not url.fragment)
        except (ValueError, TypeError, AttributeError):
            valid = False
        if not valid:
            _refuse("fabric_endpoint_invalid")
        if (type(self.proxy_token) is not str or not 32 <= len(self.proxy_token) <= 4096
                or not self.proxy_token.isascii() or any(not 33 <= ord(c) <= 126 for c in self.proxy_token)
                or self.proxy_token.startswith(("v1.", "app1.", "app2."))):
            _refuse("fabric_binding_invalid")
        if type(self.timeout_s) not in (int, float) or not 0 < self.timeout_s <= 5 or not math.isfinite(self.timeout_s):
            _refuse("fabric_timeout_invalid")

    def read(self):
        url = urlsplit(self.base_url)
        deadline = time.monotonic() + self.timeout_s
        connection = _NativeConnection("127.0.0.1", url.port, deadline=deadline, tls=url.scheme == "https")
        response = None
        try:
            connection.connect()
            connection.request("GET", "/application-pools/view", headers={
                "Authorization": "Bearer " + self.proxy_token, "Accept": "application/json"})
            connection.sock.settimeout(connection._remaining())
            response = connection.getresponse()
            if response.status != 200:
                raise FabricInferenceError("fabric_admin_view_denied" if response.status in (401, 403)
                    else "fabric_admin_view_unavailable", status_code=response.status)
            lengths = response.headers.get_all("Content-Length") or []
            if (len(lengths) != 1 or re.fullmatch(r"[0-9]{1,7}", lengths[0]) is None
                    or not 1 <= int(lengths[0]) <= 256 * 1024
                    or response.headers.get_all("Transfer-Encoding")
                    or response.headers.get_all("Content-Type") != ["application/json"]
                    or response.headers.get_all("Cache-Control") != ["no-store"]):
                _refuse("fabric_admin_view_invalid")
            body = response.read(int(lengths[0]) + 1)
            connection._remaining()
            if len(body) != int(lengths[0]):
                _refuse("fabric_admin_view_invalid")
            from engine.provider_capacity import validate_fabric_admin_pool_view
            return validate_fabric_admin_pool_view(_load_json(body, unknown=False))
        except FabricInferenceError as exc:
            # Metadata has no provider effect or turn to mark uncertain.
            raise FabricInferenceError(exc.code if exc.code in {
                "fabric_admin_view_denied", "fabric_admin_view_unavailable", "fabric_admin_view_invalid"
            } else "fabric_admin_view_invalid", status_code=exc.status_code) from None
        except Exception:
            raise FabricInferenceError("fabric_admin_view_unavailable") from None
        finally:
            if response is not None:
                response.close()
            connection.finish()


class FabricInferenceClient:
    """A turn-scoped client for a separately qualified server-owned binding."""

    def __init__(self, *, base_url: str, proxy_token: str, model: str, timeout_s=None,
                 protocol=LEGACY_PROTOCOL, operation_id=None, close_timeout_s=5,
                 prior_admission_possible=False, native_recipe_digest=None, auto_inspection=None):
        if protocol not in {LEGACY_PROTOCOL, NATIVE_PROTOCOL}:
            _refuse("fabric_protocol_invalid")
        native = protocol == NATIVE_PROTOCOL
        automatic = auto_inspection is not None
        inspection = validate_auto_inspection(auto_inspection) if automatic else None
        if automatic and (not native or model != inspection["requested_model"] or native_recipe_digest is not None):
            _refuse("fabric_auto_binding_invalid")
        if native_recipe_digest is not None and (not native or not isinstance(native_recipe_digest, str)
                or re.fullmatch(r"[0-9a-f]{64}", native_recipe_digest) is None):
            _refuse("fabric_recipe_invalid")
        if type(prior_admission_possible) is not bool or prior_admission_possible and not native:
            _refuse("fabric_binding_invalid")
        if native:
            validate_native_operation_id(operation_id)
        elif operation_id is not None:
            _refuse("fabric_binding_invalid")
        try:
            url = urlsplit(base_url)
            role_alias = (native and url.scheme == "http"
                          and url.hostname in {"127.0.0.2", "127.0.0.3"} and url.port == 50142)
            valid = (url.scheme in {"http", "https"} and (url.hostname == "127.0.0.1" or role_alias)
                     and url.port is not None and 1 <= url.port <= 65535
                     and url.netloc == f"{url.hostname}:{url.port}" and url.path == "/v1"
                     and not url.query and not url.fragment)
        except (ValueError, TypeError, AttributeError):
            valid = False
        if not valid:
            _refuse("fabric_endpoint_invalid")
        if (not isinstance(proxy_token, str) or not (32 if native else 24) <= len(proxy_token) <= 4096
                or not proxy_token.isascii() or any(ord(c) < 33 or ord(c) > 126 for c in proxy_token)):
            _refuse("fabric_binding_invalid")
        if native and proxy_token.startswith(("v1.", "app1.", "app2.")):
            _refuse("fabric_binding_invalid")
        if not automatic and not _safe_id(model):
            _refuse("fabric_model_invalid")
        if timeout_s is None:
            # B's admission5s + fresh-quota4s + provider60s and bounded
            # settlement/recovery can exceed the compatible client's old60s.
            timeout_s = 90 if native else 60
        if type(timeout_s) not in (int, float) or not math.isfinite(timeout_s) or not 0 < timeout_s <= 900:
            _refuse("fabric_timeout_invalid")
        if (type(close_timeout_s) not in (int, float) or not math.isfinite(close_timeout_s)
                or not 0 < close_timeout_s <= 10):
            _refuse("fabric_timeout_invalid")
        self.model, self._token = model, proxy_token
        self._url, self._timeout = url, float(timeout_s)
        self._native, self.operation_id = native, operation_id
        self._native_recipe_digest = native_recipe_digest
        self._auto_inspection = _canonical_auto(inspection) if automatic else None
        self._auto_turn_identity = self._auto_last_observation = None
        # Trusted restoration state comes from the existing caller/turn owner,
        # never from parsing an ID or probing during construction/inspection.
        self._prior_admission_possible = prior_admission_possible
        self._close_timeout = float(close_timeout_s)
        self._lock, self._active, self._uncertain = threading.Lock(), False, False
        self._closed = self._close_attempted = False
        self._admission_possible = prior_admission_possible
        self._close_result, self._failure_error = None, None
        self._attempted_ids = set()
        self.messages = self

    @property
    def auto_inspection(self):
        return json.loads(self._auto_inspection) if self._auto_inspection is not None else None

    @property
    def application_observation(self):
        return self._auto_last_observation

    def _auto_result(self, response, payload, request_id, original_body):
        """Validate one original routed result before exposing its answer or identity."""
        if (response.status != 200 and type(payload) is dict
                and type(payload.get("application")) is dict
                and payload["application"].get("schema") == NATIVE_SCHEMA):
            # Only receipt-only recovery, pre-admission refusal and unknown
            # turn state can omit fresh route evidence. A v1 fresh terminal
            # cannot settle AUTO without its original/routed commitments.
            original = _native_envelope(response, payload,
                operation_id=self.operation_id, request_id=request_id)
            if original.disposition == "terminal" or original.observed_usage is not None:
                raise FabricInferenceError("fabric_auto_route_missing", effect_unknown=True,
                    disposition="effect_unknown", status_code=response.status,
                    request_id=request_id, observed_usage=original.observed_usage,
                    serving_model=original.serving_model)
            raise original
        required = {"schema", "disposition", "turn_id", "request_id", "dispatch_permitted",
                    "effect_unknown", "routing", "usage", "serving_model"}
        if (type(payload) is not dict or type(payload.get("application")) is not dict
                or set(payload["application"]) != required):
            _refuse("fabric_auto_envelope_invalid", unknown=True)
        state = payload["application"]
        if state["schema"] != AUTO_SCHEMA:
            _refuse("fabric_auto_envelope_invalid", unknown=True)
        base = {key: value for key, value in state.items() if key != "routing"}
        base["schema"] = NATIVE_SCHEMA
        outcome = None
        if response.status != 200:
            if set(payload) - {"application", "error"}:
                _refuse("fabric_auto_envelope_invalid", unknown=True)
            error_payload = {"application": base}
            if "error" in payload:
                error_payload["error"] = payload["error"]
            outcome = _native_envelope(response, error_payload,
                operation_id=self.operation_id, request_id=request_id)
        else:
            if (state["disposition"] != "terminal" or state["dispatch_permitted"] is not False
                    or state["effect_unknown"] is not False or state["turn_id"] != self.operation_id
                    or state["request_id"] != request_id or "error" in payload
                    or type(state["usage"]) is not dict
                    or set(state["usage"]) != {"input_tokens", "output_tokens"}):
                _refuse("fabric_auto_envelope_invalid", unknown=True)
            _native_header(response, "X-MM-Application-Disposition", "terminal")
            _native_header(response, "X-MM-Application-Turn-ID", self.operation_id)
            _native_header(response, "X-MM-Application-Request-ID", request_id)
        usage = _usage({"prompt_tokens": state["usage"]["input_tokens"],
                        "completion_tokens": state["usage"]["output_tokens"]})
        served = state["serving_model"] if _safe_id(state["serving_model"]) else None
        original = _load_json(original_body, unknown=False)
        try:
            routing = _auto_route(state["routing"], json.loads(self._auto_inspection), original)
            turn = {key: value for key, value in routing.items()
                    if key not in {"request_digest", "routed_request_digest", "output_contract"}}
            turn["output_limit_mode"] = routing["output_contract"]["mode"]
            commitment = _canonical_auto(turn)
            with self._lock:
                if self._auto_turn_identity is not None and self._auto_turn_identity != commitment:
                    _refuse("fabric_auto_turn_changed", unknown=True)
                self._auto_turn_identity = commitment
        except (FabricInferenceError, TypeError, ValueError, KeyError, OverflowError, RecursionError) as exc:
            # Counts survive every malformed JSON route type after the envelope
            # is correlated. No positive pool attribution or answer is attached.
            error = exc if isinstance(exc, FabricInferenceError) else FabricInferenceError(
                "fabric_auto_route_invalid", effect_unknown=True)
            error.effect_unknown = True
            error.observed_usage, error.serving_model = usage, served
            error.request_id = request_id
            raise error from None
        observation = ApplicationObservation(_canonical_auto({
            "schema": "mastermind.fabric_application_observation.v2",
            "disposition": state["disposition"], "effect_unknown": state["effect_unknown"],
            "turn_id": self.operation_id, "request_id": request_id, "routing": routing,
            "serving_model": served,
            "usage": {"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens}}))
        self._auto_last_observation = observation
        if outcome is not None:
            outcome.application_observation = observation
            raise outcome
        try:
            if served != routing["selected_model"] or payload.get("model") != served:
                _refuse("fabric_auto_served_model_mismatch", unknown=True)
            message = _completion(payload, served)
            if message.usage != usage:
                _refuse("fabric_auto_usage_mismatch", unknown=True)
            return replace(message, application_observation=observation)
        except Exception:
            raise FabricInferenceError("fabric_native_terminal_unusable",
                disposition="terminal", request_id=request_id, observed_usage=usage,
                serving_model=served, application_observation=observation) from None

    def _failure(self, exc):
        error = exc if isinstance(exc, FabricInferenceError) else FabricInferenceError(
            "fabric_response_incomplete", effect_unknown=True)
        with self._lock:
            if self._native and self._failure_error is None:
                self._failure_error = error
            if error.effect_unknown:
                self._uncertain = True
        return error

    def _exchange(self, path, body, headers, *, timeout, admission=False):
        deadline = time.monotonic() + timeout
        if self._native:
            connection = _NativeConnection(self._url.hostname, self._url.port,
                deadline=deadline, tls=self._url.scheme == "https")
        else:
            cls = http.client.HTTPSConnection if self._url.scheme == "https" else http.client.HTTPConnection
            connection = cls("127.0.0.1", self._url.port, timeout=timeout)
        sent, response = False, None
        try:
            connection.connect()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _refuse("fabric_timeout")
            connection.sock.settimeout(remaining)
            if admission:
                with self._lock:
                    # A close that won while connect() was in progress prevents
                    # these first request bytes; it cannot cancel a prior send.
                    if self._closed:
                        _refuse("fabric_operation_closed")
                    self._admission_possible = True
            sent = True  # request() may write a partial frame before raising
            connection.request("POST", path, body=body, headers=headers)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _refuse("fabric_timeout", unknown=True)
            connection.sock.settimeout(remaining)
            response = connection.getresponse()
            return _Exchange(self, connection, response, deadline)
        except Exception as exc:
            if response is not None:
                response.close()
            finish = getattr(connection, "finish", connection.close)
            finish()
            if isinstance(exc, FabricInferenceError):
                raise
            raise FabricInferenceError(
                "fabric_request_uncertain" if sent else "fabric_connection_unavailable",
                effect_unknown=sent or self._prior_admission_possible) from None

    def _response_type(self, exchange, expected):
        response = exchange.response
        if self._native:
            _response_framing(response)
            if len(response.headers.get_all("Content-Type") or []) != 1:
                _refuse("fabric_content_type_invalid", unknown=True)
            if len(response.headers.get_all("Content-Encoding") or []) > 1:
                _refuse("fabric_content_encoding_invalid", unknown=True)
        if response.getheader("Content-Type", "").split(";", 1)[0].strip().lower() != expected:
            _refuse("fabric_content_type_invalid", unknown=True)
        if response.getheader("Content-Encoding", "identity").strip().lower() not in {"", "identity"}:
            _refuse("fabric_content_encoding_invalid", unknown=True)

    def _open(self, kwargs, *, streaming):
        exchange, owns_active = None, False
        try:
            if self._native and streaming:
                _refuse("fabric_native_stream_unsupported")
            request_id, body = _request(kwargs, self.model, streaming,
                exact_scoped=self._auto_inspection is not None
                    and json.loads(self._auto_inspection)["schema"] == EXACT_INSPECTION_SCHEMA)
            if self._native:
                validate_native_operation_id(request_id)
                # Translation can expand user/tool history into more wire rows.
                if len(_load_json(body, unknown=False)["messages"]) > 512:
                    _refuse("fabric_request_invalid")
                if self._auto_inspection is not None:
                    _auto_request_digest(_load_json(body, unknown=False))
            with self._lock:
                if self._closed:
                    _refuse("fabric_operation_closed")
                if self._failure_error is not None:
                    raise self._failure_error
                if self._uncertain:
                    _refuse("fabric_effect_unknown", unknown=True)
                if self._active or request_id in self._attempted_ids or len(self._attempted_ids) >= MAX_STEPS:
                    _refuse("fabric_step_unavailable")
                self._active = owns_active = True
                self._attempted_ids.add(request_id)
            headers = {"Authorization": "Bearer " + self._token,
                "Idempotency-Key": request_id, "Content-Type": "application/json",
                "Accept-Encoding": "identity",
                "Accept": "text/event-stream" if streaming else "application/json"}
            if self._native:
                headers["X-MM-Application-Turn-ID"] = self.operation_id
                if self._native_recipe_digest is not None:
                    headers["X-MM-Application-Recipe-Digest"] = self._native_recipe_digest
                if self._auto_inspection is not None:
                    headers["X-MM-Application-Route-Scope-Digest"] = json.loads(self._auto_inspection)["route_scope_digest"]
            exchange = self._exchange("/v1/chat/completions", body, headers,
                timeout=self._timeout, admission=self._native)
            response = exchange.response
            if not self._native and response.status != 200:
                raise FabricInferenceError("fabric_gateway_rejected", status_code=response.status,
                                           effect_unknown=not 400 <= response.status < 500)
            self._response_type(exchange, "text/event-stream" if streaming else "application/json")
            if self._native:
                if response.status != 200:
                    if self._auto_inspection is not None:
                        self._auto_result(response, _load_json(exchange.body()), request_id, body)
                    raise _native_envelope(response, _load_json(exchange.body()),
                        operation_id=self.operation_id, request_id=request_id)
                _native_header(response, "X-MM-Application-Disposition", "terminal")
                _native_header(response, "X-MM-Application-Turn-ID", self.operation_id)
                _native_header(response, "X-MM-Application-Request-ID", request_id)
            exchange.request_id = request_id
            exchange.original_body = body
            return exchange
        except Exception as exc:
            if exchange is not None:
                exchange.close()
            if owns_active:
                with self._lock:
                    self._active = False
            if not isinstance(exc, FabricInferenceError):
                exc = FabricInferenceError("fabric_response_incomplete" if exchange is not None
                    else "fabric_request_invalid", effect_unknown=exchange is not None)
            raise self._failure(exc) from None

    def create(self, **kwargs):
        exchange = self._open(kwargs, streaming=False)
        payload = None
        try:
            payload = _load_json(exchange.body())
            if self._auto_inspection is not None:
                return self._auto_result(exchange.response, payload, exchange.request_id, exchange.original_body)
            return _completion(payload, self.model)
        except Exception as exc:
            if self._native and self._auto_inspection is None and isinstance(payload, dict) and "application" not in payload:
                # A complete correlated original terminal can be unusable as an
                # answer while still carrying observed model/token evidence.
                exc = FabricInferenceError("fabric_native_terminal_unusable",
                    disposition="terminal", request_id=exchange.request_id,
                    observed_usage=_usage(payload.get("usage")),
                    serving_model=payload.get("model") if _safe_id(payload.get("model")) else None)
            raise self._failure(exc) from None
        finally:
            exchange.close()
            with self._lock:
                self._active = False

    def close(self):
        """Invalidate locally, then attempt the original native close once.

        Close never cancels an inference thread and never raises over its late
        observed usage. A lost/absent/unknown close is not a release receipt.
        """
        with self._lock:
            self._closed = True
            if self._close_attempted:
                return dict(self._close_result or {"disposition": "pending", "closed": False,
                    "effect_unknown": True, "attempted": True})
            self._close_attempted = True
            if not self._native or not self._admission_possible:
                self._close_result = {"disposition": "local_only", "closed": False,
                    "effect_unknown": False, "attempted": False}
                return dict(self._close_result)
        exchange = None
        result = {"disposition": "effect_unknown", "closed": False,
                  "effect_unknown": True, "attempted": True}
        try:
            exchange = self._exchange("/application-turns/close",
                _json_bytes({"turn_id": self.operation_id}),
                {"Authorization": "Bearer " + self._token, "Content-Type": "application/json",
                 "Accept": "application/json", "Accept-Encoding": "identity"},
                timeout=self._close_timeout)
            self._response_type(exchange, "application/json")
            outcome = _native_envelope(exchange.response, _load_json(exchange.body()),
                operation_id=self.operation_id, request_id=None, closing=True)
            result = {"disposition": outcome.disposition, "closed": outcome.disposition == "closed",
                      "effect_unknown": outcome.effect_unknown, "attempted": True}
        except Exception:
            pass  # Only bounded metadata survives; never retry this close.
        finally:
            if exchange is not None:
                exchange.close()
            with self._lock:
                self._close_result = result
        return dict(result)

    @contextmanager
    def stream(self, **kwargs):
        exchange = self._open(kwargs, streaming=True)
        stream = _Stream(exchange)
        try:
            yield stream
        finally:
            if stream.final is None:
                self._failure(FabricInferenceError("fabric_stream_abandoned", effect_unknown=True))
            exchange.close()
            with self._lock:
                self._active = False
