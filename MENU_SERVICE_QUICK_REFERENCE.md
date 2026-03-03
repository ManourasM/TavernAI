# Menu Service Quick Reference

## TL;DR

Your app now loads menu from the backend API with automatic fallback to static file.

### Mobile App (Zustand)
```javascript
import useMenuStore from '../store/menuStore';

// In component:
const { menu, loadMenu } = useMenuStore();

useEffect(() => {
  loadMenu();  // Loads from API with fallback
}, []);
```

### Legacy UIs (Direct)
```javascript
import { getMenu } from './menuService';

useEffect(() => {
  getMenu().then(result => {
    if (result.success) setMenu(result.menu);
  });
}, []);
```

## What Changed?

| Before | After |
|--------|-------|
| `import menu from './menu.json'` | `import { getMenu } from './menuService'` |
| Static, synchronous | Dynamic, async with API |
| No fallback on API down | Automatic /menu.json fallback |
| No cache (static import) | Cached (localStorage or sessionStorage) |

## Start Here

1. **Backend running?** Yes → API loads menu automatically
2. **Backend down?** Falls back to `public/menu.json` (no changes needed)
3. **Want fresh menu?** Call `getMenu({ forceRefresh: true })` on mobile or `getMenu({ skipCache: true })` on legacy UIs

## Files Modified

```
mobile-app/
  src/
    store/menuStore.js          (Updated)
    services/menuService.js     (New)
    services/menuService.test.js (New)

waiter-ui/src/menuService.js    (New)
kitchen-ui/src/menuService.js   (New)
grill-ui/src/menuService.js     (New)
drinks-ui/src/menuService.js    (New)

(New doc)
MENU_SERVICE_INTEGRATION.md
```

## Common Tasks

### Show loading state while menu loads
```javascript
const [loading, setLoading] = useState(true);

useEffect(() => {
  getMenu().then(() => setLoading(false));
}, []);

if (loading) return <Skeleton />;
return <Menu data={menu} />;
```

### Refresh menu manually
```javascript
// Mobile
await useMenuStore().refreshMenu();

// Legacy UI
await getMenu({ skipCache: true });
```

### Check which source was used
```javascript
const result = await getMenu();
console.log(`Loaded from: ${result.source}`);  // 'api', 'file', or 'cache'
```

### Handle network errors
```javascript
const result = await getMenu();
if (!result.success) {
  console.error('Menu failed:', result.error);
  // Show retry button
}
```

## Console Debug Output

Look for `[menuService]` logs:
```
[menuService] Fetching menu from: http://localhost:8000/api/menu
[menuService] Loaded menu from API: ["Salads", "Appetizers", ...]
[menuService] Using session cache
[menuService] API load failed, falling back to menu.json: HTTP 503
[menuService] Loaded menu from file: ["Salads", "Appetizers", ...]
```

## Return Value Structure

```javascript
{
  success: true,           // Got menu successfully
  menu: {                  // Menu data object
    "Salads": [...],
    "Appetizers": [...]
  },
  source: "api",           // Where it came from
  apiError: null,          // Error message if API failed
  error: undefined         // Only present on full failure
}
```

## Testing

```bash
cd mobile-app
npm test -- menuService.test.js
```

## Fallback Sequence

```
API available → Load from API → Success ✓
         ↓
API 503 Error → Try /menu.json → Success ✓
         ↓
No /menu.json → Return error
```

## LAN Access

Your phone connects to `192.168.1.100:8000`? No problem.
The `getConfig()` helper automatically replaces localhost with your LAN IP.

## One-Pager for Deployment

- ✅ Backend `/api/menu` endpoint working
- ✅ `public/menu.json` exists as fallback
- ✅ menuService.js in all UI folders
- ✅ menuStore imports menuService (mobile-app)
- ✅ Components call `loadMenu()` on init
- ✅ Console shows `[menuService]` logs on startup

## FAQ

**Q: Will offline users lose the menu?**
A: No. Fallback to static `/menu.json` keeps working. Desktop apps get localStorage cache.

**Q: How often is the cache refreshed?**
A: Mobile-app: 1 hour (edit `CACHE_TTL_MINUTES`). Legacy UIs: Per session.

**Q: Does the API menu sync back to app edits?**
A: Not yet. That's marked as TODO. Currently, OCR/manual edits stay local.

**Q: Can users force refresh the menu?**
A: Yes. Mobile: `refreshMenu()` button. Legacy: Reload page or manual force refresh call.

**Q: What if API returns wrong data?**
A: Error logged, fallback to file. Check backend logs and database.
