"""Mutation-survey kills for the pullback fragment template.

The sweep that produced the table below ran outside pytest, against
``tests/test_risk_radar_pullback_depth_template.py``,
``tests/test_pullback_depth_copy_states.py``,
``tests/test_pullback_depth_a11y.py`` and
``tests/test_pullback_depth_static_contract.py``. Each test here pins a
behaviour a surviving single-edit mutant of the fragment broke. Figures are
synthetic. The fragment source is not modified.

Already pinned by the suites above, and not re-tested here: an unsigned
``0.0%`` on the three measured metrics
(``test_figures_that_round_to_zero_print_without_a_sign``), the age line's
singular and plural
(``test_age_line_agrees_in_number``,
``test_one_missing_session_reads_in_the_singular``), and the forecast block
across the accessibility catalogue
(``test_a7_forecast_block_names_both_languages_without_figures``).

H039 is a source defect, not a missing assertion: ``price_ok`` treats a close
equal to the retained high as qualified in every phase. The fragment's own
comment says that close is a reclaim and is contradictory outside
``recovering`` and ``repaired``. No test here pins the permissive comparison.

Mutant table (id, verdict, killer, change):

H001 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | swap `==` -> `!=` in `ng and value|length == 10 and value[4] == '-' and`
H002 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | swap `==` -> `!=` in `== 10 and value[4] == '-' and value[7] == '-' -%}`
H003 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | swap `==` -> `!=` in `== '-' and value[7] == '-' -%} {%- set ns = namesp`
H004 | KILLED | test_zero_counts_print_only_when_the_owner_sent_zero | swap `>=` -> `>` in `s integer and value >= 0 %}{{ value }}{% endif -%}`
H005 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | swap `>=` -> `<=` in `s integer and value >= 0 %}{{ value }}{% endif -%}`
H006 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | swap `==` -> `!=` in `) and value - value == 0 and value >= 0 and value`
H007 | KILLED | test_zero_counts_print_only_when_the_owner_sent_zero | swap `>=` -> `>` in `alue == 0 and value >= 0 and value <= 100 -%} {{-`
H008 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | swap `>=` -> `<=` in `alue == 0 and value >= 0 and value <= 100 -%} {{-`
H009 | KILLED | test_recovered_share_prints_a_whole_percent_inside_the_closed_range | swap `<=` -> `<` in `alue >= 0 and value <= 100 -%} {{- '%.0f%%'|format`
H010 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | swap `<=` -> `>=` in `alue >= 0 and value <= 100 -%} {{- '%.0f%%'|format`
H011 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | swap `>` -> `<` in `s integer and value > 0 %}{{ value }}{% endif -%}`
H012 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | swap `>` -> `<` in `ing and rows|length > 0 -%} {%- set bad = namespa`
H013 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00Z', '2026-10-01 09:00... | swap `==` -> `!=` in `length -%} {%- if n == 17 or n == 20 or n == 22 or`
H014 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00:00Z', '2026-10-01 09... | swap `==` -> `!=` in `{%- if n == 17 or n == 20 or n == 22 or n == 25 -%`
H015 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00-05:00', '2026-10-01 ... | swap `==` -> `!=` in `17 or n == 20 or n == 22 or n == 25 -%} {%- set d`
H016 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00:00+00:00', '2026-10-... | swap `==` -> `!=` in `20 or n == 22 or n == 25 -%} {%- set digits = '01`
H017 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00:00+00:00', '2026-10-... | swap `==` -> `!=` in `ns.ok and value[4] == '-' and value[7] == '-' and`
H018 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00:00+00:00', '2026-10-... | swap `==` -> `!=` in `== '-' and value[7] == '-' and value[10] == 'T' an`
H019 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00:00+00:00', '2026-10-... | swap `==` -> `!=` in `= '-' and value[10] == 'T' and value[13] == ':' -%`
H020 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00:00+00:00', '2026-10-... | swap `==` -> `!=` in `= 'T' and value[13] == ':' -%} {%- if n == 17 and`
H021 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00Z', '2026-10-01 09:00... | swap `==` -> `!=` in `== ':' -%} {%- if n == 17 and value[16] == 'Z' -%}`
H022 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00Z', '2026-10-01 09:00... | swap `==` -> `!=` in `== 17 and value[16] == 'Z' -%} {{- value[0:10] ~ '`
H023 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00:00Z', '2026-10-01 09... | swap `==` -> `!=` in `UTC' -}} {%- elif n == 20 and value[16] == ':' and`
H024 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00:00Z', '2026-10-01 09... | swap `==` -> `!=` in `== 20 and value[16] == ':' and value[17] in digits`
H025 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00:00Z', '2026-10-01 09... | swap `==` -> `!=` in `igits and value[19] == 'Z' -%} {{- value[0:10] ~ '`
H026 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00-05:00', '2026-10-01 ... | swap `==` -> `!=` in `UTC' -}} {%- elif n == 22 and (value[16] == '+' or`
H027 | KILLED | test_m_both_offset_signs_render_at_each_stamp_length | swap `==` -> `!=` in `= 22 and (value[16] == '+' or value[16] == '-') an`
H028 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00-05:00', '2026-10-01 ... | swap `==` -> `!=` in `== '+' or value[16] == '-') and value[17] in digit`
H029 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00-05:00', '2026-10-01 ... | swap `==` -> `!=` in `igits and value[19] == ':' and value[20] in digits`
H030 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00:00+00:00', '2026-10-... | swap `==` -> `!=` in `:22] -}} {%- elif n == 25 and value[16] == ':' and`
H031 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00:00+00:00', '2026-10-... | swap `==` -> `!=` in `== 25 and value[16] == ':' and value[17] in digits`
H032 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00:00+00:00', '2026-10-... | swap `==` -> `!=` in `gits and (value[19] == '+' or value[19] == '-') an`
H033 | KILLED | test_m_both_offset_signs_render_at_each_stamp_length | swap `==` -> `!=` in `== '+' or value[19] == '-') and value[20] in digit`
H034 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00:00+00:00', '2026-10-... | swap `==` -> `!=` in `igits and value[22] == ':' and value[23] in digits`
H035 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | swap `==` -> `!=` in `integer) and p-p == 0 and h-h == 0 and p > 0 an`
H036 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | swap `==` -> `!=` in `nd p-p == 0 and h-h == 0 and p > 0 and h > 0 an`
H037 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | swap `>` -> `<` in `and h-h == 0 and p > 0 and h > 0 and (p <= h`
H038 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | swap `>` -> `<` in `= 0 and p > 0 and h > 0 and (p <= h or phase i`
H039 | FINDING | close == peak still qualifies outside recovering/repaired | swap `<=` -> `<` in `and h > 0 and (p <= h or phase in ('recovering'`
H040 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | swap `<=` -> `>=` in `and h > 0 and (p <= h or phase in ('recovering'`
H041 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | swap `==` -> `!=` in `nteger) and low-low == 0 and low > 0 and price_`
H042 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | swap `>` -> `<` in `low == 0 and low > 0 and price_ok and low <= p`
H043 | KILLED | test_figures_that_round_to_zero_print_without_a_sign | swap `<=` -> `<` in `nd price_ok and low <= p and low <= h %} {% set ns`
H044 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | swap `<=` -> `>=` in `nd price_ok and low <= p and low <= h %} {% set ns`
H045 | KILLED | test_m_low_equal_to_the_peak_still_measures_the_drawdown | swap `<=` -> `<` in `nd low <= p and low <= h %} {% set ns.low_ok = low`
H046 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | swap `<=` -> `>=` in `nd low <= p and low <= h %} {% set ns.low_ok = low`
H047 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | swap `==` -> `!=` in `and o.get('market') == mkt and o.get('schema')`
H048 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | swap `==` -> `!=` in `and o.get('schema') == 'pullback_observation.v1'`
H049 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | swap `==` -> `!=` in `nd o.get('quality') == 'current' and o.get('clo`
H050 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | swap `==` -> `!=` in `and o.get('clock') == 'settled_close' and o.get('`
H051 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | swap `==` -> `!=` in `in labels and phase == o.get('phase') and price_ok`
H052 | KILLED | test_prior_peak_reclaim_does_not_delete_worst_damage | swap `>` -> `<` in `igh','高于参考高点') if p > h else t('From the referenc`
H053 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | swap `>` -> `<` in `iv> {% if p > h %}{% set up_s = '%.1f'|fo`
H054 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | swap `!=` -> `==` in `ent">{{ '−' if dd_s != '0.0' else '' }}{{ dd_s }}%`
H055 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | swap `!=` -> `==` in `%}{{ '−' if worst_s != '0.0' else '' }}{{ worst_s`
H056 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | swap `==` -> `!=` in `_ok and p/low-p/low == 0 %}{% set rebound_s = '%.1`
H057 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | swap `!=` -> `==` in `{{ '+' if rebound_s != '0.0' else '' }}{{ rebound_`
H058 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | swap `>` -> `<` in `loses_since_onset') > 0 %} <div class="rrp-ag`
H059 | KILLED | test_age_line_agrees_in_number[(1, '1 observed close since the pullback was confirmed')] | swap `==` -> `!=` in `_closes_since_onset == 1 else 's') ~ ' since the p`
H060 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | swap `==` -> `!=` in `} {%- if ma == 'below' %}<dt data-signal="`
H061 | KILLED | test_average_at_or_above_uses_the_other_label | swap `==` -> `!=` in `} {%- if ma == 'above' %}<dt data-signal="`
H062 | KILLED | test_m_held_low_without_a_retracement_is_early_repair | swap `>` -> `<` in `is integer and _nnl > 0) or ((_rec is integer or`
H063 | KILLED | test_m_retracement_without_a_held_low_is_early_repair | swap `==` -> `!=` in `at) and _rec - _rec == 0 and _rec > 0) %} {%`
H064 | KILLED | test_m_retracement_without_a_held_low_is_early_repair | swap `>` -> `<` in `_rec == 0 and _rec > 0) %} {% if phase ==`
H065 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | swap `==` -> `!=` in `} {% if phase == 'underway' and _early %}<p`
H066 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('stabilizing', 'E... | swap `==` -> `!=` in `{% elif phase == 'underway' %}<p class="rrp-`
H067 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('stabilizing', 'E... | swap `==` -> `!=` in `{% elif phase == 'stabilizing' %}<p class="r`
H068 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('recovering', 'Re... | swap `==` -> `!=` in `{% elif phase == 'recovering' %}<p class="rr`
H069 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | swap `==` -> `!=` in `(' session' if gaps == '1' else ' sessions') ~ ' m`
H070 | KILLED | test_figures_that_round_to_zero_print_without_a_sign | swap `==` -> `!=` in `ng and dates|length == vals|length and dates|lengt`
H071 | KILLED | test_figures_that_round_to_zero_print_without_a_sign | swap `>` -> `<` in `th and dates|length > 0 %} <details class="`
H072 | KILLED | test_figures_that_round_to_zero_print_without_a_sign | swap `==` -> `!=` in `er) and value-value == 0 and -100 <= value <= 0 %}`
H073 | KILLED | test_m_history_table_keeps_the_closed_percent_bounds | swap `<=` -> `<` in `value == 0 and -100 <= value <= 0 %}{% set value_s`
H074 | KILLED | test_figures_that_round_to_zero_print_without_a_sign | swap `<=` -> `>=` in `value == 0 and -100 <= value <= 0 %}{% set value_s`
H075 | KILLED | test_m_history_table_keeps_the_closed_percent_bounds | swap `<=` -> `<` in `0 and -100 <= value <= 0 %}{% set value_s = '%.1f'`
H076 | KILLED | test_figures_that_round_to_zero_print_without_a_sign | swap `<=` -> `>=` in `0 and -100 <= value <= 0 %}{% set value_s = '%.1f'`
H077 | KILLED | test_figures_that_round_to_zero_print_without_a_sign | swap `!=` -> `==` in `%}{{ '−' if value_s != '0.0' else '' }}{{ value_s`
H078 | KILLED | test_withheld_chart_without_a_reason_stays_neutral_not_that_prices_are_unusable | swap `==` -> `!=` in `('detail_withheld') == 'short' %}<p>{{ t('Too few`
H079 | KILLED | test_withheld_chart_without_a_reason_stays_neutral_not_that_prices_are_unusable | swap `==` -> `!=` in `('detail_withheld') == 'uncovered' %}<p>{{ t('Char`
H080 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | negate {% if %} (value is string and value|length == 10 and value[4] == '-' and value[7]…)
H081 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | negate {% if %} (ch not in '0123456789')
H082 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | negate {% if %} (ns.ok)
H083 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | negate {% if %} (value is integer and value >= 0)
H084 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | negate {% if %} ((value is integer or value is float) and value - value == 0 and value >…)
H085 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | negate {% if %} (value is sameas true)
H086 | KILLED | test_average_at_or_above_uses_the_other_label | negate {% elif %} (value is sameas false)
H087 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | negate {% if %} (value is integer and value > 0)
H088 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | negate {% if %} (rows is sequence and rows is not string and rows is not mapping and row…)
H089 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | negate {% if %} (item is not mapping)
H090 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | negate {% if %} ((not day) or ph is not string or ph not in labels)
H091 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | negate {% if %} (not bad.v)
H092 | KILLED | test_missing_view_is_not_a_calm_or_current_vote[None] | negate {% if %} (value is string)
H093 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00:00+00:00', '2026-10-... | negate {% if %} (n == 17 or n == 20 or n == 22 or n == 25)
H094 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00:00+00:00', '2026-10-... | negate {% if %} (ch not in digits)
H095 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00:00+00:00', '2026-10-... | negate {% if %} (ns.ok and value[4] == '-' and value[7] == '-' and value[10] == 'T' and …)
H096 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00:00+00:00', '2026-10-... | negate {% if %} (n == 17 and value[16] == 'Z')
H097 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00:00+00:00', '2026-10-... | negate {% elif %} (n == 20 and value[16] == ':' and value[17] in digits and value[18] in d…)
H098 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00:00+00:00', '2026-10-... | negate {% elif %} (n == 22 and (value[16] == '+' or value[16] == '-') and value[17] in dig…)
H099 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00:00+00:00', '2026-10-... | negate {% elif %} (n == 25 and value[16] == ':' and value[17] in digits and value[18] in d…)
H100 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00:00+00:00', '2026-10-... | negate {% if %} (o.get('asof'))
H101 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00:00+00:00', '2026-10-... | negate {% if %} (_vu_disp)
H102 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | negate {% if %} (current)
H103 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | negate {% if %} (p > h)
H104 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | negate {% if %} (low_ok)
H105 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | negate {% if %} (low_ok and p/low-p/low == 0)
H106 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | negate {% if %} (o.get('observed_closes_since_onset') is integer and o.get('observed_clo…)
H107 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | negate {% if %} (show_ev)
H108 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | negate {% if %} (onset or low_s or streak or recovered or ma)
H109 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | negate {% if %} (onset)
H110 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | negate {% if %} (low_s)
H111 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | negate {% if %} (streak)
H112 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | negate {% if %} (recovered)
H113 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | negate {% if %} (ma == 'below')
H114 | KILLED | test_average_at_or_above_uses_the_other_label | negate {% if %} (ma == 'above')
H115 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | negate {% if %} (phase == 'underway' and _early)
H116 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('stabilizing', 'E... | negate {% elif %} (phase == 'underway')
H117 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('stabilizing', 'E... | negate {% elif %} (phase == 'stabilizing')
H118 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('recovering', 'Re... | negate {% elif %} (phase == 'recovering')
H119 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | negate {% if %} (trail)
H120 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | negate {% if %} (gaps)
H121 | KILLED | test_figures_that_round_to_zero_print_without_a_sign | negate {% if %} (current and v.get('detail_chart_html'))
H122 | KILLED | test_figures_that_round_to_zero_print_without_a_sign | negate {% if %} (dates is sequence and dates is not string and vals is sequence and vals…)
H123 | KILLED | test_figures_that_round_to_zero_print_without_a_sign | negate {% if %} ((value is float or value is integer) and value-value == 0 and -100 <= v…)
H124 | KILLED | test_withheld_chart_without_a_reason_stays_neutral_not_that_prices_are_unusable | negate {% elif %} (current and v.get('detail_withheld') == 'short')
H125 | KILLED | test_withheld_chart_without_a_reason_stays_neutral_not_that_prices_are_unusable | negate {% elif %} (current and v.get('detail_withheld') == 'uncovered')
H126 | KILLED | test_withheld_chart_without_a_reason_stays_neutral_not_that_prices_are_unusable | negate {% elif %} (current)
H127 | KILLED | test_average_at_or_above_uses_the_other_label | drop {% elif %} branch `{% elif value is sameas false %}above`
H128 | KILLED | test_missing_or_mistyped_evidence_field_omits_that_row[('price_transitions', [{'date'... | drop {% else %} branch `{%- else -%} {%- set day = iso_day(item.get('date'))|trim -%`
H129 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00:00Z', '2026-10-01 09... | drop {% elif %} branch `{%- elif n == 20 and value[16] == ':' and value[17] in digit`
H130 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00-05:00', '2026-10-01 ... | drop {% elif %} branch `{%- elif n == 22 and (value[16] == '+' or value[16] == '-')`
H131 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00:00+00:00', '2026-10-... | drop {% elif %} branch `{%- elif n == 25 and value[16] == ':' and value[17] in digit`
H132 | KILLED | test_c1_settled_close_is_a_time_only_when_asof_is_present | drop {% else %} branch `{% else %}—`
H133 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | drop {% else %} branch `{% else %}{% set dd = [0, 100*(1-p/h)]|max %}{% set dd_s = '`
H134 | KILLED | test_a8_metric_values_have_adjacent_text_labels[cn-monitoring-chart] | drop {% else %} branch `{% else %}{{ t('Unavailable','暂无') }}`
H135 | KILLED | test_a8_metric_values_have_adjacent_text_labels[cn-monitoring-chart] | drop {% else %} branch `{% else %}{{ t('Unavailable','暂无') }}`
H136 | KILLED | test_phase_alone_still_states_deterioration_without_inventing_counts | drop {% elif %} branch `{% elif phase == 'underway' %}<p class="rrp-verdict" data-si`
H137 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('stabilizing', 'E... | drop {% elif %} branch `{% elif phase == 'stabilizing' %}<p class="rrp-verdict" data`
H138 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('recovering', 'Re... | drop {% elif %} branch `{% elif phase == 'recovering' %}<p class="rrp-verdict" data-`
H139 | KILLED | test_m_history_table_keeps_the_closed_percent_bounds | drop {% else %} branch `{% else %}{{ t('Unavailable','暂无') }}`
H140 | KILLED | test_m_withheld_chart_keeps_its_reason | drop {% elif %} branch `{% elif current and v.get('detail_withheld') == 'short' %}<p`
H141 | KILLED | test_m_withheld_chart_keeps_its_reason | drop {% elif %} branch `{% elif current and v.get('detail_withheld') == 'uncovered'`
H142 | KILLED | test_withheld_chart_without_a_reason_stays_neutral_not_that_prices_are_unusable | drop {% elif %} branch `{% elif current %}<p>{{ t('No chart is shown for this assess`
H143 | KILLED | test_withheld_chart_without_a_reason_stays_neutral_not_that_prices_are_unusable | drop {% else %} branch `{% else %}<p>{{ t('The chart needs current, usable price evi`
H144 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | language leak t(en, zh)
H145 | KILLED | test_m_every_visible_label_keeps_its_chinese | language leak t('OBSERVED PRICE','已观测价格')
H146 | KILLED | test_missing_view_is_not_a_calm_or_current_vote[None] | language leak t('Price update needed','价格数据待更新')
H147 | KILLED | test_m_every_visible_label_keeps_its_chinese | language leak t('Watch the retest of the low; a rebound alone does not confirm recove…
H148 | KILLED | test_m_unavailable_panel_names_the_missing_price_evidence | language leak t('A current closing-price assessment is not available.', '当前收盘价评估暂不可用。…
H149 | KILLED | test_m_every_visible_label_keeps_its_chinese | language leak t(o.get('benchmark_en') or '', o.get('benchmark_zh') or '')
H150 | KILLED | test_c1_settled_close_is_a_time_only_when_asof_is_present | language leak t('Settled close','收盘价')
H151 | KILLED | test_zoned_valid_until_is_readable_without_js[('2026-10-01T09:00:00+00:00', '2026-10-... | language leak t('Current until','有效至')
H152 | KILLED | test_expiry_region_is_an_empty_live_region_with_an_inert_message | language leak t('Awaiting a newer close. This assessment is no longer current.', '等待更…
H153 | KILLED | test_prior_peak_reclaim_does_not_delete_worst_damage | language leak t('Above the reference high','高于参考高点')
H154 | KILLED | test_b2_close_equal_to_the_reference_high_stays_zero_under_the_old_label | language leak t('From the reference high','距参考高点')
H155 | KILLED | test_m_every_visible_label_keeps_its_chinese | language leak t('Reference high','参考高点')
H156 | KILLED | test_m_every_visible_label_keeps_its_chinese | language leak t('Worst drawdown so far','已发生的最深回撤')
H157 | KILLED | test_m_every_visible_label_keeps_its_chinese | language leak t('Unavailable','暂无')
H158 | KILLED | test_copy_names_measurements_not_forecasts | language leak t('Measured at the lowest close so far','按本轮最低收盘价计算')
H159 | KILLED | test_m_every_visible_label_keeps_its_chinese | language leak t('Rebound from the low','自低点回升')
H160 | KILLED | test_m_every_visible_label_keeps_its_chinese | language leak t('Unavailable','暂无')
H161 | KILLED | test_m_every_visible_label_keeps_its_chinese | language leak t('Not recovery odds','并非修复概率')
H162 | KILLED | test_age_line_agrees_in_number[(1, '1 observed close since the pullback was confirmed')] | language leak t('observed close' ~ ('' if o.observed_closes_since_onset == 1 else 's'…
H163 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | language leak t('Pullback confirmed','回撤确认')
H164 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | language leak t('Lowest close','最低收盘价')
H165 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | language leak t('Closes without a new low','未创新低的收盘数')
H166 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | language leak t('Share of the loss retraced','已收复跌幅比例')
H167 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | language leak t('Against the 20-close average','相对20日收盘均价')
H168 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | language leak t('Below','低于')
H169 | KILLED | test_m_every_visible_label_keeps_its_chinese | language leak t('Against the 20-close average','相对20日收盘均价')
H170 | KILLED | test_average_at_or_above_uses_the_other_label | language leak t('Above or at','不低于')
H171 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | language leak t('Pullback still active: early repair signs are not confirmed','回撤仍在进行…
H172 | KILLED | test_b1_underway_without_repair_evidence_keeps_the_deterioration_verdict | language leak t('Deterioration: no repair evidence yet','恶化：尚无修复证据')
H173 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('stabilizing', 'E... | language leak t('Early repair evidence: the low is holding','初步修复证据：低点守住')
H174 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('recovering', 'Re... | language leak t('Repair evidence building; not a confirmed recovery','修复证据增加中，尚未确认修复')
H175 | KILLED | test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase[('underway', 'Pull... | language leak t(gaps ~ (' session' if gaps == '1' else ' sessions') ~ ' missing from …
H176 | KILLED | test_m_every_visible_label_keeps_its_chinese | language leak t('The observed path','已观测走势')
H177 | KILLED | test_m_every_visible_label_keeps_its_chinese | language leak t('Observed closing drawdown from the reference high.', '相对参考高点的已观测收盘回撤…
H178 | KILLED | test_copy_names_measurements_not_forecasts | language leak t('View price history','查看历史价格')
H179 | KILLED | test_m_every_visible_label_keeps_its_chinese | language leak t('Closing drawdown from the reference high by session','各交易日相对参考高点的收盘回…
H180 | KILLED | test_m_every_visible_label_keeps_its_chinese | language leak t('Session','交易日')
H181 | KILLED | test_m_every_visible_label_keeps_its_chinese | language leak t('From the reference high','距参考高点')
H182 | KILLED | test_m_history_table_keeps_the_closed_percent_bounds | language leak t('Unavailable','暂无')
H183 | KILLED | test_m_withheld_chart_keeps_its_reason | language leak t('Too few closes since the reference high to draw a chart yet.', '自参考高…
H184 | KILLED | test_m_withheld_chart_keeps_its_reason | language leak t('Chart not shown: the closing history on record does not fully suppor…
H185 | KILLED | test_m_withheld_chart_keeps_its_reason | language leak t('No chart is shown for this assessment.', '本次评估不显示图表。')
H186 | KILLED | test_m_unavailable_panel_names_the_missing_price_evidence | language leak t('The chart needs current, usable price evidence.', '图表需要当前且可用的价格数据。')
H187 | KILLED | test_m_every_visible_label_keeps_its_chinese | language leak t('The chart is price history, not a forecast path.', '图表呈现历史价格，并非预测路径。…
H188 | KILLED | test_m_forecast_rows_stay_an_em_dash_with_no_figure | language leak t('FURTHER DOWNSIDE','进一步跌幅')
H189 | KILLED | test_no_forecast_or_reentry_authority_is_inferred[cn] | language leak t('Estimate unavailable','估计暂不可用')
H190 | KILLED | test_m_every_visible_label_keeps_its_chinese | language leak t('We can measure the decline that has already happened. A reliable ran…
H191 | KILLED | test_copy_names_measurements_not_forecasts | language leak t('Further decline from the latest close','自最新收盘价起的进一步跌幅')
H192 | KILLED | test_copy_names_measurements_not_forecasts | language leak t('Total pullback depth','回撤总深度')
H193 | KILLED | test_m_every_visible_label_keeps_its_chinese | language leak t('Why no estimate?','为什么暂无估计？')
H194 | KILLED | test_m_every_visible_label_keeps_its_chinese | language leak t('Publishing a range takes historical tests for this market, benchmark…
H195 | KILLED | test_copy_names_measurements_not_forecasts | language leak t('This is not a new-entry signal. Use the separate risk and entry chec…
H196 | KILLED | test_existing_phase_is_rendered_without_reclassification[('monitoring', 'Pullback mon... | phase label ZH leaked `回撤观察` -> `Pullback monitor`
H197 | KILLED | test_existing_phase_is_rendered_without_reclassification[('developing', 'Pullback dev... | phase label ZH leaked `回撤形成中` -> `Pullback developing`
H198 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | phase label ZH leaked `回撤进行中` -> `Pullback underway`
H199 | KILLED | test_existing_phase_is_rendered_without_reclassification[('stabilizing', 'Stabilizati... | phase label ZH leaked `止跌观察` -> `Stabilization watch`
H200 | KILLED | test_existing_phase_is_rendered_without_reclassification[('recovering', 'Watching pri... | phase label ZH leaked `价格修复观察` -> `Watching price repair`
H201 | KILLED | test_existing_phase_is_rendered_without_reclassification[('repaired', 'Pullback repai... | phase label ZH leaked `本轮回撤已修复` -> `Pullback repaired`
H202 | KILLED | test_prior_peak_reclaim_does_not_delete_worst_damage | '%.1f' -> '%.0f' at offset 8424
H203 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | '%.1f' -> '%.0f' at offset 8592
H204 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | '%.1f' -> '%.0f' at offset 9001
H205 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | '%.1f' -> '%.0f' at offset 9443
H206 | KILLED | test_figures_that_round_to_zero_print_without_a_sign | '%.1f' -> '%.0f' at offset 14206
H207 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | delete U+2212 replacement `{{ '−' if dd_s != '0.0' else '' }}`
H208 | KILLED | test_native_view_shows_three_distinct_observed_metrics[cn] | delete U+2212 replacement `{{ '−' if worst_s != '0.0' else '' }}`
H209 | KILLED | test_figures_that_round_to_zero_print_without_a_sign | delete U+2212 replacement `{{ '−' if value_s != '0.0' else '' }}`
"""
from bs4 import BeautifulSoup

