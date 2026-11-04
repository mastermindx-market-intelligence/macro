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
import json
import math
import re
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from types import SimpleNamespace
from urllib.parse import urlsplit

MAX_REQUEST_BYTES = 1024 * 1024
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_SSE_LINE_BYTES = 1024 * 1024
MAX_SSE_EVENTS = 32768
MAX_STEPS = 256
MAX_TOOLS = 128
_ID = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z")
_CALL_KEYS = frozenset({"model", "messages", "system", "tools", "tool_choice",
                        "max_tokens", "temperature", "stop_sequences", "request_id"})
_FINISH = {"stop": "end_turn", "length": "max_tokens", "tool_calls": "tool_use"}


class FabricInferenceError(RuntimeError):
    """Bounded failure metadata; never transport text, tokens, URLs or prompts."""

    def __init__(self, code: str, *, effect_unknown: bool = False, status_code=None):
        super().__init__(code)
        self.code = code
        self.effect_unknown = effect_unknown
        self.status_code = status_code


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


def _refuse(code="fabric_request_invalid", *, unknown=False):
    raise FabricInferenceError(code, effect_unknown=unknown)


def _safe_id(value):
    return isinstance(value, str) and _ID.fullmatch(value) is not None


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
        return json.loads(data, object_pairs_hook=pairs, parse_constant=nonfinite)
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


def _request(kwargs, model, streaming):
    if set(kwargs) - _CALL_KEYS or kwargs.get("model") != model:
        _refuse()
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
        return token if type(token) is int and token >= 0 else None
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
            self.response.close()
            self.connection.close()


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


class FabricInferenceClient:
    """A turn-scoped client for a separately qualified server-owned binding."""

    def __init__(self, *, base_url: str, proxy_token: str, model: str, timeout_s=60):
        try:
            url = urlsplit(base_url)
            valid = (url.scheme in {"http", "https"} and url.hostname == "127.0.0.1"
                     and url.port is not None and 1 <= url.port <= 65535
                     and url.netloc == f"127.0.0.1:{url.port}" and url.path == "/v1"
                     and not url.query and not url.fragment)
        except (ValueError, TypeError, AttributeError):
            valid = False
        if not valid:
            _refuse("fabric_endpoint_invalid")
        if (not isinstance(proxy_token, str) or not 24 <= len(proxy_token) <= 4096
                or not proxy_token.isascii() or any(ord(c) < 33 or ord(c) > 126 for c in proxy_token)):
            _refuse("fabric_binding_invalid")
        if not _safe_id(model):
            _refuse("fabric_model_invalid")
        if type(timeout_s) not in (int, float) or not math.isfinite(timeout_s) or not 0 < timeout_s <= 900:
            _refuse("fabric_timeout_invalid")
        self.model, self._token = model, proxy_token
        self._url, self._timeout = url, float(timeout_s)
        self._lock, self._active, self._uncertain = threading.Lock(), False, False
        self._attempted_ids = set()
        self.messages = self

    def _failure(self, exc):
        error = exc if isinstance(exc, FabricInferenceError) else FabricInferenceError(
            "fabric_response_incomplete", effect_unknown=True)
        if error.effect_unknown:
            with self._lock:
                self._uncertain = True
        return error

    def _open(self, kwargs, *, streaming):
        try:
            request_id, body = _request(kwargs, self.model, streaming)
        except FabricInferenceError:
            raise
        except Exception:
            raise FabricInferenceError("fabric_request_invalid") from None
        with self._lock:
            if self._uncertain:
                _refuse("fabric_effect_unknown", unknown=True)
            if self._active or request_id in self._attempted_ids or len(self._attempted_ids) >= MAX_STEPS:
                _refuse("fabric_step_unavailable")
            self._active = True
            self._attempted_ids.add(request_id)
        cls = http.client.HTTPSConnection if self._url.scheme == "https" else http.client.HTTPConnection
        connection = cls("127.0.0.1", self._url.port, timeout=self._timeout)
        sent, response = False, None
        try:
            deadline = time.monotonic() + self._timeout
            connection.connect()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _refuse("fabric_timeout")
            connection.sock.settimeout(remaining)
            sent = True  # request() may write a partial frame before raising
            connection.request("POST", "/v1/chat/completions", body=body, headers={
                "Authorization": "Bearer " + self._token,
                "Idempotency-Key": request_id,
                "Content-Type": "application/json",
                "Accept-Encoding": "identity",
                "Accept": "text/event-stream" if streaming else "application/json",
            })
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _refuse("fabric_timeout", unknown=True)
            connection.sock.settimeout(remaining)
            response = connection.getresponse()
            if response.status != 200:
                raise FabricInferenceError("fabric_gateway_rejected", status_code=response.status,
                                           effect_unknown=not 400 <= response.status < 500)
            expected = "text/event-stream" if streaming else "application/json"
            if response.getheader("Content-Type", "").split(";", 1)[0].strip().lower() != expected:
                _refuse("fabric_content_type_invalid", unknown=True)
            if response.getheader("Content-Encoding", "identity").strip().lower() not in {"", "identity"}:
                _refuse("fabric_content_encoding_invalid", unknown=True)
            return _Exchange(self, connection, response, deadline)
        except Exception as exc:
            if response is not None:
                response.close()
            connection.close()
            with self._lock:
                self._active = False
            if isinstance(exc, FabricInferenceError):
                raise self._failure(exc) from None
            raise self._failure(FabricInferenceError(
                "fabric_request_uncertain" if sent else "fabric_connection_unavailable",
                effect_unknown=sent)) from None

    def create(self, **kwargs):
        exchange = self._open(kwargs, streaming=False)
        try:
            parts = []
            while part := exchange.read():
                parts.append(part)
            return _completion(_load_json(b"".join(parts)), self.model)
        except Exception as exc:
            raise self._failure(exc) from None
        finally:
            exchange.close()
            with self._lock:
                self._active = False

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
