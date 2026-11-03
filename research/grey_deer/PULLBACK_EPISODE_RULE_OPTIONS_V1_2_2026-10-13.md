# Pullback episode-rule options, v1.2 (2026-10-13)

This memo is a design-options note for the seat. It is not a preregistration freeze. It does not choose a rule. Counts below are properties of the binary event-date axis. They are not measures of model skill.

Stage-1b file `research/grey_deer/pullback_stage1b/PULLBACK_STAGE1B_RESULTS.json` sha256 `0cd9b0ae0d426eda7be3ef07162cb2c279bfcd56f50f2b3694dfab715bef606d`. Fields: episodes[h].binary event_dates, clusters, episode_windows, per_ticker_episodes, ticker_events, origins, events, event_months, event_month_list. Stage-1 file `research/grey_deer/PULLBACK_STAGE1_RESULTS_2026-10-11.json` sha256 `33043d65e60f0fd5f6ab38acf08cf5b9f1c138d8706149b4a3504e27a099391f`. Fields: episodes[h].binary.honest_n origins, events, clusters, episodes, event_months.

Gap clustering and window overlap call `event_clusters`, `cluster_window` and `merge_episodes` in the frozen stage-1 script. A pre-window other than 21 is that same overlap test after a shift of the session indices, so the frozen pre lines up with the requested pre and the post length is shifted the other way. At pre = 21 the call is unshifted. Event-months are the committed count of distinct calendar months of the union event dates. None of the computable rules drop a date, so that count is copied onto every row. It is not rebuilt from a session calendar.

## Frozen v1.1 rule

The panel rule that produced the stage-1b episodes is three steps.

1. A panel event date is any session index on which at least one of the panel names has Y=1. Several names on the same session are one event date.
2. Event dates form a cluster when the gap in session index is at most h. A gap greater than h starts a new cluster.
3. Each cluster has a window from 21 sessions before its first event date through h sessions after its last. Clusters whose windows overlap become one episode.

The power floor is 10 episodes and 10 distinct event months. Below either number a claim is underpowered, whatever else is true of it. The floor was set before these panel counts existed. It is not a target for the episode rule.

## Reproduction

Rebuilding clusters and episodes from the stored union event dates, with the frozen functions, matches the stored counts and the stored windows.

| h | committed clusters | reproduced clusters | committed episodes | reproduced episodes | windows match |
| --- | --- | --- | --- | --- | --- |
| h5 | 31 | 31 | 11 | 11 | yes |
| h10 | 20 | 20 | 4 | 4 | yes |
| h21 | 5 | 5 | 1 | 1 | yes |

h5 windows: 294..371; 372..432; 434..463; 531..592; 594..638; 672..702; 736..799; 822..972; 997..1023; 1073..1120; 1125..1310.
h10 windows: 294..645; 666..805; 808..977; 994..1315.
h21 windows: 294..1319.

## Why the panel collapses

`origins` in the stage-1b binary block is a count of ticker-date rows in the comparison set, not a count of sessions. It divides evenly by the number of per-ticker keys, which is consistent with a complete cross-section and an implied session count of origins divided by that width. A balanced pattern of missing rows could also divide evenly, so the implied session count is an inference from that divisibility, not a stored session list. Date-axis occupancy is event dates divided by the implied session count. Event dates divided by origins is the row ratio. On a balanced cross-section the row ratio equals the occupancy divided by the number of names.

| h | event dates | origins (rows) | event dates / origins | implied sessions | date-axis occupancy | event months | ticker-events | mean names per event date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| h5 | 175 | 14000 | 0.012500 | 1000 | 0.175000 | 35 | 405 | 2.314286 |
| h10 | 395 | 13930 | 0.028356 | 995 | 0.396985 | 44 | 1168 | 2.956962 |
| h21 | 625 | 13776 | 0.045369 | 984 | 0.635163 | 46 | 2726 | 4.361600 |

The histogram counts session-index gaps between consecutive union event dates. A gap of 1 means the next event date is the next session. Event-free sessions between two event dates equal the gap minus 1. The longest quiet stretch is the maximum of those interior runs. It does not include sessions before the first event date or after the last.

