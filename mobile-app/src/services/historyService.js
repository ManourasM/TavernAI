// src/services/historyService.js
// Service for fetching order history and receipts

import { getConfig } from './api.js';

/**
 * Fetch order history with optional filters
 * @param {Object} filters - { from: 'YYYY-MM-DD', to: 'YYYY-MM-DD', table: number }
 * @returns {Promise<Array>} Array of historical orders/receipts
 */
export async function fetchOrderHistory(filters = {}) {
  const cfg = await getConfig();
  const params = new URLSearchParams();
  
  if (filters.from) params.append('from', filters.from);
  if (filters.to) params.append('to', filters.to);
  if (filters.table) params.append('table', filters.table);
  
  const url = `${cfg.backend_base}/api/orders/history${params.toString() ? '?' + params.toString() : ''}`;
  
  console.log('[historyService] Fetching history from:', url);
  
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch order history: ${response.status} ${response.statusText}`);
  }
  
  return await response.json();
}

/**
 * Fetch a single receipt by ID
 * @param {string|number} receiptId - The receipt/order ID
 * @returns {Promise<Object>} Receipt details
 */
export async function fetchReceipt(receiptId) {
  const cfg = await getConfig();
  const url = `${cfg.backend_base}/api/orders/history/${receiptId}`;
  
  console.log('[historyService] Fetching receipt:', url);
  
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch receipt: ${response.status} ${response.statusText}`);
  }
  
  return await response.json();
}

/**
 * Format date for display
 * @param {string} dateStr - ISO date string
 * @returns {string} Formatted date
 */
export function formatDate(dateStr) {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return date.toLocaleDateString('el-GR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
}

/**
 * Format currency for display
 * @param {number} amount - Amount in euros
 * @returns {string} Formatted currency
 */
export function formatCurrency(amount) {
  if (typeof amount !== 'number') return '€0.00';
  return `€${amount.toFixed(2)}`;
}
