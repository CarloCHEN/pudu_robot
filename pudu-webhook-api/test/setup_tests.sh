#!/bin/bash

# Setup script for Pudu Webhook API Testing Framework
# This script sets up the testing environment and runs tests

echo "=================================================="
echo "🚀 Pudu Webhook API Testing Framework Setup"
echo "=================================================="

# Check if we're in the correct directory
if [ ! -f "run_tests.py" ]; then
    echo "❌ Error: Please run this script from the test/ directory"
    echo "   cd test && ./setup_tests.sh"
    exit 1
fi

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "❌ Error: Python is not installed or not in PATH"
    exit 1
fi

# Check if required parent files exist
if [ ! -f "../main.py" ]; then
    echo "❌ Error: main.py not found in parent directory"
    echo "   Please ensure you're running from the correct project structure"
    exit 1
fi

echo "✅ Environment checks passed"

# Create __init__.py files if they don't exist
echo "📝 Creating __init__.py files..."

directories=("test_data" "mocks" "utils" "unit" "integration")
for dir in "${directories[@]}"; do
    if [ -d "$dir" ] && [ ! -f "$dir/__init__.py" ]; then
        touch "$dir/__init__.py"
        echo "   Created $dir/__init__.py"
    fi
done

# Check if webhook server is running
echo "🔍 Checking webhook server availability..."
if curl -s http://localhost:8000/api/pudu/webhook/health > /dev/null 2>&1; then
    # Check if it's the test server or production server
    response=$(curl -s http://localhost:8000/api/pudu/webhook/health)
    if echo "$response" | grep -q '"mode": "testing"'; then
        WEBHOOK_AVAILABLE=true
        WEBHOOK_TYPE="test"
        echo "✅ Test webhook server is running on localhost:8000"
    else
        WEBHOOK_AVAILABLE=false
        WEBHOOK_TYPE="production"
        echo "⚠️  Production webhook server detected on localhost:8000"
        echo "   Please stop production server and start test server for endpoint tests"
    fi
else
    WEBHOOK_AVAILABLE=false
    WEBHOOK_TYPE="none"
    echo "⚠️  No webhook server running (endpoint tests will be skipped)"
fi

# Display test options
echo ""
echo "=================================================="
echo "📋 Test Options Available:"
echo "=================================================="
echo "1. Run all tests (unit + integration, no endpoint)"
echo "2. Run all tests including webhook endpoint tests"
echo "3. Run only unit tests"
echo "4. Run only integration tests"
echo "5. Run individual test files"
echo "6. Start test webhook server"
echo "7. Exit"
echo ""

read -p "Choose an option (1-7): " choice

case $choice in
    1)
        echo "🧪 Running all tests (excluding endpoint)..."
        python run_tests.py
        ;;
    2)
        if [ "$WEBHOOK_TYPE" = "test" ]; then
            echo "🧪 Running all tests including webhook endpoint..."
            python run_tests.py --include-endpoint
        elif [ "$WEBHOOK_TYPE" = "production" ]; then
            echo "❌ Cannot run endpoint tests with production server"
            echo "   Please stop production server first, then choose option 6 to start test server"
        else
            echo "❌ Cannot run endpoint tests - no webhook server available"
            echo "   Choose option 6 to start test server first"
        fi
        ;;
    3)
        echo "🧪 Running unit tests only..."
        python run_tests.py --unit-only
        ;;
    4)
        echo "🧪 Running integration tests only..."
        python run_tests.py --integration-only
        ;;
    5)
        echo ""
        echo "Available individual test files:"
        echo "  1. test_processors.py"
        echo "  2. test_database_writer.py"
        echo "  3. test_notification_sender.py"
        echo "  4. test_complete_flow.py"
        if [ "$WEBHOOK_TYPE" = "test" ]; then
            echo "  5. test_webhook_endpoint.py"
        fi
        echo ""
        read -p "Enter test file number: " test_choice

        case $test_choice in
            1) python unit/test_processors.py ;;
            2) python unit/test_database_writer.py ;;
            3) python unit/test_notification_sender.py ;;
            4) python integration/test_complete_flow.py ;;
            5)
                if [ "$WEBHOOK_TYPE" = "test" ]; then
                    python integration/test_webhook_endpoint.py
                else
                    echo "❌ Test webhook server not available"
                fi
                ;;
            *) echo "❌ Invalid choice" ;;
        esac
        ;;
    6)
        echo "🚀 Starting test webhook server..."
        if [ "$WEBHOOK_TYPE" = "production" ]; then
            echo "⚠️  Production server detected. Please stop it first:"
            echo "   pkill -f 'python.*main.py' or manually stop your production server"
            echo "   Then run this option again"
        elif [ "$WEBHOOK_TYPE" = "test" ]; then
            echo "✅ Test server is already running!"
        else
            echo "🧪 Starting test server with mock services..."
            python start_test_server.py
        fi
        ;;
    7)
        echo "👋 Exiting..."
        exit 0
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "=================================================="
echo "✨ Testing completed!"
echo "=================================================="
echo ""
echo "💡 Tips:"
echo "  • Run 'python run_tests.py --help' for more options"
echo "  • Use --verbose for detailed output"
echo "  • Check test/README.md for comprehensive documentation"
echo ""

if [ "$WEBHOOK_AVAILABLE" = false ] && [ "$WEBHOOK_TYPE" != "production" ]; then
    echo "🚨 To run endpoint tests:"
    echo "  1. Start test server: python start_test_server.py"
    echo "  2. Run: python run_tests.py --include-endpoint"
    echo ""
elif [ "$WEBHOOK_TYPE" = "production" ]; then
    echo "🚨 To run endpoint tests:"
    echo "  1. Stop production server"
    echo "  2. Start test server: python start_test_server.py"
    echo "  3. Run: python run_tests.py --include-endpoint"
    echo ""
fi