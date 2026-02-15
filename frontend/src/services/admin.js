/**
 * Admin API client
 */
import { getCurrentLanguage } from '../i18n';
import { getAccessToken } from './auth';

const API_ORIGIN = import.meta.env?.VITE_BACKEND_ORIGIN || '';
const API_PREFIX = API_ORIGIN ? API_ORIGIN.replace(/\/+$/, '') : '';
const ADMIN_BASE = `${API_PREFIX}/api/v1/admin`;

async function fetchAdmin(url, options = {}) {
  const language = getCurrentLanguage();
  const token = getAccessToken();

  const headers = {
    'Accept-Language': language,
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const resp = await fetch(url, { ...options, headers });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const err = new Error(data.detail || '请求失败');
    err.status = resp.status;
    err.data = data;
    throw err;
  }
  return data;
}

export function adminListCookiePool({ platform, status, limit = 200, offset = 0 } = {}) {
  const qs = new URLSearchParams();
  if (platform) qs.set('platform', platform);
  qs.set('limit', String(limit));
  qs.set('offset', String(offset));
  return fetchAdmin(`${ADMIN_BASE}/cookies/pool?${qs.toString()}`);
}

export function adminCreateCookiePoolItem(payload) {
  return fetchAdmin(`${ADMIN_BASE}/cookies/pool`, { method: 'POST', body: JSON.stringify(payload) });
}

export function adminUpdateCookiePoolItem(id, payload) {
  return fetchAdmin(`${ADMIN_BASE}/cookies/pool/${id}`, { method: 'PATCH', body: JSON.stringify(payload) });
}

export function adminDeleteCookiePoolItem(id) {
  return fetchAdmin(`${ADMIN_BASE}/cookies/pool/${id}`, { method: 'DELETE' });
}

export function adminListUsers({ q, limit = 200, offset = 0 } = {}) {
  const qs = new URLSearchParams();
  if (q) qs.set('q', q);
  qs.set('limit', String(limit));
  qs.set('offset', String(offset));
  return fetchAdmin(`${ADMIN_BASE}/users?${qs.toString()}`);
}

export function adminUpdateUser(userId, payload) {
  return fetchAdmin(`${ADMIN_BASE}/users/${encodeURIComponent(userId)}`, { method: 'PATCH', body: JSON.stringify(payload) });
}

export function adminLLMUsageSummary({ days = 7, model } = {}) {
  const qs = new URLSearchParams();
  qs.set('days', String(days));
  if (model) qs.set('model', model);
  return fetchAdmin(`${ADMIN_BASE}/usage/llm/summary?${qs.toString()}`);
}
