/**
 * Menu Service - Abstraction layer for loading menu from backend API with fallback
 * 
 * Features:
 * - Attempts to load menu from backend GET /api/menu first
 * - Falls back to static menu.json from public folder on any error
 * - Caches result in sessionStorage for the session
 * - Provides clear error logging for debugging
 * - Works in both dev (localhost) and LAN environments
 */

import { getConfig } from './api';

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
      headers: { 'Content-Type': 'application/json' }
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
 * Main function: Load menu with API-first strategy and fallback
 * 
 * Strategy:
 * 1. Try to load from backend API first
 * 2. If API fails, fall back to public/menu.json
 * 3. Cache successful result in sessionStorage for the session
 * 
 * @param {Object} options - Load options
 * @param {boolean} options.skipCache - Skip session cache (default: false)
 * @returns {Promise<Object>} Menu object, success flag, and metadata
 * @returns {Object.menu} The menu object keyed by category
 * @returns {Object.success} True if menu loaded successfully
 * @returns {Object.source} Source of menu: 'cache', 'api', or 'file'
 * @returns {Object.apiError} Error message if API failed (null if loaded from cache/file)
 */
export async function getMenu(options = {}) {
  const { skipCache = false } = options;
  const CACHE_KEY = 'tavern_menu_session_cache';
  
  try {
    // Check session cache first unless explicitly skipped
    if (!skipCache) {
      const cached = sessionStorage.getItem(CACHE_KEY);
      if (cached) {
        try {
          const menu = JSON.parse(cached);
          console.log('[menuService] Using session cache');
          return { success: true, menu, source: 'cache', apiError: null };
        } catch (e) {
          console.warn('[menuService] Failed to parse cached menu, proceeding to fetch');
        }
      }
    }
    
    // Try API first
    let apiError = null;
    try {
      const menu = await loadMenuFromAPI();
      // Cache successful result
      try {
        sessionStorage.setItem(CACHE_KEY, JSON.stringify(menu));
      } catch (e) {
        console.warn('[menuService] Failed to cache menu in sessionStorage');
      }
      return { success: true, menu, source: 'api', apiError: null };
    } catch (error) {
      apiError = error.message;
      console.warn('[menuService] API load failed, falling back to menu.json:', apiError);
    }
    
    // Fall back to file
    const menu = await loadMenuFromFile();
    // Cache successful result
    try {
      sessionStorage.setItem(CACHE_KEY, JSON.stringify(menu));
    } catch (e) {
      console.warn('[menuService] Failed to cache menu in sessionStorage');
    }
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
  loadMenuFromFile
};
