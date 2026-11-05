"""Deterministic tests for scripts.ci_browser_dependency_inputs.

These tests never run apt, network operations, installers, browsers or any
subprocess: they exercise the pure helpers only with explicitly supplied bytes
and mappings, and assert the fail-closed, no-echo behavior of every record.
"""

import hashlib
import inspect
import json

import scripts.ci_browser_dependency_inputs as module
from scripts.ci_browser_dependency_inputs import (
    summarize_apt_inputs,
    summarize_playwright_inputs,
)

FULL_APT = (
    b"APT_RETRIES='1'\n"
    b"APT_HTTP_TIMEOUT='15'\n"
    b"APT_HTTPS_TIMEOUT='30'\n"
    b"APT_HTTP_DL_LIMIT='0'\n"
    b"APT_HTTPS_DL_LIMIT='65536'\n"
)
ALL_FIELDS = {
    "APT_RETRIES": 1,
    "APT_HTTP_TIMEOUT": 15,
    "APT_HTTPS_TIMEOUT": 30,
    "APT_HTTP_DL_LIMIT": 0,
    "APT_HTTPS_DL_LIMIT": 65536,
}
SECRET_PROXY = "http://user:hunter2@example.internal:8080"
APT_CONFIG_PATH = "/etc/apt/apt.conf.d/99-private-bottleneck"
ALL_PROXIES_ABSENT = {
    "HTTP_PROXY": False,
    "HTTPS_PROXY": False,
    "ALL_PROXY": False,
    "http_proxy": False,
    "https_proxy": False,
    "all_proxy": False,
}

METADATA_V1 = (
    b"Metadata-Version: 2.1\nName: playwright\nVersion: 1.64.1\n"
    b"Summary: recovered driver bundle\n"
)
DRIVER_JSON_V1 = b'{"name": "playwright", "version": "1.64.1", "bin": {"node": "node"}}'
BUNDLE = b"\x7fELF-fake-core-bundle-\x00\x01"
REFERENCE_CORE_BUNDLE_SHA256 = (
    "829521b67ed7be90c7d6d6098ff39f2241562d47e4ad7ccab13710924a56001d"
)


def test_apt_maximum_sized_decimal_fails_without_integer_conversion_exception():
    result = summarize_apt_inputs(b"APT_RETRIES='" + b"9" * 5000 + b"'\n", {})
    assert result["available"] is False
    assert result["unavailable_reason"] == "VALUE_OUT_OF_RANGE"


def test_driver_json_recursion_failure_is_unavailable(monkeypatch):
    def recursion_failure(*_args, **_kwargs):
        raise RecursionError("untrusted input is not echoed")
    monkeypatch.setattr(module.json, "loads", recursion_failure)
    result = summarize_playwright_inputs(METADATA_V1, DRIVER_JSON_V1, BUNDLE)
    assert result["available"] is False
    assert result["unavailable_reason"] == "JSON_PARSE_ERROR"


def _assert_apt_failed_closed(result, reason):
    assert result["kind"] == "apt_dependency_inputs"
    assert result["available"] is False
    assert result["unavailable_reason"] == reason
    assert result["observations"] is None
    assert result["absent_fields"] is None
    assert result["proxy_present"] is None
    assert result["apt_config_present"] is None
    assert result["authoritative"] is False


def _assert_playwright_failed_closed(result, reason):
    assert result["kind"] == "playwright_dependency_inputs"
    assert result["available"] is False
    assert result["unavailable_reason"] == reason
    assert result["observed_version"] is None
    assert result["input_sha256"] is None
    assert result["authoritative"] is False


# ---------------------------------------------------------------- apt inputs


def test_apt_observes_all_selected_fields():
    result = summarize_apt_inputs(FULL_APT, {})
    assert result["available"] is True
    assert result["unavailable_reason"] is None
    assert result["observations"] == ALL_FIELDS
    assert result["absent_fields"] == []
    assert json.dumps(result)


def test_apt_explicit_zero_is_distinct_from_absent():
    result = summarize_apt_inputs(b"APT_HTTP_DL_LIMIT='0'\n", {})
    assert result["observations"] == {"APT_HTTP_DL_LIMIT": 0}
    assert "APT_HTTP_DL_LIMIT" not in result["absent_fields"]
    assert "APT_RETRIES" in result["absent_fields"]