from tests.test_risk_radar_pullback_depth_template import native_view, render

# English span text -> the Chinese span that must sit beside it.
_ZH = {
    "OBSERVED PRICE": "已观测价格",
    "A rebound alone does not confirm recovery; that takes closes back at or above the reference high.": "仅有价格回升不足以确认修复；需收盘价重回参考高点或以上。",
    "A current closing-price assessment is not available.": "当前收盘价评估暂不可用。",
    "Shanghai Composite": "上证综指",
    "Settled close": "收盘价",
    "Current until": "有效至",
    "Reference high": "参考高点",
    "Worst drawdown so far": "已发生的最深回撤",
    "Measured at the lowest close so far": "按本轮最低收盘价计算",
    "Unavailable": "暂无",
    "Rebound from the low": "自低点回升",
    "Not recovery odds": "并非修复概率",
    "Against the 20-close average": "相对20日收盘均价",
    "Below": "低于",
    "Above or at": "不低于",
    "The observed path": "已观测走势",
    "Observed closing drawdown from the reference high.": "相对参考高点的已观测收盘回撤。",
    "Closing drawdown from the reference high by session": "各交易日相对参考高点的收盘回撤",
    "Session": "交易日",
    "From the reference high": "距参考高点",
    "Too few closes since the reference high to draw a chart yet.": "自参考高点以来的收盘价尚少，暂不绘制图表。",
    "Chart not shown: the closing history on record does not fully support these figures.": "暂不显示图表：现有收盘历史无法完整支持上述数据。",
    "No chart is shown for this assessment.": "本次评估不显示图表。",
    "A chart appears once current, usable price data is on record.": "待有当前可用的价格数据后再显示图表。",
    "The chart is price history, not a forecast path.": "图表呈现历史价格，并非预测路径。",
    "FURTHER DOWNSIDE": "进一步跌幅",
    "Estimate unavailable": "估计暂不可用",
    "We can measure the decline that has already happened. A reliable range for the next low is not yet available.": "可以测量已发生的跌幅，但下一低点的可靠区间尚不可用。",
    "Further decline from the latest close": "自最新收盘价起的进一步跌幅",
    "Total pullback depth": "回撤总深度",
    "Why no estimate?": "为什么暂无估计？",
    "Publishing a range takes historical tests for this market, benchmark, price measurement and time window. Risk level and existing pullback probabilities are not a forecast of the remaining drop.": "发布区间需要针对本市场、基准、价格衡量方式和时间范围的历史检验。风险水平与现有回撤概率并非对剩余跌幅的预测。",
    "This is not a new-entry signal. Use the separate risk and entry checks.": "这不是新开仓信号。请另行查看风险与入场检查。",
    "Price update needed": "价格数据待更新",
    "Pullback underway": "回撤进行中",
    "Pullback monitor": "回撤观察",
}

