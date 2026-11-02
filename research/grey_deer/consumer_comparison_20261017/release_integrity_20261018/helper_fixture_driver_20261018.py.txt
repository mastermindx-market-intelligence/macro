"""Execute the unchanged standalone fixture test bodies without optional pytest.

This driver deliberately never invokes the five app-import tests. Native pytest
remains a separate required gate; results identify this runner explicitly.
"""
import ast
import hashlib
import itertools
import json
from pathlib import Path
import sys
import tempfile
import time
import traceback
from types import SimpleNamespace

path = Path(sys.argv[1]).resolve()
pattern = sys.argv[2]
output = Path(sys.argv[3])
source = path.read_bytes()
tree = ast.parse(source, filename=str(path))
tree.body = [node for node in tree.body if not (
    isinstance(node, ast.Import) and any(alias.name == "pytest" for alias in node.names)
)]

def parametrize(names, values):
    def decorate(fn):
        fn._fixture_params = getattr(fn, "_fixture_params", []) + [(names, values)]
        return fn
    return decorate

def fail(reason):
    raise AssertionError(reason)

def skip(reason):
    raise RuntimeError("SKIP (not a passing test): " + reason)

namespace = {"__file__": str(path), "pytest": SimpleNamespace(
    mark=SimpleNamespace(parametrize=parametrize), fail=fail, skip=skip)}
exec(compile(tree, str(path), "exec"), namespace)
rows = []
excluded = {
    "test_deployed_sha_prefers_valid_marker",
    "test_deployed_sha_rejects_marker_and_uses_full_local_head",
    "test_deployed_sha_fails_closed_when_both_sources_are_invalid",
    "test_health_exposes_exact_full_commit",
    "test_non_serve_only_startup_fails_when_scheduler_is_unavailable",
}
for name, fn in list(namespace.items()):
    if not name.startswith("test_") or name in excluded or (pattern != "all" and pattern not in name):
        continue
    params = getattr(fn, "_fixture_params", [])
    combos = itertools.product(*(values for _, values in params)) if params else [()]
    for values in combos:
        args = dict(zip((key for key, _ in params), values))
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="rr-deploy-fixture-") as tmp:
            if "tmp_path" in fn.__code__.co_varnames[:fn.__code__.co_argcount]:
                args["tmp_path"] = Path(tmp)
            result = {"test": name, "parameters": {key: val for key, val in args.items() if key != "tmp_path"}}
            try:
                fn(**args)
                result["status"] = "passed"
            except Exception as exc:
                result.update(status="failed", error=type(exc).__name__, message=str(exc), traceback=traceback.format_exc())
            result["seconds"] = round(time.monotonic() - started, 3)
            rows.append(result)
            print(name, result["parameters"], result["status"], result["seconds"], flush=True)
helper = namespace["DEPLOY_SCRIPT"].read_bytes()
receipt = {
    "runner": "stdlib AST loader; exact standalone fixture test bodies, no pytest/app imports",
    "test_source_sha256": hashlib.sha256(source).hexdigest(),
    "helper_sha256": hashlib.sha256(helper).hexdigest(),
    "app_import_tests_executed": False, "network_or_production_calls": False,
    "cases": rows, "passed": sum(row["status"] == "passed" for row in rows),
    "failed": sum(row["status"] == "failed" for row in rows),
}
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({key: receipt[key] for key in ("helper_sha256", "passed", "failed")}))
sys.exit(1 if receipt["failed"] else 0)
