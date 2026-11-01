/* The original planned-integration decoder was reused from mastermind-terminal@98b9e664a0a3387a72f7bf360f5159235c1d8eb6, terminal/lib/companyIntelligencePrivate.ts. The SEC supplier projection is a Macro extension of the native company-intelligence contract. Owner admission remains server-side. */
/**
 * Company Intelligence private projection decoder - pure and browser-safe.
 *
 * This module performs no I/O, imports nothing server-only, and never calls fetch. It
 * only decides whether a value that the private server helper has already bounded and
 * parsed matches the original planned-integration contract at 0de7a9ca (private wire v2)
 * or the separately qualified SEC disclosed-supplier contract
 * (engine/company_intelligence/issuer_disclosures.py, issuer_disclosure_selection.py,
 * app/company_disclosures.py).
 *
 * Two things this decoder deliberately does not claim:
 *   1. A reference (schema/SHA-256/byte length) inside a projection is discovery
 *      metadata, never a permission token. Format equality grants nothing.
 *   2. The context decoder hashes the included identity receipt only. It does not
 *      retrieve or qualify its referenced artifacts, identities or disclosure rights.
 *
 * Every refusal throws PrivateDecodeError carrying one fixed reason label declared in
 * this file. A rejected object's contents are never copied into the error, because a
 * value that failed its contract may still carry fields the caller has no right to
 * read back.
 */

export const PRIVATE_ISSUER_SELECTIONS_SCHEMA = 'company_intelligence.private_issuer_selections/v1';
export const PRIVATE_COMPANY_CONTEXT_SCHEMA = 'company_intelligence.private_company_context/v1';
export const PRIVATE_IDENTITY_RECEIPT_SCHEMA = 'company_intelligence.current_issuer_identity/v1';
export const PRIVATE_PRODUCT_INTEGRATION_SCHEMA = 'company_intelligence.private_product_integration/v2';
export const PRIVATE_SUPPLIER_SCHEMA = 'company_intelligence.private_disclosed_supplier/v1';
export const PRIVATE_SUPPLIER_RESEARCH_SCHEMA = 'company_intelligence.private_supplier_research/v1';
export const PRIVATE_SUPPLIER_FACT_SCHEMA = 'company_intelligence.disclosed_supplier_fact/v1';
export const PRIVATE_SEC_EDITION_SCHEMA = 'company_intelligence.sec_disclosure_edition/v1';
export const PRIVATE_ERROR_SCHEMA = 'company_intelligence.private_error/v1';
export const PRIVATE_FACT_SCHEMA = 'company_intelligence.product_integration_fact/v1';
export const PRIVATE_EDITION_SCHEMA = 'company_intelligence.issuer_disclosure_edition/v1';
export const PRIVATE_KIND = 'product_integration';
export const PRIVATE_LIFECYCLE = 'planned';
export const PRIVATE_IDENTITY_MODE = 'current';
export const PRIVATE_ISSUER_ROLE = 'subject_disclosing_company';
export const PRIVATE_AUTHORITY = 'context_only';

/** Bounds copied from the supplied native source. */
export const PRIVATE_MAX_SELECTIONS = 16;
export const PRIVATE_MAX_OBJECT_BYTES = 16 * 1024;
export const PRIVATE_MAX_REVISION = 64;
export const PRIVATE_MAX_IDENTIFIER_LENGTH = 256;
export const PRIVATE_MAX_SCOPE_BYTES = 256;
export const PRIVATE_ISSUER_MAX_LENGTH = 128;
export const PRIVATE_FACT_ID_PREFIX = 'integration:';
export const PRIVATE_ISSUER_PREFIX = 'ISS:';

/**
 * The granted field subset of a native fact. Only fact_id/kind/lifecycle are
 * mandatory; every optional native field may be absent, and an absent magnitude field
 * is never required to be present or null.
 */

/**
 * Closed source-announcement timing copied from the verified referenced edition.
 * Original wire strings are preserved verbatim: no JS Date parsing, no locale or UTC
 * normalization of a rendered publication date, and no synthesized midnight when
 * publication_precision is 'date'. known_at is the edition's observed knowledge
 * instant — never a publication date and never a sign that the plan is current.
 */

/** Closed machine codes the mounted private transport can emit, with their status. */

/** Bounded refusal: the message is a fixed label, never data from the rejected value. */
export class PrivateDecodeError extends Error {
           reason                     ;

  constructor(reason                     ) {
    super('company_intelligence_private_' + reason);
    this.name = 'PrivateDecodeError';
    this.reason = reason;
  }
}

const LOWER_HEX_64 = /^[0-9a-f]{64}$/;
const DIGITS_10 = /^[0-9]{10}$/;
const ALL_ZEROS = /^0+$/;
const ASCII_LETTER_OR_DIGIT = /^[A-Za-z0-9]$/;
const IDENTIFIER_CHARACTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.:/-';
const ASCII_TWO_LETTERS = /^[A-Za-z]{2}$/;
const MIC_SHAPE = /^[A-Za-z0-9]{4}$/;
const LISTING_CODE = /^[A-Za-z0-9][A-Za-z0-9.-]*$/;
const LISTING_KEY_PARTS = /^([^-]*)-([^-]*)-(.*)$/;
const DIGITS_ONLY = /^[0-9]+$/;
const TIMING_DATE = /^([0-9]{4})-([0-9]{2})-([0-9]{2})$/;
/** Offset designator is mandatory, exactly as the native _INSTANT pattern. */
const TIMING_INSTANT = /^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\.([0-9]{1,6}))?(Z|[+-][0-9]{2}:[0-9]{2})$/;
/** Closed as BigInt() calls so the literal target of the terminal tsconfig is irrelevant. */
const MICROSECONDS_PER_DAY = BigInt('86400000000');
/** Inclusive: 0001-01-01T00:00:00Z. */
const MIN_EPOCH_UTC_MICROSECONDS = BigInt('-62135596800000000');
/** Exclusive: 10000-01-01T00:00:00Z, so 9999-12-31T23:59:59.999999Z is the last legal UTC instant. */
const MAX_EPOCH_UTC_MICROSECONDS = BigInt('253402300800000000');

/**
 * The MIC set is closed on purpose in lib/dataos/identity.py; the issuer id shape a
 * canonical Data OS issuer can carry is bounded here exactly as far as that supplied
 * source establishes. This is input validation only: it asserts no identity binding,
 * mints nothing, and never turns a well-formed string into a permission.
 */
const KNOWN_MICS = ['BATS', 'XNYS', 'XNAS', 'XASE', 'ARCX', 'XSHG', 'XSHE', 'XBSE', 'XHKG', 'XTSE', 'XTSX'];