| gap | h5 | h10 | h21 |
| --- | --- | --- | --- |
| 0 | 0 | 0 | 0 |
| 1 | 112 | 328 | 572 |
| 2 | 15 | 15 | 17 |
| 3 | 6 | 5 | 4 |
| 4-5 | 11 | 10 | 7 |
| 6-10 | 6 | 17 | 9 |
| 11-21 | 14 | 11 | 11 |
| 22-42 | 4 | 6 | 4 |
| 43-63 | 4 | 2 | 0 |
| 64+ | 2 | 0 | 0 |
| n gaps | 174 | 394 | 624 |
| min | 1 | 1 | 1 |
| median | 1 | 1 | 1 |
| max | 94 | 52 | 38 |
| longest event-free | 93 | 51 | 37 |

Event-month span of the union: h5 2022-10 to 2026-09; h10 2022-10 to 2026-09; h21 2022-10 to 2026-09.

| h | event dates | clusters | episodes | dates absorbed by gap | clusters absorbed by window | gap share of reduction | window share of reduction | merge reach | boundaries re-glued | boundaries | gaps > h | gaps > reach |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| h5 | 175 | 31 | 11 | 144 | 20 | 144/164 | 20/164 | 26 | 20 | 30 | 30 | 10 |
| h10 | 395 | 20 | 4 | 375 | 16 | 375/391 | 16/391 | 31 | 16 | 19 | 19 | 3 |
| h21 | 625 | 5 | 1 | 620 | 4 | 620/624 | 4/624 | 42 | 4 | 4 | 4 | 0 |

h5. A frozen episode boundary exists only where two consecutive event dates have session-index gap greater than 26 (h + 21). A frozen cluster boundary exists where the gap is greater than 5. On this union that is 30 cluster boundaries and 10 episode boundaries, so 31 clusters and 11 episodes. The longest gap is 94 (93 event-free sessions, between session indices 458 and 552), which is above the reach. Gaps that stay as episode boundaries: 27, 28, 94, 28, 60, 60, 49, 51, 76, 31. Of the reduction from 175 event dates to 11 episodes, the gap rule absorbs 144 (144/164, 0.878049) and the window merge absorbs 20 (20/164, 0.121951). The window re-glues 20 of 30 cluster boundaries.

h10. A frozen episode boundary exists only where two consecutive event dates have session-index gap greater than 31 (h + 21). A frozen cluster boundary exists where the gap is greater than 10. On this union that is 19 cluster boundaries and 3 episode boundaries, so 20 clusters and 4 episodes. The longest gap is 52 (51 event-free sessions, between session indices 635 and 687), which is above the reach. Gaps that stay as episode boundaries: 52, 34, 48. Of the reduction from 395 event dates to 4 episodes, the gap rule absorbs 375 (375/391, 0.959079) and the window merge absorbs 16 (16/391, 0.040921). The window re-glues 16 of 19 cluster boundaries.

h21. A frozen episode boundary exists only where two consecutive event dates have session-index gap greater than 42 (h + 21). A frozen cluster boundary exists where the gap is greater than 21. On this union that is 4 cluster boundaries and 0 episode boundaries, so 5 clusters and 1 episode. The longest gap is 38 (37 event-free sessions, between session indices 635 and 673). That is at most the reach, so every shorter gap is too, and the horizon is one episode. Cluster sizes in event dates: 129, 65, 20, 194, 217. Cluster-boundary gaps: 23, 28, 38, 35. Of the reduction from 625 event dates to 1 episode, the gap rule absorbs 620 (620/624, 0.993590) and the window merge absorbs 4 (4/624, 0.006410). The window re-glues 4 of 4 cluster boundaries.

The gap rule does most of the reduction in headcount when the typical gap is one session: neighbouring event dates fall into one cluster. The window merge is the step that removes the remaining boundaries. At h5 the panel has 11 episodes, above SPY's 4 episodes. At h10 the panel has 4 episodes, below SPY's 6 episodes. At h21 the panel has 1 episode, below SPY's 7 episodes. The shortfall versus SPY, where there is one, is the union plus the window, not a shortage of ticker-level events.

