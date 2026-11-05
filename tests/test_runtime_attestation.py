"""Offline consumed-buffer/invocation tests; never import the real API or contact a host."""
from __future__ import annotations

import hashlib
import importlib
import importlib.machinery
import io
import json
import marshal
import os
from pathlib import Path
import py_compile
import shlex
import sys
import threading
import time
import types

import pytest

from app import runtime_attestation as runtime


BOOTSTRAP = b"bootstrap = True\n"
BOOTSTRAP_CODE = compile(BOOTSTRAP, "bootstrap.py", "exec", dont_inherit=True)


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    records = []
    context = {"pid": os.getpid(), "invocation_id": "b" * 32, "boot_id": "a" * 32,
               "startticks": 12345, "bound": True}
    # Separate package identities prevent accidental real engine/API imports.
    for package in ("app", "engine", "lib"):
        directory = tmp_path / package
        directory.mkdir()
        module = types.ModuleType(package)
        module.__path__ = [str(directory)]
        module.__package__ = package
        monkeypatch.setitem(sys.modules, package, module)
    for name in runtime.MODULES:
        monkeypatch.delitem(sys.modules, name, raising=False)
    monkeypatch.setattr(sys, "meta_path", list(sys.meta_path))
    attestor = runtime.Attestor(tmp_path, BOOTSTRAP, BOOTSTRAP_CODE,
                               context=context, sink=records.append)
    attestor.install()
    return tmp_path, attestor, records


@pytest.mark.parametrize("cache", ["valid", "timestamp_collision", "invalid_hash"])
def test_exact_source_is_consumed_regardless_of_bytecode_cache(sandbox, cache):
    root, attestor, records = sandbox
    path = root / "engine/ontology_theme.py"
    original = b"VALUE = 'cache'\n"
    fresh = b"VALUE = 'fresh'\n"
    path.write_bytes(original)
    timestamp = path.stat().st_mtime_ns
    mode = (py_compile.PycInvalidationMode.CHECKED_HASH if cache == "invalid_hash"
            else py_compile.PycInvalidationMode.TIMESTAMP)
    pyc = Path(py_compile.compile(str(path), doraise=True, invalidation_mode=mode))
    cache_bytes = pyc.read_bytes()
    consumed = original if cache == "valid" else fresh
    path.write_bytes(consumed)
    os.utime(path, ns=(timestamp, timestamp))
    if cache == "timestamp_collision":
        # Demonstrate the falsifier: ordinary timestamp validation accepts stale code.
        ordinary = importlib.machinery.SourceFileLoader("engine.ontology_theme", str(path))
        old = {}
        exec(ordinary.get_code("engine.ontology_theme"), old)
        assert old["VALUE"] == "cache"
    module = importlib.import_module("engine.ontology_theme")
    assert module.VALUE == ("cache" if cache == "valid" else "fresh")
    assert module.__spec__.name == "engine.ontology_theme"
    assert module.__package__ == "engine"
    assert isinstance(module.__loader__, importlib.machinery.SourceFileLoader)
    record, = records
    assert record["status"] == "loaded"
    assert record["source_sha256"] == hashlib.sha256(consumed).hexdigest()
    expected_code = compile(consumed, str(path), "exec", dont_inherit=True,
                            optimize=sys.flags.optimize)
    assert record["code_sha256"] == hashlib.sha256(marshal.dumps(expected_code, 2)).hexdigest()
    assert record["code_hash_format"] == "python_marshal_v2"
    assert record["invocation_bound"] is True
    assert record["bootstrap_source_sha256"] == hashlib.sha256(BOOTSTRAP).hexdigest()
    assert pyc.read_bytes() == cache_bytes  # No pyc rewrite is needed for the proof.


def test_post_capture_file_change_cannot_change_executed_buffer(sandbox, monkeypatch):
    root, _, records = sandbox
    path = root / "engine/ontology_theme.py"
    consumed = b"VALUE = 'captured'\n"
    path.write_bytes(consumed)
    original = runtime._source
    def replace_after_read(filename):
        raw = original(filename)
        Path(filename).write_bytes(b"VALUE = 'replacement'\n")
        return raw
    monkeypatch.setattr(runtime, "_source", replace_after_read)
    assert importlib.import_module("engine.ontology_theme").VALUE == "captured"
    assert records[0]["source_sha256"] == hashlib.sha256(consumed).hexdigest()
    assert records[0]["source_sha256"] != hashlib.sha256(path.read_bytes()).hexdigest()