const FACT_MANDATORY_KEYS = ['fact_id', 'kind', 'lifecycle']         ;
const FACT_OPTIONAL_KEYS = ['revision', 'subject_id', 'object_id', 'product', 'platform', 'amount', 'economic_share']         ;

function isPlainObject(value         )                                   {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function closedObject(value         , closedKeys                   )                          {
  if (!isPlainObject(value)) throw new PrivateDecodeError('OBJECT');
  const keys = Object.keys(value);
  if (keys.length !== closedKeys.length) throw new PrivateDecodeError('KEYSET');
  for (const key of keys) {
    if (!closedKeys.includes(key)) throw new PrivateDecodeError('KEYSET');
  }
  return value;
}

function subsetObject(value         , mandatory                   , optional                   )                          {
  if (!isPlainObject(value)) throw new PrivateDecodeError('OBJECT');
  const allowed = mandatory.concat(optional);
  const keys = Object.keys(value);
  if (keys.length > allowed.length) throw new PrivateDecodeError('KEYSET');
  for (const key of keys) {
    if (!allowed.includes(key)) throw new PrivateDecodeError('KEYSET');
  }
  for (const key of mandatory) {
    if (!keys.includes(key)) throw new PrivateDecodeError('KEYSET');
  }
  return value;
}

function nativeIdentifier(value         )         {
  if (typeof value !== 'string') throw new PrivateDecodeError('IDENTIFIER');
  if (value.length < 1 || value.length > PRIVATE_MAX_IDENTIFIER_LENGTH) throw new PrivateDecodeError('IDENTIFIER');
  if (!ASCII_LETTER_OR_DIGIT.test(value.charAt(0))) throw new PrivateDecodeError('IDENTIFIER');
  for (const character of value) {
    if (!IDENTIFIER_CHARACTERS.includes(character)) throw new PrivateDecodeError('IDENTIFIER');
  }
  return value;
}

function nativeDigest(value         )         {
  if (typeof value !== 'string' || !LOWER_HEX_64.test(value)) throw new PrivateDecodeError('DIGEST');
  return value;
}

function boundedInteger(value         , minimum        , maximum        )         {
  if (typeof value !== 'number' || !Number.isSafeInteger(value)) throw new PrivateDecodeError('INTEGER');
  if (value < minimum || value > maximum) throw new PrivateDecodeError('INTEGER');
  return value;
}

function evidencedCik(value         )         {
  if (typeof value !== 'string' || !DIGITS_10.test(value)) throw new PrivateDecodeError('CIK');
  if (ALL_ZEROS.test(value)) throw new PrivateDecodeError('CIK');
  return value;
}

/**
 * Source-authoritative Gregorian civil semantics over exact integers. The native side
 * validates through datetime.fromisoformat, which tolerates noncanonical offset
 * minutes, so this consumer guesses no stricter minute range and bounds only what the
 * source establishes: a real local datetime, a total offset strictly inside ±24 hours,
 * and a UTC datetime inside years 0001..9999. (Verified against the native semantics:
 * '…-13:45' parses, '+24:00' raises, second==60 raises, and an offset that pushes UTC
 * outside 0001..9999 raises.)
 */
function isGregorianLeap(year        )          {
  return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
}

function daysInGregorianMonth(year        , month        )         {
  if (month === 2) return isGregorianLeap(year) ? 29 : 28;
  return month === 4 || month === 6 || month === 9 || month === 11 ? 30 : 31;
}

/** Days since 1970-01-01 for a known-valid civil date (Hinnant days_from_civil). */
function civilDateToDays(year        , month        , day        )         {
  const shifted = month <= 2 ? year - 1 : year;
  const era = Math.floor(shifted / 400);
  const yearOfEra = shifted - era * 400;
  const dayOfYear = Math.floor((153 * (month + (month > 2 ? -3 : 9)) + 2) / 5) + day - 1;
  const dayOfEra = yearOfEra * 365 + Math.floor(yearOfEra / 4) - Math.floor(yearOfEra / 100) + dayOfYear;
  return era * 146097 + dayOfEra - 719468;
}

function eraStartDayOfEra(yearOfEra        )         {
  return yearOfEra * 365 + Math.floor(yearOfEra / 4) - Math.floor(yearOfEra / 100);
}

/** Inverse of civilDateToDays; the clamp is the 399→0 era rollover boundary. */
function civilFromDays(days        )                                               {
  const shifted = days + 719468;
  const era = Math.floor(shifted / 146097);
  const dayOfEra = shifted - era * 146097;
  let yearOfEra = Math.floor((dayOfEra - Math.floor(dayOfEra / 4) + Math.floor(dayOfEra / 146) - Math.floor(dayOfEra / 146096)) / 365);
  while (eraStartDayOfEra(yearOfEra) > dayOfEra) yearOfEra -= 1;
  while (yearOfEra < 399 && eraStartDayOfEra(yearOfEra + 1) <= dayOfEra) yearOfEra += 1;
  const year = yearOfEra + era * 400;
  const dayOfYear = dayOfEra - eraStartDayOfEra(yearOfEra);
  const monthPrime = Math.floor((5 * dayOfYear + 2) / 153);
  const day = dayOfYear - Math.floor((153 * monthPrime + 2) / 5) + 1;
  const month = monthPrime + (monthPrime < 10 ? 3 : -9);
  return { year: month <= 2 ? year + 1 : year, month, day };
}

/** Null unless the string is an exact real YYYY-MM-DD inside Gregorian 0001..9999. */
function timingDateParts(value        )                                                      {
  const match = TIMING_DATE.exec(value);
  if (match === null) return null;
  const year = Number.parseInt(match[1], 10);
  const month = Number.parseInt(match[2], 10);
  const day = Number.parseInt(match[3], 10);
  if (year < 1 || year > 9999 || month < 1 || month > 12) return null;
  if (day < 1 || day > daysInGregorianMonth(year, month)) return null;
  return { year, month, day };
}

/**
 * Exact whole-epoch-microsecond UTC instant for a shape-checked string, or null. No
 * float milliseconds and no Date: ordering is decided to the microsecond with BigInt,
 * and the original string stays the only rendered value.
 */
function timingInstantToEpochMicroseconds(value        )                {
  const match = TIMING_INSTANT.exec(value);
  if (match === null) return null;
  const date = timingDateParts(value.slice(0, 10));
  if (date === null) return null;
  const hour = Number.parseInt(match[4], 10);
  const minute = Number.parseInt(match[5], 10);
  const second = Number.parseInt(match[6], 10);
  if (hour > 23 || minute > 59 || second > 59) return null;
  const fraction = match[7];
  const microsecond = fraction === undefined ? 0 : Number.parseInt(fraction.padEnd(6, '0'), 10);
  let offsetSeconds = 0;
  const designator = match[8];
  if (designator !== 'Z') {
    const offsetHours = Number.parseInt(designator.slice(1, 3), 10);
    const offsetMinutes = Number.parseInt(designator.slice(4, 6), 10);
    if (offsetHours * 60 + offsetMinutes >= 24 * 60) return null;
    offsetSeconds = (designator.charAt(0) === '-' ? -1 : 1) * (offsetHours * 3600 + offsetMinutes * 60);
  }
  const local = BigInt(civilDateToDays(date.year, date.month, date.day)) * MICROSECONDS_PER_DAY
    + BigInt(hour * 3600000000 + minute * 60000000) + BigInt(second * 1000000 + microsecond);
  const utc = local - BigInt(offsetSeconds) * BigInt('1000000');
  if (utc < MIN_EPOCH_UTC_MICROSECONDS || utc >= MAX_EPOCH_UTC_MICROSECONDS) return null;
  return utc;
}

/** UTC calendar date of an exact epoch-microsecond instant (floor division, not truncation). */
function utcDateFromEpochMicroseconds(microseconds        )         {
  let days = microseconds / MICROSECONDS_PER_DAY;
  if (microseconds % MICROSECONDS_PER_DAY !== BigInt('0') && microseconds < BigInt('0')) days -= BigInt('1');
  const civil = civilFromDays(Number(days));
  return String(civil.year).padStart(4, '0') + '-' + String(civil.month).padStart(2, '0') + '-' + String(civil.day).padStart(2, '0');
}

/**
 * Strict closed source_timing decoder. Every refusal is the one fixed label TIMING;
 * no rejected value, field, or native cause is ever copied into the error.
 */
function decodeSourceTiming(value         )                      {
  let timing                         ;
  try {
    timing = closedObject(value, ['published_date', 'published_at', 'publication_precision', 'known_at']);
  } catch (error) {
    if (error instanceof PrivateDecodeError) throw new PrivateDecodeError('TIMING');
    throw error;
  }
  if (typeof timing.published_date !== 'string' || timingDateParts(timing.published_date) === null) throw new PrivateDecodeError('TIMING');
  if (typeof timing.known_at !== 'string') throw new PrivateDecodeError('TIMING');
  const knownMicroseconds = timingInstantToEpochMicroseconds(timing.known_at);
  if (knownMicroseconds === null) throw new PrivateDecodeError('TIMING');
  const precision = timing.publication_precision;
  if (precision !== 'date' && precision !== 'instant') throw new PrivateDecodeError('TIMING');
  if (precision === 'date') {
    // Date-only announcements must not be upgraded to an invented instant, and the
    // announcement may not sit after the edition's observed knowledge day in UTC.
    if (timing.published_at !== null) throw new PrivateDecodeError('TIMING');
    if (timing.published_date > utcDateFromEpochMicroseconds(knownMicroseconds)) throw new PrivateDecodeError('TIMING');
    return Object.freeze({
      published_date: timing.published_date,
      published_at: null,
      publication_precision: 'date',
      known_at: timing.known_at,
    });
  }
  if (typeof timing.published_at !== 'string') throw new PrivateDecodeError('TIMING');
  const publishedMicroseconds = timingInstantToEpochMicroseconds(timing.published_at);
  if (publishedMicroseconds === null) throw new PrivateDecodeError('TIMING');
  // The syntax-checked instant string's leading ten characters ARE its offset-local
  // calendar date; comparing strings is what keeps the original offset intact.
  if (timing.published_at.slice(0, 10) !== timing.published_date) throw new PrivateDecodeError('TIMING');
  if (publishedMicroseconds > knownMicroseconds) throw new PrivateDecodeError('TIMING');
  return Object.freeze({
    published_date: timing.published_date,
    published_at: timing.published_at,
    publication_precision: 'instant',
    known_at: timing.known_at,
  });
}

function utf8ByteLength(value        )         {
  return new TextEncoder().encode(value).length;
}

/** Native fact scope text: non-empty, at most 256 characters and 256 UTF-8 bytes, untrimmed rejected. */
function nativeScopeText(value         )         {
  if (typeof value !== 'string') throw new PrivateDecodeError('TEXT');
  if (value.length < 1) throw new PrivateDecodeError('TEXT');
  if (value !== value.trim()) throw new PrivateDecodeError('TEXT');
  // TextEncoder replaces lone surrogates; native UTF-8 encoding rejects them.
  for (const character of value) {
    const codePoint = character.codePointAt(0) ?? 0;
    if (codePoint >= 0xd800 && codePoint <= 0xdfff) throw new PrivateDecodeError('TEXT');
  }
  if (Array.from(value).length > PRIVATE_MAX_SCOPE_BYTES) throw new PrivateDecodeError('TEXT');
  if (utf8ByteLength(value) > PRIVATE_MAX_SCOPE_BYTES) throw new PrivateDecodeError('TEXT');
  return value;
}

function nativeFactId(value         )         {
  const identifier = nativeIdentifier(value);
  if (!identifier.startsWith(PRIVATE_FACT_ID_PREFIX)) throw new PrivateDecodeError('VALUE');
  if (!LOWER_HEX_64.test(identifier.slice(PRIVATE_FACT_ID_PREFIX.length))) throw new PrivateDecodeError('VALUE');
  return identifier;
}

function canonicalIssuerIdentifier(value         )         {
  if (typeof value !== 'string') throw new PrivateDecodeError('IDENTIFIER');
  if (value.length > PRIVATE_ISSUER_MAX_LENGTH) throw new PrivateDecodeError('IDENTIFIER');
  nativeIdentifier(value);
  if (!value.startsWith(PRIVATE_ISSUER_PREFIX)) throw new PrivateDecodeError('IDENTIFIER');
  const match = LISTING_KEY_PARTS.exec(value.slice(PRIVATE_ISSUER_PREFIX.length));
  if (match === null) throw new PrivateDecodeError('IDENTIFIER');
  const country = match[1];
  const mic = match[2];
  let tail = match[3];
  if (!ASCII_TWO_LETTERS.test(country) || !MIC_SHAPE.test(mic)) throw new PrivateDecodeError('IDENTIFIER');
  if (!KNOWN_MICS.includes(mic.toUpperCase())) throw new PrivateDecodeError('IDENTIFIER');
  if (tail.length === 0) throw new PrivateDecodeError('IDENTIFIER');
  const dot = tail.lastIndexOf('.');
  if (dot > 0 && dot < tail.length - 1) {
    const digits = tail.slice(dot + 1);
    if (DIGITS_ONLY.test(digits)) {
      if (Number.parseInt(digits, 10) < 2) throw new PrivateDecodeError('IDENTIFIER');
      tail = tail.slice(0, dot);
    }
  }
  if (!LISTING_CODE.test(tail)) throw new PrivateDecodeError('IDENTIFIER');
  return value;
}

/** Structural shape test used by the server helper before the fixed owner fetch. */
export function isCanonicalIssuerShape(value         )                  {
  try {
    canonicalIssuerIdentifier(value);
    return true;
  } catch (error) {
    if (error instanceof PrivateDecodeError) return false;
    throw error;
  }
}

export function isFactIdShape(value         )                  {
  try {
    nativeFactId(value);
    return true;
  } catch (error) {
    if (error instanceof PrivateDecodeError) return false;
    throw error;
  }
}

/** An exact native content reference: fixed schema for its position, SHA-256, 1..16384 bytes. */
function decodeNativeReference(value         , expectedSchema        )                   {
  const record = closedObject(value, ['schema', 'sha256', 'byte_length']);
  if (record.schema !== expectedSchema) throw new PrivateDecodeError('REFERENCE');
  return Object.freeze({
    schema: expectedSchema,
    sha256: nativeDigest(record.sha256),
    byte_length: boundedInteger(record.byte_length, 1, PRIVATE_MAX_OBJECT_BYTES),
  });
}

/**
 * The identity snapshot reference names whatever actual receipt schema the incumbent
 * identity owner supplied; no Data OS snapshot contract is invented or hardcoded here.
 */
function decodeSnapshotReference(value         )                   {
  const record = closedObject(value, ['schema', 'sha256', 'byte_length']);
  return Object.freeze({
    schema: nativeIdentifier(record.schema),
    sha256: nativeDigest(record.sha256),
    byte_length: boundedInteger(record.byte_length, 1, PRIVATE_MAX_OBJECT_BYTES),
  });
}

function sameReference(left                  , right                  )          {
  return left.schema === right.schema && left.sha256 === right.sha256 && left.byte_length === right.byte_length;
}

/** Exact current store query grammar; this does not resolve or normalize identity. */
export function isPrivateCompanySymbol(value         )                  {
  return typeof value === 'string' && value.length >= 1 && value.length <= 24
    && /^[A-Z0-9][A-Z0-9.\-]{0,23}$/.test(value);
}

function currentIssuerIdentifier(value         )         {
  const id = canonicalIssuerIdentifier(value);
  if (id !== id.toUpperCase()) throw new PrivateDecodeError('IDENTIFIER');
  const suffix = id.slice(id.lastIndexOf('.') + 1);
  // Native disambiguators are arbitrary-size decimal integers. Never round them
  // through a JS Number merely to reject noncanonical leading zeroes.
  if (id.includes('.') && DIGITS_ONLY.test(suffix) && suffix.length > 1 && suffix.startsWith('0')) {
    throw new PrivateDecodeError('IDENTIFIER');
  }
  return id;
}

function currentSecurityIdentifier(value         )         {
  if (typeof value !== 'string' || !/^SEC:US-(XNAS|XNYS|XASE)-/.test(value)) {
    throw new PrivateDecodeError('IDENTIFIER');
  }
  // Reuse listing-key syntax only; this never derives the issuer of a security.
  currentIssuerIdentifier('ISS:' + value.slice(4));
  return value;
}

function identitySource(value         )                        {
  const source = closedObject(value, ['sha256', 'byte_length']);
  return Object.freeze({
    sha256: nativeDigest(source.sha256),
    byte_length: boundedInteger(source.byte_length, 1, 2 * 1024 * 1024),
  });
}

function evidenceDate(value         )         {
  if (typeof value !== 'string' || value.length !== 10 || !/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(value)) {
    throw new PrivateDecodeError('VALUE');
  }
  const date = new Date(value + 'T00:00:00.000Z');
  if (value.startsWith('0000-') || !Number.isFinite(date.getTime())
    || date.toISOString().slice(0, 10) !== value || value > new Date().toISOString().slice(0, 10)) {
    throw new PrivateDecodeError('VALUE');
  }
  return value;
}

/** Only closed ASCII strings, safe integers and objects enter this receipt encoder. */
function canonicalReceiptJson(value         )         {
  if (isPlainObject(value)) {
    return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonicalReceiptJson(value[key])).join(',') + '}';
  }
  if (typeof value === 'string' || typeof value === 'number') return JSON.stringify(value);
  throw new PrivateDecodeError('VALUE');
}

