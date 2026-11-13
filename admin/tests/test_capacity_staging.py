"""Prove native writer adaptation and installed-control enrollment, without services."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from admin.capacity_config_transaction import configuration_writer
from admin.capacity_fabric_observer import control_writers_ready
from admin.deploy.stage_capacity_observer import native_writer_candidate

HELPER=Path(__file__).resolve().parents[1]/'capacity_config_transaction.py'

class NativeWriterAdapters(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.config=self.root/'routes.json';self.config.write_text('{"routes":[],"retained":17}')
    def tearDown(self):self.tmp.cleanup()
    def test_guard_honors_shared_lock_and_keeps_native_transform(self):
        original='import json\nfrom pathlib import Path\nROUTES_JSON=Path(CONFIG_PATH)\nlog=lambda value: None\ndef guard_routes() -> None:\n    document=json.loads(ROUTES_JSON.read_text())\n    document["native_policy"]=True\n    ROUTES_JSON.write_text(json.dumps(document))\n'
        candidate=native_writer_candidate('model_exclusivity_guard.py',original,HELPER)
        context={'CONFIG_PATH':str(self.config)};exec(compile(candidate,'native-guard-fixture','exec'),context)
        with configuration_writer(self.config):context['guard_routes']()
        self.assertNotIn('native_policy',json.loads(self.config.read_text()))
        context['guard_routes']()
        self.assertEqual(json.loads(self.config.read_text()),{'routes':[],'retained':17,'native_policy':True})
        self.assertIn('document["native_policy"]=True',candidate)
    def test_peak_reads_only_after_acquiring_shared_lock(self):
        original='RESULT=$(python3 - "$ROUTES" "$WANT" <<\'PYEOF\'\nimport json, sys, pathlib\npath, want = sys.argv[1], sys.argv[2]\np = pathlib.Path(path)\nd=json.loads(p.read_text());d["native_policy"]=want\np.write_text(json.dumps(d))\nprint("CHANGED")\nPYEOF\n)\nif [[ "$CLEAN" == "CHANGED" ]]; then\n  log "reload: $OUT"\nelse\n  log "unchanged"\nfi\n'
        candidate=native_writer_candidate('peak_router.sh',original,HELPER)
        script=candidate.split("<<'PYEOF'\n",1)[1].split('\nPYEOF',1)[0]
        command=[sys.executable,'-c',script,str(self.config),'fixture-policy']
        with configuration_writer(self.config):
            held=subprocess.run(command,capture_output=True,text=True,timeout=5)
        self.assertEqual(held.returncode,0,held.stderr);self.assertEqual(held.stdout.strip(),'HELD')
        self.assertNotIn('native_policy',json.loads(self.config.read_text()))
        applied=subprocess.run(command,capture_output=True,text=True,timeout=5)
        self.assertEqual(applied.returncode,0,applied.stderr)
        self.assertEqual(json.loads(self.config.read_text())['retained'],17)
        self.assertEqual(json.loads(self.config.read_text())['native_policy'],'fixture-policy')
    def test_changed_native_writer_fences_live_controls(self):
        writer=self.root/'writer.py';writer.write_text('original writer')
        config={'control_writers':[{'path':str(writer),'sha256':hashlib.sha256(writer.read_bytes()).hexdigest()}]}
        self.assertTrue(control_writers_ready(config))
        writer.write_text('independently changed writer')
        self.assertFalse(control_writers_ready(config));self.assertFalse(control_writers_ready({}))
    def test_reenrollment_keeps_the_existing_policy_bytes(self):
        original='def guard_routes() -> None:\n    return "native policy retained"\n'
        once=native_writer_candidate('model_exclusivity_guard.py',original,HELPER)
        twice=native_writer_candidate('model_exclusivity_guard.py',once,self.root/'next-helper.py')
        self.assertEqual(twice.count('def guard_routes()'),1)
        self.assertEqual(twice.count('def _capacity_unlocked_guard_routes()'),1)
        self.assertIn('return "native policy retained"',twice)

if __name__=='__main__':unittest.main()
