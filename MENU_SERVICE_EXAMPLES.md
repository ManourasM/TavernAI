# Menu Service Implementation Examples

This file provides copy-paste ready examples for integrating the menu service into your components.

## Mobile App Examples

### Example 1: Basic Menu Loading (Functional Component)

```javascript
import React, { useEffect, useState } from 'react';
import useMenuStore from '../store/menuStore';

export function MenuDisplay() {
  const { menu, isMenuSetup, loadMenu } = useMenuStore();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const init = async () => {
      const result = await loadMenu();
      if (!result.success) {
        setError(result.error);
      }
      setLoading(false);
    };
    
    init();
  }, [loadMenu]);

  if (loading) {
    return <div className="skeleton">Loading menu...</div>;
  }

  if (error) {
    return (
      <div className="error">
        <p>Failed to load menu: {error}</p>
        <button onClick={() => loadMenu()}>Retry</button>
      </div>
    );
  }

  return (
    <div className="menu">
      {menu && Object.entries(menu).map(([category, items]) => (
        <section key={category} className="menu-category">
          <h2>{category}</h2>
          <ul>
            {items.map(item => (
              <li key={item.id}>
                <span className="name">{item.name}</span>
                <span className="price">${item.price}</span>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
```

### Example 2: With Refresh Button

```javascript
import React, { useEffect } from 'react';
import useMenuStore from '../store/menuStore';

export function MenuWithRefresh() {
  const { menu, isMenuSetup, loadMenu, refreshMenu } = useMenuStore();

  useEffect(() => {
    loadMenu();
  }, []);

  if (!isMenuSetup) {
    return <div>Loading menu...</div>;
  }

  const handleRefresh = async () => {
    const result = await refreshMenu();
    if (result.success) {
      alert(`Menu refreshed from ${result.source}`);
    }
  };

  return (
    <div>
      <button onClick={handleRefresh} className="refresh-btn">
        ↻ Refresh Menu
      </button>
      <MenuContent menu={menu} />
    </div>
  );
}
```

### Example 3: Menu with Category Filtering

```javascript
import React, { useEffect, useState } from 'react';
import useMenuStore from '../store/menuStore';

export function MenuByStation() {
  const { menu, loadMenu } = useMenuStore();
  const [station, setStation] = useState('kitchen');

  useEffect(() => {
    loadMenu();
  }, []);

  const filterByStation = (items) => {
    return items.filter(item => item.category === station);
  };

  return (
    <div>
      <select value={station} onChange={e => setStation(e.target.value)}>
        <option value="kitchen">Kitchen</option>
        <option value="grill">Grill</option>
        <option value="drinks">Drinks</option>
      </select>

      {menu && Object.entries(menu).map(([category, items]) => {
        const filtered = filterByStation(items);
        return filtered.length > 0 ? (
          <div key={category}>
            <h3>{category}</h3>
            {filtered.map(item => (
              <div key={item.id}>{item.name}</div>
            ))}
          </div>
        ) : null;
      })}
    </div>
  );
}
```

### Example 4: Menu with Search

```javascript
import React, { useEffect, useState, useMemo } from 'react';
import useMenuStore from '../store/menuStore';

export function SearchableMenu() {
  const { menu, loadMenu } = useMenuStore();
  const [search, setSearch] = useState('');

  useEffect(() => {
    loadMenu();
  }, []);

  const filtered = useMemo(() => {
    if (!menu || !search) return menu;
    
    const results = {};
    Object.entries(menu).forEach(([category, items]) => {
      const match = items.filter(item =>
        item.name.toLowerCase().includes(search.toLowerCase())
      );
      if (match.length) {
        results[category] = match;
      }
    });
    return results;
  }, [menu, search]);

  return (
    <div>
      <input
        type="search"
        placeholder="Search items..."
        value={search}
        onChange={e => setSearch(e.target.value)}
      />
      
      {filtered && Object.entries(filtered).map(([category, items]) => (
        <div key={category}>
          <h3>{category} ({items.length})</h3>
          {items.map(item => (
            <div key={item.id}>{item.name} - ${item.price}</div>
          ))}
        </div>
      ))}
    </div>
  );
}
```

### Example 5: Error Boundary with Retry

