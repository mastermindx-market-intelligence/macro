/**
 * Catalyst selection design reference — not installed application code.
 *
 * Companion to Paper 01M6Y2VTQBVC9NA39HNG1DYWFH / p-3-0 / 10D-0.
 * Source compared: mastermind-terminal 3e2f8db782b0ba2f98343edf5199a4b8ce921ec9,
 * CatalystOpportunityView.tsx blob 1f8cc491040ebbf11851bca2759316406a55276b.
 *
 * The existing owner supplies read availability, authorized eligible cases,
 * validated requested identity, and the IDs produced by its existing filters.
 * This reference does not authenticate, filter, sort, fetch, store, navigate,
 * write the clipboard, schedule work, or create a lifecycle.
 *
 * Resolved includes successful ready/partial/stale/empty views admitted by that
 * owner. It must never be supplied for a loading, unavailable or denied read.
 * Cases are eligible watches, not the broader coverage inventory.
 */

const READ_STATES = new Set(["resolved", "pending", "unavailable", "auth", "access"]);

function requireId(value, label) {
  if (typeof value !== "string" || value.length === 0 || value.trim() !== value) {
    throw new TypeError(label + " must be a nonempty, exact identity");
  }
  return value;
}

function projection(kind, requestedId, visibleCases, selected = null, outsideFilters = false) {
  return Object.freeze({
    kind,
    requestedId,
    visibleCases: Object.freeze(visibleCases),
    selected,
    selectionMode: selected === null ? null : requestedId === null ? "default" : "explicit",
    outsideFilters,
    copyThemeId: selected === null ? null : selected.theme_id,
  });
}

/**
 * Derive the list/detail relationship from one existing-owner read.
 *
 * Row objects are returned by identity from cases. The caller must treat the
 * authorized snapshot and its rows as immutable; this function does not freeze
 * or mutate caller-owned rows. visibleThemeIds carries the
 * incumbent filter owner's order; this function never recomputes filtering or
 * ranking. A requested case outside that list remains selected.
 *
 * Invalid resolved inputs throw instead of masquerading as a missing case.
 * Blocked reads ignore stale cases, visible IDs and requested-detail output.
 * The existing owner retains its URL/requested identity separately. In a
 * resolved input only explicit null means no request; omission is an error.
 */
export function deriveCaseSelection({
  readState,
  cases,
  visibleThemeIds,
  requestedId,
}) {
  if (!READ_STATES.has(readState)) throw new TypeError("Unknown readState");
  if (readState !== "resolved") return projection(readState, null, []);
  if (requestedId !== null) requireId(requestedId, "requestedId");

  if (!Array.isArray(cases) || !Array.isArray(visibleThemeIds)) {
    throw new TypeError("Resolved cases and visibleThemeIds must be arrays");
  }
  const byId = new Map();
  for (const row of cases) {
    if (row === null || typeof row !== "object" || Array.isArray(row)) {
      throw new TypeError("Each case must be a source row");
    }
    const id = requireId(row.theme_id, "case.theme_id");
    if (byId.has(id)) throw new TypeError("Duplicate eligible case: " + id);
    byId.set(id, row);
  }

  const visibleIds = new Set();
  const visibleCases = visibleThemeIds.map((value) => {
    const id = requireId(value, "visibleThemeId");
    if (visibleIds.has(id)) throw new TypeError("Duplicate visible case: " + id);
    if (!byId.has(id)) throw new TypeError("Visible case is outside the authorized view: " + id);
    visibleIds.add(id);
    return byId.get(id);
  });

  if (requestedId !== null) {
    const selected = byId.get(requestedId);
    if (selected === undefined) return projection("missing", requestedId, visibleCases);
    return projection("selected", requestedId, visibleCases, selected, !visibleIds.has(requestedId));
  }

  if (visibleCases.length === 0) return projection("none", null, visibleCases);
  return projection("selected", null, visibleCases, visibleCases[0], false);
}

/**
 * A pure eligibility check for displaying a clipboard completion status.
 *
 * completion: { attempt, readContext, themeId }
 * current:    { attempt, readContext, selection }
 *
 * Tokens are supplied by the existing owner. An attempt must be retired on a
 * later attempt, explicit selection/history change, authorized-read change,
 * or owner unmount/disposal,
 * even if the user later returns to the same theme. A readContext represents
 * identity + read/revision context; a content generation alone is insufficient.
 *
 * This predicate does not mint or retire tokens, deduplicate notifications,
 * cancel a clipboard effect, retry it, or write a replacement link. Apply it
 * equally to success and failure messages. It does not establish write success,
 * actual clipboard contents, URL construction or host lifecycle retirement.
 * The current address-bar failure fallback is not qualified here: a default
 * case may not be in that URL. The host must expose its exact constructed case
 * URL if it offers a manual-link fallback.
 */
export function isCopyCompletionCurrent(completion, current) {
  if (!completion || !current) return false;
  if (completion.attempt == null || completion.readContext == null) return false;
  if (current.attempt == null || current.readContext == null) return false;
  const selection = current.selection;
  return completion.attempt === current.attempt
    && completion.readContext === current.readContext
    && typeof completion.themeId === "string"
    && completion.themeId.length > 0
    && selection?.kind === "selected"
    && selection.copyThemeId === completion.themeId
    && selection.selected?.theme_id === completion.themeId;
}

