/* AI Brief live fragments. The server and static pages share ONE Jinja renderer.
   One in-flight GET per lens, bounded response/deadline, no provider calls from
   the browser, no persisted account data and no dependency on DATA_BASE/CDN. */
(function () {
  "use strict";
  if (window.__mmAibriefLive) return;
  window.__mmAibriefLive = true;
  var requests = new Map();
  var lastRead = new Map();
  var lenses = ["macro", "china", "btc"];
  var maxBytes = 2 * 1024 * 1024;

  function bilingual(node, en, zh) {
    node.replaceChildren();
    [["l-en", en], ["l-zh", zh]].forEach(function (pair) {
      var span = document.createElement("span");
      span.className = pair[0]; span.textContent = pair[1]; node.appendChild(span);
    });
  }
  function expired(root) {
    if (Number.isFinite(root.__aibDeadline)) return performance.now() >= root.__aibDeadline;
    var generated = Date.parse(root.dataset.generatedAt || "");
    var date = root.dataset.stateAsof || "";
    var evidence = /^\d{4}-\d{2}-\d{2}$/.test(date) ? Date.parse(date + "T00:00:00Z") : NaN;
    var days = Number(root.dataset.refreshDays);
    days = Number.isInteger(days) && days >= 1 && days <= 7 ? days : 1;
    var now = Date.now();
    return !Number.isFinite(generated) || !Number.isFinite(evidence) || generated > now + 300000 || evidence > now ||
      now >= generated + days * 86400000 || now >= evidence + (root.dataset.lens === "btc" ? 48 : 96) * 3600000;
  }
  function archive(root) {
    var content = root.querySelector(".aib2-content");
    if (!content || root.querySelector(".aib2-retained")) return;
    var details = document.createElement("details"), summary = document.createElement("summary");
    details.className = "aib2-retained";
    bilingual(summary, "Previous AI read · evidence " + (root.dataset.stateAsof || "unavailable"),
      "历史 AI 解读 · 数据日期 " + (root.dataset.stateAsof || "暂无"));
    details.appendChild(summary); content.before(details); details.appendChild(content);
  }
  function status(root, kind, en, zh) {
    root.dataset.status = kind;
    var label = root.querySelector(".aib2-status-text");
    if (label) bilingual(label, en, zh);
  }
  function age(root) {
    if (!root.__aibDenied && expired(root)) {
      archive(root);
      status(root, "stale", "AI update overdue. The previous read is archived below; it is not a current market view.",
        "AI 更新已逾期。下方旧解读仅供存档参考，不代表当前市场。");
    }
  }
  function denied(root, code) {
    root.__aibDenied = true;
    root.querySelectorAll(".aib2-content,.aib2-retained,.aib2-live-facts").forEach(function (node) { node.remove(); });
    status(root, "unavailable", code === 401 ? "Sign in to load the current AI brief." : "This account cannot load the current AI brief.",
      code === 401 ? "登录后可查看当前 AI 简报。" : "此账户无法读取当前 AI 简报。");
  }
  async function boundedJSON(response) {
    if (!/^application\/json\b/i.test(response.headers.get("content-type") || "")) throw new Error("content_type");
    if (Number(response.headers.get("content-length")) > maxBytes) throw new Error("response_size");
    var reader = response.body.getReader(), decoder = new TextDecoder(), bytes = 0, text = "";
    try {
      while (true) {
        var part = await reader.read();
        if (part.done) break;
        bytes += part.value.byteLength;
        if (bytes > maxBytes) throw new Error("response_size");
        text += decoder.decode(part.value, {stream: true});
      }
      return JSON.parse(text + decoder.decode());
    } finally { await reader.cancel().catch(function () {}); }
  }
  function fragment(data, lens) {
    var serverTime = Date.parse(data.server_time), clientTime = Date.now();
    if (data.schema !== "aibrief.live.v1" || data.lens !== lens || !Number.isSafeInteger(data.sequence) || data.sequence < 0 ||
        !/^[a-f0-9]{64}$/.test(data.revision || "") || !Number.isFinite(serverTime) ||
        Math.abs(serverTime - clientTime) > 300000 || typeof data.html !== "string") throw new Error("contract");
    var doc = new DOMParser().parseFromString(data.html, "text/html");
    var roots = doc.body.querySelectorAll(".aib2");
    if (doc.body.children.length !== 1 || roots.length !== 1 || roots[0].dataset.lens !== lens ||
        doc.querySelector("script,iframe,object,embed,link,style,form,base,meta")) throw new Error("fragment");
    doc.body.querySelectorAll("*").forEach(function (node) {
      Array.from(node.attributes).forEach(function (attr) {
        if (/^on/i.test(attr.name) || attr.name === "srcdoc" ||
            /^(href|src|xlink:href)$/i.test(attr.name)) throw new Error("active_content");
      });
    });
    return roots[0];
  }
  async function refresh(lens, roots) {
    if (requests.has(lens) || roots.every(function (root) { return root.__aibDenied; })) return;
    if (lastRead.has(lens) && performance.now() - lastRead.get(lens) < 30000) return;
    lastRead.set(lens, performance.now());
    var controller = new AbortController(), ticket = {}, start = performance.now();
    requests.set(lens, ticket);
    var timer = setTimeout(function () { controller.abort(); }, 10000);
    try {
      var response = await fetch("/api/aibrief/v1/" + lens, {
        credentials: "same-origin", cache: "no-store", redirect: "error",
        headers: {Accept: "application/json"}, signal: controller.signal
      });
      if (response.status === 401 || response.status === 403) {
        roots.forEach(function (root) { denied(root, response.status); }); return;
      }
      if (!response.ok) throw new Error("read_unavailable");
      var data = await boundedJSON(response), incoming = fragment(data, lens);
      if (controller.signal.aborted || requests.get(lens) !== ticket) return;
      roots.forEach(function (old) {
        if (!old.isConnected || old.__aibDenied || data.sequence < Number(old.dataset.sequence || 0)) return;
        // Never discard a focused control or the reader's place mid-interaction.
        // Expiry still applies immediately; the next visible refresh retries GET.
        if (old.contains(document.activeElement)) { age(old); return; }
        var next = incoming.cloneNode(true);
        var deadline = Math.min(Date.parse(data.valid_until || "") - Date.parse(data.server_time),
          Date.parse(data.valid_until || "") - Date.now());
        if (Number.isFinite(deadline)) next.__aibDeadline = start + deadline;
        var footer = old.querySelector(".aib2-footer"), slot = next.querySelector(".aib2-footer");
        if (footer && slot) slot.replaceWith(footer);
        var previous = old.querySelector(".aib2-retained"), retained = next.querySelector(".aib2-retained");
        if (retained && previous && old.dataset.generatedAt === next.dataset.generatedAt) retained.open = previous.open;
        old.replaceWith(next); age(next);
      });
    } catch (_) {
      roots.forEach(function (root) {
        if (!root.isConnected || root.__aibDenied) return;
        age(root);
        if (!expired(root)) status(root, "degraded", "Live refresh is unavailable. The retained read and its original dates are shown.",
          "实时更新暂不可用。当前显示保留的解读及其原始日期。");
      });
    } finally { clearTimeout(timer); if (requests.get(lens) === ticket) requests.delete(lens); }
  }
  function scan(fetchVisible) {
    var all = Array.from(document.querySelectorAll(".aib2[data-lens]"));
    all.forEach(age);
    if (!fetchVisible || document.hidden) return;
    lenses.forEach(function (lens) {
      var roots = all.filter(function (root) { return root.dataset.lens === lens && root.getClientRects().length; });
      if (roots.length) refresh(lens, roots);
    });
  }
  function start() {
    scan(true);
    setInterval(function () { scan(false); }, 30000);
    setInterval(function () { scan(true); }, 300000);
    document.addEventListener("visibilitychange", function () { if (!document.hidden) scan(true); });
    // A dashboard dialog/tab may become visible without navigation.
    document.addEventListener("click", function () { requestAnimationFrame(function () { scan(true); }); });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, {once: true});
  else start();
})();

