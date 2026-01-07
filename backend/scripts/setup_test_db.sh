#!/bin/bash
# Setup test database for local development

set -e

echo "🔧 Setting up test database..."

# Detect docker compose command (docker-compose vs docker compose)
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo "❌ Docker Compose not found. Please install Docker and Docker Compose."
    exit 1
fi

echo "Using: $DOCKER_COMPOSE"

# Start test database
echo "🐳 Starting PostgreSQL test database..."
$DOCKER_COMPOSE -f docker-compose.test.yml up -d

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
timeout=30
elapsed=0
while ! $DOCKER_COMPOSE -f docker-compose.test.yml exec -T devbin_test_db pg_isready -U postgres &> /dev/null; do
    if [ $elapsed -ge $timeout ]; then
        echo "❌ Database failed to start within ${timeout}s"
        $DOCKER_COMPOSE -f docker-compose.test.yml logs
        exit 1
    fi
    sleep 1
    elapsed=$((elapsed + 1))
done

echo "✅ Test database is ready!"
echo "📝 Connection string: postgresql://postgres:postgres@localhost:5433/devbin_test"
echo ""
echo "To run tests:"
echo "  uv run pytest"
echo ""
echo "To stop test database:"
echo "  $DOCKER_COMPOSE -f docker-compose.test.yml down"
echo ""
echo "To clean up test database and volumes:"
echo "  $DOCKER_COMPOSE -f docker-compose.test.yml down -v"