```javascript
import React, { useEffect, useState } from 'react';
import useMenuStore from '../store/menuStore';

export function MenuWithErrorBoundary() {
  const { menu, menuLoadError, loadMenu, refreshMenu } = useMenuStore();
  const [retrying, setRetrying] = useState(false);

  useEffect(() => {
    loadMenu();
  }, []);

  const handleRetry = async () => {
    setRetrying(true);
    try {
      await refreshMenu();
    } catch (err) {
      console.error('Retry failed:', err);
    } finally {
      setRetrying(false);
    }
  };

  if (menuLoadError) {
    return (
      <div className="error-banner">
        <h3>⚠️ Menu unavailable</h3>
        <p>{menuLoadError}</p>
        <button 
          onClick={handleRetry}
          disabled={retrying}
          className="retry-btn"
        >
          {retrying ? 'Retrying...' : 'Try Again'}
        </button>
        <p className="note">
          Check your connection or try again later.
        </p>
      </div>
    );
  }

  if (!menu) {
    return <div className="loading">Loading menu...</div>;
  }

  return <MenuContent menu={menu} />;
}
```

## Waiter UI (Legacy) Examples

### Example 1: Basic Menu Load

```javascript
import React, { useEffect, useState } from 'react';
import { getMenu } from './menuService';

export function WaiterMenu() {
  const [menu, setMenu] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadMenu = async () => {
      const result = await getMenu();
      if (result.success) {
        setMenu(result.menu);
        console.log(`Menu loaded from: ${result.source}`);
      } else {
        setError(result.error);
      }
      setLoading(false);
    };

    loadMenu();
  }, []);

  if (loading) return <div>Loading menu...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      {Object.entries(menu || {}).map(([category, items]) => (
        <div key={category}>
          <h2>{category}</h2>
          {items.map(item => (
            <div key={item.id}>{item.name}</div>
          ))}
        </div>
      ))}
    </div>
  );
}
```

### Example 2: With Manual Refresh

```javascript
import React, { useEffect, useState } from 'react';
import { getMenu } from './menuService';

export function MenuWithManualRefresh() {
  const [menu, setMenu] = useState(null);
  const [source, setSource] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    const load = async () => {
      const result = await getMenu();
      if (result.success) {
        setMenu(result.menu);
        setSource(result.source);
      }
    };
    load();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    const result = await getMenu({ skipCache: true });
    if (result.success) {
      setMenu(result.menu);
      setSource(result.source);
    }
    setRefreshing(false);
  };

  return (
    <div>
      <button onClick={handleRefresh} disabled={refreshing}>
        {refreshing ? 'Refreshing...' : 'Refresh Menu'}
      </button>
      {source && <p>Loaded from: {source}</p>}
      {/* Menu content */}
    </div>
  );
}
```

## Kitchen UI (Station) Examples

### Example 1: Station-Specific Items

```javascript
import React, { useEffect, useState } from 'react';
import { getMenu } from './menuService';

const STATION = 'kitchen'; // Change to 'grill' for grill UI

export function StationMenu() {
  const [menu, setMenu] = useState(null);
  const [items, setItems] = useState([]);

  useEffect(() => {
    getMenu().then(result => {
      if (result.success) {
        setMenu(result.menu);
        
        // Filter items for this station
        const stationItems = [];
        Object.values(result.menu)?.forEach(category => {
          category.forEach(item => {
            if (item.category === STATION) {
              stationItems.push(item);
            }
          });
        });
        setItems(stationItems);
      }
    });
  }, []);

  return (
    <div className="station-items">
      {items.map(item => (
        <div key={item.id} className="item">
          {item.name} ({item.price}€)
        </div>
      ))}
    </div>
  );
}
```

### Example 2: With Loading Skeleton

```javascript
import React, { useEffect, useState } from 'react';
import { getMenu } from './menuService';

export function StationMenuWithSkeleton() {
  const [menu, setMenu] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMenu().then(result => {
      if (result.success) {
        // Simulate loading delay for skeleton demo
        setTimeout(() => {
          setMenu(result.menu);
          setLoading(false);
        }, 500);
      }
    });
  }, []);

  if (loading) {
    return (
      <div className="skeleton-container">
        <div className="skeleton-item" />
        <div className="skeleton-item" />
        <div className="skeleton-item" />
      </div>
    );
  }

  return <MenuContent menu={menu} />;
}
```

## Admin Panel Example

### Example: Menu Management