_EARLY = (
    "Pullback still active: early repair signs are not confirmed",
    "回撤仍在进行：初步修复迹象尚未确认",
)
_MINUS = "\u2212"


def _soup(view, market="cn"):
    return BeautifulSoup(render(view, market), "html.parser")


def _pairs(soup):
    found = []
    for en in soup.select(".l-en"):
        zh = en.find_next_sibling()
        assert zh is not None and "l-zh" in (zh.get("class") or []), en.get_text()
        found.append((en.get_text(), zh.get_text()))
    return found


def _zh(soup, english):
    matches = [zh for en, zh in _pairs(soup) if en == english]
    assert matches, english
    assert all(zh == _ZH[english] for zh in matches), (english, matches)
    return matches[0]


def _forecast(soup):
    block = soup.select_one(".rrp-forecast")
    assert block is not None
    assert block.get("data-forecast-status") == "unavailable"
    assert not any(ch.isdigit() for ch in block.get_text())
    strongs = [node.get_text(strip=True) for node in block.select(".rrp-forecast-row strong")]
    assert strongs == ["\u2014", "\u2014"]
    _zh(block, "Estimate unavailable")
    _zh(block, "FURTHER DOWNSIDE")


def _chart_view():
    view = native_view()
    view["observation"]["below_20_close_average"] = True
    view["detail_path"] = {
        "dates": ["2026-09-14", "2026-09-15", "2026-09-16", "2026-09-17", "2026-09-18"],
        "vals": [0.0, -100.0, -6.8, 1.5, 101.0],
    }
    return view


