/**
 * Node replica of templates/account.js getToken() on the www / _macro path.
 *
 * theme.js binds MDXAuth.client to getSupabaseClient, which ALWAYS returns a
 * Promise. Calling `.getSession()` on that Promise throws synchronously
 * (`getSession is not a function`) and api() never reaches fetch — every
 * account action on www is dead. This suite pins the await-the-client path.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const SOURCE = readFileSync(join(ROOT, 'templates', 'account.js'), 'utf8');

function extractGetTokenSource(source) {
  const asyncIdx = source.indexOf('async function getToken()');
  const syncIdx = source.indexOf('function getToken()');
  const start = asyncIdx >= 0 ? asyncIdx : syncIdx;
  if (start < 0) throw new Error('getToken() not found in templates/account.js');
  const brace = source.indexOf('{', start);
  let depth = 0;
  for (let i = brace; i < source.length; i += 1) {
    const ch = source[i];
    if (ch === '{') depth += 1;
    else if (ch === '}') {
      depth -= 1;
      if (depth === 0) return source.slice(start, i + 1);
    }
  }
  throw new Error('getToken() brace match failed');
}

function loadGetToken(mdxAuth) {
  const fnSrc = extractGetTokenSource(SOURCE);
  const context = vm.createContext({
    window: { MDXAuth: mdxAuth },
    Promise,
  });
  // _macro is closed over by getToken in the real IIFE; bind it here so the
  // extracted function takes the www path. SUPA/hasPersisted/sbClient are the
  // standalone fallbacks and must not throw if that branch is ever hit.
  const wrapped = [
    'var _macro = true;',
    'var SUPA = null;',
    'function hasPersisted() { return false; }',
    'function sbClient() { return Promise.resolve(null); }',
    fnSrc,
    'getToken;',
  ].join('\n');
  return vm.runInContext(wrapped, context);
}

test('getToken awaits MDXAuth.client() Promise and resolves the session token', async () => {
  const getToken = loadGetToken({
    client() {
      return Promise.resolve({
        auth: {
          getSession() {
            return Promise.resolve({
              data: { session: { access_token: 'tok-from-session' } },
            });
          },
        },
      });
    },
  });
  const token = await getToken();
  assert.equal(token, 'tok-from-session');
});

test('getToken returns null when MDXAuth.client() rejects, and never throws', async () => {
  const getToken = loadGetToken({
    client() {
      return Promise.reject(new Error('auth-disabled'));
    },
  });
  const token = await getToken();
  assert.equal(token, null);
});

test('getToken returns null when MDXAuth.client is missing, and never throws', async () => {
  const getToken = loadGetToken({});
  const token = await getToken();
  assert.equal(token, null);
});