```javascript
import React, { useEffect, useState } from 'react';
import useMenuStore from '../store/menuStore';

export function AdminMenuManager() {
  const { menu, loadMenu, refreshMenu, clearCache } = useMenuStore();

  useEffect(() => {
    loadMenu();
  }, []);

  return (
    <div className="admin-panel">
      <h2>Menu Management</h2>
      
      <div className="actions">
        <button onClick={() => refreshMenu()}>
          🔄 Refresh from Backend
        </button>
        <button onClick={() => clearCache()}>
          🗑️ Clear Cache
        </button>
      </div>

      <div className="menu-tree">
        {menu && Object.entries(menu).map(([category, items]) => (
          <div key={category} className="category">
            <h3>{category} ({items.length} items)</h3>
            <ul>
              {items.map(item => (
                <li key={item.id}>
                  {item.name} - €{item.price}
                  <span className="station">{item.category}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
```

## Testing Examples

### Unit Test Example

```javascript
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { getMenu, loadMenuFromAPI } from './menuService';

describe('MenuDisplay', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  it('should display menu from API', async () => {
    const mockMenu = {
      'Salads': [{ id: '1', name: 'Greek', price: 9.99, category: 'kitchen' }]
    };

    global.fetch = vi.fn(async () => ({
      ok: true,
      json: async () => mockMenu
    }));

    const result = await getMenu();
    
    expect(result.success).toBe(true);
    expect(result.menu).toEqual(mockMenu);
    expect(result.source).toBe('api');
  });

  it('should fall back to file when API fails', async () => {
    const fallbackMenu = { 'Appetizers': [{ id: '2', name: 'Fries', price: 5, category: 'kitchen' }] };

    global.fetch = vi.fn()
      .mockRejectedValueOnce(new Error('API down'))
      .mockResolvedValueOnce({
        ok: true,
        json: async () => fallbackMenu
      });

    const result = await getMenu();

    expect(result.success).toBe(true);
    expect(result.source).toBe('file');
    expect(result.apiError).toBeDefined();
  });
});
```

## CSS Skeleton Loading Example

```css
.skeleton {
  animation: shimmer 1.5s infinite;
  background: linear-gradient(
    90deg,
    #f0f0f0 25%,
    #e0e0e0 50%,
    #f0f0f0 75%
  );
  background-size: 200% 100%;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.skeleton-item {
  height: 40px;
  margin-bottom: 10px;
  border-radius: 4px;
  @applies: .skeleton;
}

.error-banner {
  background-color: #fee;
  border: 1px solid #fcc;
  border-radius: 4px;
  padding: 16px;
  margin-bottom: 16px;
}

.error-banner h3 {
  color: #c33;
  margin: 0 0 8px 0;
}

.error-banner button {
  background: #c33;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
}

.error-banner button:hover:not(:disabled) {
  background: #a22;
}

.error-banner button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
```

## Copy-Paste Ready Functions

### Hook for Menu Loading (mobile-app)
```javascript
import { useEffect } from 'react';
import useMenuStore from '../store/menuStore';

export function useMenu() {
  const { menu, isMenuSetup, menuLoadError, loadMenu, refreshMenu } = useMenuStore();

  useEffect(() => {
    if (!isMenuSetup && !menuLoadError) {
      loadMenu();
    }
  }, [isMenuSetup, menuLoadError, loadMenu]);

  return {
    menu,
    loading: !isMenuSetup && !menuLoadError,
    error: menuLoadError,
    refresh: refreshMenu
  };
}

// Usage:
// const { menu, loading, error, refresh } = useMenu();
```

### Custom Hook for Legacy UIs
```javascript
import { useEffect, useState } from 'react';
import { getMenu } from './menuService';

export function useMenuService() {
  const [menu, setMenu] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [source, setSource] = useState(null);

  useEffect(() => {
    getMenu().then(result => {
      if (result.success) {
        setMenu(result.menu);
        setSource(result.source);
      } else {
        setError(result.error);
      }
      setLoading(false);
    });
  }, []);

  const refresh = async () => {
    setLoading(true);
    const result = await getMenu({ skipCache: true });
    if (result.success) {
      setMenu(result.menu);
      setSource(result.source);
    } else {
      setError(result.error);
    }
    setLoading(false);
  };

  return { menu, loading, error, source, refresh };
}

// Usage:
// const { menu, loading, error, refresh } = useMenuService();
```

All examples are production-ready and follow best practices for React and the TavernAI architecture.
