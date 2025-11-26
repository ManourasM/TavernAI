# Network Access Guide

## Problem
When accessing the mobile app from your phone using the network IP (e.g., `http://192.168.1.174:5177`), you get connection errors because the backend is only listening on `localhost`.

## Solution

### 1. Start Backend with Network Access

**Option A: Use the batch script (Recommended for CMD)**

```bash
cd backend
start.bat
```

**Option B: Use the PowerShell script (Recommended for PowerShell)**

```powershell
cd backend
.\start.ps1
```

**Option C: Manual command**

```bash
cd backend
venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

All options will start the backend on `0.0.0.0:8000`, making it accessible from the network.

### 2. Start Mobile App

```bash
cd mobile-app
npm run dev
```

The mobile app is already configured with `--host` flag, so it will show the network URL.

### 3. Access from Phone

1. Look for the **Network URL** in the terminal output:
   ```
   ➜  Local:   http://localhost:5177/
   ➜  Network: http://192.168.1.174:5177/
   ```

2. Open the **Network URL** on your phone's browser

3. The app should now connect successfully to the backend!

---

## Windows Firewall

If you still can't connect, Windows Firewall might be blocking the connections:

1. When you start the backend or mobile app, Windows may show a firewall prompt
2. **Click "Allow access"** for both Private and Public networks
3. If you missed the prompt, you can manually allow it:
   - Open Windows Defender Firewall
   - Click "Allow an app through firewall"
   - Find Python (for backend) and Node (for mobile app)
   - Check both Private and Public boxes

---

## Verification

To verify everything is working:

1. **Backend**: Open `http://192.168.1.174:8000/config` on your phone
   - You should see JSON with backend configuration

2. **Mobile App**: Open `http://192.168.1.174:5177` on your phone
   - You should see the login page
   - After login, check for "Connected" status (green) in the waiter view

---

## Troubleshooting

### Still seeing "Disconnected"?

1. Make sure backend is running with `--host 0.0.0.0`
2. Check Windows Firewall settings
3. Make sure both devices are on the same WiFi network
4. Try restarting both backend and mobile app

### Can't access from phone?

1. Verify your computer's IP address: `ipconfig` (look for IPv4 Address)
2. Make sure the IP in the URL matches your computer's IP
3. Try disabling Windows Firewall temporarily to test
4. Check if your router has AP isolation enabled (disable it)

---

## Quick Start (All Services)

To start all services at once with network access, use:

```bash
python start_all_windows.py
```

This will start:
- Backend on `0.0.0.0:8000`
- Waiter UI on `0.0.0.0:5173`
- Kitchen UI on `0.0.0.0:5175`
- Grill UI on `0.0.0.0:5174`
- Drinks UI on `0.0.0.0:5176`

All services will be accessible from the network!

