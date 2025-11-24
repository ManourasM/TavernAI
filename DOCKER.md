# Docker Setup for Tavern Ordering System

This document explains how to run the Tavern Ordering System using Docker.

## Prerequisites

- Docker (version 20.10 or higher)
- Docker Compose (version 2.0 or higher)

## Quick Start

### Production Build

Build and run all services:

```bash
docker-compose up --build
```

Or run in detached mode:

```bash
docker-compose up -d --build
```

### Access the Applications

Once all containers are running, access the UIs at:

- **Waiter UI**: http://localhost:5173
- **Kitchen UI**: http://localhost:5175
- **Grill UI**: http://localhost:5174
- **Drinks UI**: http://localhost:5176
- **Backend API**: http://localhost:8000

### Stop the Services

```bash
docker-compose down
```

To also remove volumes:

```bash
docker-compose down -v
```

## Development Mode

For development with hot-reload, use the development docker-compose file:

```bash
docker-compose -f docker-compose.dev.yml up
```

This mounts your local source code into the containers, so changes are reflected immediately.

## Individual Service Management

### Build a specific service

```bash
docker-compose build backend
docker-compose build waiter-ui
```

### Run a specific service

```bash
docker-compose up backend
docker-compose up waiter-ui kitchen-ui
```

### View logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f waiter-ui
```

### Restart a service

```bash
docker-compose restart backend
docker-compose restart waiter-ui
```

## Troubleshooting

### Port conflicts

If you get port conflict errors, make sure the ports are not already in use:

```bash
# Windows
netstat -ano | findstr :8000
netstat -ano | findstr :5173

# Linux/Mac
lsof -i :8000
lsof -i :5173
```

### Backend not connecting

Check backend logs:

```bash
docker-compose logs backend
```

### Frontend not loading

1. Check if the build completed successfully
2. Check nginx logs:

```bash
docker-compose logs waiter-ui
```

### WebSocket connection issues

Make sure the nginx configuration is properly mounted and the backend is healthy:

```bash
docker-compose ps
```

All services should show "healthy" or "running" status.

## Customization

### Environment Variables

Create a `.env` file in the root directory to customize settings:

```env
BACKEND_PORT=8000
WAITER_PORT=5173
KITCHEN_PORT=5175
GRILL_PORT=5174
DRINKS_PORT=5176
```

Then update docker-compose.yml to use these variables.

### Menu Configuration

The menu is stored in `backend/data/menu.json`. This file is mounted as a volume, so you can edit it without rebuilding the container.

After editing, restart the backend:

```bash
docker-compose restart backend
```

## Production Deployment

For production deployment:

1. Use a reverse proxy (nginx, Traefik, etc.) in front of the services
2. Enable HTTPS/TLS
3. Set up proper logging and monitoring
4. Use Docker secrets for sensitive data
5. Consider using Docker Swarm or Kubernetes for orchestration

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Waiter UI  │     │ Kitchen UI  │     │  Grill UI   │     │  Drinks UI  │
│   :5173     │     │   :5175     │     │   :5174     │     │   :5176     │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │                   │
       └───────────────────┴───────────────────┴───────────────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │  Backend API    │
                          │    :8000        │
                          │  (FastAPI +     │
                          │   WebSocket)    │
                          └─────────────────┘
```

All frontend UIs communicate with the backend via REST API and WebSocket connections.

