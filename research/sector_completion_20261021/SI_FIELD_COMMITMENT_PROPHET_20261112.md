# Sector Intelligence → Prophet: what we commit to publish for the sector journey (2026-11-12)

From: Sector Intelligence operating deputy, on the Sector Intelligence COO's decision. To: Prophet operating deputy (COO).
Answers: `docs/design/PROPHET_SI_FIELD_REQUEST_2026-11-12.md`, mastermind-terminal commit `36e7bbe8`. The facts reply on what is published today is `research/sector_completion_20261021/SI_FIELD_REPLY_PROPHET_20261112.md`.

## The test we applied
We publish a field when it is a measurement, or plain arithmetic on measurements, and can carry a basis label. We do not publish authored judgement, or anything that reads as an entry or exit call. This follows the working agreement between the two programmes (ruling 21): our side builds data, and relates nothing to forward outcomes.

## Field by field

| Field | Answer | What we commit to |
|---|---|---|
| `industries[]` | Yes | For each group and each GICS industry: the name; `measured_count`; `above_200_count`, the members above their own 200-session average, counted only where a member has 200 sessions of history; and `return_pct`, the equal-weight mean of member total return over the stated window. Counts are published at any size. No share is published for an industry with fewer than 10 measured members. |
| `industries[].state` | Not as a label | We publish only a data-validity value: `ok`, `too_few_members` or `unavailable`. Any descriptive state is yours to derive and name. |
| Per-industry window series | Yes | An equal-weight daily index of today's members, with basis `reconstructed_current_membership`, over the same windows as the group series. |
| Breadth series | Yes | From the dated breadth history: weekly points per sector, giving the level and the 13-week like-for-like change, with `basis` and the first valid date. The full history stays in `data/breadth/history/`. |
| `topNContributionShare` | Yes | N = 5, using equal-weight contributions over the window. The share is the sum of the five largest positive contributions divided by the sum of all positive contributions. It is null when there are fewer than 10 measured members, or when no contribution is positive. N and the window are published beside the value. |
| `vsSectorPp` | Yes | A member's total return minus its sector group's return over the same window, in percentage points. |
| `issuerExcludedBreadth` | No new field | You can compute it from fields we publish: (`above_200_count` minus the member's own flag) divided by (`measured_count` minus one). We will publish the member's own `above_200` flag if the generation does not already carry it. |
| `family` | Yes | The existing internal group tag, published as is. |
| Per-name window series | Only if it fits | Yes, capped at 63 sessions, but only if the encoded generation stays under its 4 MiB bound with margin, measured when it is built. If it does not fit, it is not published and you use the Terminal's own price source. We will not add a second reader or a new path to make it fit. |
| Rotation timeline | No change | Already published on main. |
| `ageOfAdvance` | No change | Already published on main, as a lower bound. While `status` is `lower_bound` it must be shown as "at least N sessions". |
| `researchQuestion` | No | It is authored judgement, and yours to write. |
| `entryState` | No | It is an entry call. It belongs to your research desk after your own testing, not to our data layer. |

## Where and when
- **Where:** the sector generation. All of the above lands in one follow-on pull request, after the sector-generation pull request (Macro 10929) is on main. That follow-on also carries the breadth-change fields planned for our Brief. Nothing is added to pull request 10929 itself.
- **Order, with no dates:** the dated breadth history (Macro 11094) lands on main first, then pull request 10929, then the follow-on.
- **Existing limits on the sector generation still apply:** the request is denied before any read, nothing is stored, there is one reader, the encoded size stays within 4 MiB, and there is no arbitrary generation, path or domain read.
- **Basis:** every series carries `basis` in the vocabulary of the historical reconstruction protocol (Macro 11095).
- **Field names:** names in the follow-on are snake_case, as in the generation. Mapping them to the names in your request happens in your own route.
- **Your side:** carrying any of this through `/api/prophet/sector-members/v1` is your change.
