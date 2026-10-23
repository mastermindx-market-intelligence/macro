#!/usr/bin/env python3
"""Loopback-only admission proxy for the canonical Ollama capacity source.

This is deliberately NOT a scheduler, queue, retry owner, provider router, or
worker lifecycle plane. It decides whether this physical host can safely admit
one local inference request now. On refusal it returns HTTP 503 immediately so
the caller-owned provider waterfall can use its existing next rung.

The proxy serializes requests, bounds request bytes, checks host/CI/GPU pressure,
forwards to the loopback Ollama server, and explicitly unloads the configured
model after every inference request. Unload is required because Ollama's
OpenAI-compatible endpoint may retain ~6.5 GiB VRAM for minutes even when the
service has OLLAMA_KEEP_ALIVE=0.
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
from pathlib import Path
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

DEFAULT_CGROUP = Path("/sys/fs/cgroup/mastermind.slice/mastermind-ci.slice")
DEFAULT_MODEL = "qwen3.5:9b"
DEFAULT_MAX_BODY = 8 * 1024 * 1024
DEFAULT_MIN_MEM_AVAILABLE = 16 * 1024**3
DEFAULT_GPU_OTHER_MIB = 512
_LOCK = threading.Lock()


def _read_int(path: Path) -> int | None:
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not raw or raw == "max":
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _mem_available() -> int | None:
    try:
        rows = Path("/proc/meminfo").read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for row in rows:
        if row.startswith("MemAvailable:"):
            try:
                return int(row.split()[1]) * 1024
            except (IndexError, ValueError):
                return None
    return None


def _other_gpu_mib(model_process_hint: str = "ollama") -> tuple[int | None, str | None]:
    """Return non-Ollama GPU compute memory, or None when telemetry is absent."""
    try:
        cp = subprocess.run(
            [
                "/usr/bin/nvidia-smi",
                "--query-compute-apps=process_name,used_memory",
                "--format=csv,noheader,nounits",
            ],
            check=False,
            text=True,
            capture_output=True,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"gpu_telemetry_unavailable:{type(exc).__name__}"
    if cp.returncode != 0:
        return None, "gpu_telemetry_unavailable"
    total = 0
    for raw in cp.stdout.splitlines():
        name, sep, mem = raw.rpartition(",")
        if not sep:
            continue
        name = name.strip().lower()
        if model_process_hint in name or "llama-server" in name:
            continue
        try:
            total += int(mem.strip())
        except ValueError:
            continue
    return total, None


def admission(
    *,
    cgroup: Path = DEFAULT_CGROUP,
    min_mem_available: int = DEFAULT_MIN_MEM_AVAILABLE,
    max_other_gpu_mib: int = DEFAULT_GPU_OTHER_MIB,
) -> dict:
    reasons: list[str] = []
    mem = _mem_available()
    if mem is None:
        reasons.append("host_memory_unavailable")
    elif mem < min_mem_available:
        reasons.append("host_memory_low")

    ci_current = _read_int(cgroup / "memory.current")
    ci_high = _read_int(cgroup / "memory.high")
    ci_max = _read_int(cgroup / "memory.max")
    if ci_current is None or ci_high is None or ci_max is None:
        reasons.append("ci_cgroup_unavailable")
    elif ci_current >= ci_high:
        reasons.append("ci_memory_high")

    other_gpu, gpu_note = _other_gpu_mib()
    if gpu_note:
        # Fail closed: this host owns a GPU and collision avoidance is part of
        # admission. A missing sensor must not silently become "GPU idle".
        reasons.append(gpu_note)
    elif other_gpu is not None and other_gpu > max_other_gpu_mib:
        reasons.append("gpu_busy_other_workload")

    return {
        "ok": not reasons,
        "reasons": reasons,
        "host_mem_available_bytes": mem,
        "ci_memory_current_bytes": ci_current,
        "ci_memory_high_bytes": ci_high,
        "ci_memory_max_bytes": ci_max,
        "other_gpu_compute_mib": other_gpu,
    }


def _unload(model: str, ollama_bin: str) -> None:
    if model != DEFAULT_MODEL:
        return
    try:
        subprocess.run(
            [ollama_bin, "stop", model],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        pass


class Proxy(BaseHTTPRequestHandler):
    server_version = "mastermind-inference-guard/1"

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} {fmt % args}", flush=True)

    def _json(self, status: int, payload: dict, headers: dict[str, str] | None = None) -> None:
        data = json.dumps(payload, sort_keys=True).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        state = admission()
        if self.path == "/healthz":
            self._json(200 if state["ok"] else 503, state)
            return
        self._proxy(state)

    def do_POST(self) -> None:
        state = admission()
        self._proxy(state)

    def _proxy(self, state: dict) -> None:
        if not state["ok"]:
            self._json(503, {"error": "local_inference_not_admitted", **state}, {"Retry-After": "60"})
            return
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length < 0 or length > self.server.max_body:
            self._json(413, {"error": "request_too_large"})
            return
        body = self.rfile.read(length) if length else None
        with _LOCK:
            # Re-check after waiting for the one allowed local inference slot.
            state = admission()
            if not state["ok"]:
                self._json(503, {"error": "local_inference_not_admitted", **state}, {"Retry-After": "60"})
                return
            conn = None
            try:
                conn = http.client.HTTPConnection(
                    self.server.upstream_host,
                    self.server.upstream_port,
                    timeout=self.server.upstream_timeout,
                )
                headers = {
                    key: value
                    for key, value in self.headers.items()
                    if key.lower() not in {"host", "connection", "content-length"}
                }
                if body is not None:
                    headers["Content-Length"] = str(len(body))
                conn.request(self.command, self.path, body=body, headers=headers)
                resp = conn.getresponse()
                data = resp.read()
                self.send_response(resp.status)
                for key, value in resp.getheaders():
                    if key.lower() not in {"connection", "transfer-encoding", "content-length"}:
                        self.send_header(key, value)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception as exc:  # bounded local proxy; caller owns fallback
                self._json(502, {"error": "ollama_upstream_failure", "detail": type(exc).__name__})
            finally:
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass
                if self.command == "POST":
                    _unload(self.server.model, self.server.ollama_bin)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen", default="127.0.0.1:11435")
    ap.add_argument("--upstream", default="127.0.0.1:11434")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--ollama-bin", default="/usr/local/bin/ollama")
    ap.add_argument("--max-body", type=int, default=DEFAULT_MAX_BODY)
    ap.add_argument("--upstream-timeout", type=float, default=150.0)
    args = ap.parse_args()
    host, port = urlsplit("//" + args.listen).hostname, urlsplit("//" + args.listen).port
    up_host, up_port = urlsplit("//" + args.upstream).hostname, urlsplit("//" + args.upstream).port
    server = ThreadingHTTPServer((host, port), Proxy)
    server.upstream_host = up_host
    server.upstream_port = up_port
    server.model = args.model
    server.ollama_bin = args.ollama_bin
    server.max_body = args.max_body
    server.upstream_timeout = args.upstream_timeout
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