/* Cortex (overnight AI deliberation) panel.

   ABX v2: the three lens brief bodies (macro / china / btc) are now SERVER-rendered
   into the page by the shared Jinja macro (templates/_aibrief_body.html.j2), so this
   file no longer fetches or renders briefs. It handles just Panel D below.

   Panel D (cortex deliberation, ADB-R7) is client-side: fetches
   site/neuralweb/cortex_memo.json and renders honest degraded copy when the overnight
   deliberation didn't run (the usual state — rate-limited). No synthetic content is
   ever generated; all output is escaped before insertion (no raw HTML). */
(function () {
  if (window.__mmAibriefCortex) return;
  window.__mmAibriefCortex = true;
  function esc(s) { var d = document.createElement("div"); d.textContent = (s == null ? "" : String(s)); return d.innerHTML; }

  // ── Panel D: Cortex deliberation (ADB-R7) ────────────────────────────────────
  // Fetch site/neuralweb/cortex_memo.json. If degraded (the steady state): render
  // one honest line. If non-degraded: render labeled AI-deliberation block with
  // as_of, what_fired, and deserves_operator. Never emit synthetic content.
  (function loadCortex() {
    var panel = document.getElementById("cortex-panel");
    var body  = document.getElementById("cortex-body");
    if (!panel || !body) return;

    fetch("neuralweb/cortex_memo.json?_=" + Date.now())
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (memo) {
        if (!memo) return; // absent → panel stays hidden

        var lang = document.documentElement.getAttribute("data-lang") === "zh" ? "zh" : "en";
        var status = (memo.run_status || {}).status || "degraded";
        var asOf   = memo.as_of || "";

        if (status === "degraded") {
          // Honest degraded copy — no synthetic content (ADB-R7)
          body.innerHTML = '<p class="mb-deg">' + esc(
            lang === "zh"
              ? "隔夜AI复盘遭速率限制，未能运行。以上简报完全基于确定性看板。"
              : "The overnight AI deliberation was rate-limited and did not run. " +
                "The brief above stands on the deterministic dashboards alone."
          ) + (asOf ? ' <span class="muted" style="font-size:11px">(' + esc(asOf.slice(0, 10)) + ')</span>' : "") + "</p>";
        } else {
          // Non-degraded: render labeled AI-deliberation block
          var h = '<div class="cortex-label">' + esc(
            lang === "zh" ? "AI 复盘输出 — 非交易信号" : "AI DELIBERATION OUTPUT — NOT A SIGNAL"
          ) + "</div>";

          if (asOf) {
            h += '<p class="muted sm" style="margin:0 0 6px">' +
              esc(lang === "zh" ? "复盘时间：" : "As of: ") +
              esc(asOf.slice(0, 16).replace("T", " ") + " UTC") + "</p>";
          }

          var summary = memo.summary || "";
          if (summary) {
            h += '<div class="cortex-section"><div class="cortex-h">' +
              esc(lang === "zh" ? "总结" : "What the overnight AI reviewer flagged") +
              "</div><p style='font-size:13px;margin:0'>" + esc(summary) + "</p></div>";
          }

          var whatFired = memo.what_fired || [];
          if (whatFired.length) {
            h += '<div class="cortex-section"><div class="cortex-h">' +
              esc(lang === "zh" ? "触发项" : "Flagged items") + "</div><ul class='cortex-list'>" +
              whatFired.map(function (x) { return "<li>" + esc(String(x)) + "</li>"; }).join("") +
              "</ul></div>";
          }

          var deserves = memo.deserves_operator || [];
          if (deserves.length) {
            h += '<div class="cortex-section"><div class="cortex-h">' +
              esc(lang === "zh" ? "需要关注" : "Items that deserve your attention") +
              "</div><ul class='cortex-list'>" +
              deserves.map(function (x) { return "<li>" + esc(String(x)) + "</li>"; }).join("") +
              "</ul></div>";
          }

          // Render optional forward_watch keys if present (W1/W2, absent today)
          var fw = memo.forward_watch || [];
          if (fw.length) {
            h += '<div class="cortex-section"><div class="cortex-h">' +
              esc(lang === "zh" ? "前瞻关注" : "Forward watch") + "</div><ul class='cortex-list'>" +
              fw.map(function (row) {
                return "<li>" + esc(row.date || "") + " — " + esc(row.label || String(row)) + "</li>";
              }).join("") + "</ul></div>";
          }

          body.innerHTML = h;
        }

        panel.style.display = "";  // reveal panel only after content is set
      })
      .catch(function () { /* fetch error → panel stays hidden */ });
  })();
})();