## Computable alternatives

Choosing a rule because it meets the 10-episode / 10-month floor on this consumed sample is p-hacking the power floor.

The floor column is a consequence of each rule on this already-consumed union. Searching the column for `met` and freezing that row uses the same sample that would later be called evidence. That is p-hacking the power floor. Event-months do not move across these rows, because every computable rule keeps the same event dates. On this panel the month half of the floor is already met at every horizon. Only the episode count can change the floor bit among these rows, and only a rule that drops dates could change the month count.

Rules that meet the floor at every horizon in the tables: Q=5, Q=10. Selecting one of those labels because it is on this list is the p-hack named above. They are shown so the trap is visible.

### h5

Gap g with the frozen window merge (pre = 21, post = h).

| g | clusters | episodes | event months | floor |
| --- | --- | --- | --- | --- |
| 1 | 63 | 11 | 35 | met |
| 2 | 48 | 11 | 35 | met |
| 3 | 42 | 11 | 35 | met |
| 5 | 31 | 11 | 35 | met |
| 10 | 25 | 11 | 35 | met |
| 21 | 11 | 11 | 35 | met |

Every gap g in the menu is at most 21, and the window reach is 26. Tightening g only splits clusters that the window merge joins again, so every g has the same episodes and the same windows as the frozen h5 rule. Cluster counts still change. Varying the gap without shrinking the window cannot raise episode N at this horizon.

Frozen gap with no window merge.

h5: clusters = episodes = 31, event months 35, floor met.

Frozen gap, window pre varied, post = h.

| pre | clusters | episodes | event months | floor |
| --- | --- | --- | --- | --- |
| 0 | 31 | 31 | 35 | met |
| 5 | 31 | 25 | 35 | met |
| 10 | 31 | 21 | 35 | met |
| 21 | 31 | 11 | 35 | met |

pre = 0 does not merge any frozen-gap cluster, because a cluster boundary already has gap greater than h and the pre = 0 reach is h. Those episodes are the no-window-merge episodes.

Quiet-reset: a new episode starts only after Q consecutive event-free sessions (session-index gap greater than Q). No window merge.

| Q | episodes | event months | floor |
| --- | --- | --- | --- |
| 5 | 31 | 35 | met |
| 10 | 25 | 35 | met |
| 21 | 11 | 35 | met |
| 42 | 7 | 35 | not met |

Quiet-reset Q = 5 is the frozen gap with no window merge.

### h10

Gap g with the frozen window merge (pre = 21, post = h).

| g | clusters | episodes | event months | floor |
| --- | --- | --- | --- | --- |
| 1 | 67 | 4 | 44 | not met |
| 2 | 52 | 4 | 44 | not met |
| 3 | 47 | 4 | 44 | not met |
| 5 | 37 | 4 | 44 | not met |
| 10 | 20 | 4 | 44 | not met |
| 21 | 9 | 4 | 44 | not met |

Every gap g in the menu is at most 21, and the window reach is 31. Tightening g only splits clusters that the window merge joins again, so every g has the same episodes and the same windows as the frozen h10 rule. Cluster counts still change. Varying the gap without shrinking the window cannot raise episode N at this horizon.

Frozen gap with no window merge.

h10: clusters = episodes = 20, event months 44, floor met.

Frozen gap, window pre varied, post = h.

| pre | clusters | episodes | event months | floor |
| --- | --- | --- | --- | --- |
| 0 | 20 | 20 | 44 | met |
| 5 | 20 | 13 | 44 | met |
| 10 | 20 | 10 | 44 | met |
| 21 | 20 | 4 | 44 | not met |

pre = 0 does not merge any frozen-gap cluster, because a cluster boundary already has gap greater than h and the pre = 0 reach is h. Those episodes are the no-window-merge episodes.

