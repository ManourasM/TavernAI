import { describe, it, expect, beforeEach, vi } from 'vitest';
import * as workstationsService from '../../src/services/workstationsService';
import * as api from '../../src/services/api';
import * as authService from '../../src/services/authService';

// Mock dependencies
vi.mock('../../src/services/api');
vi.mock('../../src/services/authService');

describe('Workstations Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  describe('listWorkstations', () => {
    it('makes GET request to /api/workstations', async () => {
      const mockWorkstations = [
        { id: 1, name: 'Grill', slug: 'grill', created_at: '2026-02-24T10:00:00', active: true },
        { id: 2, name: 'Kitchen', slug: 'kitchen', created_at: '2026-02-24T10:15:00', active: true },
      ];

      api.getConfig.mockResolvedValue({
        backend_base: 'http://localhost:8000',
      });
      authService.getToken.mockReturnValue('test-token');

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockWorkstations,
      });

      const result = await workstationsService.listWorkstations();

      expect(result).toEqual(mockWorkstations);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/workstations',
        expect.objectContaining({
          method: 'GET',
        })
      );
    });

    it('throws error on API failure', async () => {
      api.getConfig.mockResolvedValue({
        backend_base: 'http://localhost:8000',
      });

      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: async () => 'Server error',
      });

      await expect(workstationsService.listWorkstations()).rejects.toThrow('Failed to list workstations');
    });
  });

  describe('getActiveCategories', () => {
    it('makes GET request to /api/workstations/active', async () => {
      const mockCategories = [
        { slug: 'grill', name: 'Grill' },
        { slug: 'kitchen', name: 'Kitchen' },
      ];

      api.getConfig.mockResolvedValue({
        backend_base: 'http://localhost:8000',
      });

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockCategories,
      });

      const result = await workstationsService.getActiveCategories();

      expect(result).toEqual(mockCategories);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/workstations/active',
        expect.objectContaining({
          method: 'GET',
        })
      );
    });

    it('returns empty array when no active workstations', async () => {
      api.getConfig.mockResolvedValue({
        backend_base: 'http://localhost:8000',
      });

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

      const result = await workstationsService.getActiveCategories();

      expect(result).toEqual([]);
    });
  });

  describe('createWorkstation', () => {
    it('makes POST request with workstation payload', async () => {
      const newWorkstation = {
        id: 3,
        name: 'Pastry',
        slug: 'pastry',
        created_at: '2026-02-24T11:00:00',
        active: true,
      };

      api.getConfig.mockResolvedValue({
        backend_base: 'http://localhost:8000',
      });
      authService.getToken.mockReturnValue('test-token');

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => newWorkstation,
      });

      const payload = { name: 'Pastry', slug: 'pastry' };
      const result = await workstationsService.createWorkstation(payload);

      expect(result).toEqual(newWorkstation);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/workstations',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-token',
          }),
          body: JSON.stringify(payload),
        })
      );
    });

    it('validates name is provided', async () => {
      await expect(
        workstationsService.createWorkstation({ name: '', slug: 'test' })
      ).rejects.toThrow('Name and slug are required');
    });

    it('validates slug is provided', async () => {
      await expect(
        workstationsService.createWorkstation({ name: 'Test', slug: '' })
      ).rejects.toThrow('Name and slug are required');
    });

    it('throws error on slug duplicate', async () => {
      api.getConfig.mockResolvedValue({
        backend_base: 'http://localhost:8000',
      });
      authService.getToken.mockReturnValue('test-token');

      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 409,
        text: async () => JSON.stringify({ detail: "Workstation with slug 'grill' already exists" }),
      });

      const payload = { name: 'Grill 2', slug: 'grill' };
      await expect(workstationsService.createWorkstation(payload)).rejects.toThrow();
    });
  });

  describe('updateWorkstation', () => {
    it('makes PUT request with update payload', async () => {
      const updatedWorkstation = {
        id: 1,
        name: 'BBQ Grill',
        slug: 'bbq',
        created_at: '2026-02-24T10:00:00',
        active: true,
      };

      api.getConfig.mockResolvedValue({
        backend_base: 'http://localhost:8000',
      });
      authService.getToken.mockReturnValue('test-token');

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => updatedWorkstation,
      });

      const payload = { name: 'BBQ Grill', slug: 'bbq' };
      const result = await workstationsService.updateWorkstation(1, payload);

      expect(result).toEqual(updatedWorkstation);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/workstations/1',
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify(payload),
        })
      );
    });

    it('validates workstation ID is provided', async () => {
      await expect(
        workstationsService.updateWorkstation(null, { name: 'Test' })
      ).rejects.toThrow('Workstation ID is required');
    });

    it('throws error on workstation not found', async () => {
      api.getConfig.mockResolvedValue({
        backend_base: 'http://localhost:8000',
      });
      authService.getToken.mockReturnValue('test-token');

      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        text: async () => JSON.stringify({ detail: 'Workstation 999 not found' }),
      });

      await expect(
        workstationsService.updateWorkstation(999, { name: 'Test' })
      ).rejects.toThrow();
    });

    it('can update active status', async () => {
      const deactivatedWorkstation = {
        id: 1,
        name: 'Grill',
        slug: 'grill',
        created_at: '2026-02-24T10:00:00',
        active: false,
      };

      api.getConfig.mockResolvedValue({
        backend_base: 'http://localhost:8000',
      });
      authService.getToken.mockReturnValue('test-token');

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => deactivatedWorkstation,
      });

      const result = await workstationsService.updateWorkstation(1, { active: false });

      expect(result.active).toBe(false);
    });
  });

  describe('deleteWorkstation', () => {
    it('makes DELETE request to workstation endpoint', async () => {
      api.getConfig.mockResolvedValue({
        backend_base: 'http://localhost:8000',
      });
      authService.getToken.mockReturnValue('test-token');

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'deleted', workstation_id: 1 }),
      });

      const result = await workstationsService.deleteWorkstation(1);

      expect(result.status).toBe('deleted');
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/workstations/1',
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });

    it('validates workstation ID is provided', async () => {
      await expect(
        workstationsService.deleteWorkstation(null)
      ).rejects.toThrow('Workstation ID is required');
    });

    it('throws error on workstation not found', async () => {
      api.getConfig.mockResolvedValue({
        backend_base: 'http://localhost:8000',
      });
      authService.getToken.mockReturnValue('test-token');

      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        text: async () => JSON.stringify({ detail: 'Workstation 999 not found' }),
      });

      await expect(
        workstationsService.deleteWorkstation(999)
      ).rejects.toThrow();
    });
  });

  describe('Error handling and recovery', () => {
    it('handles JSON parse errors gracefully', async () => {
      api.getConfig.mockResolvedValue({
        backend_base: 'http://localhost:8000',
      });
      authService.getToken.mockReturnValue('test-token');

      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: async () => 'Non-JSON error message',
      });

      await expect(
        workstationsService.createWorkstation({ name: 'Test', slug: 'test' })
      ).rejects.toThrow();
    });

    it('includes error details in exception', async () => {
      api.getConfig.mockResolvedValue({
        backend_base: 'http://localhost:8000',
      });

      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: async () => 'Server error',
      });

      try {
        await workstationsService.listWorkstations();
      } catch (err) {
        expect(err.status).toBe(500);
        expect(err.detail).toBe('Server error');
      }
    });
  });
});
