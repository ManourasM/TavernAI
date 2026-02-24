import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AdminRoute, StationRoute, ProtectedRoute, SetupRoute } from './RouteGuards';
import useAuthStore from '../store/authStore';

// Mock the authStore
vi.mock('../store/authStore', () => ({
  default: vi.fn(),
}));

const renderWithRouter = (component) => {
  return render(<BrowserRouter>{component}</BrowserRouter>);
};

describe('RouteGuards', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('AdminRoute', () => {
    it('should render children when user is authenticated and admin', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: true,
          isAdmin: () => true,
        };
        return selector(state);
      });

      renderWithRouter(
        <AdminRoute>
          <div>Admin Content</div>
        </AdminRoute>
      );

      expect(screen.getByText('Admin Content')).toBeInTheDocument();
    });

    it('should redirect to login when user is not authenticated', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: false,
          isAdmin: () => false,
        };
        return selector(state);
      });

      renderWithRouter(
        <AdminRoute>
          <div>Admin Content</div>
        </AdminRoute>
      );

      expect(screen.queryByText('Admin Content')).not.toBeInTheDocument();
      // Navigate was called (location would change)
      expect(window.location.pathname).not.toBe('/error');
    });

    it('should redirect to home when user is authenticated but not admin', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: true,
          isAdmin: () => false,
        };
        return selector(state);
      });

      renderWithRouter(
        <AdminRoute>
          <div>Admin Content</div>
        </AdminRoute>
      );

      expect(screen.queryByText('Admin Content')).not.toBeInTheDocument();
    });
  });

  describe('StationRoute', () => {
    it('should render children when user is admin', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: true,
          hasRole: () => true,
          isAdmin: () => true,
        };
        return selector(state);
      });

      renderWithRouter(
        <StationRoute station="kitchen">
          <div>Kitchen Station</div>
        </StationRoute>
      );

      expect(screen.getByText('Kitchen Station')).toBeInTheDocument();
    });

    it('should render children when user has the required station role', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: true,
          hasRole: (role) => role === 'kitchen',
          isAdmin: () => false,
        };
        return selector(state);
      });

      renderWithRouter(
        <StationRoute station="kitchen">
          <div>Kitchen Station</div>
        </StationRoute>
      );

      expect(screen.getByText('Kitchen Station')).toBeInTheDocument();
    });

    it('should redirect to login when user is not authenticated', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: false,
          hasRole: () => false,
          isAdmin: () => false,
        };
        return selector(state);
      });

      renderWithRouter(
        <StationRoute station="kitchen">
          <div>Kitchen Station</div>
        </StationRoute>
      );

      expect(screen.queryByText('Kitchen Station')).not.toBeInTheDocument();
    });

    it('should redirect when user lacks the required station role', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: true,
          hasRole: (role) => role === 'grill', // User only has grill role
          isAdmin: () => false,
        };
        return selector(state);
      });

      renderWithRouter(
        <StationRoute station="kitchen">
          <div>Kitchen Station</div>
        </StationRoute>
      );

      expect(screen.queryByText('Kitchen Station')).not.toBeInTheDocument();
    });
  });

  describe('ProtectedRoute', () => {
    it('should render children when user is authenticated', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: true,
        };
        return selector(state);
      });

      renderWithRouter(
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      );

      expect(screen.getByText('Protected Content')).toBeInTheDocument();
    });

    it('should redirect to login when user is not authenticated', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: false,
        };
        return selector(state);
      });

      renderWithRouter(
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      );

      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    });
  });

  describe('SetupRoute', () => {
    it('should render children when user is authenticated and admin', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: true,
          isAdmin: () => true,
        };
        return selector(state);
      });

      renderWithRouter(
        <SetupRoute>
          <div>Setup Content</div>
        </SetupRoute>
      );

      expect(screen.getByText('Setup Content')).toBeInTheDocument();
    });

    it('should redirect to login when user is not authenticated', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: false,
          isAdmin: () => false,
        };
        return selector(state);
      });

      renderWithRouter(
        <SetupRoute>
          <div>Setup Content</div>
        </SetupRoute>
      );

      expect(screen.queryByText('Setup Content')).not.toBeInTheDocument();
    });

    it('should redirect to home when user is authenticated but not admin', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: true,
          isAdmin: () => false,
        };
        return selector(state);
      });

      renderWithRouter(
        <SetupRoute>
          <div>Setup Content</div>
        </SetupRoute>
      );

      expect(screen.queryByText('Setup Content')).not.toBeInTheDocument();
    });
  });
});
