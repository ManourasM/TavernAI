/**
 * Route Guards Test Suite
 * 
 * Tests AdminRoute, StationRoute, ProtectedRoute, and SetupRoute components
 * for proper role-based access control and redirects.
 * 
 * To run these tests:
 * 1. Install testing dependencies: npm install --save-dev vitest @testing-library/react
 * 2. Run: npm run test
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { AdminRoute, StationRoute, ProtectedRoute, SetupRoute } from '../../src/components/RouteGuards';
import useAuthStore from '../../src/store/authStore';

// Mock the authStore
vi.mock('../../src/store/authStore', () => ({
  default: vi.fn(),
  ROLES: {
    ADMIN: 'admin',
    WAITER: 'waiter',
    KITCHEN: 'kitchen',
    GRILL: 'grill',
    DRINKS: 'drinks',
  },
}));

const renderWithRouter = (component) => {
  return render(<MemoryRouter>{component}</MemoryRouter>);
};

describe('RouteGuards', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('AdminRoute - Role Based Access Control', () => {
    it('✓ should render children when user is authenticated AND has admin role', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: true,
          isAdmin: () => true,
          user: { name: 'Admin User', roles: ['admin'] },
        };
        return selector(state);
      });

      renderWithRouter(
        <AdminRoute>
          <div data-testid="admin-content">Admin Dashboard Available</div>
        </AdminRoute>
      );

      expect(screen.getByTestId('admin-content')).toBeInTheDocument();
      expect(screen.getByText('Admin Dashboard Available')).toBeInTheDocument();
    });

    it('✓ should redirect to /login when user is NOT authenticated', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: false,
          isAdmin: () => false,
          user: null,
        };
        return selector(state);
      });

      renderWithRouter(
        <AdminRoute>
          <div data-testid="admin-content">Admin Content</div>
        </AdminRoute>
      );

      expect(screen.queryByTestId('admin-content')).not.toBeInTheDocument();
    });

    it('✓ should redirect to /home when authenticate but NOT admin', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: true,
          isAdmin: () => false,
          user: { name: 'Regular User', roles: ['waiter'] },
        };
        return selector(state);
      });

      renderWithRouter(
        <AdminRoute>
          <div data-testid="admin-content">Admin Content</div>
        </AdminRoute>
      );

      expect(screen.queryByTestId('admin-content')).not.toBeInTheDocument();
    });
  });

  describe('StationRoute - Station Role Access', () => {
    it('✓ should render children when admin user (admin has all access)', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: true,
          hasRole: () => true,
          isAdmin: () => true,
          user: { name: 'Admin', roles: ['admin'] },
        };
        return selector(state);
      });

      renderWithRouter(
        <StationRoute station="kitchen">
          <div data-testid="station-content">Kitchen Station</div>
        </StationRoute>
      );

      expect(screen.getByTestId('station-content')).toBeInTheDocument();
    });

    it('✓ should render children when user has REQUIRED station role (kitchen)', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: true,
          hasRole: (role) => role === 'kitchen',
          isAdmin: () => false,
          user: { name: 'Chef', roles: ['kitchen'] },
        };
        return selector(state);
      });

      renderWithRouter(
        <StationRoute station="kitchen">
          <div data-testid="station-content">Kitchen Station</div>
        </StationRoute>
      );

      expect(screen.getByTestId('station-content')).toBeInTheDocument();
    });

    it('✓ should render children when user has REQUIRED station role (grill)', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: true,
          hasRole: (role) => role === 'grill',
          isAdmin: () => false,
          user: { name: 'Grill Master', roles: ['grill'] },
        };
        return selector(state);
      });

      renderWithRouter(
        <StationRoute station="grill">
          <div data-testid="station-content">Grill Station</div>
        </StationRoute>
      );

      expect(screen.getByTestId('station-content')).toBeInTheDocument();
    });

    it('✓ should redirect to /login when user NOT authenticated', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: false,
          hasRole: () => false,
          isAdmin: () => false,
          user: null,
        };
        return selector(state);
      });

      renderWithRouter(
        <StationRoute station="kitchen">
          <div data-testid="station-content">Kitchen Station</div>
        </StationRoute>
      );

      expect(screen.queryByTestId('station-content')).not.toBeInTheDocument();
    });

    it('✓ should redirect to /login when user lacks REQUIRED station role', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: true,
          hasRole: (role) => role === 'grill', // User only has grill role
          isAdmin: () => false,
          user: { name: 'Grill Worker', roles: ['grill'] },
        };
        return selector(state);
      });

      renderWithRouter(
        <StationRoute station="kitchen">
          <div data-testid="station-content">Kitchen Station</div>
        </StationRoute>
      );

      // User has grill role but trying to access kitchen → should be denied
      expect(screen.queryByTestId('station-content')).not.toBeInTheDocument();
    });

    it('✓ should support all station types (kitchen, grill, drinks, waiter)', () => {
      const stations = ['kitchen', 'grill', 'drinks', 'waiter'];

      stations.forEach((station) => {
        useAuthStore.mockImplementation((selector) => {
          const state = {
            isAuthenticated: true,
            hasRole: (role) => role === station,
            isAdmin: () => false,
            user: { name: `${station} user`, roles: [station] },
          };
          return selector(state);
        });

        const { unmount } = renderWithRouter(
          <StationRoute station={station}>
            <div data-testid={`${station}-content`}>{station} Access</div>
          </StationRoute>
        );

        expect(screen.getByTestId(`${station}-content`)).toBeInTheDocument();
        unmount();
      });
    });
  });

  describe('ProtectedRoute - Generic Auth Guard', () => {
    it('✓ should render children when user is authenticated', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: true,
          user: { name: 'Any User', roles: ['waiter'] },
        };
        return selector(state);
      });

      renderWithRouter(
        <ProtectedRoute>
          <div data-testid="protected-content">Protected Page</div>
        </ProtectedRoute>
      );

      expect(screen.getByTestId('protected-content')).toBeInTheDocument();
    });

    it('✓ should redirect to /login when user NOT authenticated', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: false,
          user: null,
        };
        return selector(state);
      });

      renderWithRouter(
        <ProtectedRoute>
          <div data-testid="protected-content">Protected Page</div>
        </ProtectedRoute>
      );

      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
    });

    it('✓ should allow ANY authenticated user (role-agnostic)', () => {
      const roles = ['admin', 'waiter', 'kitchen', 'grill', 'drinks'];

      roles.forEach((role) => {
        useAuthStore.mockImplementation((selector) => {
          const state = {
            isAuthenticated: true,
            user: { name: `${role} user`, roles: [role] },
          };
          return selector(state);
        });

        const { unmount } = renderWithRouter(
          <ProtectedRoute>
            <div data-testid="protected-content">Protected Page</div>
          </ProtectedRoute>
        );

        expect(screen.getByTestId('protected-content')).toBeInTheDocument();
        unmount();
      });
    });
  });

  describe('SetupRoute - Admin-Only Setup Access', () => {
    it('✓ should render children when user is authenticated AND admin', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: true,
          isAdmin: () => true,
          user: { name: 'Admin', roles: ['admin'] },
        };
        return selector(state);
      });

      renderWithRouter(
        <SetupRoute>
          <div data-testid="setup-content">Setup Wizard</div>
        </SetupRoute>
      );

      expect(screen.getByTestId('setup-content')).toBeInTheDocument();
    });

    it('✓ should redirect to /login when user NOT authenticated', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: false,
          isAdmin: () => false,
          user: null,
        };
        return selector(state);
      });

      renderWithRouter(
        <SetupRoute>
          <div data-testid="setup-content">Setup Wizard</div>
        </SetupRoute>
      );

      expect(screen.queryByTestId('setup-content')).not.toBeInTheDocument();
    });

    it('✓ should redirect to /home when authenticated but NOT admin', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: true,
          isAdmin: () => false,
          user: { name: 'Waiter', roles: ['waiter'] },
        };
        return selector(state);
      });

      renderWithRouter(
        <SetupRoute>
          <div data-testid="setup-content">Setup Wizard</div>
        </SetupRoute>
      );

      expect(screen.queryByTestId('setup-content')).not.toBeInTheDocument();
    });
  });

  describe('Role-Based Feature Visibility', () => {
    it('✓ should control visibility of Menu Editor for admin-only users', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: true,
          isAdmin: () => true,
          user: { name: 'Admin', roles: ['admin'] },
        };
        return selector(state);
      });

      renderWithRouter(
        <AdminRoute>
          <button data-testid="menu-editor">📋 Menu Editor</button>
        </AdminRoute>
      );

      expect(screen.getByTestId('menu-editor')).toBeInTheDocument();
    });

    it('✓ should hide Menu Editor from non-admin users', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: true,
          isAdmin: () => false,
          user: { name: 'Waiter', roles: ['waiter'] },
        };
        return selector(state);
      });

      renderWithRouter(
        <AdminRoute>
          <button data-testid="menu-editor">📋 Menu Editor</button>
        </AdminRoute>
      );

      expect(screen.queryByTestId('menu-editor')).not.toBeInTheDocument();
    });

    it('✓ should show Kitchen station only to kitchen staff', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: true,
          hasRole: (role) => role === 'kitchen',
          isAdmin: () => false,
          user: { name: 'Chef', roles: ['kitchen'] },
        };
        return selector(state);
      });

      renderWithRouter(
        <StationRoute station="kitchen">
          <div data-testid="kitchen-view">Kitchen Orders</div>
        </StationRoute>
      );

      expect(screen.getByTestId('kitchen-view')).toBeInTheDocument();
    });

    it('✓ should deny Kitchen access to grill staff', () => {
      useAuthStore.mockImplementation((selector) => {
        const state = {
          isAuthenticated: true,
          hasRole: (role) => role === 'grill',
          isAdmin: () => false,
          user: { name: 'Grill Master', roles: ['grill'] },
        };
        return selector(state);
      });

      renderWithRouter(
        <StationRoute station="kitchen">
          <div data-testid="kitchen-view">Kitchen Orders</div>
        </StationRoute>
      );

      expect(screen.queryByTestId('kitchen-view')).not.toBeInTheDocument();
    });
  });
});
