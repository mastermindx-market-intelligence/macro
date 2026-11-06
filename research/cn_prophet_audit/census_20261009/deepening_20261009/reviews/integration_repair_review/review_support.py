#!/usr/bin/env python3
"""Independent review support: exact native bytes, no shared checkout imports."""
from hashlib import sha256
from pathlib import Path
from types import ModuleType
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DEEP = HERE.parents[1]
PIN = "3d90aad6d83152dfeeaf8345bc995826ac9d3139"
ORIGINAL_LAB_MANIFEST = "d755a012d80469c241a554252e61bee88e604eb445ce7ca03ec1e2eecfdbc8b6"
ORIGINAL_REVIEW_MANIFEST = "78fcfa3c271d214c751a40220dc92e44cec67409eb49fbe7421b9c22a32698b6"
NATIVE_BUNDLE = "2c139c0fef2c83296374069aed3338ccc28802bbf535d75054176384ec9ec829"


def read(path):
    return json.loads(Path(path).read_text())


def hash_file(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def capture(operation):
    try:
        value = operation()
        return {"outcome": "accepted", "value": value}
    except Exception as exc:
        return {"outcome": "exception", "exception_class": type(exc).__name__,
                "reason": getattr(exc, "reason", str(exc))}


def verify_manifest(path, expected):
    path = Path(path)
    assert hash_file(path) == expected, ("manifest changed", str(path))
    manifest = read(path)
    identities = {path.name: expected}
    for entry in manifest["files"]:
        name = entry["path"]
        assert hash_file(path.parent / name) == entry["sha256"], ("payload changed", str(path), name)
        if "bytes" in entry:
            assert (path.parent / name).stat().st_size == entry["bytes"]
        identities[name] = entry["sha256"]
    return manifest, identities


def unchanged_originals():
    lab = DEEP / "integration_lab"
    review = HERE.parent / "integration_review"
    _, lab_files = verify_manifest(lab / "INTEGRATION_MANIFEST.json", ORIGINAL_LAB_MANIFEST)
    _, review_files = verify_manifest(review / "MANIFEST.json", ORIGINAL_REVIEW_MANIFEST)
    return {"integration_lab": lab_files, "integration_review": review_files}


def load_native(bundle_path=None):
    bundle_path = Path(bundle_path) if bundle_path else HERE.parent / "integration_review/native_source_bundle.json"
    assert hash_file(bundle_path) == NATIVE_BUNDLE
    bundle = read(bundle_path)
    assert bundle["source_sha"] == PIN
    for path, item in bundle["files"].items():
        raw = item["code"].encode()
        assert sha256(raw).hexdigest() == item["sha256"], path
        assert len(raw) == item["bytes"], path
    for name in ("lib", "engine", "engine.prophet_live", "scripts"):
        module = ModuleType(name)
        module.__path__ = []
        sys.modules[name] = module
        if "." in name:
            parent, child = name.rsplit(".", 1)
            setattr(sys.modules[parent], child, module)
    modules = {}
    order = ["lib/exchange_holidays.py", "lib/cn_calendar.py",
             "engine/prophet_live/interval.py", "engine/prophet_live/live_states.py",
             "engine/prophet_live/cn_clock.py", "engine/prophet_live/cn_states.py",
             "engine/prophet_live/cn_reconcile.py", "engine/prophet_live/r2io.py",
             "scripts/reconcile_cn_live.py"]
    for path in order:
        name = path[:-3].replace("/", ".")
        module = ModuleType(name)
        module.__file__ = str(HERE / "_virtual_pinned_source" / path)
        module.__package__ = name.rsplit(".", 1)[0]
        sys.modules[name] = module
        parent, child = name.rsplit(".", 1)
        setattr(sys.modules[parent], child, module)
        exec(compile(bundle["files"][path]["code"], module.__file__, "exec"), module.__dict__)
        modules[path] = module
    return modules, {path: row["sha256"] for path, row in bundle["files"].items()}


def load_subject(path):
    path = Path(path)
    module = ModuleType("integration_repair_under_independent_review")
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), module.__file__, "exec"), module.__dict__)
    return module
