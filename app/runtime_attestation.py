"""Source-consuming import evidence for the ordinary macro-api invocation.

Only the fixed F04 module set is intercepted. The loader compiles and executes
one captured source buffer, bypassing both valid and stale bytecode caches.
Records go to the existing service journal, never a public API or another store.
An absent record is UNOBSERVED; source placement is not loaded-code evidence.
"""
from __future__ import annotations

import hashlib
import importlib.abc
import importlib.machinery
import json
import marshal
import os
from pathlib import Path
import re
import stat
import sys
import threading


MODULES = (
    "app.main", "app.company_disclosures",
    "engine.company_intelligence.current_company_context",
    "engine.company_intelligence.current_context_runtime",
    "app.ontology_explorer", "engine.ontology_explorer", "engine.ontology_theme",
    "engine.ontology_scenario_runtime", "engine.ontology_portfolio",
    "lib.quote_native_metadata", "lib.evidence_foundation",
)
MAX_SOURCE_BYTES = 262144
JOURNAL_PREFIX = "F04_RUNTIME_IMPORT "


def _bounded_text(path: str, limit: int) -> str:
    with open(path, "rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("METADATA_BOUND")
    return raw.decode("ascii").strip()


def invocation_context() -> dict:
    """No environment export: only systemd's fixed non-secret invocation token."""
    result = {"pid": os.getpid(), "invocation_id": None, "boot_id": None,
              "startticks": None, "bound": False}
    try:
        invocation = os.environ.get("INVOCATION_ID", "")
        if re.fullmatch(r"[0-9a-f]{32}", invocation) is None:
            raise ValueError("INVOCATION_ID")
        boot = _bounded_text("/proc/sys/kernel/random/boot_id", 64)
        if re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", boot) is None:
            raise ValueError("BOOT_ID")
        proc = _bounded_text("/proc/self/stat", 4096)
        fields = proc[proc.rfind(")") + 2:].split()
        ticks = int(fields[19])
        if int(proc.split("(", 1)[0]) != result["pid"] or ticks <= 0:
            raise ValueError("PROCESS_IDENTITY")
        result.update(invocation_id=invocation, boot_id=boot.replace("-", ""),
                      startticks=ticks, bound=True)
    except (OSError, UnicodeError, ValueError, IndexError):
        # The API can still run; these events cannot qualify a service invocation.
        pass
    return result


def _journal(record: dict) -> None:
    # Fixed metadata only. No exception messages, paths, argv, source or env values.
    line = JOURNAL_PREFIX + json.dumps(record, sort_keys=True, separators=(",", ":"))
    if len(line.encode("utf-8")) > 2048:
        raise ValueError("F04_JOURNAL_RECORD_BOUND")
    sys.stderr.write(line + "\n")
    sys.stderr.flush()


def _source(path: str) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= MAX_SOURCE_BYTES:
            raise ImportError("F04_SOURCE_TYPE_OR_BOUND")
        raw = os.pread(fd, before.st_size + 1, 0)
        after = os.fstat(fd)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if len(raw) != before.st_size or identity(before) != identity(after):
            raise ImportError("F04_SOURCE_CHANGED_DURING_READ")
        return raw
    finally:
        os.close(fd)


class Attestor(importlib.abc.MetaPathFinder):
    def __init__(self, root: Path, bootstrap_source: bytes, bootstrap_code,
                 *, context: dict | None = None, sink=None):
        # Resolve only the installed bootstrap's own root, never a cwd fallback
        # or a search for another checkout. The fixed unit supplies /opt/macro.
        self.root = root.resolve()
        candidate = invocation_context() if context is None else context
        candidate = candidate if isinstance(candidate, dict) else {}
        invocation = candidate.get("invocation_id")
        boot = candidate.get("boot_id")
        ticks = candidate.get("startticks")
        invocation = invocation if isinstance(invocation, str) and re.fullmatch(r"[0-9a-f]{32}", invocation) else None
        boot = boot if isinstance(boot, str) and re.fullmatch(r"[0-9a-f]{32}", boot) else None
        ticks = ticks if type(ticks) is int and ticks > 0 else None
        self.context = {"pid": os.getpid(), "invocation_id": invocation, "boot_id": boot,
                        "startticks": ticks, "bound": (candidate.get("bound") is True
                        and candidate.get("pid") == os.getpid() and invocation is not None
                        and boot is not None and ticks is not None)}
        self.sink = _journal if sink is None else sink
        self._emission_lock = threading.Lock()
        self.sequence = 0
        self.delivery_failures = 0
        self.bootstrap = {
            "bootstrap_source_sha256": hashlib.sha256(bootstrap_source).hexdigest(),
            "bootstrap_code_sha256": hashlib.sha256(marshal.dumps(bootstrap_code, 2)).hexdigest(),
        }

    def emit(self, module: str, status: str, raw=None, code=None, error=None) -> None:
        # Serialize the entire small record, not module execution. Imports of
        # different lazy modules may complete on different request threads.
        with self._emission_lock:
            try:
                self._emit(module, status, raw, code, error)
            except Exception:
                # Metadata construction or output failure must not turn a
                # successfully executed import into a discarded/re-executed one.
                self.delivery_failures += 1

    def _emit(self, module: str, status: str, raw, code, error) -> None:
        self.sequence += 1
        pid = os.getpid()
        record = {
            "schema": "f04.runtime_import/v1", "module": module, "status": status,
            "loader_mode": "captured_source_no_pyc", "sequence": self.sequence,
            "pid": pid, "invocation_id": self.context.get("invocation_id"),
            "boot_id": self.context.get("boot_id"), "startticks": self.context.get("startticks"),
            "invocation_bound": self.context.get("bound") is True and pid == self.context.get("pid"),
            "python_cache_tag": sys.implementation.cache_tag, "optimize": sys.flags.optimize,
            "code_hash_format": "python_marshal_v2",
            "source_sha256": hashlib.sha256(raw).hexdigest() if raw is not None else None,
            "source_bytes": len(raw) if raw is not None else None,
            "code_sha256": hashlib.sha256(marshal.dumps(code, 2)).hexdigest() if code is not None else None,
            "error_class": type(error).__name__[:80] if error is not None else None,
            **self.bootstrap,
        }
        self.sink(record)

    def install(self) -> None:
        if any(name in sys.modules for name in MODULES):
            raise ImportError("F04_ATTESTATION_INSTALLED_AFTER_IMPORT")
        if any(isinstance(finder, Attestor) for finder in sys.meta_path):
            raise ImportError("F04_ATTESTATION_ALREADY_INSTALLED")
        sys.meta_path.insert(0, self)

    def find_spec(self, fullname, path=None, target=None):
        if fullname not in MODULES:
            return None
        spec = importlib.machinery.PathFinder.find_spec(fullname, path, target)
        expected = self.root.joinpath(*fullname.split(".")).with_suffix(".py")
        if spec is None:
            error = ModuleNotFoundError(f"No module named {fullname!r}", name=fullname)
            self.emit(fullname, "failed", error=error)
            raise error
        if (not isinstance(spec.loader, importlib.machinery.SourceFileLoader)
                or not spec.origin or Path(spec.origin).resolve() != expected):
            error = ImportError("F04_SOURCE_ORIGIN_MISMATCH", name=fullname)
            self.emit(fullname, "failed", error=error)
            raise error
        spec.loader = _CapturedSourceLoader(fullname, str(expected), self)
        return spec


class _CapturedSourceLoader(importlib.machinery.SourceFileLoader):
    def __init__(self, fullname: str, path: str, attestor: Attestor):
        super().__init__(fullname, path)
        self.attestor = attestor

    def exec_module(self, module) -> None:
        raw = code = None
        try:
            raw = _source(self.path)
            code = compile(raw, self.path, "exec", dont_inherit=True, optimize=sys.flags.optimize)
            # The digest and execution refer to this SAME code object and buffer.
            exec(code, module.__dict__)
        except BaseException as exc:
            self.attestor.emit(self.name, "failed", raw, code, exc)
            raise
        self.attestor.emit(self.name, "loaded", raw, code)


def run(bootstrap_source: bytes, bootstrap_code) -> None:
    attestor = Attestor(Path(__file__).parent.parent, bootstrap_source, bootstrap_code)
    attestor.install()
    attestor.emit("app.runtime_attestation", "bootstrap_ready", bootstrap_source, bootstrap_code)
    import uvicorn

    # Same single-process serving contract; no eager F04 import or service action.
    # Preserve the removed CLI's proxy-header setting explicitly across versions.
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, proxy_headers=True)


if __name__ == "__main__":
    # The unit supplies the exact buffer/code object it compiled, not a later file hash.
    run(_BOOTSTRAP_SOURCE, _BOOTSTRAP_CODE)