def test_apt_missing_fields_listed_absent_never_zero():
    result = summarize_apt_inputs(b"APT_RETRIES='3'\n", {})
    assert result["observations"] == {"APT_RETRIES": 3}
    assert result["absent_fields"] == [
        "APT_HTTP_TIMEOUT",
        "APT_HTTPS_TIMEOUT",
        "APT_HTTP_DL_LIMIT",
        "APT_HTTPS_DL_LIMIT",
    ]
    assert all(name not in result["observations"] for name in result["absent_fields"])


def test_apt_empty_input_reports_all_fields_absent():
    result = summarize_apt_inputs(b"", {})
    assert result["available"] is True
    assert result["observations"] == {}
    assert sorted(result["absent_fields"]) == sorted(ALL_FIELDS)


def test_apt_boundary_value_observed():
    result = summarize_apt_inputs(b"APT_RETRIES='2147483647'\n", {})
    assert result["observations"] == {"APT_RETRIES": 2147483647}


def test_apt_exact_limit_accepted():
    raw = b"APT_RETRIES='1'\n" + b"\n" * (8192 - 16)
    assert len(raw) == 8192
    result = summarize_apt_inputs(raw, {})
    assert result["observations"] == {"APT_RETRIES": 1}
    assert result["input_bytes"] == 8192


def test_apt_duplicate_field_fails_closed():
    _assert_apt_failed_closed(
        summarize_apt_inputs(b"APT_RETRIES='1'\nAPT_RETRIES='2'\n", {}),
        "DUPLICATE_FIELD",
    )


def test_apt_unknown_name_fails_closed_without_echo():
    raw = b"APT_SECRET_TUNNEL='7'\n"
    result = summarize_apt_inputs(raw, {})
    _assert_apt_failed_closed(result, "UNKNOWN_FIELD")
    assert "APT_SECRET_TUNNEL" not in json.dumps(result)


def test_apt_malformed_lines_fail_closed():
    for raw in (
        b"APT_RETRIES=1\n",
        b"APT_RETRIES='x'\n",
        b"APT_RETRIES=''\n",
        b"apt_retries='1'\n",
        b"APT_RETRIES='1' extra\n",
        b"APT_RETRIES=\"1\"\n",
    ):
        _assert_apt_failed_closed(summarize_apt_inputs(raw, {}), "MALFORMED_LINE")


def test_apt_negative_and_padded_values_fail_closed():
    _assert_apt_failed_closed(
        summarize_apt_inputs(b"APT_RETRIES='-1'\n", {}), "MALFORMED_LINE")
    _assert_apt_failed_closed(
        summarize_apt_inputs(b"APT_RETRIES=' 1'\n", {}), "MALFORMED_LINE")


def test_apt_out_of_range_value_fails_closed():
    _assert_apt_failed_closed(
        summarize_apt_inputs(b"APT_RETRIES='2147483648'\n", {}), "VALUE_OUT_OF_RANGE")


def test_apt_oversize_input_fails_closed():
    _assert_apt_failed_closed(summarize_apt_inputs(b"x" * 8193, {}), "INPUT_OVERSIZE")


def test_apt_non_ascii_input_fails_closed():
    raw = "APT_RETRIES='1é'\n".encode("utf-8")
    _assert_apt_failed_closed(summarize_apt_inputs(raw, {}), "NON_ASCII_INPUT")


def test_apt_partial_parse_never_returns_partial_fields():
    raw = b"APT_RETRIES='1'\nAPT_HTTP_TIMEOUT='15'\nbogus\n"
    _assert_apt_failed_closed(summarize_apt_inputs(raw, {}), "MALFORMED_LINE")


def test_apt_non_bytes_input_fails_closed():
    _assert_apt_failed_closed(
        summarize_apt_inputs("APT_RETRIES='1'\n", {}), "INPUT_TYPE_INVALID")


def test_apt_invalid_environment_fails_closed():
    for env in (None, "HTTP_PROXY=1", ["HTTP_PROXY"]):
        _assert_apt_failed_closed(
            summarize_apt_inputs(FULL_APT, env), "ENVIRONMENT_TYPE_INVALID")


