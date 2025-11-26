# TavernAI - Tavern Ordering System

A modern, lightweight tavern ordering and management system that runs entirely on your local network.

## 🎯 What's Included

**Mobile App (PWA)** — All-in-one Progressive Web App with:
- Waiter interface for table management
- Kitchen, Grill, and Drinks station views
- Admin panel for menu and user management
- Works on phones, tablets, and computers
- Can be installed as a native app

**Legacy UIs** — Individual interfaces for:
- Waiter UI — Create/edit table orders, set table metadata, finalize tables
- Kitchen UI — View and confirm kitchen items
- Grill UI — View and confirm grill items
- Drinks UI — View and confirm drink orders

**Backend (FastAPI)** — Lightweight server with:
- REST API + WebSocket for real-time updates
- Greek NLP for automatic item classification
- Menu management with 97 items
- In-memory storage (MVP)

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

## 🚀 Quick Start

### Option 1: Docker (Recommended)

The easiest way to run TavernAI is using Docker:

```bash
# Mobile App Only (Recommended for most users)
make mobile-only
# or
docker-compose -f docker/docker-compose.mobile.yml up -d

# All Services (Mobile App + Legacy UIs)
make up
# or
docker-compose -f docker/docker-compose.yml up -d

# Development Mode (with hot-reload)
make mobile-dev
# or
make dev
```

**Access the applications:**
- 🌟 **Mobile App (PWA)**: http://localhost:5177
- **Waiter UI**: http://localhost:5173
- **Kitchen UI**: http://localhost:5175
- **Grill UI**: http://localhost:5174
- **Drinks UI**: http://localhost:5176
- **Backend API**: http://localhost:8000

**Access from your phone:**
1. Find your computer's IP: `ipconfig` (Windows) or `ifconfig` (Linux/Mac)
2. Open browser on phone: `http://YOUR_IP:5177`
3. Install as PWA for best experience!

For detailed Docker instructions, see [docs/DOCKER.md](docs/DOCKER.md).

### Option 2: Manual Setup (Windows)

#### Backend Setup

```bash
cd backend
setup.bat
start.bat
```

The backend will start on `http://0.0.0.0:8000` (accessible from network).

#### Mobile App Setup

```bash
cd mobile-app
npm install
npm run dev
```

The mobile app will start on `http://localhost:5177`.

For detailed setup instructions, see [mobile-app/QUICK_START.md](mobile-app/QUICK_START.md).

## ✨ Features

### Mobile App (PWA)
- ✅ **All-in-one interface** - Waiter, Kitchen, Grill, Drinks, and Admin in one app
- ✅ **Progressive Web App** - Install on any device, works offline
- ✅ **Modern UI** - Professional design with Greek language support
- ✅ **17 Tables** - Color-coded status (free, occupied, finalized)
- ✅ **Real-time updates** - WebSocket-based live synchronization
- ✅ **Sound notifications** - Audio alerts for new orders and completions
- ✅ **Item aggregation** - Smart grouping of items by station
- ✅ **Total price calculation** - Automatic pricing from menu.json
- ✅ **Menu management** - 97 items organized by category
- ✅ **Network accessible** - Access from any device on your network

### Backend
- ✅ **Greek NLP** - Automatic classification of Greek menu items
- ✅ **Multi-station routing** - Smart routing to kitchen, grill, or drinks
- ✅ **WebSocket support** - Real-time bidirectional communication
- ✅ **REST API** - Full CRUD operations for orders and items
- ✅ **Offline-first** - Runs entirely on local network, no internet required
- ✅ **Smart matching** - Unit-aware menu item matching (kg, λ, ml, portions)
- ✅ **Price preservation** - Maintains custom pricing for unmatched items
- ✅ **Special instructions** - Handles notes like "(χωρίς σάλτσα)"

## 📁 Project Structure

```
TavernAI/
├── backend/              # FastAPI backend server
│   ├── app/             # Application code
│   ├── data/            # Menu data (menu.json)
│   ├── setup.bat        # Windows setup script
│   └── start.bat        # Windows start script
├── mobile-app/          # Mobile PWA (All-in-one)
│   ├── src/             # React source code
│   ├── public/          # Static assets
│   └── docs/            # Mobile app documentation
├── waiter-ui/           # Legacy waiter interface
├── kitchen-ui/          # Legacy kitchen interface
├── grill-ui/            # Legacy grill interface
├── drinks-ui/           # Legacy drinks interface
├── docker/              # Docker configuration
│   ├── docker-compose.yml           # Production setup
│   ├── docker-compose.dev.yml       # Development setup
│   ├── docker-compose.mobile.yml    # Mobile-only setup
│   ├── Dockerfile.frontend          # Frontend build
│   └── nginx.conf                   # Nginx config
├── docs/                # Documentation
│   ├── DOCKER.md                    # Docker guide
│   ├── DOCKER_QUICK_REFERENCE.md    # Quick reference
│   └── ...
├── Makefile             # Docker shortcuts
└── README.md            # This file
```

## 📚 Documentation

- **[docs/DOCKER.md](docs/DOCKER.md)** - Complete Docker setup guide
- **[docs/DOCKER_QUICK_REFERENCE.md](docs/DOCKER_QUICK_REFERENCE.md)** - Quick command reference
- **[mobile-app/QUICK_START.md](mobile-app/QUICK_START.md)** - Mobile app quick start
- **[mobile-app/DOCKER_GUIDE.md](mobile-app/DOCKER_GUIDE.md)** - Mobile app Docker guide
- **[mobile-app/PWA_DEPLOYMENT.md](mobile-app/PWA_DEPLOYMENT.md)** - PWA deployment guide

## 🛠️ Technology Stack

**Frontend:**
- React 18
- Vite
- Zustand (state management)
- PWA (Progressive Web App)
- WebSocket client

**Backend:**
- FastAPI
- Python 3.12
- spaCy (Greek NLP)
- WebSocket server
- Uvicorn

**DevOps:**
- Docker & Docker Compose
- Nginx (production)
- Multi-stage builds

## 📱 Screenshots

<img width="400" height="400" alt="Screenshot 2025-10-13 142805" src="https://github.com/user-attachments/assets/e5fba5db-f395-49c0-bbc5-bb45ab57fa91" />
<img width="400" height="400" alt="Screenshot 2025-10-13 142514" src="https://github.com/user-attachments/assets/a2d1ea43-3524-4366-b213-d7e8961575ef" />
<img width="400" height="400" alt="Screenshot 2025-10-13 142621" src="https://github.com/user-attachments/assets/c164b4bb-ceb0-4da5-bb08-b5c2637aef2a" />
<img width="400" height="400" alt="Screenshot 2025-10-13 142723" src="https://github.com/user-attachments/assets/6b88df79-9ecc-49f3-8986-e146bb575396" />

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 💡 Use Cases

Perfect for:
- Traditional Greek taverns
- Small restaurants
- Family-owned eateries
- Any establishment wanting to digitize their ordering process
- Offline-first environments without reliable internet

## 🌟 Why TavernAI?

- **No internet required** - Runs entirely on local network
- **Simple setup** - Docker or manual, your choice
- **Modern UI** - Professional design that's easy to use
- **Greek language** - Built for Greek taverns
- **Real-time** - Instant updates across all stations
- **Free & Open Source** - MIT licensed

