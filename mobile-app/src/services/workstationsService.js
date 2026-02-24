/**
 * Workstations Service - Admin management of kitchen workstations
 * 
 * Provides API abstraction for workstation CRUD operations:
 * - List all workstations (active and inactive)
 * - Get active workstation categories
 * - Create new workstation
 * - Update workstation properties
 * - Delete workstation (soft-delete via active=false)
 * 
 * All write requests include auth token in Authorization header
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
 * @param {string} path - API path (e.g., '/api/workstations')
 * @returns {Promise<string>} Full URL
 */
async function buildHttpUrl(path) {
  const config = await getConfig();
  const base = config.backend_base || `${location.protocol}//${location.host}`;
  return `${base}${path}`;
}

/**
 * List all workstations (active and inactive)
 * @returns {Promise<Array>} Array of workstation objects {id, name, slug, created_at, active}
 * @throws {Error} If API call fails
 */
export async function listWorkstations() {
  console.log('[workstationsService.listWorkstations] START');
  const url = await buildHttpUrl('/api/workstations');
  console.log('[workstationsService.listWorkstations] GET', url);
  
  const res = await fetch(url, {
    method: 'GET',
    headers: buildHeaders(),
  });
  
  if (!res.ok) {
    const errorText = await res.text();
    const error = new Error(`Failed to list workstations: HTTP ${res.status}`);
    error.status = res.status;
    error.detail = errorText;
    console.error('[workstationsService.listWorkstations] Error:', error);
    throw error;
  }
  
  const workstations = await res.json();
  console.log('[workstationsService.listWorkstations] Success, returned', workstations.length, 'workstations');
  return workstations;
}

/**
 * Get active workstation categories (slugs)
 * @returns {Promise<Array>} Array of {slug, name} objects for active workstations
 * @throws {Error} If API call fails
 */
export async function getActiveCategories() {
  console.log('[workstationsService.getActiveCategories] START');
  const url = await buildHttpUrl('/api/workstations/active');
  console.log('[workstationsService.getActiveCategories] GET', url);
  
  const res = await fetch(url, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });
  
  if (!res.ok) {
    const errorText = await res.text();
    const error = new Error(`Failed to get active categories: HTTP ${res.status}`);
    error.status = res.status;
    error.detail = errorText;
    console.error('[workstationsService.getActiveCategories] Error:', error);
    throw error;
  }
  
  const categories = await res.json();
  console.log('[workstationsService.getActiveCategories] Success, returned', categories.length, 'categories');
  return categories;
}

/**
 * Create a new workstation (admin-only)
 * @param {Object} payload - Workstation creation payload {name, slug}
 * @returns {Promise<Object>} Created workstation object {id, name, slug, created_at, active}
 * @throws {Error} If validation fails or slug already exists
 */
export async function createWorkstation(payload) {
  console.log('[workstationsService.createWorkstation] START', { name: payload.name, slug: payload.slug });
  
  if (!payload.name || !payload.slug) {
    throw new Error('Name and slug are required');
  }
  
  const url = await buildHttpUrl('/api/workstations');
  console.log('[workstationsService.createWorkstation] POST', url, payload);
  
  const res = await fetch(url, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(payload),
  });
  
  if (!res.ok) {
    const errorText = await res.text();
    let errorDetail = errorText;
    try {
      const json = JSON.parse(errorText);
      errorDetail = json.detail || errorText;
    } catch {}
    
    const error = new Error(`Failed to create workstation: ${errorDetail}`);
    error.status = res.status;
    error.detail = errorDetail;
    console.error('[workstationsService.createWorkstation] Error:', error);
    throw error;
  }
  
  const workstation = await res.json();
  console.log('[workstationsService.createWorkstation] Success, created workstation:', workstation.id);
  return workstation;
}

/**
 * Update a workstation (admin-only)
 * @param {number} workstationId - Workstation ID
 * @param {Object} payload - Update payload {name?, slug?, active?}
 * @returns {Promise<Object>} Updated workstation object
 * @throws {Error} If workstation not found or validation fails
 */
export async function updateWorkstation(workstationId, payload) {
  console.log('[workstationsService.updateWorkstation] START', { id: workstationId, payload });
  
  if (!workstationId) {
    throw new Error('Workstation ID is required');
  }
  
  const url = await buildHttpUrl(`/api/workstations/${workstationId}`);
  console.log('[workstationsService.updateWorkstation] PUT', url, payload);
  
  const res = await fetch(url, {
    method: 'PUT',
    headers: buildHeaders(),
    body: JSON.stringify(payload),
  });
  
  if (!res.ok) {
    const errorText = await res.text();
    let errorDetail = errorText;
    try {
      const json = JSON.parse(errorText);
      errorDetail = json.detail || errorText;
    } catch {}
    
    const error = new Error(`Failed to update workstation: ${errorDetail}`);
    error.status = res.status;
    error.detail = errorDetail;
    console.error('[workstationsService.updateWorkstation] Error:', error);
    throw error;
  }
  
  const workstation = await res.json();
  console.log('[workstationsService.updateWorkstation] Success, updated workstation:', workstation.id);
  return workstation;
}

/**
 * Delete a workstation (admin-only, soft-delete via active=false)
 * @param {number} workstationId - Workstation ID
 * @returns {Promise<Object>} Deletion response {status: 'deleted', workstation_id, message}
 * @throws {Error} If workstation not found
 */
export async function deleteWorkstation(workstationId) {
  console.log('[workstationsService.deleteWorkstation] START', { id: workstationId });
  
  if (!workstationId) {
    throw new Error('Workstation ID is required');
  }
  
  const url = await buildHttpUrl(`/api/workstations/${workstationId}`);
  console.log('[workstationsService.deleteWorkstation] DELETE', url);
  
  const res = await fetch(url, {
    method: 'DELETE',
    headers: buildHeaders(),
  });
  
  if (!res.ok) {
    const errorText = await res.text();
    let errorDetail = errorText;
    try {
      const json = JSON.parse(errorText);
      errorDetail = json.detail || errorText;
    } catch {}
    
    const error = new Error(`Failed to delete workstation: ${errorDetail}`);
    error.status = res.status;
    error.detail = errorDetail;
    console.error('[workstationsService.deleteWorkstation] Error:', error);
    throw error;
  }
  
  const result = await res.json();
  console.log('[workstationsService.deleteWorkstation] Success, deleted workstation:', workstationId);
  return result;
}
