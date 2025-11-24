# Backend Integration Guide

## ✅ Integration Complete!

The mobile PWA is now fully integrated with the backend API and WebSocket system.

---

## 🔌 What's Integrated

### 1. **API Service** (`src/services/api.js`)

Complete REST API integration with all backend endpoints:

#### Order Management
- ✅ `submitOrder(table, orderText, people, bread)` - Submit new order
- ✅ `updateOrder(table, orderText, people, bread)` - Update existing order
- ✅ `getOrders(includeHistory)` - Get all orders
- ✅ `getTableMeta(table)` - Get table metadata
- ✅ `cancelItem(table, itemId)` - Cancel specific item
- ✅ `markItemDone(itemId)` - Mark item as done
- ✅ `updateItem(itemId, newText)` - Update item text

#### WebSocket Connection
- ✅ `createWebSocket(station, handlers)` - Create resilient WebSocket connection
- ✅ Auto-reconnect on disconnect
- ✅ Message queuing when offline
- ✅ Event handlers: onOpen, onMessage, onClose, onError

---

### 2. **Waiter Interface** (`src/components/WaiterView.jsx`)

Full waiter functionality integrated with backend:

#### Features
- ✅ **Table Grid** - Visual table selection (12 tables)
- ✅ **Order Form** - Submit/update orders with:
  - Multi-line order text
  - Number of people
  - Bread preference
- ✅ **Real-time Updates** - WebSocket integration
- ✅ **Order Status** - See pending/done/cancelled items
- ✅ **Item Management** - Cancel individual items
- ✅ **Table Finalization** - Clear completed tables
- ✅ **Connection Status** - Visual indicator
- ✅ **Notifications** - Receive alerts from kitchen/grill/drinks

#### WebSocket Events Handled
- `init` - Initial data load
- `new` - New item added
- `update` - Item updated
- `delete` - Item deleted
- `table_finalized` - Table cleared
- `notify` - Notification from stations

---

## 🚀 How to Use

### Start the Backend

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

### Start the Mobile App

```bash
cd mobile-app
npm run dev
```

### Test the Integration

1. **Login as Waiter**
   - Username: `waiter`
   - Password: `waiter123`

2. **Select a Table**
   - Click on any table number (1-12)

3. **Submit an Order**
   - Enter number of people (optional)
   - Check "Bread" if needed
   - Enter order items (one per line):
     ```
     2 μπύρες
     1 σαλάτα
     1 σουβλάκι χοιρινό
     ```
   - Click "Submit Order"

4. **Watch Real-time Updates**
   - Order appears in the current orders list
   - Items are routed to appropriate stations (kitchen/grill/drinks)
   - Status updates automatically via WebSocket

5. **Manage Orders**
   - Cancel individual items with ✕ button
   - Update order by editing text and clicking "Submit Order"
   - Finalize table when all items are done

---

## 🔧 Configuration

The app automatically detects the backend URL from `/config` endpoint or uses defaults:

**Default URLs:**
- HTTP: `http://localhost:8000`
- WebSocket: `ws://localhost:8000`

**Vite Proxy** (configured in `vite.config.js`):
- `/order/*` → Backend
- `/orders/*` → Backend
- `/table_meta/*` → Backend
- `/item/*` → Backend
- `/ws/*` → Backend WebSocket
- `/config` → Backend config

---

## 📡 WebSocket Protocol

### Waiter → Backend

```json
{
  "action": "finalize_table",
  "table": 5
}
```

### Backend → Waiter

**Initial Data:**
```json
{
  "action": "init",
  "orders": {
    "1": [...items],
    "2": [...items]
  },
  "meta": {
    "1": {"people": 4, "bread": true},
    "2": {"people": 2, "bread": false}
  }
}
```

**New Item:**
```json
{
  "action": "new",
  "item": {
    "id": "uuid",
    "table": 1,
    "text": "2 μπύρες",
    "category": "drinks",
    "status": "pending",
    "created_at": "2024-01-01T12:00:00Z"
  }
}
```

**Item Updated:**
```json
{
  "action": "update",
  "item": {
    "id": "uuid",
    "status": "done",
    ...
  }
}
```

**Item Deleted:**
```json
{
  "action": "delete",
  "item_id": "uuid",
  "table": 1
}
```

**Table Finalized:**
```json
{
  "action": "table_finalized",
  "table": 1
}
```

**Notification:**
```json
{
  "action": "notify",
  "message": "ετοιμα 2 μπύρες τραπέζι 1",
  "id": "uuid"
}
```

---

## 🎨 UI Components

### WaiterView
- **Location:** `src/components/WaiterView.jsx`
- **Styles:** `src/components/WaiterView.css`
- **Features:**
  - Table grid with status badges
  - Order form with validation
  - Real-time order list
  - Connection status indicator

### API Service
- **Location:** `src/services/api.js`
- **Features:**
  - Automatic backend URL detection
  - Error handling
  - WebSocket auto-reconnect
  - Message queuing

---

## 🧪 Testing Checklist

- [ ] Backend running on port 8000
- [ ] Mobile app running on port 5177
- [ ] Login as waiter
- [ ] Select table
- [ ] Submit order
- [ ] See order in current orders list
- [ ] Check WebSocket connection status (should show "Connected")
- [ ] Cancel an item
- [ ] Update order (edit text and resubmit)
- [ ] Open kitchen/grill/drinks UI and verify items appear
- [ ] Mark item as done in station UI
- [ ] Verify status updates in waiter view
- [ ] Finalize table
- [ ] Verify table clears

---

## 🔍 Troubleshooting

### WebSocket Not Connecting

**Check:**
1. Backend is running: `http://localhost:8000`
2. WebSocket endpoint accessible: `ws://localhost:8000/ws/waiter`
3. Browser console for errors
4. Network tab in DevTools

**Solution:**
- Restart backend
- Check firewall settings
- Verify proxy configuration in `vite.config.js`

### Orders Not Appearing

**Check:**
1. WebSocket connected (green dot in UI)
2. Backend console for errors
3. Network tab for failed requests

**Solution:**
- Check backend logs
- Verify order submission payload
- Test with curl/Postman

### Items Not Routing to Correct Station

**Check:**
1. `menu.json` has correct categories
2. Backend NLP classification working
3. Item text matches menu items

**Solution:**
- Check backend logs for classification results
- Verify menu.json categories (kitchen/grill/drinks)
- Test with exact menu item names

---

## 📚 Next Steps

### Remaining Work

1. **Station Views** - Implement kitchen/grill/drinks views
2. **Notifications** - Trigger PWA notifications on order ready
3. **Menu Integration** - Use menu.json from setup for autocomplete
4. **Voice Input** - Add speech-to-text for order entry
5. **Offline Mode** - Queue orders when offline

### Enhancement Ideas

- Order history view
- Table layout customization
- Print receipts
- Analytics dashboard
- Multi-language support

---

## ✅ Summary

The mobile PWA now has **full backend integration** with:

- ✅ Complete REST API integration
- ✅ Real-time WebSocket communication
- ✅ Waiter interface with table management
- ✅ Order submission and updates
- ✅ Item cancellation
- ✅ Table finalization
- ✅ Connection status monitoring
- ✅ Auto-reconnect on disconnect

**Ready for production testing!** 🎉

