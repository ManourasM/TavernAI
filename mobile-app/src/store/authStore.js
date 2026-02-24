import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import * as authService from '../services/authService';

// User roles
export const ROLES = {
  ADMIN: 'admin',
  WAITER: 'waiter',
  KITCHEN: 'kitchen',
  GRILL: 'grill',
  DRINKS: 'drinks',
};

const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      users: [], // List of all users (for admin)
      isAuthenticated: false,
      isLoading: false,
      error: null,
      needsBootstrap: false,
      token: null,

      // Initialize auth on app start (check stored token)
      initializeAuth: async () => {
        try {
          set({ isLoading: true });
          
          // Check if token is still valid
          const result = await authService.verifyToken();
          if (result.valid && result.user) {
            set({ 
              user: result.user, 
              isAuthenticated: true,
              token: authService.getToken(),
              error: null 
            });
            console.log('[authStore] Restored session from token');
          } else {
            // Clear invalid token
            authService.clearToken();
            set({ 
              user: null, 
              isAuthenticated: false,
              token: null,
              error: null 
            });
          }
        } catch (error) {
          console.error('[authStore] Initialize error:', error);
          set({ error: error.message });
        } finally {
          set({ isLoading: false });
        }
      },

      // Check if bootstrap mode is active
      checkBootstrap: async () => {
        try {
          const result = await authService.checkBootstrapMode();
          set({ needsBootstrap: result.needsBootstrap });
          return result;
        } catch (error) {
          console.error('[authStore] Bootstrap check error:', error);
          set({ needsBootstrap: false });
          return { needsBootstrap: false, error: error.message };
        }
      },

      // Login with backend
      login: async (username, password) => {
        try {
          set({ isLoading: true, error: null });
          
          const result = await authService.login(username, password);
          
          if (result.success) {
            set({ 
              user: result.user, 
              isAuthenticated: true,
              token: result.token,
              error: null 
            });
            console.log('[authStore] Login successful:', username);
            return { success: true, user: result.user };
          } else {
            set({ error: result.error });
            console.error('[authStore] Login failed:', result.error);
            return { success: false, error: result.error };
          }
        } catch (error) {
          const errorMsg = error?.message || 'Login failed';
          set({ error: errorMsg, isLoading: false });
          console.error('[authStore] Login error:', error);
          return { success: false, error: errorMsg };
        } finally {
          set({ isLoading: false });
        }
      },

      // Signup new user (bootstrap mode only)
      signup: async (username, password) => {
        try {
          set({ isLoading: true, error: null });
          
          const result = await authService.signup(username, password);
          
          if (result.success) {
            // After signup, user should login to get token
            set({ 
              error: null,
              needsBootstrap: false 
            });
            console.log('[authStore] Signup successful, now login');
            return { success: true, user: result.user };
          } else {
            set({ error: result.error });
            console.error('[authStore] Signup failed:', result.error);
            return { success: false, error: result.error };
          }
        } catch (error) {
          const errorMsg = error?.message || 'Signup failed';
          set({ error: errorMsg });
          console.error('[authStore] Signup error:', error);
          return { success: false, error: errorMsg };
        } finally {
          set({ isLoading: false });
        }
      },

      // Logout function
      logout: () => {
        authService.logout();
        set({ user: null, isAuthenticated: false, token: null, error: null });
        console.log('[authStore] Logged out');
      },

      // Check if user has specific role
      hasRole: (role) => {
        const user = get().user;
        if (!user) return false;
        const roles = user.roles || [];
        if (roles.includes(ROLES.ADMIN)) return true; // Admin has all roles
        return roles.includes(role);
      },

      // Get accessible endpoints based on user roles
      getAccessibleEndpoints: () => {
        const user = get().user;
        if (!user) return [];
        
        const roles = user.roles || [];
        
        // Map roles to endpoint names
        const endpoints = [];
        if (roles.includes(ROLES.ADMIN)) {
          return ['waiter', 'kitchen', 'grill', 'drinks'];
        }
        if (roles.includes(ROLES.WAITER)) endpoints.push('waiter');
        if (roles.includes(ROLES.KITCHEN)) endpoints.push('kitchen');
        if (roles.includes(ROLES.GRILL)) endpoints.push('grill');
        if (roles.includes(ROLES.DRINKS)) endpoints.push('drinks');
        
        return endpoints;
      },

      // Check if user is admin
      isAdmin: () => {
        const user = get().user;
        if (!user) return false;
        const roles = user.roles || [];
        return roles.includes(ROLES.ADMIN);
      },

      // Fetch all users (admin only)
      fetchUsers: async () => {
        try {
          // TODO: Implement API call to /api/users when backend supports it
          // For now, return empty array
          console.log('[authStore] fetchUsers not implemented yet');
          set({ users: [] });
          return [];
        } catch (error) {
          console.error('[authStore] Fetch users error:', error);
          return [];
        }
      },

      // Add new user (admin only)
      addUser: async (userData) => {
        try {
          // TODO: Implement API call to /api/users when backend supports it
          console.log('[authStore] addUser not implemented yet', userData);
          const newUser = {
            id: Date.now(),
            ...userData,
            name: userData.username,
          };
          set((state) => ({ users: [...state.users, newUser] }));
          return { success: true, user: newUser };
        } catch (error) {
          console.error('[authStore] Add user error:', error);
          return { success: false, error: error.message };
        }
      },

      // Delete user (admin only)
      deleteUser: async (userId) => {
        try {
          // TODO: Implement API call to DELETE /api/users/:id when backend supports it
          console.log('[authStore] deleteUser not implemented yet', userId);
          set((state) => ({
            users: state.users.filter((u) => u.id !== userId),
          }));
          return { success: true };
        } catch (error) {
          console.error('[authStore] Delete user error:', error);
          return { success: false, error: error.message };
        }
      },
    }),
    {
      name: 'tavern-auth-storage',
    }
  )
);

export default useAuthStore;

