#!/usr/bin/env python3
"""Bounded loopback admission for the existing pinned Ollama capacity source.

Busy requests are refused before body reads. The caller owns fallback; this
guard has no queue, scheduler, retries, model selection or worker lifecycle.
Inference responses are released only after one explicit unload and a bounded
residency read. Historical host canaries do not attest to this source revision.
"""
from __future__ import annotations

import argparse
import http.client
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

DEFAULT_CGROUP = Path("/sys/fs/cgroup/mastermind.slice/mastermind-ci.slice")
DEFAULT_MODEL = "qwen3.5:9b"
DEFAULT_MAX_BODY = 8 * 1024 * 1024
DEFAULT_MAX_RESPONSE = 8 * 1024 * 1024
DEFAULT_REQUEST_TIMEOUT = 5.0
# The earnings consumer has a 120-second response timeout. Leave room for
# admission, its bounded body read, one 10-second stop and residency checks.
DEFAULT_UPSTREAM_TIMEOUT = 90.0
DEFAULT_MIN_MEM_AVAILABLE = 16 * 1024**3
DEFAULT_GPU_OTHER_MIB = 512
MAX_CONNECTIONS = 4
_LOCK = threading.Lock()
_INFERENCE_PATHS = frozenset({"/v1/chat/completions"})
_HOP_HEADERS = frozenset({
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailer", "transfer-encoding", "upgrade", "content-length",
})


def _read_int(path: Path) -> int | None:
    try:
        value = int(path.read_text(encoding="utf-8").strip())
        return value if value >= 0 else None
    except (OSError, ValueError):
        return None


def _mem_available() -> int | None:
    try:
        rows = Path("/proc/meminfo").read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for row in rows:
        if row.startswith("MemAvailable:"):
            try:
                value = int(row.split()[1]) * 1024
                return value if value >= 0 else None
            except (IndexError, ValueError):
                return None
    return None


