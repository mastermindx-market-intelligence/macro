"""Settle one original GovRev intent, then retain its SAME proof witness.

No proof rebuild, retry, admission mint, new intent or consumer authority. The
original native callback runs only after protected publication readback.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess

from scripts.ci import govrev_candidate_proof as proof
from scripts.ci import native_queue_push as native


def settle_original(api, root, record, deadline, receipt, identity, out):
    root = Path(root).resolve()
    def confirmed(release):
        if proof._head_commit(root) != release['source_head']:
            raise native.PublicationHeld('original_govrev_candidate_custody_changed')
        args = proof.build_parser().parse_args(['publication-witness', '--root', str(root),
            '--receipt', str(receipt), '--commit', release['source_head'],
            '--push-status', 'successful', '--push-identity', str(identity), '--out', str(out)])
        args.native_release = release
        if proof.command_publication_witness(args) != 0:
            raise native.PublicationHeld('same_original_govrev_publication_witness_unqualified')
        witness=json.loads(Path(out).read_bytes())
        if (witness.get('contract')!='government_revenue.publication_witness.v1'
                or witness.get('native_publication')!=release
                or witness.get('issuance_authority') is not False
                or witness.get('serving_generation_authority') is not False):
            raise native.PublicationHeld('same_original_govrev_witness_not_retained')
        # Consumers see ONLY the actual protected squash after its witness exists.
        with Path(os.environ['GITHUB_OUTPUT']).open('a') as output:
            output.write('published=true\nsource_sha='+native.sha(release['merge_sha'])+'\n')
    return native.settle(api, root, record, deadline, on_published=confirmed)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',default='.')
    parser.add_argument('--record',required=True)
    parser.add_argument('--deadline',type=float,required=True)
    parser.add_argument('--receipt',required=True)
    parser.add_argument('--identity',required=True)
    parser.add_argument('--out',required=True)
    args=parser.parse_args(argv)
    try:
        root=Path(args.root).resolve()
        return settle_original(native.GitHub(root,args.deadline),root,args.record,args.deadline,
                               args.receipt,args.identity,args.out)
    except native.EffectUnknown:
        return native.UNKNOWN
    except (native.PublicationHeld,OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError):
        return native.REFUSED


if __name__=='__main__':
    raise SystemExit(main())