def test_apt_proxy_and_apt_config_presence_booleans_only():
    env = {
        "HTTP_PROXY": SECRET_PROXY,
        "https_proxy": SECRET_PROXY,
        "APT_CONFIG": APT_CONFIG_PATH,
    }
    result = summarize_apt_inputs(FULL_APT, env)
    assert result["proxy_present"] == {
        "HTTP_PROXY": True,
        "HTTPS_PROXY": False,
        "ALL_PROXY": False,
        "http_proxy": False,
        "https_proxy": True,
        "all_proxy": False,
    }
    assert result["apt_config_present"] is True
    serialized = json.dumps(result)
    for secret in (SECRET_PROXY, "hunter2", "example.internal", "user:",
                   APT_CONFIG_PATH, "99-private"):
        assert secret not in serialized


def test_apt_environment_without_proxies_stays_value_free():
    result = summarize_apt_inputs(FULL_APT, {"PATH": "/usr/bin:/sbin"})
    assert result["proxy_present"] == ALL_PROXIES_ABSENT
    assert result["apt_config_present"] is False
    assert "/usr/bin" not in json.dumps(result)


def test_apt_record_is_explicitly_diagnostic():
    result = summarize_apt_inputs(FULL_APT, {})
    assert result["diagnostic"] is True
    assert result["authoritative"] is False
    joined = " ".join(result["notes"])
    assert "not authoritative" in joined
    assert "historical runtime" in joined


def test_apt_inputs_are_not_mutated():
    raw = b"APT_RETRIES='1'\n"
    env = {"HTTP_PROXY": SECRET_PROXY, "APT_CONFIG": APT_CONFIG_PATH}
    summarize_apt_inputs(raw, env)
    assert raw == b"APT_RETRIES='1'\n"
    assert env == {"HTTP_PROXY": SECRET_PROXY, "APT_CONFIG": APT_CONFIG_PATH}


def test_apt_repeated_calls_are_independent():
    first = summarize_apt_inputs(FULL_APT, {})
    second = summarize_apt_inputs(FULL_APT, {})
    assert first == second
    first["observations"]["APT_RETRIES"] = 999
    assert second["observations"]["APT_RETRIES"] == 1


def test_apt_bytearray_input_accepted():
    result = summarize_apt_inputs(bytearray(FULL_APT), {})
    assert result["observations"] == ALL_FIELDS


# ---------------------------------------------------- playwright driver inputs


def test_playwright_observed_version_and_exact_digests():
    result = summarize_playwright_inputs(METADATA_V1, DRIVER_JSON_V1, BUNDLE)
    assert result["available"] is True
    assert result["unavailable_reason"] is None
    assert result["observed_version"] == "1.64.1"
    assert result["input_bytes"] == {
        "metadata": len(METADATA_V1),
        "driver_package_json": len(DRIVER_JSON_V1),
        "driver_bundle": len(BUNDLE),
    }
    assert result["input_sha256"] == {
        "metadata": hashlib.sha256(METADATA_V1).hexdigest(),
        "driver_package_json": hashlib.sha256(DRIVER_JSON_V1).hexdigest(),
        "driver_bundle": hashlib.sha256(BUNDLE).hexdigest(),
    }


def test_playwright_different_versions_remain_separate_non_authoritative_observations():
    result = summarize_playwright_inputs(
        b"Version: 1.64.1\n", b'{"version": "1.62.0"}', BUNDLE)
    assert result["available"] is True
    assert result["observed_version"] == "1.64.1"
    assert result["driver_version"] == "1.62.0"
    assert result["version_relationship"] == "different"
    assert result["authoritative"] is False


def test_official_python_wheel_can_contain_a_distinct_bundled_driver_version():
    result = summarize_playwright_inputs(
        b"Version: 1.64.1\n", b'{"version":"1.64.0-beta-1791568591000"}', BUNDLE)
    assert result["available"] is True
    assert result["driver_version"] == "1.64.0-beta-1791568591000"
    assert result["version_relationship"] == "different"
    assert result["authoritative"] is False


def test_playwright_duplicate_metadata_version_fails_closed():
    result = summarize_playwright_inputs(
        b"Version: 1.64.1\nVersion: 1.64.1\n", DRIVER_JSON_V1, BUNDLE)
    _assert_playwright_failed_closed(result, "METADATA_VERSION_DUPLICATE")


