"""Reproduce the local research assay without network, credentials or runtime data."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import io
import json
import platform
import unittest
import revision_oracle
import test_revision_oracle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('_assay_output'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    args.output_dir.mkdir(parents=True, exist_ok=True)
    log = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromModule(test_revision_oracle)
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    data = json.loads((root/'public_control_case.json').read_text())
    cs = {c['id']: c for c in data['claims']}
    pairs = [('initial','reaffirmed'),('reaffirmed','revised'),('revised','range_revision'),
             ('range_revision','actual_2025'),('range_revision','outlook_2026')]
    receipt = {
        'schema':'offline_research_assay_receipt.v1',
        'executed_at_utc':datetime.now(timezone.utc).isoformat(),
        'python':platform.python_version(),
        'tests_run':result.testsRun,'failures':len(result.failures),
        'errors':len(result.errors),'skipped':len(result.skipped),
        'success':result.wasSuccessful(),
        'scope':'Manually normalized public issuer control series and adversarial fixtures; not production or parser performance.',
        'counts':{'source_documents':len(data['sources']),'normalized_claims':len(data['claims']),
                  'real_pair_comparisons':len(pairs),'broker_source_pairs_verified':0},
        'sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in
                  ('revision_oracle.py','test_revision_oracle.py','public_control_case.json','run_assay.py')},
        'comparisons':[{'before':a,'after':b,'result':revision_oracle.compare(cs[a],cs[b])} for a,b in pairs],
        'operational_pit_probe':revision_oracle.select_visible(data['claims'],'2026-03-01T00:00:00Z'),
        'not_proven':['Automated extraction accuracy','Original broker PDF acquisition or rights',
                      'Full source-byte identity','Live four-set census','Production viewer behavior',
                      'Incremental account value','Model answer quality','Historical operational knowledge']
    }
    (args.output_dir/'verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (args.output_dir/'tests.txt').write_text(log.getvalue())
    print(json.dumps({k:receipt[k] for k in ('tests_run','failures','errors','skipped','success','counts')}))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
