/**
 * Authentication Service
 * 
 * Handles all auth-related operations:
 * - Login/Signup via backend API
 * - JWT token storage and retrieval
 * - Token injection into API calls
 * - Bootstrap detection (check if signup is allowed)
 * 
 * Token Storage Strategy:
 * - localStorage: Persist across page reloads
 * - Also stores in memory for current session
 */

import { getConfig } from './api';

const TOKEN_KEY = 'tavern_auth_token';
const USER_KEY = 'tavern_auth_user';
const BOOTSTRAP_KEY = 'tavern_bootstrap_checked';

/**
 * Get stored JWT token from localStorage
 * @returns {string|null} JWT token or null if not found
 */
export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch (error) {
    console.error('[authService] Failed to read token from localStorage:', error);
    return null;
  }
}

/**
 * Store JWT token in localStorage
 * @param {string} token - JWT token to store
 */
export function setToken(token) {
  try {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  } catch (error) {
    console.error('[authService] Failed to store token in localStorage:', error);
  }
}

/**
 * Clear stored JWT token
 */
export function clearToken() {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(BOOTSTRAP_KEY);
  } catch (error) {
    console.error('[authService] Failed to clear token:', error);
  }
}

/**
 * Get current user info from localStorage
 * @returns {Object|null} User object or null if not logged in
 */
export function getCurrentUser() {
  try {
    const user = localStorage.getItem(USER_KEY);
    return user ? JSON.parse(user) : null;
  } catch (error) {
    console.error('[authService] Failed to parse user from localStorage:', error);
    return null;
  }
}

/**
 * Store user info in localStorage
 * @param {Object} user - User object to store
 */
function setCurrentUser(user) {
  try {
    if (user) {
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(USER_KEY);
    }
  } catch (error) {
    console.error('[authService] Failed to store user in localStorage:', error);
  }
}

/**
 * Decode JWT token to extract user info (without verification - frontend only)
 * Note: This decodes the token but does NOT verify the signature.
 * Signature verification must happen on the backend.
 * 
 * @param {string} token - JWT token to decode
 * @returns {Object|null} Decoded token payload or null if invalid
 */
function decodeToken(token) {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) {
      return null;
    }
    
    // Decode base64url (replace URL-safe chars, add padding)
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64 + '=='.substring(0, (4 - base64.length % 4) % 4);
    const json = atob(padded);
    
    return JSON.parse(json);
  } catch (error) {
    console.error('[authService] Failed to decode token:', error);
    return null;
  }
}

/**
 * Check if token is valid (not expired)
 * @param {string|null} token - JWT token to check
 * @returns {boolean} True if token exists and not expired
 */
export function isTokenValid(token = null) {
  const checkToken = token || getToken();
  if (!checkToken) return false;
  
  const decoded = decodeToken(checkToken);
  if (!decoded || !decoded.exp) return false;
  
  // exp is in seconds, convert to milliseconds
  const expiresAt = decoded.exp * 1000;
  return Date.now() < expiresAt;
}

/**
 * Login with username and password
 * 
 * @param {string} username - Username
 * @param {string} password - Password
 * @returns {Promise<Object>} { success, token, user?, error? }
 */
export async function login(username, password) {
  try {
    const config = await getConfig();
    const url = `${config.backend_base}/api/auth/login`;
    
    console.log('[authService] Logging in:', username);
    
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
      cache: 'no-store'
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      const detail = error.detail || 'Invalid credentials';
      console.error('[authService] Login failed:', detail);
      return { success: false, error: detail };
    }
    
    const data = await response.json();
    const token = data.access_token;
    
    if (!token) {
      console.error('[authService] No token in response');
      return { success: false, error: 'No token in response' };
    }
    
    // Decode token to get user info (frontend only - no verification)
    const decoded = decodeToken(token);
    const user = {
      id: decoded?.sub,
      roles: decoded?.roles || [],
      username
    };
    
    // Store token and user
    setToken(token);
    setCurrentUser(user);
    
    console.log('[authService] Login successful:', username);
    return { success: true, token, user };
    
  } catch (error) {
    console.error('[authService] Login error:', error.message);
    return { success: false, error: error.message };
  }
}

/**
 * Signup a new user (only in bootstrap mode)
 * 
 * @param {string} username - Username
 * @param {string} password - Password
 * @returns {Promise<Object>} { success, user?, error? }
 */
export async function signup(username, password) {
  try {
    const config = await getConfig();
    const url = `${config.backend_base}/api/auth/signup`;
    
    console.log('[authService] Signing up:', username);
    
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        username, 
        password,
        roles: ['admin']  // First user is admin by default
      }),
      cache: 'no-store'
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      const detail = error.detail || 'Signup failed';
      console.error('[authService] Signup failed:', detail);
      return { success: false, error: detail };
    }
    
    const data = await response.json();
    const user = {
      id: data.id,
      username: data.username,
      roles: data.roles || ['admin']
    };
    
    console.log('[authService] Signup successful:', username);
    return { success: true, user };
    
  } catch (error) {
    console.error('[authService] Signup error:', error.message);
    return { success: false, error: error.message };
  }
}

/**
 * Check if bootstrap mode is active (no users exist yet)
 * This allows first-time signup without existing credentials.
 * 
 * @returns {Promise<Object>} { needsBootstrap, error? }
 */
export async function checkBootstrapMode() {
  try {
    const config = await getConfig();
    
    // Try to check if bootstrap is needed via a special endpoint
    const url = `${config.backend_base}/api/auth/bootstrap`;
    
    const response = await fetch(url, {
      method: 'GET',
      cache: 'no-store'
    });
    
    if (response.ok) {
      const data = await response.json();
      console.log('[authService] Bootstrap check:', data.needs_bootstrap);
      return { needsBootstrap: data.needs_bootstrap, error: null };
    }
    
    // Fallback: Assume no bootstrap if endpoint doesn't exist
    // In production, configure via environment variable
    const allowBootstrap = localStorage.getItem(BOOTSTRAP_KEY) !== 'false';
    return { needsBootstrap: allowBootstrap, error: null };
    
  } catch (error) {
    console.warn('[authService] Bootstrap check error, defaulting to allow:', error.message);
    // Default to allowing signup for first-time users
    return { needsBootstrap: true, error: null };
  }
}

/**
 * Logout current user
 */
export function logout() {
  console.log('[authService] Logging out');
  clearToken();
  setCurrentUser(null);
}

/**
 * Get Authorization header for API requests
 * @returns {Object|null} { Authorization: "Bearer <token>" } or null if no token
 */
export function getAuthHeader() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : null;
}

/**
 * Verify token with backend (optional: call to validate token is still valid)
 * @returns {Promise<Object>} { valid, user?, error? }
 */
export async function verifyToken() {
  try {
    const token = getToken();
    if (!token) {
      return { valid: false, error: 'No token found' };
    }
    
    // Check expiration client-side first
    if (!isTokenValid(token)) {
      clearToken();
      return { valid: false, error: 'Token expired' };
    }
    
    // Could call backend to verify, but not necessary for MVP
    // Backend will validate when we use the token in protected endpoints
    
    const user = getCurrentUser();
    return { valid: true, user };
    
  } catch (error) {
    console.error('[authService] Token verification error:', error);
    return { valid: false, error: error.message };
  }
}

export default {
  login,
  signup,
  logout,
  getToken,
  setToken,
  clearToken,
  getCurrentUser,
  isTokenValid,
  getAuthHeader,
  checkBootstrapMode,
  verifyToken
};
