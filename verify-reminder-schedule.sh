#!/bin/sh
# Verify reminder schedule configuration and test it
# Usage: ./verify-reminder-schedule.sh

cd "$(dirname "$0")" || exit 1

# Check if Python is available
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ Error: python3 is not installed"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    . .venv/bin/activate
elif [ -d "venv" ]; then
    . venv/bin/activate
fi

# Check if required modules are installed
if ! python3 -c "import aiosmtplib" 2>/dev/null; then
    echo "📦 Installing required dependencies from requirements.txt..."
    pip install -q -r requirements.txt
fi

# Run the verification script
python3 verify_reminder_schedule.py

