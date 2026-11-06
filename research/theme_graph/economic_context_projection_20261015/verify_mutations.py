"""Read-only, in-memory fault injection for the native economic context view."""
from pathlib import Path
import hashlib
import json
import sys
import types
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tests import test_gmi_native_economic_context as tests


def main():
    path = ROOT / "engine/theme_graph/economic_context.py"
    source = path.read_text()
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    def fixture():
        return tests.ready.__wrapped__(tests.sample.__wrapped__())
    def fields():
        tests.test_all_needed_fields_are_granted_before_any_artifact_read(fixture(), "subject_id")
    def pin():
        tests.test_generation_change_prevents_stale_positive(fixture(), 2)
    def clock():
        tests.test_no_fact_clock_replaced_by_publication_or_generation(fixture())
    def graph():
        tests.test_no_implicit_supplier_edge_hypothesis_forecast_or_magnitude(fixture())
    mutations = [
        ("removed_field_permission_gate", "if not REQUIRED_FIELDS <= admission.allowed_fields:",
         "if False and not REQUIRED_FIELDS <= admission.allowed_fields:", fields),
        ("removed_admission_pin", "expected_admission=admission,", "expected_admission=None,", pin),
        ("collapsed_fact_known_clock", '\"fact_known_at\": admission.known_at,',
         '\"fact_known_at\": timing[\"known_at\"],', clock),
        ("invented_graph_edge", '\"legacy_theme_graph_edge\": None,',
         '\"legacy_theme_graph_edge\": \"invented:edge\",', graph),
    ]
    rows = []
    for name, old, replacement, verify in mutations:
        verify()
        if source.count(old) != 1:
            raise AssertionError("MUTATION_PREIMAGE_CHANGED:" + name)
        module = types.ModuleType("isolated_" + name)
        exec(compile(source.replace(old, replacement, 1), name, "exec"), module.__dict__)
        with patch.object(tests.context, "read_economic_context", module.read_economic_context):
            try:
                verify()
            except AssertionError:
                rows.append({"mutation": name, "control": "passed", "fault": "detected"})
            else:
                raise AssertionError("UNDETECTED_MUTATION:" + name)
    if hashlib.sha256(path.read_bytes()).hexdigest() != before:
        raise AssertionError("SOURCE_CHANGED")
    print(json.dumps({"scope": "in_memory_fault_injection_only", "module_sha256": before,
                      "source_unchanged": True, "results": rows}, indent=2))


if __name__ == "__main__":
    main()