def test_playwright_missing_metadata_version_fails_closed():
    metadata = b"Metadata-Version: 2.1\nName: playwright\n"
    result = summarize_playwright_inputs(metadata, DRIVER_JSON_V1, BUNDLE)
    _assert_playwright_failed_closed(result, "METADATA_VERSION_MISSING")


def test_playwright_malformed_metadata_version_fails_closed_without_echo():
    bad_versions = (
        b"Version: 1.64.1 beta!!\n",
        b"Version: \n",
        b"Version: " + b"1" * 65 + b"\n",
        "Version: 1.64.1–1\n".encode("utf-8"),
        b"Version: 01.64.1\n",
    )
    for tail in bad_versions:
        result = summarize_playwright_inputs(
            b"Name: playwright\n" + tail, DRIVER_JSON_V1, BUNDLE)
        _assert_playwright_failed_closed(result, "METADATA_VERSION_MALFORMED")
        assert "beta!!" not in json.dumps(result)


def test_playwright_missing_json_version_fails_closed():
    result = summarize_playwright_inputs(
        METADATA_V1, b'{"name": "playwright"}', BUNDLE)
    _assert_playwright_failed_closed(result, "JSON_VERSION_MISSING")


def test_playwright_duplicate_json_version_fails_closed():
    driver = b'{"version": "1.64.1", "version": "1.64.1"}'
    result = summarize_playwright_inputs(METADATA_V1, driver, BUNDLE)
    _assert_playwright_failed_closed(result, "JSON_VERSION_DUPLICATE")


def test_playwright_any_duplicate_json_key_fails_closed():
    driver = b'{"name": "playwright", "name": "playwright", "version": "1.64.1"}'
    result = summarize_playwright_inputs(METADATA_V1, driver, BUNDLE)
    _assert_playwright_failed_closed(result, "JSON_DUPLICATE_KEY")


def test_playwright_nested_duplicate_json_key_fails_closed():
    driver = b'{"version": "1.64.1", "bin": {"node": "n", "node": "n2"}}'
    result = summarize_playwright_inputs(METADATA_V1, driver, BUNDLE)
    _assert_playwright_failed_closed(result, "JSON_DUPLICATE_KEY")


def test_playwright_broken_json_fails_closed():
    result = summarize_playwright_inputs(METADATA_V1, b'{"version": 1.64.1}', BUNDLE)
    _assert_playwright_failed_closed(result, "JSON_PARSE_ERROR")


def test_playwright_non_utf8_json_fails_closed():
    driver = b'{"version": "1.64.1\xff"}'
    result = summarize_playwright_inputs(METADATA_V1, driver, BUNDLE)
    _assert_playwright_failed_closed(result, "JSON_PARSE_ERROR")


def test_playwright_non_object_json_fails_closed():
    result = summarize_playwright_inputs(METADATA_V1, b'["1.64.1"]', BUNDLE)
    _assert_playwright_failed_closed(result, "JSON_PARSE_ERROR")


def test_playwright_non_string_or_malformed_json_version_fails_closed():
    for driver in (b'{"version": 1641}', b'{"version": "beta"}', b'{"version": null}'):
        result = summarize_playwright_inputs(METADATA_V1, driver, BUNDLE)
        _assert_playwright_failed_closed(result, "JSON_VERSION_MALFORMED")


def test_playwright_oversize_inputs_fail_closed():
    result = summarize_playwright_inputs(b"V" * 65537, DRIVER_JSON_V1, BUNDLE)
    _assert_playwright_failed_closed(result, "METADATA_OVERSIZE")
    result = summarize_playwright_inputs(METADATA_V1, b"{" * 65537, BUNDLE)
    _assert_playwright_failed_closed(result, "DRIVER_PACKAGE_JSON_OVERSIZE")
    result = summarize_playwright_inputs(
        METADATA_V1, DRIVER_JSON_V1, b"\0" * (8 * 1024 * 1024 + 1))
    _assert_playwright_failed_closed(result, "DRIVER_BUNDLE_OVERSIZE")


def test_playwright_max_sizes_accepted():
    big_metadata = b"Version: 1.64.1\n" + b"#" * (65536 - 16)
    big_json = b'{"version": "1.64.1"}' + b" " * (65536 - 21)
    assert len(big_metadata) == 65536 and len(big_json) == 65536
    result = summarize_playwright_inputs(big_metadata, big_json, b"\0" * (8 * 1024 * 1024))
    assert result["available"] is True
    assert result["observed_version"] == "1.64.1"