Quiet-reset: a new episode starts only after Q consecutive event-free sessions (session-index gap greater than Q). No window merge.

| Q | episodes | event months | floor |
| --- | --- | --- | --- |
| 5 | 37 | 44 | met |
| 10 | 20 | 44 | met |
| 21 | 9 | 44 | not met |
| 42 | 3 | 44 | not met |

Quiet-reset Q = 10 is the frozen gap with no window merge.

### h21

Gap g with the frozen window merge (pre = 21, post = h).

| g | clusters | episodes | event months | floor |
| --- | --- | --- | --- | --- |
| 1 | 53 | 1 | 46 | not met |
| 2 | 36 | 1 | 46 | not met |
| 3 | 32 | 1 | 46 | not met |
| 5 | 25 | 1 | 46 | not met |
| 10 | 16 | 1 | 46 | not met |
| 21 | 5 | 1 | 46 | not met |

Every gap g in the menu is at most 21, and the window reach is 42. Tightening g only splits clusters that the window merge joins again, so every g has the same episodes and the same windows as the frozen h21 rule. Cluster counts still change. Varying the gap without shrinking the window cannot raise episode N at this horizon.

Frozen gap with no window merge.

h21: clusters = episodes = 5, event months 46, floor not met.

Frozen gap, window pre varied, post = h.

| pre | clusters | episodes | event months | floor |
| --- | --- | --- | --- | --- |
| 0 | 5 | 5 | 46 | not met |
| 5 | 5 | 4 | 46 | not met |
| 10 | 5 | 3 | 46 | not met |
| 21 | 5 | 1 | 46 | not met |

pre = 0 does not merge any frozen-gap cluster, because a cluster boundary already has gap greater than h and the pre = 0 reach is h. Those episodes are the no-window-merge episodes.

Quiet-reset: a new episode starts only after Q consecutive event-free sessions (session-index gap greater than Q). No window merge.

| Q | episodes | event months | floor |
| --- | --- | --- | --- |
| 5 | 25 | 46 | met |
| 10 | 16 | 46 | met |
| 21 | 5 | 46 | not met |
| 42 | 1 | 46 | not met |

Quiet-reset Q = 21 is the frozen gap with no window merge. Quiet-reset Q = 42 is the frozen episode partition, because both break only when the gap is greater than 42.

## Not computable from the committed artifacts

The three designs below need data the artifacts do not store. No episode count, month count or floor bit is available for them, and none is guessed here.

### Breadth threshold

A session is a panel event date only when at least m names have Y=1 on that session. A predeclared gap and window then run on the dates that survive.

Data required: The per-session count of names with Y=1 on the comparison-set date axis, or the per-name event dates that would produce it. The committed union records only that the count was at least one. The ticker-event total is a sum across sessions, not a per-date histogram.

### Per-ticker episodes with a common-shock correction

Count episodes on each name, then treat episodes that overlap in time as one common shock. Honest-N is the number of common shocks, not the sum of the per-name counts.

Data required: Per-name event dates or per-name episode windows. The artifact stores the per-name episode count only, so overlap across names cannot be recovered.

### Sector-stratified episodes

Form the union of event dates inside a predeclared grouping of names, then run the episode rule inside each group.

Data required: Per-name event dates. The sector labels of these ETFs can be named without data. The dates cannot. A group union cannot be rebuilt from the panel-wide union or from per-name counts.

## Per-ticker sums and SPY

Stage-1 binary honest-N is the single-series SPY run. SPY is not a key in the panel's per-ticker episode counts. The panel and SPY use the same frozen cluster and window rule. They do not use the same event dates.

| h | panel episodes | sum of per-ticker episodes | SPY episodes | SPY clusters | SPY events | SPY event months | SPY origins | SPY floor |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| h5 | 11 | 93 | 4 | 4 | 11 | 5 | 1001 | not met |
| h10 | 4 | 126 | 6 | 8 | 36 | 9 | 996 | not met |
| h21 | 1 | 114 | 7 | 9 | 117 | 16 | 985 | not met |

