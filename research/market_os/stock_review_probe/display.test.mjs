import test from 'node:test';
import assert from 'node:assert/strict';
import {escapeHTML,number,change,tone} from './review-display.mjs';
test('untrusted text cannot create HTML or attributes',()=>assert.equal(escapeHTML('<img src=x onerror="alert(1)"> & \'x\''),'&lt;img src=x onerror=&quot;alert(1)&quot;&gt; &amp; &#39;x&#39;'));
test('zero is a displayed value, not unknown',()=>assert.equal(number(0,2),'0.00'));
test('null/undefined/NaN are an em dash rather than zero',()=>{for(const v of [null,undefined,NaN,Infinity,'2'])assert.equal(number(v),'—');});
test('signed changes carry positive and negative signs',()=>{assert.equal(change(1.5),'+1.50%');assert.equal(change(-1.5),'−1.50%');});
test('missing change is not a neutral zero percent',()=>assert.equal(change(null),'—'));
test('unknown readiness has neutral presentation',()=>assert.equal(tone('unseen-lane'),'muted'));
test('quote rise is not reused as an entry badge',()=>{assert.equal(tone('Almost ready'),'info');assert.equal(tone('Watch — don’t chase'),'warn');});

test('inherited object names cannot become a CSS presentation token',()=>{for(const lane of ['__proto__','constructor','toString'])assert.equal(tone(lane),'muted');});
