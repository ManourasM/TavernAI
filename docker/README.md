# Docker Configuration

This folder contains all Docker-related files for the TavernAI project.

## Files

- **docker-compose.yml** - Production configuration for all services
- **docker-compose.dev.yml** - Development configuration with hot-reload
- **docker-compose.mobile.yml** - Lightweight configuration (backend + mobile app only)
- **Dockerfile.frontend** - Multi-stage build for all frontend UIs
- **nginx.conf** - Nginx configuration for production frontend serving

## Quick Start

### From Project Root

```bash
# Mobile app only (recommended)
make mobile-only

# All services
make up

# Development mode
make mobile-dev
```

### From This Directory

```bash
# Mobile app only
docker-compose -f docker-compose.mobile.yml up -d

# All services
docker-compose -f docker-compose.yml up -d

# Development mode
docker-compose -f docker-compose.dev.yml up
```

## Services

### Production (docker-compose.yml)

- **backend** - FastAPI server on port 8000
- **mobile-app** - Mobile PWA on port 5177
- **waiter-ui** - Legacy waiter UI on port 5173
- **kitchen-ui** - Legacy kitchen UI on port 5175
- **grill-ui** - Legacy grill UI on port 5174
- **drinks-ui** - Legacy drinks UI on port 5176

### Mobile Only (docker-compose.mobile.yml)

- **backend** - FastAPI server on port 8000
- **mobile-app** - Mobile PWA on port 5177

### Development (docker-compose.dev.yml)

Same services as production but with:
- Hot-reload enabled
- Source code mounted as volumes
- Vite dev server for frontends
- Uvicorn reload for backend

## Network

All services run on the `tavern-network` bridge network, allowing them to communicate with each other using service names (e.g., `http://backend:8000`).

## Volumes

- **Backend data**: `../backend/data:/app/data` - Persists menu.json and other data
- **Nginx config**: `./nginx.conf:/etc/nginx/conf.d/default.conf:ro` - Nginx configuration

## Health Checks

The backend service includes a health check that verifies the `/config` endpoint is responding.

## Building

The frontend services use a multi-stage build:
1. **Builder stage**: Installs dependencies and builds the React app
2. **Production stage**: Serves the built files with nginx

## Documentation

For complete documentation, see:
- [../docs/DOCKER.md](../docs/DOCKER.md) - Full Docker guide
- [../docs/DOCKER_QUICK_REFERENCE.md](../docs/DOCKER_QUICK_REFERENCE.md) - Quick reference
- [../mobile-app/DOCKER_GUIDE.md](../mobile-app/DOCKER_GUIDE.md) - Mobile app Docker guide

