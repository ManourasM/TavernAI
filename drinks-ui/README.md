# Drinks Station UI

This is the drinks station interface for the Tavern Ordering System. It displays all drink orders (beers, wines, spirits, soft drinks) and allows the bartender to mark them as done.

## Features

- **Real-time updates** via WebSocket connection to backend
- **Aggregated view** showing total quantities of each drink across all tables
- **Table-by-table view** showing individual orders with timestamps
- **Sound notifications** when new drink orders arrive
- **Mark as done** functionality with checkbox selection
- **Responsive design** works on desktop and mobile devices

## Running the Drinks UI

### Development Mode

```bash
npm run dev
```

The drinks UI will start on port **5176** by default.

### Using the Start Script

The easiest way to start all services including the drinks UI is to use the main start script:

```bash
python start_all_windows.py
```

This will start:
- Backend (port 8000)
- Waiter UI (port 5173)
- Grill UI (port 5174)
- Kitchen UI (port 5175)
- **Drinks UI (port 5176)**

## How It Works

1. The drinks UI connects to the backend WebSocket endpoint at `/ws/drinks`
2. It receives all items with `category: "drinks"` from the menu
3. Bartender can check off drinks as they're prepared
4. Clicking "Επιβεβαίωση" (Confirm) marks all checked drinks as done
5. Done drinks are removed from the display and sent back to the waiter UI

## Configuration

- **Port**: 5176 (configured in `vite.config.js`)
- **Station**: "drinks" (configured in `src/App.jsx`)
- **Title**: "ΠΟΤΑ" (Greek for "Drinks")

## Dependencies

Same as kitchen-ui and grill-ui:
- React 19.1.1
- Vite 7.1.0
- ESLint for code quality