def test_source_mutation_during_capture_refuses_import(sandbox, monkeypatch):
    root, _, records = sandbox
    path = root / "engine/ontology_theme.py"
    path.write_text("VALUE = 1\n")
    original = os.pread
    def racing_read(fd, size, offset):
        raw = original(fd, size, offset)
        path.write_text("VALUE = 200\n")
        return raw
    monkeypatch.setattr(runtime.os, "pread", racing_read)
    with pytest.raises(ImportError, match="SOURCE_CHANGED"):
        importlib.import_module("engine.ontology_theme")
    assert records[0]["status"] == "failed"
    assert records[0]["source_sha256"] is None


@pytest.mark.parametrize(("source", "error"), [
    ("def broken(:\n", SyntaxError),
    ("raise RuntimeError('PRIVATE_EXCEPTION_TEXT')\n", RuntimeError),
    ("raise SystemExit(7)\n", SystemExit),
    ("def f(value: UndefinedType): pass\nf.__annotations__\n", NameError),
])
def test_failed_import_stays_failed_and_does_not_leak_details(sandbox, source, error):
    root, _, records = sandbox
    (root / "engine/ontology_theme.py").write_text(source)
    with pytest.raises(error):
        importlib.import_module("engine.ontology_theme")
    assert "engine.ontology_theme" not in sys.modules
    record, = records
    assert record["status"] == "failed" and record["error_class"] == error.__name__
    assert "PRIVATE_EXCEPTION_TEXT" not in json.dumps(record)
    assert str(root) not in json.dumps(record)


def test_lazy_module_remains_unobserved_until_authenticated_call(sandbox):
    root, _, records = sandbox
    (root / "app/main.py").write_text(
        "def journey(entitled):\n"
        "    if not entitled: raise PermissionError('denied')\n"
        "    from engine.ontology_theme import VALUE\n"
        "    return VALUE\n")
    (root / "engine/ontology_theme.py").write_text("VALUE = 42\n")
    main = importlib.import_module("app.main")
    assert [r["module"] for r in records] == ["app.main"]
    assert "engine.ontology_theme" not in sys.modules
    with pytest.raises(PermissionError):
        main.journey(False)
    assert [r["module"] for r in records] == ["app.main"]
    assert main.journey(True) == 42
    assert [r["module"] for r in records] == ["app.main", "engine.ontology_theme"]
    assert records[1]["sequence"] > records[0]["sequence"]


@pytest.mark.parametrize("failure", ["unbound", "different_pid", "sink"])
def test_metadata_or_journal_failure_does_not_replace_import_result(sandbox, monkeypatch, failure):
    root, attestor, records = sandbox
    (root / "engine/ontology_theme.py").write_text("VALUE = 42\n")
    if failure == "unbound":
        attestor.context["bound"] = False
    elif failure == "different_pid":
        monkeypatch.setattr(runtime.os, "getpid", lambda: attestor.context["pid"] + 1)
    else:
        def unavailable(record):
            raise OSError("PRIVATE_SINK_TEXT")
        attestor.sink = unavailable
    assert importlib.import_module("engine.ontology_theme").VALUE == 42
    if failure == "sink":
        assert records == [] and attestor.delivery_failures == 1
    else:
        assert records[0]["invocation_bound"] is False


def test_failed_import_is_not_hidden_by_failed_journal(sandbox):
    root, attestor, _ = sandbox
    (root / "engine/ontology_theme.py").write_text("raise KeyError('original')\n")
    attestor.sink = lambda record: (_ for _ in ()).throw(OSError("sink"))
    with pytest.raises(KeyError, match="original"):
        importlib.import_module("engine.ontology_theme")
    assert attestor.delivery_failures == 1


@pytest.mark.parametrize("failure", [None, "invocation", "boot", "process"])
def test_context_binds_only_systemd_invocation_boot_and_process(monkeypatch, failure):
    pid = 456
    monkeypatch.setattr(runtime.os, "getpid", lambda: pid)
    monkeypatch.setenv("INVOCATION_ID", "b" * 32 if failure != "invocation" else "invalid")
    fields = ["S"] + ["0"] * 18 + ["12345"]
    proc = f"{pid} (name with ) inside) " + " ".join(fields)
    values = {"/proc/sys/kernel/random/boot_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
              "/proc/self/stat": proc}
    if failure == "boot":
        values["/proc/sys/kernel/random/boot_id"] = "bad"
    if failure == "process":
        values["/proc/self/stat"] = "incomplete"
    monkeypatch.setattr(runtime, "_bounded_text", lambda path, limit: values[path])
    context = runtime.invocation_context()
    assert context["bound"] is (failure is None)
    if failure is None:
        assert context == {"pid": pid, "invocation_id": "b" * 32,
                           "boot_id": "a" * 32, "startticks": 12345, "bound": True}


