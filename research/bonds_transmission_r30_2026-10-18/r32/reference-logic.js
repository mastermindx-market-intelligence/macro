/* Deterministic R32 DESIGN REFERENCE. No network, service, alert, or persistence owner.
 * Eligibility flags and clocks are synthetic fixture inputs, not production qualification.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.MMXReferenceLogic = api;
})(typeof globalThis === 'object' ? globalThis : this, function () {
  'use strict';
  const finite = x => typeof x === 'number' && Number.isFinite(x);
  const clone = x => JSON.parse(JSON.stringify(x));
  const PEERS = Array.from({ length: 12 }, (_, i) => 'P' + String(i + 1).padStart(2, '0'));
  const CLOSED = new Set(['matched', 'invalidated', 'expired', 'window_closed']);
  function durationPrice(duration, convexity, shockBp) {
    if (![duration, convexity, shockBp].every(finite) || duration < 0 || convexity < 0) return null;
    const dy = shockBp / 10000;
    return 100 * (-duration * dy + 0.5 * convexity * dy * dy);
  }
  function scenario(x) {
    if (![x.policy, x.premium, x.spread].every(finite) || (x.rateBasis && x.rateBasis !== 'benchmark')) return null;
    const yieldBp = x.policy + x.premium;
    const rate = -5.5 * yieldBp / 100;
    const spread = -4.7 * x.spread / 100;
    return { yieldBp, rate, spread, corporate: rate + spread, treasury: durationPrice(7.8, 64, yieldBp) };
  }
  function keyRate(durations, shocksBp, compatible = true) {
    if (!compatible || !Array.isArray(durations) || !Array.isArray(shocksBp) || durations.length !== 4 || shocksBp.length !== 4 || !durations.every(finite) || !shocksBp.every(finite)) return null;
    const contributions = durations.map((d, i) => -d * shocksBp[i] / 100);
    return { contributions, total: contributions.reduce((a, b) => a + b, 0), method: 'first_order_only' };
  }
  function priorVolatility(closesIncludingCurrent) {
    if (!Array.isArray(closesIncludingCurrent) || closesIncludingCurrent.length < 22) return null;
    const prior = closesIncludingCurrent.slice(-22, -1);
    if (!prior.every(finite)) return null;
    const changes = prior.slice(1).map((v, i) => v - prior[i]);
    const mean = changes.reduce((a, b) => a + b, 0) / changes.length;
    const variance = changes.reduce((a, b) => a + (b - mean) ** 2, 0) / (changes.length - 1);
    return variance > 0 ? Math.sqrt(variance) : null;
  }
  function usable(input, cutoff) {
    if (!input || input.quality !== 'current' || input.eligible !== true) return false;
    const released = Date.parse(input.releasedAt), decision = Date.parse(cutoff);
    return Number.isFinite(released) && Number.isFinite(decision) && released <= decision;
  }
  function peerMean(peers, cutoff, cohort = PEERS) {
    if (!Array.isArray(peers) || peers.length !== cohort.length || !peers.every(x => x && typeof x === 'object') || new Set(peers.map(x => x.id)).size !== cohort.length) return null;
    if (!peers.every(x => cohort.includes(x.id) && finite(x.value) && usable(x, cutoff))) return null;
    return peers.reduce((a, p) => a + p.value, 0) / peers.length;
  }
  function evaluateFixture(observation, previous = null, rule = { confirm: 5.08, invalidate: 5.22, peerMean: 15 }) {
    if (previous && CLOSED.has(previous.state)) return clone(previous);
    const o = observation, cutoff = o.cutoff;
    if (![rule.confirm, rule.invalidate, rule.peerMean].every(finite) || rule.confirm <= 0 || rule.confirm >= rule.invalidate) return { state: 'data_paused', reason: 'Invalid authored rule', cutoff };
    if (!Number.isInteger(o.sessionNo) || o.sessionNo < 1) return { state: 'data_paused', reason: 'Invalid eligible-session clock', cutoff };
    const yOK = usable(o.yield, cutoff) && finite(o.yield.value);
    const fOK = usable(o.funding, cutoff) && ['orderly', 'stress'].includes(o.funding.value);
    if (o.sessionNo > 5) return { state: 'window_closed', reason: 'Evidence arrived after the five-close window', cutoff, sessionNo: o.sessionNo, rule: clone(rule) };
    if ((yOK && o.yield.value > rule.invalidate) || (fOK && o.funding.value === 'stress')) return { state: 'invalidated', reason: yOK && o.yield.value > rule.invalidate ? 'Fresh 10Y close above ' + rule.invalidate + '%' : 'Current funding stress', cutoff, sessionNo: o.sessionNo, rule: clone(rule) };
    const mean = peerMean(o.peers, cutoff);
    const predicates = {
      yield: !yOK ? 'unknown' : o.yield.value < rule.confirm ? 'met' : 'not_met',
      credit: mean === null ? 'unknown' : mean >= rule.peerMean ? 'met' : 'not_met',
      funding: !fOK ? 'unknown' : o.funding.value === 'orderly' ? 'met' : 'not_met'
    };
    if (Object.values(predicates).every(x => x === 'met')) return { state: 'matched', reason: 'Complete authored conjunction at the eligible close', cutoff, sessionNo: o.sessionNo, predicates, peerMean: mean, rule: clone(rule) };
    if (o.sessionNo === 5) return { state: 'expired', reason: 'Fifth eligible close evaluated; no complete match', cutoff, sessionNo: 5, predicates, peerMean: mean, rule: clone(rule) };
    return { state: Object.values(predicates).includes('unknown') ? 'data_paused' : 'waiting', reason: Object.values(predicates).includes('unknown') ? 'Critical input missing, stale, incompatible or not yet released' : 'One or more numeric conditions not met', cutoff, sessionNo: o.sessionNo, predicates, peerMean: mean, rule: clone(rule) };
  }
  function laterReview(event, observation) {
    const level = event.rule?.invalidate;
    const later = Date.parse(observation.cutoff) > Date.parse(event.cutoff);
    if (!later || !finite(level)) return { event: clone(event), interpretation: 'unresolved', mechanism: 'unresolved', reason: !later ? 'Review is not later than the event' : 'Original review level unavailable', reviewedAt: observation.cutoff };
    const eligibleYield = usable(observation.yield, observation.cutoff) && finite(observation.yield.value);
    const eligibleFunding = usable(observation.funding, observation.cutoff);
    const challenged = (eligibleYield && observation.yield.value > level) || (eligibleFunding && observation.funding.value === 'stress');
    return { event: clone(event), interpretation: challenged ? 'continuation_challenged' : 'unresolved', mechanism: 'unresolved', reviewedAt: observation.cutoff };
  }
  function correctionReview(event, correctedObservation) {
    return { originalEvent: clone(event), annotation: 'Corrected input received after original evaluation', revisedEvaluation: event.rule ? evaluateFixture(correctedObservation, null, event.rule) : {state:'data_paused',reason:'Original rule unavailable'}, originalRewritten: false, retrospectiveNotification: false };
  }
  function holdingReconciliation(row) {
    const fields = ['opening', 'closing', 'transactions', 'price_revaluation', 'fx', 'other'];
    if (!fields.every(k => finite(row[k]))) return null;
    return { change: row.closing - row.opening, transactions: row.transactions, residual: row.closing - row.opening - row.transactions - row.price_revaluation - row.fx - row.other, fundingOrigin: 'unresolved' };
  }
  function indicativeHedgedYield(yieldPct, annualCostPct, compatible = true) {
    return compatible && finite(yieldPct) && finite(annualCostPct) ? yieldPct - annualCostPct : null;
  }
  function issuerFunding(issueYieldPct, swapAdjustmentPct, sameBorrowerAndTenor = true) {
    return sameBorrowerAndTenor && finite(issueYieldPct) && finite(swapAdjustmentPct) ? issueYieldPct + swapAdjustmentPct : null;
  }
  function cashProjection({ opening = 2100, buffer = 300, draw = 'none', delayReceipt = false } = {}) {
    if (![opening, buffer].every(finite) || opening < 0 || buffer < 0 || !['none', 'before', 'late'].includes(draw)) return null;
    const events = [
      { time: '2026-10-16T09:00:00Z', label: 'Opening usable cash', amount: 0 },
      { time: '2026-11-02T09:00:00Z', label: 'Vendor payment', amount: -600 },
      { time: '2026-11-16T09:00:00Z', label: 'Debt interest', amount: -50 },
      { time: '2026-12-01T09:00:00Z', label: 'Assumed receipt', amount: delayReceipt ? 0 : 200 },
      { time: '2026-12-15T09:00:00Z', label: 'Amortization', amount: -850 },
      { time: '2026-12-16T09:00:00Z', label: 'Lease payment', amount: -90 },
      { time: '2027-01-14T09:00:00Z', label: 'Eligible draw before cutoff', amount: draw === 'before' ? 900 : 0 },
      { time: '2027-01-15T09:00:00Z', label: 'Maturity + other payments', amount: -900 }
    ];
    if (draw === 'late') events.push({ time: '2027-01-15T16:00:00Z', label: 'Late draw after payment cutoff', amount: 900 });
    let balance = opening;
    const rows = events.map(e => ({ ...e, balance: balance += e.amount }));
    const atCutoff = rows.find(e => e.time === '2027-01-15T09:00:00Z').balance;
    return { rows, ending: balance, atCutoff, paymentGap: Math.max(0, -atCutoff), bufferGap: Math.max(0, buffer - atCutoff), bufferHeadroom: balance - buffer, borrower: 'Synthetic Parent A', currency: 'USD', units: 'millions', actualLegalDefaultEstablished: false };
  }
  function compatibleAddition(context, item) {
    if (item.kind === 'cash' && item.borrower !== context.borrower) return { ok: false, reason: 'Different borrower' };
    if (item.instrument && item.instrument !== context.instrument) return { ok: false, reason: 'Different instrument' };
    if (item.horizon && item.horizon !== context.horizon) return { ok: false, reason: 'Different horizon' };
    return { ok: true };
  }
  function addItem(context, items, item) {
    const admission = compatibleAddition(context, item);
    if (!admission.ok) return { ...admission, items: clone(items) };
    return { ok: true, items: [...items.filter(x => x.key !== item.key), clone(item)] };
  }
  function distinctOrigins(evidence) {
    return { originCount: new Set(evidence.map(x => x.origin)).size, statisticalIndependence: 'not_established', probability: null };
  }
  function freezeReplay(view, cutoff) { return { view: clone(view), cutoff, recorded: true }; }
  function revealReplay(record) { return record && record.recorded ? { allowed: true, frozen: clone(record) } : { allowed: false, reason: 'Record the view first' }; }
  function makeObservation(values = {}) {
    const cutoff = values.cutoff === undefined ? '2026-10-19T21:00:00Z' : values.cutoff;
    const input = value => ({ value, quality: 'current', eligible: true, releasedAt: cutoff });
    return { cutoff, sessionNo: values.sessionNo === undefined ? 1 : values.sessionNo, yield: input(values.yield === undefined ? 5.10 : values.yield), funding: input(values.funding === undefined ? 'orderly' : values.funding), peers: values.peers === null ? null : (values.peers === undefined ? [25,30,35,40,45,-1,-2,-3,-4,-5,-6,-22] : values.peers).map((value, i) => ({ id: PEERS[i], ...input(value) })) };
  }
  return { finite, clone, PEERS, durationPrice, scenario, keyRate, priorVolatility, usable, peerMean, evaluateFixture, laterReview, correctionReview, holdingReconciliation, indicativeHedgedYield, issuerFunding, cashProjection, compatibleAddition, addItem, distinctOrigins, freezeReplay, revealReplay, makeObservation };
});
