# Prophet Save — visual and interaction evidence (2026-11-04)

This receipt owns `templates/prophet_save.css` and proves the presentation and
the interaction states of the candidate's Save surface: the Save control on a
card, the dialog itself, the account-list readback, the return control, and the
failed and uncertain outcomes.

It is a NEW, versioned directory. No earlier screenshot was moved, replaced,
rewritten or deleted: `../cells/`, `../full-page-20261103/`,
`../compact-sizing/` and `../public-sources/` are untouched.

## What is captured

Eight fixture pages, one per state of the candidate's own dialog, each captured
by `scripts/capture_page_evidence.py` across desktop (1440) x mobile (390) x
en/zh x light/dark, plus one `save-focus` force state per cell.

| page | `data-save-state` | what it shows |
|---|---|---|
| `save_signed_out.html` | `signed-out` | "Sign in to save GM to your account." + Sign in |
| `save_unavailable.html` | `unavailable` | "Account lists are unavailable. Nothing was saved." |
| `save_empty_lists.html` | `empty` | "No account lists yet. Create a list in Watchlists, then return here." + the Watchlists return control |
| `save_choose.html` | `choose` | the account-list picker and "Save ticker" |
| `save_saved.html` | `saved` | "GM read back in Fixture List at 2026-11-04T07:30:00Z." + the Watchlists return control |
| `save_rejected.html` | `rejected` | "Your account did not accept this save. Nothing is being retried." |
| `save_uncertain.html` | `uncertain` | "The save to Fixture List is unconfirmed. Check membership without saving again." + the membership-read control |
| `save_observed.html` | `observed` | "Your account currently contains this ticker. This read does not prove the earlier save." |

The `save-focus` force state is `focus(#prophet-save-dialog .prophet-save-head button)`:
it proves the candidate's own `:focus-visible` ring on the dialog's Close
control, in both themes, on desktop/en.

## What is real, and what is fixture

Real, byte-for-byte, hashed in `save-inputs.json`:

- `templates/prophet_save.css` and `templates/prophet_save.js`, copied from the
  template sources into the fixture (the built `site/` copies are byte-identical;
  both pairs of hashes are recorded).
- The rendered `<head>` of the real dashboard, the real built `theme.css` and
  `assets/css/*`, and the real page-level `<style>` blocks, so the light/dark
  axis and the card CSS are the candidate's own.
- The real `#us-standouts` / `#us-today` / `#us-today-grid` wrappers and the real
  Today card (GM, `as_of 2026-11-02`), extracted from the real dashboard render
  produced by `../render_public_fixture.py` from the real board, action board
  and Plan snapshot.
- The real `site/watchstore.js`.

Fixture, and stated as such:

- **The page is reduced.** Everything outside the Save surface (the 212-row
  stock table, the other panes, the footer) is dropped so the dialog is legible
  in a full-page capture. This is a presentation reduction, not a restyle: the
  card and its CSS are the real ones.
- **The account store is a stub** for the six session-requiring states. A
  signed-in session cannot be produced offline without inventing credentials,
  so those states install a local store implementing the same `WatchStore`
  surface the real one exposes (`checkedSession`, `lists.refresh`,
  `symbols.saveChecked`, `symbols.inspect`) and answering from a constant. It
  contacts no account and writes no list.
- **`save_signed_out.html` uses no stub at all.** The real `site/watchstore.js`
  answers `signed_out` for an anonymous page, and that is what the candidate
  actually does for a visitor.

Every activation in the fixture is a synthetic, untrusted DOM click, so the
page records no real pointer or key event. That is what lets the candidate's own
`dialog.querySelector('button').focus()` leave the Close control
`:focus-visible`, so the captured focus ring is the candidate's real focus
treatment rather than a forced class.

## NOT PROVEN

- **No signed-in account was contacted. No list was written. No membership was
  read from a real account.** Every session-requiring state above answers from
  the fixture store. The `saved`, `rejected`, `uncertain` and `observed` rows
  prove the candidate's *dialog contract* — which text, which controls and
  which no-retry behaviour appear in each outcome — and not that a real account
  behaves that way.
- **No served production or signed-in acceptance is claimed from this fixture.**
  Every cell was captured from a locally served fixture directory, anonymously,
  through `scripts/capture_page_evidence.py`.
- The manifest records the repository's own gated-access gap on every page:
  `access: free / essential / pro — "requires authenticated session; not
  automatable without approved fixtures"`.

### The next real-path gate for the authenticated Save

To close the authenticated half, run the same capture against a served build
with a real approved session, so that the candidate's own `site/watchstore.js`
supplies the account instead of the fixture store:

1. An approved authenticated fixture — a disposable account that owns at least
   one watchlist — authorised to run `scripts/capture_page_evidence.py` against
   `--base-url` of the served candidate, with the account's own session and no
   credential copied into the repo.
2. The real `WatchStore` then answers `ready`, `lists.refresh()` returns the
   account's real lists, and `symbols.saveChecked` performs the real write and
   the real read-back. The `choose`, `saved`, `rejected`, `uncertain` and
   `observed` states would then be captured from the real account's answers,
   with the real list names and a real `readBackAt`.
3. Until that run exists, the real Save path is **NOT_PROVEN** and this receipt
   must not be read as evidence for it.

## Reproducing

From the repository root:

```sh
proof=mockups/evidence/prophet-opportunity-workspace/save-visual-20261104-fabric
fixture=site/_tmp/prophet-save-visual-20261104-fabric
python3 "$proof/render_save_fixture.py" "$fixture" > "$proof/save-inputs.json"
python3 scripts/capture_page_evidence.py --repo macro --site-dir "$fixture" \
  --routes /save_signed_out.html,/save_unavailable.html,/save_empty_lists.html,/save_choose.html,/save_saved.html,/save_rejected.html,/save_uncertain.html,/save_observed.html \
  --viewports desktop,mobile --locales en,zh --themes light,dark \
  --force-state 'save-focus:focus(#prophet-save-dialog .prophet-save-head button)' \
  --output-dir "$proof/cells" --manifest "$proof/manifest.json" --smells "$proof/smells.json" \
  --settle-ms 1200 --as-of 2026-11-04T07:30:00Z --delay-ms 150
```

`render_save_fixture.py` renders the real dashboard through the sibling
`../render_public_fixture.py`, so the board, the action board and the Plan
snapshot it binds to are the ones this branch actually ships. The board vintage
it rendered is recorded in `save-inputs.json` as `board_as_of`.
