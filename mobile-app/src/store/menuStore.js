import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const useMenuStore = create(
  persist(
    (set, get) => ({
      menu: null,
      endpoints: [
        { id: 'waiter', name: 'Σερβιτόρος', color: '#9C27B0' },
        { id: 'kitchen', name: 'Κουζίνα', color: '#4CAF50' },
        { id: 'grill', name: 'Ψησταριά', color: '#FF5722' },
        { id: 'drinks', name: 'Ποτά', color: '#2196F3' },
      ],
      isMenuSetup: false,

      // Load menu from backend or local storage
      loadMenu: async () => {
        try {
          // Try to fetch from public folder first (default menu)
          const menuResponse = await fetch('/menu.json');
          if (menuResponse.ok) {
            const menu = await menuResponse.json();
            set({ menu, isMenuSetup: true });
            localStorage.setItem('tavern_menu', JSON.stringify(menu));
            return { success: true, menu };
          }
        } catch (error) {
          console.error('Failed to load menu from public folder:', error);
        }

        // Fallback to local storage
        const storedMenu = localStorage.getItem('tavern_menu');
        if (storedMenu) {
          const menu = JSON.parse(storedMenu);
          set({ menu, isMenuSetup: true });
          return { success: true, menu };
        }

        return { success: false, error: 'No menu found' };
      },

      // Save menu (from OCR or manual entry)
      saveMenu: async (menu) => {
        set({ menu, isMenuSetup: true });

        // Save to local storage
        localStorage.setItem('tavern_menu', JSON.stringify(menu));

        // TODO: Optionally sync to backend
        return { success: true };
      },

      // Add menu item
      addMenuItem: (item) => {
        const menu = get().menu || [];
        const newMenu = [...menu, { ...item, id: Date.now() }];
        set({ menu: newMenu });
        localStorage.setItem('tavern_menu', JSON.stringify(newMenu));
        return { success: true };
      },

      // Update menu item
      updateMenuItem: (itemId, updates) => {
        const menu = get().menu || [];
        const newMenu = menu.map((item) =>
          item.id === itemId ? { ...item, ...updates } : item
        );
        set({ menu: newMenu });
        localStorage.setItem('tavern_menu', JSON.stringify(newMenu));
        return { success: true };
      },

      // Delete menu item
      deleteMenuItem: (itemId) => {
        const menu = get().menu || [];
        const newMenu = menu.filter((item) => item.id !== itemId);
        set({ menu: newMenu });
        localStorage.setItem('tavern_menu', JSON.stringify(newMenu));
        return { success: true };
      },

      // Add endpoint
      addEndpoint: (endpoint) => {
        const endpoints = get().endpoints;
        const newEndpoint = {
          id: endpoint.id || endpoint.name.toLowerCase().replace(/\s+/g, '-'),
          name: endpoint.name,
          color: endpoint.color || '#9E9E9E',
        };
        set({ endpoints: [...endpoints, newEndpoint] });
        return { success: true };
      },

      // Update endpoint
      updateEndpoint: (endpointId, updates) => {
        const endpoints = get().endpoints;
        const newEndpoints = endpoints.map((ep) =>
          ep.id === endpointId ? { ...ep, ...updates } : ep
        );
        set({ endpoints: newEndpoints });
        return { success: true };
      },

      // Delete endpoint
      deleteEndpoint: (endpointId) => {
        const endpoints = get().endpoints;
        const newEndpoints = endpoints.filter((ep) => ep.id !== endpointId);
        set({ endpoints: newEndpoints });
        return { success: true };
      },

      // Get menu items for specific endpoint
      getMenuItemsByEndpoint: (endpointId) => {
        const menu = get().menu || [];
        return menu.filter((item) => item.category === endpointId);
      },

      // Reset menu (for testing or re-setup)
      resetMenu: async () => {
        set({ menu: null, isMenuSetup: false });
        localStorage.removeItem('tavern_menu');
        return { success: true };
      },
    }),
    {
      name: 'tavern-menu-storage',
    }
  )
);

export default useMenuStore;

