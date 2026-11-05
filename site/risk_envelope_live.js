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

  // Present source-owned states; never compute a score, action or dwell threshold.
  function contextView(d, copy) {
    var hz = d.hazard_summary || {}, trans = d.live_transition || {};
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
    if (Array.isArray(sources)) sources.forEach(function (source) {
      if (!source) return;
      var label = [source.label_en || copy.source[0], source.label_zh || copy.source[1]];
      var word = copy.source_states[source.state] || [source.state || copy.source_missing[0], source.state || copy.source_missing[1]];
      var coverage = (copy.coverage || {})[source.coverage] || copy.source_missing;
      sourceLines[0].push(label[0] + ": " + word[0] + " · " + (source.as_of || "—") + " · " + coverage[0]);
      sourceLines[1].push(label[1] + "：" + word[1] + " · " + (source.as_of || "—") + " · " + coverage[1]);
    });
    return {stage: stage, pending: pending, label: copy.hazard[stage] || copy.unknown,
      hint: pending ? copy.checking : (copy.hint[stage] || copy.partial_hint),
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
      textPair(hint, config.copy.hint[config.settled_stage] || config.copy.partial_hint);
      hint.setAttribute("data-gde-stage", config.settled_stage || "UNKNOWN");
      hint.hidden = config.settled_stage === "NONE";
    }
    lastLiveFeed = null;
  }

  function unpaint(showFallback) {
    restoreContext(showFallback);
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
      } else {
        unpaint(!(d.live_active === false || d.precedence === "settled"));
      }
    } catch (e) { unpaint(true); }
  }

  function tick() {
    relocateLegacyEnvelope();
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
