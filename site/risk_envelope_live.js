/* risk_envelope_live.js — GD-3: paint a live-provisional overlay on the settled Risk
   Envelope band (macro.html #risk-envelope-band), polling site/live/risk_envelope.json
   (written by scripts/build_live_risk_envelope.py during market hours). Modeled closely
   on risk_state_live.js: same poll-interval idiom, cache:"no-store", every fetch/parse
   error swallowed silently (an anonymous 401 on a tier-gated live artifact must stay
   quiet — the settled band underneath is always a complete, correct read on its own).

   Display/advisory only. The overlay paints ONLY when every identity + freshness check
   below holds; otherwise the pre-baked hidden hooks stay hidden and the settled band is
   the whole story. No falsifier/refutation vocabulary; stage vocabulary (NONE/FRAGILE/
   TRANSMITTING/BREAKDOWN) is written ONLY into the drawer's machine receipt, never into
   the glance-tier chip/pending copy. */
(function () {
  "use strict";
  var FEED_URL = "live/risk_envelope.json";
  var POLL = (window.LIVE_POLL_SEC && +window.LIVE_POLL_SEC) || 60;

  /* Older rendered pages may still contain the standalone band. Move that same
     node (including all live identities) into optional Risk Radar detail. New
     server renders already place the compact context there. Never clone a feed
     consumer or leave a second first-level panel. */
  function relocateLegacyEnvelope() {
    var band = document.getElementById("risk-envelope-band");
    if (!band || band.closest("#dlg-risk")) return;
    var body = document.querySelector("#dlg-risk .mx5-dlg-body");
    if (!body) { band.hidden = true; band.style.display = "none"; return; }
    var detail = document.createElement("details");
    detail.className = "mx-disc riskdlg-envelope-legacy";
    var summary = document.createElement("summary");
    var en = document.createElement("span"), zh = document.createElement("span");
    en.className = "l-en"; en.textContent = "Market internals · trend and stress";
    zh.className = "l-zh"; zh.textContent = "市场内部 · 趋势与压力";
    summary.appendChild(en); summary.appendChild(zh);
    detail.appendChild(summary);
    body.insertBefore(detail, body.querySelector(".riskdlg-drivers"));
    band.classList.remove("panel", "span12");
    detail.appendChild(band);
  }

  var lastLiveFeed = null, hadLive = false, requestPending = false;
  // Per-page ordering fence in this existing reader, not a retained warning or
  // a source freshness clock. Keep it through unpaint so delayed responses do
  // not undo newer evidence. `built` only orders publications within a session.
  var latestPaintedOrder = null;

  function contextCopy() {
    var el = document.getElementById("gde-context-copy");
    if (!el) return null;
    try { return JSON.parse(el.textContent); } catch (e) { return null; }
  }

  function textPair(el, pair) {
    if (!el) return;
    [".l-en", ".l-zh"].forEach(function (selector, i) {
      var node = el.querySelector(selector);
      if (node && node.textContent !== pair[i]) node.textContent = pair[i];
    });
  }

  /* ── Chairman 2026-10-15 bounded foreground slice ──
     The page carries ONE pre-gauge summary (#risk-response-summary) beside the
     settled band. It reuses this module's existing contextView qualification and
     the single existing poller — no new fetch, timer, storage or event plane, and
     no second envelope in the copy JSON. Before the first foreground paint the
     server-rendered text/hidden/data-state are snapshotted ONCE into these
     ephemeral variables; unpaint() restores exactly that DOM. Pages without the
     nodes no-op. */
  var FG_IDS = ["risk-response-title", "risk-response-cause", "risk-response-action", "risk-response-date"];
  var fgSaved = null, fgUnresolvedRisk = false;

  function fgSave() {
    if (fgSaved) return;
    var sec = document.getElementById("risk-response-summary");
    if (!sec) return;
    fgSaved = {hidden: sec.hidden, state: sec.getAttribute("data-state"),
      expectedSession: sec.getAttribute("data-expected-session") || "", text: {}};
    FG_IDS.forEach(function (id) {
      var el = document.getElementById(id);
      fgSaved.text[id] = el ? [".l-en", ".l-zh"].map(function (selector) {
        var node = el.querySelector(selector);
        return node ? node.textContent : null;
      }) : null;
    });
  }

  // Mirror the already-qualified foreground action into the existing action
  // card. Base copy stays on that DOM node so either existing reader may update
  // first. No added source, listener, timer, persistence or trading authority.
  function syncPrimaryAction() {
    if (typeof document.querySelector !== "function") return;
    var label = document.querySelector("[data-wtd-primary] .mx5-action-label");
    if (!label) return;
    var base = [label.getAttribute("data-wtd-base-en"), label.getAttribute("data-wtd-base-zh")];
    var verdict = label.getAttribute("data-wtd-base-verdict");
    if (!base[0] || !base[1] || !verdict) return;
    var selected = base, summary = document.getElementById("risk-response-summary");
    if (verdict !== "RISK_OFF" && summary && !summary.hidden &&
        ["warning", "partial-warning", "checking", "unavailable"].indexOf(summary.getAttribute("data-state")) >= 0) {
      var action = document.getElementById("risk-response-action");
      var en = action && action.querySelector(".l-en"), zh = action && action.querySelector(".l-zh");
      if (en && zh && en.textContent && zh.textContent) selected = [en.textContent, zh.textContent];
    }
    textPair(label, selected);
    var icon = document.querySelector("[data-wtd-primary] .mx5-action-icon");
    if (icon && icon.style) icon.style.display = selected === base ? "" : "none";
  }

  function restoreForeground() {
    if (!fgSaved) return;
    var sec = document.getElementById("risk-response-summary");
    if (!sec) { fgSaved = null; return; }
    sec.hidden = fgSaved.hidden;
    if (fgSaved.state === null) sec.removeAttribute("data-state");
    else sec.setAttribute("data-state", fgSaved.state);
    FG_IDS.forEach(function (id) {
      var el = document.getElementById(id), saved = fgSaved.text[id];
      if (!el || !saved) return;
      textPair(el, [saved[0] || "", saved[1] || ""]);
    });
    /* A failed/expired feed is not recovery. Never restore a prior quiet
       snapshot as an all-clear after a qualified live warning. Retain only
       the dated settled context; this is not a new alert-retention store. */
    if (fgUnresolvedRisk && fgSaved.state === "quiet") {
      var config = contextCopy(), copy = config && config.copy;
      if (!copy) return;
      var fg = copy.foreground || {};
      sec.hidden = false; sec.setAttribute("data-state", "unavailable");
      textPair(document.getElementById("risk-response-title"), fg.unavailable_title || copy.unknown);
      textPair(document.getElementById("risk-response-cause"), ["", ""]);
      textPair(document.getElementById("risk-response-action"), fg.unavailable_action || copy.unknown);
      var savedDate = fgSaved.text["risk-response-date"];
      if ((!savedDate || !savedDate[0]) && fgSaved.expectedSession) {
        var label = fg.settled_label || ["Settled: ", "收盘："];
        textPair(document.getElementById("risk-response-date"),
          [label[0] + fgSaved.expectedSession, label[1] + fgSaved.expectedSession]);
      }
    }
    syncPrimaryAction();
  }

  /* Same cause qualification the settled band applies, tightened for the glance
     tier: the source must own its date (as_of equals the feed's own source_session),
     so carried prior-session leadership is never projected as a fresh current
     warning. */
  function fgCauses(d, copy) {
    var hz = d.hazard_summary || {};
    var contributing = Array.isArray(hz.contributing_sources) ? hz.contributing_sources : [];
    var sources = (d.provenance || {}).sources || [];
    var rows = [[], []];
    if (!Array.isArray(sources) || typeof d.source_session !== "string" || !d.source_session) return rows;
    sources.forEach(function (source) {
      if (!source || source.role !== "hazard_evidence" || source.coverage !== "FRESH" ||
          contributing.indexOf(source.source_id) < 0 ||
          ["FRAGILE", "TRANSMITTING", "BREAKDOWN"].indexOf(source.hazard_stage) < 0 ||
          !Object.prototype.hasOwnProperty.call(copy.source_states, source.state) ||
          typeof source.as_of !== "string" || !source.as_of || source.as_of !== d.source_session ||
          sources.filter(function (other) { return other && other.source_id === source.source_id; }).length !== 1) return;
      var detail = source.detail || {};
      var name = [source.label_en || copy.source[0], source.label_zh || source.label_en || copy.source[1]];
      if (detail.cohort_role === "tracked_ai_hardware_damage_monitor") name = copy.ai_leaders;
      else if (source.source_id === "risk-radar-us") name = [detail.label_en || name[0], detail.label_zh || name[1]];
      var word = copy.source_states[source.state];
      rows[0].push(name[0] + ": " + word[0]); rows[1].push(name[1] + "：" + word[1]);
    });
    return rows;
  }

  /* Foreground presentation state from the already-qualified view plus the
     source-owned source_session (never built/event time): checking while a
     transition is unconfirmed; warning only on the engine's own stage WITH fully
     qualified causes; quiet (hidden) only on a current NONE; partial-warning only
     on the recognized coverage/mapping gap the band already accepts; anything
     unknown, malformed or ungrounded renders unavailable — never an all-clear. */
  function publicationUsDay(d) {
    // Causality ceiling only: a US observation cannot belong to a calendar day
    // after its own publication. This is not an exchange-session/freshness SLA.
    if (!d || typeof d.built !== "string") return "";
    var stamp = Date.parse(d.built.replace(" UTC", "Z").replace(" ", "T"));
    if (!isFinite(stamp)) return "";
    try {
      var parts = new Intl.DateTimeFormat("en-US", {timeZone: "America/New_York",
        year: "numeric", month: "2-digit", day: "2-digit"}).formatToParts(new Date(stamp));
      var fields = {};
      parts.forEach(function (part) { fields[part.type] = part.value; });
      return fields.year + "-" + fields.month + "-" + fields.day;
    } catch (e) { return ""; }
  }

  function foregroundView(d, copy) {
    var fgc = copy.foreground || {};
    var hz = d.hazard_summary || {};
    var view = contextView(d, copy);
    var session = (typeof d.source_session === "string" && /^\d{4}-\d{2}-\d{2}$/.test(d.source_session)) ? d.source_session : "";
    var summary = document.getElementById("risk-response-summary");
    var expected = summary && summary.getAttribute("data-expected-session");
    var publicationDay = publicationUsDay(d);
    // Reject an explicitly foreign owner or a source older than the independent
    // calendar expectation. A newly generated wrapper cannot refresh either.
    if ((Object.prototype.hasOwnProperty.call(d, "market") && d.market !== "US") ||
        !publicationDay || !session || session > publicationDay ||
        (expected && session < expected))
      return {state: "unavailable", title: fgc.unavailable_title || copy.unknown,
        cause: ["", ""], action: fgc.unavailable_action || copy.unknown, date: ""};
    var partialGrounds = hz.stage === null && (hz.stage_reason === "required_coverage_unavailable" ||
      hz.stage_reason === "required_source_state_unmapped");
    var rows = fgCauses(d, copy);
    var warningTitle = fgc.warning_title || copy.partial_warning;
    var warningAction = fgc.warning_action || copy.partial_warning;
    if (view.pending) return {state: "checking", title: fgc.checking_title || copy.checking,
      cause: ["", ""], action: fgc.checking_action || copy.checking, date: session};
    if (["FRAGILE", "TRANSMITTING", "BREAKDOWN"].indexOf(view.stage) >= 0 && rows[0].length && session)
      return {state: "warning", title: warningTitle, cause: [rows[0].join(" · "), rows[1].join(" · ")],
        action: warningAction, date: session};
    if (view.stage === "NONE" && session && (d.measured_state || {}).usable === true) return {state: "quiet"};
    if (partialGrounds && rows[0].length && session)
      return {state: "partial-warning", title: warningTitle,
        cause: [(fgc.partial_prefix || copy.partial_hint)[0] + rows[0].join(" · "),
                (fgc.partial_prefix || copy.partial_hint)[1] + rows[1].join(" · ")],
        action: warningAction, date: session};
    return {state: "unavailable", title: fgc.unavailable_title || copy.unknown,
      cause: ["", ""], action: fgc.unavailable_action || copy.unknown, date: ""};
  }

  function paintForeground(d, preserveSettledDate) {
    var sec = document.getElementById("risk-response-summary");
    if (!sec) return;
    fgSave();
    var config = contextCopy();
    if (!config || !config.copy) return;
    var view = foregroundView(d, config.copy);
    var fgc = config.copy.foreground || {};
    if (view.state === "quiet") {
      fgUnresolvedRisk = false;
      sec.setAttribute("data-state", "quiet");
      sec.hidden = true;
      syncPrimaryAction();
      return;
    }
    if (["warning", "partial-warning", "checking"].indexOf(view.state) >= 0) fgUnresolvedRisk = true;
    sec.hidden = false;
    sec.setAttribute("data-state", view.state);
    textPair(document.getElementById("risk-response-title"), view.title);
    textPair(document.getElementById("risk-response-cause"), view.cause);
    textPair(document.getElementById("risk-response-action"), view.action);
    var label = fgc.source_label || ["Source session: ", "来源交易日："];
    if (view.date || !preserveSettledDate)
      textPair(document.getElementById("risk-response-date"), view.date ? [label[0] + view.date, label[1] + view.date] : ["", ""]);
    syncPrimaryAction();
  }

  // Present source-owned states; never compute a score, action or dwell threshold.
  function contextView(d, copy) {
    var hz = d.hazard_summary || {}, trans = d.live_transition || {};
    var originalStage = hz.stage;
    var stage = Object.prototype.hasOwnProperty.call(copy.hazard, hz.stage) ? hz.stage : null;
    var pending = trans.pending != null, p = trans.pending || {};
    if (stage !== null && (trans.candidate_stage !== stage ||
        (!pending && trans.stable_stage !== stage) ||
        (pending && (p.stage !== stage || trans.stable_stage === stage ||
          !Number.isInteger(p.ticks) || !Number.isInteger(p.needs) || p.ticks < 1 || p.needs <= p.ticks ||
          (trans.stable_stage !== null && !Object.prototype.hasOwnProperty.call(copy.hazard, trans.stable_stage)))))) stage = null;
    if (stage === null) pending = false;
    var causes = [[], []], sourceLines = [[], []];
    var contributing = Array.isArray(hz.contributing_sources) ? hz.contributing_sources : [];
    var sources = (d.provenance || {}).sources || [];
    if (stage !== null && Array.isArray(sources)) sources.forEach(function (source) {
      if (!source || source.role !== "hazard_evidence" || source.coverage !== "FRESH" ||
          contributing.indexOf(source.source_id) < 0 ||
          ["FRAGILE", "TRANSMITTING", "BREAKDOWN"].indexOf(source.hazard_stage) < 0) return;
      var detail = source.detail || {};
      var name = [source.label_en || copy.source[0], source.label_zh || copy.source[1]];
      if (detail.cohort_role === "tracked_ai_hardware_damage_monitor") name = copy.ai_leaders;
      else if (source.source_id === "risk-radar-us") name = [detail.label_en || name[0], detail.label_zh || name[1]];
      var word = copy.source_states[source.state] || copy.source_missing;
      causes[0].push(name[0] + ": " + word[0]); causes[1].push(name[1] + "：" + word[1]);
    });
    /* Partial read: the engine already preserved contributing_sources when the combined
       stage is null for a recognized coverage/mapping gap. A source-native cause may
       stand in only when it is complete on its own — fresh this session (as_of equals
       d.source_session), attributed, and carrying its own known state copy. A stage
       nulled out of a NON-null summary by malformed live-transition metadata never
       qualifies, and the aggregate is never promoted from these causes. */
    if (originalStage === null && (hz.stage_reason === "required_coverage_unavailable" ||
        hz.stage_reason === "required_source_state_unmapped") && Array.isArray(sources))
      sources.forEach(function (source) {
        if (!source || source.role !== "hazard_evidence" || source.coverage !== "FRESH" ||
            contributing.indexOf(source.source_id) < 0 ||
            ["FRAGILE", "TRANSMITTING", "BREAKDOWN"].indexOf(source.hazard_stage) < 0 ||
            !Object.prototype.hasOwnProperty.call(copy.source_states, source.state) ||
            typeof source.as_of !== "string" || !source.as_of || source.as_of !== d.source_session ||
            sources.filter(function (other) { return other && other.source_id === source.source_id; }).length !== 1) return;
        var detail = source.detail || {};
        var name = [source.label_en || copy.source[0], source.label_zh || copy.source[1]];
        if (detail.cohort_role === "tracked_ai_hardware_damage_monitor") name = copy.ai_leaders;
        else if (source.source_id === "risk-radar-us") name = [detail.label_en || name[0], detail.label_zh || name[1]];
        var word = copy.source_states[source.state];
        causes[0].push(name[0] + ": " + word[0]); causes[1].push(name[1] + "：" + word[1]);
      });
    if (Array.isArray(sources)) sources.forEach(function (source) {
      if (!source) return;
      var label = [source.label_en || copy.source[0], source.label_zh || copy.source[1]];
      var word = copy.source_states[source.state] || [source.state || copy.source_missing[0], source.state || copy.source_missing[1]];
      var coverage = (copy.coverage || {})[source.coverage] || copy.source_missing;
      sourceLines[0].push(label[0] + ": " + word[0] + " · " + (source.as_of || "—") + " · " + coverage[0]);
      sourceLines[1].push(label[1] + "：" + word[1] + " · " + (source.as_of || "—") + " · " + coverage[1]);
    });
    return {stage: stage, pending: pending, label: copy.hazard[stage] || copy.unknown,
      hint: pending ? copy.checking : (copy.hint[stage] ||
        (causes[0].length ? (copy.partial_warning || copy.partial_hint) : copy.partial_hint)),
      causes: [causes[0].join(" · "), causes[1].join(" · ")],
      sourceLines: [sourceLines[0].join("\n"), sourceLines[1].join("\n")]};
  }

  function paintContext(d) {
    var config = contextCopy();
    if (!config || !config.copy) return;
    var copy = config.copy, view = contextView(d, copy);
    var heading = view.pending ? (copy.live_pending || copy.checking) : copy.live;
    textPair(document.getElementById("gde-live-stage"), [heading[0] + ": " + view.label[0], heading[1] + "：" + view.label[1]]);
    textPair(document.getElementById("gde-live-cause"), view.causes);
    textPair(document.getElementById("gde-live-source-rows"), view.sourceLines);
    var sources = document.getElementById("gde-live-sources");
    if (sources) sources.hidden = false;
    var row = document.getElementById("gde-live-reading");
    if (row) row.hidden = false;
    var fallback = document.getElementById("gde-live-fallback");
    if (fallback) fallback.hidden = true;
    var hint = document.getElementById("gde-button-context");
    if (hint) {
      var words = view.pending ? view.hint : (view.stage === "NONE" ? view.label : view.hint);
      textPair(hint, ["Live: " + words[0], "实时：" + words[1]]);
      hint.setAttribute("data-gde-stage", view.stage || "UNKNOWN");
      hint.hidden = false;
    }
  }

  function restoreContext(showFallback) {
    var sources = document.getElementById("gde-live-sources");
    if (sources) sources.hidden = true;
    var row = document.getElementById("gde-live-reading");
    if (row) row.hidden = true;
    var fallback = document.getElementById("gde-live-fallback");
    if (fallback) fallback.hidden = !(hadLive && showFallback);
    var config = contextCopy(), hint = document.getElementById("gde-button-context");
    if (config && config.copy && hint) {
      /* The settled render bakes the hint the button actually shipped (possibly the
         qualified partial warning); older pages without the key fall back to the
         stage enum exactly as before. */
      var settled = config.settled_hint;
      if (!Array.isArray(settled) || settled.length !== 2 || typeof settled[0] !== "string" || typeof settled[1] !== "string")
        settled = config.copy.hint[config.settled_stage] || config.copy.partial_hint;
      textPair(hint, settled);
      hint.setAttribute("data-gde-stage", config.settled_stage || "UNKNOWN");
      hint.hidden = config.settled_stage === "NONE";
    }
    lastLiveFeed = null;
  }

  function unpaint(showFallback) {
    restoreContext(showFallback);
    restoreForeground();
    var chip = document.getElementById("gde-live-chip");
    var pending = document.getElementById("gde-pending-chip");
    var receipt = document.getElementById("gde-live-receipt");
    if (chip) chip.hidden = true;
    if (pending) pending.hidden = true;
    if (receipt) { receipt.hidden = true; receipt.textContent = ""; }
  }

  /* Healthy live overlay. Every call re-asserts the chip's baked copy — never
     relies on the DOM still holding it from a render or a prior tick, since
     paintDegraded() below overwrites it and a paint()->degraded->paint() cycle
     must not leave the degraded copy stuck (adjudication #4). */
  function paint(d, band) {
    lastLiveFeed = d; hadLive = true;
    paintContext(d);
    paintForeground(d);
    var chip = document.getElementById("gde-live-chip");
    var pending = document.getElementById("gde-pending-chip");
    var receipt = document.getElementById("gde-live-receipt");

    if (chip) {
      var enEl = chip.querySelector(".l-en"), zhEl = chip.querySelector(".l-zh");
      if (enEl) enEl.textContent = "Live · provisional";
      if (zhEl) zhEl.textContent = "实时 · 临时";
      var t = chip.querySelector(".gde-live-time");
      if (t) t.textContent = "· " + (d.built || "").slice(11, 16) + " UTC";
      chip.hidden = false;
    }

    var trans = d.live_transition || {};
    if (pending) {
      if (trans.pending && trans.pending.stage) {
        var needs = trans.pending.needs || "?";
        var ticks = trans.pending.ticks || 0;
        var en = pending.querySelector(".l-en"), zh = pending.querySelector(".l-zh");
        if (en) en.textContent = "· live read shifting · confirming " + ticks + "/" + needs;
        if (zh) zh.textContent = "· 实时读数变化 · 确认中 " + ticks + "/" + needs;
        pending.hidden = false;
      } else {
        pending.hidden = true;
      }
    }

    if (receipt) {
      var bundle = (d.bundle_id || "").slice(0, 8);
      var line = "live: candidate " + (trans.candidate_stage == null ? "null" : trans.candidate_stage) +
                  " · stable " + (trans.stable_stage == null ? "null" : trans.stable_stage) +
                  " · pending " + (trans.pending ? (trans.pending.ticks + "/" + trans.pending.needs) : "0/0") +
                  " · built " + (d.built || "—") +
                  " · bundle " + (bundle || "—");
      receipt.textContent = line;
      receipt.hidden = false;
    }
  }

  /* DEGRADED live state (outage / null candidate): chip stays visible with a
     "not enough to say" plain-word read; pending never shows on a null candidate
     (freeze §GD-3: a null candidate never ticks in any direction). The receipt
     must never keep showing a stale HEALTHY line beside degraded chip copy
     (adjudication #4), so it is overwritten with a matching degraded receipt
     rather than left as whatever paint() last wrote. */
  function paintDegraded(d) {
    lastLiveFeed = d; hadLive = true;
    paintContext(d);
    paintForeground(d);
    var chip = document.getElementById("gde-live-chip");
    var pending = document.getElementById("gde-pending-chip");
    var receipt = document.getElementById("gde-live-receipt");
    if (chip) {
      var enEl = chip.querySelector(".l-en"), zhEl = chip.querySelector(".l-zh");
      if (enEl) enEl.textContent = "Live · not enough to say";
      if (zhEl) zhEl.textContent = "实时 · 暂无法判断";
      var t = chip.querySelector(".gde-live-time");
      if (t) t.textContent = "";
      chip.hidden = false;
    }
    if (pending) pending.hidden = true;
    if (receipt) {
      var trans = d.live_transition || {};
      var bundle = (d.bundle_id || "").slice(0, 8);
      receipt.textContent = "live: candidate null · stable " +
        (trans.stable_stage == null ? "null" : trans.stable_stage) +
        " · degraded (" + (d.data_state || "unknown") + ") · built " + (d.built || "—") +
        " · bundle " + (bundle || "—");
      receipt.hidden = false;
    }
  }

  function active(d, band) {
    if (!d || d.schema !== "mastermind.risk_envelope/v1") return false;
    if (d.revision !== "live_provisional") return false;
    if (d.precedence !== "live") return false;
    var wantBundle = band.getAttribute("data-bundle-id");
    var overlays = d.overlays || {};
    if (!wantBundle || overlays.settled_bundle_id !== wantBundle) return false;
    if (d.live_active !== true) return false;
    var built = d.built ? Date.parse(d.built.replace(" UTC", "Z").replace(" ", "T")) : NaN;
    var horizonMin = (typeof d.stale_after_min === "undefined") ? 5 : d.stale_after_min;
    if (typeof horizonMin !== "number" || !isFinite(horizonMin) || horizonMin <= 0 || !isFinite(built) || built > Date.now() ||
        (Date.now() - built) > horizonMin * 60 * 1000) return false;
    /* Feed-behind-the-render floor (same law as risk_state_live.js): a live read
       older than the page's baked settled session must never paint — that would
       look fresher/looser than a stale read actually is. */
    var floor = band.getAttribute("data-settled-session") || "";
    if (floor && (typeof d.source_session !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(d.source_session) || d.source_session < floor)) return false;
    return true;
  }

  /* The one entry point that decides paint vs. degraded vs. unpaint for a
     PARSED feed object — factored out of tick()'s fetch chain so the shipped
     module is directly testable (tests/test_risk_state_live_session_floor.py
     drives risk_state_live.js the same way: strip the auto-run tail, call the
     entry function with a fixture feed, read the DOM back). No behavior change
     from inlining it in tick() — same band lookup, same try/catch-to-unpaint. */
  function applyFeed(d) {
    var band = document.getElementById("risk-envelope-band");
    if (!band) return;
    try {
      if (!d) { unpaint(true); return; }
      if (active(d, band)) {
        var foreground = document.getElementById("risk-response-summary");
        var expected = foreground && foreground.getAttribute("data-expected-session");
        var publicationDay = publicationUsDay(d);
        if ((Object.prototype.hasOwnProperty.call(d, "market") && d.market !== "US") ||
            !publicationDay || !d.source_session || d.source_session > publicationDay ||
            (expected && d.source_session < expected)) {
          // Neither the dialog nor the ordering fence may adopt a different
          // market or an observation rejected by this page's session floor.
          unpaint(true);
          paintForeground(d, true);
          return;
        }
        var order = {session: d.source_session,
          published: Date.parse(d.built.replace(" UTC", "Z").replace(" ", "T")),
          content: JSON.stringify(d)};
        if (latestPaintedOrder && (order.session < latestPaintedOrder.session ||
            (order.session === latestPaintedOrder.session &&
              (order.published < latestPaintedOrder.published ||
               (order.published === latestPaintedOrder.published && order.content !== latestPaintedOrder.content))))) return;
        // An identical still-fresh response may repaint after a transient outage;
        // changed content at the same publication identity is not a new recovery.
        /* Route on the ENVELOPE's own hazard stage alone (adjudication #8):
           a null stage means "not enough to say" regardless of what
           data_state happens to read (FRESH-but-null is exactly the shape a
           laundered empty live block used to produce) — never gate degraded
           copy on data_state, which is a coverage grade, not a knowability
           verdict. */
        var stage = ((d.hazard_summary || {}).stage);
        var config = contextCopy();
        var unreadable = config && config.copy && contextView(d, config.copy).stage === null;
        if (["NONE", "FRAGILE", "TRANSMITTING", "BREAKDOWN"].indexOf(stage) < 0 || unreadable) {
          paintDegraded(d);
        } else {
          paint(d, band);
        }
        latestPaintedOrder = order;
      } else {
        unpaint(!(d.live_active === false || d.precedence === "settled"));
      }
    } catch (e) { unpaint(true); }
  }

  function tick() {
    relocateLegacyEnvelope();
    syncPrimaryAction();
    if (!document.getElementById("risk-envelope-band")) return;   // no wasted fetch
    var band = document.getElementById("risk-envelope-band");
    if (lastLiveFeed && !active(lastLiveFeed, band)) unpaint(true);
    if (requestPending) return;
    requestPending = true;
    var options = { cache: "no-store" };
    // Bound the existing request; no second polling or retry loop.
    if (typeof AbortSignal !== "undefined" && typeof AbortSignal.timeout === "function") {
      options.signal = AbortSignal.timeout(10000);
    }
    fetch(FEED_URL + "?t=" + Date.now(), options)
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(applyFeed)
      .then(function () { requestPending = false; })
      .catch(function () { requestPending = false; unpaint(true); });
  }

  if (document.readyState !== "loading") tick();
  else document.addEventListener("DOMContentLoaded", tick);
  setInterval(tick, Math.max(15, POLL) * 1000);
})();