def _monitoring_view():
    view = native_view()
    view["phase"] = view["observation"]["phase"] = "monitoring"
    view["observation"]["active"] = False
    view["observation"]["low_close"] = None
    view["detail_chart_html"] = ""
    return view


def _withheld(reason):
    view = native_view()
    view["detail_chart_html"] = ""
    if reason:
        view["detail_withheld"] = reason
    return view


def _above_average_view():
    view = native_view()
    view["observation"]["below_20_close_average"] = False
    return view


def _gallery():
    return [
        _soup(_chart_view()),
        _soup(_above_average_view()),
        _soup(_monitoring_view()),
        _soup(None),
        _soup(_withheld("short")),
        _soup(_withheld("uncovered")),
        _soup(_withheld(None)),
    ]


def test_m_both_offset_signs_render_at_each_stamp_length():
    """A minute stamp with a positive offset and a seconds stamp with a negative offset both stay readable.

    The zoned display accepts either sign. One existing stamp of each length uses the other sign, so a flip of the untested sign empties the clock.
    """
    view = native_view()
    view["observation"]["valid_until"] = "2026-10-01T09:00+00:00"
    soup = _soup(view)
    times = soup.select(".rrp-stamp time")
    assert times[1].get("datetime") == "2026-10-01T09:00+00:00"
    assert times[1].get_text(strip=True) == "2026-10-01 09:00 UTC+00:00"
    view["observation"]["valid_until"] = "2026-10-01T09:30:45-05:00"
    soup = _soup(view)
    times = soup.select(".rrp-stamp time")
    assert times[1].get("datetime") == "2026-10-01T09:30:45-05:00"
    assert times[1].get_text(strip=True) == "2026-10-01 09:30 UTC-05:00"