def test_other_modules_are_not_intercepted_and_preloaded_modules_are_not_attested(sandbox):
    root, attestor, _ = sandbox
    assert attestor.find_spec("engine.unrelated", [str(root / "engine")]) is None
    sys.modules["engine.ontology_theme"] = types.ModuleType("engine.ontology_theme")
    with pytest.raises(ImportError, match="INSTALLED_AFTER_IMPORT"):
        runtime.Attestor(root, BOOTSTRAP, BOOTSTRAP_CODE, context=attestor.context).install()


def test_journal_records_are_bounded_metadata_only(sandbox, capsys):
    _, attestor, records = sandbox
    attestor.emit("engine.company_intelligence.current_company_context", "failed",
                  BOOTSTRAP, BOOTSTRAP_CODE, RuntimeError("PRIVATE_TEXT"))
    record, = records
    runtime._journal(record)
    line = capsys.readouterr().err.strip()
    assert line.startswith(runtime.JOURNAL_PREFIX) and len(line.encode()) <= 2048
    assert json.loads(line[len(runtime.JOURNAL_PREFIX):]) == record
    assert "PRIVATE_TEXT" not in line and "source_path" not in record
    with pytest.raises(ValueError, match="RECORD_BOUND"):
        runtime._journal({"oversized": "x" * 2048})


@pytest.mark.parametrize("kind", ["symlink", "oversized"])
def test_source_resource_refusals_never_report_a_loaded_module(sandbox, kind):
    root, _, records = sandbox
    path = root / "engine/ontology_theme.py"
    if kind == "symlink":
        target = root / "elsewhere.py"
        target.write_text("VALUE = 42\n")
        path.symlink_to(target)
    else:
        path.write_bytes(b"#" * (runtime.MAX_SOURCE_BYTES + 1))
    with pytest.raises((OSError, ImportError)):
        importlib.import_module("engine.ontology_theme")
    assert [r["status"] for r in records] == ["failed"]


def test_origin_mismatch_cannot_fall_back_to_unattested_import(sandbox, monkeypatch):
    root, _, records = sandbox
    elsewhere = root / "unbound"
    elsewhere.mkdir()
    (elsewhere / "ontology_theme.py").write_text("VALUE = 42\n")
    monkeypatch.setattr(sys.modules["engine"], "__path__", [str(elsewhere)])
    with pytest.raises(ImportError, match="ORIGIN_MISMATCH"):
        importlib.import_module("engine.ontology_theme")
    assert records[0]["status"] == "failed"
    assert records[0]["source_sha256"] is None


def test_bootstrap_root_alias_matches_only_the_same_physical_tree(sandbox):
    root, original, records = sandbox
    alias = root / "logical-checkout"
    alias.symlink_to(root, target_is_directory=True)
    sys.meta_path.remove(original)
    attestor = runtime.Attestor(alias, BOOTSTRAP, BOOTSTRAP_CODE,
                               context=original.context, sink=records.append)
    attestor.install()
    (root / "engine/ontology_theme.py").write_text("VALUE = 42\n")
    assert importlib.import_module("engine.ontology_theme").VALUE == 42
    assert attestor.root == root.resolve()
    assert records[0]["status"] == "loaded"


def test_missing_module_preserves_optional_import_fallback(sandbox):
    root, _, records = sandbox
    (root / "app/main.py").write_text(
        "try:\n    import engine.ontology_theme\n"
        "except ModuleNotFoundError as error:\n    missing = error.name\n")
    assert importlib.import_module("app.main").missing == "engine.ontology_theme"
    assert [(r["module"], r["status"], r["error_class"]) for r in records] == [
        ("engine.ontology_theme", "failed", "ModuleNotFoundError"),
        ("app.main", "loaded", None)]


def test_journal_uses_one_complete_write(sandbox, monkeypatch):
    _, attestor, records = sandbox
    attestor.emit("app.main", "loaded", BOOTSTRAP, BOOTSTRAP_CODE)
    writes = []
    class Stream:
        def write(self, value):
            writes.append(value)
        def flush(self):
            pass
    monkeypatch.setattr(runtime.sys, "stderr", Stream())
    runtime._journal(records[0])
    assert len(writes) == 1 and writes[0].endswith("\n")
    assert json.loads(writes[0][len(runtime.JOURNAL_PREFIX):]) == records[0]