/** Verify the closed current metadata receipt; its digest is not an owner grant. */
export async function decodePrivateCompanyContext(value         , expectedSymbol        )                                 {
  const root = closedObject(value, ['schema', 'identity_mode', 'query', 'security_id', 'issuer_binding', 'identity_receipt']);
  if (root.schema !== PRIVATE_COMPANY_CONTEXT_SCHEMA) throw new PrivateDecodeError('SCHEMA');
  if (root.identity_mode !== PRIVATE_IDENTITY_MODE) throw new PrivateDecodeError('VALUE');
  const query = closedObject(root.query, ['namespace', 'symbol']);
  if (query.namespace !== 'store' || !isPrivateCompanySymbol(query.symbol) || query.symbol !== expectedSymbol) {
    throw new PrivateDecodeError('BINDING');
  }
  const symbol = query.symbol;
  const securityId = currentSecurityIdentifier(root.security_id);
  const binding = closedObject(root.issuer_binding, ['issuer_id', 'evidenced_cik', 'identity_snapshot_reference']);
  const issuerId = currentIssuerIdentifier(binding.issuer_id);
  const cik = evidencedCik(binding.evidenced_cik);
  const reference = decodeNativeReference(binding.identity_snapshot_reference, PRIVATE_IDENTITY_RECEIPT_SCHEMA);
  const raw = closedObject(root.identity_receipt, ['schema', 'identity_mode', 'issuer_id', 'evidenced_cik', 'source_commit', 'sources', 'evidence_source', 'evidence_snapshot']);
  if (raw.schema !== PRIVATE_IDENTITY_RECEIPT_SCHEMA || raw.identity_mode !== PRIVATE_IDENTITY_MODE
    || raw.issuer_id !== issuerId || raw.evidenced_cik !== cik || raw.evidence_source !== 'sec_company_tickers') {
    throw new PrivateDecodeError('BINDING');
  }
  if (typeof raw.source_commit !== 'string' || raw.source_commit.length !== 40 || !/^[0-9a-f]{40}$/.test(raw.source_commit)) {
    throw new PrivateDecodeError('DIGEST');
  }
  const sources = closedObject(raw.sources, ['security_master', 'vendor_aliases', 'issuer_master']);
  // Snapshot/freeze before awaiting crypto: caller mutation cannot replace a hashed value.
  const receipt                         = Object.freeze({
    schema: PRIVATE_IDENTITY_RECEIPT_SCHEMA, identity_mode: PRIVATE_IDENTITY_MODE,
    issuer_id: issuerId, evidenced_cik: cik, source_commit: raw.source_commit,
    sources: Object.freeze({
      security_master: identitySource(sources.security_master),
      vendor_aliases: identitySource(sources.vendor_aliases),
      issuer_master: identitySource(sources.issuer_master),
    }),
    evidence_source: 'sec_company_tickers', evidence_snapshot: evidenceDate(raw.evidence_snapshot),
  });
  const bytes = new TextEncoder().encode(canonicalReceiptJson(receipt));
  if (bytes.byteLength > PRIVATE_MAX_OBJECT_BYTES || bytes.byteLength !== reference.byte_length) {
    throw new PrivateDecodeError('REFERENCE');
  }
  let digest        ;
  try {
    const hash = await globalThis.crypto.subtle.digest('SHA-256', bytes);
    digest = Array.from(new Uint8Array(hash), byte => byte.toString(16).padStart(2, '0')).join('');
  } catch {
    throw new PrivateDecodeError('DIGEST');
  }
  if (digest !== reference.sha256) throw new PrivateDecodeError('REFERENCE');
  return Object.freeze({
    schema: PRIVATE_COMPANY_CONTEXT_SCHEMA, identity_mode: PRIVATE_IDENTITY_MODE,
    query: Object.freeze({ namespace: 'store', symbol }), security_id: securityId,
    issuer_binding: Object.freeze({ issuer_id: issuerId, evidenced_cik: cik, identity_snapshot_reference: reference }),
    identity_receipt: receipt,
  });
}

