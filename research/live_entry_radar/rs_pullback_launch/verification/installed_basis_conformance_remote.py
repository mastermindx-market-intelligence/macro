"""Run the accepted installed v2 pair and the repaired HTTP framing path.

Executed on the existing host only after the producer merge is deployed. All
transport and market inputs are synthetic; writes are confined to temporary
directories. The existing committed conformance harness remains the owner.
"""
import argparse
import contextlib
import datetime
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import time
import urllib.request
from unittest.mock import patch
from urllib.parse import urlsplit, urlunsplit


EXPECTED = {
    "/opt/terminal/ingest/backfill_intraday.py": "0d0dff7facf60a39a9c504f8fbb63f62226da7675ed6296207dad03bcbacdf7f",
    "/opt/terminal/ingest/intraday_capture.py": "57708686d607e2a16ab3f374081f2810778d9d38a6ddaba2b735b3f044fc7969",
    "/opt/macro/engine/entry_radar/replay/rs_pullback_launch_data.py": "c7b3ea3fada013364c40c1cd041194ef30ff3f97f098b5bbadda9dc246dd1820",
    "/opt/macro/engine/entry_radar/replay/terminal_minute_observations.py": "941f5412e81402f772c9c8d546228e1ee03c8a34322091de638344b5a7df023b",
    "/opt/macro/scripts/entry_radar_rs_pullback_source_retention_check.py": "86badb07b209c574508ec4e3fed225da5007dd4c27f0cee9d1723dce2354cc03",
    "/opt/macro/tests/test_entry_radar_rs_pullback_phase1.py": "25a01209db7ccb95036976722017b96c7d1df7629f8eaad9cfaf2ed4a56caf6c",
    "/opt/macro/tests/test_entry_radar_terminal_minute_observations.py": "7d924fe83b4182f8b160304757a26f670dc4f7ee10eb22039aff0de656ae36e6",
    "/opt/macro/research/live_entry_radar/rs_pullback_launch/PHASE1_ADMISSION_2026-10-07.json": "a4e00a5c191917dc8c64fb74ca3348827ab9bd47d9ad8a03a1130a50fde36e9f",
    "/opt/macro/research/live_entry_radar/rs_pullback_launch/SOURCE_RETENTION_CONFORMANCE_2026-10-07.json": "2b5b86eeba28d0a0ae7064e3cf680be7fe62bb61730fbee3aaa870db160fe27c",
    "/opt/macro/research/live_entry_radar/rs_pullback_launch/SOURCE_BASIS_DECLARATION_CONFORMANCE_2026-10-07.json": "8fbb51cc41e9acf7bb70be23cd4d86d030dfa15c42b38c2d1e3d9ff7aaa4ed49",
    "/opt/macro/research/live_entry_radar/rs_pullback_launch/SOURCE_RETENTION_READER_CONTRACT_2026-10-07.md": "7482f417154a1cc6ffee22fe22ccc6754d12c8b78f79760d5362341162fc6356",
}
MACRO_MERGE = "67c1d8155d9194825f6cb301967d6b1c1f91b433"
TERMINAL_MERGE = "e963eefb3ac1984008caae922d6f43bfafa9d827"
DUMMY_KEY = "SYNTHETIC_INSTALLED_FRAMING_NO_VENDOR"


def git(root, *args):
    return subprocess.check_output(
        ["/usr/bin/git", "--no-optional-locks", "-c", "core.fsmonitor=false",
         "-c", "log.showSignature=false", "-c", "protocol.allow=never", "-C", root, *args],
        text=True, timeout=30,
        env={"PATH": "/usr/bin:/bin", "LANG": "C", "GIT_OPTIONAL_LOCKS": "0",
             "GIT_TERMINAL_PROMPT": "0", "GIT_NO_LAZY_FETCH": "1",
             "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"},
    ).strip()


def hashes():
    return {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in EXPECTED}


def heads():
    return {
        "macro": git("/opt/macro", "rev-parse", "HEAD"),
        "terminal": git("/opt/terminal/.gitsrc", "rev-parse", "HEAD"),
    }


def shallow_state():
    result = {}
    for name, root in (("macro", "/opt/macro"), ("terminal", "/opt/terminal/.gitsrc")):
        value = git(root, "rev-parse", "--is-shallow-repository")
        assert value in ("true", "false"), "Unrecognized installed shallow state"
        result[name] = value == "true"
    return result


