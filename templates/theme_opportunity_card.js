/* Shared Theme Opportunity Card. Consumes Lane A/D owner contracts only. */
(function (global) {
  "use strict";

  var COMPONENT_VERSION = "theme-opportunity-card.presentation.v5";
  var OWNER_SCHEMA = "theme_intelligence.consumer.v1";
  var ENTRY_SCHEMA = "mastermind.entry_context.v1";
  var AXES = ["leadership", "thesis", "crowding", "entry", "health"];
  var LABELS = {
    leadership: ["Leadership", "领导力"],
    thesis: ["Economic thesis", "经济论点"],
    crowding: ["Crowding", "拥挤度"],
    entry: ["Theme-level entry", "主题层入场"],
    health: ["Evidence health", "证据健康"]
  };
  var TONES = { neutral: true, info: true, up: true, warn: true, down: true, unknown: true };
  var ROUTES = {
    tracker: "state_of_themes.html",
    foresight: "foresight.html",
    radar: "radar.html",
    sector: "sector_central.html"
  };
  var CLOCKS = ["observation", "availability", "computation", "publication"];
  var TRUE_AUTH = ["is_context_only", "display_only", "not_a_signal"];
  var FALSE_AUTH = ["may_rank", "may_gate", "may_size", "may_escalate", "may_trade"];
  var EVIDENCE_KEYS = {
    ref: true, artifact: true, source_family: true, evidence_family: true,
    source_record_id: true, observation_id: true, parent_identity: true,
    observation_session: true, input_hash: true, source_input_hash: true,
    observed_at: true, available_at: true
  };
  var QUALIFIED_STATES = {
    QUALIFIED: true,
    QUALIFIED_PENDING_CONFIRMATION: true,
    QUALIFIED_PENDING_CONFIRMATION_EXTENDED: true,
    QUALIFIED_GROUP_EXTENDED: true
  };
  var DEGRADED_HEALTH_STATES = {
    UNAVAILABLE: true, STALE: true, ERROR: true, FAILED: true,
    DARK_OR_DISCONNECTED: true, BROKEN: true
  };
  var DISPLAY_FORBIDDEN = {
    schema: true, state: true, reason_code: true, reason_codes: true,
    source_records: true, clocks: true, watermarks: true, bar_status: true,
    authority: true, permissions: true, contract_version: true,
    display_state: true, rank: true, quality_score: true,
    confidence_pct: true, confidence_percentage: true, buyable: true,
    price_target: true, may_rank: true, may_gate: true, may_size: true,
    may_escalate: true, may_trade: true
  };
  var ENTRY_COPY = {
    QUALIFIED: ["Qualified individual setup", "合格的个股形态", "The current member gate and owner stock setup agree.", "当前成员门槛与所有者个股形态一致。", "up", "Open qualified setup", "打开合格形态"],
    QUALIFIED_PENDING_CONFIRMATION: ["Qualified; confirmation pending", "已合格；等待确认", "The setup is current, but the owner still marks confirmation pending.", "形态当前有效，但所有者仍标记为等待确认。", "info", "Open qualified setup", "打开合格形态"],
    QUALIFIED_PENDING_CONFIRMATION_EXTENDED: ["Qualified; confirmation pending, group extended", "已合格；等待确认，群组已延伸", "The individual setup is current; the parent group is extended, so do not treat the group as fresh entry permission.", "个股形态当前有效；母群组已延伸，不应把群组状态当作新的入场许可。", "warn", "Open qualified setup", "打开合格形态"],
    QUALIFIED_GROUP_EXTENDED: ["Qualified individual setup; group extended", "个股形态合格；群组已延伸", "The stock setup is qualified independently of the extended parent group.", "个股形态独立合格，母群组则已延伸。", "warn", "Open qualified setup", "打开合格形态"],
    QUALIFIED_GROUP_HEADWIND: ["Individual evidence present; group headwind", "个股证据存在；群组有逆风", "Review the setup, but do not present it as a qualified entry while the owner reports a group headwind.", "可查看该形态，但所有者报告群组逆风时不得将其展示为合格入场。", "warn", "Review setup and headwind", "查看形态与逆风"],
    EXPIRED: ["Setup expired", "形态已过期", "The owner no longer considers this a fresh entry.", "所有者不再将其视为新鲜入场。", "down", "View expired context", "查看已过期背景"],
    DESCRIPTIVE_ONLY_SETUP_STALE: ["Stock setup is stale", "个股形态已陈旧", "The record can be inspected, but it is not current entry permission.", "可以查看记录，但它不是当前入场许可。", "warn", "View stale context", "查看陈旧背景"],
    DESCRIPTIVE_ONLY_SETUP_UNAVAILABLE: ["No current stock setup record", "没有当前个股形态记录", "Absence is scoped to the named owner snapshot, not the whole market.", "缺失仅限于指定所有者快照，并非全市场缺失。", "unknown", "View instrument context", "查看标的背景"],
    DESCRIPTIVE_ONLY_MEMBER_INELIGIBLE: ["Member is not currently entry-eligible", "成员当前不具备入场资格", "Parent-group strength does not grant this member buyability.", "母群组强势不会赋予该成员可买性。", "neutral", "View instrument context", "查看标的背景"],
    DESCRIPTIVE_ONLY_SETUP_INELIGIBLE: ["Stock setup is not qualified", "个股形态未合格", "The owner setup record does not pass the current stock gate.", "所有者形态记录未通过当前个股门槛。", "neutral", "View instrument context", "查看标的背景"],
    DESCRIPTIVE_ONLY_PROXY: ["Proxy exposure only", "仅为代理敞口", "A proxy relationship cannot be presented as a direct qualified stock setup.", "代理关系不得展示为直接合格的个股形态。", "unknown", "View proxy context", "查看代理背景"],
    DESCRIPTIVE_ONLY_RELATIONSHIP_UNKNOWN: ["Relationship unresolved", "关系尚未解析", "The instrument relationship is unknown, so entry qualification is withheld.", "标的关系未知，因此不展示入场资格。", "unknown", "View instrument context", "查看标的背景"]
  };

  function own(obj, key) { return Object.prototype.hasOwnProperty.call(obj, key); }
  function clone(value) { return JSON.parse(JSON.stringify(value)); }
  function object(value, path) {
    if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(path + " must be a mapping");
    return value;
  }
  function text(parent, key, path) {
    if (!parent || typeof parent[key] !== "string" || !parent[key].trim()) throw new Error(path + " must be non-empty text");
    return parent[key];
  }
  function nullableText(parent, key, path) {
    if (!own(parent, key)) throw new Error(path + " must be explicitly present");
    if (parent[key] !== null && (typeof parent[key] !== "string" || !parent[key].trim())) throw new Error(path + " must be null or non-empty text");
    return parent[key];
  }
  function textList(value, path) {
    if (!Array.isArray(value) || value.some(function (item) { return typeof item !== "string" || !item.trim(); })) throw new Error(path + " must contain only non-empty text");
    return value.slice();
  }
  function evidenceRecords(value, path) {
    if (!Array.isArray(value)) throw new Error(path + " must be a list");
    return value.map(function (item, index) {
      var itemPath = path + "[" + index + "]";
      if (typeof item === "string") {
        if (!item.trim()) throw new Error(itemPath + " must be non-empty text");
        return { ref: item };
      }
      var record = object(item, itemPath);
      var keys = Object.keys(record);
      if (!keys.length) throw new Error(itemPath + " must not be empty");
      keys.forEach(function (key) {
        if (!EVIDENCE_KEYS[key]) throw new Error(itemPath + " has unsupported provenance field " + key);
        if (record[key] !== null && (typeof record[key] !== "string" || !record[key].trim())) {
          throw new Error(itemPath + "." + key + " must be null or non-empty text");
        }
      });
      if (!keys.some(function (key) { return record[key] !== null; })) {
        throw new Error(itemPath + " must carry at least one owner identity field");
      }
      return clone(record);
    });
  }
  function evidenceRecordLabel(record) {
    if (record.ref) return record.ref;
    if (record.artifact) return record.artifact;
    var ordered = [
      ["family", record.source_family || record.evidence_family],
      ["parent", record.parent_identity],
      ["session", record.observation_session],
      ["input", record.input_hash || record.source_input_hash],
      ["observation", record.observation_id],
      ["record", record.source_record_id]
    ];
    var label = ordered.filter(function (pair) { return !!pair[1]; })
      .map(function (pair) { return pair[0] + "=" + pair[1]; }).join(" · ");
    if (!label) throw new Error("provenance record has no displayable owner identity");
    return label;
  }
  function evidenceRecordLabels(records) {
    return records.map(evidenceRecordLabel);
  }
  function evidenceIdentity(value, path) {
    var identity = object(value, path);
    if (!sameKeys(identity, ["available", "reason_code", "records"])) {
      throw new Error(path + " must contain available, reason_code and records");
    }
    if (typeof identity.available !== "boolean") throw new Error(path + ".available must be true or false");
    if (identity.reason_code !== null && (typeof identity.reason_code !== "string" || !identity.reason_code.trim())) {
      throw new Error(path + ".reason_code must be null or non-empty text");
    }
    var records = evidenceRecords(identity.records, path + ".records");
    if (identity.available && !records.length) throw new Error(path + ".available cannot be true without owner records");
    return { available: identity.available, reason_code: identity.reason_code, records: records };
  }
  function dimensionClockMap(value, path) {
    var clocks = object(value, path);
    if (!sameKeys(clocks, CLOCKS)) throw new Error(path + " must keep observation/availability/computation/publication separate");
    var out = {};
    CLOCKS.forEach(function (key) {
      var raw = clocks[key], leaf;
      if (raw && typeof raw === "object" && !Array.isArray(raw)) {
        leaf = object(raw, path + "." + key);
        if (!sameKeys(leaf, ["value", "reason"])) throw new Error(path + "." + key + " must contain value and reason");
      } else {
        leaf = { value: raw, reason: null };
      }
      if (leaf.value !== null && (typeof leaf.value !== "string" || !leaf.value.trim())) {
        throw new Error(path + "." + key + ".value must be null or non-empty text");
      }
      if (leaf.reason !== null && (typeof leaf.reason !== "string" || !leaf.reason.trim())) {
        throw new Error(path + "." + key + ".reason must be null or non-empty text");
      }
      out[key] = { value: leaf.value, reason: leaf.reason };
    });
    return out;
  }
  function clockValues(details) {
    var out = {}; CLOCKS.forEach(function (key) { out[key] = details[key].value; }); return out;
  }
  function clockReasons(details) {
    var out = {}; CLOCKS.forEach(function (key) { out[key] = details[key].reason; }); return out;
  }
  function sameKeys(obj, expected) {
    var keys = Object.keys(obj).sort();
    var want = expected.slice().sort();
    return keys.length === want.length && keys.every(function (key, index) { return key === want[index]; });
  }
  function safeRoute(value, expected, pathLabel) {
    if (typeof value !== "string" || !value.trim()) throw new Error(pathLabel + " must be a non-empty safe relative route");
    var decoded;
    try { decoded = decodeURIComponent(value); } catch (error) { throw new Error(pathLabel + " must be a safe relative route"); }
    var lower = decoded.toLowerCase();
    if (decoded.charAt(0) === "/" || decoded.indexOf("\\") !== -1 || /^[a-z][a-z0-9+.-]*:/i.test(decoded) || lower.indexOf("javascript:") === 0 || lower.indexOf("data:") === 0 || /[\x00-\x1f]/.test(decoded)) throw new Error(pathLabel + " must be a safe relative route");
    var path = decoded.split(/[?#]/, 1)[0];
    if (path.split("/").some(function (part) { return part === ".."; })) throw new Error(pathLabel + " must be a safe relative route");
    if (expected && path !== expected) throw new Error(pathLabel + " must preserve " + expected);
    return value;
  }
  function validateAuthority(value, path, includeTrue) {
    var authority = object(value, path);
    var expected = FALSE_AUTH.slice();
    if (includeTrue) expected = expected.concat(TRUE_AUTH);
    if (!sameKeys(authority, expected)) throw new Error(path + " must use the complete closed authority field set");
    if (includeTrue) TRUE_AUTH.forEach(function (key) { if (authority[key] !== true) throw new Error(path + "." + key + " must remain true"); });
    FALSE_AUTH.forEach(function (key) { if (authority[key] !== false) throw new Error(path + "." + key + " must remain false"); });
    return authority;
  }
  function clockMap(value, path) {
    var clocks = object(value, path);
    if (!sameKeys(clocks, CLOCKS)) throw new Error(path + " must keep observation/availability/computation/publication separate");
    CLOCKS.forEach(function (key) {
      if (clocks[key] !== null && (typeof clocks[key] !== "string" || !clocks[key].trim())) throw new Error(path + "." + key + " must be null or non-empty text");
    });
    return clocks;
  }
  function barStatus(value, path) {
    var status = object(value, path);
    if (!sameKeys(status, ["closed", "provisional"])) throw new Error(path + " must contain closed and provisional");
    ["closed", "provisional"].forEach(function (key) { if (status[key] !== null && typeof status[key] !== "boolean") throw new Error(path + "." + key + " must be true, false, or null"); });
    return status;
  }
  function ownerDetails(dimension, path) {
    var out = {};
    ["label", "value", "band"].forEach(function (key) {
      if (!own(dimension, key)) return;
      var value = dimension[key];
      if (value !== null && typeof value === "object") throw new Error(path + "." + key + " must be a scalar or null");
      if ((key === "label" || key === "band") && value !== null && (typeof value !== "string" || !value.trim())) {
        throw new Error(path + "." + key + " must be null or non-empty text");
      }
      out[key] = clone(value);
    });
    return out;
  }
  function entryClockLeaf(value, path) {
    var leaf = object(value, path);
    if (!sameKeys(leaf, ["value", "reason"])) throw new Error(path + " must contain value and reason");
    if (leaf.value !== null && typeof leaf.value === "object") throw new Error(path + ".value must be a scalar or null");
    if (leaf.reason !== null && (typeof leaf.reason !== "string" || !leaf.reason.trim())) throw new Error(path + ".reason must be null or non-empty text");
    return clone(leaf);
  }
  function entryClocks(value, path) {
    var clocks = object(value, path);
    ["stock_setup", "group", "live_entry_radar"].forEach(function (owner) {
      if (!own(clocks, owner)) throw new Error(path + " is missing required owner clock sets: " + owner);
    });
    var out = {};
    Object.keys(clocks).forEach(function (owner) {
      if (!owner.trim()) throw new Error(path + " owner keys must be non-empty text");
      var set = object(clocks[owner], path + "." + owner);
      if (!sameKeys(set, CLOCKS)) throw new Error(path + "." + owner + " must keep observation/availability/computation/publication separate");
      out[owner] = {};
      CLOCKS.forEach(function (key) { out[owner][key] = entryClockLeaf(set[key], path + "." + owner + "." + key); });
    });
    return out;
  }
  function entryLineage(value, path) {
    var lineage = object(value, path);
    var expected = ["state", "source_revision", "correction_of", "supersedes", "source_content_sha256", "reason"];
    if (!sameKeys(lineage, expected)) throw new Error(path + " must use the exact Lane D lineage fields");
    text(lineage, "state", path + ".state");
    if (lineage.source_revision !== null && typeof lineage.source_revision === "object") throw new Error(path + ".source_revision must be a scalar or null");
    ["correction_of", "supersedes", "source_content_sha256", "reason"].forEach(function (key) {
      if (lineage[key] !== null && (typeof lineage[key] !== "string" || !lineage[key].trim())) throw new Error(path + "." + key + " must be null or non-empty text");
    });
    return clone(lineage);
  }
  function walkDisplay(value, path) {
    if (Array.isArray(value)) { value.forEach(function (item, index) { walkDisplay(item, path + "[" + index + "]"); }); return; }
    if (!value || typeof value !== "object") return;
    Object.keys(value).forEach(function (key) {
      if (DISPLAY_FORBIDDEN[key]) throw new Error(path + "." + key + " is owner-controlled, not presentation copy");
      walkDisplay(value[key], path + "." + key);
    });
  }
  function validateHealthCopy(ownerDims, displayDims) {
    var health = object(ownerDims.health, "theme_context.dimensions.health");
    var copy = object(displayDims.health, "display.dimensions.health");
    if (!DEGRADED_HEALTH_STATES[String(health.state || "").toUpperCase()]) return;
    if (["warn", "down", "unknown"].indexOf(copy.tone) === -1) {
      throw new Error("display.dimensions.health must visibly disclose degraded source health");
    }
    var prose = [copy.label_en, copy.label_zh, copy.reason_en, copy.reason_zh]
      .map(function (value) { return String(value || "").toLowerCase(); }).join(" ");
    if (/quiet|nothing notable|平静|暂无值得关注/.test(prose)) {
      throw new Error("source failure cannot be presented as quiet");
    }
  }
  function entrySetup(raw) {
    var entry = object(raw, "entry_context");
    if (entry.schema !== ENTRY_SCHEMA) throw new Error("entry_context.schema must be " + ENTRY_SCHEMA);
    if (entry.context_only !== true) throw new Error("entry_context.context_only must remain true");
    validateAuthority(entry.authority, "entry_context.authority", false);
    var permissions = object(entry.permissions, "entry_context.permissions");
    if (!sameKeys(permissions, ["may_describe", "may_link"].concat(FALSE_AUTH))) throw new Error("entry_context.permissions must use the complete closed field set");
    if (permissions.may_describe !== true || permissions.may_link !== true) throw new Error("entry_context may_describe and may_link must remain true");
    FALSE_AUTH.forEach(function (key) { if (permissions[key] !== false) throw new Error("entry_context.permissions." + key + " must remain false"); });
    var instrument = object(entry.instrument, "entry_context.instrument");
    var relationship = object(entry.relationship, "entry_context.relationship");
    var qualification = object(entry.qualification, "entry_context.qualification");
    var setup = object(entry.stock_setup, "entry_context.stock_setup");
    var expiry = object(entry.expiry, "entry_context.expiry");
    var routing = object(entry.routing, "entry_context.routing");
    var routes = object(entry.routes, "entry_context.routes");
    var group = object(entry.group_context, "entry_context.group_context");
    var confirmation = object(entry.confirmation, "entry_context.confirmation");
    var levels = object(entry.levels, "entry_context.levels");
    var instrumentId = text(instrument, "id", "entry_context.instrument.id");
    var href = safeRoute(routes.instrument, null, "entry_context.routes.instrument");
    var groupHref = safeRoute(routes.group, null, "entry_context.routes.group");
    var state = text(routing, "state", "entry_context.routing.state");
    ["may_navigate", "may_present_as_qualified_setup", "may_present_as_headwind_warning"].forEach(function (key) {
      if (typeof routing[key] !== "boolean") throw new Error("entry_context.routing." + key + " must be explicit true/false");
    });
    if (routing.rank_effect !== "NONE" || routing.size_effect !== "NONE") throw new Error("entry_context routing cannot affect rank or size");
    var qualified = routing.may_present_as_qualified_setup;
    var warning = routing.may_present_as_headwind_warning;
    if (qualified) {
      if (!QUALIFIED_STATES[state]) throw new Error("qualified entry uses an unsupported routing state");
      if (instrument.kind !== "DIRECT_INSTRUMENT") throw new Error("qualified entry requires DIRECT_INSTRUMENT");
      if (relationship.kind !== "DIRECT_MEMBER") throw new Error("qualified entry requires DIRECT_MEMBER");
      if (qualification.member_gate !== "QUALIFIED") throw new Error("qualified entry requires qualified member gate");
      if (qualification.stock_setup !== "QUALIFIED") throw new Error("qualified entry requires qualified stock setup");
      if (setup.availability !== "AVAILABLE") throw new Error("qualified entry requires available stock setup");
      if (expiry.state !== "ACTIVE") throw new Error("qualified entry requires active expiry state");
    }
    if (warning && state !== "QUALIFIED_GROUP_HEADWIND") throw new Error("headwind warning must use QUALIFIED_GROUP_HEADWIND");
    if (warning && qualified) throw new Error("headwind warning cannot be presented as a qualified setup");
    var copy = ENTRY_COPY[state] || ["Individual entry context", "个股入场背景", "The owner supplied entry context; inspect the exact routing state and receipt.", "所有者提供了入场背景；请查看精确路由状态与依据。", "unknown", "View instrument context", "查看标的背景"];
    return {
      instrument_id: instrumentId,
      instrument_kind: instrument.kind,
      relationship_kind: relationship.kind,
      group_id: relationship.group_id,
      group_label: relationship.group_label,
      routing_state: state,
      qualified: qualified,
      headwind_warning: warning,
      may_navigate: routing.may_navigate,
      href: routing.may_navigate ? href : null,
      group_href: routing.may_navigate ? groupHref : null,
      record_ref: setup.source_ref,
      record_id: setup.source_setup_id,
      label_en: copy[0], label_zh: copy[1], reason_en: copy[2], reason_zh: copy[3], tone: copy[4], cta_en: copy[5], cta_zh: copy[6],
      confirmation_state: confirmation.state,
      group_confirmation_state: confirmation.group_state,
      group_extended: !!group.extended,
      group_headwind: !!group.headwind,
      availability: setup.availability,
      expiry_state: expiry.state,
      levels: clone(levels),
      clocks: entryClocks(entry.clocks, "entry_context.clocks"),
      lineage: entryLineage(entry.lineage, "entry_context.lineage")
    };
  }
  function fromOwnerContext(raw) {
    var envelope = object(raw, "owner envelope");
    if (typeof envelope.fixture !== "boolean") throw new Error("fixture must be explicit true/false");
    var sourceRef = text(envelope, "theme_context_ref", "theme_context_ref");
    var owner = object(envelope.theme_context, "theme_context");
    if (owner.schema !== OWNER_SCHEMA) throw new Error("theme_context.schema must be " + OWNER_SCHEMA);
    validateAuthority(owner.authority, "theme_context.authority", true);
    var identity = object(owner.identity, "theme_context.identity");
    var themeId = text(identity, "theme_id", "theme_context.identity.theme_id");
    if (!/^[A-Za-z0-9_-]+$/.test(themeId)) throw new Error("theme_context.identity.theme_id contains unsafe characters");
    ["relationship_kind", "basket_id", "market", "horizon"].forEach(function (key) { nullableText(identity, key, "theme_context.identity." + key); });
    var ownerDims = object(owner.dimensions, "theme_context.dimensions");
    if (!sameKeys(ownerDims, AXES)) throw new Error("theme_context.dimensions must contain exactly the five Lane A dimensions");
    var topClocks = clockMap(owner.clocks, "theme_context.clocks");
    var topBar = barStatus(owner.bar_status, "theme_context.bar_status");
    var topSourceRecords = evidenceRecords(owner.source_records, "theme_context.source_records");
    var ownerEvidenceIdentity = own(owner, "evidence_identity")
      ? evidenceIdentity(owner.evidence_identity, "theme_context.evidence_identity")
      : { available: false, reason_code: null, records: [] };
    textList(owner.independent_evidence_families, "theme_context.independent_evidence_families");
    object(owner.specialist_context, "theme_context.specialist_context");
    object(owner.watermarks, "theme_context.watermarks");
    object(owner.correction_lineage, "theme_context.correction_lineage");

    var display = object(envelope.display, "display");
    walkDisplay(display, "display");
    var themeCopy = object(display.theme, "display.theme");
    text(themeCopy, "name_en", "display.theme.name_en");
    text(themeCopy, "name_zh", "display.theme.name_zh");
    var surface = object(display.surface, "display.surface");
    text(surface, "source_lens_en", "display.surface.source_lens_en");
    text(surface, "source_lens_zh", "display.surface.source_lens_zh");
    safeRoute(surface.current_route, null, "display.surface.current_route");
    var summary = object(display.summary, "display.summary");
    ["what_changed_en", "what_changed_zh", "why_matters_en", "why_matters_zh", "opportunity_en", "opportunity_zh", "risk_en", "risk_zh", "disagreement_en", "disagreement_zh"].forEach(function (key) { text(summary, key, "display.summary." + key); });
    var displayDims = object(display.dimensions, "display.dimensions");
    if (!sameKeys(displayDims, AXES)) throw new Error("display.dimensions must explain exactly the five owner dimensions");
    validateHealthCopy(ownerDims, displayDims);
    var axes = {};
    AXES.forEach(function (name) {
      var dimension = object(ownerDims[name], "theme_context.dimensions." + name);
      text(dimension, "state", "theme_context.dimensions." + name + ".state");
      var copy = object(displayDims[name], "display.dimensions." + name);
      ["label_en", "label_zh", "reason_en", "reason_zh"].forEach(function (key) { text(copy, key, "display.dimensions." + name + "." + key); });
      if (!TONES[copy.tone]) throw new Error("display.dimensions." + name + ".tone has unsupported presentation tone");
      var codes = Array.isArray(dimension.reason_codes) ? dimension.reason_codes.slice() : [];
      if (dimension.reason_code) codes.unshift(dimension.reason_code);
      codes = codes.filter(function (item, index) { return codes.indexOf(item) === index; });
      textList(codes, "theme_context.dimensions." + name + ".reason_codes");
      var records = evidenceRecords(dimension.source_records || [], "theme_context.dimensions." + name + ".source_records");
      var clockDetails = dimension.clocks
        ? dimensionClockMap(dimension.clocks, "theme_context.dimensions." + name + ".clocks")
        : dimensionClockMap(topClocks, "theme_context.clocks");
      axes[name] = {
        label_en: copy.label_en, label_zh: copy.label_zh,
        reason_en: copy.reason_en, reason_zh: copy.reason_zh,
        tone: copy.tone, state: dimension.state,
        owner_details: ownerDetails(dimension, "theme_context.dimensions." + name),
        reason_codes: codes,
        source_records: clone(records),
        source_refs: evidenceRecordLabels(records),
        clocks: clockValues(clockDetails),
        clock_reasons: clockReasons(clockDetails),
        watermarks: clone(dimension.watermarks || owner.watermarks),
        bar_status: clone(dimension.bar_status || topBar)
      };
    });
    var routes = object(display.routes, "display.routes");
    if (!sameKeys(routes, Object.keys(ROUTES))) throw new Error("display.routes must contain tracker, foresight, radar and sector");
    Object.keys(ROUTES).forEach(function (key) { safeRoute(routes[key], ROUTES[key], "display.routes." + key); });
    if (!Array.isArray(display.names)) throw new Error("display.names must be a list");
    var entries = Array.isArray(envelope.entry_contexts) ? envelope.entry_contexts.map(entrySetup) : [];
    return validate({
      fixture: envelope.fixture,
      source_contract: owner.schema,
      source_record_ref: sourceRef,
      theme: Object.assign({}, clone(identity), clone(themeCopy)),
      surface: clone(surface), summary: clone(summary), axes: axes,
      axis_order: AXES.slice(), axis_labels: clone(LABELS),
      specialist_context: clone(owner.specialist_context),
      names: clone(display.names), routes: clone(routes),
      entry_setups: entries,
      receipts: {
        source_records: evidenceRecordLabels(topSourceRecords),
        source_record_details: clone(topSourceRecords),
        evidence_identity: clone(ownerEvidenceIdentity),
        evidence_identity_refs: evidenceRecordLabels(ownerEvidenceIdentity.records),
        independent_evidence_families: clone(owner.independent_evidence_families),
        clocks: clone(topClocks), watermarks: clone(owner.watermarks),
        bar_status: clone(topBar), correction_lineage: clone(owner.correction_lineage)
      },
      authority: clone(owner.authority), component_version: COMPONENT_VERSION
    });
  }
  function validate(model) {
    object(model, "card");
    if (typeof model.fixture !== "boolean") throw new Error("fixture must be explicit true/false");
    if (model.source_contract !== OWNER_SCHEMA) throw new Error("source_contract must be " + OWNER_SCHEMA);
    text(model, "source_record_ref", "source_record_ref");
    var theme = object(model.theme, "theme");
    text(theme, "theme_id", "theme.theme_id"); text(theme, "name_en", "theme.name_en"); text(theme, "name_zh", "theme.name_zh");
    ["relationship_kind", "basket_id", "market", "horizon"].forEach(function (key) { nullableText(theme, key, "theme." + key); });
    var surface = object(model.surface, "surface");
    text(surface, "source_lens_en", "surface.source_lens_en");
    text(surface, "source_lens_zh", "surface.source_lens_zh");
    safeRoute(surface.current_route, null, "surface.current_route");
    var summary = object(model.summary, "summary");
    walkDisplay(summary, "summary");
    ["what_changed_en", "what_changed_zh", "why_matters_en", "why_matters_zh", "opportunity_en", "opportunity_zh", "risk_en", "risk_zh", "disagreement_en", "disagreement_zh"].forEach(function (key) {
      text(summary, key, "summary." + key);
    });
    var axes = object(model.axes, "axes");
    if (!sameKeys(axes, AXES)) throw new Error("axes must contain exactly the five Lane A dimensions");
    AXES.forEach(function (name) {
      var axis = object(axes[name], "axes." + name);
      text(axis, "state", "axes." + name + ".state");
      ["label_en", "label_zh", "reason_en", "reason_zh"].forEach(function (key) { text(axis, key, "axes." + name + "." + key); });
      if (!TONES[axis.tone]) throw new Error("axes." + name + ".tone has unsupported presentation tone");
      var details = object(axis.owner_details, "axes." + name + ".owner_details");
      if (Object.keys(details).some(function (key) { return ["label", "value", "band"].indexOf(key) === -1; })) throw new Error("axes." + name + ".owner_details has unsupported fields");
      ownerDetails(details, "axes." + name + ".owner_details");
      textList(axis.reason_codes, "axes." + name + ".reason_codes");
      evidenceRecords(axis.source_records, "axes." + name + ".source_records");
      textList(axis.source_refs, "axes." + name + ".source_refs");
      clockMap(axis.clocks, "axes." + name + ".clocks");
      var reasons = object(axis.clock_reasons, "axes." + name + ".clock_reasons");
      if (!sameKeys(reasons, CLOCKS)) throw new Error("axes." + name + ".clock_reasons must keep observation/availability/computation/publication separate");
      CLOCKS.forEach(function (clockName) {
        if (reasons[clockName] !== null && (typeof reasons[clockName] !== "string" || !reasons[clockName].trim())) {
          throw new Error("axes." + name + ".clock_reasons." + clockName + " must be null or non-empty text");
        }
      });
      object(axis.watermarks, "axes." + name + ".watermarks");
      barStatus(axis.bar_status, "axes." + name + ".bar_status");
    });
    if (!Array.isArray(model.entry_setups)) throw new Error("entry_setups must be a list");
    model.entry_setups.forEach(function (setup, index) {
      var path = "entry_setups[" + index + "]";
      object(setup, path);
      ["instrument_id", "instrument_kind", "relationship_kind", "routing_state", "label_en", "label_zh", "reason_en", "reason_zh", "tone", "cta_en", "cta_zh"].forEach(function (key) {
        text(setup, key, path + "." + key);
      });
      if (!TONES[setup.tone]) throw new Error(path + ".tone has unsupported presentation tone");
      ["qualified", "headwind_warning", "may_navigate", "group_extended", "group_headwind"].forEach(function (key) {
        if (typeof setup[key] !== "boolean") throw new Error(path + "." + key + " must be explicit true/false");
      });
      ["href", "group_href", "record_ref", "record_id"].forEach(function (key) {
        if (!own(setup, key)) throw new Error(path + "." + key + " must be explicit");
      });
      var expectedQualified = !!QUALIFIED_STATES[setup.routing_state];
      if (setup.qualified !== expectedQualified) throw new Error(path + " qualified flag must match the owner routing state");
      var expectedHeadwind = setup.routing_state === "QUALIFIED_GROUP_HEADWIND";
      if (setup.headwind_warning !== expectedHeadwind) throw new Error(path + " headwind warning must match the owner routing state");
      if (setup.qualified) {
        if (setup.instrument_kind !== "DIRECT_INSTRUMENT") throw new Error(path + " qualified setup requires DIRECT_INSTRUMENT");
        if (setup.relationship_kind !== "DIRECT_MEMBER") throw new Error(path + " qualified setup requires DIRECT_MEMBER");
        if (setup.availability !== "AVAILABLE") throw new Error(path + " qualified setup requires available owner data");
        if (setup.expiry_state !== "ACTIVE") throw new Error(path + " qualified setup requires active owner expiry");
      }
      if (setup.may_navigate) {
        safeRoute(setup.href, null, path + ".href");
        safeRoute(setup.group_href, null, path + ".group_href");
      } else if (setup.href !== null || setup.group_href !== null) {
        throw new Error("non-navigable setup cannot carry routes");
      }
      entryClocks(setup.clocks, path + ".clocks");
      entryLineage(setup.lineage, path + ".lineage");
    });
    if (!Array.isArray(model.names)) throw new Error("names must be a list");
    model.names.forEach(function (name, index) {
      var path = "names[" + index + "]";
      object(name, path);
      ["instrument_id", "symbol", "name_en", "name_zh", "relationship_kind", "membership_basis", "membership_as_of"].forEach(function (key) {
        text(name, key, path + "." + key);
      });
    });
    var receipts = object(model.receipts, "receipts");
    textList(receipts.source_records, "receipts.source_records");
    evidenceRecords(receipts.source_record_details, "receipts.source_record_details");
    evidenceIdentity(receipts.evidence_identity, "receipts.evidence_identity");
    textList(receipts.evidence_identity_refs, "receipts.evidence_identity_refs");
    textList(receipts.independent_evidence_families, "receipts.independent_evidence_families");
    clockMap(receipts.clocks, "receipts.clocks");
    var watermarks = object(receipts.watermarks, "receipts.watermarks");
    if (!own(watermarks, "snapshot") || !own(watermarks, "inputs")) throw new Error("receipts.watermarks must contain snapshot and inputs");
    if (watermarks.snapshot !== null && (typeof watermarks.snapshot !== "string" || !watermarks.snapshot.trim())) throw new Error("receipts.watermarks.snapshot must be text or null");
    var inputs = object(watermarks.inputs, "receipts.watermarks.inputs");
    Object.keys(inputs).forEach(function (key) {
      if (!key.trim()) throw new Error("receipts.watermarks.inputs keys must be text");
      if (inputs[key] !== null && (typeof inputs[key] !== "string" || !inputs[key].trim())) throw new Error("receipts.watermarks.inputs values must be text or null");
    });
    barStatus(receipts.bar_status, "receipts.bar_status");
    var lineage = object(receipts.correction_lineage, "receipts.correction_lineage");
    ["supersedes", "first_observed", "first_displayed"].forEach(function (key) {
      nullableText(lineage, key, "receipts.correction_lineage." + key);
    });
    var routes = object(model.routes, "routes");
    Object.keys(ROUTES).forEach(function (key) { safeRoute(routes[key], ROUTES[key], "routes." + key); });
    validateAuthority(model.authority, "authority", true);
    return model;
  }

  function esc(value) { return String(value == null ? "" : value).replace(/[&<>"']/g, function (c) { return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]; }); }
  function bi(en, zh) { return '<span class="l-en">' + esc(en) + '</span><span class="l-zh">' + esc(zh || en) + '</span>'; }
  function clock(label, value, reason) { return '<span class="toc-clock"><b>' + label + '</b> ' + esc(value || "—") + (reason ? '<small>' + esc(reason) + '</small>' : '') + '</span>'; }
  function bar(status) { return '<span class="toc-clock"><b>BAR</b> closed=' + esc(status.closed === null ? "—" : status.closed) + ' · provisional=' + esc(status.provisional === null ? "—" : status.provisional) + '</span>'; }
  function displayValue(value) {
    if (value === null || value === undefined) return "—";
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
  }
  function axis(name, value) {
    var receipts = (value.reason_codes || []).map(function (item) { return '<code>' + esc(item) + '</code>'; }).join("") + (value.source_refs || []).map(function (item) { return '<code>' + esc(item) + '</code>'; }).join("");
    var details = Object.keys(value.owner_details || {}).map(function (field) { return '<span class="toc-owner-detail" data-owner-field="' + esc(field) + '"><b>' + esc(field) + '</b> ' + esc(displayValue(value.owner_details[field])) + '</span>'; }).join("");
    return '<section class="toc-axis" data-axis="' + esc(name) + '" data-owner-state="' + esc(value.state) + '" data-tone="' + esc(value.tone) + '">' +
      '<div class="toc-axis-top"><span>' + bi(LABELS[name][0], LABELS[name][1]) + '</span><strong class="toc-owner-state">' + esc(value.state) + '</strong></div>' +
      (details ? '<div class="toc-owner-details">' + details + '</div>' : '') +
      '<p class="toc-axis-explanation"><strong>' + bi(value.label_en, value.label_zh) + '</strong> · ' + bi(value.reason_en, value.reason_zh) + '</p><div class="toc-receipt">' + receipts + '</div>' +
      '<div class="toc-clocks">' + clock("O", value.clocks.observation, value.clock_reasons.observation) + clock("A", value.clocks.availability, value.clock_reasons.availability) + clock("C", value.clocks.computation, value.clock_reasons.computation) + clock("P", value.clocks.publication, value.clock_reasons.publication) + bar(value.bar_status) + '</div></section>';
  }
  function setupClockHtml(clocks) {
    return Object.keys(clocks || {}).map(function (owner) {
      var set = clocks[owner];
      var cells = CLOCKS.map(function (name) {
        var leaf = set[name];
        return '<span><strong>' + esc(name) + '</strong> ' + esc(displayValue(leaf.value)) + (leaf.reason ? '<small>' + esc(leaf.reason) + '</small>' : '') + '</span>';
      }).join("");
      return '<div class="toc-setup-clock-row" data-clock-owner="' + esc(owner) + '"><b>' + esc(owner) + '</b>' + cells + '</div>';
    }).join("");
  }
  function setupLineageHtml(lineage) {
    return 'state=' + esc(displayValue(lineage.state)) + ' · source_revision=' + esc(displayValue(lineage.source_revision)) + ' · correction_of=' + esc(displayValue(lineage.correction_of)) + ' · supersedes=' + esc(displayValue(lineage.supersedes)) + ' · source_content_sha256=' + esc(displayValue(lineage.source_content_sha256)) + (lineage.reason ? ' · reason=' + esc(lineage.reason) : '');
  }
  function setupHtml(setup) {
    var links = setup.may_navigate ? '<div class="toc-setup-links"><a href="' + esc(setup.href) + '" data-entry-record-ref="' + esc(setup.record_ref || "") + '" data-entry-record-id="' + esc(setup.record_id || "") + '">' + bi(setup.cta_en, setup.cta_zh) + '</a><a href="' + esc(setup.group_href) + '">' + bi("Open group context", "打开群组背景") + '</a></div>' : '';
    var levels = setup.levels || {};
    return '<article class="toc-setup" data-routing-state="' + esc(setup.routing_state) + '" data-qualified="' + (setup.qualified ? 'true' : 'false') + '" data-headwind-warning="' + (setup.headwind_warning ? 'true' : 'false') + '" data-tone="' + esc(setup.tone) + '">' +
      '<div class="toc-setup-copy"><strong>' + esc(setup.instrument_id) + ' · ' + bi(setup.label_en, setup.label_zh) + '</strong><p>' + bi(setup.reason_en, setup.reason_zh) + '</p><small>' + esc(setup.relationship_kind) + ' · confirmation=' + esc(setup.confirmation_state || "—") + ' · extended=' + esc(setup.group_extended) + ' · headwind=' + esc(setup.group_headwind) + '</small></div>' + links +
      '<details class="toc-setup-detail"><summary>' + bi("Levels, clocks and receipt", "价位、时钟与依据") + '</summary><div class="toc-levels"><span>trigger=' + esc(levels.trigger == null ? "—" : levels.trigger) + '</span><span>zone=' + esc(levels.zone == null ? "—" : JSON.stringify(levels.zone)) + '</span><span>invalidation=' + esc(levels.invalidation == null ? "—" : levels.invalidation) + '</span><span>chase_above=' + esc(levels.chase_above == null ? "—" : levels.chase_above) + '</span></div><div class="toc-receipt"><code>' + esc(setup.record_ref || "—") + '</code>' + (setup.record_id ? '<code>' + esc(setup.record_id) + '</code>' : '') + '<code>' + esc(setup.routing_state) + '</code></div><div class="toc-setup-clocks">' + setupClockHtml(setup.clocks) + '</div><p class="toc-setup-lineage">' + setupLineageHtml(setup.lineage) + '</p></details></article>';
  }
  function render(model) {
    model = validate(model);
    var t = model.theme, s = model.summary, r = model.receipts;
    var fixture = model.fixture ? '<span class="toc-fixture">' + bi("Fixture — not live data", "样例——非实时数据") + '</span>' : '';
    var specialist = model.specialist_context || {};
    var names = (model.names || []).map(function (name) { return '<span class="toc-namechip" data-instrument-id="' + esc(name.instrument_id) + '" data-relationship-kind="' + esc(name.relationship_kind) + '" data-membership-basis="' + esc(name.membership_basis) + '" data-membership-as-of="' + esc(name.membership_as_of) + '"><strong>' + esc(name.symbol) + '</strong> ' + bi(name.name_en, name.name_zh) + '</span>'; }).join("") || '<span class="toc-null">' + bi("No owner-qualified names", "暂无所有者确认的标的") + '</span>';
    var setups = (model.entry_setups || []).map(setupHtml).join("") || '<p class="toc-null">' + bi("No owner-authorized individual setup records supplied.", "未提供所有者授权的个股形态记录。") + '</p>';
    var watermarkInputs = Object.keys((r.watermarks || {}).inputs || {}).map(function (key) { return '<span><b>' + esc(key) + '</b> ' + esc(r.watermarks.inputs[key] || "—") + '</span>'; }).join("");
    var receiptCodes = (r.source_records || []).map(function (ref) { return '<code>' + esc(ref) + '</code>'; }).join("") + (r.independent_evidence_families || []).map(function (family) { return '<code>family:' + esc(family) + '</code>'; }).join("");
    var evidenceIdentity = r.evidence_identity || { available: false, reason_code: null, records: [] };
    var evidenceIdentityText = bi("Evidence identity", "证据身份") + ': available=' + esc(evidenceIdentity.available) + ' · reason=' + esc(evidenceIdentity.reason_code || "—") + (r.evidence_identity_refs || []).map(function (ref) { return ' · ' + esc(ref); }).join("");
    var lineage = r.correction_lineage || {};
    return '<article class="toc-card" id="theme-' + esc(t.theme_id) + '" data-component-version="' + COMPONENT_VERSION + '" data-source-contract="' + esc(model.source_contract) + '" data-source-record-ref="' + esc(model.source_record_ref) + '" data-fixture="' + (model.fixture ? 'true' : 'false') + '">' +
      '<header class="toc-head"><div><p class="toc-eyebrow">' + bi(model.surface.source_lens_en, model.surface.source_lens_zh) + '</p><h3>' + bi(t.name_en, t.name_zh) + '</h3><p class="toc-meta">' + esc(t.market || "—") + ' · ' + esc(t.horizon || "—") + ' · ' + esc(t.relationship_kind || "—") + (t.basket_id ? ' · ' + esc(t.basket_id) : '') + '</p><div class="toc-specialist"><span>' + bi("Lane", "分组") + ': ' + esc(specialist.lane || "—") + '</span><span>' + bi("Stage", "阶段") + ': ' + esc(specialist.stage || "—") + '</span><span>' + bi("Divergence", "背离") + ': ' + esc(specialist.divergence || "—") + '</span></div></div>' + fixture + '</header>' +
      '<section class="toc-answer" aria-label="Decision summary"><div><b>' + bi("What changed", "发生了什么变化") + '</b><p>' + bi(s.what_changed_en, s.what_changed_zh) + '</p></div><div><b>' + bi("Why it matters", "为何重要") + '</b><p>' + bi(s.why_matters_en, s.why_matters_zh) + '</p></div><div><b>' + bi("Opportunity condition", "机会条件") + '</b><p>' + bi(s.opportunity_en, s.opportunity_zh) + '</p></div><div><b>' + bi("Risk / invalidation", "风险／失效条件") + '</b><p>' + bi(s.risk_en, s.risk_zh) + '</p></div><div class="toc-wide"><b>' + bi("Disagreement", "分歧") + '</b><p>' + bi(s.disagreement_en, s.disagreement_zh) + '</p></div></section>' +
      '<div class="toc-axes">' + AXES.map(function (name) { return axis(name, model.axes[name]); }).join("") + '</div>' +
      '<section class="toc-names"><b>' + bi("Subtheme and names", "子主题与标的") + '</b><div class="toc-name-list">' + names + '</div></section>' +
      '<section class="toc-setups" aria-label="Individual setups"><div class="toc-setups-head"><b>' + bi("Individual setups", "个股形态") + '</b><span>' + bi("Stock qualification is independent from the theme-level entry read.", "个股资格独立于主题层入场读数。") + '</span></div>' + setups + '</section>' +
      '<nav class="toc-routes" aria-label="Theme intelligence routes"><a href="' + esc(model.routes.tracker) + '">' + bi("Theme Tracker", "主题追踪") + '</a><a href="' + esc(model.routes.foresight) + '">' + bi("Foresight", "前瞻") + '</a><a href="' + esc(model.routes.radar) + '">' + bi("Divergence Radar", "背离雷达") + '</a><a href="' + esc(model.routes.sector) + '">' + bi("Sector Confluence", "行业汇聚") + '</a></nav>' +
      '<details class="toc-evidence"><summary>' + bi("Evidence, clocks and capability ceiling", "证据、时钟与能力上限") + '</summary><div class="toc-clocks">' + clock("O", r.clocks.observation) + clock("A", r.clocks.availability) + clock("C", r.clocks.computation) + clock("P", r.clocks.publication) + bar(r.bar_status) + '</div><div class="toc-watermarks"><b>' + bi("Snapshot", "快照") + '</b> ' + esc(r.watermarks.snapshot || "—") + watermarkInputs + '</div><div class="toc-receipt">' + receiptCodes + '</div><p class="toc-evidence-identity" data-evidence-identity-available="' + (evidenceIdentity.available ? 'true' : 'false') + '">' + evidenceIdentityText + '</p><p class="toc-lineage">' + bi("Correction lineage", "更正沿革") + ': supersedes=' + esc(lineage.supersedes || "—") + ' · first_observed=' + esc(lineage.first_observed || "—") + ' · first_displayed=' + esc(lineage.first_displayed || "—") + '</p><p class="toc-ceiling">context=on · display=on · signal=off · rank=off · gate=off · size=off · escalate=off · trade=off</p></details></article>';
  }
  function mount(root, model) { if (!root) throw new Error("mount root required"); root.innerHTML = render(model); return root.firstElementChild; }

  global.ThemeOpportunityCard = {
    version: COMPONENT_VERSION,
    fromOwnerContext: fromOwnerContext,
    validate: validate,
    render: render,
    mount: mount
  };
})(window);
