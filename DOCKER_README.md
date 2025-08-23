# 🐳 Badho Search Docker Deployment

This guide explains how to deploy Badho Search using Docker and Docker Compose, including Ollama for embeddings.

## 📋 Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 4GB RAM available (2GB for app + 2GB for Ollama)
- FAISS index artifacts (run `python scripts/build_index.py` first)

## 🚀 Quick Start

### 1. Build and Start Development Environment

```bash
# Make sure you have built the FAISS index first
python scripts/build_index.py

# Start development environment with Ollama
./deploy.sh dev

# Wait for Ollama to start, then setup the model
./setup-ollama.sh
```

### 2. Build and Start Production Environment

```bash
# Copy environment template
cp env.example .env

# Edit .env with your production values
nano .env

# Start production environment with Ollama
./deploy.sh prod

# Wait for Ollama to start, then setup the model
./setup-ollama.sh
```

## 🤖 Ollama Integration

### What is Ollama?
Ollama is a local LLM server that provides the `nomic-embed-text` model for generating embeddings. It's now integrated into the Docker environment.

### Ollama Services
- **Development**: `badho-ollama` container
- **Production**: `badho-ollama-prod` container
- **External Port**: 11434 (accessible at `http://localhost:11434`)
- **Internal Network**: Search app connects to `http://ollama:11434`
- **Model**: `nomic-embed-text` (automatically pulled)

### Network Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   Badho Search  │    │     Ollama      │
│   Container     │◄──►│   Container     │
│   Port: 5001    │    │   Port: 11434   │
└─────────────────┘    └─────────────────┘
         │                       │
         └───────────────────────┘
                    │
         ┌─────────────────┐
         │  Docker Network │
         │  badho-network  │
         └─────────────────┘
```

**External Access:**
- Search App: `http://localhost:5001`
- Ollama: `http://localhost:11434`

**Internal Communication:**
- Search App → Ollama: `http://ollama:11434`

### Setup Ollama Model

```bash
# After starting the environment, setup the model
./setup-ollama.sh

# Or manually
docker exec badho-ollama ollama pull nomic-embed-text
```

### Verify Ollama Status

```bash
# Check if Ollama is running
docker ps | grep ollama

# Check Ollama logs
docker-compose logs ollama

# List available models
docker exec badho-ollama ollama list
```

## 🏗️ Manual Docker Commands

### Build Image Only

```bash
docker build -t badho-search:latest .
```

### Development Environment

```bash
# Start services (including Ollama)
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production Environment

```bash
# Start production services (including Ollama)
docker-compose -f docker-compose.prod.yml up --build -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop services
docker-compose -f docker-compose.prod.yml down
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file based on `env.example`:

```bash
# Database Configuration
CONNECTION_STRING=postgres://postgres:Badho_1301@db.badho.in:5432/badho-app

# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=0

# Application Configuration
PYTHONPATH=/app/src

# Ollama Configuration (automatically set in Docker)
OLLAMA_BASE_URL=http://ollama:11434
```

### Volume Mounts

The application mounts these directories:
- `./artifacts` → `/app/artifacts` (FAISS index and lookup files)
- `./templates` → `/app/templates` (HTML templates)
- `ollama_data` → `/root/.ollama` (Ollama models and data)

### Resource Allocation

**Development:**
- Badho Search: 2GB RAM, 1 CPU
- Ollama: 2GB RAM, 1 CPU

**Production:**
- Badho Search: 2GB RAM, 1 CPU
- Ollama: 4GB RAM, 2 CPU

## 📊 Monitoring

### Health Check

The application includes a health check endpoint:
- **URL**: `http://localhost:5001/health`
- **Response**: `{"status": "healthy"}`

### Ollama Health

```bash
# Check Ollama status (external access)
curl http://localhost:11434/api/tags

# Check if model is loaded (internal container access)
docker exec badho-ollama ollama list

# Verify internal network connectivity
docker exec badho-search-app curl -f http://ollama:11434/api/tags
```

### Logs

