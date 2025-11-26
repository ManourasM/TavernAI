# Windows Quick Start Guide

This guide is specifically for Windows users who want to run TavernAI.

## 🚀 Quick Start Options

### Option 1: Docker (Recommended)

#### Prerequisites
- Install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
- Make sure Docker Desktop is running

#### Start the Application

**Mobile App Only (Recommended):**
```powershell
docker-compose -f docker/docker-compose.mobile.yml up -d
```

**All Services:**
```powershell
docker-compose -f docker/docker-compose.yml up -d
```

**Development Mode (with hot-reload):**
```powershell
docker-compose -f docker/docker-compose.dev.yml up
```

#### Access the Application

- **Mobile App**: http://localhost:5177
- **Backend API**: http://localhost:8000

#### Stop the Application

```powershell
docker-compose -f docker/docker-compose.yml down
```

---

### Option 2: Manual Setup (No Docker)

#### Prerequisites
- Python 3.12 or higher
- Node.js 20 or higher

#### Backend Setup

1. Open PowerShell or Command Prompt
2. Navigate to the backend folder:
   ```powershell
   cd backend
   ```

3. Run the setup script:
   ```powershell
   .\setup.bat
   ```

4. Start the backend:
   ```powershell
   .\start.bat
   ```

The backend will start on `http://0.0.0.0:8000` (accessible from your network).

#### Mobile App Setup

1. Open a **new** PowerShell or Command Prompt window
2. Navigate to the mobile-app folder:
   ```powershell
   cd mobile-app
   ```

3. Install dependencies:
   ```powershell
   npm install
   ```

4. Start the development server:
   ```powershell
   npm run dev
   ```

The mobile app will start on `http://localhost:5177`.

---

## 📱 Access from Your Phone

### 1. Find Your Computer's IP Address

Open PowerShell and run:
```powershell
ipconfig
```

Look for "IPv4 Address" under your active network adapter (e.g., `192.168.1.174`).

### 2. Make Sure Both Devices Are on the Same WiFi

Your phone and computer must be connected to the same WiFi network.

### 3. Open the App on Your Phone

Open your phone's browser and go to:
```
http://YOUR_COMPUTER_IP:5177
```

Example: `http://192.168.1.174:5177`

### 4. Install as PWA (Optional)

**On iPhone (Safari):**
1. Tap the Share button (square with arrow)
2. Scroll down and tap "Add to Home Screen"
3. Tap "Add"

**On Android (Chrome):**
1. Tap the menu (three dots)
2. Tap "Install App" or "Add to Home Screen"

The app will now appear on your home screen and work like a native app!

---

## 🛠️ Common Commands

### Docker Commands

```powershell
# Start mobile app only
docker-compose -f docker/docker-compose.mobile.yml up -d

# Start all services
docker-compose -f docker/docker-compose.yml up -d

# View logs
docker-compose -f docker/docker-compose.yml logs -f

# View logs for specific service
docker-compose -f docker/docker-compose.yml logs -f mobile-app
docker-compose -f docker/docker-compose.yml logs -f backend

# Restart services
docker-compose -f docker/docker-compose.yml restart

# Stop services
docker-compose -f docker/docker-compose.yml down

# Rebuild and restart
docker-compose -f docker/docker-compose.yml up -d --build
```

### Manual Setup Commands

```powershell
# Backend
cd backend
.\setup.bat          # First time only
.\start.bat          # Start backend

# Mobile App
cd mobile-app
npm install          # First time only
npm run dev          # Start mobile app
```

---

## 🐛 Troubleshooting

### Docker Desktop Not Running

**Error:** "Cannot connect to the Docker daemon"

**Solution:** Start Docker Desktop from the Start menu.

### Port Already in Use

**Error:** "Port 5177 is already allocated"

**Solution:** Stop the service using that port or change the port in the docker-compose file.

### Can't Access from Phone

**Checklist:**
1. ✅ Computer and phone on same WiFi?
2. ✅ Windows Firewall allowing connections?
3. ✅ Using correct IP address?
4. ✅ Backend and mobile app both running?

**Solution:** Check Windows Firewall settings and allow Python/Node through the firewall.

### WebSocket Connection Failed

**Error:** "WebSocket connection failed"

**Solution:** 
1. Make sure backend is running
2. Check backend logs: `docker-compose -f docker/docker-compose.yml logs backend`
3. Restart services: `docker-compose -f docker/docker-compose.yml restart`

---

## 📚 More Information

- **[README.md](README.md)** - Project overview
- **[docs/DOCKER.md](docs/DOCKER.md)** - Complete Docker guide
- **[mobile-app/QUICK_START.md](mobile-app/QUICK_START.md)** - Mobile app guide
- **[docs/NETWORK_ACCESS_GUIDE.md](docs/NETWORK_ACCESS_GUIDE.md)** - Network setup

---

## 💡 Tips

- **Use Docker** for the easiest setup
- **Use mobile-only** configuration for lighter resource usage
- **Install as PWA** on your phone for the best experience
- **Check firewall** if you can't access from phone
- **Use PowerShell** instead of Command Prompt for better compatibility

---

## 🎯 Recommended Setup

For most users, we recommend:

1. **Install Docker Desktop**
2. **Run mobile app only:**
   ```powershell
   docker-compose -f docker/docker-compose.mobile.yml up -d
   ```
3. **Access from computer:** http://localhost:5177
4. **Access from phone:** http://YOUR_IP:5177
5. **Install as PWA** on your phone

This gives you the full functionality with minimal setup! 🚀

