#!/bin/bash

# SkillLedger License Verification System - Quick Setup Script

set -e

echo "=========================================="
echo "SkillLedger License Verification Setup"
echo "=========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first:"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

echo "✓ Docker is installed"

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first:"
    echo "   https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✓ Docker Compose is installed"
echo ""

# Create .env file if it doesn't exist
if [ ! -f backend/.env ]; then
    echo "Creating .env file..."
    cp backend/.env.example backend/.env
    
    # Generate a random secret key
    SECRET_KEY=$(openssl rand -hex 32)
    sed -i.bak "s/your-secret-key-here-change-this-in-production/$SECRET_KEY/" backend/.env
    rm backend/.env.bak 2>/dev/null || true
    
    echo "✓ Created .env file with generated secret key"
else
    echo "✓ .env file already exists"
fi

echo ""
echo "Starting services with Docker Compose..."
echo ""

# Start Docker Compose
docker-compose up -d

echo ""
echo "Waiting for services to be ready..."
sleep 10

# Check if services are healthy
echo ""
echo "Checking service health..."

if docker-compose ps | grep -q "Up"; then
    echo "✓ Services are running"
else
    echo "❌ Services failed to start. Check logs with: docker-compose logs"
    exit 1
fi

echo ""
echo "Initializing database..."

# Wait for PostgreSQL to be ready
until docker-compose exec -T db pg_isready -U skilledger > /dev/null 2>&1; do
    echo "Waiting for PostgreSQL..."
    sleep 2
done

echo "✓ PostgreSQL is ready"

# Run database initialization
docker-compose exec -T db psql -U skilledger -d skilledger_licenses -f /docker-entrypoint-initdb.d/init.sql 2>/dev/null || true

echo ""
echo "=========================================="
echo "✓ Setup Complete!"
echo "=========================================="
echo ""
echo "Your SkillLedger API is now running at:"
echo "  http://localhost:10000"
echo ""
echo "Interactive API Documentation:"
echo "  http://localhost:10000/docs"
echo ""
echo "Demo API Key:"
echo "  sk_test_demo_key_12345"
echo ""
echo "Test the API:"
echo "  curl -X POST \"http://localhost:10000/api/verify/license\" \\"
echo "    -H \"X-API-Key: sk_test_demo_key_12345\" \\"
echo "    -H \"Content-Type: application/json\" \\"
echo "    -d '{\"license_number\": \"123456\", \"state_code\": \"AZ\"}'"
echo ""
echo "View logs:"
echo "  docker-compose logs -f api"
echo ""
echo "Stop services:"
echo "  docker-compose down"
echo ""
echo "=========================================="
