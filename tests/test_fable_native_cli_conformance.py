"""Pure tests for the fixed native protocol oracle; no installed CLI is used."""
import importlib.util
import json
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location("conformance", Path(__file__).with_name("fable_native_cli_conformance.py"))
C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C)


class OracleTests(unittest.TestCase):
    def test_sse_has_balanced_tool_blocks_and_terminal(self):
        blocks = [{"type": "tool_use", "id": "t", "name": "Read", "input": {"file_path": "fixture.txt"}}]
        kind, raw = C.answer(blocks, "fixture", stream=True)
        self.assertEqual(kind, "text/event-stream")
        events = [json.loads(line[6:]) for line in raw.decode().splitlines() if line.startswith("data: ")]
        self.assertEqual(events[0]["type"], "message_start")
        self.assertEqual(events[-1]["type"], "message_stop")
        self.assertEqual(events[-2]["delta"]["stop_reason"], "tool_use")
        self.assertEqual(json.loads(events[2]["delta"]["partial_json"]), blocks[0]["input"])

    def test_plain_reply_is_an_anthropic_message(self):
        kind, raw = C.answer([{"type": "text", "text": "done"}], "fixture", stream=False)
        self.assertEqual(kind, "application/json")
        self.assertEqual(json.loads(raw)["stop_reason"], "end_turn")

    def test_parent_requires_actual_read_then_consumed_return(self):
        oracle = C.Oracle("leaf_result", Path("/fixture"))
        first = oracle.respond({"model": "fixture", "tools": [{"name": "Agent"}], "messages": [{"role": "user", "content": C.ROOT_MARKER}]})
        self.assertEqual(first[0]["name"], "Agent")
        leaf_input = {"model": "fixture", "tools": [{"name": "Agent"}], "messages": [{"role": "user", "content": C.census_prompt()}]}
        leaf_first = oracle.respond(leaf_input)
        self.assertEqual(leaf_first[0]["name"], "Read")
        self.assertFalse(oracle.leaf_read)
        leaf_input["messages"].append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": "toolu_read", "content": C.VALUE}]})
        leaf_result = oracle.respond(leaf_input)
        self.assertTrue(oracle.leaf_read)
        self.assertFalse(oracle.parent_consumed)
        oracle.respond({"model": "fixture", "tools": [{"name": "Agent"}], "messages": [{"role": "user", "content": C.ROOT_MARKER},
                       {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "toolu_agent_0", "content": leaf_result}]}]})
        self.assertTrue(oracle.parent_consumed)
        self.assertEqual([r["role"] for r in oracle.records], ["parent", "leaf", "leaf", "parent"])

    def test_tool_error_containing_prompt_cannot_become_leaf(self):
        oracle = C.Oracle("ten_fable", Path("/fixture"))
        blocks = oracle.respond({"tools": [{"name": "Agent"}], "messages": [{"role": "user", "content": C.ROOT_MARKER}]})
        self.assertEqual(len(blocks), 10)
        self.assertTrue(all(b["input"]["model"] == "fable" for b in blocks))
        oracle.respond({"tools": [{"name": "Agent"}], "messages": [{"role": "user", "content": C.ROOT_MARKER}, {"role": "user", "content": [{"type": "tool_result", "is_error": True, "content": C.census_prompt()}]}]})
        self.assertEqual(oracle.records[-1]["role"], "parent")
        self.assertEqual(oracle.records[-1]["error_results"], 1)

    def test_error_marker_is_not_positive_read(self):
        oracle = C.Oracle("leaf_result", Path("/fixture"))
        oracle.respond({"messages": [{"role": "user", "content": C.census_prompt()},
                       {"role": "user", "content": [{"type": "tool_result", "is_error": True, "content": C.VALUE}]}]})
        self.assertFalse(oracle.leaf_read)

    def test_native_auxiliary_probe_does_not_consume_parent_turn(self):
        oracle = C.Oracle("leaf_result", Path("/fixture"))
        reply = oracle.respond({"messages": [{"role": "user", "content": C.ROOT_MARKER}]})
        self.assertEqual(reply[0]["text"], "FIXTURE_AUXILIARY_OK")
        self.assertFalse(oracle.started)
        reply = oracle.respond({"tools": [{"name": "Agent"}], "messages": [{"role": "user", "content": C.ROOT_MARKER}]})
        self.assertEqual(reply[0]["name"], "Agent")

    def test_unbound_tool_result_does_not_count_as_read(self):
        oracle = C.Oracle("leaf_result", Path("/fixture"))
        oracle.respond({"messages": [{"role": "user", "content": C.census_prompt()},
                       {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "wrong", "content": C.VALUE}]}]})
        self.assertFalse(oracle.leaf_read)

    def test_turn_limit_probe_stops_itself_after_fourteen_without_hanging(self):
        oracle = C.Oracle("leaf_turn_limit", Path("/fixture"))
        request = {"messages": [{"role": "user", "content": C.census_prompt()}]}
        for i in range(14):
            self.assertEqual(oracle.respond(request)[0]["name"], "Read")
        self.assertEqual(oracle.respond(request)[0]["text"], "NATIVE_TURN_LIMIT_NOT_ENFORCED")

    def test_request_budget_is_finite(self):
        oracle = C.Oracle("router_only", Path("/fixture"))
        for _ in range(C.MAX_REQUESTS):
            oracle.respond({"messages": []})
        with self.assertRaises(ValueError):
            oracle.respond({"messages": []})

    def test_environment_is_not_ambient(self):
        env = C.isolated_environment(Path("/home/fixture"), Path("/work/fixture"), 12345, {"env": {"MASTERMIND_NATIVE_DELEGATION_MODE": "router_only"}})
        self.assertEqual(env["ANTHROPIC_BASE_URL"], "http://127.0.0.1:12345")
        self.assertEqual(env["ANTHROPIC_API_KEY"], "fixture-not-a-real-key")
        self.assertNotIn("CLAUDE_CODE_OAUTH_TOKEN", env)
        self.assertNotIn("HTTP_PROXY", env)
        self.assertNotIn("AWS_ACCESS_KEY_ID", env)


if __name__ == "__main__":
    unittest.main()
