"""Audit the exact W2 display-shrinkage function without running the probe program."""
import argparse
import ast
import json
from pathlib import Path
import pandas as pd

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-root', required=True, type=Path)
args = parser.parse_args()
source = args.source_root / 'scripts/probe_theme_exposure_axes.py'
tree = ast.parse(source.read_text())
function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'vasicek_shrink')
context = {'pd': pd, 'VASICEK_W': 0.66}
exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), 'exec'), context)
x = pd.Series([-0.2, 0.3, 0.3, 1.4, 2.0])
y = pd.Series([-0.1, 0.5, 0.1, 1.1, 1.8])
xs, ys = context['vasicek_shrink'](x), context['vasicek_shrink'](y)
raw = float(x.corr(y, method='spearman'))
shrunk = float(xs.corr(ys, method='spearman'))
result = {
    'formula': '0.66 * beta + 0.34 * cross_section_mean(beta)',
    'x_raw': x.tolist(), 'x_shrunk': xs.tolist(),
    'x_rank_unchanged': x.rank().equals(xs.rank()),
    'y_rank_unchanged': y.rank().equals(ys.rank()),
    'raw_spearman': raw, 'shrunk_spearman': shrunk,
    'x_dispersion_reduced': bool(xs.std() < x.std()),
}
assert result['x_rank_unchanged'] and result['y_rank_unchanged'] and raw == shrunk
assert result['x_dispersion_reduced']
print(json.dumps(result, indent=2))
