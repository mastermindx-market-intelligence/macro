"""Read-only, dormant Vercel data-origin Caddy source qualification.

This test does not change the currently installed Caddyfile, DNS, EdgeOne,
backend publishers, or the live server. Only the reviewed Caddy owner may add
the candidate block after completing the overlapping Caddy release.
"""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
LIVE_SOURCE = ROOT / "app/deploy/Caddyfile"
CANDIDATE = ROOT / "app/deploy/vercel_data_origin_candidate.caddy"


class VercelDataOriginCandidate(unittest.TestCase):
    def setUp(self):
        self.base = LIVE_SOURCE.read_text()
        self.candidate = CANDIDATE.read_text()

    def test_candidate_not_implicitly_enabled(self):
        self.assertNotIn("data.mastermind-x.com {", self.base)
        self.assertNotIn("import vercel_data_origin_candidate.caddy", self.base)
        self.assertNotIn("import *.caddy", self.base)
        self.assertIn("(terminal_public_data)", self.base)

    def test_candidate_has_narrow_host_and_no_private_api(self):
        self.assertEqual(self.candidate.count("data.mastermind-x.com {"), 1)
        self.assertIn("import terminal_public_data", self.candidate)
        self.assertIn('respond "Not Found" 404', self.candidate)
        self.assertIn('tls internal', self.candidate)
        self.assertNotIn("reverse_proxy", self.candidate)
        self.assertNotIn("handle /api/", self.candidate)
        self.assertNotIn("app.mastermind-x.com {", self.candidate)
        self.assertNotIn("beta.mastermind-x.com {", self.candidate)

    @unittest.skipUnless(shutil.which("caddy"), "Caddy binary not installed")
    def test_serial_candidate_adapts_with_existing_caddy(self):
        with tempfile.TemporaryDirectory(prefix="mmx-vercel-origin-test-") as tmp:
            path = Path(tmp) / "Caddyfile"
            path.write_text(self.base + "\n" + self.candidate)
            run = subprocess.run(
                ["caddy", "adapt", "--config", str(path), "--adapter", "caddyfile"],
                capture_output=True, text=True, timeout=20,
            )
            self.assertEqual(run.returncode, 0, run.stderr[:1500])
            cfg = json.loads(run.stdout)
            routes = [
                route for server in cfg["apps"]["http"]["servers"].values()
                for route in server.get("routes", [])
            ]
            matches = [route for route in routes if any(
                "data.mastermind-x.com" in matcher.get("host", [])
                for matcher in route.get("match", [])
            )]
            self.assertEqual(len(matches), 1)
            encoded = json.dumps(matches[0])
            self.assertIn("/data/*", encoded)
            self.assertIn("/opt/terminal/terminal/public", encoded)
            self.assertIn('"status_code": 404', encoded)
            self.assertNotIn("reverse_proxy", encoded)
            self.assertNotIn("127.0.0.1:3000", encoded)


if __name__ == "__main__":
    unittest.main()