/** Compare decoded projections before selecting a fact; matching hashes grant no rights. */
export function assertPrivateContextSelection(context                       , selection                         )       {
  const left = context.issuer_binding;
  const right = selection.issuer_binding;
  if (left.issuer_id !== right.issuer_id || left.evidenced_cik !== right.evidenced_cik
    || !sameReference(left.identity_snapshot_reference, right.identity_snapshot_reference)) {
    throw new PrivateDecodeError('COMPOSITION');
  }
}

function sameSelectionEntry(left                       , right                       )          {
  return left.fact_id === right.fact_id
    && sameReference(left.fact_reference, right.fact_reference)
    && sameReference(left.edition_reference, right.edition_reference)
    && left.kind === right.kind
    && left.lifecycle === right.lifecycle;
}

function decodeFactFields(value, supplier = false)                    {
  const fact = subsetObject(value, FACT_MANDATORY_KEYS, FACT_OPTIONAL_KEYS);
  const kind = supplier ? 'disclosed_supplier' : PRIVATE_KIND;
  const lifecycle = supplier ? 'reported_use' : PRIVATE_LIFECYCLE;
  if (fact.kind !== kind || fact.lifecycle !== lifecycle) throw new PrivateDecodeError('VALUE');
  const draft = { fact_id: nativeFactId(fact.fact_id), kind, lifecycle };
  if ('revision' in fact) draft.revision = boundedInteger(fact.revision, 1, PRIVATE_MAX_REVISION);
  if ('subject_id' in fact) draft.subject_id = nativeIdentifier(fact.subject_id);
  if ('object_id' in fact) draft.object_id = nativeIdentifier(fact.object_id);
  if (draft.subject_id !== undefined && draft.object_id !== undefined && draft.subject_id === draft.object_id) {
    throw new PrivateDecodeError('IDENTITY');
  }
  if ('product' in fact) draft.product = nativeScopeText(fact.product);
  if ('platform' in fact) draft.platform = nativeScopeText(fact.platform);
  if ('amount' in fact) {
    if (fact.amount !== null) throw new PrivateDecodeError('MAGNITUDE');
    draft.amount = null;
  }
  if ('economic_share' in fact) {
    if (fact.economic_share !== null) throw new PrivateDecodeError('MAGNITUDE');
    draft.economic_share = null;
  }
  return Object.freeze(draft);
}

