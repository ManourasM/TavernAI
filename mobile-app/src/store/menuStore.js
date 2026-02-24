import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { getMenu, clearMenuCache } from '../services/menuService';
import { listWorkstations } from '../services/workstationsService';

const useMenuStore = create(
  persist(
    (set, get) => ({
      menu: null,
      workstations: [],
      endpoints: [],
      isMenuSetup: false,
      menuLoadError: null,
      workstationsLoadError: null,

      // Load menu from backend API with fallback to public/menu.json
      loadMenu: async (options = {}) => {
        try {
          const result = await getMenu(options);
          
          if (result.success) {
            // Remove API metadata fields before storing
            const cleanMenu = JSON.parse(JSON.stringify(result.menu || {}));
            delete cleanMenu.available_categories;
            
            set({ menu: cleanMenu, isMenuSetup: true, menuLoadError: null });
            console.log(`[menuStore] Loaded menu from ${result.source}`);
            if (result.apiError) {
              console.warn(`[menuStore] API error (using fallback): ${result.apiError}`);
            }
            return { success: true, menu: cleanMenu, source: result.source };
          } else {
            set({ menu: null, isMenuSetup: false, menuLoadError: result.error });
            console.error('[menuStore] Failed to load menu:', result.error);
            return { success: false, error: result.error };
          }
        } catch (error) {
          const errorMsg = error?.message || 'Unknown error loading menu';
          set({ menu: null, isMenuSetup: false, menuLoadError: errorMsg });
          console.error('[menuStore] Menu load error:', error);
          return { success: false, error: errorMsg };
        }
      },

      // Load all workstations from backend (active and inactive)
      loadWorkstations: async () => {
        try {
          const data = await listWorkstations();
          // Store all workstations (both active and inactive) for admin/editing purposes
          const allWorkstations = data || [];
          // Filter only active stations for endpoint/routing purposes
          const activeWorkstations = allWorkstations.filter((ws) => ws.active !== false);
          const stationsOnly = activeWorkstations.filter((ws) => ws.slug !== 'waiter');
          set({
            workstations: allWorkstations,
            endpoints: stationsOnly.map((ws) => ({
              id: ws.slug,
              name: ws.name,
              color: ws.color || '#667eea',
            })),
            workstationsLoadError: null,
          });
          return { success: true, workstations: allWorkstations };
        } catch (error) {
          const errorMsg = error?.message || 'Unknown error loading workstations';
          set({ workstations: [], endpoints: [], workstationsLoadError: errorMsg });
          console.error('[menuStore] Workstations load error:', error);
          return { success: false, error: errorMsg };
        }
      },

      // Save menu (from OCR or manual entry)
      saveMenu: async (menu) => {
        set({ menu, isMenuSetup: true });
        // TODO: Optionally sync to backend API (POST /api/menu)
        return { success: true };
      },

      // Refresh menu from source (skip cache)
      refreshMenu: async () => {
        console.log('[menuStore] Refreshing menu from source...');
        return get().loadMenu({ forceRefresh: true });
      },

      // Clear menu cache
      clearCache: async () => {
        clearMenuCache();
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
        clearMenuCache();
        set({ menu: null, isMenuSetup: false, menuLoadError: null });
        return { success: true };
      },
    }),
    {
      name: 'tavern-menu-storage',
    }
  )
);

export default useMenuStore;

