/**
 * Menu Service - Abstraction layer for loading menu from backend API with fallback
 * 
 * Features:
 * - Attempts to load menu from backend POST /api/menu first
 * - Falls back to static menu.json from public folder on any error
 * - Caches result in localStorage to reduce API calls
 * - Provides clear error logging for debugging
 * - Works in both dev (localhost) and LAN environments
 */

import { getConfig } from './api';
import { getToken } from './authService';

// Cache key
const MENU_CACHE_KEY = 'tavern_menu_cache';
const CACHE_TIMESTAMP_KEY = 'tavern_menu_cache_time';
const CACHE_TTL_MINUTES = 60; // Cache for 1 hour

function buildHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  const token = getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

/**
 * Load menu from static JSON file in public folder
 * @returns {Promise<Object>} Menu object keyed by category
 */
export async function loadMenuFromFile() {
  console.log('[menuService] Loading menu from public/menu.json');
  try {
    const response = await fetch('/menu.json', { cache: 'no-store' });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status} loading menu.json`);
    }
    const menu = await response.json();
    console.log('[menuService] Loaded menu from file:', Object.keys(menu));
    return menu;
  } catch (error) {
    console.error('[menuService] Failed to load menu from file:', error);
    throw error;
  }
}

/**
 * Load menu from backend API
 * @returns {Promise<Object>} Menu object keyed by category
 */
export async function loadMenuFromAPI() {
  try {
    // Get backend config (handles localhost → LAN IP replacement)
    const config = await getConfig();
    
    const menuUrl = `${config.backend_base}/api/menu`;
    console.log('[menuService] Fetching menu from:', menuUrl);
    
    const response = await fetch(menuUrl, {
      method: 'GET',
      cache: 'no-store',
      headers: buildHeaders(),
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status} from backend API`);
    }
    
    const menu = await response.json();
    
    // Validate menu is an object with items
    if (!menu || typeof menu !== 'object' || Object.keys(menu).length === 0) {
      throw new Error('Menu API returned empty or invalid response');
    }
    
    console.log('[menuService] Loaded menu from API:', Object.keys(menu));
    return menu;
  } catch (error) {
    console.error('[menuService] Failed to load menu from API:', error);
    throw error;
  }
}

/**
 * Get available menu versions
 * @returns {Promise<Array>} Menu version list
 */
