(function (root, factory) {
  'use strict';
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.IntlWorkspaceState = factory();
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  var VIEWS = ['overview', 'compare', 'macro', 'risk', 'history', 'library'];
  var BASES = ['local', 'usd_unhedged'];
  var CONFIG_FIELDS = ['markets', 'horizons', 'bases', 'default_horizon', 'default_basis', 'source_reference', 'anchor_ids', 'library_group_ids'];
  var STATE_FIELDS = ['view', 'selected_market', 'compare_markets', 'horizon', 'currency_basis', 'return_basis', 'source_reference', 'expanded', 'library_group', 'baseline', 'return_stack'];
  var CONTEXT_FIELDS = ['view', 'selected_market', 'compare_markets', 'horizon', 'currency_basis', 'return_basis', 'source_reference', 'expanded', 'library_group'];
  var BASELINE_FIELDS = ['source_reference', 'currency_basis', 'horizon', 'selected_market', 'compare_markets'];
  var RETURN_FIELDS = ['context', 'anchor_id'];
  var QUERY_FIELDS = ['view', 'market', 'pins', 'horizon', 'basis', 'return_basis', 'group'];
  var MAX_SCALARS = 128;
  var MAX_SOURCE_SCALARS = 256;
  var MAX_PINS = 4;
  var MAX_RETURN_STACK = 8;
  var MAX_QUERY_UNITS = 2048;
  var MAX_QUERY_PAIRS = 16;

  function ValidationError(code, field) {
    this.code = code;
    this.field = field;
  }
  ValidationError.prototype = Object.create(Error.prototype, {
    constructor: { value: ValidationError, enumerable: false, writable: true, configurable: true },
    name: { value: 'ValidationError', enumerable: false, writable: true, configurable: true },
    message: { value: 'Validation failed', enumerable: false, writable: true, configurable: true },
  });

  function fail(code, field) {
    throw new ValidationError(code, field);
  }

  function isPlainObject(value) {
    if (typeof value !== 'object' || value === null || Array.isArray(value)) return false;
    var prototype = Object.getPrototypeOf(value);
    return prototype === Object.prototype || prototype === null;
  }

  function isNormalArray(value) {
    if (!Array.isArray(value)) return false;
    var prototype = Object.getPrototypeOf(value);
    return prototype === Array.prototype;
  }

  function checkNormalArray(value, code, field) {
    if (!isNormalArray(value)) return false;
    var descriptor = Object.getOwnPropertyDescriptor(value, 'length');
    if (!descriptor || !('value' in descriptor) || descriptor.get || descriptor.set) fail(code, field);
    var keys = Object.getOwnPropertyNames(value);
    if (keys.length !== value.length + 1) fail(code, field);
    for (var index = 0; index < value.length; index += 1) {
      if (!Object.prototype.hasOwnProperty.call(value, index)) fail(code, field);
      descriptor = Object.getOwnPropertyDescriptor(value, index);
      if (!descriptor || !('value' in descriptor) || descriptor.get || descriptor.set) fail(code, field);
    }
    if (Object.getOwnPropertySymbols(value).length !== 0) fail(code, field);
    return true;
  }

  function exactFields(value, expected, code) {
    var keys = Object.getOwnPropertyNames(value);
    if (keys.length !== expected.length) fail(code, code === 'INVALID_CONFIG' ? 'config' : code === 'INVALID_STATE' ? 'state' : 'action');
    for (var index = 0; index < expected.length; index += 1) {
      if (!Object.prototype.hasOwnProperty.call(value, expected[index])) fail(code, expected[index]);
      var descriptor = Object.getOwnPropertyDescriptor(value, expected[index]);
      if (!descriptor || !('value' in descriptor) || descriptor.get || descriptor.set) fail(code, expected[index]);
    }
    if (Object.getOwnPropertySymbols(value).length !== 0) fail(code, code === 'INVALID_ACTION' ? 'action' : code === 'INVALID_CONFIG' ? 'config' : 'state');
  }

  function isString(value) {
    return typeof value === 'string';
  }

  function validScalars(value, limit, field, code) {
    if (!isString(value)) fail(code, field);
    if (value.length === 0) fail(code, field);
    var iterator = value[Symbol.iterator]();
    var count = 0;
    var next = iterator.next();
    while (!next.done) {
      var token = next.value;
      var unit = token.codePointAt(0);
      if (token.length > 2 || unit >= 0xd800 && unit <= 0xdfff) fail(code, field);
      if (unit <= 0x1f || unit === 0x7f || unit >= 0x80 && unit <= 0x9f) fail(code, field);
      count += 1;
      if (count > limit) fail(code, field);
      next = iterator.next();
    }
    return value;
  }

  function validateMembers(value, permitted, field) {
    if (!checkNormalArray(value, 'INVALID_CONFIG', field)) fail('INVALID_CONFIG', field);
    var seen = new Set();
    for (var index = 0; index < value.length; index += 1) {
      var member = validScalars(value[index], MAX_SCALARS, field, 'INVALID_CONFIG');
      if (seen.has(member) || (field === 'markets' && member.indexOf(',') !== -1)) fail('INVALID_CONFIG', field);
      if (permitted && permitted.indexOf(member) === -1) fail('INVALID_CONFIG', field);
      seen.add(member);
    }
  }

  function validateConfig(config) {
    if (!isPlainObject(config)) fail('INVALID_CONFIG', 'config');
    exactFields(config, CONFIG_FIELDS, 'INVALID_CONFIG');
    if (!checkNormalArray(config.markets, 'INVALID_CONFIG', 'markets') || config.markets.length === 0) fail('INVALID_CONFIG', 'markets');
    validateMembers(config.markets, null, 'markets');
    validateMembers(config.horizons, null, 'horizons');
    validateMembers(config.bases, BASES, 'bases');
    validScalars(config.default_horizon, MAX_SCALARS, 'default_horizon', 'INVALID_CONFIG');
    validScalars(config.default_basis, MAX_SCALARS, 'default_basis', 'INVALID_CONFIG');
    if (config.horizons.indexOf(config.default_horizon) === -1) fail('INVALID_CONFIG', 'default_horizon');
    if (config.bases.indexOf(config.default_basis) === -1) fail('INVALID_CONFIG', 'default_basis');
    if (config.source_reference !== null) validScalars(config.source_reference, MAX_SOURCE_SCALARS, 'source_reference', 'INVALID_CONFIG');
    if (!checkNormalArray(config.anchor_ids, 'INVALID_CONFIG', 'anchor_ids')) fail('INVALID_CONFIG', 'anchor_ids');
    if (!checkNormalArray(config.library_group_ids, 'INVALID_CONFIG', 'library_group_ids')) fail('INVALID_CONFIG', 'library_group_ids');
    validateMembers(config.anchor_ids, null, 'anchor_ids');
    validateMembers(config.library_group_ids, null, 'library_group_ids');
    return {
      markets: config.markets.slice(),
      horizons: config.horizons.slice(),
      bases: config.bases.slice(),
      default_horizon: config.default_horizon,
      default_basis: config.default_basis,
      source_reference: config.source_reference,
      anchor_ids: config.anchor_ids.slice(),
      library_group_ids: config.library_group_ids.slice()
    };
  }

  function oneOf(value, choices, field, code) {
    if (!isString(value) || choices.indexOf(value) === -1) fail(code || 'INVALID_STATE', field);
    return value;
  }

  function optionalId(value, choices, field, code, nullable) {
    if (nullable && value === null) return value;
    if (value === null) fail(code, field);
    validScalars(value, MAX_SCALARS, field, code);
    if (choices.indexOf(value) === -1) fail(code, field);
    return value;
  }

  function optionalSource(value, field, code) {
    if (value === null) return value;
    validScalars(value, MAX_SOURCE_SCALARS, field, code);
    return value;
  }

  function uniquePins(value, privateConfig, field, code) {
    code = code || 'INVALID_STATE';
    if (!checkNormalArray(value, code, field)) fail(code, field);
    if (value.length > MAX_PINS) fail(code, field);
    for (var index = 0; index < value.length; index += 1) {
      if (value[index] === null) fail(code, field);
      optionalId(value[index], privateConfig.markets, field, code, false);
      for (var prior = 0; prior < index; prior += 1) {
        if (value[prior] === value[index]) fail(code, field);
      }
    }
    return value;
  }

  function validateContext(context, privateConfig, expectedSource) {
    if (!isPlainObject(context)) fail('INVALID_STATE', 'return_stack');
    exactFields(context, CONTEXT_FIELDS, 'INVALID_STATE');
    oneOf(context.view, VIEWS, 'return_stack');
    optionalId(context.selected_market, privateConfig.markets, 'return_stack', 'INVALID_STATE', true);
    uniquePins(context.compare_markets, privateConfig, 'return_stack');
    oneOf(context.horizon, privateConfig.horizons, 'return_stack');
    oneOf(context.currency_basis, privateConfig.bases, 'return_stack');
    if (context.return_basis !== 'price') fail('INVALID_STATE', 'return_stack');
    optionalSource(context.source_reference, 'return_stack', 'INVALID_STATE');
    if (typeof context.expanded !== 'boolean') fail('INVALID_STATE', 'return_stack');
    optionalId(context.library_group, privateConfig.library_group_ids, 'return_stack', 'INVALID_STATE', true);
    if (context.source_reference !== expectedSource) fail('INVALID_STATE', 'return_stack');
  }

  function validateState(state, privateConfig) {
    if (!isPlainObject(state)) fail('INVALID_STATE', 'state');
    exactFields(state, STATE_FIELDS, 'INVALID_STATE');
    oneOf(state.view, VIEWS, 'view');
    optionalId(state.selected_market, privateConfig.markets, 'selected_market', 'INVALID_STATE', true);
    uniquePins(state.compare_markets, privateConfig, 'compare_markets');
    oneOf(state.horizon, privateConfig.horizons, 'horizon');
    oneOf(state.currency_basis, privateConfig.bases, 'currency_basis');
    if (state.return_basis !== 'price') fail('INVALID_STATE', 'return_basis');
    var currentSource = optionalSource(state.source_reference, 'source_reference', 'INVALID_STATE');
    if (typeof state.expanded !== 'boolean') fail('INVALID_STATE', 'expanded');
    optionalId(state.library_group, privateConfig.library_group_ids, 'library_group', 'INVALID_STATE', true);
    if (state.baseline !== null) {
      var baseline = state.baseline;
      if (!isPlainObject(baseline)) fail('INVALID_STATE', 'baseline');
      exactFields(baseline, BASELINE_FIELDS, 'INVALID_STATE');
      if (baseline.source_reference !== currentSource) fail('INVALID_STATE', 'baseline');
      if (baseline.source_reference === null) fail('INVALID_STATE', 'baseline');
      oneOf(baseline.currency_basis, privateConfig.bases, 'baseline');
      oneOf(baseline.horizon, privateConfig.horizons, 'baseline');
      optionalId(baseline.selected_market, privateConfig.markets, 'baseline', 'INVALID_STATE', true);
      uniquePins(baseline.compare_markets, privateConfig, 'baseline');
      if (baseline.currency_basis !== state.currency_basis || baseline.horizon !== state.horizon || baseline.selected_market !== state.selected_market || baseline.compare_markets.length !== state.compare_markets.length) fail('INVALID_STATE', 'baseline');
      for (var index = 0; index < baseline.compare_markets.length; index += 1) {
        if (baseline.compare_markets[index] !== state.compare_markets[index]) fail('INVALID_STATE', 'baseline');
      }
    }
    if (!checkNormalArray(state.return_stack, 'INVALID_STATE', 'return_stack')) fail('INVALID_STATE', 'return_stack');
    if (state.return_stack.length > MAX_RETURN_STACK) fail('INVALID_STATE', 'return_stack');
    for (var stackIndex = 0; stackIndex < state.return_stack.length; stackIndex += 1) {
      var entry = state.return_stack[stackIndex];
      if (!isPlainObject(entry)) fail('INVALID_STATE', 'return_stack');
      exactFields(entry, RETURN_FIELDS, 'INVALID_STATE');
      validateContext(entry.context, privateConfig, currentSource);
      optionalId(entry.anchor_id, privateConfig.anchor_ids, 'return_stack', 'INVALID_STATE', true);
    }
    return currentSource;
  }

  function copyState(state) {
    return {
      view: state.view,
      selected_market: state.selected_market,
      compare_markets: state.compare_markets.slice(),
      horizon: state.horizon,
      currency_basis: state.currency_basis,
      return_basis: state.return_basis,
      source_reference: state.source_reference,
      expanded: state.expanded,
      library_group: state.library_group,
      baseline: state.baseline === null ? null : {
        source_reference: state.baseline.source_reference,
        currency_basis: state.baseline.currency_basis,
        horizon: state.baseline.horizon,
        selected_market: state.baseline.selected_market,
        compare_markets: state.baseline.compare_markets.slice()
      },
      return_stack: state.return_stack.map(function (entry) {
        var context = {};
        for (var index = 0; index < CONTEXT_FIELDS.length; index += 1) context[CONTEXT_FIELDS[index]] = entry.context[CONTEXT_FIELDS[index]];
        context.compare_markets = entry.context.compare_markets.slice();
        return { context: context, anchor_id: entry.anchor_id };
      })
    };
  }

  function issue(code, field) {
    return { code: code, field: field };
  }

  function actionFields(type) {
    switch (type) {
      case 'set_view': return ['view'];
      case 'select_market': return ['market_id'];
      case 'set_horizon': return ['horizon'];
      case 'set_basis': return ['currency_basis'];
      case 'pin': return ['market_id'];
      case 'unpin': return ['market_id'];
      case 'set_expanded': return ['expanded'];
      case 'set_library_group': return ['group_id'];
      case 'push_return': return ['anchor_id'];
      case 'replace_source': return ['source_reference'];
      case 'capture_baseline': return [];
      case 'back': return [];
      case 'resize': return [];
      default: return null;
    }
  }

  function initialStateFor(privateConfig) {
    return {
      view: 'overview',
      selected_market: null,
      compare_markets: [],
      horizon: privateConfig.default_horizon,
      currency_basis: privateConfig.default_basis,
      return_basis: 'price',
      source_reference: privateConfig.source_reference,
      expanded: false,
      library_group: null,
      baseline: null,
      return_stack: []
    };
  }

  function tupleOf(state) {
    return [state.source_reference, state.currency_basis, state.horizon, state.selected_market, state.compare_markets];
  }

  function sameTuple(left, right) {
    return left[0] === right[0] && left[1] === right[1] && left[2] === right[2] && left[3] === right[3] && left[4].length === right[4].length && left[4].every(function (value, index) {
      return value === right[4][index];
    });
  }

  function createIntlWorkspaceState(config) {
    var privateConfig;
    try {
      privateConfig = validateConfig(config);
    } catch (error) {
      if (!(error instanceof ValidationError)) throw error;
      var publicError = new TypeError('Invalid International workspace configuration');
      publicError.code = 'INVALID_CONFIG';
      publicError.field = error.field;
      throw publicError;
    }
    var api = {
      initialState: initialStateFor(privateConfig),
      reduce: function (state, action) {
        var currentSource;
        try {
          currentSource = validateState(state, privateConfig);
        } catch (error) {
          if (!(error instanceof ValidationError)) throw error;
          return { ok: false, state: null, issues: [issue(error.code, error.field)], intent: null };
        }
        try {
          if (!isPlainObject(action)) fail('INVALID_ACTION', 'action');
          if (!Object.prototype.hasOwnProperty.call(action, 'type')) fail('INVALID_ACTION', 'type');
          var typeDescriptor = Object.getOwnPropertyDescriptor(action, 'type');
          if (!typeDescriptor || !('value' in typeDescriptor) || typeDescriptor.get || typeDescriptor.set) fail('INVALID_ACTION', 'type');
          if (!isString(action.type)) fail('INVALID_ACTION', 'type');
          var type = action.type;
          var expectedActionFields = actionFields(type);
          if (expectedActionFields === null) return { ok: false, state: state, issues: [issue('UNKNOWN_ACTION', 'type')], intent: null };
          exactFields(action, ['type'].concat(expectedActionFields), 'INVALID_ACTION');
          var next;
          next = copyState(state);
          switch (type) {
            case 'set_view':
              next.view = oneOf(action.view, VIEWS, 'view', 'UNSUPPORTED_VALUE');
              break;
            case 'select_market':
              next.selected_market = optionalId(action.market_id, privateConfig.markets, 'market_id', 'UNSUPPORTED_VALUE', true);
              break;
            case 'set_horizon':
              next.horizon = oneOf(action.horizon, privateConfig.horizons, 'horizon', 'UNSUPPORTED_VALUE');
              break;
            case 'set_basis':
              next.currency_basis = oneOf(action.currency_basis, privateConfig.bases, 'currency_basis', 'UNSUPPORTED_VALUE');
              break;
            case 'pin': {
              var pin = optionalId(action.market_id, privateConfig.markets, 'market_id', 'UNSUPPORTED_VALUE', false);
              if (next.compare_markets.indexOf(pin) === -1) {
                if (next.compare_markets.length >= MAX_PINS) fail('PIN_LIMIT', 'market_id');
                next.compare_markets.push(pin);
              }
              break;
            }
            case 'unpin': {
              var unpinned = optionalId(action.market_id, privateConfig.markets, 'market_id', 'UNSUPPORTED_VALUE', false);
              var pinIndex = next.compare_markets.indexOf(unpinned);
              if (pinIndex !== -1) next.compare_markets.splice(pinIndex, 1);
              break;
            }
            case 'set_expanded':
              if (typeof action.expanded !== 'boolean') fail('INVALID_ACTION', 'expanded');
              next.expanded = action.expanded;
              break;
            case 'set_library_group':
              next.library_group = optionalId(action.group_id, privateConfig.library_group_ids, 'group_id', 'UNSUPPORTED_VALUE', true);
              break;
            case 'capture_baseline':
              next.baseline = next.source_reference === null ? null : {
                source_reference: next.source_reference,
                currency_basis: next.currency_basis,
                horizon: next.horizon,
                selected_market: next.selected_market,
                compare_markets: next.compare_markets.slice()
              };
              break;
            case 'push_return': {
              optionalId(action.anchor_id, privateConfig.anchor_ids, 'anchor_id', 'UNSUPPORTED_VALUE', true);
              if (next.return_stack.length >= MAX_RETURN_STACK) fail('RETURN_STACK_LIMIT', 'return_stack');
              var context = {};
              for (var contextIndex = 0; contextIndex < CONTEXT_FIELDS.length; contextIndex += 1) context[CONTEXT_FIELDS[contextIndex]] = next[CONTEXT_FIELDS[contextIndex]];
              context.compare_markets = next.compare_markets.slice();
              next.return_stack.push({ context: context, anchor_id: action.anchor_id });
              break;
            }
            case 'back': {
              if (next.return_stack.length === 0) break;
              var restored = next.return_stack[next.return_stack.length - 1].context;
              next.view = restored.view;
              next.selected_market = restored.selected_market;
              next.compare_markets = restored.compare_markets.slice();
              next.horizon = restored.horizon;
              next.currency_basis = restored.currency_basis;
              next.return_basis = restored.return_basis;
              next.source_reference = restored.source_reference;
              next.expanded = restored.expanded;
              next.library_group = restored.library_group;
              next.return_stack.pop();
              break;
            }
            case 'replace_source': {
              var replacement = optionalSource(action.source_reference, 'source_reference', 'INVALID_ACTION');
              if (replacement === state.source_reference) return { ok: true, state: next, issues: [], intent: null };
              next.source_reference = replacement;
              next.baseline = null;
              next.return_stack = [];
              break;
            }
          }

          if (type === 'select_market' || type === 'set_horizon' || type === 'set_basis' || type === 'pin' || type === 'unpin' || type === 'back' || type === 'replace_source') {
            if (!sameTuple(tupleOf(next), tupleOf(state))) next.baseline = null;
          }
          if (type === 'back' && next.return_stack.length < state.return_stack.length) {
            return { ok: true, state: next, issues: [], intent: { type: 'restore_focus', anchor_id: state.return_stack[state.return_stack.length - 1].anchor_id } };
          }
          if (type === 'replace_source' && next.source_reference !== state.source_reference) {
            return { ok: true, state: next, issues: [], intent: { type: 'invalidate_source_bound_context' } };
          }
          return { ok: true, state: next, issues: [], intent: null };
        } catch (error) {
          if (error instanceof ValidationError) return { ok: false, state: state, issues: [issue(error.code, error.field)], intent: null };
          throw error;
        }
      },
      parseQuery: function (rawQuery) {
        var initial = initialStateFor(privateConfig);
        try {
          if (!isString(rawQuery)) fail('INVALID_QUERY', 'query');
          if (rawQuery.length > MAX_QUERY_UNITS) fail('QUERY_TOO_LONG', 'query');
          if (rawQuery.indexOf('#') !== -1) fail('INVALID_QUERY', 'query');
          var query = rawQuery.charAt(0) === '?' ? rawQuery.slice(1) : rawQuery;
          var pairs = query === '' ? [] : query.split('&');
          if (pairs.length > MAX_QUERY_PAIRS) fail('INVALID_QUERY', 'query');
          var values = {};
          for (var index = 0; index < pairs.length; index += 1) {
            var separator = pairs[index].indexOf('=');
            if (separator === -1) fail('INVALID_QUERY', 'query');
            var encodedKey = pairs[index].slice(0, separator);
            var encodedValue = pairs[index].slice(separator + 1);
            var decodedKey = decodeQueryPart(encodedKey);
            if (QUERY_FIELDS.indexOf(decodedKey) === -1) fail('INVALID_QUERY', decodedKey);
            if (Object.prototype.hasOwnProperty.call(values, decodedKey)) fail('INVALID_QUERY', decodedKey);
            if (decodedKey === 'pins') {
              if (encodedValue === '') {
                values.pins = [];
              } else {
                var encodedPins = encodedValue.split(',');
                if (encodedPins.length > MAX_PINS) fail('INVALID_QUERY', 'pins');
                values.pins = encodedPins.map(function (pin) {
                  var decodedPin = decodeQueryPart(pin);
                  if (decodedPin.indexOf(',') !== -1) fail('INVALID_QUERY', 'pins');
                  return decodedPin;
                });
              }
            } else {
              values[decodedKey] = decodeQueryPart(encodedValue);
            }
          }
          var decoded = {view: 'overview', market: '', pins: [], horizon: privateConfig.default_horizon,
            basis: privateConfig.default_basis, return_basis: 'price', group: ''};
          for (var fieldIndex = 0; fieldIndex < QUERY_FIELDS.length; fieldIndex += 1) {
            var field = QUERY_FIELDS[fieldIndex];
            if (Object.prototype.hasOwnProperty.call(values, field)) decoded[field] = values[field];
          }
          decoded.view = decoded.view === '' ? invalid('view') : oneOf(decoded.view, VIEWS, 'view', 'UNSUPPORTED_VALUE');
          decoded.market = decoded.market === '' ? null : optionalId(decoded.market, privateConfig.markets, 'market', 'UNSUPPORTED_VALUE');
          if (!checkNormalArray(decoded.pins, 'INVALID_QUERY', 'pins')) fail('INVALID_QUERY', 'pins');
          if (decoded.pins.length > MAX_PINS) fail('INVALID_QUERY', 'pins');
          for (var pinIndex = 0; pinIndex < decoded.pins.length; pinIndex += 1) {
            if (decoded.pins[pinIndex] === '') fail('INVALID_QUERY', 'pins');
            optionalId(decoded.pins[pinIndex], privateConfig.markets, 'pins', 'UNSUPPORTED_VALUE', false);
            for (var previous = 0; previous < pinIndex; previous += 1) {
              if (decoded.pins[previous] === decoded.pins[pinIndex]) fail('INVALID_QUERY', 'pins');
            }
          }
          decoded.horizon = decoded.horizon === '' ? invalid('horizon') : oneOf(decoded.horizon, privateConfig.horizons, 'horizon', 'UNSUPPORTED_VALUE');
          decoded.basis = decoded.basis === '' ? invalid('basis') : oneOf(decoded.basis, privateConfig.bases, 'basis', 'UNSUPPORTED_VALUE');
          decoded.return_basis = decoded.return_basis === '' ? invalid('return_basis') : decoded.return_basis === 'price' ? 'price' : fail('UNSUPPORTED_VALUE', 'return_basis');
          decoded.group = decoded.group === '' ? null : optionalId(decoded.group, privateConfig.library_group_ids, 'group', 'UNSUPPORTED_VALUE');
          return {
            ok: true,
            state: {
              view: decoded.view,
              selected_market: decoded.market,
              compare_markets: decoded.pins,
              horizon: decoded.horizon,
              currency_basis: decoded.basis,
              return_basis: decoded.return_basis,
              source_reference: privateConfig.source_reference,
              expanded: false,
              library_group: decoded.group,
              baseline: null,
              return_stack: []
            },
            issues: [],
            intent: null
          };
        } catch (error) {
          if (!(error instanceof ValidationError)) return { ok: false, state: initialStateFor(privateConfig), issues: [issue('INVALID_QUERY', 'query')], intent: null };
          return { ok: false, state: initialStateFor(privateConfig), issues: [issue(error.code, error.field)], intent: null };
        }
      },
      serializeQuery: function (state) {
        try {
          validateState(state, privateConfig);
          var query = 'view=' + encodeURIComponent(state.view) + '&market=' + (state.selected_market === null ? '' : encodeURIComponent(state.selected_market)) + '&pins=' + state.compare_markets.map(encodeURIComponent).join(',') + '&horizon=' + encodeURIComponent(state.horizon) + '&basis=' + encodeURIComponent(state.currency_basis) + '&return_basis=' + encodeURIComponent(state.return_basis) + '&group=' + (state.library_group === null ? '' : encodeURIComponent(state.library_group));
          if (query.length > MAX_QUERY_UNITS) fail('QUERY_TOO_LONG', 'query');
          return { ok: true, query: query, issues: [] };
        } catch (error) {
          if (!(error instanceof ValidationError)) throw error;
          return { ok: false, query: null, issues: [issue(error.code, error.field)] };
        }
      }
    };
    return api;
  }

  function invalid(field) {
    fail('INVALID_QUERY', field);
  }

  function decodeQueryPart(value) {
    var spaced = value.replace(/\+/g, ' ');
    var decoded;
    try {
      decoded = decodeURIComponent(spaced);
    } catch (error) {
      fail('INVALID_QUERY', 'query');
    }
    for (var index = 0; index < decoded.length; index += 1) {
      var unit = decoded.charCodeAt(index);
      if (unit <= 0x1f || unit === 0x7f || unit >= 0x80 && unit <= 0x9f) fail('INVALID_QUERY', 'query');
    }
    var iterator = decoded[Symbol.iterator]();
    var next = iterator.next();
    while (!next.done) {
      var code = next.value.codePointAt(0);
          if (next.value.length > 2 || code >= 0xd800 && code <= 0xdfff) fail('INVALID_QUERY', 'query');
      next = iterator.next();
    }
    return decoded;
  }

  return { createIntlWorkspaceState: createIntlWorkspaceState };
});
