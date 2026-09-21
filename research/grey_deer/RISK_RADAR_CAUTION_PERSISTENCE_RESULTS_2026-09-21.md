# Risk Radar Caution-Persistence Display Study — Results

Protocol commit: `1882492ee09ef9baefbf0412aed175388c23c631`.

Descriptive display-tier research only; no live model or policy changed.

## Daily 5% / 21-observation results

| Window | Base rate | Caution+ event rate | Persistent-5 event rate | Caution+ lift | Persistent-5 lift | Caution+ recall | Persistent-5 recall | Persistent fire rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Full usable history | 17.7% | 19.6% | 20.3% | 1.11× | 1.15× | 83.3% | 72.8% | 63.4% |
| 2020+ | 17.6% | 20.6% | 22.7% | 1.17× | 1.29× | 98.6% | 94.6% | 73.3% |

Daily windows overlap and are not independent episodes.

## Product implication

- Since 2020, persistent-five caution raises the event rate to **22.7%** from the 17.6% base rate, but is active on **73.3%** of eligible sessions.
- Full history: lift **1.15×**, fire rate **63.4%**; this is context, not a sparse alert.
- Therefore a five-session persistence fact is suitable only as neutral duration context inside Risk Radar; it is too common for a new prominent warning badge and carries no authority to escalate the state.

## Distinct-event view

- Complete 5%/21 anchors: **110**.
- Caution-or-higher by T0: **106**.
- Persistent-five caution by T0: **99**.
- Persistent-five appears by T0 in **99** anchors; **77** are already active at the T-21 window edge.
- Exact (non-left-censored) first-persistence lead is available for **22** anchors; median **11.5 sessions**.
- The window-bounded median is **21.0 sessions** and must not be read as an exact lead because of left-censoring.
- Persistent-five appeared before the first 5% breach in **99** event rows.

## Evidence ceiling

The five-session rule was frozen as one trading week before outcome inspection and was not swept. This is reconstructed historical display research, not genuinely issued forecast history. A favorable result can support duration copy only; it cannot escalate the state or alter odds, gates, or capital authority.

