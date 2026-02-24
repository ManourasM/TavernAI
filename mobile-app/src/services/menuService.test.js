/**
 * Unit tests for menuService.js
 * 
 * Tests cover:
 * - Loading menu from API (success and error cases)
 * - Loading menu from file (success and error cases)
 * - Fallback logic when API fails
 * - Session caching behavior
 * - Force refresh behavior
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import * as menuService from './menuService';

// Mock API configuration
const mockConfig = {
  backend_base: 'http://localhost:8000',
  ws_base: 'ws://localhost:8000',
  backend_port: 8000
};

// Mock menu data
const mockMenu = {
  'Salads': [
    { id: 'salads_01', name: 'Greek Salad', price: 9.5, category: 'kitchen' }
  ],
  'Appetizers': [
    { id: 'appetizers_01', name: 'Fries', price: 5.0, category: 'kitchen' }
  ]
};

// Mock the api module
vi.mock('./api', () => ({
  getConfig: vi.fn(async () => mockConfig)
}));

describe('menuService', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    vi.clearAllMocks();
    // Clear sessionStorage
    sessionStorage.clear();
    // Clear global fetch mock
    global.fetch = vi.fn();
  });

  afterEach(() => {
    sessionStorage.clear();
  });

  describe('loadMenuFromFile', () => {
    it('should load menu from public/menu.json successfully', async () => {
      global.fetch = vi.fn(async () => ({
        ok: true,
        json: async () => mockMenu
      }));

      const result = await menuService.loadMenuFromFile();

      expect(global.fetch).toHaveBeenCalledWith('/menu.json', { cache: 'no-store' });
      expect(result).toEqual(mockMenu);
    });

    it('should throw error when menu.json is not found', async () => {
      global.fetch = vi.fn(async () => ({
        ok: false,
        status: 404
      }));

      await expect(menuService.loadMenuFromFile()).rejects.toThrow('HTTP 404');
    });

    it('should throw error on network failure', async () => {
      global.fetch = vi.fn(async () => {
        throw new Error('Network error');
      });

      await expect(menuService.loadMenuFromFile()).rejects.toThrow('Network error');
    });
  });

  describe('loadMenuFromAPI', () => {
    it('should load menu from backend API successfully', async () => {
      global.fetch = vi.fn(async () => ({
        ok: true,
        json: async () => mockMenu
      }));

      const result = await menuService.loadMenuFromAPI();

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/menu',
        expect.objectContaining({
          method: 'GET',
          cache: 'no-store'
        })
      );
      expect(result).toEqual(mockMenu);
    });

    it('should throw error when API returns non-200 status', async () => {
      global.fetch = vi.fn(async () => ({
        ok: false,
        status: 500
      }));

      await expect(menuService.loadMenuFromAPI()).rejects.toThrow('HTTP 500');
    });

    it('should throw error when API returns empty menu', async () => {
      global.fetch = vi.fn(async () => ({
        ok: true,
        json: async () => ({})
      }));

      await expect(menuService.loadMenuFromAPI()).rejects.toThrow('empty or invalid');
    });

    it('should throw error when API returns null', async () => {
      global.fetch = vi.fn(async () => ({
        ok: true,
        json: async () => null
      }));

      await expect(menuService.loadMenuFromAPI()).rejects.toThrow('empty or invalid');
    });

    it('should throw error on network failure', async () => {
      global.fetch = vi.fn(async () => {
        throw new Error('Network timeout');
      });

      await expect(menuService.loadMenuFromAPI()).rejects.toThrow('Network timeout');
    });
  });

  describe('getMenu', () => {
    it('should load menu from API and cache it', async () => {
      global.fetch = vi.fn(async () => ({
        ok: true,
        json: async () => mockMenu
      }));

      const result = await menuService.getMenu();

      expect(result.success).toBe(true);
      expect(result.menu).toEqual(mockMenu);
      expect(result.source).toBe('api');
      expect(result.apiError).toBeNull();

      // Check cache was set
      const cached = sessionStorage.getItem('tavern_menu_session_cache');
      expect(cached).toBe(JSON.stringify(mockMenu));
    });

    it('should return cached menu on second call', async () => {
      global.fetch = vi.fn(async () => ({
        ok: true,
        json: async () => mockMenu
      }));

      // First call
      await menuService.getMenu();
      // Reset mock to verify it's not called again
      global.fetch.mockClear();

      // Second call
      const result = await menuService.getMenu();

      expect(result.success).toBe(true);
      expect(result.menu).toEqual(mockMenu);
      expect(result.source).toBe('cache');
      // Fetch should not have been called
      expect(global.fetch).not.toHaveBeenCalled();
    });

    it('should skip cache when skipCache option is true', async () => {
      global.fetch = vi.fn(async () => ({
        ok: true,
        json: async () => mockMenu
      }));

      // First call to populate cache
      await menuService.getMenu();
      global.fetch.mockClear();

      // Second call with skipCache
      const result = await menuService.getMenu({ skipCache: true });

      expect(result.source).toBe('api');
      expect(global.fetch).toHaveBeenCalled();
    });

    it('should fall back to file when API fails', async () => {
      // Mock API failure
      global.fetch = vi.fn()
        .mockRejectedValueOnce(new Error('API unavailable'))
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockMenu
        });

      const result = await menuService.getMenu();

      expect(result.success).toBe(true);
      expect(result.menu).toEqual(mockMenu);
      expect(result.source).toBe('file');
      expect(result.apiError).toContain('API unavailable');
    });

    it('should fail when both API and file sources fail', async () => {
      global.fetch = vi.fn()
        .mockRejectedValueOnce(new Error('API unavailable'))
        .mockRejectedValueOnce(new Error('File not found'));

      const result = await menuService.getMenu();

      expect(result.success).toBe(false);
      expect(result.menu).toBeNull();
      expect(result.source).toBeNull();
      expect(result.apiError).toContain('API unavailable');
      expect(result.error).toContain('File not found');
    });

    it('should handle corrupted cache gracefully', async () => {
      // Set corrupted cache
      sessionStorage.setItem('tavern_menu_session_cache', 'not-valid-json{');

      global.fetch = vi.fn(async () => ({
        ok: true,
        json: async () => mockMenu
      }));

      const result = await menuService.getMenu();

      expect(result.success).toBe(true);
      expect(result.menu).toEqual(mockMenu);
      expect(result.source).toBe('api');
    });

    it('should handle sessionStorage errors gracefully', async () => {
      // Mock sessionStorage to throw
      const setItemError = new Error('QuotaExceededError');
      vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
        throw setItemError;
      });

      global.fetch = vi.fn(async () => ({
        ok: true,
        json: async () => mockMenu
      }));

      const result = await menuService.getMenu();

      expect(result.success).toBe(true);
      expect(result.menu).toEqual(mockMenu);
      // Should succeed even if caching fails
    });
  });

  describe('Integration scenarios', () => {
    it('should handle LAN IP replacement from getConfig', async () => {
      const { getConfig } = await import('./api');
      const lanConfig = {
        backend_base: 'http://192.168.1.100:8000',
        ws_base: 'ws://192.168.1.100:8000',
        backend_port: 8000
      };
      getConfig.mockResolvedValueOnce(lanConfig);

      global.fetch = vi.fn(async () => ({
        ok: true,
        json: async () => mockMenu
      }));

      await menuService.loadMenuFromAPI();

      expect(global.fetch).toHaveBeenCalledWith(
        'http://192.168.1.100:8000/api/menu',
        expect.any(Object)
      );
    });

    it('should prefer API over file when both are available', async () => {
      global.fetch = vi.fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockMenu
        });

      const result = await menuService.getMenu();

      expect(result.source).toBe('api');
      expect(result.apiError).toBeNull();
      // Should only call fetch once (for API, not file)
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    it('should include diagnostic info in response', async () => {
      global.fetch = vi.fn(async () => ({
        ok: true,
        json: async () => mockMenu
      }));

      const result = await menuService.getMenu();

      expect(result).toHaveProperty('success');
      expect(result).toHaveProperty('menu');
      expect(result).toHaveProperty('source');
      expect(result).toHaveProperty('apiError');
    });
  });

  describe('Error messages', () => {
    it('should provide clear error message for API failures', async () => {
      global.fetch = vi.fn(async () => ({
        ok: false,
        status: 503
      }));

      const result = await menuService.getMenu();

      expect(result.apiError).toContain('503');
      expect(result.source).toBe('file');
    });

    it('should log errors to console for debugging', async () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

      global.fetch = vi.fn()
        .mockRejectedValueOnce(new Error('API error'))
        .mockRejectedValueOnce(new Error('File error'));

      await menuService.getMenu();

      expect(consoleError).toHaveBeenCalled();
      consoleError.mockRestore();
    });
  });
});
