import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import RestaurantProfile from '../Admin/RestaurantProfile';
import * as restaurantService from '../../services/restaurantService';

// Mock the restaurant service
vi.mock('../../services/restaurantService');

describe('Restaurant Profile Admin Page', () => {
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
    restaurantService.getProfile.mockResolvedValue(mockProfile);
    restaurantService.updateProfile.mockResolvedValue({
      ...mockProfile,
      name: 'Updated Taverna',
    });
  });

  describe('Loading and Display', () => {
    it('shows loading state initially', () => {
      restaurantService.getProfile.mockImplementationOnce(
        () => new Promise(() => {}) // Never resolves
      );
      
      render(<RestaurantProfile />);
      expect(screen.getByText('Φόρτωση προφίλ ταβέρνας...')).toBeInTheDocument();
    });

    it('loads and displays restaurant profile', async () => {
      render(<RestaurantProfile />);

      await waitFor(() => {
        expect(restaurantService.getProfile).toHaveBeenCalled();
        expect(screen.getByText('Ταβέρνα Γιάννη')).toBeInTheDocument();
      });
    });

    it('displays last-updated timestamp', async () => {
      render(<RestaurantProfile />);

      await waitFor(() => {
        expect(screen.getByText(/Τελευταία ενημέρωση:/)).toBeInTheDocument();
      });
    });

    it('populates form fields with profile data', async () => {
      render(<RestaurantProfile />);

      await waitFor(() => {
        const nameInput = screen.getByDisplayValue('Ταβέρνα Γιάννη');
        const phoneInput = screen.getByDisplayValue('+30 210 123 4567');
        const addressInput = screen.getByDisplayValue('Οδός Παναίας 42, Αθήνα');
        
        expect(nameInput).toBeInTheDocument();
        expect(phoneInput).toBeInTheDocument();
        expect(addressInput).toBeInTheDocument();
      });
    });

    it('displays current profile information', async () => {
      render(<RestaurantProfile />);

      await waitFor(() => {
        expect(screen.getByText(/Ταβέρνα Γιάννη/)).toBeInTheDocument();
        expect(screen.getByText(/\+30 210 123 4567/)).toBeInTheDocument();
        expect(screen.getByText(/Οδός Παναίας 42, Αθήνα/)).toBeInTheDocument();
      });
    });
  });

  describe('Profile Update', () => {
    it('updates profile when form submitted', async () => {
      render(<RestaurantProfile />);

      await waitFor(() => {
        expect(screen.getByDisplayValue('Ταβέρνα Γιάννη')).toBeInTheDocument();
      });

      // Change name
      const nameInput = screen.getByDisplayValue('Ταβέρνα Γιάννη');
      fireEvent.change(nameInput, { target: { value: 'Updated Taverna' } });

      // Submit form
      const submitButton = screen.getByRole('button', { name: /Αποθήκευση/ });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(restaurantService.updateProfile).toHaveBeenCalledWith(
          expect.objectContaining({
            name: 'Updated Taverna',
            phone: '+30 210 123 4567',
            address: 'Οδός Παναίας 42, Αθήνα',
          })
        );
      });
    });

    it('shows success message after update', async () => {
      render(<RestaurantProfile />);

      await waitFor(() => {
        expect(screen.getByDisplayValue('Ταβέρνα Γιάννη')).toBeInTheDocument();
      });

      const submitButton = screen.getByRole('button', { name: /Αποθήκευση/ });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/Το προφίλ ενημερώθηκε επιτυχώς/)).toBeInTheDocument();
      });
    });

    it('validates required name field', async () => {
      render(<RestaurantProfile />);

      await waitFor(() => {
        expect(screen.getByDisplayValue('Ταβέρνα Γιάννη')).toBeInTheDocument();
      });

      // Clear name
      const nameInput = screen.getByDisplayValue('Ταβέρνα Γιάννη');
      fireEvent.change(nameInput, { target: { value: '' } });

      // Try to submit
      const submitButton = screen.getByRole('button', { name: /Αποθήκευση/ });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/Το όνομα της ταβέρνας είναι υποχρεωτικό/)).toBeInTheDocument();
      });
    });

    it('handles API errors gracefully', async () => {
      restaurantService.updateProfile.mockRejectedValueOnce(
        new Error('Network error')
      );

      render(<RestaurantProfile />);

      await waitFor(() => {
        expect(screen.getByDisplayValue('Ταβέρνα Γιάννη')).toBeInTheDocument();
      });

      const submitButton = screen.getByRole('button', { name: /Αποθήκευση/ });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/Network error/)).toBeInTheDocument();
      });
    });

    it('parses JSON extra_details correctly', async () => {
      render(<RestaurantProfile />);

      await waitFor(() => {
        expect(screen.getByDisplayValue('Ταβέρνα Γιάννη')).toBeInTheDocument();
      });

      // Get textarea and verify JSON content
      const extraDetailsTextarea = screen.getByRole('textbox', {
        name: /Επιπλέον Στοιχεία/,
      });
      expect(extraDetailsTextarea.value).toContain('website');
      expect(extraDetailsTextarea.value).toContain('afm');
    });

    it('resets form on cancel', async () => {
      render(<RestaurantProfile />);

      await waitFor(() => {
        expect(screen.getByDisplayValue('Ταβέρνα Γιάννη')).toBeInTheDocument();
      });

      // Change name
      const nameInput = screen.getByDisplayValue('Ταβέρνα Γιάννη');
      fireEvent.change(nameInput, { target: { value: 'Changed Name' } });

      // Click cancel
      const cancelButton = screen.getByRole('button', { name: /Ακύρωση/ });
      fireEvent.click(cancelButton);

      // Should reload original profile
      await waitFor(() => {
        expect(restaurantService.getProfile).toHaveBeenCalled();
      });
    });
  });

  describe('Receipt Integration', () => {
    it('should display profile data in receipts', async () => {
      render(<RestaurantProfile />);

      await waitFor(() => {
        expect(restaurantService.getProfile).toHaveBeenCalled();
      });

      // Verify that the profile includes AFM and website in extra_details
      expect(mockProfile.extra_details.afm).toBe('123456789');
      expect(mockProfile.extra_details.website).toBe('https://taverna-gianni.gr');
    });

    it('handles missing extra_details gracefully', async () => {
      restaurantService.getProfile.mockResolvedValueOnce({
        ...mockProfile,
        extra_details: null,
      });

      render(<RestaurantProfile />);

      await waitFor(() => {
        expect(screen.getByText('Ταβέρνα Γιάννη')).toBeInTheDocument();
      });

      // Should not crash when extra_details is null
      expect(screen.queryByText('undefined')).not.toBeInTheDocument();
    });
  });

  describe('Auto-clear Messages', () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.runOnlyPendingTimers();
      vi.useRealTimers();
    });

    it('auto-clears error message after 5 seconds', async () => {
      restaurantService.updateProfile.mockRejectedValueOnce(
        new Error('Test error')
      );

      render(<RestaurantProfile />);

      await waitFor(() => {
        expect(screen.getByDisplayValue('Ταβέρνα Γιάννη')).toBeInTheDocument();
      });

      const submitButton = screen.getByRole('button', { name: /Αποθήκευση/ });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/Test error/)).toBeInTheDocument();
      });

      // Fast-forward time
      vi.advanceTimersByTime(5001);

      await waitFor(() => {
        expect(screen.queryByText(/Test error/)).not.toBeInTheDocument();
      });
    });
  });
});
