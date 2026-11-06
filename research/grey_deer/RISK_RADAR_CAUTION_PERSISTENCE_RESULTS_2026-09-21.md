# Risk Radar Caution-Persistence Display Study — Results

Protocol commit: `1882492ee09ef9baefbf0412aed175388c23c631`.

Descriptive display-tier research only; no live model or policy changed.

## Daily 5% / 21-observation results

| Window | Base rate | Caution+ event rate | Persistent-5 event rate | Caution+ lift | Persistent-5 lift | Caution+ recall | Persistent-5 recall | Persistent fire rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Full usable history | 17.7% | 20.0% | 20.8% | 1.13× | 1.18× | 82.6% | 72.1% | 61.2% |
| 2020+ | 17.6% | 21.4% | 24.0% | 1.22× | 1.36× | 96.9% | 93.5% | 68.8% |

Daily windows overlap and are not independent episodes.

## Product implication

- Since 2020, persistent-five caution raises the event rate to **24.0%** from the 17.6% base rate, but is active on **68.8%** of eligible sessions.
- Full history: lift **1.18×**, fire rate **61.2%**; this is context, not a sparse alert.
- Therefore a five-session persistence fact is suitable only as neutral duration context inside Risk Radar; it is too common for a new prominent warning badge and carries no authority to escalate the state.

## Distinct-event view

- Complete 5%/21 anchors: **110**.
- Caution-or-higher by T0: **106**.
- Persistent-five caution by T0: **99**.
- Persistent-five appears by T0 in **99** anchors; **76** are already active at the T-21 window edge.
- Exact (non-left-censored) first-persistence lead is available for **23** anchors; median **12.0 sessions**.
- The window-bounded median is **21.0 sessions** and must not be read as an exact lead because of left-censoring.
- Persistent-five appeared before the first 5% breach in **99** event rows.

## Evidence ceiling

The five-session rule was frozen as one trading week before outcome inspection and was not swept. This is reconstructed historical display research, not genuinely issued forecast history. A favorable result can support duration copy only; it cannot escalate the state or alter odds, gates, or capital authority.

