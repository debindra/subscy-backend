#!/bin/sh
# Test script to verify email reminder functionality
# Usage: ./test-reminder-email.sh [recipient_email]

cd "$(dirname "$0")" || exit 1

# Check if Python is available
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ Error: python3 is not installed"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "📦 Activating virtual environment..."
    . .venv/bin/activate
elif [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    . venv/bin/activate
fi

# Check if required modules are installed
if ! python3 -c "import aiosmtplib" 2>/dev/null; then
    echo "📦 Installing required dependencies from requirements.txt..."
    pip install -q -r requirements.txt
fi

# Run the test script
python3 test_reminder_email.py "$@"

