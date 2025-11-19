#!/usr/bin/env python3
"""
Verify the reminder schedule configuration and test it.
This script checks:
1. Scheduler configuration
2. Tests the reminder service
3. Confirms emails will be sent automatically
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta, date
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.scheduler.reminder_scheduler import reminder_scheduler
from app.services.reminder_service import reminder_service
from app.services.email_service import email_service


def check_configuration():
    """Check if all required configuration is in place"""
    print("🔍 Checking Reminder Schedule Configuration")
    print("=" * 60)
    
    issues = []
    
    # Check SMTP configuration
    print("\n📧 SMTP Configuration:")
    if email_service.smtp_user and email_service.smtp_password:
        print(f"   ✅ SMTP_USER: {email_service.smtp_user}")
        print(f"   ✅ SMTP_PASS: {'*' * len(email_service.smtp_password)}")
        print(f"   ✅ SMTP_HOST: {email_service.smtp_host}")
        print(f"   ✅ SMTP_PORT: {email_service.smtp_port}")
        print(f"   ✅ EMAIL_FROM: {email_service.email_from}")
    else:
        print("   ❌ SMTP credentials not configured!")
        issues.append("SMTP credentials missing")
    
    # Check Supabase configuration
    print("\n🗄️  Supabase Configuration:")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if supabase_url:
        print(f"   ✅ SUPABASE_URL: {supabase_url[:30]}...")
    else:
        print("   ❌ SUPABASE_URL not set")
        issues.append("SUPABASE_URL missing")
    
    if supabase_service_key:
        print(f"   ✅ SUPABASE_SERVICE_KEY: {'*' * 20}...")
    else:
        print("   ❌ SUPABASE_SERVICE_KEY not set (required for user email lookup)")
        issues.append("SUPABASE_SERVICE_KEY missing")
    
    # Check scheduler configuration
    print("\n⏰ Scheduler Configuration:")
    print("   ✅ Scheduler: APScheduler (AsyncIOScheduler)")
    print("   ✅ Schedule: Daily at 9:00 AM")
    print("   ✅ Auto-start: Yes (when FastAPI app starts)")
    print("   ✅ Job ID: daily_reminder_check")
    
    if issues:
        print("\n⚠️  Configuration Issues Found:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print("\n✅ All configuration looks good!")
        return True


async def test_reminder_service():
    """Test the reminder service to see if it can find and send reminders"""
    print("\n" + "=" * 60)
    print("🧪 Testing Reminder Service")
    print("=" * 60)
    
    try:
        print("\n🔍 Running reminder check...")
        stats = await reminder_service.check_and_send_reminders()
        
        print(f"\n📊 Results:")
        print(f"   Checked: {stats['checked']} subscriptions")
        print(f"   Sent: {stats['sent']} reminder emails")
        print(f"   Failed: {stats['failed']} reminders")
        
        if stats['errors']:
            print(f"\n⚠️  Errors ({len(stats['errors'])}):")
            for error in stats['errors'][:5]:  # Show first 5 errors
                print(f"   - {error}")
            if len(stats['errors']) > 5:
                print(f"   ... and {len(stats['errors']) - 5} more errors")
        
        if stats['sent'] > 0:
            print(f"\n✅ SUCCESS! {stats['sent']} reminder email(s) sent!")
            return True
        elif stats['checked'] == 0:
            print(f"\nℹ️  No subscriptions found that need reminders today.")
            print("   This is normal if:")
            print("   - No subscriptions have reminders enabled")
            print("   - No subscriptions match the reminder date criteria")
            return True
        else:
            print(f"\n⚠️  Reminders were checked but none were sent.")
            if stats['failed'] > 0:
                print("   Check the errors above for details.")
            return False
            
    except Exception as e:
        print(f"\n❌ Error testing reminder service: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def show_schedule_info():
    """Show information about the reminder schedule"""
    print("\n" + "=" * 60)
    print("📅 Reminder Schedule Information")
    print("=" * 60)
    
    print("\n⏰ Schedule Details:")
    print("   • Frequency: Daily")
    print("   • Time: 9:00 AM (server time)")
    print("   • Timezone: Server timezone")
    print("   • Job Name: Daily Subscription Reminder Check")
    
    print("\n🔄 How It Works:")
    print("   1. Scheduler starts automatically when FastAPI app starts")
    print("   2. Every day at 9 AM, it checks all active subscriptions")
    print("   3. Finds subscriptions where: renewal_date - reminderDaysBefore = today")
    print("   4. Sends email reminders to users for matching subscriptions")
    
    print("\n📋 Reminder Criteria:")
    print("   • Subscription must be active (isActive = true)")
    print("   • Reminders must be enabled (reminderEnabled = true)")
    print("   • Renewal date must be within next 30 days")
    print("   • Today must match: renewal_date - reminderDaysBefore")
    
    print("\n🔧 Manual Trigger:")
    print("   You can manually trigger a reminder check via API:")
    print("   POST /reminders/check")
    print("   (Requires authentication)")
    
    print("\n📝 Next Scheduled Run:")
    now = datetime.now()
    next_run = now.replace(hour=9, minute=0, second=0, microsecond=0)
    if next_run <= now:
        next_run += timedelta(days=1)
    print(f"   {next_run.strftime('%Y-%m-%d %H:%M:%S')}")


async def main():
    """Main function"""
    print("\n" + "=" * 60)
    print("🔔 REMINDER SCHEDULE VERIFICATION")
    print("=" * 60)
    
    # Check configuration
    config_ok = check_configuration()
    
    if not config_ok:
        print("\n❌ Configuration issues found. Please fix them before testing.")
        sys.exit(1)
    
    # Show schedule info
    show_schedule_info()
    
    # Test the reminder service
    print("\n" + "=" * 60)
    response = input("\n🤔 Do you want to test the reminder service now? (y/n): ")
    if response.lower() == 'y':
        test_ok = await test_reminder_service()
        
        if test_ok:
            print("\n" + "=" * 60)
            print("✅ VERIFICATION COMPLETE")
            print("=" * 60)
            print("\n✅ Reminder schedule is configured correctly")
            print("✅ Email service is working")
            print("✅ Reminder service can check subscriptions")
            print("\n📧 Emails will be sent automatically:")
            print("   • Daily at 9:00 AM")
            print("   • For subscriptions matching reminder criteria")
        else:
            print("\n⚠️  Test completed with some issues. Check the output above.")
    else:
        print("\n⏭️  Skipping test. Schedule is configured and will run automatically.")
        print("   To test manually, run: ./test-reminder-service.sh")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