def test_playwright_version_length_bound():
    longest = "1.0-" + "a" * 60
    assert len(longest) == 64
    metadata = ("Version: %s\n" % longest).encode("ascii")
    driver = json.dumps({"version": longest}).encode("ascii")
    result = summarize_playwright_inputs(metadata, driver, BUNDLE)
    assert result["available"] is True
    assert result["observed_version"] == longest
    too_long = longest + "a"
    result = summarize_playwright_inputs(
        ("Version: %s\n" % too_long).encode("ascii"),
        json.dumps({"version": too_long}).encode("ascii"),
        BUNDLE,
    )
    _assert_playwright_failed_closed(result, "METADATA_VERSION_MALFORMED")


def test_playwright_reference_digest_is_context_not_allowlist():
    result = summarize_playwright_inputs(
        b"Version: 1.62.0\n", b'{"version": "1.62.0"}', BUNDLE)
    assert result["available"] is True
    assert result["observed_version"] == "1.62.0"
    assert REFERENCE_CORE_BUNDLE_SHA256 not in json.dumps(result)


def test_playwright_record_is_explicitly_diagnostic():
    result = summarize_playwright_inputs(METADATA_V1, DRIVER_JSON_V1, BUNDLE)
    assert result["diagnostic"] is True
    assert result["authoritative"] is False
    joined = " ".join(result["notes"])
    assert "not establish" in joined
    assert "authenticity" in joined


def test_playwright_inputs_are_not_mutated():
    summarize_playwright_inputs(METADATA_V1, DRIVER_JSON_V1, BUNDLE)
    assert METADATA_V1.endswith(b"recovered driver bundle\n")
    assert DRIVER_JSON_V1.startswith(b'{"name": "playwright"')
    assert BUNDLE.startswith(b"\x7fELF")


def test_playwright_non_bytes_input_fails_closed():
    result = summarize_playwright_inputs("Version: 1.64.1\n", DRIVER_JSON_V1, BUNDLE)
    _assert_playwright_failed_closed(result, "INPUT_TYPE_INVALID")
    result = summarize_playwright_inputs(METADATA_V1, None, BUNDLE)
    _assert_playwright_failed_closed(result, "INPUT_TYPE_INVALID")
    result = summarize_playwright_inputs(METADATA_V1, DRIVER_JSON_V1, 12345)
    _assert_playwright_failed_closed(result, "INPUT_TYPE_INVALID")


def test_playwright_bytearray_inputs_accepted():
    result = summarize_playwright_inputs(
        bytearray(METADATA_V1), bytearray(DRIVER_JSON_V1), bytearray(BUNDLE))
    assert result["available"] is True
    assert result["observed_version"] == "1.64.1"


def test_all_records_are_json_serializable():
    cases = [
        summarize_apt_inputs(FULL_APT, {"HTTP_PROXY": SECRET_PROXY}),
        summarize_apt_inputs(b"bogus\n", {}),
        summarize_playwright_inputs(METADATA_V1, DRIVER_JSON_V1, BUNDLE),
        summarize_playwright_inputs(b"Version: nope\n", b"{}", BUNDLE),
    ]
    for case in cases:
        assert isinstance(json.dumps(case), str)


# ------------------------------------------------------------ purity of target


_FORBIDDEN_TOKENS = (
    "subprocess",
    "popen",
    "socket",
    "urllib",
    "http.client",
    "requests",
    "shutil",
    "pathlib",
    "tempfile",
    "import os",
    "os.open",
    "os.system",
    "open(",
    "eval(",
    "exec(",
    "run(",
)


def test_module_uses_no_io_process_or_network_apis():
    source = inspect.getsource(module).lower()
    for token in _FORBIDDEN_TOKENS:
        assert token not in source, token
    for attribute in ("os", "subprocess", "socket", "shutil", "pathlib", "tempfile"):
        assert not hasattr(module, attribute)


def test_module_exports_only_the_two_helpers():
    assert sorted(module.__all__) == [
        "summarize_apt_inputs",
        "summarize_playwright_inputs",
    ]
