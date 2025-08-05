#!/bin/bash
# diagnose.sh
# Diagnostic script to check project setup

echo "🔍 Solidus Project Diagnostic"
echo "============================="

# Check current directory
echo ""
echo "📁 Current Directory Check:"
echo "  Current path: $(pwd)"
echo "  Contents:"
ls -la | head -10

echo ""
echo "📋 Required Files Check:"
echo "  manage.py exists: $([ -f manage.py ] && echo '✅ Found' || echo '❌ Missing')"
echo "  docker-compose.yml exists: $([ -f docker-compose.yml ] && echo '✅ Found' || echo '❌ Missing')"
echo "  src/ directory exists: $([ -d src ] && echo '✅ Found' || echo '❌ Missing')"
echo "  .env file exists: $([ -f .env ] && echo '✅ Found' || echo '❌ Missing')"

if [ -f docker-compose.yml ]; then
    echo ""
    echo "🐳 Docker Compose File Check:"
    echo "  File size: $(stat -c%s docker-compose.yml) bytes"
    echo "  First few lines:"
    head -5 docker-compose.yml
fi

echo ""
echo "🐳 Docker Check:"
echo "  Docker installed: $(command -v docker &> /dev/null && echo '✅ Yes' || echo '❌ No')"
echo "  Docker running: $(docker info &> /dev/null && echo '✅ Yes' || echo '❌ No')"

# Check Docker Compose syntax
echo "  Docker Compose v2 (new): $(docker compose version &> /dev/null && echo '✅ Available' || echo '❌ Not available')"
echo "  Docker Compose v1 (old): $(docker-compose version &> /dev/null && echo '✅ Available' || echo '❌ Not available')"

# Check UV
echo ""
echo "📦 UV Check:"
echo "  UV installed: $(command -v uv &> /dev/null && echo '✅ Yes' || echo '❌ No')"
if command -v uv &> /dev/null; then
    echo "  UV version: $(uv --version)"
fi

# Check Python
echo ""
echo "🐍 Python Check:"
echo "  Python installed: $(command -v python &> /dev/null && echo '✅ Yes' || echo '❌ No')"
echo "  Python3 installed: $(command -v python3 &> /dev/null && echo '✅ Yes' || echo '❌ No')"
if command -v python3 &> /dev/null; then
    echo "  Python version: $(python3 --version)"
fi

# Check if we're in the right directory
echo ""
echo "🎯 Project Structure Validation:"
if [ -f manage.py ] && [ -d src ]; then
    echo "  ✅ Correct project structure detected"
    echo "  📁 Django apps in src/:"
    ls src/ 2>/dev/null | grep -v __pycache__ | head -10
else
    echo "  ❌ Incorrect project structure"
    echo "  Expected: manage.py in root, Django apps in src/"
    if [ ! -f manage.py ]; then
        echo "    • manage.py not found in current directory"
        echo "    • Are you in the right folder?"
    fi
    if [ ! -d src ]; then
        echo "    • src/ directory not found"
        echo "    • Django apps should be in src/"
    fi
fi

# Test Docker Compose syntax
echo ""
echo "🧪 Docker Compose Test:"
if [ -f docker-compose.yml ]; then
    echo "  Testing 'docker compose' (v2 syntax):"
    if docker compose config --quiet &> /dev/null; then
        echo "    ✅ docker compose syntax works"
        DOCKER_COMPOSE_CMD="docker compose"
    else
        echo "    ❌ docker compose syntax failed"
        echo "  Testing 'docker-compose' (v1 syntax):"
        if docker-compose config --quiet &> /dev/null; then
            echo "    ✅ docker-compose syntax works"
            DOCKER_COMPOSE_CMD="docker-compose"
        else
            echo "    ❌ docker-compose syntax failed"
            echo "    ⚠️  Configuration file may have issues"
        fi
    fi

    if [ -n "$DOCKER_COMPOSE_CMD" ]; then
        echo ""
        echo "  ✅ Recommended command: $DOCKER_COMPOSE_CMD"
        echo "  📋 Services defined:"
        $DOCKER_COMPOSE_CMD config --services 2>/dev/null || echo "    ❌ Could not list services"
    fi
else
    echo "  ❌ docker-compose.yml not found"
fi

# Port checks
echo ""
echo "🔌 Port Check:"
PORTS=(5432 6379 8000 1025 8025)
for port in "${PORTS[@]}"; do
    if nc -z localhost $port 2>/dev/null; then
        echo "  Port $port: ⚠️  In use"
    else
        echo "  Port $port: ✅ Available"
    fi
done

echo ""
echo "🔧 Recommendations:"
if [ ! -f manage.py ]; then
    echo "  • Navigate to the directory containing manage.py"
fi
if [ ! -f docker-compose.yml ]; then
    echo "  • Ensure docker-compose.yml exists in the project root"
fi
if ! docker info &> /dev/null; then
    echo "  • Start Docker daemon"
fi
if ! command -v uv &> /dev/null; then
    echo "  • Install UV: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

echo ""
echo "🚀 Next Steps:"
if [ -f manage.py ] && [ -d src ] && [ -f docker-compose.yml ]; then
    echo "  Project structure looks good! Try:"
    echo "  1. ./setup_dev.sh  (use the corrected version)"
    echo "  2. Or manually: make up-db && make migrate && make up"
else
    echo "  Fix the issues above first, then run setup script"
fi