function decodeSelectionEntries(value         )                                   {
  if (!Array.isArray(value)) throw new PrivateDecodeError('VALUE');
  if (value.length > PRIVATE_MAX_SELECTIONS) throw new PrivateDecodeError('LIMIT');
  const entries                          = [];
  let previous = '';
  for (const [index, element] of value.entries()) {
    const record = closedObject(element, ['fact_id', 'fact_reference', 'edition_reference', 'kind', 'lifecycle']);
    const factId = nativeFactId(record.fact_id);
    const supplier = record.kind === 'disclosed_supplier' && record.lifecycle === 'reported_use';
    if (!supplier && (record.kind !== PRIVATE_KIND || record.lifecycle !== PRIVATE_LIFECYCLE)) throw new PrivateDecodeError('VALUE');
    const factReference = decodeNativeReference(record.fact_reference, supplier ? PRIVATE_SUPPLIER_FACT_SCHEMA : PRIVATE_FACT_SCHEMA);
    const editionReference = decodeNativeReference(record.edition_reference, supplier ? PRIVATE_SEC_EDITION_SCHEMA : PRIVATE_EDITION_SCHEMA);
    // Sorted and unique is the source ordering contract: it also refuses duplicates.
    if (index > 0 && !(factId > previous)) throw new PrivateDecodeError('ORDER');
    previous = factId;
    entries.push(Object.freeze({
      fact_id: factId,
      fact_reference: factReference,
      edition_reference: editionReference,
      kind: record.kind,
      lifecycle: record.lifecycle,
    }));
  }
  return Object.freeze(entries);
}

/**
 * Decode one current issuer selection projection. A qualified empty list is valid and
 * stays empty; a malformed projection is a refusal, never an empty answer.
 */
export function decodePrivateIssuerSelections(value         , expectedIssuerId        )                          {
  const root = closedObject(value, ['schema', 'generation', 'identity_mode', 'issuer_role', 'issuer_binding', 'selections']);
  if (root.schema !== PRIVATE_ISSUER_SELECTIONS_SCHEMA) throw new PrivateDecodeError('SCHEMA');
  if (root.identity_mode !== PRIVATE_IDENTITY_MODE) throw new PrivateDecodeError('VALUE');
  if (root.issuer_role !== PRIVATE_ISSUER_ROLE) throw new PrivateDecodeError('VALUE');
  const generation = nativeIdentifier(root.generation);
  const binding = closedObject(root.issuer_binding, ['issuer_id', 'evidenced_cik', 'identity_snapshot_reference']);
  const issuerId = canonicalIssuerIdentifier(binding.issuer_id);
  // The expected issuer is the caller's already-resolved company context; a projection
  // that names any other issuer is refused. The shape of a CIK grants nothing.
  if (issuerId !== expectedIssuerId) throw new PrivateDecodeError('BINDING');
  const cik = evidencedCik(binding.evidenced_cik);
  const snapshot = decodeSnapshotReference(binding.identity_snapshot_reference);
  const selections = decodeSelectionEntries(root.selections);
  return Object.freeze({
    schema: PRIVATE_ISSUER_SELECTIONS_SCHEMA,
    generation,
    identity_mode: PRIVATE_IDENTITY_MODE,
    issuer_role: PRIVATE_ISSUER_ROLE,
    issuer_binding: Object.freeze({
      issuer_id: issuerId,
      evidenced_cik: cik,
      identity_snapshot_reference: snapshot,
    }),
    selections,
  });
}

