#!/bin/bash

# Badho Search Docker Deployment Script

set -e

echo "🚀 Starting Badho Search deployment..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install it and try again."
    exit 1
fi

# Function to show usage
show_usage() {
    echo "Usage: $0 [dev|prod|build|clean|ollama|logs]"
    echo ""
    echo "Commands:"
    echo "  dev     - Start development environment with Ollama"
    echo "  prod    - Start production environment with Ollama"
    echo "  build   - Build Docker image only"
    echo "  clean   - Clean up Docker containers and images"
    echo "  ollama  - Setup Ollama model (nomic-embed-text)"
    echo "  logs    - Show application logs"
    echo ""
}

# Function to build image
build_image() {
    echo "🔨 Building Docker image..."
    docker build -t badho-search:latest .
    echo "✅ Image built successfully!"
}

# Function to start development environment
start_dev() {
    echo "🔄 Starting development environment with Ollama..."
    docker-compose up --build -d
    echo "✅ Development environment started!"
    echo "🌐 Application available at: http://localhost:5001"
    echo "🤖 Ollama available at: http://localhost:11434 (external)"
    echo "🔗 Search app connects to: http://ollama:11434 (internal Docker network)"
    echo ""
    echo "📝 Next steps:"
    echo "   1. Wait for Ollama to start (check: docker-compose logs ollama)"
    echo "   2. Setup model: ./setup-ollama.sh"
    echo "   3. View logs: docker-compose logs -f"
}

# Function to start production environment
start_prod() {
    echo "🚀 Starting production environment with Ollama..."
    
    # Check if .env file exists
    if [ ! -f .env ]; then
        echo "⚠️  .env file not found. Creating from template..."
        cp env.example .env
        echo "📝 Please edit .env file with your production values"
        exit 1
    fi
    
    docker-compose -f docker-compose.prod.yml up --build -d
    echo "✅ Production environment started!"
    echo "🌐 Application available at: http://localhost:5001"
    echo "🤖 Ollama available at: http://localhost:11434 (external)"
    echo "🔗 Search app connects to: http://ollama:11434 (internal Docker network)"
    echo ""
    echo "📝 Next steps:"
    echo "   1. Wait for Ollama to start (check: docker-compose -f docker-compose.prod.yml logs ollama)"
    echo "   2. Setup model: ./setup-ollama.sh"
    echo "   3. View logs: docker-compose -f docker-compose.prod.yml logs -f"
}

# Function to setup Ollama
setup_ollama() {
    echo "🤖 Setting up Ollama model..."
    ./setup-ollama.sh
}

# Function to show logs
show_logs() {
    echo "📊 Showing application logs..."
    docker-compose logs -f
}

# Function to clean up
cleanup() {
    echo "🧹 Cleaning up Docker resources..."
    
    # Stop and remove containers
    docker-compose down --remove-orphans 2>/dev/null || true
    docker-compose -f docker-compose.prod.yml down --remove-orphans 2>/dev/null || true
    
    # Remove images
    docker rmi badho-search:latest 2>/dev/null || true
    docker rmi ollama/ollama:latest 2>/dev/null || true
    
    # Remove unused containers, networks, and images
    docker system prune -f
    
    echo "✅ Cleanup completed!"
}

# Main script logic
case "${1:-dev}" in
    "dev")
        build_image
        start_dev
        ;;
    "prod")
        build_image
        start_prod
        ;;
    "build")
        build_image
        ;;
    "ollama")
        setup_ollama
        ;;
    "logs")
        show_logs
        ;;
    "clean")
        cleanup
        ;;
    "help"|"-h"|"--help")
        show_usage
        ;;
    *)
        echo "❌ Unknown command: $1"
        show_usage
        exit 1
        ;;
esac 