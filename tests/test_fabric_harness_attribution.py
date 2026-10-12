"""Causal parent evidence, not filename guesses, for Fabric use census."""
from scripts.fabric_harness_attribution import census, parse_ps, trace_parent


PS = """
 PID PPID ELAPSED COMMAND
 100 1 01:30:00 /Users/u/.claude/remote/ccd-cli/2 --output-format stream-json
 101 100 00:15:00 /bin/zsh -c exec dispatch
 102 101 00:14:00 bash ext/remote_sub.sh ubuntu0 glm /tmp/packetA
 201 1 00:30:00 /Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex app-server
 202 201 00:10:00 python3 /tmp/fabric_task.py request
 203 202 00:09:00 /bin/bash /tmp/ext/remote_sub.sh ubuntu1 minimax /tmp/packetB
 301 1 00:08:00 zsh some unrelated command
 302 301 00:04:00 bash /tmp/ext/remote_sub.sh auto grok /tmp/packetC
 400 1 00:02:00 /bin/bash -lc echo bash ext/remote_sub.sh ubuntu9 glm
"""


def test_known_parent_chains_and_unknown_are_not_conflated():
    report = census(parse_ps(PS))
    assert report["controller_processes"] == 3
    assert report["by_parent_harness"] == {"CLAUDE": 1, "CODEX": 1, "UNKNOWN": 1}
    assert report["by_target_host"] == {"auto": 1, "ubuntu0": 1, "ubuntu1": 1}
    assert [x["parent_harness"] for x in report["launches"]] == ["CLAUDE", "CODEX", "UNKNOWN"]
    assert report["limitations"] == "controller_processes_only_not_worker_start_or_historical_usage"
    assert all("command" not in x for x in report["launches"])


def test_no_claims_from_child_packet_names():
    rows = parse_ps("1 0 3s init\n2 1 2s bash ext/remote_sub.sh ubuntu2 glm /tmp/claude-fable-5-1.codex\n")
    assert census(rows)["by_parent_harness"] == {"UNKNOWN": 1}


def test_conflicting_ancestry_is_not_misattributed():
    rows = parse_ps("""
 10 1 1h /usr/bin/codex app-server
 11 10 30m /home/u/.claude/remote/ccd-cli/2 --output-format stream-json
 12 11 2m bash ext/remote_sub.sh ubuntu0 glm /tmp/work
 """)
    assert trace_parent(rows, 11)[0] == "CONFLICTING"
    assert census(rows)["by_parent_harness"] == {"CONFLICTING": 1}


def test_circular_or_missing_parent_does_not_hang_or_invent_origin():
    rows = parse_ps("11 12 1m /bin/zsh\n12 11 1m bash ext/remote_sub.sh ubuntu3 qwen /tmp/x\n")
    assert census(rows)["by_parent_harness"] == {"UNKNOWN": 1}