/**
 * Decode one current private product-integration fact. The expected fact id must match
 * exactly; the granted subset may omit every optional native field, so a fact decoded
 * here is not yet evidence that it belongs to any issuer selection.
 */
export function decodePrivateProductIntegration(value         , expectedFactId        )                            {
  const root = closedObject(value, ['schema', 'fact', 'reference', 'edition', 'source_timing', 'generation', 'authority']);
  if (root.schema !== PRIVATE_PRODUCT_INTEGRATION_SCHEMA) throw new PrivateDecodeError('SCHEMA');
  if (root.authority !== PRIVATE_AUTHORITY) throw new PrivateDecodeError('VALUE');
  const generation = nativeIdentifier(root.generation);
  const reference = decodeNativeReference(root.reference, PRIVATE_FACT_SCHEMA);
  const edition = decodeNativeReference(root.edition, PRIVATE_EDITION_SCHEMA);
  const fact = decodeFactFields(root.fact);
  if (fact.fact_id !== expectedFactId) throw new PrivateDecodeError('BINDING');
  return Object.freeze({
    schema: PRIVATE_PRODUCT_INTEGRATION_SCHEMA,
    fact,
    reference,
    edition,
    source_timing: decodeSourceTiming(root.source_timing),
    generation,
    authority: PRIVATE_AUTHORITY,
  });
}