```bash
# Development
docker-compose logs -f badho-search
docker-compose logs -f ollama

# Production
docker-compose -f docker-compose.prod.yml logs -f badho-search
docker-compose -f docker-compose.prod.yml logs -f ollama
```

### Container Status

```bash
# Check running containers
docker ps

# Check container resources
docker stats badho-search-app badho-ollama
```

## 🧹 Cleanup

### Remove All Resources

```bash
./deploy.sh clean
```

### Manual Cleanup

```bash
# Stop and remove containers
docker-compose down --remove-orphans
docker-compose -f docker-compose.prod.yml down --remove-orphans

# Remove images
docker rmi badho-search:latest
docker rmi ollama/ollama:latest

# Clean up unused resources
docker system prune -f

# Remove Ollama data volume (optional)
docker volume rm badho-search_ollama_data
```

## 🔍 Troubleshooting

### Common Issues

1. **Ollama Model Not Found**
   ```bash
   # Pull the model
   ./setup-ollama.sh
   
   # Or manually
   docker exec badho-ollama ollama pull nomic-embed-text
   ```

2. **Ollama Container Won't Start**
   ```bash
   # Check Ollama logs
   docker-compose logs ollama
   
   # Check available memory
   free -h
   ```

3. **Embedding Errors**
   ```bash
   # Verify Ollama is running
   docker ps | grep ollama
   
   # Check model availability
   docker exec badho-ollama ollama list
   ```

4. **Port Already in Use**
   ```bash
   # Check what's using port 11434
   lsof -i :11434
   
   # Kill the process or change port in docker-compose.yml
   ```

### Debug Mode

```bash
# Run Ollama container interactively
docker run -it --rm -p 11434:11434 -v ollama_data:/root/.ollama ollama/ollama:latest

# Inside container
ollama pull nomic-embed-text
ollama list
```

## 📁 File Structure

```
badho-search/
├── Dockerfile                 # Docker image definition
├── docker-compose.yml         # Development environment with Ollama
├── docker-compose.prod.yml    # Production environment with Ollama
├── .dockerignore             # Files to exclude from build
├── deploy.sh                 # Deployment automation script
├── setup-ollama.sh           # Ollama model setup script
├── env.example               # Environment variables template
├── artifacts/                # FAISS index files (mounted)
├── templates/                # HTML templates (mounted)
└── src/                      # Application source code
```

## 🚀 Production Deployment

### 1. Environment Setup

```bash
# Copy and configure environment
cp env.example .env
nano .env

# Set production values
FLASK_ENV=production
FLASK_DEBUG=0
CONNECTION_STRING=your_production_db_url
```

### 2. Build and Deploy

```bash
# Build production image
./deploy.sh build

# Start production environment
./deploy.sh prod
```

### 3. Setup Ollama

```bash
# Wait for Ollama to start, then setup model
./setup-ollama.sh
```

### 4. Verify Deployment

```bash
# Check health
curl http://localhost:5001/health

# Check Ollama (external access)
curl http://localhost:11434/api/tags

# Verify internal network connectivity
docker exec badho-search-prod curl -f http://ollama:11434/api/tags

# Check logs
docker-compose -f docker-compose.prod.yml logs -f
```

## 🔒 Security Considerations

- **Non-root user**: Both containers run as non-root users
- **Read-only volumes**: Production mounts volumes as read-only
- **Resource limits**: Memory and CPU limits configured
- **Health checks**: Regular health monitoring
- **Network isolation**: Custom bridge network
- **Model isolation**: Ollama models stored in Docker volumes

## 📈 Scaling

### Horizontal Scaling

```bash
# Scale Badho Search instances (Ollama remains single)
docker-compose -f docker-compose.prod.yml up --scale badho-search=3 -d
```

### Load Balancer

Use nginx or HAProxy in front of multiple instances:

```yaml
# Add to docker-compose.prod.yml
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf
  depends_on:
    - badho-search
```

## 🆘 Support

For issues related to Docker deployment:
1. Check container logs
2. Verify environment variables
3. Ensure artifacts directory exists
4. Check resource availability
5. Verify Ollama model is loaded
6. Review Docker and Docker Compose versions 