Per-ticker episode counts stored beside the panel floor. The sum is not an input to the floor.

| ticker | h5 | h10 | h21 |
| --- | --- | --- | --- |
| QQQ | 10 | 10 | 7 |
| IWM | 8 | 12 | 9 |
| DIA | 2 | 5 | 9 |
| XLB | 10 | 13 | 8 |
| XLC | 6 | 9 | 8 |
| XLE | 11 | 12 | 7 |
| XLF | 5 | 9 | 8 |
| XLI | 4 | 7 | 8 |
| XLK | 10 | 7 | 7 |
| XLP | 2 | 5 | 7 |
| XLRE | 8 | 10 | 9 |
| XLU | 7 | 12 | 10 |
| XLV | 2 | 7 | 9 |
| XLY | 8 | 8 | 8 |
| sum | 93 | 126 | 114 |

Per-ticker episodes are not independent and the sum is not an honest N. Each name runs the episode rule on its own event dates. The artifact keeps the count and drops the dates. Adding the counts treats each name's episode as a separate piece of evidence. One selloff that prints Y=1 on several names increments several counters for one shock. The mean number of names with Y=1 on a union event date, ticker-events divided by union event dates, is the co-occurrence in the density table. That average is not a per-date breadth histogram: the same mean can be many single-name dates plus a few broad dates, or a steady breadth. The sum is an upper count of name-level spells. It is not a count of independent spells.

The union rule makes the opposite mistake. Any one name marks the session for the whole panel, and the window then chains those marks. At h21 the union-and-window rule has 1 episode, SPY has 7 episodes, and the sum of per-ticker episodes is 114. None of these counts is the number of common shocks. That number needs the per-name dates.

## Candidates for a v1.2 preregistration

Two computable candidates and one candidate that has to wait for new fields. The justifications use the structure of the frozen rule and, where they use the union's occupancy, they are covered by the disclosure in the next section. None of them is chosen because its floor column says met. Consequence counts are reported so a failure of the floor is visible. They are not the selection criterion.

### C1. Frozen gap, no window merge

v1.1 names a cluster with the gap rule and then merges clusters whose dependence buffers overlap. The buffer exists so origins near an event are not treated as independent evidence. Overlap of two buffers is not a reason to call the clusters one spell. Dropping the window merge keeps the buffer available for a later deletion rule and lets the gap rule name the episode. The reason is the two-step structure of the frozen rule. It is not a skill result, and it is not the floor column.

Consequence on this sample, not a reason to prefer the row: h5 31 episodes, floor met; h10 20 episodes, floor met; h21 5 episodes, floor not met.

### C2. Quiet-reset at Q=21, no window merge, same Q at every horizon

v1.1 lets the label horizon set the gap, so a longer outcome window is also a longer chain. The frozen rule already contains a dependence scale that is not the label horizon: the 21-session pre-window. A quiet-reset at 21, on each horizon's own event dates, with no window merge, uses that scale at every horizon. The union's event-date occupancy is why a gap as short as the label horizon chains sessions. A v1.2 preregistration has to disclose that this density was seen. 21 is taken from the pre-window constant. It is not taken from the rows that clear the floor.

Consequence on this sample, not a reason to prefer the row: h5 11 episodes, floor met; h10 9 episodes, floor not met; h21 5 episodes, floor not met.

### C3. Breadth threshold m=2, after per-date counts are retained

The panel event date is any session on which at least one name has Y=1. That union is what fills the date axis. A spell that is supposed to be shared needs a second name on the session. m=2 is that minimum confirmation. It is a property of a common-move question. This memo has no episode count for it: the artifacts do not store per-date breadth. A preregistration that wants a breadth rule has to keep those counts and must not choose m by which value clears the floor on this sample.

No episode count is computed. Computing one would require the per-date breadth, which is not in the artifact.

## Disclosure a v1.2 preregistration must carry

this rule was chosen after observing v1.1 event-date density (not skill)

This memo does not freeze a rule. A later preregistration that freezes one of the candidates, or any other rule motivated by these tables, carries that sentence.
