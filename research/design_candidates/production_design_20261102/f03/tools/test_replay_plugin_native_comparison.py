"""No-network tests of replay CLI evidence-state reporting."""
import contextlib
import io
import json
import unittest
from unittest.mock import patch

import replay_plugin_native_comparison as replay_cli


class TestReplayExitStates(unittest.TestCase):
    def run_state(self, state):
        payload = {"comparison": {"state": state}, "installed_guard_execution": False,
                   "native_transport_reexecuted_by_replay": False, "paper_mutations": 0}
        output = io.StringIO()
        with patch.object(replay_cli, "replay", return_value=payload) as read, \
                patch("sys.argv", ["replay", "recorded.json", "--guard-source", "guard.py"]), \
                contextlib.redirect_stdout(output):
            code = replay_cli.main()
        read.assert_called_once()
        self.assertFalse(json.loads(output.getvalue())["installed_guard_execution"])
        return code

    def test_observed_parity_is_success_not_native_execution(self):
        self.assertEqual(self.run_state("OBSERVED_SCOPE_PARITY"), 0)

    def test_observed_divergence_is_nonzero(self):
        self.assertEqual(self.run_state("OBSERVED_SCOPE_DIVERGENCE"), 3)

    def test_incomplete_is_not_silently_successful(self):
        self.assertEqual(self.run_state("OBSERVED_SCOPE_INCOMPLETE"), 4)

    def test_unknown_state_is_not_silently_successful(self):
        with self.assertRaisesRegex(ValueError, "unknown comparison state"):
            self.run_state("UNRECOGNIZED")


if __name__ == "__main__":
    unittest.main()
