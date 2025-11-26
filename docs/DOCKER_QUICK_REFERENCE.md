# Docker Quick Reference

## 🚀 Start Services

```bash
# Mobile App Only (Recommended)
make mobile-only
# or
docker-compose -f docker-compose.mobile.yml up -d

# All Services
make up
# or
docker-compose up -d

# Development Mode (Hot-reload)
make mobile-dev          # Mobile app only
make dev                 # All services
```

---

## 🛑 Stop Services

```bash
make down
# or
docker-compose down
```

---

## 📊 View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f mobile-app
docker-compose logs -f backend
```

---

## 🔄 Restart Services

```bash
# All services
docker-compose restart

# Specific service
docker-compose restart mobile-app
docker-compose restart backend
```

---

## 🔨 Rebuild

```bash
# Rebuild all
docker-compose build

# Rebuild specific service
docker-compose build mobile-app

# Rebuild and restart
docker-compose up -d --build mobile-app
```

---

## 🧹 Clean Up

```bash
# Remove containers and networks
docker-compose down

# Remove containers, networks, and volumes
docker-compose down -v

# Remove everything including images
make clean
```

---

## 📱 Access URLs

### From Computer
- Mobile App: http://localhost:5177
- Backend: http://localhost:8000

### From Phone
1. Find your IP: `ipconfig` (Windows) or `ifconfig` (Linux/Mac)
2. Access: `http://YOUR_IP:5177`
3. Example: `http://192.168.1.174:5177`

---

## 🔍 Check Status

```bash
# List running containers
docker-compose ps

# Check health
docker-compose ps backend

# View resource usage
docker stats
```

---

## 🐛 Troubleshooting

```bash
# View logs
docker-compose logs -f mobile-app
docker-compose logs -f backend

# Restart services
docker-compose restart

# Rebuild from scratch
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Check network
docker network ls
docker network inspect tavern-network
```

---

## 📋 Service Ports

| Service | Port | URL |
|---------|------|-----|
| Mobile App | 5177 | http://localhost:5177 |
| Backend | 8000 | http://localhost:8000 |
| Waiter UI | 5173 | http://localhost:5173 |
| Kitchen UI | 5175 | http://localhost:5175 |
| Grill UI | 5174 | http://localhost:5174 |
| Drinks UI | 5176 | http://localhost:5176 |

---

## 💡 Tips

- Use `make mobile-only` for production (lighter, faster)
- Use `make mobile-dev` for development (hot-reload)
- Install as PWA on phone for best experience
- Check logs if WebSocket fails to connect
- Ensure phone and computer are on same WiFi

---

## 📚 More Info

- **DOCKER.md** - Full Docker documentation
- **mobile-app/DOCKER_GUIDE.md** - Mobile app Docker guide
- **DOCKER_UPDATE_SUMMARY.md** - Update summary

