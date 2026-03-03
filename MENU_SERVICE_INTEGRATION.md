# Frontend Menu Service Integration Guide

## Overview

This guide documents the new `menuService` abstraction layer that enables dynamic menu loading from the TavernAI backend API with automatic fallback to static `menu.json`.

## Architecture

### Menu Loading Strategy

The `menuService` implements a three-tier strategy:

```
1. Try Backend API (/api/menu)
       ↓ (on success) → Cache Result → Return to App
       ↓ (on failure)
2. Fall back to Static File (/menu.json)
       ↓ (on success) → Cache Result → Return to App
       ↓ (on failure)
3. Return Error (all sources exhausted)
```

### Cache Strategy

- **Mobile App**: Uses `localStorage` with 1-hour TTL via Zustand persistence
- **Legacy UIs** (waiter/kitchen/grill/drinks): Uses `sessionStorage` (cleared on page close)
- Fallback to static file is always available offline

## Files Changed

### New Services

- **`mobile-app/src/services/menuService.js`** - Main service with API/file loading
- **`waiter-ui/src/menuService.js`** - Standalone copy for legacy UI
- **`kitchen-ui/src/menuService.js`** - Standalone copy for kitchen station
- **`grill-ui/src/menuService.js`** - Standalone copy for grill station
- **`drinks-ui/src/menuService.js`** - Standalone copy for drinks station

### Updated Files

- **`mobile-app/src/store/menuStore.js`** - Now imports and uses menuService
  - Updated `loadMenu()` to call `menuService.getMenu()`
  - Added `refreshMenu()` method for force refresh
  - Added `clearCache()` method for cache management
  - Added `menuLoadError` state for error tracking

### New Tests

- **`mobile-app/src/services/menuService.test.js`** - Comprehensive test suite (30+ test cases)

## API

### menuService.getMenu(options)

Main function for loading menu with automatic fallback.

**Parameters:**
```javascript
{
  forceRefresh: boolean  // Skip cache, reload from source (mobile-app only, default: false)
  skipCache: boolean     // Skip cache, reload from source (legacy UIs, default: false)
}
```

**Returns:**
```javascript
{
  success: boolean,      // true if menu loaded
  menu: Object,          // Menu keyed by category (e.g., { "Salads": [...], ... })
  source: string,        // 'api', 'file', or 'cache'
  apiError: string|null  // Error message if API failed (null if successful or cached)
}
```

**Example:**
```javascript
import { getMenu } from './services/menuService';

// Load with caching
const result = await getMenu();
if (result.success) {
  console.log(`Menu loaded from ${result.source}:`, result.menu);
} else {
  console.error('Failed to load menu:', result.error);
}

// Force refresh (skip cache)
const fresh = await getMenu({ forceRefresh: true });
```

### menuService.loadMenuFromAPI()

Load menu directly from backend API (no fallback).

**Returns:** `Promise<Object>` - Menu object or throws error

```javascript
try {
  const menu = await loadMenuFromAPI();
} catch (error) {
  console.error('API failed:', error.message);
}
```

### menuService.loadMenuFromFile()

Load menu from static public/menu.json (no fallback).

**Returns:** `Promise<Object>` - Menu object or throws error

### menuService.clearMenuCache() (mobile-app only)

Clear localStorage cache (useful for testing or settings).

```javascript
import { clearMenuCache } from './services/menuService';
clearMenuCache();
```

## Integration Examples

### In mobile-app components

Using the Zustand store:

```javascript
import useMenuStore from '../store/menuStore';

function MyComponent() {
  const { menu, isMenuSetup, menuLoadError, loadMenu, refreshMenu } = useMenuStore();

  useEffect(() => {
    loadMenu();
  }, [loadMenu]);

  if (!isMenuSetup && !menuLoadError) {
    return <div>Loading menu...</div>;
  }

  if (menuLoadError) {
    return (
      <div>
        <p>Error: {menuLoadError}</p>
        <button onClick={() => refreshMenu()}>Retry</button>
      </div>
    );
  }

  return (
    <div>
      {menu && Object.entries(menu).map(([category, items]) => (
        <div key={category}>
          <h2>{category}</h2>
          {items.map(item => (
            <div key={item.id}>{item.name} - ${item.price}</div>
          ))}
        </div>
      ))}
    </div>
  );
}
```

### In legacy UIs (waiter/kitchen/grill/drinks)

Direct service usage:

```javascript
import { getMenu } from './menuService';

useEffect(() => {
  const loadMenu = async () => {
    const result = await getMenu();
    if (result.success) {
      setMenu(result.menu);
      console.log(`Loaded from ${result.source}`);
    } else {
      console.error('Menu load failed:', result.error);
    }
  };
  
  loadMenu();
}, []);

// Force refresh if needed
async function handleRefresh() {
  const result = await getMenu({ skipCache: true });
  if (result.success) {
    setMenu(result.menu);
  }
}
```

## Behavior in Different Scenarios

