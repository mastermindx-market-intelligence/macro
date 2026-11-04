/**
 * Intl library search. Dependency-free UMD.
 * Browser global: IntlLibrarySearch
 * CommonJS: module.exports
 *
 * searchIntlTools(catalogue, rawQuery, groupId=null, options={composing:false})
 * acceptIntlSearchReply(active, reply)
 */
(function (root, factory) {
  if (typeof exports === 'object' && typeof module !== 'undefined') {
    module.exports = factory();
  } else {
    root.IntlLibrarySearch = factory();
  }
})(
  typeof globalThis !== 'undefined' ? globalThis : typeof self !== 'undefined' ? self : this,
  function () {
    'use strict';

    var INVALID_QUERY = 'INVALID_QUERY';
    var INVALID_CATALOGUE = 'INVALID_CATALOGUE';
    var MAX_QUERY_SCALARS = 256;
    var MAX_SAFE_INTEGER = 9007199254740991;

    var IDENTITY_FIELDS = [
      'principal_partition',
      'catalogue_generation',
      'query_generation',
      'raw_query',
      'group_id'
    ];

    function fail(Type, code, message) {
      var err = new Type(message);
      err.code = code;
      throw err;
    }

    function hasOwn(obj, key) {
      return Object.prototype.hasOwnProperty.call(obj, key);
    }

    function ownDataDescriptor(obj, key) {
      if (!hasOwn(obj, key)) return null;
      var desc = Object.getOwnPropertyDescriptor(obj, key);
      if (!desc) return null;
      if (typeof desc.get !== 'undefined' || typeof desc.set !== 'undefined') return null;
      if (!hasOwn(desc, 'value')) return null;
      return desc;
    }

    function isPlainObject(value) {
      return value !== null && typeof value === 'object' && !isArray(value);
    }

    function isArray(value) {
      return Array.isArray(value);
    }

    function isNonNegativeSafeInteger(value) {
      return (
        typeof value === 'number' &&
        isFinite(value) &&
        Math.floor(value) === value &&
        value >= 0 &&
        value <= MAX_SAFE_INTEGER
      );
    }

    function isForbiddenControl(cp) {
      if (cp >= 0x09 && cp <= 0x0d) return false;
      if (cp <= 0x1f) return true;
      if (cp >= 0x7f && cp <= 0x9f) return true;
      return false;
    }

    /**
     * Shared query inspection. Does not truncate or mutate the input string.
     * rawQuery must be a string of <=256 Unicode scalars, without unpaired
     * surrogates, NUL, or non-whitespace controls. Space/tab/newline allowed.
     */
    function inspectQuery(rawQuery) {
      if (typeof rawQuery !== 'string') {
        return {
          ok: false,
          Type: TypeError,
          code: INVALID_QUERY,
          message: 'Query must be a string'
        };
      }
      var units = rawQuery.length;
      var scalars = 0;
      var i = 0;
      while (i < units) {
        var c = rawQuery.charCodeAt(i);
        var cp;
        if (c >= 0xd800 && c <= 0xdbff) {
          if (i + 1 >= units) {
            return {
              ok: false,
              Type: RangeError,
              code: INVALID_QUERY,
              message: 'Query contains unpaired surrogates'
            };
          }
          var low = rawQuery.charCodeAt(i + 1);
          if (low < 0xdc00 || low > 0xdfff) {
            return {
              ok: false,
              Type: RangeError,
              code: INVALID_QUERY,
              message: 'Query contains unpaired surrogates'
            };
          }
          cp = (c - 0xd800) * 0x400 + (low - 0xdc00) + 0x10000;
          i += 2;
        } else if (c >= 0xdc00 && c <= 0xdfff) {
          return {
            ok: false,
            Type: RangeError,
            code: INVALID_QUERY,
            message: 'Query contains unpaired surrogates'
          };
        } else {
          cp = c;
          i += 1;
        }
        if (isForbiddenControl(cp)) {
          return {
            ok: false,
            Type: RangeError,
            code: INVALID_QUERY,
            message: 'Query contains NUL or non-whitespace control characters'
          };
        }
        scalars += 1;
        if (scalars > MAX_QUERY_SCALARS) {
          return {
            ok: false,
            Type: RangeError,
            code: INVALID_QUERY,
            message: 'Query exceeds 256 Unicode scalars'
          };
        }
      }
      return { ok: true, value: rawQuery, scalars: scalars };
    }

    function assertQuery(rawQuery) {
      var inspected = inspectQuery(rawQuery);
      if (!inspected.ok) fail(inspected.Type, inspected.code, inspected.message);
      return inspected;
    }

    function queryIsValid(rawQuery) {
      return inspectQuery(rawQuery).ok;
    }

    function normalizeSearchText(text) {
      return String(text).normalize('NFKC').toLowerCase();
    }

    function trimQueryWhitespace(text) {
      return text.trim();
    }

    function splitQueryTerms(normalized) {
      var parts = normalized.split(/\s+/);
      var terms = [];
      var i;
      for (i = 0; i < parts.length; i++) {
        if (parts[i]) terms.push(parts[i]);
      }
      return terms;
    }

    function termsAppearIn(normalizedHaystack, terms) {
      var i;
      for (i = 0; i < terms.length; i++) {
        if (normalizedHaystack.indexOf(terms[i]) === -1) return false;
      }
      return true;
    }

    function anyHaystackHasTerm(haystacks, term) {
      var i;
      for (i = 0; i < haystacks.length; i++) {
        if (haystacks[i].indexOf(term) !== -1) return true;
      }
      return false;
    }

    function allTermsAppearAcross(haystacks, terms) {
      var i;
      for (i = 0; i < terms.length; i++) {
        if (!anyHaystackHasTerm(haystacks, terms[i])) return false;
      }
      return true;
    }

    function readOwnData(obj, key) {
      var desc = ownDataDescriptor(obj, key);
      if (!desc) return { present: false };
      return { present: true, value: desc.value };
    }

    function catalogueFailType(message) {
      fail(TypeError, INVALID_CATALOGUE, message);
    }

    function catalogueFailRange(message) {
      fail(RangeError, INVALID_CATALOGUE, message);
    }

    function readRequiredString(row, key, nonempty) {
      var got = readOwnData(row, key);
      if (!got.present) catalogueFailType('Catalogue row missing ' + key);
      if (typeof got.value !== 'string') catalogueFailType('Catalogue row ' + key + ' must be a string');
      if (nonempty && got.value.length === 0) {
        catalogueFailRange('Catalogue row ' + key + ' must be nonempty');
      }
      return got.value;
    }

    function readAliases(row) {
      var got = readOwnData(row, 'aliases');
      if (!got.present) catalogueFailType('Catalogue row missing aliases');
      if (!isArray(got.value)) catalogueFailType('Catalogue row aliases must be a string array');
      var aliases = got.value;
      var out = [];
      var i;
      for (i = 0; i < aliases.length; i++) {
        if (!hasOwn(aliases, i) || typeof aliases[i] !== 'string') {
          catalogueFailType('Catalogue row aliases must be a string array');
        }
        out.push(aliases[i]);
      }
      return out;
    }

    function readOrder(row) {
      var got = readOwnData(row, 'order');
      if (!got.present) catalogueFailType('Catalogue row missing order');
      if (typeof got.value !== 'number') catalogueFailType('Catalogue row order must be a number');
      if (!isNonNegativeSafeInteger(got.value)) {
        catalogueFailRange('Catalogue row order must be a nonnegative safe integer');
      }
      return got.value;
    }

    function validateAndProjectCatalogue(catalogue) {
      if (!isArray(catalogue)) {
        catalogueFailType('Catalogue must be an array');
      }
      var seenKeys = Object.create(null);
      var seenOrders = Object.create(null);
      var rows = [];
      var i;
      for (i = 0; i < catalogue.length; i++) {
        if (!hasOwn(catalogue, i)) {
          catalogueFailType('Catalogue is malformed');
        }
        var raw = catalogue[i];
        if (!isPlainObject(raw)) {
          catalogueFailType('Catalogue row must be an object');
        }
        var presentation_key = readRequiredString(raw, 'presentation_key', true);
        var group_id = readRequiredString(raw, 'group_id', true);
        var order = readOrder(raw);
        var label_en = readRequiredString(raw, 'label_en', false);
        var label_zh = readRequiredString(raw, 'label_zh', false);
        var question_en = readRequiredString(raw, 'question_en', false);
        var question_zh = readRequiredString(raw, 'question_zh', false);
        var aliases = readAliases(raw);
        if (label_en.length === 0 && label_zh.length === 0) {
          catalogueFailRange('Catalogue row must include at least one tool label');
        }
        var keyMark = '#' + presentation_key;
        if (seenKeys[keyMark]) {
          catalogueFailRange('Catalogue has duplicate presentation_key');
        }
        seenKeys[keyMark] = true;
        var orderMark = '#' + String(order);
        if (seenOrders[orderMark]) {
          catalogueFailRange('Catalogue has duplicate order');
        }
        seenOrders[orderMark] = true;

        var aliasNorm = [];
        var a;
        for (a = 0; a < aliases.length; a++) {
          aliasNorm.push(normalizeSearchText(aliases[a]));
        }
        rows.push({
          index: i,
          presentation_key: presentation_key,
          group_id: group_id,
          order: order,
          label_en: label_en,
          label_zh: label_zh,
          label_en_n: normalizeSearchText(label_en),
          label_zh_n: normalizeSearchText(label_zh),
          question_en_n: normalizeSearchText(question_en),
          question_zh_n: normalizeSearchText(question_zh),
          alias_n: aliasNorm
        });
      }
      return rows;
    }

    function haystacksOf(row) {
      var list = [row.label_en_n, row.label_zh_n, row.question_en_n, row.question_zh_n];
      var i;
      for (i = 0; i < row.alias_n.length; i++) list.push(row.alias_n[i]);
      return list;
    }

    function rankMatch(row, fullQueryNorm) {
      if (row.label_en.length > 0 && row.label_en_n === fullQueryNorm) return 0;
      if (row.label_zh.length > 0 && row.label_zh_n === fullQueryNorm) return 0;
      if (fullQueryNorm.length > 0 && row.label_en.length > 0 && row.label_en_n.indexOf(fullQueryNorm) === 0) {
        return 1;
      }
      if (fullQueryNorm.length > 0 && row.label_zh.length > 0 && row.label_zh_n.indexOf(fullQueryNorm) === 0) {
        return 1;
      }
      return 2;
    }

    function chooseMatchedLabel(row, fullQueryNorm, terms, emptyQuery) {
      if (emptyQuery) {
        return row.label_en.length > 0 ? row.label_en : row.label_zh;
      }
      if (row.label_en.length > 0 && row.label_en_n === fullQueryNorm) return row.label_en;
      if (row.label_zh.length > 0 && row.label_zh_n === fullQueryNorm) return row.label_zh;
      if (fullQueryNorm.length > 0 && row.label_en.length > 0 && row.label_en_n.indexOf(fullQueryNorm) === 0) {
        return row.label_en;
      }
      if (fullQueryNorm.length > 0 && row.label_zh.length > 0 && row.label_zh_n.indexOf(fullQueryNorm) === 0) {
        return row.label_zh;
      }
      if (row.label_en.length > 0 && termsAppearIn(row.label_en_n, terms)) return row.label_en;
      if (row.label_zh.length > 0 && termsAppearIn(row.label_zh_n, terms)) return row.label_zh;
      return row.label_en.length > 0 ? row.label_en : row.label_zh;
    }

    function toResult(row, fullQueryNorm, terms, emptyQuery) {
      return {
        presentation_key: row.presentation_key,
        matched_label: chooseMatchedLabel(row, fullQueryNorm, terms, emptyQuery),
        order: row.order
      };
    }

    function compareHits(a, b) {
      if (a.rank !== b.rank) return a.rank - b.rank;
      if (a.order !== b.order) return a.order - b.order;
      return a.index - b.index;
    }

    function searchIntlTools(catalogue, rawQuery, groupId, options) {
      if (typeof groupId === 'undefined') groupId = null;
      if (typeof options === 'undefined' || options === null) options = {};

      var rows = validateAndProjectCatalogue(catalogue);
      assertQuery(rawQuery);

      if (groupId !== null && typeof groupId !== 'string') {
        fail(TypeError, INVALID_QUERY, 'group_id must be null or a string');
      }

      var composing = false;
      if (typeof options === 'object' && options !== null && !isArray(options)) {
        composing = options.composing === true;
      }
      if (composing) return null;

      var normalizedAll = normalizeSearchText(rawQuery);
      var terms = splitQueryTerms(normalizedAll);
      var fullQueryNorm = trimQueryWhitespace(normalizedAll);
      var emptyQuery = terms.length === 0;
      var hits = [];
      var i;
      for (i = 0; i < rows.length; i++) {
        var row = rows[i];
        if (groupId !== null && row.group_id !== groupId) continue;
        if (!emptyQuery && !allTermsAppearAcross(haystacksOf(row), terms)) continue;
        hits.push({
          rank: emptyQuery ? 0 : rankMatch(row, fullQueryNorm),
          order: row.order,
          index: row.index,
          row: row
        });
      }
      hits.sort(compareHits);
      var out = [];
      for (i = 0; i < hits.length; i++) {
        out.push(toResult(hits[i].row, fullQueryNorm, terms, emptyQuery));
      }
      return out;
    }

    function identityOwnNames(obj) {
      var names = Object.getOwnPropertyNames(obj);
      if (typeof Object.getOwnPropertySymbols === 'function') {
        if (Object.getOwnPropertySymbols(obj).length > 0) return null;
      }
      if (names.length !== IDENTITY_FIELDS.length) return null;
      var i;
      for (i = 0; i < IDENTITY_FIELDS.length; i++) {
        if (names.indexOf(IDENTITY_FIELDS[i]) === -1) return null;
      }
      return names;
    }

    function readIdentity(obj) {
      if (!isPlainObject(obj)) return null;
      if (!identityOwnNames(obj)) return null;
      // Consume the own data descriptors themselves; do not invoke property
      // accessors or a second proxy get path after checking their descriptors.
      var values = {};
      var i;
      for (i = 0; i < IDENTITY_FIELDS.length; i++) {
        var descriptor = ownDataDescriptor(obj, IDENTITY_FIELDS[i]);
        if (!descriptor) return null;
        values[IDENTITY_FIELDS[i]] = descriptor.value;
      }
      var principal_partition = values.principal_partition;
      var catalogue_generation = values.catalogue_generation;
      var query_generation = values.query_generation;
      var raw_query = values.raw_query;
      var group_id = values.group_id;
      if (typeof principal_partition !== 'string' || principal_partition.length === 0) return null;
      if (typeof catalogue_generation !== 'string' || catalogue_generation.length === 0) return null;
      if (!isNonNegativeSafeInteger(query_generation)) return null;
      if (!queryIsValid(raw_query)) return null;
      if (!(group_id === null || (typeof group_id === 'string' && group_id.length > 0))) return null;
      return {
        principal_partition: principal_partition,
        catalogue_generation: catalogue_generation,
        query_generation: query_generation,
        raw_query: raw_query,
        group_id: group_id
      };
    }

    function acceptIntlSearchReply(active, reply) {
      try {
        var a = readIdentity(active);
        var b = readIdentity(reply);
        if (!a || !b) return false;
        return (
          a.principal_partition === b.principal_partition &&
          a.catalogue_generation === b.catalogue_generation &&
          a.query_generation === b.query_generation &&
          a.raw_query === b.raw_query &&
          a.group_id === b.group_id
        );
      } catch (_) {
        // Revoked or malformed proxies may throw during reflective inspection.
        // A reply that cannot prove its exact identity must never paint.
        return false;
      }
    }

    return {
      searchIntlTools: searchIntlTools,
      acceptIntlSearchReply: acceptIntlSearchReply
    };
  }
);
