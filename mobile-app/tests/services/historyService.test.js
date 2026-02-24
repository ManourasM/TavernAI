// tests/services/historyService.test.js
// Unit tests for history service

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { fetchOrderHistory, fetchReceipt, formatDate, formatCurrency } from '../../src/services/historyService';

// Mock the API module
vi.mock('../../src/services/api.js', () => ({
  getConfig: vi.fn(() => Promise.resolve({
    backend_base: 'http://localhost:8000',
    ws_base: 'ws://localhost:8000',
    backend_port: 8000
  }))
}));

describe('historyService', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    vi.clearAllMocks();
    // Reset fetch mock
    global.fetch = vi.fn();
  });

  describe('fetchOrderHistory', () => {
    it('should fetch order history without filters', async () => {
      const mockData = [
        { id: '1', table: 1, total: 25.50, closed_at: '2026-02-23T10:00:00Z' },
        { id: '2', table: 2, total: 35.00, closed_at: '2026-02-23T11:00:00Z' }
      ];

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData
      });

      const result = await fetchOrderHistory();

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/orders/history',
        expect.objectContaining({
          method: 'GET',
          credentials: 'include'
        })
      );
      expect(result).toEqual(mockData);
    });

    it('should fetch order history with filters', async () => {
      const mockData = [
        { id: '1', table: 5, total: 45.00, closed_at: '2026-02-20T15:00:00Z' }
      ];

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData
      });

      const filters = {
        from: '2026-02-20',
        to: '2026-02-23',
        table: 5
      };

      const result = await fetchOrderHistory(filters);

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/orders/history?from=2026-02-20&to=2026-02-23&table=5',
        expect.objectContaining({
          method: 'GET',
          credentials: 'include'
        })
      );
      expect(result).toEqual(mockData);
    });

    it('should handle fetch errors', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error'
      });

      await expect(fetchOrderHistory()).rejects.toThrow('Failed to fetch order history: 500 Internal Server Error');
    });

    it('should handle network errors', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(fetchOrderHistory()).rejects.toThrow('Network error');
    });
  });

  describe('fetchReceipt', () => {
    it('should fetch a single receipt by ID', async () => {
      const mockReceipt = {
        id: 'receipt-123',
        table: 3,
        items: [
          { id: '1', name: 'Μουσακάς', price: 12.00, quantity: 2 },
          { id: '2', name: 'Σαλάτα', price: 5.00, quantity: 1 }
        ],
        total: 29.00,
        closed_at: '2026-02-23T12:30:00Z'
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockReceipt
      });

      const result = await fetchReceipt('receipt-123');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/orders/history/receipt-123',
        expect.objectContaining({
          method: 'GET',
          credentials: 'include'
        })
      );
      expect(result).toEqual(mockReceipt);
    });

    it('should handle receipt not found', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found'
      });

      await expect(fetchReceipt('invalid-id')).rejects.toThrow('Failed to fetch receipt: 404 Not Found');
    });

    it('should handle server errors', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error'
      });

      await expect(fetchReceipt('receipt-123')).rejects.toThrow('Failed to fetch receipt: 500 Internal Server Error');
    });
  });

  describe('formatDate', () => {
    it('should format ISO date string to Greek locale', () => {
      const isoDate = '2026-02-23T14:30:00Z';
      const formatted = formatDate(isoDate);
      
      // Check that it contains expected date parts
      expect(formatted).toMatch(/23/);
      expect(formatted).toMatch(/02/);
      expect(formatted).toMatch(/2026/);
    });

    it('should handle empty date string', () => {
      expect(formatDate('')).toBe('');
      expect(formatDate(null)).toBe('');
      expect(formatDate(undefined)).toBe('');
    });

    it('should format date with time', () => {
      const isoDate = '2026-02-23T14:30:00Z';
      const formatted = formatDate(isoDate);
      
      // Should include time components
      expect(formatted).toMatch(/:/);
    });
  });

  describe('formatCurrency', () => {
    it('should format number as Euro currency', () => {
      expect(formatCurrency(25.50)).toBe('€25.50');
      expect(formatCurrency(100)).toBe('€100.00');
      expect(formatCurrency(0.99)).toBe('€0.99');
    });

    it('should handle zero', () => {
      expect(formatCurrency(0)).toBe('€0.00');
    });

    it('should handle negative numbers', () => {
      expect(formatCurrency(-10.50)).toBe('€-10.50');
    });

    it('should handle non-number input', () => {
      expect(formatCurrency(null)).toBe('€0.00');
      expect(formatCurrency(undefined)).toBe('€0.00');
      expect(formatCurrency('invalid')).toBe('€0.00');
    });

    it('should round to 2 decimal places', () => {
      expect(formatCurrency(25.555)).toBe('€25.56');
      expect(formatCurrency(25.554)).toBe('€25.55');
    });
  });
});
