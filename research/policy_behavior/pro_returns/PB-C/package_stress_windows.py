#!/usr/bin/env python3
"""Wrap the independently derived Treasury calendar in the PB-C delivery schema."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent)
a=p.parse_args()
rows=json.loads((a.directory/'rates_sensitivity_stress_calendar.json').read_text())
out={'schema':'PB_C_research_stress_windows_v1','not_a_production_contract':True,
 'primary_nasdaq_drawdown':'NOT_MEASURED_RIGHTS_AND_DATA_UNRESOLVED',
 'secondary_vix':'NOT_MEASURED_RIGHTS_UNRESOLVED','issuer_drawdowns_and_sector_breadth':'NOT_MEASURED',
 'rates_sensitivity_status':'DERIVED_RETROSPECTIVE_PRIOR_DATE_CURRENT_VINTAGE',
 'source_manifest':'treasury_stress_manifest.json','daily_derived_rates':rows}
(a.directory/'PB_C_STRESS_WINDOWS.json').write_text(json.dumps(out,indent=2)+'\n')
