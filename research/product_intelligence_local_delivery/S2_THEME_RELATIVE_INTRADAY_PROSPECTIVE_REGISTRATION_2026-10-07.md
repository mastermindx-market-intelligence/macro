# S2 — Theme-relative intraday prospective registration (hourly RTH)

**OUTCOME-BLIND / PROSPECTIVE / NO RESULT CLAIM**

**BASE_PIN:** `007e0cccbd06f089605ba122efc658f406043dd3`
**Frozen at:** `2026-10-07T03:09:01Z`
**Registration SHA-256:** `8048f6ef48ca7362a5d5a5dde68615aa546989571d5c3e8ad3deba9885e10c61`
**Owner acceptance:** [https://github.com/mastermindx-market-intelligence/macro/pull/8528#issuecomment-6029833181](https://github.com/mastermindx-market-intelligence/macro/pull/8528#issuecomment-6029833181) at `2026-10-07T02:46:58Z`

## Formation boundary

- First eligible `decision_at`: `2026-10-07T15:00:00+00:00` (session `2026-10-07`)
- English rule: First formation decision_at strictly after owner acceptance timestamp; decision clock is 11:00 America/New_York (end of bar starting 10:00 ET).
- 中文规则：首次形成的 decision_at 必须严格晚于产品负责人接受时间；决策时刻为美国东部时间 11:00（10:00 起始小时棒的结束）。

## Frozen parameters (summary)

- Maturity **n = 120** valid decision sessions; rejection **δ = 0.1**
- Vendor bar `t` semantics: **ASSUMED** (interval audit required before promotion)
- Session years: **[2026, 2027]**; early closes: **['2026-11-27', '2026-12-24', '2027-11-26']**

## Authority

Research-only. All `authority` flags are false. No rank, gate, size, capital, or trading authority.

## S1 bindings

- `research/product_intelligence_local_delivery/S1_THEME_RELATIVE_INTRADAY_HYPOTHESIS_PROPOSAL_2026-10-06.md` blob `6015a38223ef4122049adebfc695107b36e2ad35`
- `research/product_intelligence_local_delivery/S1_THEME_RELATIVE_INTRADAY_HYPOTHESIS_PROPOSAL_2026-10-06.json` blob `e4935d05fed97f8ef37221adce559b485d78e4cf`

## Calendar verification

- Source: https://beta.nyse.com/trade/hours-calendars
- Core trading 09:30–16:00 ET; 2027 full holidays and single early close 2027-11-26 verified against NYSE beta hours page at registration time.
