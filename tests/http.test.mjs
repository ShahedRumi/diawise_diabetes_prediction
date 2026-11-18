import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';


test('fetchJson returns parsed JSON', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({ok: true, status: 200, json: async () => ({ready: true})});
  try {
    const {fetchJson} = await import('../static/js/http.js');
    assert.deepEqual(await fetchJson('/api/health'), {ready: true});
  } finally {
    globalThis.fetch = originalFetch;
  }
});


test('fetchJson surfaces API detail', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({ok: false, status: 422, json: async () => ({detail: 'Invalid nutrition input'})});
  try {
    const {fetchJson} = await import('../static/js/http.js');
    await assert.rejects(fetchJson('/api/predict/food'), /Invalid nutrition input/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});


test('fetchJson aborts after the deadline', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (_url, options) => new Promise((_resolve, reject) => {
    options.signal.addEventListener('abort', () => {
      const error = new Error('aborted');
      error.name = 'AbortError';
      reject(error);
    }, {once: true});
  });
  try {
    const {fetchJson} = await import('../static/js/http.js');
    await assert.rejects(fetchJson('/slow', {}, 10), /timed out/i);
  } finally {
    globalThis.fetch = originalFetch;
  }
});


test('fetchJson rejects when reading a successful body exceeds the deadline', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (_url, options) => ({
    ok: true,
    status: 200,
    json: () => new Promise((_resolve, reject) => {
      options.signal.addEventListener('abort', () => {
        const error = new Error('aborted');
        error.name = 'AbortError';
        reject(error);
      }, {once: true});
    }),
  });
  try {
    const {fetchJson} = await import('../static/js/http.js');
    await assert.rejects(fetchJson('/slow-body', {}, 10), /timed out/i);
  } finally {
    globalThis.fetch = originalFetch;
  }
});


test('fetchJson rejects malformed JSON from a successful response', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: true,
    status: 200,
    json: async () => { throw new SyntaxError('Unexpected token'); },
  });
  try {
    const {fetchJson} = await import('../static/js/http.js');
    await assert.rejects(fetchJson('/broken-json'), /invalid JSON/i);
  } finally {
    globalThis.fetch = originalFetch;
  }
});


test('classic browser scripts share one realm and restore the form after failure', async () => {
  const httpSource = await readFile(new URL('../static/js/http.js', import.meta.url), 'utf8');
  const mainSource = await readFile(new URL('../static/js/main.js', import.meta.url), 'utf8');
  const elements = new Map();
  for (const id of ['form-errors', 'submit-button', 'submit-label']) {
    elements.set(id, {hidden: true, disabled: false, textContent: ''});
  }
  const values = {
    Pregnancies: '2', Glucose: '125', BloodPressure: '72', SkinThickness: '25',
    Insulin: '88', BMI: '28.4', DiabetesPedigreeFunction: '.42', Age: '38',
  };
  for (const [name, value] of Object.entries(values)) {
    elements.set(`f-${name}`, {value, checkValidity: () => true, reportValidity: () => {}});
  }
  let domReadyListener;
  const document = {
    querySelector: selector => elements.get(selector.slice(1)),
    querySelectorAll: () => [],
    getElementById: id => elements.get(id),
    addEventListener: (name, listener) => { if (name === 'DOMContentLoaded') domReadyListener = listener; },
  };
  const context = vm.createContext({
    window: {innerWidth: 1024}, document, AbortController, setTimeout, clearTimeout, console,
    fetch: async () => { throw new Error('unused'); },
  });

  vm.runInContext(httpSource, context, {filename: 'http.js'});
  context.window.DiaWiseHttp.fetchJson = async () => { throw new Error('Request timed out after 10 seconds.'); };
  vm.runInContext(mainSource, context, {filename: 'main.js'});
  assert.equal(typeof domReadyListener, 'function');

  await context.submitPrediction({preventDefault() {}});
  assert.equal(elements.get('submit-button').disabled, false);
  assert.equal(elements.get('form-errors').hidden, false);
  assert.match(elements.get('form-errors').textContent, /timed out/i);
});
