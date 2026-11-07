"""Native v1 envelope and bounded CLI; no authenticated consumer is implied."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import jsonschema
import pytest

from tests.test_factor_atlas_read import IDS, case, run

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "contracts/factor_atlas_read.v1.schema.json"
CLI = ROOT / "scripts/factor_atlas_read.py"


def validator():
    assert SCHEMA.is_file(), "native Factor Atlas v1 schema is missing"
    value = json.loads(SCHEMA.read_text())
    jsonschema.Draft202012Validator.check_schema(value)
    return jsonschema.Draft202012Validator(value, format_checker=jsonschema.FormatChecker())


def test_ready_and_unavailable_outputs_match_the_native_contract():
    request, inputs = case()
    validator().validate(run(request, inputs))
    inputs["prices"][IDS[0]]["values"]["2026-01-29"] = None
    validator().validate(run(request, inputs))


@pytest.mark.parametrize("path,value", [
    (("authority", "may_trade"), True), (("authority", "may_publish"), True),
    (("schema",), "factor_read_model.v0"), (("release_state",), "PROVEN_LIVE"),
    (("points", 0, "return"), "0.0"), (("input_digest",), "unverified"),
    (("points", 0, "return"), None), (("points", 0, "coverage", "weight"), 50),
])
def test_envelope_rejects_mutated_claims(path, value):
    request, inputs = case()
    output = run(request, inputs)
    obj = output
    for key in path[:-1]:
        obj = obj[key]
    obj[path[-1]] = value
    with pytest.raises(jsonschema.ValidationError):
        validator().validate(output)


def test_no_escalation_capability_is_explicit():
    request, inputs = case()
    assert run(request, inputs)["authority"]["may_escalate"] is False


def invoke(tmp_path, text, seed="1"):
    assert CLI.is_file(), "native Factor Atlas CLI is missing"
    source = tmp_path / ("request-" + seed + ".json")
    source.write_text(text)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    env = {**os.environ, "PYTHONHASHSEED": seed}
    process = subprocess.run([sys.executable, str(CLI), "--input", str(source)],
                             cwd=tmp_path, env=env, text=True, capture_output=True, timeout=30)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    return process


def test_cli_recomputes_identical_bytes_in_distinct_processes(tmp_path):
    request, inputs = case()
    text = json.dumps({"request": request, "owner_inputs": inputs})
    first, second = invoke(tmp_path, text, "1"), invoke(tmp_path, text, "777")
    assert first.returncode == second.returncode == 0, first.stderr + second.stderr
    assert first.stdout == second.stdout
    result = json.loads(first.stdout)
    validator().validate(result)
    assert result["release_state"] == "CANDIDATE_NOT_ADMITTED"


@pytest.mark.parametrize("text", [
    '{"request": {}, "request": {}, "owner_inputs": {}}',
    '{"request": {}, "owner_inputs": {"values": NaN}}',
    '{"request": {}, "owner_inputs": {}, "override_authority": true}',
    '[]',
])
def test_cli_refuses_ambiguous_or_nonfinite_input(tmp_path, text):
    result = invoke(tmp_path, text)
    assert result.returncode == 2
    assert result.stdout == ""
    assert "factor_atlas:" in result.stderr
    assert "Traceback" not in result.stderr


def test_output_integrity_check_rejects_a_changed_number():
    from scripts.factor_atlas_read import validate_output
    request, inputs = case()
    output = run(request, inputs)
    output["points"][0]["return"] = 0.123
    with pytest.raises(ValueError, match="digest"):
        validate_output(output)


def test_self_consistent_digest_does_not_override_request_identity():
    from engine.factor_atlas_read import canonical_bytes
    from scripts.factor_atlas_read import validate_output
    request, inputs = case()
    output = run(request, inputs)
    output["basket_id"] = "different-basket"
    del output["result_digest"]
    output["result_digest"] = hashlib.sha256(canonical_bytes(output)).hexdigest()
    with pytest.raises(ValueError, match="request"):
        validate_output(output)
