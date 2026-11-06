#!/usr/bin/env python3
"""Render the same saved-result figures as SVG for GitHub, without changing study rules."""
from pathlib import Path

if __name__ == '__main__':
    path = Path(__file__).with_name('build_figures.py')
    source = path.read_text().replace(".png'", ".svg'")
    source = source.replace("'font.family':'DejaVu Sans'", "'svg.fonttype':'none','font.family':'DejaVu Sans'")
    exec(compile(source, str(path), 'exec'), {'__file__': str(path), '__name__': '__main__'})

    for figure in (path.parent / 'deliverables/figures').glob('*.svg'):
        figure.write_text('\n'.join(line.rstrip() for line in figure.read_text().splitlines()) + '\n')
