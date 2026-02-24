/**
 * Users Service - Admin management of system users
 * 
 * Provides API abstraction for admin user CRUD operations:
 * - List all users
 * - Create new user
 * - Update user roles/password
 * - Delete user
 * 
 * All requests include auth token in Authorization header
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
 * @param {string} path - API path (e.g., '/api/users')
 * @returns {Promise<string>} Full URL
 */
async function buildHttpUrl(path) {
  const config = await getConfig();
  const base = config.backend_base || `${location.protocol}//${location.host}`;
  return `${base}${path}`;
}

/**
 * List all users (admin-only)
 * @returns {Promise<Array>} Array of user objects {id, username, roles, created_at}
 * @throws {Error} If API call fails
 */
export async function listUsers() {
  console.log('[usersService.listUsers] START');
  const url = await buildHttpUrl('/api/users');
  console.log('[usersService.listUsers] GET', url);
  
  const res = await fetch(url, {
    method: 'GET',
    headers: buildHeaders(),
  });
  
  if (!res.ok) {
    const errorText = await res.text();
    const error = new Error(`Failed to list users: HTTP ${res.status}`);
    error.status = res.status;
    error.detail = errorText;
    console.error('[usersService.listUsers] Error:', error);
    throw error;
  }
  
  const users = await res.json();
  console.log('[usersService.listUsers] Success, returned', users.length, 'users');
  return users;
}

/**
 * Create a new user (admin-only)
 * @param {Object} payload - User creation payload {username, password, roles}
 * @returns {Promise<Object>} Created user object {id, username, roles, created_at}
 * @throws {Error} If validation fails or user already exists
 */
export async function createUser(payload) {
  console.log('[usersService.createUser] START', { username: payload.username });
  
  if (!payload.username || !payload.password) {
    throw new Error('Username and password are required');
  }
  
  const url = await buildHttpUrl('/api/users');
  console.log('[usersService.createUser] POST', url, payload);
  
  const res = await fetch(url, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(payload),
  });
  
  if (!res.ok) {
    const errorText = await res.text();
    let detail = errorText;
    try {
      const errorJson = JSON.parse(errorText);
      detail = errorJson.detail || errorText;
    } catch { /* keep errorText */ }
    
    const error = new Error(`Failed to create user: ${detail}`);
    error.status = res.status;
    error.detail = detail;
    console.error('[usersService.createUser] Error:', error);
    throw error;
  }
  
  const user = await res.json();
  console.log('[usersService.createUser] Success, created user:', user.id);
  return user;
}

/**
 * Update user roles and/or password (admin-only)
 * @param {number} userId - User ID to update
 * @param {Object} payload - Update payload {roles?, password?}
 * @returns {Promise<Object>} Updated user object
 * @throws {Error} If user not found or update fails
 */
export async function updateUser(userId, payload) {
  console.log('[usersService.updateUser] START', { userId, payload });
  
  const url = await buildHttpUrl(`/api/users/${userId}`);
  console.log('[usersService.updateUser] PUT', url, payload);
  
  const res = await fetch(url, {
    method: 'PUT',
    headers: buildHeaders(),
    body: JSON.stringify(payload),
  });
  
  if (!res.ok) {
    const errorText = await res.text();
    let detail = errorText;
    try {
      const errorJson = JSON.parse(errorText);
      detail = errorJson.detail || errorText;
    } catch { /* keep errorText */ }
    
    const error = new Error(`Failed to update user: ${detail}`);
    error.status = res.status;
    error.detail = detail;
    console.error('[usersService.updateUser] Error:', error);
    throw error;
  }
  
  const user = await res.json();
  console.log('[usersService.updateUser] Success, updated user:', user.id);
  return user;
}

/**
 * Delete a user (admin-only)
 * @param {number} userId - User ID to delete
 * @returns {Promise<void>}
 * @throws {Error} If user not found or delete fails
 */
export async function deleteUser(userId) {
  console.log('[usersService.deleteUser] START', { userId });
  
  const url = await buildHttpUrl(`/api/users/${userId}`);
  console.log('[usersService.deleteUser] DELETE', url);
  
  const res = await fetch(url, {
    method: 'DELETE',
    headers: buildHeaders(),
  });
  
  if (!res.ok) {
    const errorText = await res.text();
    let detail = errorText;
    try {
      const errorJson = JSON.parse(errorText);
      detail = errorJson.detail || errorText;
    } catch { /* keep errorText */ }
    
    const error = new Error(`Failed to delete user: ${detail}`);
    error.status = res.status;
    error.detail = detail;
    console.error('[usersService.deleteUser] Error:', error);
    throw error;
  }
  
  console.log('[usersService.deleteUser] Success, deleted user:', userId);
}