@pytest.mark.parametrize("fail_body", [False, True])
def test_incomplete_context_does_not_discard_or_reexecute_import(sandbox, monkeypatch, fail_body):
    root, original, records = sandbox
    sys.meta_path.remove(original)
    attestor = runtime.Attestor(root, BOOTSTRAP, BOOTSTRAP_CODE, context={}, sink=records.append)
    attestor.install()
    import builtins
    monkeypatch.setattr(builtins, "_f04_test_executions", 0, raising=False)
    source = "import builtins\nbuiltins._f04_test_executions += 1\n"
    if fail_body:
        source += "raise LookupError('original')\n"
    (root / "engine/ontology_theme.py").write_text(source)
    if fail_body:
        with pytest.raises(LookupError, match="original"):
            importlib.import_module("engine.ontology_theme")
    else:
        importlib.import_module("engine.ontology_theme")
        importlib.import_module("engine.ontology_theme")
    assert builtins._f04_test_executions == 1
    assert records[0]["invocation_bound"] is False
    assert records[0]["status"] == ("failed" if fail_body else "loaded")


def test_metadata_construction_failure_does_not_replace_execution(sandbox, monkeypatch):
    root, attestor, _ = sandbox
    (root / "engine/ontology_theme.py").write_text("VALUE = 42\n")
    monkeypatch.setattr(attestor, "_emit", lambda *args: (_ for _ in ()).throw(ValueError("metadata")))
    assert importlib.import_module("engine.ontology_theme").VALUE == 42
    assert attestor.delivery_failures == 1


def test_concurrent_emissions_have_unique_ordered_sequences(sandbox):
    _, attestor, records = sandbox
    def sink(record):
        time.sleep(0.001)
        records.append(record)
    attestor.sink = sink
    def emit():
        for _ in range(10):
            attestor.emit("engine.ontology_theme", "loaded", BOOTSTRAP, BOOTSTRAP_CODE)
    threads = [threading.Thread(target=emit) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=3)
        assert not thread.is_alive()
    assert [record["sequence"] for record in records] == list(range(1, 41))


def test_unit_executes_the_exact_bootstrap_buffer_without_importing_a_pyc(monkeypatch):
    unit = (Path(__file__).resolve().parents[1] / "app/deploy/macro-api.service").read_text()
    command = next(line.split("=", 1)[1] for line in unit.splitlines() if line.startswith("ExecStart="))
    argv = shlex.split(command)
    assert argv[:3] == ["/opt/macro-api/.venv/bin/python3", "-B", "-c"]
    captured = {}
    bootstrap = (b"capture(_BOOTSTRAP_SOURCE, _BOOTSTRAP_CODE, __name__, __file__)\n")
    def open_bootstrap(path, mode):
        assert path == "/opt/macro/app/runtime_attestation.py" and mode == "rb"
        return io.BytesIO(bootstrap)
    def capture(raw, code, name, filename):
        captured.update(raw=raw, code=code, name=name, filename=filename)
    import builtins
    monkeypatch.setattr(builtins, "capture", capture, raising=False)
    exec(argv[3], {"open": open_bootstrap})
    assert captured["raw"] is bootstrap
    assert captured["name"] == "__main__"
    assert captured["code"].co_filename == captured["filename"]
    expected = compile(bootstrap, captured["filename"], "exec", dont_inherit=True)
    assert marshal.dumps(captured["code"], 2) == marshal.dumps(expected, 2)


@pytest.mark.parametrize("size", [0, runtime.MAX_SOURCE_BYTES + 1])
def test_unit_bootstrap_bound_survives_optimization(monkeypatch, size):
    unit = (Path(__file__).resolve().parents[1] / "app/deploy/macro-api.service").read_text()
    command = next(line.split("=", 1)[1] for line in unit.splitlines() if line.startswith("ExecStart="))
    inline = shlex.split(command)[3]
    with pytest.raises(SystemExit, match="F04_BOOTSTRAP_BOUND"):
        exec(compile(inline, "unit-startup", "exec", optimize=2),
             {"open": lambda *args: io.BytesIO(b"#" * size)})


def test_run_preserves_single_process_uvicorn_and_only_installs_the_finder(monkeypatch):
    calls = []
    class FakeAttestor:
        def __init__(self, root, source, code):
            calls.append(("construct", root, source, code))
        def install(self):
            calls.append(("install",))
        def emit(self, *args):
            calls.append(("emit", *args))
    uvicorn = types.ModuleType("uvicorn")
    uvicorn.run = lambda *args, **kwargs: calls.append(("uvicorn", args, kwargs))
    monkeypatch.setitem(sys.modules, "uvicorn", uvicorn)
    monkeypatch.setattr(runtime, "Attestor", FakeAttestor)
    runtime.run(BOOTSTRAP, BOOTSTRAP_CODE)
    assert calls[0][2:] == (BOOTSTRAP, BOOTSTRAP_CODE)
    assert calls[1] == ("install",)
    assert calls[2][1:3] == ("app.runtime_attestation", "bootstrap_ready")
    assert calls[3] == ("uvicorn", ("app.main:app",),
                        {"host": "127.0.0.1", "port": 8000, "proxy_headers": True})