/** Decode the independently qualified SEC species, never reinterpret a plan. */
export async function decodePrivateDisclosure(value, expectedFactId) {
  if (value?.schema !== PRIVATE_SUPPLIER_SCHEMA) return decodePrivateProductIntegration(value, expectedFactId);
  const root = closedObject(value, ['schema','fact','reference','edition','source_timing','generation','authority','supplier_binding']);
  if (root.authority !== PRIVATE_AUTHORITY) throw new PrivateDecodeError('VALUE');
  closedObject(root.fact, [...FACT_MANDATORY_KEYS, ...FACT_OPTIONAL_KEYS]);
  const fact = decodeFactFields(root.fact, true);
  canonicalIssuerIdentifier(fact.subject_id); canonicalIssuerIdentifier(fact.object_id);
  if (fact.fact_id !== expectedFactId || fact.platform !== 'foundry_services') throw new PrivateDecodeError('BINDING');
  const reference = decodeNativeReference(root.reference, PRIVATE_SUPPLIER_FACT_SCHEMA);
  const edition = decodeNativeReference(root.edition, PRIVATE_SEC_EDITION_SCHEMA);
  const generation = nativeIdentifier(root.generation);
  const timing = closedObject(root.source_timing, ['published_date','published_at','publication_precision','known_at','sec_source']);
  const baseTiming = decodeSourceTiming(Object.fromEntries(['published_date','published_at','publication_precision','known_at'].map(k => [k,timing[k]])));
  if (baseTiming.publication_precision !== 'date') throw new PrivateDecodeError('TIMING');
  const source = closedObject(timing.sec_source, ['snapshot_id','snapshot_at','manifest_key','document_id','accession',
    'issuer_cik','archive_url','accepted_at','retrieved_at','recorded_at','retrieval_receipt_id','span_start_byte','span_end_byte','span_sha256']);
  for (const key of Object.keys(source)) {
    if (key === 'span_start_byte' || key === 'span_end_byte') continue;
    if (typeof source[key] !== 'string' || !source[key].length || source[key].length > 700 || /[\x00-\x1f]/.test(source[key])) throw new PrivateDecodeError('VALUE');
  }
  const cik = evidencedCik(source.issuer_cik);
  if (!/^ffsecsrc_[a-f0-9]{64}$/.test(source.snapshot_id) || !/^sec_document_[a-f0-9]{64}$/.test(source.document_id)
      || !/^[0-9]{10}-[0-9]{2}-[0-9]{6}$/.test(source.accession)
      || !/^sec_archive_receipt_[a-f0-9]{64}$/.test(source.retrieval_receipt_id)
      || !new RegExp('^manifests/'+cik+'/'+source.accession+'/ffsec_manifest_[a-f0-9]{64}\\.json$').test(source.manifest_key)) throw new PrivateDecodeError('BINDING');
  let url; try { url = new URL(source.archive_url); } catch (_) { throw new PrivateDecodeError('BINDING'); }
  const prefix = '/Archives/edgar/data/'+String(BigInt(cik))+'/'+source.accession.replaceAll('-','')+'/';
  if (url.origin !== 'https://www.sec.gov' || url.username || url.password || url.search || url.hash
      || !url.pathname.startsWith(prefix) || !/^[A-Za-z0-9_.-]+\.html?$/.test(url.pathname.slice(prefix.length))
      || url.href !== source.archive_url) throw new PrivateDecodeError('BINDING');
  const start = boundedInteger(source.span_start_byte, 0, 4*1024*1024);
  const end = boundedInteger(source.span_end_byte, start+1, 4*1024*1024);
  nativeDigest(source.span_sha256);
  const binding = closedObject(root.supplier_binding, ['direction','identity_mode','identity_observed_at','adopted_at',
    'evidence_revision','span','subject_identity','object_identity','current_subject_identity','current_object_identity']);
  if (binding.direction !== 'object_supplies_subject' || binding.identity_mode !== 'current') throw new PrivateDecodeError('VALUE');
  const span = closedObject(binding.span, ['start_byte','end_byte','text_sha256']);
  if (span.start_byte !== start || span.end_byte !== end || span.text_sha256 !== source.span_sha256) throw new PrivateDecodeError('BINDING');
  nativeDigest(binding.evidence_revision);nativeDigest(binding.subject_identity);nativeDigest(binding.object_identity);
  nativeDigest(binding.current_subject_identity);nativeDigest(binding.current_object_identity);
  const instant = value => { const n = typeof value === 'string' && timingInstantToEpochMicroseconds(value);
    if (n === false || n === null || n > BigInt(Date.now())*BigInt(1000)) throw new PrivateDecodeError('TIMING'); return n; };
  const clocks = [source.accepted_at,source.retrieved_at,source.recorded_at,source.snapshot_at,baseTiming.known_at,binding.adopted_at].map(instant);
  if (clocks.some((v,i) => i && v < clocks[i-1]) || instant(binding.identity_observed_at) > clocks.at(-1)
      || baseTiming.published_date !== source.accepted_at.slice(0,10)) throw new PrivateDecodeError('TIMING');
  const bytes = new TextEncoder().encode(canonicalReceiptJson(source));
  const digest = [...new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256',bytes))].map(v=>v.toString(16).padStart(2,'0')).join('');
  if (digest !== binding.evidence_revision) throw new PrivateDecodeError('DIGEST');
  return Object.freeze({schema:PRIVATE_SUPPLIER_SCHEMA,fact,reference,edition,generation,authority:PRIVATE_AUTHORITY,
    source_timing:Object.freeze({...baseTiming,sec_source:Object.freeze({...source})}),
    supplier_binding:Object.freeze({...binding,span:Object.freeze({...span})})});
}

/** Status-bound allowlist mirrored from the mounted transport in app/company_disclosures.py. */
const KNOWN_PRIVATE_ERRORS                                                        = Object.freeze({
  400: Object.freeze(['REQUEST_INVALID']         ),
  401: Object.freeze(['AUTHENTICATION_REQUIRED']         ),
  403: Object.freeze(['ENTITLEMENT_REQUIRED']         ),
  502: Object.freeze(['AUTHENTICATION_UNAVAILABLE']         ),
  503: Object.freeze(['PRIVATE_SERVICE_UNAVAILABLE', 'SOURCE_RUNTIME_UNAVAILABLE', 'PRIVATE_SOURCE_UNAVAILABLE', 'SOURCE_NOT_ADMITTED']         ),
});

export function isKnownPrivateErrorPairing(status        , code        )                           {
  const allowed = KNOWN_PRIVATE_ERRORS[status];
  if (allowed === undefined) return false;
  return allowed.includes(code                    );
}

/** The only bounded local error namespace this consumer may emit or forward. */
export function privateErrorPayload(code                  )                      {
  return Object.freeze({ schema: PRIVATE_ERROR_SCHEMA, code, automatic_retry_permitted: false });
}

/**
 * Decode a closed upstream error. An unknown code, a code bound to the wrong status,
 * a missing or extra key, or any retry permission is a refusal, not a pass-through.
 */
export function decodePrivateError(value         , status        )                      {
  if (!Number.isSafeInteger(status)) throw new PrivateDecodeError('STATUS');
  const root = closedObject(value, ['schema', 'code', 'automatic_retry_permitted']);
  if (root.schema !== PRIVATE_ERROR_SCHEMA) throw new PrivateDecodeError('SCHEMA');
  const code = root.code;
  if (typeof code !== 'string' || !isKnownPrivateErrorPairing(status, code)) throw new PrivateDecodeError('STATUS');
  if (root.automatic_retry_permitted !== false) throw new PrivateDecodeError('RETRY');
  return privateErrorPayload(code);
}

/**
 * The narrow selection-to-fact join the later admitted host calls before display.
 *
 * It requires what the native reader requires of a selected fact: the entry really
 * belongs to this snapshot, the fact is the entry's exact fact id, its subject_id is
 * present and equals the selection issuer, the fact and edition references match
 * component for component, and the generation matches. A caller cannot force an old
 * generation to stay authorized: any mismatch is a refusal.
 *
 * subject_id is mandatory here even though the generic fact decoder leaves every
 * optional granted field absent. This assertion compares projection metadata; it does
 * not recompute content hashes and it is not an admission decision.
 */
export function assertPrivateComposition(
  selection                         ,
  entry                       ,
  fact                           ,
)       {
  if (!isPlainObject(selection) || !isPlainObject(entry) || !isPlainObject(fact)) {
    throw new PrivateDecodeError('COMPOSITION');
  }
  if (!selection.selections.some((candidate) => sameSelectionEntry(candidate, entry))) {
    throw new PrivateDecodeError('COMPOSITION');
  }
  if (fact.fact.fact_id !== entry.fact_id) throw new PrivateDecodeError('COMPOSITION');
  const subjectId = fact.fact.subject_id;
  if (typeof subjectId !== 'string' || subjectId !== selection.issuer_binding.issuer_id) {
    throw new PrivateDecodeError('COMPOSITION');
  }
  if (!sameReference(fact.reference, entry.fact_reference)) throw new PrivateDecodeError('COMPOSITION');
  if (!sameReference(fact.edition, entry.edition_reference)) throw new PrivateDecodeError('COMPOSITION');
  if (fact.generation !== selection.generation) throw new PrivateDecodeError('COMPOSITION');
  if (fact.schema === PRIVATE_SUPPLIER_SCHEMA && (fact.source_timing.sec_source.issuer_cik !== selection.issuer_binding.evidenced_cik
      || fact.supplier_binding.current_subject_identity !== selection.issuer_binding.identity_snapshot_reference.sha256)) throw new PrivateDecodeError('COMPOSITION');
  if (entry.kind !== fact.fact.kind || entry.lifecycle !== fact.fact.lifecycle) {
    throw new PrivateDecodeError('COMPOSITION');
  }
}

/** Closed, current research projection. Shape checks do not grant source rights. */
export async function decodePrivateSupplierResearch(value, expectedFactId) {
  const root = closedObject(value, ['schema','status','reason','disclosure','candidate']);
  if (root.schema !== PRIVATE_SUPPLIER_RESEARCH_SCHEMA) throw new PrivateDecodeError('SCHEMA');
  const disclosure = await decodePrivateDisclosure(root.disclosure, expectedFactId);
  if (root.status === 'context_only') {
    if (root.reason !== 'NO_QUALIFIED_SUPPLIER_ROLE' || root.candidate !== null
        || disclosure.schema === PRIVATE_SUPPLIER_SCHEMA) throw new PrivateDecodeError('VALUE');
    return Object.freeze({schema: root.schema, status: root.status, reason: root.reason, disclosure, candidate: null});
  }
  if (root.status !== 'available' || root.reason !== null || disclosure.schema !== PRIVATE_SUPPLIER_SCHEMA) {
    throw new PrivateDecodeError('VALUE');
  }
  const c = closedObject(root.candidate, ['record_id','content_sha256','compiled_at','review_by','target',
    'observed','mechanism','alternatives','falsifiers','applicability_conditions','evaluation_requirements',
    'contextual_refusal','lineage','empirical_evaluation','authority']);
  function text(v) {
    if (typeof v !== 'string' || !v.length || v.length > 2048 || /[\x00-\x1f]/.test(v)) throw new PrivateDecodeError('VALUE');
    return v;
  }
  function instant(v) {
    const n = typeof v === 'string' ? timingInstantToEpochMicroseconds(v) : null;
    if (n === null || n > BigInt(Date.now())*1000n) throw new PrivateDecodeError('TIMING');
    return n;
  }
  function rows(v, keys, maximum) {
    if (!Array.isArray(v) || v.length < 1 || v.length > maximum) throw new PrivateDecodeError('VALUE');
    return Object.freeze(v.map(row => Object.freeze(Object.fromEntries(
      keys.map(k => [k,text(closedObject(row, keys)[k])])))));
  }
  nativeIdentifier(c.record_id); nativeDigest(c.content_sha256);
  const compiled = instant(c.compiled_at);
  if (typeof c.review_by !== 'string' || timingDateParts(c.review_by) === null) throw new PrivateDecodeError('TIMING');
  const currentDay = new Date().toISOString().slice(0,10);
  if (c.compiled_at.slice(0,10) !== currentDay || c.review_by < currentDay) throw new PrivateDecodeError('TIMING');
  const target = closedObject(c.target, ['issuer_id','security_id','symbol']);
  currentIssuerIdentifier(target.issuer_id); currentSecurityIdentifier(target.security_id);
  if (!isPrivateCompanySymbol(target.symbol) || target.symbol !== 'TSM'
      || target.issuer_id !== disclosure.fact.object_id || disclosure.fact.subject_id !== 'ISS:US-XNAS-NVDA') {
    throw new PrivateDecodeError('BINDING');
  }
  const o = closedObject(c.observed, ['event_fact_id','kind','source_report_period','occurrence_period','occurrence_at',
    'reporting_at','retrieved_at','adopted_at','verified_at','document_id','raw_sha256','span_sha256',
    'span_start_byte','span_end_byte','accession','archive_url','policy_sha256','decision_sha256']);
  nativeIdentifier(o.event_fact_id);
  const period = closedObject(o.occurrence_period, ['year','quarter']);
  if (o.kind !== 'reported_h20_demand_loss' || o.source_report_period !== 'FY2026'
      || period.year !== 2026 || period.quarter !== 1 || o.occurrence_at !== null) throw new PrivateDecodeError('VALUE');
  const source = disclosure.source_timing.sec_source;
  for (const k of ['document_id','accession','archive_url']) {
    if (o[k] !== source[k]) throw new PrivateDecodeError('BINDING');
  }
  for (const k of ['raw_sha256','span_sha256','policy_sha256','decision_sha256']) nativeDigest(o[k]);
  const start = boundedInteger(o.span_start_byte, 0, 4*1024*1024);
  boundedInteger(o.span_end_byte, start+1, 4*1024*1024);
  const clocks = ['reporting_at','retrieved_at','adopted_at','verified_at'].map(k => instant(o[k]));
  if (o.reporting_at !== source.accepted_at || o.retrieved_at !== source.retrieved_at
      || clocks.some((n,i) => i && n < clocks[i-1]) || clocks.at(-1) > compiled) throw new PrivateDecodeError('TIMING');
  const m = closedObject(c.mechanism, ['state','mechanism_class','mechanism_polarity',
    'predicted_operating_direction','operating_metric_class','hypothesis_text']);
  if (m.state !== 'hypothesized' || m.mechanism_class !== 'demand_transfer' || m.mechanism_polarity !== 'away_from_target'
      || m.predicted_operating_direction !== 'deteriorates' || m.operating_metric_class !== 'volume') throw new PrivateDecodeError('VALUE');
  text(m.hypothesis_text);
  const alternatives = rows(c.alternatives, ['explanation_class','text'], 6);
  if (alternatives.length !== 2 || !alternatives.some(r=>r.explanation_class==='sector_factor')
      || !alternatives.some(r=>r.explanation_class==='coincident_timing')) throw new PrivateDecodeError('VALUE');
  const falsifiers = rows(c.falsifiers, ['condition','observable'], 4);
  const applicability = rows(c.applicability_conditions, ['reason','condition','consequence'], 6);
  const reasons = ['antecedent_not_observed','relationship_inapplicable','outcome_unavailable','evaluation_not_registered','review_expired_untested'];
  if (applicability.length !== reasons.length || reasons.some(r=>!applicability.some(a=>a.reason===r))) throw new PrivateDecodeError('VALUE');
  const requirements = ['native_owner_confirmed_antecedent_occurrence','applicable_role_specific_relationship',
    'preregistered_metric_scope_and_comparable_baseline','preregistered_event_window_outcome_lag_and_window',
    'preregistered_rejection_rule_and_uncertainty_handling','sufficient_purpose_eligible_comparable_outcome_observations'];
  if (!Array.isArray(c.evaluation_requirements) || c.evaluation_requirements.length !== requirements.length
      || requirements.some((v,i)=>c.evaluation_requirements[i]!==v)) throw new PrivateDecodeError('VALUE');
  const refusal = closedObject(c.contextual_refusal, ['reason','hypothesis','relationship_input_used']);
  const lineage = closedObject(c.lineage, ['same_document','independent_corroboration']);
  const authority = closedObject(c.authority, ['rank','gate','size','trade','prediction']);
  if (refusal.reason !== 'CO_DOCUMENT_CONTEXT_IS_NOT_GRAPH1' || refusal.hypothesis !== null || refusal.relationship_input_used !== false
      || lineage.same_document !== true || lineage.independent_corroboration !== false
      || c.empirical_evaluation !== 'not_performed' || Object.values(authority).some(v=>v!==false)) throw new PrivateDecodeError('VALUE');
  return Object.freeze({schema: root.schema, status: root.status, reason: null, disclosure,
    candidate: Object.freeze({...c, target: Object.freeze({...target}), observed: Object.freeze({...o, occurrence_period:Object.freeze({...period})}),
      mechanism:Object.freeze({...m}), alternatives, falsifiers, applicability_conditions:applicability,
      evaluation_requirements:Object.freeze([...requirements]), contextual_refusal:Object.freeze({...refusal}),
      lineage:Object.freeze({...lineage}), authority:Object.freeze({...authority})})});
}

export function assertPrivateResearchComposition(fact, research) {
  // Both operands already passed closed decoders; normalize only JSON ordering.
  function stable(v) {
    if (v === null || typeof v !== 'object') return JSON.stringify(v);
    if (Array.isArray(v)) return '[' + v.map(stable).join(',') + ']';
    return '{' + Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+stable(v[k])).join(',') + '}';
  }
  if (stable(fact) !== stable(research.disclosure)) throw new PrivateDecodeError('COMPOSITION');
}
