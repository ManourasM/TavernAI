# TavernAI
A lightweight, local network tavern ordering app with three frontends and a small FastAPI backend:

Waiter UI — create / edit table orders, set table meta (people, bread), finalize table

Kitchen UI — see kitchen items (non-grill), confirm items as done

Grill UI — see grill items, confirm items as done

Backend (FastAPI) — stores orders in-memory (MVP), exposes REST + WebSocket endpoints, simple NLP to classify lines into grill / kitchen / drinks

## The problem

In many traditional Greek taverns — especially in rural areas — the ordering process is still completely manual. Waiters take orders on paper, bring them to the kitchen or grill, and later re-enter each item into the cashier’s machine to print the receipt.

This manual workflow causes several issues:

Time delays: Waiters spend valuable time walking between stations and rewriting orders.

Miscommunication: Handwritten notes can be unclear or lost, leading to mistakes in the kitchen or grill.

Inefficiency: During busy hours, staff are forced to juggle multiple papers and remember which table ordered what.

No live tracking: There’s no way to see which dishes are ready without physically checking each workstation.

The result is slower service, more errors, and unnecessary stress for both the staff and customers.

## The solution

TavernAI replaces the traditional pen-and-paper workflow with a smart, connected, and AI-assisted ordering system that runs entirely on a local network, without requiring internet access.

When a waiter takes an order, they simply type it on a tablet or phone. The system’s Greek-capable NLP model automatically recognizes and classifies each dish into the correct workstation — kitchen, grill, or drinks — based on the menu.

Each workstation has its own dedicated interface:

Kitchen UI: Displays only the dishes prepared in the kitchen.

Grill UI: Displays grill items separately, with live updates.

Drinks UI: (in development) will handle beverages and bar items.

As soon as the order is sent, all relevant stations receive the items instantly through WebSockets. When a dish is prepared, the staff marks it as “done,” and the waiter sees the live status at their station.

When the table is finalized, TavernAI automatically calculates the total cost using the prices defined in menu.json, allowing the receipt to be printed or recorded immediately — no manual copying, no communication delays, and no double work.

In short, TavernAI turns a traditional taverna's chaotic, paper-based workflow into a real-time, efficient, and fully connected system. It preserves the simplicity of a traditional setting while introducing the power of modern AI and automation.

## Quick Start

### Option 1: Docker (Recommended)

The easiest way to run TavernAI is using Docker:

```bash
# Start all services
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

Access the applications:
- **Waiter UI**: http://localhost:5173
- **Kitchen UI**: http://localhost:5175
- **Grill UI**: http://localhost:5174
- **Drinks UI**: http://localhost:5176
- **Backend API**: http://localhost:8000

For detailed Docker instructions, see [DOCKER.md](DOCKER.md).

### Option 2: Manual Setup

#### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download el_core_news_sm  # Optional: Greek NLP model
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### Frontend Setup (for each UI)

```bash
# Waiter UI
cd waiter-ui
npm install
npm run dev

# Kitchen UI
cd kitchen-ui
npm install
npm run dev

# Grill UI
cd grill-ui
npm install
npm run dev

# Drinks UI
cd drinks-ui
npm install
npm run dev
```

Or use the provided script:

```bash
python start_all_windows.py
```

## Features

- **Real-time Updates**: WebSocket-based live updates across all stations
- **Greek NLP**: Automatic classification of Greek menu items
- **Multi-station Support**: Separate UIs for waiter, kitchen, grill, and drinks
- **Offline-first**: Runs entirely on local network, no internet required
- **Smart Matching**: Unit-aware menu item matching (kg, λ, ml, portions)
- **Price Preservation**: Maintains custom pricing for unmatched items
- **Parentheses Support**: Handles special instructions like "(χωρίς σάλτσα)"

# Screenshots
<img width="400" height="400" alt="Screenshot 2025-10-13 142805" src="https://github.com/user-attachments/assets/e5fba5db-f395-49c0-bbc5-bb45ab57fa91" />
<img width="400" height="400" alt="Screenshot 2025-10-13 142514" src="https://github.com/user-attachments/assets/a2d1ea43-3524-4366-b213-d7e8961575ef" />
<img width="400" height="400" alt="Screenshot 2025-10-13 142621" src="https://github.com/user-attachments/assets/c164b4bb-ceb0-4da5-bb08-b5c2637aef2a" />
<img width="400" height="400" alt="Screenshot 2025-10-13 142723" src="https://github.com/user-attachments/assets/6b88df79-9ecc-49f3-8986-e146bb575396" />

