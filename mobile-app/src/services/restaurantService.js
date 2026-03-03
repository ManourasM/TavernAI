/**
 * Restaurant Service - Admin management of restaurant profile
 * 
 * Provides API abstraction for restaurant profile operations:
 * - Get restaurant profile (auto-creates default from env)
 * - Update restaurant profile (admin-only)
 * 
 * Profile includes: name, phone, address, extra_details
 */

import { getConfig } from './api';
import { getToken } from './authService';

/**
 * Build auth headers with JWT token
 * @returns {Object} Headers object with Authorization if token exists
 */
function buildHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  const token = getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

/**
 * Build full HTTP URL for a given API path
 * @param {string} path - API path (e.g., '/api/restaurant')
 * @returns {Promise<string>} Full URL
 */
async function buildHttpUrl(path) {
  const config = await getConfig();
  const base = config.backend_base || `${location.protocol}//${location.host}`;
  return `${base}${path}`;
}

/**
 * Get restaurant profile
 * 
 * Returns existing profile or creates default one if none exists.
 * Default values sourced from environment variables:
 * - RESTAURANT_NAME (fallback: "My Taverna")
 * - RESTAURANT_PHONE (optional)
 * - RESTAURANT_ADDRESS (optional)
 * 
 * @returns {Promise<Object>} Profile object {id, restaurant_id, name, phone, address, extra_details, updated_at}
 * @throws {Error} If API call fails
 */
export async function getProfile() {
  console.log('[restaurantService.getProfile] START');
  const url = await buildHttpUrl('/api/restaurant');
  console.log('[restaurantService.getProfile] GET', url);
  
  const res = await fetch(url, {
    method: 'GET',
    headers: buildHeaders(),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch profile: ${res.status}`);
  }

  const profile = await res.json();
  console.log('[restaurantService.getProfile] SUCCESS:', profile);
  return profile;
}

/**
 * Update restaurant profile (admin-only)
 * 
 * Updates restaurant name, phone, address, and extra_details.
 * All fields are optional; only provided fields are updated.
 * 
 * @param {Object} payload - Update payload: {name?, phone?, address?, extra_details?}
 * @returns {Promise<Object>} Updated profile object
 * @throws {Error} If API call fails or user not admin
 */
export async function updateProfile(payload) {
  console.log('[restaurantService.updateProfile] START', payload);
  const url = await buildHttpUrl('/api/restaurant');
  console.log('[restaurantService.updateProfile] PUT', url);

  const res = await fetch(url, {
    method: 'PUT',
    headers: buildHeaders(),
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail || `Failed to update profile: ${res.status}`;
    console.error('[restaurantService.updateProfile] FAILED:', message);
    throw new Error(message);
  }

  const updatedProfile = await res.json();
  console.log('[restaurantService.updateProfile] SUCCESS:', updatedProfile);
  return updatedProfile;
}
