/**
 * T47 ranked-search transition reference, 9 November 2026.
 *
 * This is a pure design reference, not an installed application component.
 * The accepted host, DOM adapter and runtime fit remain unqualified.
 *
 * The caller supplies its existing row identities, display groups and snapshot
 * identity. The reference never derives rank, sorts, fetches, stores, navigates,
 * operates on the DOM or changes source data.
 *
 * Integration rules:
 * - Map group from the host's existing primary/secondary disclosure structure.
 * - Start a new state explicitly when the source inventory identity changes.
 * - Render with the existing list, disclosure, count status and focus owner.
 * - Before hiding a focused control, move focus to the existing search input.
 * - Clear requests that input's focus; typing does not request focus or scroll.
 * - Keep enhancement inactive until inventory validation/handlers succeed.
 * - Empty supplied rows do not establish ready-empty, loading or unavailable;
 *   the existing host must classify source availability before rendering copy.
 * - A primary-only positive match withholds the empty secondary group. This is
 *   an explicit additional reference decision, not a claim about installed UI.
 * - On initialization failure, retain the original browsable list/disclosure.
 * - Empty Escape remains untouched; nonempty Escape dispatches clear.
 * - Enter must not submit/navigate. Keyboard/DOM behavior is not tested here.
 *
 * A query is literal and case-insensitive. Whitespace is not trimmed, and
 * regular-expression characters have no special meaning.
 */

function requireBoolean(value, name) {
  if (typeof value !== "boolean") throw new TypeError(name + " must be boolean");
}

function requireInventoryKey(value) {
  if (typeof value !== "string" || value.length === 0) {
    throw new TypeError("inventoryKey must be a nonempty host-supplied identity");
  }
}

function validateState(state) {
  if (!state || typeof state !== "object") throw new TypeError("state is required");
  requireInventoryKey(state.inventoryKey);
  if (typeof state.query !== "string") throw new TypeError("query must be a string");
  requireBoolean(state.expanded, "expanded");
  if (state.query.length === 0) {
    if (state.beforeSearchOpen !== null) {
      throw new TypeError("empty query must not retain a search baseline");
    }
  } else {
    requireBoolean(state.beforeSearchOpen, "beforeSearchOpen");
  }
}

function validateRows(rows) {
  if (!Array.isArray(rows)) throw new TypeError("rows must be an array");
  const ids = new Set();
  for (const row of rows) {
    if (!row || typeof row !== "object" ||
        typeof row.id !== "string" || row.id.length === 0 || ids.has(row.id)) {
      throw new TypeError("rows require unique, nonempty host IDs");
    }
    ids.add(row.id);
    if (row.group !== "primary" && row.group !== "secondary") {
      throw new TypeError("row group must come from the existing disclosure");
    }
    for (const field of ["symbol", "name"]) {
      if (row[field] != null && typeof row[field] !== "string") {
        throw new TypeError(field + " must be a string or missing");
      }
    }
  }
}

function literalMatch(row, query) {
  const needle = query.toLowerCase();
  return (row.symbol ?? "").toLowerCase().includes(needle) ||
    (row.name ?? "").toLowerCase().includes(needle);
}

/**
 * Row input: { id: string, group: "primary" | "secondary",
 *              symbol?: string | null, name?: string | null, ...sourceFields }
 * Other source fields, including rank and missing values, are never rewritten.
 * The state is returned to the caller; this module owns no store.
 */
export function createRankedSearchState({ inventoryKey, expanded }) {
  requireInventoryKey(inventoryKey);
  requireBoolean(expanded, "expanded");
  return Object.freeze({
    inventoryKey,
    query: "",
    expanded,
    beforeSearchOpen: null,
  });
}

/**
 * Projection preserves the supplied object identities and order.
 * matchCount covers all supplied groups, including collapsed matching rows.
 * A disclosure is shown only when it has rows to reveal.
 */
export function projectRankedSearch({ rows, state, inventoryKey }) {
  validateRows(rows);
  validateState(state);
  requireInventoryKey(inventoryKey);
  if (inventoryKey !== state.inventoryKey) {
    throw new Error("inventory changed; initialize explicitly from the new host view");
  }

  const searching = state.query.length > 0;
  const matchingRows = searching
    ? rows.filter((row) => literalMatch(row, state.query))
    : rows.slice();
  const hasSecondaryMatches = matchingRows.some((row) => row.group === "secondary");
  const disclosureVisible = hasSecondaryMatches;
  const disclosureOpen = disclosureVisible && state.expanded;
  const visibleRows = matchingRows.filter(
    (row) => row.group === "primary" || disclosureOpen
  );

  return {
    searching,
    controlsAvailable: rows.length > 0,
    totalCount: rows.length,
    matchCount: matchingRows.length,
    noRows: rows.length === 0,
    noMatches: rows.length > 0 && searching && matchingRows.length === 0,
    disclosureVisible,
    disclosureOpen,
    matchingRows,
    visibleRows,
  };
}

/**
 * Events:
 * - { type: "query", value: string } for input changes
 * - { type: "clear" } for the existing Clear action/nonempty Escape
 * - { type: "disclosure", open: boolean } for the existing native control
 *
 * Programmatic query auto-opening never overwrites beforeSearchOpen.
 * A stale disclosure event from a hidden control is ignored.
 */
export function transitionRankedSearch({ rows, state, inventoryKey, event }) {
  const before = projectRankedSearch({ rows, state, inventoryKey });
  if (!event || typeof event !== "object") throw new TypeError("event is required");

  let next = { ...state };
  let focus = null;
  let handled = true;

  if (event.type === "query" || event.type === "clear") {
    const query = event.type === "clear" ? "" : event.value;
    if (typeof query !== "string") throw new TypeError("query must be a string");
    const entering = !before.searching && query.length > 0;
    const leaving = before.searching && query.length === 0;
    if (entering) next.beforeSearchOpen = state.expanded;
    if (leaving) {
      next.expanded = state.beforeSearchOpen;
      next.beforeSearchOpen = null;
    }
    next.query = query;
    if (query.length > 0 && query !== state.query) {
      const hasMatchingSecondary = rows.some(
        (row) => row.group === "secondary" && literalMatch(row, query)
      );
      if (hasMatchingSecondary) next.expanded = true;
    }
    if (event.type === "clear" && rows.length > 0) focus = "search-input";
  } else if (event.type === "disclosure") {
    requireBoolean(event.open, "event.open");
    if (before.disclosureVisible) next.expanded = event.open;
    else handled = false;
  } else {
    throw new TypeError("unsupported event type");
  }

  next = Object.freeze(next);
  return {
    state: next,
    projection: projectRankedSearch({ rows, state: next, inventoryKey }),
    focus,
    handled,
  };
}

