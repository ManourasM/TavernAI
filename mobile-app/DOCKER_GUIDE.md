# Docker Guide for Mobile App

This guide explains how to run the Mobile App (PWA) using Docker.

## Quick Start

### Option 1: Mobile App Only (Recommended)

If you only want to run the mobile app without the individual station UIs:

```bash
# From the project root directory
make mobile-only
```

Or using docker-compose directly:

```bash
docker-compose up -d backend mobile-app
```

This starts:
- Backend API on port 8000
- Mobile App on port 5177

### Option 2: All Services

To run all services including the legacy UIs:

```bash
make up
# or
docker-compose up -d
```

This starts:
- Backend API on port 8000
- Mobile App on port 5177
- Waiter UI on port 5173
- Kitchen UI on port 5175
- Grill UI on port 5174
- Drinks UI on port 5176

---

## Development Mode

For development with hot-reload:

```bash
# Mobile app only
make mobile-dev

# All services
make dev
```

In development mode:
- Code changes are reflected immediately
- Source code is mounted as a volume
- Vite dev server runs with hot module replacement

---

## Accessing the Mobile App

### From Your Computer

Open your browser and go to:
```
http://localhost:5177
```

### From Your Phone/Tablet

1. **Find your computer's IP address**:
   
   **Windows**:
   ```bash
   ipconfig
   ```
   Look for "IPv4 Address" (e.g., 192.168.1.174)
   
   **Linux/Mac**:
   ```bash
   ifconfig
   # or
   ip addr show
   ```

2. **Make sure your phone and computer are on the same WiFi network**

3. **Open your phone's browser** and go to:
   ```
   http://YOUR_COMPUTER_IP:5177
   ```
   Example: `http://192.168.1.174:5177`

4. **Install as PWA** (optional but recommended):
   
   **iOS (Safari)**:
   - Tap the Share button (square with arrow)
   - Scroll down and tap "Add to Home Screen"
   - Tap "Add"
   
   **Android (Chrome)**:
   - Tap the menu (three dots)
   - Tap "Install App" or "Add to Home Screen"
   
   The app will now appear on your home screen and work like a native app!

---

## Docker Commands

### View Logs

```bash
# All services
docker-compose logs -f

# Mobile app only
docker-compose logs -f mobile-app

# Backend only
docker-compose logs -f backend
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart mobile app only
docker-compose restart mobile-app

# Restart backend only
docker-compose restart backend
```

### Stop Services

```bash
# Stop all
docker-compose down

# Stop but keep volumes (preserves data)
docker-compose down
```

### Rebuild After Changes

If you make changes to the code and want to rebuild:

```bash
# Rebuild all
docker-compose build

# Rebuild mobile app only
docker-compose build mobile-app

# Rebuild and restart
docker-compose up -d --build mobile-app
```

---

## Troubleshooting

### Port Already in Use

If port 5177 is already in use, you can change it in `docker-compose.yml`:

```yaml
mobile-app:
  ports:
    - "8080:80"  # Change 5177 to any available port
```

### Can't Access from Phone

1. **Check firewall**: Make sure Windows Firewall allows connections on port 5177
2. **Check network**: Ensure phone and computer are on the same WiFi
3. **Check IP**: Verify you're using the correct IP address
4. **Check containers**: Run `docker-compose ps` to ensure services are running

### WebSocket Connection Failed

1. **Check backend**: Make sure backend is running and healthy
   ```bash
   docker-compose ps backend
   ```

2. **Check logs**:
   ```bash
   docker-compose logs backend
   docker-compose logs mobile-app
   ```

3. **Restart services**:
   ```bash
   docker-compose restart backend mobile-app
   ```

---

## Production Deployment

For production deployment:

1. **Use environment variables** for configuration
2. **Enable HTTPS** with a reverse proxy (nginx, Traefik, Caddy)
3. **Set up proper logging** and monitoring
4. **Use Docker secrets** for sensitive data
5. **Consider orchestration** (Docker Swarm, Kubernetes) for scaling

Example with Traefik reverse proxy:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.mobile-app.rule=Host(`tavern.example.com`)"
  - "traefik.http.routers.mobile-app.entrypoints=websecure"
  - "traefik.http.routers.mobile-app.tls.certresolver=letsencrypt"
```

---

## What's Included in the Mobile App

The Mobile App (PWA) includes all functionality in one interface:

✅ **Waiter Interface**
- 17 tables with color-coded status
- Order submission and editing
- Real-time updates
- Total price calculation

✅ **Station Views**
- Kitchen station
- Grill station
- Drinks station
- Item aggregation
- Sound notifications

✅ **Admin Panel**
- Menu management (97 items)
- User management
- Endpoint configuration

✅ **PWA Features**
- Offline support
- Install to home screen
- Push notifications (future)
- Modern, professional UI
- Greek language throughout

---

## Next Steps

After starting the containers:

1. Access the app at `http://localhost:5177` or `http://YOUR_IP:5177`
2. Login with your credentials
3. Start taking orders!

For more information, see:
- [QUICK_START.md](./QUICK_START.md) - Quick start guide
- [PWA_DEPLOYMENT.md](./PWA_DEPLOYMENT.md) - PWA deployment guide
- [BACKEND_INTEGRATION.md](./BACKEND_INTEGRATION.md) - Backend integration details
- [../DOCKER.md](../DOCKER.md) - Main Docker documentation

