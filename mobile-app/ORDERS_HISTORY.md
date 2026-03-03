# Orders History & Receipt Viewer

This feature allows admins and waiters to view past orders and print receipts.

## Features

### Orders History Page (`/history`)
- **Access**: Admin and Waiter roles only
- **Location**: Click the 📋 icon in the top navigation bar
- **Features**:
  - View all completed orders
  - Filter by date range (from/to)
  - Filter by table number
  - Pagination (20 items per page)
  - Click any order to view full receipt

### Receipt Viewer Page (`/receipt/:id`)
- **Features**:
  - Full receipt details with restaurant header
  - Table number and timestamp
  - Waiter name (if available)
  - Itemized list with quantities and prices
  - Subtotal, VAT (24%), and total
  - Print button for physical receipts
  - Back button to return to history

## API Endpoints

The frontend expects these backend endpoints:

### GET `/api/orders/history`
Fetch order history with optional filters.

**Query Parameters:**
- `from` (optional): Start date in YYYY-MM-DD format
- `to` (optional): End date in YYYY-MM-DD format
- `table` (optional): Table number (integer)

**Response:**
```json
[
  {
    "id": "receipt-001",
    "table": 1,
    "items": [
      {
        "id": "item-1",
        "name": "Μουσακάς",
        "menu_name": "Μουσακάς",
        "text": "2 μουσακας",
        "price": 12.00,
        "quantity": 2
      }
    ],
    "total": 29.00,
    "closed_at": "2026-02-23T12:30:00Z",
    "created_at": "2026-02-23T12:00:00Z"
  }
]
```

### GET `/api/orders/history/:receiptId`
Fetch a single receipt by ID.

**Response:**
```json
{
  "id": "receipt-001",
  "table": 1,
  "items": [...],
  "total": 29.00,
  "closed_at": "2026-02-23T12:30:00Z",
  "created_at": "2026-02-23T12:00:00Z",
  "waiter": "Γιώργος"
}
```

## Usage

### Accessing History
1. Log in as admin or waiter
2. Click the 📋 icon in the top navigation
3. View list of all completed orders

### Filtering Orders
1. Enter date range in "Από:" and "Έως:" fields
2. Enter table number in "Τραπέζι:" field (optional)
3. Click "Αναζήτηση" button
4. Click "Καθαρισμός" to clear filters

### Viewing Receipt
1. Click any order in the history list
2. View full receipt with all details
3. Click "Εκτύπωση" to print
4. Click "← Πίσω στο Ιστορικό" to go back

### Printing Receipts
1. Open any receipt
2. Click "🖨️ Εκτύπωση" button
3. Browser print dialog opens
4. Select printer and print settings
5. Print physical receipt

## Testing

### Unit Tests
Run unit tests for the history service:
```bash
npm test tests/services/historyService.test.js
```

Tests cover:
- Fetching order history with/without filters
- Fetching single receipt by ID
- Error handling for network failures
- Date and currency formatting functions

### E2E Tests
Run end-to-end tests for the full flow:
```bash
npm test tests/e2e/ordersHistory.test.js
```

Tests cover:
- Rendering history page with data
- Filtering by table and date range
- Clearing filters
- Navigation to receipt view
- Receipt rendering with all details
- Print button functionality
- Back navigation
- Error handling for non-existent receipts

## Implementation Details

### Files Added
- `src/services/historyService.js` - API client for history endpoints
- `src/pages/OrdersHistory.jsx` - History list page component
- `src/pages/OrdersHistory.css` - History page styles
- `src/pages/ReceiptView.jsx` - Receipt viewer component
- `src/pages/ReceiptView.css` - Receipt styles with print media queries
- `tests/services/historyService.test.js` - Unit tests
- `tests/e2e/ordersHistory.test.js` - E2E tests

### Files Modified
- `src/App.jsx` - Added routes for `/history` and `/receipt/:receiptId`
- `src/pages/HomePage.jsx` - Added 📋 icon for history navigation
- `mobile-app/README.md` - Updated documentation

### Print Styles
The receipt viewer includes special `@media print` styles:
- Hides controls (no-print class)
- Optimizes layout for physical receipts
- Adjusts font sizes for better readability
- Removes shadows and backgrounds

### Greek Localization
All UI text is in Greek:
- "Ιστορικό Παραγγελιών" (Orders History)
- "Από/Έως" (From/To)
- "Τραπέζι" (Table)
- "Αναζήτηση" (Search)
- "Καθαρισμός" (Clear)
- "Εκτύπωση" (Print)
- "ΣΥΝΟΛΟ" (Total)
- "ΦΠΑ" (VAT)

## Backend Requirements

The backend must implement the two history endpoints shown above. The receipts should include:
- Unique receipt ID
- Table number
- List of items with prices and quantities
- Timestamps (created_at, closed_at)
- Optional waiter name

## Future Enhancements

Potential improvements:
- Export receipts as PDF
- Email receipts to customers
- Daily/weekly sales reports
- Revenue analytics charts
- Search by menu item name
- Bulk receipt printing