def _other_gpu_mib() -> tuple[int | None, str | None]:
    """Conservatively count ALL compute memory; names do not establish ownership.

    Admission requires no resident Ollama model, so even an Ollama/llama-server
    process cannot be exempted by name. Malformed telemetry is never GPU idle.
    """
    try:
        cp = subprocess.run(
            ["/usr/bin/nvidia-smi", "--query-compute-apps=process_name,used_memory",
             "--format=csv,noheader,nounits"],
            check=False, text=True, capture_output=True, timeout=3,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"gpu_telemetry_unavailable:{type(exc).__name__}"
    if cp.returncode != 0:
        return None, "gpu_telemetry_unavailable"
    total = 0
    for raw in cp.stdout.splitlines():
        if not raw.strip():
            continue
        name, sep, mem = raw.rpartition(",")
        if not sep or not name.strip() or not mem.strip().isdecimal() or len(mem.strip()) > 20:
            return None, "gpu_telemetry_invalid"
        total += int(mem.strip())
    return total, None


def admission(*, cgroup: Path = DEFAULT_CGROUP,
              min_mem_available: int = DEFAULT_MIN_MEM_AVAILABLE,
              max_other_gpu_mib: int = DEFAULT_GPU_OTHER_MIB) -> dict:
    reasons: list[str] = []
    mem = _mem_available()
    if mem is None:
        reasons.append("host_memory_unavailable")
    elif mem < min_mem_available:
        reasons.append("host_memory_low")
    current = _read_int(cgroup / "memory.current")
    high = _read_int(cgroup / "memory.high")
    maximum = _read_int(cgroup / "memory.max")
    if current is None or high is None or maximum is None:
        reasons.append("ci_cgroup_unavailable")
    elif high <= 0 or maximum < high:
        reasons.append("ci_cgroup_invalid")
    elif current >= high:
        reasons.append("ci_memory_high")
    gpu, note = _other_gpu_mib()
    if note or gpu is None:
        reasons.append(note or "gpu_telemetry_unavailable")
    elif gpu > max_other_gpu_mib:
        reasons.append("gpu_busy_other_workload")
    return {
        "ok": not reasons, "reasons": reasons,
        "host_mem_available_bytes": mem, "ci_memory_current_bytes": current,
        "ci_memory_high_bytes": high, "ci_memory_max_bytes": maximum,
        "other_gpu_compute_mib": gpu,
    }


def _unload(model: str, ollama_bin: str, *, upstream_host: str = "127.0.0.1",
            upstream_port: int = 11434) -> bool:
    if (model != DEFAULT_MODEL or upstream_host != "127.0.0.1"
            or type(upstream_port) is not int or not 1 <= upstream_port <= 65535):
        return False
    environment = os.environ.copy()
    environment["OLLAMA_HOST"] = f"http://{upstream_host}:{upstream_port}"
    try:
        result = subprocess.run(
            [ollama_bin, "stop", model], check=False,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10,
            env=environment,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _read_response(response, connection, limit: int, deadline: float) -> bytes:
    declared = response.getheader("Content-Length")
    if declared is not None and (not declared.isdecimal() or len(declared) > 20 or int(declared) > limit):
        raise ValueError("upstream_response_size")
    chunks, size = [], 0
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("upstream_response_timeout")
        if connection.sock is not None:
            connection.sock.settimeout(remaining)
        chunk = response.read1(min(65536, limit + 1 - size))
        if not chunk:
            if declared is not None and size != int(declared):
                raise ValueError("upstream_response_incomplete")
            return b"".join(chunks)
        size += len(chunk)
        if size > limit:
            raise ValueError("upstream_response_size")
        chunks.append(chunk)


def _interrupt_socket(sock) -> None:
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass


def _upstream(server, method: str, path: str, body: bytes | None = None,
              *, limit: int | None = None, timeout: float | None = None):
    budget = server.upstream_timeout if timeout is None else timeout
    deadline = time.monotonic() + budget
    connection = http.client.HTTPConnection(
        server.upstream_host, server.upstream_port, timeout=budget,
    )
    timer = None
    try:
        connection.connect()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("upstream_connect_timeout")
        # Interrupt the actual socket even if HTTPResponse subsequently owns
        # it. Socket inactivity timeouts alone do not bound dripping headers.
        timer = threading.Timer(remaining, _interrupt_socket, args=(connection.sock,))
        timer.daemon = True
        timer.start()
        headers = {"Connection": "close", "Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        data = _read_response(response, connection,
                              server.max_response if limit is None else limit, deadline)
        return response.status, response.getheaders(), data
    finally:
        if timer is not None:
            timer.cancel()
        connection.close()


def _resident_models(server) -> tuple[list[str] | None, str | None]:
    try:
        status, _, data = _upstream(
            server, "GET", "/api/ps", limit=64 * 1024,
            timeout=min(3.0, server.upstream_timeout),
        )
        payload = json.loads(data)
        if status != 200 or not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
            raise ValueError("invalid_residency")
        names = []
        for entry in payload["models"]:
            name = entry.get("name", entry.get("model")) if isinstance(entry, dict) else None
            if not isinstance(name, str) or not name.strip():
                raise ValueError("invalid_residency")
            names.append(name)
        return names, None
    except (OSError, ValueError, RecursionError, http.client.HTTPException):
        return None, "ollama_residency_unavailable"


def _admission_state(server) -> dict:
    state = admission()
    if state["ok"]:
        models, note = _resident_models(server)
        state["resident_models"] = models
        if note or models:
            state["reasons"].append(note or "ollama_models_resident")
            state["ok"] = False
    return state


class RequestRejected(Exception):
    def __init__(self, status: int, reason: str):
        self.status, self.reason = status, reason


class Proxy(BaseHTTPRequestHandler):
    server_version = "mastermind-inference-guard/2"

    def setup(self) -> None:
        self.request.settimeout(self.server.request_timeout)
        super().setup()
        self._header_deadline = threading.Timer(
            self.server.request_timeout, _interrupt_socket, args=(self.connection,),
        )
        self._header_deadline.daemon = True
        self._header_deadline.start()

    def finish(self) -> None:
        self._header_deadline.cancel()
        super().finish()

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} {fmt % args}", flush=True)

    def _json(self, status: int, payload: dict, headers: dict | None = None) -> None:
        self._send(status, [("Content-Type", "application/json"), *(headers or {}).items()],
                   json.dumps(payload, sort_keys=True).encode())

    def _send(self, status: int, headers, data: bytes) -> None:
        self.close_connection = True
        self.send_response(status)
        for key, value in headers:
            if key.lower() not in _HOP_HEADERS:
                self.send_header(key, value)
        self.send_header("Connection", "close")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _length(self) -> int:
        lengths = self.headers.get_all("Content-Length", [])
        if self.headers.get("Transfer-Encoding") is not None or len(lengths) > 1:
            raise RequestRejected(400, "ambiguous_request_length")
        if not lengths:
            if self.command == "POST":
                raise RequestRejected(411, "content_length_required")
            return 0
        raw = lengths[0].strip()
        if not raw.isdecimal():
            raise RequestRejected(400, "invalid_request_length")
        if len(raw) > 20:
            raise RequestRejected(413, "request_too_large")
        length = int(raw)
        if length > self.server.max_body:
            raise RequestRejected(413, "request_too_large")
        if self.command == "GET" and length:
            raise RequestRejected(400, "get_body_not_allowed")
        return length

    def _body(self, length: int) -> bytes:
        deadline = time.monotonic() + self.server.request_timeout
        chunks, size = [], 0
        while size < length:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RequestRejected(408, "request_body_timeout")
            self.connection.settimeout(remaining)
            try:
                chunk = self.rfile.read1(min(65536, length - size))
            except (TimeoutError, OSError):
                raise RequestRejected(408, "request_body_timeout") from None
            if not chunk:
                raise RequestRejected(400, "incomplete_request_body")
            size += len(chunk)
            chunks.append(chunk)
        return b"".join(chunks)

    def do_GET(self) -> None:
        self._header_deadline.cancel()
        if self.path not in {"/healthz", "/v1/models"}:
            self._json(404, {"error": "endpoint_not_admitted"})
            return
        self._proxy()

    def do_POST(self) -> None:
        self._header_deadline.cancel()
        if self.path not in _INFERENCE_PATHS:
            self._json(404, {"error": "endpoint_not_admitted"})
            return
        self._proxy()

    def _proxy(self) -> None:
        if not _LOCK.acquire(blocking=False):
            self._json(503, {"ok": False, "error": "local_inference_busy"})
            return
        try:
            try:
                length = self._length()
                state = _admission_state(self.server)
                if self.path == "/healthz":
                    self._json(200 if state["ok"] else 503, state)
                    return
                if not state["ok"]:
                    self._json(503, {"error": "local_inference_not_admitted", **state})
                    return
                body = None
                if self.command == "POST":
                    body = self._body(length)
                    try:
                        payload = json.loads(body)
                    except (ValueError, UnicodeError, RecursionError):
                        raise RequestRejected(400, "invalid_json") from None
                    if not isinstance(payload, dict) or payload.get("model") != self.server.model:
                        raise RequestRejected(400, "model_not_admitted")
                    if payload.get("stream", False) is not False:
                        raise RequestRejected(400, "streaming_not_admitted")
            except RequestRejected as exc:
                self._json(exc.status, {"error": exc.reason})
                return

            result, error = None, None
            try:
                result = _upstream(self.server, self.command, self.path, body)
            except (OSError, ValueError, http.client.HTTPException) as exc:
                error = type(exc).__name__
            finally:
                if self.command == "POST":
                    stopped = _unload(
                        self.server.model, self.server.ollama_bin,
                        upstream_host=self.server.upstream_host,
                        upstream_port=self.server.upstream_port,
                    )
                    models, note = _resident_models(self.server)
                    if not stopped or note or models:
                        error = "ollama_cleanup_unverified"
            if error:
                self._json(502, {"error": "ollama_upstream_failure", "detail": error})
                return
            self._send(*result)
        finally:
            _LOCK.release()


class GuardServer(ThreadingHTTPServer):
    """Bound connection handlers as well as the single inference operation."""
    request_queue_size = MAX_CONNECTIONS

    def __init__(self, *args, **kwargs):
        self._connections = threading.BoundedSemaphore(MAX_CONNECTIONS)
        super().__init__(*args, **kwargs)

    def process_request(self, request, client_address):
        if not self._connections.acquire(blocking=False):
            data = b'{"ok":false,"error":"local_inference_busy"}'
            try:
                request.settimeout(0.1)
                request.sendall(
                    b"HTTP/1.1 503 Service Unavailable\r\nConnection: close\r\n"
                    b"Content-Type: application/json\r\nContent-Length: "
                    + str(len(data)).encode() + b"\r\n\r\n" + data
                )
            except OSError:
                pass
            finally:
                self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._connections.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._connections.release()


def _loopback_address(value: str) -> tuple[str, int]:
    try:
        address = urlsplit("//" + value)
        port = address.port
        if (address.hostname != "127.0.0.1" or port is None or not 1 <= port <= 65535
                or address.username is not None or address.password is not None
                or address.path or address.query or address.fragment):
            raise ValueError("expected 127.0.0.1:<port>")
        return "127.0.0.1", port
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected 127.0.0.1:<port>") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen", type=_loopback_address, default="127.0.0.1:11435")
    parser.add_argument("--upstream", type=_loopback_address, default="127.0.0.1:11434")
    parser.add_argument("--model", choices=[DEFAULT_MODEL], default=DEFAULT_MODEL)
    parser.add_argument("--ollama-bin", default="/usr/local/bin/ollama")
    parser.add_argument("--max-body", type=int, default=DEFAULT_MAX_BODY)
    parser.add_argument("--max-response", type=int, default=DEFAULT_MAX_RESPONSE)
    parser.add_argument("--request-timeout", type=float, default=DEFAULT_REQUEST_TIMEOUT)
    parser.add_argument("--upstream-timeout", type=float, default=DEFAULT_UPSTREAM_TIMEOUT)
    args = parser.parse_args()
    if args.listen == args.upstream:
        parser.error("listen and upstream must be distinct loopback endpoints")
    if not (0 < args.max_body <= DEFAULT_MAX_BODY and 0 < args.max_response <= DEFAULT_MAX_RESPONSE):
        parser.error("body/response bounds must be positive and at most 8 MiB")
    for value, maximum in ((args.request_timeout, DEFAULT_REQUEST_TIMEOUT),
                           (args.upstream_timeout, DEFAULT_UPSTREAM_TIMEOUT)):
        if not math.isfinite(value) or not 0 < value <= maximum:
            parser.error("timeouts must be positive, finite and within the default bound")
    if not Path(args.ollama_bin).is_absolute():
        parser.error("ollama-bin must be an absolute executable path")
    server = GuardServer(args.listen, Proxy)
    server.upstream_host, server.upstream_port = args.upstream
    server.model, server.ollama_bin = args.model, args.ollama_bin
    server.max_body, server.max_response = args.max_body, args.max_response
    server.request_timeout, server.upstream_timeout = args.request_timeout, args.upstream_timeout
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
