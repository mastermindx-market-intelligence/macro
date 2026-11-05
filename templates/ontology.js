/* ontology.js — F04-X1 WTI Live Trace client.
   Paired plain-copy asset: templates/ontology.js and site/ontology.js must stay
   byte-identical (scripts/check_template_site_sync.py).

   This file is the ONLY place a current value enters the page. The shell that
   ships to the public CDN contains none, and nothing read here is written back
   to any browser store — the response is `private, no-store` on the wire, and
   persisting it client-side would undo that in one line.

   The vocabulary rules this file follows are product law, not style:
     * no internal state names, study names or raw slugs reach the reader; every
       leg is named by its own bilingual title
     * no refutation language on a user surface. The chain's falsifiers are real
       and keep evaluating, but they are presented as what we are watching, not
       as a thesis being refuted
     * an unavailable comparison is stated as unavailable. "Nothing changed" is
       a different claim and this data cannot support it */
(function () {
  "use strict";

  var DEFAULT_CHAIN = "oil_inflation_duration_derate";
  var CHAINS = [DEFAULT_CHAIN, "dollar_spike_em_multinational"];
  var requestedChains = new URLSearchParams(window.location.search).getAll("chain");
  var selectedChain = requestedChains.length ? requestedChains[0] : DEFAULT_CHAIN;
  var acceptedChain = requestedChains.length <= 1 && CHAINS.includes(selectedChain);
  var API = "/api/ontology/explorer/v1" + (requestedChains.length ? "?chain=" + encodeURIComponent(selectedChain) : "");
  var OPS = { gt: "\u003e", lt: "\u003c", gte: "\u2265", lte: "\u2264",
    eq: "=", ne: "\u2260" };
  var root = document.getElementById("ox-root");
  if (!root) return;
  document.querySelectorAll("[data-ontology-chain]").forEach(function (link) {
    if (acceptedChain && link.getAttribute("data-ontology-chain") === selectedChain) link.setAttribute("aria-current", "page");
  });
  var LEG_DETAIL_ID = "ox-steps";
  var legDetail = null;
  var readingEpoch = 0;
  var activeRequest = null;
  var portfolioReading = null;
  var scenarioReading = null;
  var canonicalOwner = null;
  try { canonicalOwner = window.MDXAuth && window.MDXAuth.user && window.MDXAuth.user(); }
  catch (e) { canonicalOwner = null; }
  canonicalOwner = canonicalOwner && canonicalOwner.id || null;

  function invalidateReading() {
    readingEpoch += 1;
    if (activeRequest) activeRequest.abort();
    activeRequest = null;
    portfolioReading = null;
    scenarioReading = null;
    var theme = document.getElementById("ox-theme");
    if (theme) theme.dispatchEvent(new CustomEvent("ontology-source-changed"));
    var scenario = document.getElementById("ox-scenario");
    if (scenario) scenario.dispatchEvent(new CustomEvent("ontology-source-changed"));
    var portfolio = document.getElementById("ox-portfolio");
    if (portfolio) portfolio.dispatchEvent(new CustomEvent("ontology-source-changed"));
    selectedPathRef = null;
    returnFocusRef = null;
    returnScrollX = returnScrollY = null;
    brainContextRevision += 1;
    var company = document.getElementById("ox-company");
    if (company) company.dispatchEvent(new CustomEvent("ontology-source-changed"));
  }

  /* Selected-path context is transient page state, not a fifth F04 object and
     not browser persistence. It binds the current chain/leg to the existing
     Mastermind Brain and remembers the exact control that should regain focus. */
  var selectedPathRef = null;
  var returnFocusRef = null;
  var returnScrollX = null;
  var returnScrollY = null;
  var brainContextRevision = 0;
  var brainContextOrigin = mintBrainOrigin();

  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = text;
    return node;
  }

  /* Both languages are always emitted; CSS decides which one paints. Building
     one language from a runtime flag would leave the other absent from the DOM
     and break the instant language toggle the rest of the site relies on. */
  function bi(pair, tag) {
    var frag = document.createDocumentFragment();
    var en = el(tag || "span", "l-en", (pair && pair.en) || "");
    var zh = el(tag || "span", "l-zh", (pair && (pair.zh || pair.en)) || "");
    frag.appendChild(en);
    frag.appendChild(zh);
    return frag;
  }

  function say(en, zh) { return bi({ en: en, zh: zh }); }

  function mintBrainOrigin() {
    try {
      if (window.crypto && window.crypto.randomUUID) {
        return "ox" + window.crypto.randomUUID().replace(/-/g, "").slice(0, 30);
      }
    } catch (e) { /* use the bounded local fallback below */ }
    return "ox" + Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
  }

  function brainLabel(value, fallback) {
    var text = String(value == null || value === "" ? fallback : value)
      .replace(/_/g, "-");
    return text.slice(0, 32);
  }

  /* Reuse the shared Brain host seam that already owns context receipts,
     permissions, threads, retry and persistence. Only bounded references ride
     here: chain, revision and selected leg. No source bytes or values are copied
     into a second state object. */
  function configureBrainHost() {
    window.MM_BRAIN_CFG = window.MM_BRAIN_CFG || {};
    window.MM_BRAIN_CFG.page = "ontology";
    window.MM_BRAIN_CFG.getOntologySelection = function () {
      if (!selectedPathRef) return null;
      return {
        chain: selectedPathRef.chain, revision: selectedPathRef.revision,
        asof: selectedPathRef.asof, manifest_hash: selectedPathRef.manifest_hash,
        node_id: selectedPathRef.node_id
      };
    };
    window.MM_BRAIN_CFG.getAiContext = function () {
      var ambient = selectedPathRef ? {
        symbol: null,
        timeframe: null,
        page: "ontology",
        panel: selectedPathRef.leg
      } : { symbol: null, timeframe: null, page: "ontology", panel: null };
      return {
        schema: "ai_context_client.v1",
        origin_id: brainContextOrigin,
        context_revision: brainContextRevision,
        captured_at: new Date().toISOString(),
        pinned: [],
        active: null,
        ambient: ambient
      };
    };
    window.MM_BRAIN_CFG.onClose = function () {
      if (!returnFocusRef) return false;
      if (!document.contains(returnFocusRef)) {
        returnFocusRef = null;
        returnScrollX = null;
        returnScrollY = null;
        selectedPathRef = null;
        brainContextRevision += 1;
        return false;
      }
      try { returnFocusRef.focus({ preventScroll: true }); }
      catch (e) { try { returnFocusRef.focus(); } catch (ignored) {} }
      if (returnScrollY != null) {
        try {
          window.scrollTo({ left: returnScrollX || 0, top: returnScrollY, behavior: "auto" });
        } catch (e) {
          try { window.scrollTo(returnScrollX || 0, returnScrollY); } catch (ignored) {}
        }
      }
      var restored = document.activeElement === returnFocusRef;
      if (restored && returnScrollY == null) {
        var box = returnFocusRef.getBoundingClientRect();
        var height = window.innerHeight || document.documentElement.clientHeight;
        if (box.top < 0 || box.bottom > height) {
          returnFocusRef.scrollIntoView({ block: "center" });
        }
      }
      returnFocusRef = null;
      returnScrollX = null;
      returnScrollY = null;
      selectedPathRef = null;
      brainContextRevision += 1;
      return restored;
    };
  }
  configureBrainHost();

  function replaceFocusHash(nodeId) {
    if (!nodeId) return;
    try {
      window.history.replaceState(window.history.state, "",
        window.location.pathname + window.location.search
        + "#ox-leg-" + encodeURIComponent(nodeId));
    } catch (e) { /* selection remains usable when URL replacement is unavailable */ }
  }

  function selectBrainPath(snapshot, leg, trigger) {
    var source = snapshot && snapshot.source ? snapshot.source : {};
    var next = {
      chain: source.chain,
      revision: source.rev == null ? null : source.rev,
      asof: source.asof,
      manifest_hash: source.source_manifest_hash,
      node_id: leg && leg.node_id,
      leg: brainLabel(leg && leg.node_id, "path")
    };
    var previousKey = selectedPathRef ? JSON.stringify(selectedPathRef) : "";
    var nextKey = JSON.stringify(next);
    if (nextKey !== previousKey) brainContextRevision += 1;
    selectedPathRef = next;
    returnFocusRef = trigger;
    returnScrollX = window.scrollX || window.pageXOffset || 0;
    returnScrollY = window.scrollY || window.pageYOffset || 0;
    replaceFocusHash(leg.node_id);
  }

  function openBrainForLeg(snapshot, leg, trigger) {
    selectBrainPath(snapshot, leg, trigger);
    if (window.MMBrain && typeof window.MMBrain.open === "function") {
      window.MMBrain.open();
      return true;
    }
    /* theme.js owns the shared widget's lazy loader. Clicking its accessible
       stub preserves one loader and one Brain rather than mounting another. */
    var boot = document.getElementById("mmb-boot");
    if (boot) {
      boot.click();
      return true;
    }
    return false;
  }

  async function withAuth(headers) {
    headers = headers || {};
    if (!(window.MDXAuth && window.MDXAuth.client)) return { headers: headers, identity: null };
    var client = await window.MDXAuth.client();
    var result = await client.auth.getSession();
    var session = result && result.data && result.data.session;
    var user = window.MDXAuth.user && window.MDXAuth.user();
    if (!session || !session.user || !user || typeof user.id !== "string" || !user.id
        || user.id !== session.user.id || typeof session.access_token !== "string" || !session.access_token) {
      return { headers: headers, identity: null };
    }
    headers.Authorization = "Bearer " + session.access_token;
    return { headers: headers, identity: { id: user.id, token: session.access_token } };
  }

  async function sameReadingOwner(identity) {
    // Authenticated responses must still belong to the same canonical account.
    if (!identity) return false;
    var latest = await withAuth({});
    return !!latest.identity && latest.identity.id === identity.id && latest.identity.token === identity.token;
  }

  /* aria-busy must be cleared on every terminal state, success or failure. A
     screen reader parked on a page that finished loading an ERROR is still
     being told the region is updating, so it waits for a result that already
     came and went. */
  function settle() {
    root.setAttribute("aria-busy", "false");
    root.classList.remove("ox-skeleton");
  }

  /* The house sign-in convention carries the exact page state to come back to:
     `?signin=1&ret=<root-relative path>`, consumed by onboard.js:retTarget(),
     which accepts same-origin "/..." only. The selected ontology leg lives in
     `location.hash`, so omitting it returns the reader to the route but silently
     loses the first blocker they were inspecting. Preserve path + query + hash
     inside the same guarded, root-relative carrier; do not create another return
     store just for this page. */
  function signinHref() {
    var here = "/ontology.html";
    try {
      var path = location.pathname + location.search + location.hash;
      if (path.charAt(0) === "/" && path.slice(0, 2) !== "//") here = path;
    } catch (e) { /* keep the static fallback */ }
    return "/?signin=1&ret=" + encodeURIComponent(here);
  }

  function gate(titleEn, titleZh, bodyEn, bodyZh, ctaEn, ctaZh, href,
                gateCode, retry) {
    var box = el("section", "ox-gate");
    if (gateCode) box.setAttribute("data-gate-code", gateCode);
    var h = el("h2");
    h.appendChild(say(titleEn, titleZh));
    var p = el("p");
    p.appendChild(say(bodyEn, bodyZh));
    box.appendChild(h);
    box.appendChild(p);
    if (href) {
      var a = el("a", "ox-cta");
      a.href = href;
      a.appendChild(say(ctaEn, ctaZh));
      box.appendChild(a);
    } else if (typeof retry === "function") {
      var button = el("button", "ox-cta");
      button.type = "button";
      button.appendChild(say(ctaEn || "Retry current reading",
        ctaZh || "重试当前读数"));
      button.addEventListener("click", function () {
        if (button.disabled) return;
        button.disabled = true;
        button.textContent = "";
        button.appendChild(say("Retrying…", "正在重试…"));
        root.setAttribute("aria-busy", "true");
        retry();
      });
      box.appendChild(button);
    }
    root.textContent = "";
    root.appendChild(box);
    settle();
  }

  function gateForFailure(code) {
    if (code === "chain_not_admitted") {
      gate("This path is not available here", "此处尚不支持该路径",
        "Choose one of the supported paths above. Another path's reading will not be substituted.",
        "请选择上方支持的路径。不会用其他路径的读数替代。",
        null, null, null, code);
      return;
    }
    if (code === "source_incoherent") {
      gate("The current sources disagree", "当前来源相互矛盾",
        "The owner artifacts could not be trusted together, so no partial or earlier reading is shown as current.",
        "所有者产物无法被共同信任，因此不会把部分或既往读数当作当前读数展示。",
        "Retry current reading", "重试当前读数", null, code, load);
      return;
    }
    if (code === "source_unavailable") {
      gate("A required owner source is unavailable", "必要的所有者来源不可用",
        "The current path cannot be read completely. No remembered value is substituted.",
        "当前路径无法完整读取，且不会用记忆中的数值替代。",
        "Retry current reading", "重试当前读数", null, code, load);
      return;
    }
    gate("The current reading cannot be safely shown", "当前读数无法安全展示",
      "The request ended without a trustworthy current snapshot. Nothing stale or partial is shown in its place.",
      "本次请求未得到可信的当前快照，因此不会以过时或部分数据替代。",
      "Retry current reading", "重试当前读数", null, code || "request_failed", load);
  }

  function conditionCounts(snapshot) {
    var legs = snapshot && snapshot.path && snapshot.path.legs || [];
    var coverage = snapshot && snapshot.state && snapshot.state.coverage || {};
    var total = Number(coverage.legs_declared);
    if (!Number.isFinite(total) || total < legs.length) total = legs.length;
    var met = 0;
    var observed = 0;
    legs.forEach(function (leg) {
      if (leg.observation !== "unobserved") observed += 1;
      if (leg.confirmed === true) met += 1;
    });
    return { met: met, total: total, observed: observed };
  }

  function answerFlag(kind, en, zh, tone) {
    var flag = el("span", "ox-answer-flag");
    flag.setAttribute("data-kind", kind);
    if (tone) flag.setAttribute("data-tone", tone);
    flag.appendChild(say(en, zh));
    return flag;
  }

  function renderAnswerSummary(snapshot) {
    var counts = conditionCounts(snapshot);
    var summary = el("section", "ox-answer-summary");
    summary.setAttribute("aria-label", "Current path answer summary");

    var count = el("div", "ox-answer-metric");
    var countLabel = el("span", "ox-answer-label");
    countLabel.appendChild(say("Current conditions", "当前条件"));
    count.appendChild(countLabel);
    count.appendChild(el("strong", "ox-answer-count", counts.met + " / " + counts.total));
    var countNote = el("span", "ox-answer-note");
    countNote.appendChild(say("met now", "当前满足"));
    count.appendChild(countNote);
    summary.appendChild(count);

    var blocker = el("div", "ox-answer-metric ox-answer-blocker");
    var blockerLabel = el("span", "ox-answer-label");
    blockerLabel.appendChild(say("First blocker", "首个阻断环节"));
    blocker.appendChild(blockerLabel);
    var blockerValue = el("strong");
    if (snapshot.first_blocking_leg) {
      blockerValue.appendChild(bi(pathLegTitle(snapshot, snapshot.first_blocking_leg)));
    } else {
      blockerValue.appendChild(say("No current blocker", "当前无阻断环节"));
    }
    blocker.appendChild(blockerValue);
    var blockerNote = el("span", "ox-answer-note");
    blockerNote.appendChild(snapshot.first_blocking_leg
      ? say("path order decides", "按路径顺序判定")
      : say("owner episode still governs", "仍以所有者事件记录为准"));
    blocker.appendChild(blockerNote);
    summary.appendChild(blocker);

    var flags = el("div", "ox-answer-flags");
    if (snapshot.contradiction) {
      flags.appendChild(answerFlag("contradiction", "Downstream contradiction",
        "后段读数矛盾", "warn"));
    }
    var change = snapshot.what_changed && snapshot.what_changed.status;
    if (change === "recorded_transition") {
      flags.appendChild(answerFlag("comparison", "Prior transition available",
        "已有既往状态转换", "ok"));
    } else {
      flags.appendChild(answerFlag("comparison", "Comparison unavailable",
        "比较不可用", "muted"));
    }
    var freshness = snapshot.source && snapshot.source.freshness;
    if (freshness && freshness.status === "verification_unavailable") {
      flags.appendChild(answerFlag("verification", "Verification unavailable",
        "核验不可用", "warn"));
    }
    summary.appendChild(flags);
    return summary;
  }

  function renderHeroAction(snapshot) {
    var blocking = snapshot.first_blocking_leg;
    if (!blocking || !blocking.node_id) return null;
    var button = el("button", "ox-action ox-hero-action");
    button.type = "button";
    button.setAttribute("aria-controls", LEG_DETAIL_ID);
    button.appendChild(say("Inspect first blocker", "查看首个阻断环节"));
    button.addEventListener("click", function () {
      if (!focusLeg(blocking.node_id)) {
        button.disabled = true;
        button.textContent = "";
        button.appendChild(say("That step is not available", "该环节不可用"));
      }
    });
    return button;
  }

  function legVerdict(leg) {
    if (leg.observation === "unobserved") return say("No current reading", "暂无当前读数");
    if (leg.observation === "unreadable") return say("Reading unreadable", "\u8bfb\u6570\u65e0\u6cd5\u8bfb\u53d6");
    if (leg.confirmed === true) return say("Met", "已满足");
    if (leg.confirmed === false) return say("Not met", "未满足");
    return say("Unresolved", "无法判定");
  }

  function renderRail(snapshot) {
    var rail = el("ol", "rail");
    var blockingId = snapshot.first_blocking_leg && snapshot.first_blocking_leg.node_id;
    var hopByFrom = {};
    (snapshot.path.hops || []).forEach(function (hop) { hopByFrom[hop.from] = hop; });

    snapshot.path.legs.forEach(function (leg) {
      var station = el("li", "station");
      var legState = leg.observation === "unobserved" ? "unobserved"
        : leg.observation === "unreadable" ? "unreadable"
        : String(leg.confirmed === true);
      station.setAttribute("data-leg", legState);
      if (leg.node_id === blockingId) station.setAttribute("data-blocking", "1");
      var hop = hopByFrom[leg.node_id];
      /* The terminal station has no outbound hop. Saying "true" would claim a
         confirmed link that does not exist; "none" says there is nothing there. */
      station.setAttribute("data-link", hop ? String(hop.confirmed === true) : "none");

      var top = el("div", "st-top");
      top.appendChild(el("span", "st-dot"));
      top.appendChild(el("span", "st-break"));
      station.appendChild(top);

      var body = el("div", "st-body");
      body.appendChild(el("div", "st-idx", String(leg.index).padStart(2, "0")));
      var name = el("div", "st-name");
      name.appendChild(bi(pathLegTitle(snapshot, leg)));
      body.appendChild(name);
      var verdict = el("div", "st-verdict");
      verdict.appendChild(legVerdict(leg));
      body.appendChild(verdict);
      station.appendChild(body);
      rail.appendChild(station);
    });
    return rail;
  }

  /* The episode and today's conditions are two different facts and the stance
     says which one it is speaking about. A chain can sit here with every
     condition true and still be dormant, stopped, or already finished — the
     owner's chain is a history, and this sentence used to read the history off
     today's booleans. */
  function stance(snapshot) {
    var blocking = snapshot.first_blocking_leg;
    var name = blocking ? blocking.title : null;
    var code = snapshot.state.code;
    var allMet = snapshot.state.conditions && snapshot.state.conditions.all_current_met;

    if (code === "unknown") {
      return say("The owners' record for this path could not be read, so its state "
        + "cannot be called.",
        "无法读取所有者对该路径的记录，因此无法判定其状态。");
    }
    if (code === "active") {
      return say("The owners have this path running.", "所有者记录该路径正在运行。");
    }
    if (code === "completed") {
      return say("This path ran all the way through. What follows is the record of "
        + "that, not a live reading.",
        "该路径已完整传导。以下为其记录，并非实时读数。");
    }
    if (code === "stopped") {
      return say("This path started and then stopped: one of the conditions the "
        + "owners watch for came true.",
        "该路径曾启动后中止：所有者所观察的条件之一已发生。");
    }
    if (code === "ended") {
      return say("This path started and ended without completing.",
        "该路径曾启动，但未完成即结束。");
    }
    if (allMet === true) {
      /* The case the old code got wrong in the other direction: everything true
         today, and still dormant. Saying "every step is met" as the headline
         invited the reader to treat a coincidence as a running path. */
      return say("Every step reads true right now, but the owners have not recorded "
        + "this path as running. Conditions lining up on one day is not the same as "
        + "the path having carried through.",
        "当前各环节读数均为真，但所有者并未将该路径记录为运行中。"
        + "某一天条件同时成立，与路径确已传导并非同一回事。");
    }
    if (allMet === null || allMet === undefined) {
      return say("Part of this path has no current reading, and the owners have not "
        + "recorded it as running.",
        "该路径部分环节暂无当前读数，且所有者未将其记录为运行中。");
    }
    /* Keep the first glance short. The contradiction flag and blocking card
       retain the causal warning; a later true leg never starts this path. */
    var simple = document.createDocumentFragment();
    simple.appendChild(say("Not running. First unmet condition: ",
      "未运行。首个未满足条件："));
    var subject = el("span", "ox-answer-subject");
    subject.appendChild(bi(name));
    subject.appendChild(say(".", "。"));
    simple.appendChild(subject);
    return simple;
  }

  /* Three facts the reader needs before trusting anything below: how much of
     the path was actually read, how old those readings are, and what this page
     cannot verify. Compact by design — the full receipts live in Study, and a
     diagnostic wall in the first viewport buries the answer it is qualifying. */
  function renderMeta(snapshot) {
    var meta = el("p", "ox-meta");
    var cov = snapshot.state.coverage;

    var covSpan = el("span", "ox-meta-item");
    if (cov.legs_unobserved && cov.legs_unobserved.length) {
      covSpan.setAttribute("data-flag", "1");
      covSpan.appendChild(say(
        cov.legs_observed + " of " + cov.legs_declared + " steps have a current reading",
        cov.legs_declared + " 个环节中有 " + cov.legs_observed + " 个具备当前读数"));
    } else {
      covSpan.appendChild(say("All " + cov.legs_declared + " steps have a current reading",
        "全部 " + cov.legs_declared + " 个环节均有当前读数"));
    }
    meta.appendChild(covSpan);

    var fresh = snapshot.source.freshness;
    var age = el("span", "ox-meta-item");
    if (fresh.observation_asof && fresh.observation_age_days != null) {
      age.appendChild(say(
        "Readings dated " + fresh.observation_asof + " ("
          + (fresh.observation_age_days === 0 ? "today"
             : fresh.observation_age_days === 1 ? "1 day ago"
             : fresh.observation_age_days + " days ago") + ")",
        "读数日期 " + fresh.observation_asof + "（"
          + (fresh.observation_age_days === 0 ? "今日"
             : fresh.observation_age_days + " 天前") + "）"));
    } else {
      age.setAttribute("data-flag", "1");
      age.appendChild(say("Reading date not published", "读数日期未发布"));
    }
    meta.appendChild(age);

    if (fresh.status === "verification_unavailable") {
      var unc = el("span", "ox-meta-item");
      unc.setAttribute("data-flag", "1");
      unc.appendChild(say("Not verified against the published page",
        "未与已发布页面比对核验"));
      meta.appendChild(unc);
    }
    return meta;
  }

  function card(titleEn, titleZh, tone) {
    var box = el("article", "ox-card");
    if (tone) box.setAttribute("data-tone", tone);
    var h = el("h2");
    h.appendChild(say(titleEn, titleZh));
    box.appendChild(h);
    return box;
  }

  function renderWhatChanged(snapshot) {
    var box = card("What changed", "有何变化");
    var p = el("p");
    if (snapshot.what_changed.status === "recorded_transition") {
      var item = snapshot.what_changed.items[0];
      p.appendChild(say("A transition was recorded on " + (item.asof || "an earlier date") + ".",
        "已于 " + (item.asof || "较早日期") + " 记录到一次状态转换。"));
    } else if (snapshot.what_changed.status === "comparison_incomplete") {
      /* An unread history is not a history of nothing, and this branch exists so
         the page stops answering in the owners' voice about records it could
         not read. */
      p.className = "ox-unavailable";
      p.appendChild(bi(snapshot.what_changed.note));
    } else {
      p.className = "ox-unavailable";
      p.appendChild(say(
        "No transition has been recorded for this path, so there is no earlier accepted "
        + "reading to compare against. The comparison is unavailable — that is not the "
        + "same as the conditions having held still.",
        "该路径尚无已记录的状态转换，因此没有可比对的既往认定读数。"
        + "比较不可用——这与条件未发生变动并非同一回事。"));
    }
    box.appendChild(p);
    return box;
  }

  function renderWhyItMatters(snapshot) {
    var box = card("Why it matters", "为何重要");
    var p = el("p");
    var first = (snapshot.why_it_matters.legs || [])[0];
    if (first && first.mechanism) {
      /* The mechanism note comes from the knowledge file and does not end in a
         full stop. Appending the caution to the same sentence ran the two
         together into one ungrammatical line, so the caution gets its own
         paragraph — which is also where it belongs in the reading order. */
      p.appendChild(bi(first.mechanism));
      box.appendChild(p);
      var caution = el("p", "ox-note");
      caution.appendChild(say("That describes how the steps are meant to connect. It is "
        + "not a measurement that they are connecting now.",
        "以上说明的是各环节理论上的连接方式，并非当前确实连通的度量。"));
      box.appendChild(caution);
      return box;
    }
    p.appendChild(say("No mechanism note is published for this path.",
      "该路径未发布机制说明。"));
    box.appendChild(p);
    return box;
  }

  /* Factories, not fragments. A DocumentFragment is emptied when it is appended,
     so a shared one would render correctly once and then insert nothing on every
     later render. */
  var BLOCKING_REASON = {
    condition_false: function () {
      return say(", whose condition is not met.", "，该环节条件未满足。"); },
    not_observed: function () {
      return say(", which has no current reading.", "，该环节暂无当前读数。"); },
    not_resolved: function () {
      return say(", which the owners have not resolved yet.",
        "，所有者尚未对该环节作出判定。"); },
    not_judged: function () {
      return say(", which the owners recorded without a verdict.",
        "，所有者已记录该环节但未给出判定结果。"); },
    not_readable: function () {
      return say(", whose recorded verdict could not be read.",
        "，该环节已记录的判定无法读取。"); }
  };

  function renderBlocking(snapshot) {
    var blocking = snapshot.first_blocking_leg;
    if (!blocking) {
      var okBox = card("Why it does not fire", "为何未触发");
      var okP = el("p");
      /* Nothing blocks the CONDITIONS. Whether the path is running is the
         owner's episode, and saying "nothing is blocking this path" while the
         owner has it dormant would answer a different question than the one
         the card asks. */
      okP.appendChild(snapshot.state.activation === true
        ? say("Every step is met and the owners have this path running.",
          "所有环节均已满足，且所有者记录该路径正在运行。")
        : say("No step is blocking: every condition reads true right now. The "
          + "path is still not running, which is a fact about the owners' record "
          + "rather than about today's conditions.",
          "当前没有受阻环节：各项条件读数均为真。但该路径仍未运行——"
          + "这取决于所有者的记录，而非当日条件。"));
      okBox.appendChild(okP);
      return okBox;
    }
    var box = card("Why it does not fire", "为何未触发", "blocked");
    var p = el("p");
    var strong = el("strong");
    strong.appendChild(bi(blocking.title));
    p.appendChild(say("The path stops at step " + blocking.index + ", ", "路径止于第 "
      + blocking.index + " 环节，"));
    p.appendChild(strong);
    /* Every reason the composer can emit, said as what it is. The else-branch
       used to narrate not_resolved / not_judged / not_readable as "condition is
       not met" — which converts "we could not judge this" into a market verdict
       on the customer surface, the same collapse the composer refuses upstream.
       A step we could not read is a step we could not read. */
    var reason = BLOCKING_REASON[blocking.reason];
    p.appendChild(reason ? reason()
      : say(", which this page could not judge.", "，本页面无法对该环节作出判定。"));
    if (snapshot.contradiction) {
      p.appendChild(say(" A later step does read true. That reading has its own causes; "
        + "it is not evidence for the earlier step.",
        "后段确有环节读数为真。该读数有其自身成因，并不构成前段环节的证据。"));
    }
    box.appendChild(p);
    return box;
  }

  function reducedMotion() {
    return !!(window.matchMedia
      && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }

  /* The action actually performs the thing its label promises: it opens the
     step-by-step section, brings the named step into view and moves focus onto
     it, so a keyboard or screen-reader user lands where a sighted user is
     looking. The target id is stable and derived from the owner's node id, so
     the anchor survives a re-render and can be linked to directly. */
  function focusLeg(nodeId) {
    var target = document.getElementById("ox-leg-" + nodeId);
    if (!target) return false;
    replaceFocusHash(nodeId);
    var wasClosed = !!(legDetail && !legDetail.open);
    if (wasClosed) legDetail.open = true;
    /* Opening a <details> reveals content that has not been laid out yet, so a
       scroll issued in the same tick measures the pre-open position and lands
       somewhere else entirely — measured: the step ended up 200px below the
       fold. Wait for the frame that includes the newly revealed content. */
    var inView = function () {
      var box = target.getBoundingClientRect();
      return box.top >= 0 && box.bottom <= (window.innerHeight
        || document.documentElement.clientHeight);
    };
    var go = function () {
      if (!target.scrollIntoView) { target.focus({ preventScroll: true }); return; }
      var smooth = !reducedMotion();
      target.scrollIntoView(smooth
        ? { block: "center", behavior: "smooth" }
        : { block: "center" });
      target.focus({ preventScroll: true });
      /* Smooth scrolling is an animation, and an animation is not a guarantee:
         a hidden or throttled tab never runs it, and a competing scroll can
         interrupt it — measured, the step stayed 200px below the fold while the
         focus ring sat on something the reader could not see. Motion is the
         enhancement; arriving is the requirement, so the destination is checked
         and corrected without it. */
      if (!smooth) return;
      window.setTimeout(function () {
        if (!inView()) target.scrollIntoView({ block: "center" });
      }, 500);
    };
    if (!wasClosed) {
      go();
      return true;
    }
    /* rAF is the right clock for "after the next paint", but a background or
       hidden tab throttles it to nothing — measured here: the callback never
       ran and the action silently did half its job. A timeout is racing it so
       the action always completes; whichever wins, `go` runs once. */
    var done = false;
    var once = function () { if (done) return; done = true; go(); };
    if (window.requestAnimationFrame) {
      window.requestAnimationFrame(function () { window.requestAnimationFrame(once); });
    }
    window.setTimeout(once, 60);
    return true;
  }

  /* The canonical surface is always reachable, in every state. It used to be
     offered only by the one action branch that fires when nothing is blocking
     and nothing is unobserved — a rare case — which left the ordinary dormant
     reader with the link present solely inside <noscript>, i.e. exactly where
     the reader who can see the page never looks. This path is a real page that
     carries every chain the owners publish, so it is a genuine continuation
     rather than a courtesy link. */
  /* M1 acceptance item 5: every continuation link the page renders carries the
     selected path / step / source context that the reader actually arrived
     from. A bare `/transmission.html` loses the focused step (so a reader who
     followed the link from a particular block lands on the page with no
     indication of which path / step / revision they came from). The
     transmission surface may or may not consume these today; that is the
     surface's job, not this page's — the link carries the context regardless.
     `focus` names the step the page last focused — the one its next_action
     pointed at (unobserved leg, downstream-of-contradiction leg, or
     first-blocking leg), NOT the first blocking leg whenever there is one
     (which can be a different step than what the next-action control just
     opened). `from` is the chain identifier (`source.chain`), which uniquely
     names this chain on the overview — `path.sequence[0]` is the chain's
     first node slug, NOT a chain identifier. `rev` is the source revision the
     snapshot was read at. */
  /* Arriving back from a continuation page: `#ox-leg-<node>` names the step the
     reader was on (the transmission page writes it from the `focus=` we sent).
     The hash is the only carrier — nothing here prints the identifier. */
  function focusFromHash() {
    var h = window.location.hash || "";
    if (h.indexOf("#ox-leg-") !== 0) return false;
    var nodeId;
    try { nodeId = decodeURIComponent(h.slice("#ox-leg-".length)); }
    catch (e) { return false; }
    return nodeId ? focusLeg(nodeId) : false;
  }

  /* `?rev=<n>` is the path revision the reader left at. When the served
     revision differs, say so in plain words before the reading — a reader
     returning to a re-drawn path should not mistake it for the one they left. */
  function continuationNotice(snapshot) {
    var left;
    try { left = new URLSearchParams(window.location.search).get("rev"); }
    catch (e) { return null; }
    if (!left) return null;
    var now = snapshot && snapshot.source ? snapshot.source.rev : null;
    if (now == null || String(now) === String(left)) return null;
    var p = el("p", "ox-note ox-revised");
    p.appendChild(say(
      "This path has been revised since you left it (you read revision " + left
      + "; this is revision " + String(now) + "). What follows is the current reading.",
      "您离开后该路径已修订（您阅读的是版本 " + left + "，当前为版本 " + String(now)
      + "）。以下为当前读数。"));
    return p;
  }

  function continuationHref(snapshot) {
    var src = snapshot && snapshot.source;
    var chain = src && src.chain;
    var from = (chain != null && chain !== "") ? String(chain) : "";
    var focus = "";
    var action = snapshot && snapshot.next_action;
    if (action && action.target) {
      focus = String(action.target);
    } else if (snapshot && snapshot.first_blocking_leg
               && snapshot.first_blocking_leg.node_id) {
      focus = String(snapshot.first_blocking_leg.node_id);
    }
    var rev = src && src.rev;
    rev = (rev == null) ? "" : String(rev);
    var q = [];
    if (from)  q.push("from="  + encodeURIComponent(from));
    if (focus) q.push("focus=" + encodeURIComponent(focus));
    if (rev)   q.push("rev="   + encodeURIComponent(rev));
    return "transmission.html" + (q.length ? "?" + q.join("&") : "");
  }
  function transmissionLink(snapshot) {
    var p = el("p", "ox-more");
    var a = el("a");
    a.href = continuationHref(snapshot);
    a.appendChild(say("See this path among all the owners publish",
      "在所有者发布的全部路径中查看本条"));
    p.appendChild(a);
    return p;
  }

  function researchReadingLink() {
    var d = detail("Compare theme evidence", "比较主题证据");
    d.classList.add("ox-detail--flush");
    d.id = "ox-research-reading";
    var a = el("a", "ox-action");
    a.href = "state_of_themes.html#research-reading-order";
    a.appendChild(say("Open the theme reading order", "打开主题阅读顺序"));
    d.appendChild(a);
    var basis = el("p", "ox-note");
    basis.appendChild(say("The Theme Tracker orders its own recorded evidence by date, then daily count and name. Its dates are separate from this path's reading.",
      "主题追踪页按自身证据的记录日期、当日条数和名称排序。其日期与本路径读数分开。"));
    d.appendChild(basis);
    var held = el("p", "ox-note");
    held.setAttribute("data-opportunity-abstention", "uncalibrated");
    held.appendChild(say("Calibrated opportunity estimates are unavailable. This reading order does not establish impact, direction, confidence or what is already priced in.",
      "经校准的机会估计尚不可用。此阅读顺序不说明影响幅度、方向、把握程度或价格已消化程度。"));
    d.appendChild(held);
    return d;
  }

  function renderNextAction(snapshot) {
    var action = snapshot.next_action;
    var box = card("Next", "下一步", "watch");

    if (action.handler === "focus_leg" && action.target) {
      var button = el("button", "ox-action");
      button.type = "button";
      button.setAttribute("aria-controls", LEG_DETAIL_ID);
      button.appendChild(bi(action.label));
      button.addEventListener("click", function () {
        if (!focusLeg(action.target)) {
          /* The step this action names is not on the page. Silently doing
             nothing would leave the reader clicking a dead control, so the
             button states that instead of pretending it worked. */
          button.disabled = true;
          button.textContent = "";
          button.appendChild(say("That step is not on this page",
            "该环节不在本页面上"));
        }
      });
      box.appendChild(button);
      var hint = el("p", "ox-note");
      hint.appendChild(say("Opens the step-by-step readings below.",
        "将展开下方的逐环节读数。"));
      box.appendChild(hint);
      box.appendChild(transmissionLink(snapshot));
      box.appendChild(researchReadingLink());
      return box;
    }

    var link = el("a", "ox-action");
    link.href = continuationHref(snapshot);
    link.appendChild(bi(action.label));
    box.appendChild(link);
    var note = el("p", "ox-note");
    note.appendChild(say("The transmission overview carries every path the owners "
      + "publish, not only this one.",
      "传导链总览页面涵盖所有者发布的全部路径，而不仅是本条。"));
    box.appendChild(note);
    box.appendChild(researchReadingLink());
    return box;
  }

  function detail(summaryEn, summaryZh) {
    var d = el("details", "ox-detail");
    var s = el("summary");
    s.appendChild(say(summaryEn, summaryZh));
    d.appendChild(s);
    return d;
  }

  function pathLegTitle(snapshot, leg) {
    if (snapshot.source?.chain === 'dollar_spike_em_multinational') {
      if (leg.node_id === 'em_derate') return {en: 'FXI versus SPY: EM proxy', zh: 'FXI 相对 SPY：新兴市场代理'};
      if (leg.node_id === 'dollar_spike') return {en: 'Dollar trend and positioning', zh: '美元趋势与持仓分位'};
    }
    return leg.title;
  }
  function pathLegQualification(snapshot, leg) {
    if (snapshot.source?.chain !== 'dollar_spike_em_multinational') return null;
    if (leg.node_id === 'em_derate') return {
      en: 'The native predicate uses FXI (China large-cap) relative to SPY over 63 observations as an EM proxy. It does not measure all emerging markets or multinational earnings.',
      zh: '原生条件使用 FXI（中国大型股）相对 SPY 的63个观测间隔表现作为新兴市场代理，并非全部新兴市场或跨国企业盈利的测量。'};
    if (leg.node_id === 'dollar_spike') return {
      en: 'This condition measures dollar trend and positioning. High real rates are a declared mechanism, not an observed cause in this predicate.',
      zh: '此条件测量美元趋势与持仓分位。高实际利率是声明的机制，并非该条件中已观测到的原因。'};
    return null;
  }
  function renderLegDetail(snapshot) {
    var d = detail("Inspect each step: readings, timing and what we are watching",
      "查看各环节：读数、时间窗口与我们正在观察的条件");
    d.id = LEG_DETAIL_ID;
    snapshot.path.legs.forEach(function (leg) {
      var box = el("div", "ox-leg");
      box.id = "ox-leg-" + leg.node_id;
      /* -1 keeps the step out of the tab order — it is a destination, not a
         control — while still allowing focus() to land on it. */
      box.tabIndex = -1;
      var h = el("h3");
      h.appendChild(bi(pathLegTitle(snapshot, leg)));
      box.appendChild(h);
      var qualification = pathLegQualification(snapshot, leg);
      if (qualification) { var note = el('p', 'ox-note'); note.appendChild(bi(qualification)); box.appendChild(note); }
      var kv = el("dl", "ox-kv");
      (leg.receipts || []).forEach(function (receipt) {
        /* Receipts are facts about a single reading. Their fields are ALL
           optional: an owner artifact may publish only some of them, and the
           earlier implementation concatenated `undefined` strings when any
           one was absent. Here every field that exists is named in a
           bilingual sentence, and missing fields contribute nothing. The
           series identifier (e.g. "T10YIE", "CL=F") is the owner's public
           name for the series, the way a ticker is — what would otherwise be
           a study slug is the metric name (e.g. "ret_bp"), which the page
           never reaches the reader with: a sentence that names a window
           and a value is enough to describe what the reading says. */
        var dt = el("dt");
        dt.appendChild(receiptLabel(receipt));
        kv.appendChild(dt);
        var dd = el("dd");
        dd.appendChild(receiptValue(receipt));
        kv.appendChild(dd);
      });
      if (!(leg.receipts || []).length) {
        var dt2 = el("dt");
        dt2.appendChild(say("Reading", "读数"));
        var dd2 = el("dd");
        dd2.appendChild(say("not published", "未发布"));
        kv.appendChild(dt2);
        kv.appendChild(dd2);
      }
      box.appendChild(kv);
      var ask = el("button", "ox-action ox-brain-action");
      ask.type = "button";
      ask.appendChild(say("Ask Mastermind about this step",
        "向 Mastermind 询问此环节"));
      ask.addEventListener("click", function () {
        if (!openBrainForLeg(snapshot, leg, ask)) {
          ask.disabled = true;
          ask.textContent = "";
          ask.appendChild(say("Mastermind is unavailable right now",
            "Mastermind 当前不可用"));
        }
      });
      box.appendChild(ask);
      d.appendChild(box);
    });

    if ((snapshot.invalidators || []).length) {
      var watch = el("div", "ox-leg");
      var wh = el("h3");
      wh.appendChild(say("What we are watching", "我们正在观察"));
      watch.appendChild(wh);
      /* Owner notes are shown only when the composer cleared them. When it did
         not, the condition itself is shown as facts — which is what the reader
         needs anyway, and never carries refutation wording, a raw node id, or
         untranslated English into the Chinese view. */
      snapshot.invalidators.forEach(function (item) {
        var row = el("p", "ox-note");
        if (item.note) {
          row.appendChild(bi(item.note));
        } else if (item.watched && item.watched.series) {
          /* The watched condition without a note: a reading on a series, with
             whatever window / operator / value the owner published. Built
             bilingually and never as raw concatenated fields \u2014 `T10YIE \u00b7 ret_bp
             22d < 5` is the previous shape, and it let a study slug ("ret_bp")
             reach the reader. Here every field that exists becomes part of a
             sentence, and missing fields contribute nothing. */
          row.appendChild(watchedSentence(item.watched));
        } else {
          return;
        }
        watch.appendChild(row);
      });
      d.appendChild(watch);
    }
    return d;
  }

  /* Receipts and watched conditions are rendered as bilingual sentences. Each
     helper takes the partial field set an owner can publish and only names the
     fields that actually exist — `undefined` is never written to the page.
     `series` is treated as the owner's public identifier (a ticker-style name
     like "T10YIE" or "CL=F" is part of what the reader is told); `metric` is
     treated as a study slug and is dropped on the glance tier — the value,
     operator, threshold and window together already say what the reading is. */
  function _present(field) {
    return field != null && field !== "";
  }
  function _opGlyph(op) {
    return OPS[op] || (op == null ? "" : String(op));
  }
  function _num(n) {
    if (n == null || n === "") return "";
    if (typeof n === "number" && isFinite(n)) {
      /* Strip trailing zeros so a threshold of 5.0 reads as 5 and a value of
         0.50 reads as 0.5 — both carry no information in the trailing digit. */
      var s = String(n);
      return s;
    }
    return String(n);
  }
  function receiptLabel(receipt) {
    /* The dt: names the reading — series identifier and window if present.
       The metric name is intentionally omitted; the value/op/threshold line
       below already says what the reading says. */
    var series = _present(receipt.series) ? String(receipt.series) : "";
    var window = _present(receipt.window) ? String(receipt.window) : "";
    if (series && window) {
      return say(series + " · " + window + "-day reading",
        series + " · " + window + " 日读数");
    }
    if (series) {
      return say(series + " · reading", series + " · 读数");
    }
    if (window) {
      return say(window + "-day reading", window + " 日读数");
    }
    return say("Reading", "读数");
  }
  function receiptValue(receipt) {
    /* The dd: says the reading — value, operator, threshold, in plain English
       and plain Chinese. Missing fields are skipped; an entirely empty
       receipt is still disclosed as such rather than printed as "undefined". */
    var value = _present(receipt.value) ? _num(receipt.value) : "";
    var op = _opGlyph(receipt.op);
    var threshold = _present(receipt.threshold) ? _num(receipt.threshold) : "";
    var window = _present(receipt.window) ? String(receipt.window) : "";

    if (!value && !threshold) {
      return say("reading published without a value",
        "已发布读数，但未给出数值");
    }
    /* Never join a false test into a false mathematical assertion (6 > 10).
       Name observed value, requirement and the owner's result separately.
       Units come only from the closed, already-published metric vocabulary. */
    var units = { ret: "%", ret_pct: "%", ret_bp: " bp", rs: " pp", rs_pp: " pp" };
    var unit = Object.prototype.hasOwnProperty.call(units, receipt.metric)
      ? units[receipt.metric] : "";
    var en = value ? "Observed: " + value + unit : "Observed value unavailable in this view";
    var zh = value ? "读数：" + value + unit : "此视图无法显示观测值";
    var named = { up: "向上", strengthening: "走强", "EM equities": "新兴市场股票" };
    if (Object.prototype.hasOwnProperty.call(named, value)) zh = "读数：" + named[value];
    if (threshold) {
      en += " · Requires: " + (receipt.op === "in_contains" ? "includes " : op ? op + " " : "") + threshold + unit;
      zh += " · 要求：" + (receipt.op === "in_contains" ? "包含 " : op ? op + " " : "") + (named[threshold] || threshold) + unit;
    }
    if (receipt.passed === true) {
      en += value ? " · Met" : " · Owner verdict: met";
      zh += value ? " · 已满足" : " · 来源判定：已满足";
    } else if (receipt.passed === false) {
      en += value ? " · Not met" : " · Owner verdict: not met";
      zh += value ? " · 未满足" : " · 来源判定：未满足";
    } else {
      en += " · Result not published"; zh += " · 结果未发布";
    }
    if (_present(receipt.vs)) {
      en += " · vs " + String(receipt.vs);
      zh += " · 对比 " + String(receipt.vs);
    }
    if (window) {
      en += " · " + window + "-day reading";
      zh += " · " + window + " 日读数";
    }
    return say(en, zh);
  }
  function watchedSentence(w) {
    /* An invalidator without an owner note: render the watched condition as a
       plain bilingual sentence. `metric` is a study slug and is dropped; the
       series, window, operator and value together say what we are watching. */
    var series = _present(w.series) ? String(w.series) : "";
    var vs = _present(w.vs) ? String(w.vs) : "";
    var window = _present(w.window) ? String(w.window) : "";
    var op = _opGlyph(w.op);
    var value = _present(w.value) ? _num(w.value) : "";

    var en, zh;
    if (series && vs && window && op && value) {
      en = "Watching " + series + " against " + vs + ": " + window
        + "-day value " + op + " " + value;
      zh = "观察 " + series + " 与 " + vs + " 的对照：" + window
        + " 日数值 " + op + " " + value;
    } else if (series && window && op && value) {
      en = "Watching " + series + ": " + window + "-day value " + op + " " + value;
      zh = "观察 " + series + "：" + window + " 日数值 " + op + " " + value;
    } else if (series && op && value) {
      en = "Watching " + series + ": value " + op + " " + value;
      zh = "观察 " + series + "：数值 " + op + " " + value;
    } else if (series) {
      en = "Watching " + series;
      zh = "观察 " + series;
    } else {
      return say("Watching this step's condition",
        "观察该环节的条件");
    }
    return say(en, zh);
  }

  /* Every gap kind the composer can emit has a plain-language sentence here.
     The composer is the source of truth (engine/ontology_explorer.py); this
     table is the reader-facing layer. A missing entry falls through to the
     raw-slug branch at the bottom of `gapLabel`, and the test pinning parity
     refuses to ship a kind the composer can emit without a sentence of its
     own — see tests/test_ontology_explorer_shell.py::test_every_engine_gap_
     kind_has_a_reader_facing_sentence. */
  var GAP_TEXT = {
    node_incomplete: { en: "a step the owners have not finished recording",
      zh: "所有者尚未记录完整的环节" },
    node_unresolved: { en: "a step the owners have not resolved",
      zh: "所有者尚未判定的环节" },
    node_unjudged: { en: "a step recorded without a verdict",
      zh: "已记录但未给出判定的环节" },
    node_unreadable: { en: "a step whose verdict could not be read",
      zh: "判定无法读取的环节" },
    node_unobserved: { en: "a step that has no current reading",
      zh: "暂无当前读数的环节" },
    clock_absent: { en: "a step whose clock the owners did not publish",
      zh: "所有者未发布时间的环节" },
    path_incomplete: { en: "part of the path the walk never reached",
      zh: "遍历未触及的路径片段" },
    build_stamp_in_future: { en: "a build stamp dated ahead of now",
      zh: "时间戳晚于当前时刻的构建记录" },
    text_withheld: { en: "an owner note held back from this page",
      zh: "未在本页面展示的所有者备注" },
    text_untranslated: { en: "an owner note published in one language only",
      zh: "仅以单一语言发布的所有者备注" },
    episode_ledger_truncated: { en: "a change history longer than this page reads",
      zh: "长度超出本页面读取上限的变更历史" },
    invalidators_absent: { en: "the watch list the owners did not publish",
      zh: "所有者未发布的观察清单" },
    exposure_screens_absent: { en: "the exposure screens the owners did not publish",
      zh: "所有者未发布的敞口展示" },
    unparseable_observation_date: { en: "a reading date this page could not read",
      zh: "本页面无法解析的读数日期" },
    owner_state_absent: { en: "the owners' recorded state for this path",
      zh: "所有者为该路径记录的状态" },
    owner_state_unrecognised: { en: "an owner state this page does not recognise",
      zh: "本页面无法识别的所有者状态" },
    observation_date_in_future: { en: "a reading dated ahead of now",
      zh: "日期晚于当前时刻的读数" },
    receipts_malformed: { en: "a set of readings this page could not read",
      zh: "本页面无法读取的一组读数" },
    receipt_value_not_finite: { en: "a reading that is not a usable number",
      zh: "并非可用数值的读数" },
    receipt_field_not_scalar: { en: "a reading that was not a single value",
      zh: "并非单一数值的读数" },
    transitions_from_another_revision: {
      en: "a transition recorded against a different revision of this path",
      zh: "针对该路径另一版本记录的状态转换" },
    transitions_unreadable: {
      en: "a transition whose record this page could not read",
      zh: "本页面无法读取的状态转换记录" },
    transitions_malformed: {
      en: "a transition record this page could not parse",
      zh: "本页面无法解析的状态转换记录" },
    transitions_after_cutoff: {
      en: "a transition dated after the artifact's effective date",
      zh: "晚于产物生效日期的状态转换" }
  };

  function gapLabel(gap) {
    var known = GAP_TEXT[gap.kind];
    if (known) return say(known.en, known.zh);
    /* An unmapped kind is still disclosed. Hiding it because this page has no
       sentence for it would turn a known gap into a silent one. */
    return say(gap.kind.replace(/_/g, " "), gap.kind.replace(/_/g, " "));
  }

  function renderExposure(snapshot) {
    var screens = snapshot.exposure_screens || [];
    if (!screens.length) return null;
    var d = detail("What this path bears on", "该路径涉及什么");
    d.setAttribute("data-exposure-membership", "true");
    var lead = el("p", "ox-note");
    lead.appendChild(say(
      "These are the owner's exposure screens. Any company names are the recorded screen membership, not an impact estimate, ranking or suggestion to act. Companies the owner could not evaluate remain outside that conclusion.",
      "以下为来源提供的敞口筛选。公司名单仅代表已记录的筛选成员，并非影响估计、排名或操作建议。来源无法评估的公司不包含在该结论之内。"));
    d.appendChild(lead);
    function count(value) { return Number.isSafeInteger(value) && value >= 0 ? String(value) : "—"; }
    screens.forEach(function (screen) {
      var box = el("div", "ox-leg");
      var h = el("h3"); h.appendChild(bi(screen.label)); box.appendChild(h);
      if (snapshot.source?.chain === 'dollar_spike_em_multinational') {
        var limits = {
          em_revenue_exposure: {en: 'Disclosed EM revenue is a conservative lower bound; mixed geographic regions are excluded. Missing disclosures remain unevaluable.', zh: '已披露的新兴市场营收是保守下限，不计入混合地区。缺失披露仍属无法评估。'},
          multinational_fx_translation: {en: 'Foreign revenue is a disclosed screening input, not a measured earnings response to this dollar move.', zh: '海外营收是已披露的筛选输入，并非本次美元变化对盈利影响的测量。'},
          dollar_debt_burden: {en: "The screen assumes US filers' debt is USD-denominated. This is a stated assumption: debt currency is not measured in the substrate.", zh: '此筛选假设美国披露人的债务以美元计价。这是明示假设；底层数据未测量债务币种。'},
          em_commodity_sector_proxy: {en: 'Materials and Energy sector membership is a coarse proxy, not a per-company EM revenue measurement.', zh: '材料与能源行业归属是粗略代理，并非逐公司新兴市场营收测量。'}
        };
        if (limits[screen.id]) { var limit = el('p','ox-note'); limit.dataset.screenQualification = screen.id; limit.appendChild(bi(limits[screen.id])); box.appendChild(limit); }
      }
      if (screen.note) { var note = el("p", "ox-note"); note.appendChild(bi(screen.note)); box.appendChild(note); }
      var companies = screen.companies;
      if (companies && Array.isArray(companies.linked) && Array.isArray(companies.unlinked)) {
        var coverage = el("p", "ox-note");
        coverage.appendChild(say("Recorded members: ", "已记录成员："));
        coverage.appendChild(document.createTextNode(count(screen.n)));
        coverage.appendChild(say(" · Could not evaluate: ", " · 无法评估："));
        coverage.appendChild(document.createTextNode(count(screen.unevaluable)));
        box.appendChild(coverage);
        var clock = el("p", "ox-note");
        clock.appendChild(say("Membership date: ", "成员名单日期："));
        clock.appendChild(document.createTextNode(snapshot.source.asof || "—"));
        clock.appendChild(say(" · Substrate date: ", " · 基础数据日期："));
        var range = snapshot.source.substrate_asof;
        var start = range && typeof range.min === "string" ? range.min : null;
        var end = range && typeof range.max === "string" ? range.max : null;
        var dates = start && end ? (start === end ? start : start + " – " + end) : null;
        clock.appendChild(document.createTextNode(dates || "—"));
        box.appendChild(clock);
        var list = el("ul", "ox-exposure-members");
        var epoch = readingEpoch;
        companies.linked.forEach(function (entry) {
          if (!entry || typeof entry.symbol !== "string" || typeof entry.security_id !== "string") return;
          var row = el("li"); row.appendChild(el("strong", null, entry.symbol));
          var company = document.getElementById("ox-company");
          if (company) {
            var button = el("button", "ox-cta secondary"); button.type = "button";
            button.appendChild(say("Inspect company disclosures", "查看公司披露"));
            function readiness() { button.disabled = company.dataset.companyReady !== "true"; }
            readiness();
            if (button.disabled) company.addEventListener("ontology-company-ready", readiness, { once: true });
            button.addEventListener("click", function () {
              if (epoch !== readingEpoch || !document.contains(button) || button.disabled) return;
              company.dispatchEvent(new CustomEvent("ontology-select-company", { detail: {
                symbol: entry.symbol, security_id: entry.security_id,
                asof: snapshot.source.asof, manifest_hash: snapshot.source.source_manifest_hash
              }}));
            });
            row.appendChild(button);
          }
          list.appendChild(row);
        });
        companies.unlinked.forEach(function (entry) {
          if (!entry || typeof entry.symbol !== "string") return;
          var row = el("li"); row.appendChild(el("strong", null, entry.symbol));
          var refusal = el("span", "ox-note");
          refusal.appendChild(say("Identity could not be verified for this reading.", "本次读数无法核实其身份。"));
          row.appendChild(refusal); list.appendChild(row);
        });
        if (list.childNodes.length) box.appendChild(list);
        else { var empty = el("p", "ox-note"); empty.appendChild(say("No company members in this owner reading.", "本次来源读数没有公司成员。")); box.appendChild(empty); }
        if (screen.cuts && typeof screen.cuts === "object") {
          var cuts = detail("Owner screen thresholds", "来源筛选阈值");
          Object.keys(screen.cuts).forEach(function (key) {
            var line = el("p", "ox-note");
            line.textContent = key + ": " + JSON.stringify(screen.cuts[key]); cuts.appendChild(line);
          });
          box.appendChild(cuts);
        }
      } else {
        var unavailable = el("p", "ox-note");
        unavailable.appendChild(say("No actionable company membership is established for this reading.", "本次读数尚未确立可继续查看的公司成员名单。"));
        box.appendChild(unavailable);
      }
      d.appendChild(box);
    });
    return d;
  }

  function renderSourceDetail(snapshot) {
    var d = detail("Study: where every number on this page came from",
      "溯源：本页面每个数字的来源");
    var src = snapshot.source;

    var kv = el("dl", "ox-kv");
    function row(labelEn, labelZh, value) {
      var dt = el("dt");
      dt.appendChild(say(labelEn, labelZh));
      kv.appendChild(dt);
      kv.appendChild(el("dd", null, value));
    }
    row("Effective as of", "数据截至", src.asof || "—");
    row("Artifact built", "产物构建于", src.built || "—");
    row("Composed at", "本次生成于", snapshot.generated_at || "—");
    row("Path revision", "路径版本", src.rev == null ? "—" : String(src.rev));
    row("Owner state schema", "所有者状态模式", src.state_schema || "—");
    row("Composed by", "生成方法", src.composer_method || "—");
    row("Snapshot contract", "快照契约", snapshot.schema || "—");
    d.appendChild(kv);

    /* The full digest, not a prefix. A truncated hash cannot be recomputed
       against, which is the only thing a read receipt is for. */
    var manifest = el("p", "ox-hash");
    manifest.appendChild(say("Read manifest", "读取清单"));
    manifest.appendChild(el("code", null, src.source_manifest_hash || "—"));
    d.appendChild(manifest);
    var manifestNote = el("p", "ox-note");
    manifestNote.appendChild(say(
      "That digest binds the composing method above together with the exact bytes of "
      + "every file read below. It identifies this read; it is not a signature by the "
      + "owners of the data.",
      "该摘要将上述生成方法与下列各文件本次读取的确切字节绑定在一起。"
      + "它用于标识本次读取，并非数据所有者的签名。"));
    d.appendChild(manifestNote);

    var readsBox = el("div", "ox-leg");
    var rh = el("h3");
    rh.appendChild(say("Files read for this answer", "为本次回答读取的文件"));
    readsBox.appendChild(rh);
    (src.reads || []).forEach(function (read) {
      var line = el("p", "ox-hash");
      line.appendChild(el("span", "ox-hash-path", read.path));
      line.appendChild(el("code", null, "sha256:" + read.sha256));
      line.appendChild(el("span", "ox-hash-size", read.bytes + " B"));
      readsBox.appendChild(line);
    });
    if (!(src.reads || []).length) {
      var none = el("p", "ox-note");
      none.appendChild(say("No read receipts were recorded.", "未记录任何读取凭证。"));
      readsBox.appendChild(none);
    }
    d.appendChild(readsBox);

    var freshness = el("p", "ox-note");
    freshness.appendChild(bi(src.freshness.note));
    d.appendChild(freshness);

    var k1 = snapshot.evidence.k1;
    if (k1.status !== "available") {
      var k1p = el("p", "ox-note");
      if (k1.status === "partial" && Array.isArray(k1.refs) && k1.refs.length > 0
          && k1.refs_count === k1.refs.length) {
        k1p.appendChild(say(
          "Bound transition references: " + k1.refs_count + ". These identify recorded instrument events, not independent market evidence. "
          + "Native rights and freshness policies, source-body access and historical replay remain unavailable.",
          "已绑定状态转换引用：" + k1.refs_count + "。这些引用标识已记录的工具事件，并非独立市场证据。"
          + "原生权限与时效政策、来源正文访问及历史回放仍不可用。"));
        var references = el("details", "ox-detail");
        var title = el("summary");
        title.appendChild(say("Transition reference details", "状态转换引用详情"));
        references.appendChild(title);
        var referenceList = el("ul");
        k1.refs.forEach(function (ref) {
          var entry = el("li"), native = ref.native_identity || {};
          entry.appendChild(el("p", "ox-note", String(native.transition || "") + " · " + String(native.asof || "")));
          [ref.reference_id, ref.provenance && ref.provenance.pointer].forEach(function (value) {
            var reference = el("p", "ox-hash");
            reference.appendChild(el("code", "", String(value || "")));
            entry.appendChild(reference);
          });
          referenceList.appendChild(entry);
        });
        references.appendChild(referenceList);
        d.appendChild(references);
      } else if (k1.reason_code === "eligible_transition_not_k1_resolved"
          || k1.reason_code === "native_transition_reference_unavailable") {
        k1p.appendChild(say(
          "The owners have recorded " + k1.recorded_transitions + " transition(s) for this "
          + "path, but this page resolved none of them into a formal evidence reference, so "
          + "none is cited. A recorded transition is not itself a reference.",
          "所有者已记录该路径的 " + k1.recorded_transitions + " 次状态转换，"
          + "但本页面未将其中任何一次解析为正式证据引用，故不予引用。"
          + "已记录的状态转换本身并不构成引用。"));
      } else {
        k1p.appendChild(say(
          "No formal evidence reference is cited for this reading. The current summary is a "
          + "derived view the evidence contract does not accept as a citable source, and no "
          + "recorded transition exists to cite instead. The readings above come straight "
          + "from the owner fields, with the read receipts listed here.",
          "本次读数未引用正式证据。当前汇总属于派生视图，证据契约不接受其作为可引用来源，"
          + "亦无已记录的状态转换可供引用。上文读数直接取自所有者字段，"
          + "其读取凭证已在此列出。"));
      }
      d.appendChild(k1p);
    }

    if (snapshot.display_permission
        && snapshot.display_permission.status !== "determined") {
      var perm = el("p", "ox-note");
      perm.appendChild(say(
        "Whether the underlying sources may be redistributed is not determined on this "
        + "page. Access to this reading is controlled by your account, which is a "
        + "different question.",
        "本页面不判定底层数据源是否可再分发。本次读数的访问权限由您的账户控制，"
        + "两者并非同一问题。"));
      d.appendChild(perm);
    }

    /* Two different things end up in `gaps` and calling them both "missing"
       would be inaccurate: something the owners never published, and something
       they published that this surface refused to print. Both are named
       individually — a count tells the reader something is absent without ever
       letting them find out what. */
    var missing = (snapshot.gaps || []).filter(function (g) {
      return g.kind !== "text_withheld" && g.kind !== "text_untranslated";
    });
    var withheld = (snapshot.gaps || []).filter(function (g) {
      return g.kind === "text_withheld" || g.kind === "text_untranslated";
    });

    function gapList(items, headEn, headZh) {
      var box = el("div", "ox-leg");
      var h = el("h3");
      h.appendChild(say(headEn, headZh));
      box.appendChild(h);
      var ul = el("ul", "ox-gaps");
      items.forEach(function (gap) {
        var li = el("li");
        li.appendChild(gapLabel(gap));
        /* The reader-facing location only. `gap.where` is the machine field
           path — it names internal fields and, for the watch list, carries the
           refutation family this page does not print. Making a gap reachable
           must not smuggle either onto the surface. */
        if (gap.where_label) {
          var where = el("span", "ox-gap-where");
          where.appendChild(bi(gap.where_label));
          li.appendChild(where);
        }
        if (gap.reason_label) {
          var why = el("span", "ox-gap-why");
          why.appendChild(bi(gap.reason_label));
          li.appendChild(why);
        }
        ul.appendChild(li);
      });
      box.appendChild(ul);
      return box;
    }

    if (missing.length) {
      var mBox = gapList(missing,
        "Published by the owners incompletely", "所有者发布不完整之处");
      var mNote = el("p", "ox-note");
      mNote.appendChild(say("These are named rather than filled in.",
        "以上各项仅具名列出，未作填补。"));
      mBox.appendChild(mNote);
      d.appendChild(mBox);
    }
    if (withheld.length) {
      var wBox = gapList(withheld, "Published, but not shown here", "已发布但未在此展示");
      var wNote = el("p", "ox-note");
      wNote.appendChild(say(
        "This page held these back — the wording would not meet its standard for "
        + "reader-facing text. The condition each one describes is shown with its step.",
        "本页面主动保留了以上内容——其措辞不符合本页面面向读者文本的标准。"
        + "其所描述的条件已随对应环节展示。"));
      wBox.appendChild(wNote);
      d.appendChild(wBox);
    }
    return d;
  }

  var themeRoot = document.getElementById("ox-theme");
  function deliverThemeReading() {
    if (themeRoot && scenarioReading) themeRoot.dispatchEvent(new CustomEvent("ontology-reading", { detail: scenarioReading }));
  }
  if (themeRoot) themeRoot.addEventListener("ontology-consumer-ready", deliverThemeReading);
  var scenarioRoot = document.getElementById("ox-scenario");
  function deliverScenarioReading() {
    if (scenarioRoot && scenarioReading) scenarioRoot.dispatchEvent(new CustomEvent("ontology-reading", { detail: scenarioReading }));
  }
  if (scenarioRoot) scenarioRoot.addEventListener("ontology-consumer-ready", deliverScenarioReading);
  var portfolioRoot = document.getElementById("ox-portfolio");
  function deliverPortfolioReading() {
    if (portfolioRoot && portfolioReading) portfolioRoot.dispatchEvent(new CustomEvent("ontology-reading", { detail: portfolioReading }));
  }
  if (portfolioRoot) portfolioRoot.addEventListener("ontology-consumer-ready", deliverPortfolioReading);

  function validTargetPredicate(p) {
    var count = 0;
    function text(v,n) { return typeof v === "string" && v.length > 0 && v.length <= n && !/[\x00-\x1f]/.test(v); }
    function scalar(v) { return v === null || typeof v === "boolean" || typeof v === "number" && isFinite(v) || text(v,128); }
    function test(t,depth) {
      if (++count > 64 || depth > 8 || !t || typeof t !== "object" || Array.isArray(t)) return false;
      var keys=Object.keys(t), groups=keys.filter(function(k){return k === "all" || k === "any";});
      if (groups.length) return groups.length === 1 && keys.length === 1 && Array.isArray(t[groups[0]])
        && t[groups[0]].length > 0 && t[groups[0]].length <= 64
        && t[groups[0]].every(function(child){return test(child,depth+1);});
      if (!keys.every(function(k){return ["path","series","metric","window","lookback","vs","ratio","op","value"].includes(k);})
          || !["gt","gte","lt","lte","eq","ne","is_true","is_false","in","in_contains"].includes(t.op)
          || (Object.hasOwn(t,"path") === Object.hasOwn(t,"series"))) return false;
      if (t.op !== "is_true" && t.op !== "is_false" && !Object.hasOwn(t,"value")) return false;
      if (Object.hasOwn(t,"value") && !(Array.isArray(t.value) ? t.value.length > 0 && t.value.length <= 64 && t.value.every(scalar) : scalar(t.value))) return false;
      if (Object.hasOwn(t,"series") && (!["ret","ret_bp","ma_slope","rs","ratio_ret","off_high_bp"].includes(t.metric)
          || !Number.isInteger(t.window) || t.window <= 0 || t.window > 100000
          || (Object.hasOwn(t,"vs") !== (t.metric === "rs")) || (Object.hasOwn(t,"ratio") !== (t.metric === "ratio_ret")))) return false;
      return keys.every(function(k){return k === "value" || k === "window" || k === "lookback"
        ? k !== "lookback" || Number.isInteger(t[k]) && t[k] > 0 && t[k] <= 100000 : text(t[k],128);});
    }
    return p && Object.keys(p).sort().join(",") === "node_id,src,test" && text(p.node_id,128) && text(p.src,64) && test(p.test,0);
  }

  function targetPredicateSentence(t) {
    var p=el("div"),group=t.all?"all":t.any?"any":null;
    if (group) {
      p.appendChild(group === "all" ? say("All conditions must hold:","以下条件须全部满足：") : say("At least one condition must hold:","以下条件至少须满足一项："));
      var list=el("ul");t[group].forEach(function(child){var li=el("li");li.appendChild(targetPredicateSentence(child));list.appendChild(li);});p.appendChild(list);return p;
    }
    var paths={"state.rates.direction":["Real-yield direction","实际收益率方向"],
      "state.rates.real_10y_chg_63d_bp":["63-observation change in the real 10-year yield (bp)","实际10年期收益率63期变动（基点）"],
      "dollar_desk.trend":["Dollar trend","美元趋势"],"dollar_desk.usd_pos_pctile":["Dollar positioning percentile","美元持仓百分位"],
      "transmission.usd_dir":["Dollar transmission direction","美元传导方向"],"transmission.headwind_for":["Declared headwind list","声明的逆风列表"]};
    if (t.path) p.appendChild(Object.prototype.hasOwnProperty.call(paths,t.path) ? say.apply(null,paths[t.path]) : say("Declared field "+t.path,"声明字段 "+t.path));
    else {
      var metrics={ret:["change (%)","变动（%）"],ret_bp:["change (bp)","变动（基点）"],rs:["relative return (pp)","相对回报（百分点）"],
        ratio_ret:["ratio change (%)","比率变动（%）"],ma_slope:["moving-average slope","均线斜率"],off_high_bp:["distance below high (bp)","距高点幅度（基点）"]};
      p.appendChild(document.createTextNode(t.series+(t.vs?" vs "+t.vs:t.ratio?" / "+t.ratio:"")+" · "));
      p.appendChild(say(t.window+"-observation "+metrics[t.metric][0],t.window+"期"+metrics[t.metric][1]));
      if (t.lookback) p.appendChild(say(" · slope lookback: "+t.lookback+" observations"," · 斜率回看："+t.lookback+"期"));
    }
    var names={up:["up","向上"],rising:["rising","上升"],strengthening:["strengthening","走强"],"EM equities":["EM equities","新兴市场股票"]};
    p.appendChild(document.createTextNode(" "));
    if (t.op === "is_true" || t.op === "is_false") p.appendChild(t.op === "is_true" ? say("must be true","须为真") : say("must be false","须为假"));
    else {
      p.appendChild(t.op === "in_contains" ? say("must include ","须包含 ") : t.op === "in" ? say("must be one of ","须为以下之一 ") : document.createTextNode((_opGlyph(t.op)||t.op)+" "));
      var values=Array.isArray(t.value)?t.value:[t.value];values.forEach(function(v,i){if(i)p.appendChild(document.createTextNode(", "));
        p.appendChild(Object.prototype.hasOwnProperty.call(names,v) ? say.apply(null,names[v]) : document.createTextNode(String(v)));});
    }
    return p;
  }

  function renderTransmissionGap(snapshot) {
    var box = card("Transmission gap", "传导缺口");
    box.setAttribute("data-transmission-gap", "");
    var g = snapshot.transmission_gap, src = snapshot.source;
    var states = {
      waiting_inside_window: ["Waiting inside the declared window", "正在声明的窗口内等待"],
      stalled: ["Native stall annotation", "原生停滞标注"],
      contradicted: ["Current readings disagree with the expected sequence", "当前读数与预期顺序不一致"],
      condition_stopped: ["A watched condition stopped this episode", "观察条件使本轮过程停止"],
      owner_expired: ["The owner recorded the window as expired", "数据方已记录窗口到期"],
      owner_completed: ["The owner recorded this episode as complete", "数据方已记录本轮过程完成"],
      dormant: ["No active episode", "暂无活动过程"]
    };
    function note(en, zh) { var p = el("p", "ox-note"); p.appendChild(say(en,zh)); box.appendChild(p); }
    function calendar(v) { return typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v)
      && isFinite(Date.parse(v)) && new Date(v).toISOString().slice(0,10) === v; }
    function instant(v) { return typeof v === "string" ? Date.parse(v.replace(" UTC","Z").replace(" ","T")) : NaN; }
    function same(a,b) { return JSON.stringify(a) === JSON.stringify(b); }
    function unavailable(reason) {
      box.setAttribute("data-gap-state", "source_unavailable");
      note("A transmission gap cannot be qualified for this reading. Missing data is not failed transmission.",
        "本次读数无法确认传导缺口。缺失数据不代表传导失败。");
      if (reason === "owner_transition_unsettled") note("The target already reads met, but the owner has not settled the next transition.",
        "目标条件已满足，但数据方尚未确认下一次状态转换。");
      else if (reason === "owner_window_elapsed_unsettled") note("The captured window has elapsed without a settled owner transition. This page does not expire it.",
        "所记录窗口已结束，但数据方尚未确认状态转换。本页不会自行判定到期。");
      else if (reason === "arming_observation_unavailable" || reason === "episode_ledger_unavailable")
        note("The recorded initiating observation is unavailable.", "已记录的起始观测不可用。");
      return box;
    }
    if (!g || g.schema !== "txi_gap_projection.v1" || g.scope !== "txi_only"
        || g.method_class !== "native_owner_state_projection" || g.instrument_only !== true || g.market_thesis_verdict !== null
        || !g.identity || g.identity.chain !== src.chain || g.identity.rev !== src.rev
        || g.identity.episode_id !== snapshot.state.episode_id || g.owner_state !== snapshot.state.owner_state
        || !g.observation || g.observation.asof !== src.asof || !calendar(src.asof)
        || !isFinite(instant(src.built)) || instant(g.observation.built) !== instant(src.built)
        || g.ledger?.clock_basis !== "native_transition_asof" || g.ledger.historical_knowledge !== "unavailable") return unavailable();
    if (g.status === "unavailable" && g.state === "source_unavailable") return unavailable(g.reason);
    if (g.status !== "available" || g.reason !== null || !Object.prototype.hasOwnProperty.call(states,g.state)) return unavailable();
    var legs = snapshot.path.legs, hops = snapshot.path.hops, p = g.pending_hop;
    var ledger = (src.reads || []).find(function(r) { return r.path === "data/transmission/chain_episodes.jsonl"; });
    if (!same(g.current_contradiction,snapshot.contradiction) || !same(g.watched_conditions,snapshot.invalidators)) return unavailable();
    if (g.state !== "dormant") {
      var initial = g.initiating_observation;
      if (!ledger || ledger.sha256 !== g.ledger.sha256 || ledger.bytes !== g.ledger.bytes
          || !initial || initial.node_id !== legs[0].node_id || !calendar(initial.asof) || initial.asof > src.asof
          || !Array.isArray(initial.receipts) || !initial.receipts.length || initial.receipts.length > 64) return unavailable();
    } else if (g.owner_state !== "dormant" || g.identity.episode_id !== null || p !== null) return unavailable();
    if (g.state === "owner_completed") { if (g.owner_state !== "expressed" || p !== null) return unavailable(); }
    else if (g.state !== "dormant") {
      var hop = hops.find(function(h) { return h.hop_id === p?.hop_id; });
      var target = legs.find(function(n) { return n.node_id === p?.to; });
      if (!p || !hop || !target || p.from !== hop.from || p.to !== hop.to || !same(p.lag_d,hop.lag_d)
          || !validTargetPredicate(p.expected_target) || !same(p.expected_target,target.declared_predicate)
          || p.expected_target.node_id !== target.node_id || p.expected_target.src !== target.src
          || !same(p.applicability_assumption,hop.condition) || !Array.isArray(p.lag_d) || p.lag_d.length !== 2
          || !p.lag_d.every(function(n){return typeof n === "number" && isFinite(n);}) || p.lag_d[0] < 0 || p.lag_d[1] < p.lag_d[0]
          || p.elapsed_basis !== "native_calendar_days" || !calendar(p.anchor_asof) || p.anchor_asof > src.asof
          || !Number.isInteger(p.elapsed_calendar_days) || p.elapsed_calendar_days !== (Date.parse(src.asof)-Date.parse(p.anchor_asof))/86400000
          || p.minimum_lag_elapsed !== (p.elapsed_calendar_days >= p.lag_d[0])
          || !p.target_observation || p.target_observation.asof !== src.asof || p.target_observation.node_id !== target.node_id
          || p.target_observation.confirmed !== target.confirmed || target.observation !== "observed"
          || !same(p.target_observation.receipts,target.receipts)) return unavailable();
      if (["waiting_inside_window","stalled","contradicted"].includes(g.state)
          && (!["arming","propagating"].includes(g.owner_state) || p.elapsed_calendar_days > p.lag_d[1])) return unavailable();
      if (["waiting_inside_window","stalled"].includes(g.state) && target.confirmed !== false) return unavailable();
      if (g.state === "stalled" && (g.turn_watch?.status !== "available" || g.turn_watch.stalling !== true)) return unavailable();
      if (g.state === "contradicted" && !snapshot.contradiction) return unavailable();
      if (g.state === "owner_expired" && g.owner_state !== "expired") return unavailable();
      if (g.state === "condition_stopped" && (g.owner_state !== "failed" || !g.condition_stop
          || !calendar(g.condition_stop.asof) || g.condition_stop.asof > src.asof
          || !snapshot.invalidators.some(function(c){return c.id === g.condition_stop.condition_id;}))) return unavailable();
    }
    box.setAttribute("data-gap-state",g.state);
    var headline = el("h3"); headline.appendChild(say.apply(null,states[g.state])); box.appendChild(headline);
    note("TXI conditions only. This is an instrument reading, not a verdict on the market thesis.",
      "仅反映 TXI 条件。这是仪表读数，不是对市场论点的裁定。");
    if (p) {
      var named = el("p"); named.appendChild(bi(target.title)); box.appendChild(named);
      var assumption=el("p","ox-note");assumption.setAttribute("data-gap-applicability","");
      assumption.appendChild(say("Applicability assumption: ","适用前提："));
      assumption.appendChild(p.applicability_assumption ? bi(p.applicability_assumption) : say("Not declared","未声明"));box.appendChild(assumption);
      note("Declared lag: "+p.lag_d[0]+"–"+p.lag_d[1]+" calendar days. Elapsed: "+p.elapsed_calendar_days+" calendar days since "+p.anchor_asof+".",
        "声明滞后："+p.lag_d[0]+"–"+p.lag_d[1]+" 个日历日。自 "+p.anchor_asof+" 起已过 "+p.elapsed_calendar_days+" 个日历日。");
      if (!p.minimum_lag_elapsed) note("The declared minimum lag has not elapsed.", "声明的最短滞后尚未届满。");
      var focus = el("button","ox-action"); focus.type="button";focus.setAttribute("aria-controls",LEG_DETAIL_ID);
      focus.appendChild(say("Inspect the expected step", "查看预期环节"));
      focus.addEventListener("click",function(){focusLeg(p.to);});box.appendChild(focus);
    }
    var d = detail("Initiating observation, target and source clocks", "起始观测、目标与来源时间");
    function row(en,zh,value) { var kv=el("dl","ox-kv"),dt=el("dt");dt.appendChild(say(en,zh));kv.appendChild(dt);kv.appendChild(el("dd",null,value));d.appendChild(kv); }
    function readings(receipts) { var kv=el("dl","ox-kv"); (receipts || []).forEach(function(r){var dt=el("dt"),dd=el("dd");
      dt.appendChild(receiptLabel(r));dd.appendChild(receiptValue(r));kv.appendChild(dt);kv.appendChild(dd);});d.appendChild(kv); }
    if (g.initiating_observation) { row("Initiating observation","起始观测",g.initiating_observation.asof);readings(g.initiating_observation.receipts); }
    if (p) {
      var declared=el("div");declared.setAttribute("data-gap-target-predicate","");
      var title=el("p");title.appendChild(say("Expected target condition","预期目标条件"));declared.appendChild(title);
      declared.appendChild(targetPredicateSentence(p.expected_target.test));d.appendChild(declared);
      row("Native source adapter","原生来源适配器",p.expected_target.src);
      row("Target observation","目标观测",p.target_observation.asof);readings(target.receipts);
    }
    if (g.condition_stop) { row("Condition stopped on","条件停止日期",g.condition_stop.asof);readings(g.condition_stop.receipts); }
    if (snapshot.invalidators.length) {
      var watch = el("p","ox-note");watch.appendChild(say("Watched conditions: ","观察条件："));
      snapshot.invalidators.forEach(function(c,i){if(i)watch.appendChild(document.createTextNode(" · "));if(c.note)watch.appendChild(bi(c.note));else if(c.watched && c.watched.series)watch.appendChild(watchedSentence(c.watched));else watch.appendChild(say("Condition wording unavailable", "条件描述不可用"));});d.appendChild(watch);
    }
    row("Owner observation / build","数据方观测 / 构建",g.observation.asof+" / "+g.observation.built);
    row("Path revision","路径版本",String(g.identity.rev));
    if (g.identity.episode_id) row("Episode reference","过程引用",g.identity.episode_id);
    row("Source generation","来源版本",src.source_manifest_hash);
    if (g.ledger.sha256) row("Captured ledger SHA-256","已读取账本 SHA-256",g.ledger.sha256);
    var caution=el("p","ox-note");caution.appendChild(say("The ledger records transition dates without ingestion clocks. This is a captured reading, not historical point-in-time evidence.",
      "账本记录状态转换日期，但不含接收时间。本页是本次读取结果，不是历史时点证据。"));d.appendChild(caution);
    box.appendChild(d);return box;
  }


  function render(snapshot) {
    root.textContent = "";

    var hero = el("header", "ox-hero ox-hero--answer");
    var lead = el("div", "ox-hero-lead");
    var eyebrow = el("p", "ox-eyebrow");
    eyebrow.appendChild(bi(snapshot.path.title));
    lead.appendChild(eyebrow);

    var stateRow = el("div", "ox-state");
    stateRow.setAttribute("data-state", snapshot.state.code);
    var word = el("span", "ox-state-word");
    word.appendChild(bi(snapshot.state.label));
    stateRow.appendChild(word);
    var asof = el("span", "ox-asof", snapshot.source.asof || "");
    stateRow.appendChild(asof);

    var answerTitle = el("h1", "ox-stance ox-answer-title");
    answerTitle.appendChild(stance(snapshot));
    lead.appendChild(answerTitle);
    var heroAction = renderHeroAction(snapshot);
    if (heroAction) lead.appendChild(heroAction);
    lead.appendChild(renderMeta(snapshot));
    var revised = continuationNotice(snapshot);
    if (revised) lead.appendChild(revised);
    hero.appendChild(lead);
    var answerSummary = renderAnswerSummary(snapshot);
    answerSummary.insertBefore(stateRow, answerSummary.firstChild);
    hero.appendChild(answerSummary);
    root.appendChild(hero);

    root.appendChild(renderRail(snapshot));

    var answers = el("section", "ox-answers");
    answers.appendChild(renderWhatChanged(snapshot));
    answers.appendChild(renderWhyItMatters(snapshot));
    answers.appendChild(renderBlocking(snapshot));
    answers.appendChild(renderNextAction(snapshot));
    root.appendChild(answers);

    root.appendChild(renderTransmissionGap(snapshot));

    legDetail = renderLegDetail(snapshot);
    root.appendChild(legDetail);
    var exposure = renderExposure(snapshot);
    if (exposure) root.appendChild(exposure);
    root.appendChild(renderSourceDetail(snapshot));
    settle();
  }

  async function load() {
    invalidateReading();
    if (!acceptedChain) { gateForFailure("chain_not_admitted"); return; }
    var epoch = readingEpoch;
    root.replaceChildren();
    root.setAttribute("aria-busy", "true");
    var request = new AbortController();
    activeRequest = request;
    try {
      var auth = await withAuth({ Accept: "application/json" });
      if (epoch !== readingEpoch) return;
      if (!auth.identity) { signedOutGate(); return; }
      var response = await fetch(API, {
        credentials: "same-origin", cache: "no-store", headers: auth.headers,
        signal: request.signal
      });
      if (epoch !== readingEpoch) return;
      if (response.status === 401) {
        signedOutGate();
        return;
      }
      if (response.status === 403) {
        gate("Included with full access", "包含于完整访问权限",
          "Your account is signed in but does not include this desk yet.",
          "您的账户已登录，但尚未包含此功能。",
          "See plans", "查看方案", "/plans.html?upgrade=1");
        return;
      }
      var snapshot = await response.json().catch(function () { return null; });
      if (epoch !== readingEpoch) return;
      if (!response.ok) {
        var failure = snapshot && snapshot.detail && typeof snapshot.detail === "object" ? snapshot.detail : {};
        gateForFailure(failure.code || "request_failed");
        return;
      }
      if (!snapshot || typeof snapshot !== "object" || Array.isArray(snapshot)
          || snapshot.schema !== "ontology_explorer_snapshot.v1"
          || snapshot.source?.chain !== selectedChain) {
        gateForFailure("invalid_snapshot");
        return;
      }
      var sameOwner = await sameReadingOwner(auth.identity);
      if (epoch !== readingEpoch) return;
      if (!sameOwner) { signedOutGate(); return; }
      render(snapshot);
      focusFromHash();
      portfolioReading = {
        chain: snapshot.source.chain, source_manifest_hash: snapshot.source.source_manifest_hash,
        asof: snapshot.company_exposure && snapshot.company_exposure.asof,
        identity_sha256: snapshot.company_exposure && snapshot.company_exposure.identity_source && snapshot.company_exposure.identity_source.sha256 || null,
        owner_id: auth.identity.id,
        channels: (snapshot.exposure_screens || []).map(function (s) { return {id:s.id, label:s.label}; })
      };
      deliverPortfolioReading();
      scenarioReading = Object.assign({}, snapshot.source, { owner_id: auth.identity.id });
      deliverScenarioReading();
      deliverThemeReading();
    } catch (error) {
      if (epoch === readingEpoch) gateForFailure("request_failed");
    } finally {
      if (activeRequest === request) activeRequest = null;
    }
  }

  function signedOutGate() {
    gate("Sign in to see the current path", "登录后查看当前路径",
      "This page describes the product. The current reading is served only to a signed-in account.",
      "本页面介绍该产品。当前读数仅向已登录账户提供。",
      "Sign in", "登录", signinHref());
  }
  window.addEventListener("mdx-auth", function (event) {
    var user = event.detail && event.detail.user;
    var next = user && typeof user.id === "string" ? user.id : null;
    if (next === canonicalOwner && (!event.detail || event.detail.event !== "SIGNED_OUT")) return;
    canonicalOwner = next;
    invalidateReading();
    root.replaceChildren();
    if (next) load(); else signedOutGate();
  });
  window.addEventListener("pagehide", function () { invalidateReading(); root.replaceChildren(); });
  window.addEventListener("pageshow", function (event) { if (event.persisted) load(); });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", load);
  } else {
    load();
  }
})();
