import { describe, it, expect, beforeEach, vi } from 'vitest';
import * as restaurantService from '../../services/restaurantService';
import * as api from '../../services/api';
import * as authService from '../../services/authService';

// Mock the api and authService modules
vi.mock('../../services/api');
vi.mock('../../services/authService');

describe('Restaurant Service', () => {
  const mockProfile = {
    id: 1,
    restaurant_id: 'default',
    name: 'Ταβέρνα Γιάννη',
    phone: '+30 210 123 4567',
    address: 'Οδός Παναίας 42, Αθήνα',
    extra_details: {
      website: 'https://taverna-gianni.gr',
      afm: '123456789',
    },
    updated_at: '2026-02-23T10:00:00',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    api.getConfig.mockResolvedValue({
      backend_base: 'http://localhost:8000',
    });
    authService.getToken.mockReturnValue('test-token-123');
  });

  describe('getProfile', () => {
    it('fetches restaurant profile from API', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockProfile),
        })
      );

      const result = await restaurantService.getProfile();

      expect(result).toEqual(mockProfile);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/restaurant',
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test-token-123',
          }),
        })
      );
    });

    it('includes auth token in request headers', async () => {
      authService.getToken.mockReturnValueOnce('my-auth-token');
      
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockProfile),
        })
      );

      await restaurantService.getProfile();

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer my-auth-token',
          }),
        })
      );
    });

    it('handles API errors gracefully', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 404,
          json: () => Promise.resolve({ detail: 'Profile not found' }),
        })
      );

      await expect(restaurantService.getProfile()).rejects.toThrow('Profile not found');
    });

    it('handles network errors', async () => {
      global.fetch = vi.fn(() =>
        Promise.reject(new Error('Network timeout'))
      );

      await expect(restaurantService.getProfile()).rejects.toThrow('Network timeout');
    });

    it('returns default profile structure', async () => {
      const minimalProfile = {
        id: 1,
        restaurant_id: 'default',
        name: 'My Taverna',
        phone: null,
        address: null,
        extra_details: null,
        updated_at: '2026-02-23T10:00:00',
      };

      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(minimalProfile),
        })
      );

      const result = await restaurantService.getProfile();

      expect(result.name).toBe('My Taverna');
      expect(result.phone).toBeNull();
      expect(result.address).toBeNull();
    });
  });

  describe('updateProfile', () => {
    it('sends PUT request with updated profile data', async () => {
      const updatePayload = {
        name: 'Updated Taverna',
        phone: '+30 210 987 6543',
        address: 'New Address 99',
      };

      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            ...mockProfile,
            ...updatePayload,
          }),
        })
      );

      const result = await restaurantService.updateProfile(updatePayload);

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/restaurant',
        expect.objectContaining({
          method: 'PUT',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test-token-123',
          }),
          body: JSON.stringify(updatePayload),
        })
      );

      expect(result.name).toBe('Updated Taverna');
    });

    it('handles partial profile updates', async () => {
      const partialPayload = {
        name: 'Just Name Change',
      };

      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            ...mockProfile,
            name: 'Just Name Change',
          }),
        })
      );

      const result = await restaurantService.updateProfile(partialPayload);

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify(partialPayload),
        })
      );

      expect(result.name).toBe('Just Name Change');
    });

    it('sends JSON extra_details correctly', async () => {
      const updatePayload = {
        name: 'Taverna',
        extra_details: {
          website: 'https://example.com',
          afm: '123456789',
          logo: 'https://example.com/logo.png',
        },
      };

      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            ...mockProfile,
            ...updatePayload,
          }),
        })
      );

      await restaurantService.updateProfile(updatePayload);

      const callArgs = global.fetch.mock.calls[0];
      const sentBody = JSON.parse(callArgs[1].body);
      
      expect(sentBody.extra_details).toEqual(updatePayload.extra_details);
    });

    it('requires admin authentication (401 error handling)', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 401,
          json: () => Promise.resolve({ detail: 'Unauthorized' }),
        })
      );

      await expect(
        restaurantService.updateProfile({ name: 'New Name' })
      ).rejects.toThrow('Unauthorized');
    });

    it('handles validation errors from API', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 422,
          json: () => Promise.resolve({
            detail: 'Invalid phone number format',
          }),
        })
      );

      await expect(
        restaurantService.updateProfile({ phone: 'invalid' })
      ).rejects.toThrow('Invalid phone number format');
    });

    it('handles network errors during update', async () => {
      global.fetch = vi.fn(() =>
        Promise.reject(new Error('Connection refused'))
      );

      await expect(
        restaurantService.updateProfile({ name: 'New Name' })
      ).rejects.toThrow('Connection refused');
    });

    it('handles null/empty extra_details correctly', async () => {
      const updatePayload = {
        name: 'Taverna',
        extra_details: null,
      };

      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            ...mockProfile,
            ...updatePayload,
          }),
        })
      );

      await restaurantService.updateProfile(updatePayload);

      const callArgs = global.fetch.mock.calls[0];
      const sentBody = JSON.parse(callArgs[1].body);
      
      expect(sentBody.extra_details).toBeNull();
    });
  });

  describe('Header Building', () => {
    it('does not include Authorization header when no token', async () => {
      authService.getToken.mockReturnValueOnce(null);

      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockProfile),
        })
      );

      await restaurantService.getProfile();

      const callArgs = global.fetch.mock.calls[0];
      const headers = callArgs[1].headers;
      
      expect(headers.Authorization).toBeUndefined();
      expect(headers['Content-Type']).toBe('application/json');
    });
  });
});
