#!/bin/sh
# Test the full reminder service (requires Supabase connection)
# This tests the complete reminder check flow including database queries
# Usage: ./test_reminder_service.sh

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

# Create a simple test script
cat > /tmp/test_reminder_service.py << 'EOF'
#!/usr/bin/env python3
import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from app.services.reminder_service import reminder_service

async def test():
    print("🔍 Testing Reminder Service")
    print("=" * 50)
    print("This will check all subscriptions and send reminders where needed.")
    print("=" * 50)
    print()
    
    try:
        stats = await reminder_service.check_and_send_reminders()
        
        print()
        print("📊 Results:")
        print(f"   Checked: {stats['checked']} subscriptions")
        print(f"   Sent: {stats['sent']} reminders")
        print(f"   Failed: {stats['failed']} reminders")
        
        if stats['errors']:
            print()
            print("⚠️  Errors:")
            for error in stats['errors']:
                print(f"   - {error}")
        
        if stats['sent'] > 0:
            print()
            print("✅ Reminder emails sent successfully!")
        elif stats['checked'] == 0:
            print()
            print("ℹ️  No subscriptions found that need reminders today.")
        else:
            print()
            print("⚠️  No reminders were sent (check errors above).")
        
        return stats['sent'] > 0 or stats['checked'] == 0
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test())
    sys.exit(0 if success else 1)
EOF

# Copy to current directory and run
cp /tmp/test_reminder_service.py ./test_reminder_service_temp.py
python3 test_reminder_service_temp.py
rm -f test_reminder_service_temp.py