def test_m_low_equal_to_the_peak_still_measures_the_drawdown():
    """A low sitting on the retained high is a measured 0.0% worst drawdown, with no minus sign.

    The latest close is above that high, so the panel is a recovering reclaim and the rebound is the distance off the low.
    """
    view = native_view()
    view["phase"] = view["observation"]["phase"] = "recovering"
    view["observation"].update(close=101.0, peak_close=100.0, low_close=100.0)
    soup = _soup(view)
    assert soup.select_one("section.rrp").get("data-pb-phase") == "recovering"
    assert soup.select_one('[data-metric="current"]').get_text(strip=True) == "+1.0%"
    worst = soup.select_one('[data-metric="worst"]').get_text(strip=True)
    assert worst == "0.0%"
    assert _MINUS not in worst and "+" not in worst
    assert soup.select_one('[data-metric="rebound"]').get_text(strip=True) == "+1.0%"


def _counts(no_new_low, recovered):
    view = native_view()
    view["observation"]["no_new_low_closes"] = no_new_low
    view["observation"]["loss_recovered_pct"] = recovered
    return view


def _verdict(view):
    node = _soup(view).select_one('[data-signal="verdict"]')
    assert node is not None
    return node.select_one(".l-en").get_text(), node.select_one(".l-zh").get_text()


