#!/bin/bash

# Redis Database Reset Script for MarkUI Backend
# This is a simple wrapper around the Python cleanup script

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

echo "🧹 MarkUI Redis Database Reset"
echo "=============================="

# Check if we're in the right directory
if [ ! -f "$BACKEND_DIR/app/main.py" ]; then
    echo "❌ Error: This script must be run from the backend directory or scripts directory"
    echo "   Current directory: $(pwd)"
    echo "   Expected backend structure not found"
    exit 1
fi

# Check if Redis is running
echo "🔍 Checking Redis connection..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Error: Redis server is not running or not accessible"
    echo "   Please start Redis server first:"
    echo "   - On Ubuntu/Debian: sudo systemctl start redis-server"
    echo "   - On macOS with Homebrew: brew services start redis"
    echo "   - With Docker: docker run -d -p 6379:6379 redis:alpine"
    exit 1
fi

echo "✅ Redis is running"

# Change to backend directory
cd "$BACKEND_DIR"

# Check if we have poetry or python
if command -v poetry > /dev/null 2>&1; then
    echo "🐍 Using Poetry to run cleanup script..."
    PYTHON_CMD="poetry run python"
elif command -v python3 > /dev/null 2>&1; then
    echo "🐍 Using Python3 to run cleanup script..."
    PYTHON_CMD="python3"
elif command -v python > /dev/null 2>&1; then
    echo "🐍 Using Python to run cleanup script..."
    PYTHON_CMD="python"
else
    echo "❌ Error: Python not found. Please install Python or Poetry"
    exit 1
fi

# Parse command line arguments
case "${1:-interactive}" in
    "all"|"--all")
        echo "⚠️  COMPLETE DATABASE RESET"
        echo "   This will delete ALL data in Redis!"
        read -p "   Type 'YES' to confirm: " confirm
        if [ "$confirm" = "YES" ]; then
            $PYTHON_CMD scripts/cleanup_redis.py --all --force
        else
            echo "❌ Reset cancelled"
            exit 1
        fi
        ;;
    "pdfs"|"--pdfs")
        echo "🗂️  Cleaning PDF documents only..."
        $PYTHON_CMD scripts/cleanup_redis.py --pdfs --force
        ;;
    "jobs"|"--jobs")
        echo "⚙️  Cleaning conversion jobs only..."
        $PYTHON_CMD scripts/cleanup_redis.py --jobs --force
        ;;
    "settings"|"--settings")
        echo "⚙️  Cleaning user settings only..."
        $PYTHON_CMD scripts/cleanup_redis.py --settings --force
        ;;
    "expired"|"--expired")
        echo "🕐 Cleaning expired keys only..."
        $PYTHON_CMD scripts/cleanup_redis.py --expired --force
        ;;
    "stats"|"--stats")
        echo "📊 Showing database statistics..."
        $PYTHON_CMD scripts/cleanup_redis.py --stats
        ;;
    "interactive"|"--interactive"|"-i"|"")
        echo "🎯 Starting interactive cleanup..."
        $PYTHON_CMD scripts/cleanup_redis.py --interactive
        ;;
    "help"|"--help"|"-h")
        echo ""
        echo "Usage: $0 [option]"
        echo ""
        echo "Options:"
        echo "  all          Complete database reset (deletes everything)"
        echo "  pdfs         Clean only PDF documents"
        echo "  jobs         Clean only conversion jobs"
        echo "  settings     Clean only user settings"
        echo "  expired      Clean only expired keys"
        echo "  stats        Show database statistics"
        echo "  interactive  Interactive mode (default)"
        echo "  help         Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0                    # Interactive mode"
        echo "  $0 all                # Complete reset"
        echo "  $0 pdfs               # Clean only PDFs"
        echo "  $0 stats              # Show statistics"
        echo ""
        ;;
    *)
        echo "❌ Unknown option: $1"
        echo "   Use '$0 help' to see available options"
        exit 1
        ;;
esac

echo ""
echo "✅ Redis cleanup completed!"
echo ""
echo "💡 Tip: You can check the current state with:"
echo "   $0 stats" 