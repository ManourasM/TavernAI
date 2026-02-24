import { describe, it, expect, beforeEach, vi } from 'vitest';
import * as usersService from '../../src/services/usersService';
import * as api from '../../src/services/api';
import * as authService from '../../src/services/authService';

// Mock dependencies
vi.mock('../../src/services/api');
vi.mock('../../src/services/authService');

describe('Users Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  describe('listUsers', () => {
    it('makes GET request to /api/users with auth headers', async () => {
      const mockUsers = [
        { id: 1, username: 'user1', roles: ['admin'], created_at: '2026-02-24T10:00:00' },
      ];

      api.getConfig.mockResolvedValue({
        backend_base: 'http://localhost:8000',
      });
      authService.getToken.mockReturnValue('test-token');

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUsers,
      });

      const result = await usersService.listUsers();

      expect(result).toEqual(mockUsers);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/users',
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test-token',
          }),
        })
      );
    });

    it('throws error on API failure', async () => {
      api.getConfig.mockResolvedValue({
        backend_base: 'http://localhost:8000',
      });
      authService.getToken.mockReturnValue('test-token');

      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        text: async () => 'Unauthorized',
      });

      await expect(usersService.listUsers()).rejects.toThrow('Failed to list users: HTTP 401');
    });
  });

  describe('createUser', () => {
    it('makes POST request with user payload', async () => {
      const newUser = {
        id: 2,
        username: 'newuser',
        roles: ['waiter'],
        created_at: '2026-02-24T11:00:00',
      };

      api.getConfig.mockResolvedValue({
        backend_base: 'http://localhost:8000',
      });
      authService.getToken.mockReturnValue('test-token');

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => newUser,
      });

      const payload = { username: 'newuser', password: 'pass123', roles: ['waiter'] };
      const result = await usersService.createUser(payload);

      expect(result).toEqual(newUser);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/users',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test-token',
          }),
          body: JSON.stringify(payload),
        })
      );
    });

    it('validates username is provided', async () => {
      await expect(
        usersService.createUser({ password: 'pass', roles: [] })
      ).rejects.toThrow('Username and password are required');
    });

    it('validates password is provided', async () => {
      await expect(
        usersService.createUser({ username: 'user', roles: [] })
      ).rejects.toThrow('Username and password are required');
    });

    it('throws error on API failure', async () => {
      api.getConfig.mockResolvedValue({
        backend_base: 'http://localhost:8000',
      });
      authService.getToken.mockReturnValue('test-token');

      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 409,
        text: async () => JSON.stringify({ detail: 'username already exists' }),
      });

      const payload = { username: 'existing', password: 'pass123', roles: ['waiter'] };
      await expect(usersService.createUser(payload)).rejects.toThrow('Failed to create user');
    });
  });

  describe('updateUser', () => {
    it('makes PUT request with update payload', async () => {
      const updatedUser = {
        id: 1,
        username: 'user1',
        roles: ['admin', 'waiter'],
        created_at: '2026-02-24T10:00:00',
      };

      api.getConfig.mockResolvedValue({
        backend_base: 'http://localhost:8000',
      });
      authService.getToken.mockReturnValue('test-token');

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => updatedUser,
      });

      const payload = { roles: ['admin', 'waiter'] };
      const result = await usersService.updateUser(1, payload);

      expect(result).toEqual(updatedUser);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/users/1',
        expect.objectContaining({
          method: 'PUT',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test-token',
          }),
          body: JSON.stringify(payload),
        })
      );
    });

    it('throws error on API failure', async () => {
      api.getConfig.mockResolvedValue({
        backend_base: 'http://localhost:8000',
      });
      authService.getToken.mockReturnValue('test-token');

      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        text: async () => JSON.stringify({ detail: 'User not found' }),
      });

      await expect(usersService.updateUser(999, { roles: ['admin'] })).rejects.toThrow(
        'Failed to update user'
      );
    });
  });

  describe('deleteUser', () => {
    it('makes DELETE request to user endpoint', async () => {
      api.getConfig.mockResolvedValue({
        backend_base: 'http://localhost:8000',
      });
      authService.getToken.mockReturnValue('test-token');

      global.fetch.mockResolvedValueOnce({
        ok: true,
        text: async () => '',
      });

      await usersService.deleteUser(1);

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/users/1',
        expect.objectContaining({
          method: 'DELETE',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test-token',
          }),
        })
      );
    });

    it('throws error on API failure', async () => {
      api.getConfig.mockResolvedValue({
        backend_base: 'http://localhost:8000',
      });
      authService.getToken.mockReturnValue('test-token');

      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        text: async () => JSON.stringify({ detail: 'Cannot delete admin user' }),
      });

      await expect(usersService.deleteUser(1)).rejects.toThrow('Failed to delete user');
    });
  });

  it('handles requests without auth token', async () => {
    api.getConfig.mockResolvedValue({
      backend_base: 'http://localhost:8000',
    });
    authService.getToken.mockReturnValue(null);

    const mockUsers = [{ id: 1, username: 'user1', roles: ['admin'], created_at: '' }];
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockUsers,
    });

    const result = await usersService.listUsers();

    expect(result).toEqual(mockUsers);
    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/users',
      expect.objectContaining({
        headers: expect.not.objectContaining({
          'Authorization': expect.anything(),
        }),
      })
    );
  });
});
