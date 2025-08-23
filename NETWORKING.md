# 🌐 Docker Networking Architecture

## Overview

This document explains how the Badho Search application communicates with Ollama in the Docker environment.

## 🔗 Network Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Host                              │
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │   Badho Search  │    │     Ollama      │                    │
│  │   Container     │◄──►│   Container     │                    │
│  │   Port: 5001    │    │   Port: 11434   │                    │
│  └─────────────────┘    └─────────────────┘                    │
│           │                       │                            │
│           └───────────────────────┘                            │
│                      │                                         │
│           ┌─────────────────┐                                  │
│           │  Docker Network │                                  │
│           │  badho-network  │                                  │
│           └─────────────────┘                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 🌍 URL Access Patterns

### **External Access (from your computer)**

| Service | URL | Purpose |
|---------|-----|---------|
| **Badho Search** | `http://localhost:5001` | Web interface and API |
| **Ollama** | `http://localhost:11434` | Ollama API (for debugging) |

### **Internal Access (container-to-container)**

| Service | URL | Purpose |
|---------|-----|---------|
| **Badho Search → Ollama** | `http://ollama:11434` | Embeddings generation |

## 🔧 Configuration

### **Environment Variables**

```bash
# In docker-compose.yml
environment:
  - OLLAMA_BASE_URL=http://ollama:11434  # Internal Docker network
```

### **Port Mappings**

```yaml
# Ollama service
ports:
  - "11434:11434"  # Maps host port 11434 to container port 11434

# Badho Search service  
ports:
  - "5001:5001"    # Maps host port 5001 to container port 5001
```

## 📋 Verification Commands

### **Check External Access**

```bash
# Verify Badho Search is accessible
curl http://localhost:5001/health

# Verify Ollama is accessible  
curl http://localhost:11434/api/tags
```

### **Check Internal Network**

```bash
# Verify Badho Search can reach Ollama internally
docker exec badho-search-app curl -f http://ollama:11434/api/tags

# Check if containers are on the same network
docker network inspect badho-search_badho-network
```

### **Check Container Status**

```bash
# See running containers
docker ps

# Check container logs
docker-compose logs -f
```

## 🚨 Common Issues

### **1. "Failed to reach Ollama embeddings endpoint"**

**Cause**: Badho Search container can't connect to Ollama container

**Solutions**:
```bash
# Check if both containers are running
docker ps

# Verify network connectivity
docker exec badho-search-app curl -f http://ollama:11434/api/tags

# Check container logs
docker-compose logs badho-search
docker-compose logs ollama
```

### **2. Ollama accessible externally but not internally**

**Cause**: Network configuration issue

**Solutions**:
```bash
# Restart containers
docker-compose down
docker-compose up --build -d

# Check network configuration
docker network ls
docker network inspect badho-search_badho-network
```

### **3. Port already in use**

**Cause**: Another service is using the same port

**Solutions**:
```bash
# Check what's using the port
lsof -i :11434
lsof -i :5001

# Kill the process or change ports in docker-compose.yml
```

## 📚 Key Concepts

- **Port Mapping**: `"11434:11434"` means host port 11434 maps to container port 11434
- **Internal Network**: Containers communicate using service names (`ollama`, `badho-search`)
- **External Access**: Your computer accesses services via `localhost:PORT`
- **Network Isolation**: Containers can only reach each other through the defined network

## 🔍 Debugging

### **Network Debugging**

```bash
# Inspect the Docker network
docker network inspect badho-search_badho-network

# Check container network settings
docker inspect badho-search-app | grep -A 20 "NetworkSettings"
docker inspect badho-ollama | grep -A 20 "NetworkSettings"
```

### **Container Debugging**

```bash
# Access container shell
docker exec -it badho-search-app bash
docker exec -it badho-ollama bash

# Test network connectivity from inside container
curl http://ollama:11434/api/tags
ping ollama
```

## 📖 Related Files

- `docker-compose.yml` - Network configuration
- `src/badho_search/config.py` - Ollama URL configuration
- `deploy.sh` - Deployment script
- `DOCKER_README.md` - Complete Docker documentation 