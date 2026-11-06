"""Source-only backend API origin admission; never activates Caddy or DNS."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app/deploy/Caddyfile"
DATA = ROOT / "app/deploy/vercel_data_origin_candidate.caddy"
APIS = ROOT / "app/deploy/vercel_api_origins_candidate.caddy"
EXPECTED = {
    "terminal-origin.mastermind-x.com": ("127.0.0.1:3000", "app.mastermind-x.com"),
    "beta-origin.mastermind-x.com": ("127.0.0.1:3001", "beta.mastermind-x.com"),
}


class BackendOriginAdmission(unittest.TestCase):
    def test_uninstalled_and_nonrecursive(self):
        live = SOURCE.read_text()
        candidate = APIS.read_text()
        for host, (_, old) in EXPECTED.items():
            self.assertNotIn(f"{host} {{", live)
            self.assertEqual(candidate.count(f"{host} {{"), 1)
            self.assertIn(f"header_up Host {old}", candidate)
        self.assertNotIn("import vercel_api_origins_candidate.caddy", live)
        self.assertNotIn("import *.caddy", live)
        self.assertNotIn("reverse_proxy https://app.mastermind-x.com", candidate)
        self.assertNotIn("reverse_proxy https://beta.mastermind-x.com", candidate)
        self.assertNotIn("handle /data/*", candidate)

    @unittest.skipUnless(shutil.which("caddy"), "Caddy binary missing")
    def test_exact_host_ports_api_only_and_explicit_404(self):
        with tempfile.TemporaryDirectory(prefix="mmx-vercel-api-test-") as td:
            path = Path(td) / "Caddyfile"
            path.write_text(SOURCE.read_text() + "\n" + DATA.read_text() +
                            "\n" + APIS.read_text())
            result = subprocess.run(["caddy", "adapt", "--config", str(path), "--adapter", "caddyfile"],
                                    capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr[:1700])
            cfg = json.loads(result.stdout)
            routes = [r for sv in cfg["apps"]["http"]["servers"].values()
                      for r in sv.get("routes", [])]
            for host, (port, legacy_host) in EXPECTED.items():
                own = [r for r in routes if any(host in m.get("host", [])
                       for m in r.get("match", []))]
                self.assertEqual(len(own), 1, host)
                route = own[0]
                serialized = json.dumps(route)
                self.assertIn('"/api/*"', serialized)
                self.assertIn('"status_code": 404', serialized)
                self.assertNotIn('"/data/*"', serialized)
                self.assertNotIn('"/terminal"', serialized)
                self.assertIn('"dial": "' + port + '"', serialized)
                self.assertIn('"Host": ["' + legacy_host + '"]', serialized)
                self.assertIn('"X-Forwarded-Host": ["' + legacy_host + '"]', serialized)
                self.assertIn("private, no-store", serialized)
                self.assertNotIn('"dial": "127.0.0.1:8000"', serialized)


if __name__ == "__main__":
    unittest.main()
