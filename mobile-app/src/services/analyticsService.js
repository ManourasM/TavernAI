/**
 * Analytics Service - Fetch dashboard summary data from the backend
 *
 * Endpoints used:
 *   GET /api/analytics/summary?from=YYYY-MM-DD&to=YYYY-MM-DD
 */

import { getConfig } from './api';
import { getToken } from './authService';

function buildHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  const token = getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

async function buildHttpUrl(path) {
  const config = await getConfig();
  const base = config.backend_base || `${location.protocol}//${location.host}`;
  return `${base}${path}`;
}

/**
 * Fetch the analytics dashboard summary for a date range.
 *
 * @param {string|null} from - Start date YYYY-MM-DD (optional, defaults to today on backend)
 * @param {string|null} to   - End date YYYY-MM-DD (optional, defaults to today on backend)
 * @returns {Promise<Object>} Summary object with today_revenue, orders_count, etc.
 */
export async function getAnalyticsSummary(from = null, to = null) {
  const params = new URLSearchParams();
  if (from) params.set('from', from);
  if (to) params.set('to', to);

  const query = params.toString() ? `?${params.toString()}` : '';
  const url = await buildHttpUrl(`/api/analytics/summary${query}`);

  console.log('[analyticsService] Fetching summary:', url);

  const res = await fetch(url, {
    method: 'GET',
    headers: buildHeaders(),
    cache: 'no-store',
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Αποτυχία φόρτωσης στατιστικών: ${res.status}`);
  }

  const data = await res.json();
  console.log('[analyticsService] Summary loaded:', data);
  return data;
}

/**
 * Fetch chart-ready revenue grouped by day.
 *
 * @param {string|null} from - Start date YYYY-MM-DD (optional)
 * @param {string|null} to   - End date YYYY-MM-DD (optional)
 * @returns {Promise<Array<{date: string, revenue: number}>>}
 */
export async function getRevenuePerDay(from = null, to = null) {
  const params = new URLSearchParams();
  if (from) params.set('from', from);
  if (to) params.set('to', to);

  const query = params.toString() ? `?${params.toString()}` : '';
  const url = await buildHttpUrl(`/api/analytics/revenue-per-day${query}`);

  const res = await fetch(url, {
    method: 'GET',
    headers: buildHeaders(),
    cache: 'no-store',
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Αποτυχία φόρτωσης εσόδων ανά ημέρα: ${res.status}`);
  }

  return res.json();
}

/**
 * Fetch chart-ready revenue grouped by workstation.
 *
 * @param {string|null} from - Start date YYYY-MM-DD (optional)
 * @param {string|null} to   - End date YYYY-MM-DD (optional)
 * @returns {Promise<Array<{workstation: string, revenue: number}>>}
 */
export async function getRevenuePerWorkstation(from = null, to = null) {
  const params = new URLSearchParams();
  if (from) params.set('from', from);
  if (to) params.set('to', to);

  const query = params.toString() ? `?${params.toString()}` : '';
  const url = await buildHttpUrl(`/api/analytics/revenue-per-workstation${query}`);

  const res = await fetch(url, {
    method: 'GET',
    headers: buildHeaders(),
    cache: 'no-store',
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Αποτυχία φόρτωσης εσόδων ανά πόστο: ${res.status}`);
  }

  return res.json();
}

/**
 * Fetch order counts grouped by hour.
 *
 * @param {string|null} from - Start date YYYY-MM-DD (optional)
 * @param {string|null} to   - End date YYYY-MM-DD (optional)
 * @returns {Promise<Array<{hour: string, orders_count: number}>>}
 */
export async function getOrdersByHour(from = null, to = null) {
  const params = new URLSearchParams();
  if (from) params.set('from', from);
  if (to) params.set('to', to);

  const query = params.toString() ? `?${params.toString()}` : '';
  const url = await buildHttpUrl(`/api/analytics/orders-by-hour${query}`);

  const res = await fetch(url, {
    method: 'GET',
    headers: buildHeaders(),
    cache: 'no-store',
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Αποτυχία φόρτωσης παραγγελιών ανά ώρα: ${res.status}`);
  }

  return res.json();
}

/**
 * Fetch lowest-rotation items by quantity sold.
 *
 * @param {string|null} from - Start date YYYY-MM-DD (optional)
 * @param {string|null} to   - End date YYYY-MM-DD (optional)
 * @returns {Promise<Array<{item_name: string, qty_sold: number}>>}
 */
export async function getLowRotationItems(from = null, to = null) {
  const params = new URLSearchParams();
  if (from) params.set('from', from);
  if (to) params.set('to', to);

  const query = params.toString() ? `?${params.toString()}` : '';
  const url = await buildHttpUrl(`/api/analytics/low-rotation-items${query}`);

  const res = await fetch(url, {
    method: 'GET',
    headers: buildHeaders(),
    cache: 'no-store',
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Αποτυχία φόρτωσης ειδών χαμηλής κυκλοφορίας: ${res.status}`);
  }

  return res.json();
}