### Scenario 1: Backend Running (Normal)
```
[App Start] → API endpoint available → Load from API → Cache → Display menu
```

### Scenario 2: Backend Down (Offline)
```
[App Start] → API fails (ConnectionError) → Fall back to /menu.json → Cache → Display menu
```

### Scenario 3: API Updated Menu
```
[App Start] → Load from localStorage cache → Display cached menu
[Manual Refresh] → Force reload from API → Display new menu → Update cache
```

### Scenario 4: LAN Access
```
[Phone on network] → Backend at 192.168.1.100:8000 → getConfig() handles IP replacement → 
API call succeeds → Load from API → Display menu
```

## Error Handling

### API Errors
- Network errors → Fall back to file
- HTTP 5xx errors → Fall back to file
- JSON parse errors → Fall back to file
- Empty menu response → Fall back to file

### File Errors
- 404 Not Found → Return error, show offline message
- Parse errors → Return error after trying API

### Error Messages in Console

All errors are logged with `[menuService]` prefix for easy filtering:
```
[menuService] Fetching menu from: http://localhost:8000/api/menu
[menuService] Loaded menu from API: ["Salads", "Appetizers", ...]
[menuService] API load failed, falling back to menu.json: HTTP 503 Service Unavailable
[menuService] Loaded menu from file: ["Salads", "Appetizers", ...]
[menuService] Using session cache
```

## Testing

Run tests for menuService:

```bash
cd mobile-app
npm test -- menuService.test.js
```

Test coverage includes:
- ✅ Successful API loading
- ✅ Successful file loading
- ✅ API error → file fallback
- ✅ All sources fail
- ✅ Cache hit and miss
- ✅ Force refresh
- ✅ Cache corruption handling
- ✅ sessionStorage quota errors
- ✅ LAN IP replacement
- ✅ Invalid responses

## Backend API Contract

The backend `/api/menu` endpoint must return:

```json
{
  "CategoryName": [
    {
      "id": "item_id",
      "name": "Item Name",
      "price": 9.99,
      "category": "station_id"
    }
  ]
}
```

See `backend/app/api/menu_router.py` for implementation.

## Migration Path from Static Import

### Old Approach
```javascript
import menu from './menu.json';

function App() {
  return <div>{menu.Salads}</div>;
}
```

### New Approach
```javascript
import { getMenu } from './services/menuService';

function App() {
  const [menu, setMenu] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMenu().then(result => {
      if (result.success) {
        setMenu(result.menu);
      }
      setLoading(false);
    });
  }, []);

  if (loading) return <Skeleton />;
  return <div>{menu.Salads}</div>;
}
```

## Deployment Checklist

- [ ] Confirm backend `/api/menu` endpoint is running
- [ ] Menu data is seeded in database or fallback file exists
- [ ] All frontends (mobile-app, waiter-ui, etc.) have menuService.js
- [ ] Mobile-app menuStore imports menuService
- [ ] Components call `loadMenu()` on app initialization
- [ ] User can see loading indicator while menu loads
- [ ] Fallback to static menu.json works when backend is down
- [ ] Console logs show expected sources (api, file, or cache)
- [ ] Tests pass: `npm test`

## Troubleshooting

### Menu shows "Error loading" after restart
**Symptoms:** Backend is running, but menu doesn't load

**Steps:**
1. Check console for `[menuService]` logs
2. Verify `/api/menu` returns valid JSON:
   ```bash
   curl http://localhost:8000/api/menu | jq
   ```
3. Ensure database has menu data (see `backend/README_DB.md`)
4. Check CORS if accessing from different domain

### Menu appears outdated
**Cause:** Showing cached version even after backend menu updated

**Solution:**
- Mobile app: Click "Refresh" or call `useMenuStore().refreshMenu()`
- Legacy UIs: Reload page (sessionStorage clears)
- Force all clients to refresh: Restart backend

### Static menu.json not loading as fallback
**Symptoms:** API fails, no fallback occurs

**Steps:**
1. Verify `/menu.json` exists in `public/` folder
2. Check network tab: is `/menu.json` request successful?
3. Ensure `menu.json` is valid JSON: `cat public/menu.json | jq`

## Performance Considerations

- **First Load:** API call (async) + parsing
- **Cached Load:** Instant (no network call)
- **Legacy UIs:** sessionStorage (not persistent across page loads)
- **Mobile App:** localStorage + Zustand (persists across app restarts)

For busy restaurants, consider:
- Setting longer cache TTL in mobile-app (edit `CACHE_TTL_MINUTES`)
- Pre-loading menu on app boot (add `useEffect` early in App.jsx)
- Only refreshing on user action (not on every page visit)

## Future Enhancements

- [ ] Streaming menu updates via WebSocket (when admin updates menu)
- [ ] Menu version tracking (cache invalidation on version change)
- [ ] Partial menu updates (only send changed items)
- [ ] Sync custom local edits back to API
- [ ] Offline mode with local menu persistence
