#!/bin/bash

# Simple wrapper script for updating support ticket timeline
# Usage: ./update_ticket.sh <report_id> "<status_message>" [user_id] [database]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_SCRIPT="$SCRIPT_DIR/support_timeline_api.py"

# Check if the API script exists
if [ ! -f "$API_SCRIPT" ]; then
    echo "❌ Error: API script not found at $API_SCRIPT"
    echo "   Please make sure you're running this from the project root directory"
    exit 1
fi

# Function to show usage
show_usage() {
    echo "Usage: $0 <report_id> \"<status_message>\" [user_id] [database]"
    echo "       $0 <report_id> --history [database]"
    echo ""
    echo "Arguments:"
    echo "  report_id      - The report ID to update"
    echo "  status_message - The status message to add (or --history to view timeline)"
    echo "  user_id        - Optional: User ID creating this entry (default: system)"
    echo "  database       - Optional: Specific database to target (foxx_irvine_office, foxx_irvine_office_test)"
    echo ""
    echo "Examples:"
    echo "  $0 12345 \"Email sent to customer\""
    echo "  $0 12345 \"Issue resolved\" admin_001"
    echo "  $0 12345 \"Customer contacted\" admin_001 foxx_irvine_office"
    echo "  $0 12345 --history"
    echo "  $0 12345 --history foxx_irvine_office"
}

# Check arguments
if [ $# -lt 2 ]; then
    show_usage
    exit 1
fi

REPORT_ID="$1"
STATUS_MESSAGE="$2"
USER_ID="${3:-system}"
DATABASE="$4"

# Build command arguments
CMD_ARGS="--report-id \"$REPORT_ID\""

# Check if user wants to see history
if [ "$STATUS_MESSAGE" = "--history" ]; then
    echo "📋 Retrieving timeline history for report ID: $REPORT_ID"
    CMD_ARGS="$CMD_ARGS --history"

    # If user_id is actually a database name for history command
    if [ -n "$3" ] && [ "$3" != "system" ]; then
        DATABASE="$3"
    fi
else
    echo "📝 Adding timeline entry..."
    echo "   Report ID: $REPORT_ID"
    echo "   Status: $STATUS_MESSAGE"
    echo "   User: $USER_ID"
    if [ -n "$DATABASE" ]; then
        echo "   Database: $DATABASE"
    fi
    echo ""

    CMD_ARGS="$CMD_ARGS --status \"$STATUS_MESSAGE\" --user-id \"$USER_ID\""
fi

# Add database parameter if specified
if [ -n "$DATABASE" ]; then
    CMD_ARGS="$CMD_ARGS --database \"$DATABASE\""
fi

# Execute the Python script
eval "python3 \"$API_SCRIPT\" $CMD_ARGS"

# Check exit status
if [ $? -eq 0 ]; then
    if [ "$STATUS_MESSAGE" != "--history" ]; then
        echo ""
        echo "✅ Timeline entry added successfully!"
    fi
else
    echo ""
    echo "❌ Operation failed. Check the logs above for details."
    exit 1
fi