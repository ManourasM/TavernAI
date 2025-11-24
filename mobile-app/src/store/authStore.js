import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// User roles
export const ROLES = {
  ADMIN: 'admin',
  WAITER: 'waiter',
  KITCHEN: 'kitchen',
  GRILL: 'grill',
  DRINKS: 'drinks',
};

// Default users (in production, this would be in a database)
const DEFAULT_USERS = [
  { id: 1, username: 'admin', password: 'admin123', role: ROLES.ADMIN, name: 'Administrator' },
  { id: 2, username: 'waiter', password: 'waiter123', role: ROLES.WAITER, name: 'Waiter' },
  { id: 3, username: 'kitchen', password: 'kitchen123', role: ROLES.KITCHEN, name: 'Kitchen Staff' },
  { id: 4, username: 'grill', password: 'grill123', role: ROLES.GRILL, name: 'Grill Staff' },
  { id: 5, username: 'drinks', password: 'drinks123', role: ROLES.DRINKS, name: 'Drinks Staff' },
];

const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      users: DEFAULT_USERS,

      // Login function
      login: async (username, password) => {
        const users = get().users;
        const user = users.find(
          (u) => u.username === username && u.password === password
        );

        if (user) {
          const { password: _, ...userWithoutPassword } = user;
          set({ user: userWithoutPassword, isAuthenticated: true });
          return { success: true, user: userWithoutPassword };
        }

        return { success: false, error: 'Invalid username or password' };
      },

      // Logout function
      logout: async () => {
        set({ user: null, isAuthenticated: false });
      },

      // Check if user has specific role
      hasRole: (role) => {
        const user = get().user;
        if (!user) return false;
        if (user.role === ROLES.ADMIN) return true; // Admin has access to everything
        return user.role === role;
      },

      // Get accessible endpoints based on role
      getAccessibleEndpoints: () => {
        const user = get().user;
        if (!user) return [];
        
        if (user.role === ROLES.ADMIN) {
          return ['waiter', 'kitchen', 'grill', 'drinks'];
        }
        
        if (user.role === ROLES.WAITER) {
          return ['waiter'];
        }
        
        return [user.role];
      },

      // Add new user (admin only)
      addUser: (newUser) => {
        const currentUser = get().user;
        if (currentUser?.role !== ROLES.ADMIN) {
          return { success: false, error: 'Only admins can add users' };
        }

        const users = get().users;
        const userExists = users.some((u) => u.username === newUser.username);
        
        if (userExists) {
          return { success: false, error: 'Username already exists' };
        }

        const user = {
          id: users.length + 1,
          ...newUser,
        };

        set({ users: [...users, user] });
        return { success: true, user };
      },

      // Update user (admin only)
      updateUser: (userId, updates) => {
        const currentUser = get().user;
        if (currentUser?.role !== ROLES.ADMIN) {
          return { success: false, error: 'Only admins can update users' };
        }

        const users = get().users;
        const updatedUsers = users.map((u) =>
          u.id === userId ? { ...u, ...updates } : u
        );

        set({ users: updatedUsers });
        return { success: true };
      },

      // Delete user (admin only)
      deleteUser: (userId) => {
        const currentUser = get().user;
        if (currentUser?.role !== ROLES.ADMIN) {
          return { success: false, error: 'Only admins can delete users' };
        }

        if (userId === currentUser.id) {
          return { success: false, error: 'Cannot delete your own account' };
        }

        const users = get().users;
        const updatedUsers = users.filter((u) => u.id !== userId);

        set({ users: updatedUsers });
        return { success: true };
      },
    }),
    {
      name: 'tavern-auth-storage',
    }
  )
);

export default useAuthStore;