def test_m_held_low_without_a_retracement_is_early_repair():
    """Closes that hold the low are early repair evidence even when none of the loss has been retraced."""
    assert _verdict(_counts(3, 0)) == _EARLY


def test_m_retracement_without_a_held_low_is_early_repair():
    """A positive recovered share is early repair evidence even when the no-new-low count is zero."""
    assert _verdict(_counts(0, 25.0)) == _EARLY


def test_m_history_table_keeps_the_closed_percent_bounds():
    """The history cell prints 0, -100, and a positive above the high, and names anything outside [-100, 100].

    ``0.0%`` carries no sign. ``-100`` and ``+1.5`` stay percents. ``101`` is outside the closed range.
    """
    soup = _soup(_chart_view())
    rows = soup.select(".rrp-history tbody tr")
    cells = [row.select("td")[1] for row in rows]
    assert cells[0].get_text() == "0.0%"
    assert _MINUS not in cells[0].get_text() and "+" not in cells[0].get_text()
    assert cells[1].get_text() == _MINUS + "100.0%"
    assert cells[2].get_text() == _MINUS + "6.8%"
    assert cells[3].get_text() == "+1.5%"
    assert cells[4].select_one(".l-en").get_text() == "Unavailable"
    assert cells[4].select_one(".l-zh").get_text() == "暂无"


