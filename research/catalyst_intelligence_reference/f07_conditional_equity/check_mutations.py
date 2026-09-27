"""Run syntax-valid harmful mutations of this isolated research reference."""
from __future__ import annotations
import argparse
import ast
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
SOURCE=(HERE/'f07_scenario_reference.py').read_text()
MUTATIONS={
    'double_count_balance_sheet': ('residual = common * multiple  # Common earnings multiple already values equity.',
                                 'residual = common * multiple + cash - debt'),
    'gross_margin_as_net_earnings': ('residual = common * multiple  # Common earnings multiple already values equity.',
                                   'residual = gp * multiple'),
    'ignore_new_share_dilution': ('shares = opening_shares + new_shares','shares = opening_shares'),
    'ignore_financing_fees': ('+ issue_proceeds - n[\'equity_issue_fees\']','+ issue_proceeds'),
    'company_distribution_as_per_share_cash': ("dividend = _d(s['dividend_to_entry_share'], 'dividend_to_entry_share', nonnegative=True)",
                                              "dividend = n['distributions_paid'] / opening_shares"),
    'missing_probability_becomes_zero': ("_s(expected) if expected is not None else None","_s(expected) if expected is not None else '0'"),
    'grant_ranking_authority': ("'can_rank':False","'can_rank':True"),
    'pe_proceeds_disappear': ("if new_shares != 0:","if False and new_shares != 0:"),
    'preinformation_entry': ("if quote_at < known_at:","if False and quote_at < known_at:"),
    'different_security_quote': ("if _text(quote['subject_ref'], 'quote.subject_ref') != packet['subject_ref']:","if False and _text(quote['subject_ref'], 'quote.subject_ref') != packet['subject_ref']:"),
    'different_share_basis': ("if _text(quote['share_basis_ref'], 'quote.share_basis_ref') != packet['share_basis_ref']:","if False and _text(quote['share_basis_ref'], 'quote.share_basis_ref') != packet['share_basis_ref']:"),
    'unsupported_conversion': ("if _d(quote['common_shares_per_unit'], 'quote.common_shares_per_unit', positive=True) != 1:","if False and _d(quote['common_shares_per_unit'], 'quote.common_shares_per_unit', positive=True) != 1:"),
    'discard_replay_inputs': ("'input_envelope':envelope","'input_envelope':{}"),
    'permit_future_input': ("if known_at > at:","if False and known_at > at:"),
}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report",type=Path,default=HERE.parent/"reports"/"mutations.json")
    args=parser.parse_args()
    report=[]
    for name,(old,new) in MUTATIONS.items():
        if SOURCE.count(old)!=1:raise RuntimeError(f'ambiguous mutation anchor: {name}')
        changed=SOURCE.replace(old,new);ast.parse(changed)
        with tempfile.TemporaryDirectory(prefix='f07-mutant-') as td:
            root=Path(td);(root/'f07_scenario_reference.py').write_text(changed)
            shutil.copy2(HERE/'test_f07_scenario_reference.py',root/'test_f07_scenario_reference.py')
            shutil.copy2(HERE/'test_f07_review_regressions.py',root/'test_f07_review_regressions.py')
            p=subprocess.run([sys.executable,'-m','pytest','-q','--tb=no','--junitxml=result.xml'],cwd=root,capture_output=True,text=True,timeout=20)
            tree=ET.parse(root/'result.xml').getroot()
            suites=list(tree.iter('testsuite'))
            row={'mutation':name,'syntax_valid':True,'exit_code':p.returncode,
                 'tests':sum(int(x.attrib.get('tests',0)) for x in suites),
                 'failures':sum(int(x.attrib.get('failures',0)) for x in suites),
                 'errors':sum(int(x.attrib.get('errors',0)) for x in suites)}
            row['detected_by_assertions']=row['failures']>0 and row['errors']==0 and p.returncode==1
            report.append(row)
    out={'scope':'isolated synthetic financial-contract reference','mutants':report,
         'all_detected':all(r['detected_by_assertions'] for r in report)}
    dest=args.report;dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))
    return 0 if out['all_detected'] else 1

if __name__=='__main__':raise SystemExit(main())
