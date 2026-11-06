"""Deterministic guard contracts; no real host, provider or subprocess calls."""
from __future__ import annotations

from email.message import Message
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "ops/inference-host/ubuntu/inference_guard.py"
SPEC = importlib.util.spec_from_file_location("inference_guard", PATH)
assert SPEC and SPEC.loader
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)


class FakeSocket:
    def __init__(self):
        self.timeouts, self.shutdowns, self.sent = [], [], []

    def settimeout(self, value):
        self.timeouts.append(value)

    def shutdown(self, how):
        self.shutdowns.append(how)

    def sendall(self, data):
        self.sent.append(data)


class FakeResponse:
    status = 200

    def __init__(self, data=b'{}', declared=None):
        self.data = io.BytesIO(data)
        self.declared = declared

    def getheader(self, name):
        return self.declared if name == "Content-Length" else None

    def getheaders(self):
        return [("Content-Type", "application/json")]

    def read1(self, size):
        return self.data.read(size)


class GuardTests(unittest.TestCase):
    def setUp(self):
        # A missing mock must fail before any physical host action or HTTP call.
        self.subprocess_fence = patch.object(
            GUARD.subprocess, "run", side_effect=AssertionError("real subprocess forbidden"),
        )
        self.http_fence = patch.object(
            GUARD.http.client, "HTTPConnection", side_effect=AssertionError("real HTTP forbidden"),
        )
        self.subprocess_fence.start()
        self.http_fence.start()
        self.addCleanup(self.subprocess_fence.stop)
        self.addCleanup(self.http_fence.stop)

    def _admission(self, *, memory=1000, current="10", high="100", maximum="200", gpu=(0, None)):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for name, value in (("current", current), ("high", high), ("max", maximum)):
                (root / ("memory." + name)).write_text(value)
            with patch.object(GUARD, "_mem_available", return_value=memory), \
                    patch.object(GUARD, "_other_gpu_mib", return_value=gpu):
                return GUARD.admission(cgroup=root, min_mem_available=11, max_other_gpu_mib=512)

    def test_admission_preserves_original_memory_ci_gpu_limits(self):
        for changes, reason in (
            ({"memory": 10}, "host_memory_low"),
            ({"memory": None}, "host_memory_unavailable"),
            ({"current": "100"}, "ci_memory_high"),
            ({"gpu": (513, None)}, "gpu_busy_other_workload"),
        ):
            with self.subTest(reason=reason):
                result = self._admission(**changes)
                self.assertFalse(result["ok"])
                self.assertIn(reason, result["reasons"])
        self.assertTrue(self._admission()["ok"])
        self.assertEqual(GUARD.DEFAULT_MIN_MEM_AVAILABLE, 16 * 1024**3)
        self.assertEqual(GUARD.DEFAULT_GPU_OTHER_MIB, 512)

    def test_admission_rejects_invalid_or_missing_cgroup_and_gpu(self):
        for changes in ({"current": "-1"}, {"high": "max"}, {"high": "0"},
                        {"maximum": "50"}, {"gpu": (None, None)}):
            with self.subTest(changes=changes):
                self.assertFalse(self._admission(**changes)["ok"])

    def test_gpu_counts_ollama_and_llama_names_conservatively(self):
        result = SimpleNamespace(returncode=0, stdout="/bin/ollama, 400\nllama-server, 200\nother, 3\n")
        with patch.object(GUARD.subprocess, "run", return_value=result):
            self.assertEqual(GUARD._other_gpu_mib(), (603, None))

    def test_gpu_invalid_rows_are_not_idle(self):
        for row in ("no comma", "process, N/A", "process, -1", ", 0", "process, 1.5",
                    "ollama, N/A", "process, " + "9" * 30):
            with self.subTest(row=row), patch.object(
                GUARD.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=row),
            ):
                value, reason = GUARD._other_gpu_mib()
                self.assertIsNone(value)
                self.assertTrue(reason)

    def test_gpu_empty_output_is_idle_but_command_failure_is_not(self):
        with patch.object(GUARD.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout="\n")):
            self.assertEqual(GUARD._other_gpu_mib(), (0, None))
        with patch.object(GUARD.subprocess, "run", return_value=SimpleNamespace(returncode=1, stdout="")):
            self.assertIsNone(GUARD._other_gpu_mib()[0])
        with patch.object(GUARD.subprocess, "run", side_effect=subprocess.TimeoutExpired("sensor", 3)):
            self.assertIsNone(GUARD._other_gpu_mib()[0])

    def test_unload_is_pinned_and_failures_are_observable(self):
        with patch.object(GUARD.subprocess, "run", return_value=SimpleNamespace(returncode=0)) as run:
            self.assertFalse(GUARD._unload("other-model", "/usr/local/bin/ollama"))
            run.assert_not_called()
            self.assertTrue(GUARD._unload(GUARD.DEFAULT_MODEL, "/usr/local/bin/ollama"))
            self.assertEqual(run.call_args.args[0], ["/usr/local/bin/ollama", "stop", GUARD.DEFAULT_MODEL])
        for result in (SimpleNamespace(returncode=1), OSError("absent"),
                       subprocess.TimeoutExpired("stop", 10)):
            with self.subTest(result=result), patch.object(GUARD.subprocess, "run") as run:
                if isinstance(result, Exception):
                    run.side_effect = result
                else:
                    run.return_value = result
                self.assertFalse(GUARD._unload(GUARD.DEFAULT_MODEL, "/usr/local/bin/ollama"))

    def test_loopback_configuration_is_intrinsic(self):
        self.assertEqual(GUARD._loopback_address("127.0.0.1:11435"), ("127.0.0.1", 11435))
        for value in ("0.0.0.0:11435", "localhost:11435", "192.168.1.2:11434",
                      "user@127.0.0.1:11434", "127.0.0.1:11434/path", "127.0.0.1:0"):
            with self.subTest(value=value), self.assertRaises(GUARD.argparse.ArgumentTypeError):
                GUARD._loopback_address(value)
        for args in (["--model", "other"], ["--max-body", "0"], ["--request-timeout", "nan"],
                     ["--upstream-timeout", "150"], ["--upstream", "127.0.0.1:11435"]):
            with self.subTest(args=args), patch("sys.argv", ["guard", *args]), \
                    patch.object(GUARD, "GuardServer") as server, patch("sys.stderr", io.StringIO()), \
                    self.assertRaises(SystemExit):
                GUARD.main()
            server.assert_not_called()

    def test_unload_binds_the_same_endpoint_despite_inherited_host(self):
        with patch.dict(GUARD.os.environ, {"OLLAMA_HOST": "http://192.0.2.5:11434"}), \
                patch.object(GUARD.subprocess, "run", return_value=SimpleNamespace(returncode=0)) as run:
            self.assertTrue(GUARD._unload(
                GUARD.DEFAULT_MODEL, "/usr/local/bin/ollama",
                upstream_host="127.0.0.1", upstream_port=21434,
            ))
            self.assertEqual(run.call_args.kwargs["env"]["OLLAMA_HOST"], "http://127.0.0.1:21434")
            self.assertEqual(run.call_count, 1)
            self.assertFalse(GUARD._unload(
                GUARD.DEFAULT_MODEL, "/usr/local/bin/ollama",
                upstream_host="192.0.2.5", upstream_port=21434,
            ))
            self.assertEqual(run.call_count, 1)

    def test_bounded_response_rejects_oversize_incomplete_and_deadline(self):
        conn = SimpleNamespace(sock=FakeSocket())
        for response, limit, deadline in (
            (FakeResponse(b"12345"), 4, time.monotonic() + 1),
            (FakeResponse(b"1", "5"), 4, time.monotonic() + 1),
            (FakeResponse(b"12", "4"), 4, time.monotonic() + 1),
            (FakeResponse(b"", "bad"), 4, time.monotonic() + 1),
            (FakeResponse(), 4, time.monotonic() - 1),
        ):
            with self.subTest(response=response), self.assertRaises((ValueError, TimeoutError)):
                GUARD._read_response(response, conn, limit, deadline)
        self.assertEqual(GUARD._read_response(FakeResponse(b"1234", "4"), conn, 4,
                                             time.monotonic() + 1), b"1234")

    def test_upstream_uses_socket_deadline_closes_and_preserves_bytes(self):
        server = SimpleNamespace(upstream_host="127.0.0.1", upstream_port=11434,
                                 upstream_timeout=90, max_response=1024)
        conn = Mock(sock=FakeSocket())
        conn.getresponse.return_value = FakeResponse(b'{"choices": []}')
        with patch.object(GUARD.http.client, "HTTPConnection", return_value=conn), \
                patch.object(GUARD.threading, "Timer") as timer:
            result = GUARD._upstream(server, "POST", "/v1/chat/completions", b'{"model":"pinned"}')
        self.assertEqual(result[2], b'{"choices": []}')
        self.assertEqual(conn.request.call_args.kwargs["body"], b'{"model":"pinned"}')
        self.assertEqual(timer.call_args.args[1], GUARD._interrupt_socket)
        timer.return_value.start.assert_called_once()
        timer.return_value.cancel.assert_called_once()
        conn.close.assert_called_once()

    def test_residency_unknown_or_nonempty_refuses_next_admission(self):
        server = SimpleNamespace(upstream_timeout=90)
        for status, body in ((200, b'{"models":[{"name":"qwen3.5:9b"}]}'),
                             (200, b'{"models":[{}]}'), (200, b'{}'), (500, b'{}')):
            with self.subTest(body=body), patch.object(GUARD, "admission", side_effect=lambda: {"ok": True, "reasons": []}), \
                    patch.object(GUARD, "_upstream", return_value=(status, [], body)):
                self.assertFalse(GUARD._admission_state(server)["ok"])
        with patch.object(GUARD, "admission", return_value={"ok": False, "reasons": ["busy"]}), \
                patch.object(GUARD, "_upstream") as upstream:
            self.assertFalse(GUARD._admission_state(server)["ok"])
            upstream.assert_not_called()
        with patch.object(GUARD, "admission", return_value={"ok": True, "reasons": []}), \
                patch.object(GUARD, "_upstream", return_value=(200, [], b'{"models":[]}')):
            self.assertTrue(GUARD._admission_state(server)["ok"])

    def _handler(self, *, method="POST", path="/v1/chat/completions", payload=None, raw=None):
        if raw is None:
            payload = payload if payload is not None else {
                "model": GUARD.DEFAULT_MODEL, "stream": False, "temperature": 0,
                "reasoning_effort": "none", "max_tokens": 1200,
                "messages": [{"role": "user", "content": "/no_think bounded fixture"}],
            }
            raw = json.dumps(payload).encode() if method == "POST" else b""
        handler = object.__new__(GUARD.Proxy)
        handler.command, handler.path = method, path
        handler.server = SimpleNamespace(model=GUARD.DEFAULT_MODEL, ollama_bin="/usr/local/bin/ollama",
                                         max_body=1024, max_response=1024, request_timeout=5,
                                         upstream_timeout=90, upstream_host="127.0.0.1", upstream_port=11434)
        handler.headers = Message()
        handler.headers["Content-Length"] = str(len(raw))
        handler.rfile, handler.connection = io.BytesIO(raw), FakeSocket()
        handler._header_deadline = Mock()
        handler.outputs = []
        handler._send = lambda status, headers, data: handler.outputs.append((status, headers, data))
        return handler, raw

    def _dispatch(self, handler):
        getattr(handler, "do_" + handler.command)()
        return handler.outputs[-1]

    def test_busy_refuses_before_body_telemetry_or_upstream(self):
        handler, _ = self._handler()
        handler.rfile = Mock()
        GUARD._LOCK.acquire()
        try:
            with patch.object(GUARD, "_admission_state") as state:
                result = self._dispatch(handler)
                self.assertEqual(result[0], 503)
                state.assert_not_called()
                handler.rfile.read1.assert_not_called()
        finally:
            GUARD._LOCK.release()

    def test_request_input_and_path_rejections_do_not_infer_or_unload(self):
        for payload in ({"model": "other"}, {"model": GUARD.DEFAULT_MODEL, "stream": True}, []):
            with self.subTest(payload=payload):
                handler, _ = self._handler(payload=payload)
                with patch.object(GUARD, "_admission_state", return_value={"ok": True}), \
                        patch.object(GUARD, "_upstream") as upstream, patch.object(GUARD, "_unload") as unload:
                    self.assertEqual(self._dispatch(handler)[0], 400)
                    upstream.assert_not_called()
                    unload.assert_not_called()
        for path in ("/api/generate", "/api/pull", "/api/delete", "/v1/chat/completions?x=1"):
            handler, _ = self._handler(path=path)
            with patch.object(GUARD, "_admission_state") as state:
                self.assertEqual(self._dispatch(handler)[0], 404)
                state.assert_not_called()

    def test_bad_lengths_and_body_timeout_release_slot(self):
        for length, expected in (("-1", 400), ("bad", 400), ("2048", 413), ("9" * 30, 413)):
            handler, _ = self._handler()
            handler.headers.replace_header("Content-Length", length)
            self.assertEqual(self._dispatch(handler)[0], expected)
            self.assertFalse(GUARD._LOCK.locked())
        for raw, declared, expected in ((b"{bad", "4", 400), (b"{}", "4", 400)):
            handler, _ = self._handler(raw=raw)
            handler.headers.replace_header("Content-Length", declared)
            with patch.object(GUARD, "_admission_state", return_value={"ok": True}):
                self.assertEqual(self._dispatch(handler)[0], expected)
        handler, _ = self._handler()
        handler.rfile = Mock()
        handler.rfile.read1.side_effect = TimeoutError()
        with patch.object(GUARD, "_admission_state", return_value={"ok": True}):
            self.assertEqual(self._dispatch(handler)[0], 408)
        self.assertFalse(GUARD._LOCK.locked())

    def test_ambiguous_or_missing_length_is_rejected(self):
        for mode, code in (("duplicate", 400), ("transfer", 400), ("missing", 411)):
            handler, _ = self._handler()
            if mode == "duplicate":
                handler.headers["Content-Length"] = "1"
            elif mode == "transfer":
                handler.headers["Transfer-Encoding"] = "chunked"
            else:
                del handler.headers["Content-Length"]
            self.assertEqual(self._dispatch(handler)[0], code)

    def test_success_keeps_earnings_payload_and_waits_for_cleanup(self):
        handler, body = self._handler()
        events = []
        response = b'{"choices":[{"message":{"content":"healthy fixture"}}],"usage":{}}'
        def upstream(server, method, path, raw):
            events.append("inference")
            self.assertEqual((method, path, raw), ("POST", "/v1/chat/completions", body))
            return 200, [("Content-Type", "application/json")], response
        original_send = handler._send
        handler._send = lambda *args: (events.append("response"), original_send(*args))
        with patch.object(GUARD, "_admission_state", return_value={"ok": True}), \
                patch.object(GUARD, "_upstream", side_effect=upstream), \
                patch.object(GUARD, "_unload", side_effect=lambda *a, **k: events.append("stop") or True), \
                patch.object(GUARD, "_resident_models", side_effect=lambda *a: (events.append("residency") or [], None)):
            self.assertEqual(self._dispatch(handler)[2], response)
        self.assertEqual(events, ["inference", "stop", "residency", "response"])
        self.assertFalse(GUARD._LOCK.locked())

    def test_cleanup_failure_never_returns_buffered_success(self):
        for stopped, models, note in ((False, [], None), (True, [GUARD.DEFAULT_MODEL], None),
                                      (True, None, "unavailable")):
            handler, _ = self._handler()
            with self.subTest(stopped=stopped, models=models), \
                    patch.object(GUARD, "_admission_state", return_value={"ok": True}), \
                    patch.object(GUARD, "_upstream", return_value=(200, [], b"success")), \
                    patch.object(GUARD, "_unload", return_value=stopped) as unload, \
                    patch.object(GUARD, "_resident_models", return_value=(models, note)):
                result = self._dispatch(handler)
                self.assertEqual(result[0], 502)
                self.assertIn(b"cleanup_unverified", result[2])
                unload.assert_called_once()
            self.assertFalse(GUARD._LOCK.locked())

    def test_upstream_error_still_unloads_once_and_releases_slot(self):
        handler, _ = self._handler()
        with patch.object(GUARD, "_admission_state", return_value={"ok": True}), \
                patch.object(GUARD, "_upstream", side_effect=ValueError("response limit")), \
                patch.object(GUARD, "_unload", return_value=True) as unload, \
                patch.object(GUARD, "_resident_models", return_value=([], None)):
            self.assertEqual(self._dispatch(handler)[0], 502)
            unload.assert_called_once()
        self.assertFalse(GUARD._LOCK.locked())

    def test_models_inventory_shape_and_health_refusal_are_preserved(self):
        handler, _ = self._handler(method="GET", path="/v1/models")
        response = json.dumps({"data": [{"id": GUARD.DEFAULT_MODEL}]}).encode()
        with patch.object(GUARD, "_admission_state", return_value={"ok": True}), \
                patch.object(GUARD, "_upstream", return_value=(200, [], response)), \
                patch.object(GUARD, "_unload") as unload:
            self.assertEqual(self._dispatch(handler)[2], response)
            unload.assert_not_called()
        handler, _ = self._handler(method="GET", path="/healthz")
        with patch.object(GUARD, "_admission_state", return_value={"ok": False, "reasons": ["resident"]}):
            self.assertEqual(self._dispatch(handler)[0], 503)

    def test_concurrent_request_is_refused_while_first_is_running(self):
        first, _ = self._handler()
        second, _ = self._handler()
        second.rfile = Mock()
        entered, release, done = threading.Event(), threading.Event(), threading.Event()
        def upstream(*args):
            entered.set()
            if not release.wait(3):
                raise TimeoutError("test release")
            return 200, [], b"fixture"
        def contender():
            self._dispatch(second)
            done.set()
        with patch.object(GUARD, "_admission_state", return_value={"ok": True}), \
                patch.object(GUARD, "_upstream", side_effect=upstream), \
                patch.object(GUARD, "_unload", return_value=True), \
                patch.object(GUARD, "_resident_models", return_value=([], None)):
            one = threading.Thread(target=self._dispatch, args=(first,))
            two = threading.Thread(target=contender)
            one.start()
            try:
                self.assertTrue(entered.wait(1))
                two.start()
                self.assertTrue(done.wait(1), "contending request queued behind inference")
                self.assertEqual(second.outputs[0][0], 503)
                second.rfile.read1.assert_not_called()
            finally:
                release.set()
                one.join(2)
                if two.ident is not None:
                    two.join(2)
        self.assertFalse(one.is_alive())
        self.assertFalse(GUARD._LOCK.locked())

    def test_connection_handler_bound_refuses_excess_socket(self):
        server = object.__new__(GUARD.GuardServer)
        server._connections = threading.BoundedSemaphore(1)
        server._connections.acquire()
        server.shutdown_request = Mock()
        sock = FakeSocket()
        server.process_request(sock, ("127.0.0.1", 1))
        self.assertTrue(sock.sent[0].startswith(b"HTTP/1.1 503"))
        server.shutdown_request.assert_called_once_with(sock)
        self.assertFalse(server._connections.acquire(blocking=False))
        server._connections.release()

    def test_service_and_existing_resource_envelope_are_preserved(self):
        unit = (ROOT / "ops/inference-host/ubuntu/mastermind-inference-guard.service").read_text()
        for token in ("--listen 127.0.0.1:11435", "--upstream 127.0.0.1:11434", "--model qwen3.5:9b",
                      "Requires=ollama.service", "NoNewPrivileges=true", "ProtectSystem=strict",
                      "ProtectHome=true", "Slice=mastermind-inference.slice", "CPUWeight=10", "IOWeight=10"):
            self.assertIn(token, unit)
        envelope = (ROOT / "ops/inference-host/ubuntu/mastermind-inference.slice").read_text()
        for token in ("CPUQuota=400%", "CPUWeight=10", "IOWeight=10", "MemoryHigh=12G", "MemoryMax=16G", "MemorySwapMax=2G"):
            self.assertIn(token, envelope)
        dropin = (ROOT / "ops/inference-host/ubuntu/ollama-mastermind.conf").read_text()
        for token in ("Slice=mastermind-inference.slice", 'Environment="OLLAMA_HOST=127.0.0.1:11434"',
                      'Environment="OLLAMA_NUM_PARALLEL=1"', 'Environment="OLLAMA_MAX_LOADED_MODELS=1"',
                      "MemoryHigh=12G", "MemoryMax=16G"):
            self.assertIn(token, dropin)


if __name__ == "__main__":
    unittest.main()
