"""TP-1 connection risk classification has no automated side effects."""
import unittest

from engine.tick_plane.connection_safety import classify_socket_close


class SafetyTests(unittest.TestCase):
    def test_postauth_1008_blocks_auto_retry(self):
        o=classify_socket_close(close_code=1008,had_authenticated=True,
                                observed_max_connections=True)
        self.assertEqual(o["verdict"],"HARD_STOP")
        self.assertFalse(o["may_reconnect"])

    def test_policy_close_even_without_literal_max_connections_stops(self):
        o=classify_socket_close(close_code=1008,had_authenticated=False,
                                observed_max_connections=False)
        self.assertEqual(o["verdict"],"HARD_STOP")

    def test_unrelated_close_cannot_be_called_slot_conflict(self):
        o=classify_socket_close(close_code=1006,had_authenticated=True,
                                observed_max_connections=False)
        self.assertEqual(o["verdict"],"EXTERNAL_SUPERVISOR_REQUIRED")
        self.assertFalse(o["may_reconnect"])

    def test_unknown_evidence_does_not_reconnect(self):
        o=classify_socket_close(close_code=None,had_authenticated=True,
                                observed_max_connections=False)
        self.assertEqual(o["verdict"],"HOLD")
        self.assertFalse(o["may_reconnect"])

    def test_regular_close_has_no_retry(self):
        o=classify_socket_close(close_code=1000,had_authenticated=True,
                                observed_max_connections=False)
        self.assertEqual(o["verdict"],"STOP")
        self.assertFalse(o["may_reconnect"])

if __name__ == "__main__":
    unittest.main()