export async function getMenuVersions() {
  try {
    const config = await getConfig();
    const response = await fetch(`${config.backend_base}/api/menu/versions`, {
      method: 'GET',
      headers: buildHeaders(),
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch menu versions: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('[menuService] getMenuVersions error:', error);
    throw error;
  }
}

/**
 * Get menu for a specific version
 * @param {number} versionId - Menu version ID
 * @returns {Promise<Object>} Menu data
 */
export async function getMenuByVersion(versionId) {
  try {
    const config = await getConfig();
    const response = await fetch(`${config.backend_base}/api/menu/${versionId}`, {
      method: 'GET',
      headers: buildHeaders(),
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch menu version ${versionId}: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('[menuService] getMenuByVersion error:', error);
    throw error;
  }
}

/**
 * Create a new menu version from full menu data
 * @param {Object} menuData - Menu data blob
 * @returns {Promise<Object>} Version info
 */
export async function createMenuVersion(menuData) {
  try {
    const config = await getConfig();
    const response = await fetch(`${config.backend_base}/api/menu`, {
      method: 'POST',
      headers: buildHeaders(),
      body: JSON.stringify({ menu_dict: menuData }),
    });

    if (!response.ok) {
      throw new Error(`Failed to create menu version: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('[menuService] createMenuVersion error:', error);
    throw error;
  }
}

/**
 * Update a menu item (creates a new version on backend)
 * @param {string|number} itemId - Item ID
 * @param {Object} itemData - Updated item data
 * @returns {Promise<Object>} Updated item
 */
export async function updateMenuItem(itemId, itemData) {
  try {
    const config = await getConfig();
    const payload = {
      name: itemData?.name,
      price: itemData?.price,
      category: itemData?.category,
      station: itemData?.station || itemData?.category,
      extra_data: itemData?.extra_data || itemData?.metadata,
    };
    const response = await fetch(`${config.backend_base}/api/menu/item/${itemId}`, {
      method: 'PUT',
      headers: buildHeaders(),
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Failed to update menu item: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('[menuService] updateMenuItem error:', error);
    throw error;
  }
}

/**
 * Soft delete a menu item (creates a new version on backend)
 * @param {string|number} itemId - Item ID
 * @returns {Promise<Object>} Result
 */
export async function softDeleteMenuItem(itemId) {
  try {
    const config = await getConfig();
    const response = await fetch(`${config.backend_base}/api/menu/item/${itemId}`, {
      method: 'DELETE',
      headers: buildHeaders(),
    });

    if (!response.ok) {
      throw new Error(`Failed to delete menu item: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('[menuService] softDeleteMenuItem error:', error);
    throw error;
  }
}

/**
 * Get current active menu
 * @returns {Promise<Object>} Menu data
 */
export async function getCurrentMenu() {
  return await loadMenuFromAPI();
}

/**
 * Format a date/time for display
 * @param {string} dateStr - ISO date
 * @returns {string}
 */
export function formatDateTime(dateStr) {
  if (!dateStr) return '';
  try {
    return new Date(dateStr).toLocaleString('el-GR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateStr;
  }
}

/**
 * Check if cached menu is still valid
 * @returns {boolean} True if cache exists and is not expired
 */
function isCacheValid() {
  const cachedMenu = localStorage.getItem(MENU_CACHE_KEY);
  const cacheTime = localStorage.getItem(CACHE_TIMESTAMP_KEY);
  
  if (!cachedMenu || !cacheTime) {
    return false;
  }
  
  const ageMinutes = (Date.now() - parseInt(cacheTime)) / (1000 * 60);
  return ageMinutes < CACHE_TTL_MINUTES;
}

/**
 * Get cached menu
 * @returns {Object|null} Cached menu or null if expired/not found
 */
function getCachedMenu() {
  if (!isCacheValid()) {
    return null;
  }
  
  try {
    const cached = localStorage.getItem(MENU_CACHE_KEY);
    if (cached) {
      console.log('[menuService] Using cached menu');
      return JSON.parse(cached);
    }
  } catch (error) {
    console.error('[menuService] Failed to parse cached menu:', error);
  }
  
  return null;
}

/**
 * Save menu to cache
 * @param {Object} menu - Menu to cache
 */
function cacheMenu(menu) {
  try {
    localStorage.setItem(MENU_CACHE_KEY, JSON.stringify(menu));
    localStorage.setItem(CACHE_TIMESTAMP_KEY, Date.now().toString());
    console.log('[menuService] Cached menu');
  } catch (error) {
    console.error('[menuService] Failed to cache menu:', error);
    // Non-fatal: continue without caching
  }
}

/**
 * Clear cached menu
 */
export function clearMenuCache() {
  localStorage.removeItem(MENU_CACHE_KEY);
  localStorage.removeItem(CACHE_TIMESTAMP_KEY);
  console.log('[menuService] Cleared cached menu');
}

/**
 * Main function: Load menu with API-first strategy and fallback
 * 
 * Strategy:
 * 1. Return cached menu if valid
 * 2. Try to load from backend API first
 * 3. If API fails, fall back to public/menu.json
 * 4. Cache successful result
 * 
 * @param {Object} options - Load options
 * @param {boolean} options.forceRefresh - Skip cache and reload from source (default: false)
 * @returns {Promise<Object>} Menu object, success flag, and any errors
 * @returns {Object.menu} The menu object keyed by category
 * @returns {Object.success} True if menu loaded successfully
 * @returns {Object.source} Source of menu: 'cache', 'api', or 'file'
 * @returns {Object.apiError} Error message if API failed (will be null if loaded from cache/file)
 */
export async function getMenu(options = {}) {
  const { forceRefresh = false } = options;
  
  try {
    // Check cache first unless forced refresh
    if (!forceRefresh) {
      const cached = getCachedMenu();
      if (cached) {
        return { success: true, menu: cached, source: 'cache', apiError: null };
      }
    }
    
    // Try API first
    let apiError = null;
    try {
      const menu = await loadMenuFromAPI();
      cacheMenu(menu);
      return { success: true, menu, source: 'api', apiError: null };
    } catch (error) {
      apiError = error.message;
      console.warn('[menuService] API load failed, falling back to menu.json:', apiError);
    }
    
    // Fall back to file
    const menu = await loadMenuFromFile();
    cacheMenu(menu);
    return { success: true, menu, source: 'file', apiError };
    
  } catch (error) {
    console.error('[menuService] All menu sources failed:', error);
    return {
      success: false,
      menu: null,
      source: null,
      apiError: error.message,
      error: error.message
    };
  }
}

export default {
  getMenu,
  loadMenuFromAPI,
  loadMenuFromFile,
  clearMenuCache,
  getMenuVersions,
  getMenuByVersion,
  createMenuVersion,
  updateMenuItem,
  softDeleteMenuItem,
  getCurrentMenu,
  formatDateTime
};