def test_m_withheld_chart_keeps_its_reason():
    """Each withheld reason keeps its own sentence. Dropping a branch would fall through to the neutral line."""
    short = _soup(_withheld("short")).select_one(".rrp-evidence")
    _zh(short, "Too few closes since the reference high to draw a chart yet.")
    assert "No chart is shown for this assessment." not in short.get_text()
    uncovered = _soup(_withheld("uncovered")).select_one(".rrp-evidence")
    _zh(uncovered, "Chart not shown: the closing history on record does not fully support these figures.")
    assert "No chart is shown for this assessment." not in uncovered.get_text()
    neutral = _soup(_withheld(None)).select_one(".rrp-evidence")
    _zh(neutral, "No chart is shown for this assessment.")
    assert "Too few closes" not in neutral.get_text()
    assert "does not fully support" not in neutral.get_text()


def test_m_unavailable_panel_names_the_missing_price_evidence():
    """An unqualified view says the assessment and the chart both lack current prices, and still publishes no estimate."""
    soup = _soup(None)
    assert soup.select_one("section.rrp").get("data-pb-phase") == "unavailable"
    _forecast(soup)
    _zh(soup, "A current closing-price assessment is not available.")
    _zh(soup, "A chart appears once current, usable price data is on record.")
    assert "A rebound alone does not confirm recovery; that takes closes back at or above the reference high." not in soup.get_text()


