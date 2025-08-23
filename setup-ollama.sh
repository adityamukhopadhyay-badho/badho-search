#!/bin/bash

# Ollama Setup Script for Badho Search Docker Environment

set -e

echo "🚀 Setting up Ollama for Badho Search..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if containers are running
if ! docker ps | grep -q "badho-ollama"; then
    echo "❌ Ollama container is not running. Please start the Docker Compose services first:"
    echo "   ./deploy.sh dev"
    exit 1
fi

echo "📥 Pulling nomic-embed-text model to Ollama container..."

# Pull the required model
docker exec badho-ollama ollama pull nomic-embed-text

echo "✅ Model pulled successfully!"

# Verify the model is available
echo "🔍 Verifying model availability..."
docker exec badho-ollama ollama list

echo ""
echo "🎉 Ollama setup complete!"
echo "📊 You can now use the search functionality with embeddings."
echo ""
echo "💡 To test the setup:"
echo "   1. Open http://localhost:5001 in your browser"
echo "   2. Try searching for a product"
echo "   3. Check logs: docker-compose logs -f" 