def nanoseconds_for_output(value):
    """Encode ns integers exactly at the JSON boundary; controls keep their types."""
    if isinstance(value, dict):
        return {key: str(child) if key.endswith("_ns") and type(child) is int
                else nanoseconds_for_output(child) for key, child in value.items()}
    if isinstance(value, list):
        return [nanoseconds_for_output(child) for child in value]
    return value


def forbidden(*args, **kwargs):
    raise AssertionError("Unpatched provider transport is forbidden in conformance")


class Socket:
    def __init__(self, wire):
        self.wire = wire

    def makefile(self, mode):
        return io.BytesIO(self.wire)


def response(body, short=False):
    wire = (b"HTTP/1.1 200 OK\r\nContent-Length: "
            + str(len(body) + (10 if short else 0)).encode()
            + b"\r\n\r\n" + body)
    result = http.client.HTTPResponse(Socket(wire))
    result.begin()
    return result


def framing_controls(namespace):
    producer_path = Path("/opt/terminal/ingest/backfill_intraday.py")
    with patch.dict(os.environ, {"POLYGON_API_KEY": DUMMY_KEY}):
        producer = namespace["load_module"]("installed_framing_producer", producer_path)
    capture = producer.capture_owner
    assert Path(producer.__file__).resolve() == producer_path
    assert Path(capture.__file__).resolve() == Path("/opt/terminal/ingest/intraday_capture.py")
    event_ms = (int(time.time() - 3600) // 60) * 60000
    controls = {}
    with tempfile.TemporaryDirectory(prefix="installed-basis-framing-") as temporary:
        with patch.object(producer.time, "sleep", lambda _: None), \
                patch.object(producer.urllib.request, "urlopen", forbidden):
            for case in ("complete_length", "short_first_page", "short_later_page"):
                root = Path(temporary) / case
                file = root / "SPY.1m.json"
                calls, responses, response_bodies = [], [], []

                def body(close=100.0):
                    return {"status": "OK", "adjusted": True, "results": [{
                        "t": event_ms, "o": 100, "h": 101, "l": 99,
                        "c": close, "v": 1.25,
                    }]}

                def invoke(transport):
                    with patch.object(producer, "INTRADAY", root), \
                            patch.object(producer, "_open_capture_request", transport), \
                            contextlib.redirect_stdout(io.StringIO()):
                        return producer.main([
                            "--capture-minutes", "--symbols", "SPY", "--tf", "1m",
                            "--workers", "1",
                        ])

                before = None
                if case == "short_later_page":
                    def baseline(request, *, timeout):
                        assert timeout == 45
                        return response(json.dumps(body()).encode())
                    assert invoke(baseline) == 0
                    before = capture.read_document(file)

                def transport(request, *, timeout):
                    assert timeout == 45
                    calls.append(request.full_url)
                    value = body(100.25 if before is not None else 100.0)
                    short = case != "complete_length"
                    if case == "short_later_page" and len(calls) == 1:
                        parts = urlsplit(request.full_url)
                        value["next_url"] = urlunsplit((
                            parts.scheme, parts.netloc, parts.path, "cursor=next", "",
                        ))
                        short = False
                    elif case == "short_later_page":
                        value["results"][0].update(t=event_ms + 60000, c=100.5)
                    raw_response = json.dumps(value).encode()
                    response_bodies.append(raw_response)
                    received = response(raw_response, short)
                    responses.append(received)
                    return received

                exit_code = invoke(transport)
                document = capture.read_document(file)
                envelope = capture.validate_envelope(document["minute_capture"], "SPY")
                payload = envelope["captures"][-1]["payload"]
                expected = {
                    "complete_length": (0, 1, "complete", 1, 1, True, None),
                    "short_first_page": (1, 5, "failed", 0, 0, False, "transport_exhausted"),
                    "short_later_page": (1, 6, "partial", 1, 1, False, "transport_exhausted"),
                }[case]
                actual = (exit_code, len(calls), payload["status"], len(payload["pages"]),
                          len(payload["observations"]), payload["chart_eligible"],
                          payload["failure_kind"])
                assert actual == expected, (case, actual)
                assert len(document["bars"]) == (0 if case == "short_first_page" else 1)
                assert responses[-1].length == (0 if case == "complete_length" else 10)
                if before is not None:
                    first_raw = response_bodies[0]
                    first_row = json.loads(first_raw)["results"][0]
                    assert first_raw != response_bodies[-1]
                    assert payload["pages"][0]["page_index"] == 0
                    assert payload["pages"][0]["response_sha256"] == hashlib.sha256(first_raw).hexdigest()
                    assert payload["pages"][0]["response_bytes"] == len(first_raw)
                    assert payload["observations"] == [{
                        "page_index": 0, "row_index": 0,
                        "event_start_utc_ms": event_ms, "event_end_utc_ms": event_ms + 60000,
                        "raw": first_row,
                    }]
                    assert {k: v for k, v in document.items() if k != "minute_capture"} == {
                        k: v for k, v in before.items() if k != "minute_capture"
                    }
                    assert envelope["captures"][0] == before["minute_capture"]["captures"][0]
                assert DUMMY_KEY.encode() not in file.read_bytes()
                controls[case] = {
                    "result": "PASS", "exit": exit_code, "requests": len(calls),
                    "capture_status": payload["status"], "failure_kind": payload["failure_kind"],
                    "pages": len(payload["pages"]), "observations": len(payload["observations"]),
                    "chart_eligible": payload["chart_eligible"],
                    "declared_remaining_bytes": responses[-1].length,
                    "prior_capture_and_chart_preserved": True if before is not None else None,
                    "exact_first_complete_page_and_observation_preserved": True if before is not None else None,
                }
    return controls


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-macro-head", required=True)
    parser.add_argument("--expected-terminal-head", required=True)
    args = parser.parse_args()
    expected_heads = {"macro": args.expected_macro_head, "terminal": args.expected_terminal_head}
    assert all(len(value) == 40 and all(c in "0123456789abcdef" for c in value)
               for value in expected_heads.values()), "Exact expected installed heads required"
    terminal_merge = TERMINAL_MERGE
    assert hashes() == EXPECTED, "Installed source differs from the reviewed v2 pair"
    before_heads = heads()
    assert before_heads == expected_heads, "Installed heads differ from root-supplied exact heads"
    before_shallow = shallow_state()
    # Host history may omit older objects. This script makes NO ancestry claim;
    # the single-attempt M2 wrapper must retain positive lineage before SSH.
    started = time.time_ns()
    with contextlib.redirect_stdout(io.StringIO()), \
            patch.dict(os.environ, {"POLYGON_API_KEY": DUMMY_KEY}), \
            patch.object(urllib.request, "urlopen", forbidden):
        namespace = runpy.run_path(
            "/opt/macro/scripts/entry_radar_rs_pullback_source_retention_check.py",
            run_name="installed_basis_conformance",
        )
        proof = namespace["run"](Path("/opt/terminal"))
        assert proof["result"] == "PASS" and len(proof["checks"]) == 19
        assert all(value is True for value in proof["checks"].values())
        framing = framing_controls(namespace)
    completed = time.time_ns()
    assert hashes() == EXPECTED, "Installed source moved during conformance"
    after_heads = heads()
    assert after_heads == expected_heads, "Installed heads moved during conformance"
    after_shallow = shallow_state()
    record = {
        "schema": "mastermind.rs_pullback_launch.installed_basis_conformance.v1",
        "observed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "execution_started_at_utc_ns": started,
        "execution_completed_at_utc_ns": completed,
        "macro_merge_commit": MACRO_MERGE, "terminal_merge_commit": terminal_merge,
        "expected_installed_heads": expected_heads,
        "installed_heads_before": before_heads, "installed_heads_after": after_heads,
        "installed_shallow_before": before_shallow, "installed_shallow_after": after_shallow,
        "host_release_ancestry": {
            "status": "UNAVAILABLE_NOT_CHECKED", "positive_ancestry_claimed": False,
            "required_external_evidence": "POSITIVE_M2_LINEAGE_BEFORE_SINGLE_SSH",
        },
        "installed_sha256": EXPECTED, "exact_installed_source_hashes_unchanged": True,
        "proof": proof, "installed_http_framing_controls": framing,
        "provider_calls": 0, "runtime_data_writes": 0,
        "market_inputs": "SYNTHETIC_CONFORMANCE", "result": "PASS",
        "overall_panel": "NOT_ADMITTED", "H1": "NOT_TESTED", "H2": "NOT_TESTED", "H3": "NOT_TESTED",
    }
    print(json.dumps(nanoseconds_for_output(record), sort_keys=True, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