def test_m_forecast_rows_stay_an_em_dash_with_no_figure():
    """Forecast rows stay an em dash and the unavailable label, in both languages, with a numeric payload ignored."""
    stuffed = native_view()
    stuffed.update(probability=0.97, score=99, forecast={"q25": 0.024, "q75": 0.056})
    for view in (_chart_view(), _monitoring_view(), None, _withheld("short"), stuffed):
        soup = _soup(view)
        _forecast(soup)
        block = soup.select_one(".rrp-forecast").get_text()
        assert "0.97" not in block and "2.4" not in block and "5.6" not in block


def test_m_every_visible_label_keeps_its_chinese():
    """Every rendered English label keeps the Chinese written beside it, including both Unavailable sites and the benchmark."""
    required = {
        "OBSERVED PRICE",
        "A rebound alone does not confirm recovery; that takes closes back at or above the reference high.",
        "A current closing-price assessment is not available.",
        "Shanghai Composite",
        "Reference high",
        "Worst drawdown so far",
        "Unavailable",
        "Rebound from the low",
        "Not recovery odds",
        "Against the 20-close average",
        "The observed path",
        "Observed closing drawdown from the reference high.",
        "Closing drawdown from the reference high by session",
        "Session",
        "From the reference high",
        "Too few closes since the reference high to draw a chart yet.",
        "Chart not shown: the closing history on record does not fully support these figures.",
        "No chart is shown for this assessment.",
        "A chart appears once current, usable price data is on record.",
        "The chart is price history, not a forecast path.",
        "FURTHER DOWNSIDE",
        "We can measure the decline that has already happened. A reliable range for the next low is not yet available.",
        "Why no estimate?",
        "Publishing a range takes historical tests for this market, benchmark, price measurement and time window. Risk level and existing pullback probabilities are not a forecast of the remaining drop.",
    }
    seen = set()
    for soup in _gallery():
        _forecast(soup)
        for english, chinese in _pairs(soup):
            if english in _ZH:
                assert chinese == _ZH[english], (english, chinese)
            seen.add(english)
    missing = sorted(required - seen)
    assert not missing, missing
