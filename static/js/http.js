/* Shared JSON request helper with a bounded wait. */
'use strict';

async function fetchJson(url, options = {}, timeoutMs = 10000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {...options, signal: controller.signal});
    let body = {};
    try {
      body = await response.json();
    } catch (error) {
      if (controller.signal.aborted) throw error;
      if (response.ok) throw new Error('Server returned invalid JSON.');
    }
    if (!response.ok) {
      let detail = body.detail;
      if (Array.isArray(detail)) detail = detail.map(item => item.msg || String(item)).join('; ');
      throw new Error(detail || `Request failed (${response.status})`);
    }
    return body;
  } catch (error) {
    if (controller.signal.aborted) {
      throw new Error(`Request timed out after ${Math.ceil(timeoutMs / 1000)} seconds.`);
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

if (typeof window !== 'undefined') window.DiaWiseHttp = {fetchJson};
if (typeof module !== 'undefined' && module.exports) module.exports.fetchJson = fetchJson;
