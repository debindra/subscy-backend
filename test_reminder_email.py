#!/usr/bin/env python3
"""
Test script to verify email reminder functionality.
This script sends a test reminder email using the actual EmailService.
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables FIRST, before importing email_service
# This is critical because EmailService reads env vars during initialization
load_dotenv()

# Add the app directory to the path so we can import the email service
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.email_service import email_service


async def test_reminder_email(to_email: str = None):
    """Test sending a reminder email with sample subscription data"""
    
    # Get recipient email
    if not to_email:
        to_email = os.getenv("SMTP_USER")
        if not to_email:
            print("❌ Error: No recipient email provided and SMTP_USER not set!")
            print("Usage: python test_reminder_email.py <recipient_email>")
            sys.exit(1)
    
    # Check SMTP configuration
    if not email_service.smtp_user or not email_service.smtp_password:
        print("❌ Error: SMTP credentials not configured!")
        print("\nPlease set the following environment variables:")
        print("  - SMTP_USER (your email address)")
        print("  - SMTP_PASS (your email password/app password)")
        print("\nOptional:")
        print("  - SMTP_HOST (default: smtp.gmail.com)")
        print("  - SMTP_PORT (default: 587)")
        print("  - EMAIL_FROM (default: SMTP_USER)")
        print("  - SMTP_SECURE (default: false)")
        sys.exit(1)
    
    print("📧 Testing Email Reminder Service")
    print("=" * 50)
    print(f"From: {email_service.email_from}")
    print(f"To: {to_email}")
    print(f"SMTP: {email_service.smtp_host}:{email_service.smtp_port}")
    print(f"Secure: {email_service.smtp_secure}")
    print("=" * 50)
    print()
    
    # Create sample subscription data
    renewal_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    sample_subscription = {
        "id": "test-subscription-123",
        "name": "Netflix Premium",
        "amount": 15.99,
        "currency": "USD",
        "billingCycle": "monthly",
        "category": "Entertainment",
        "nextRenewalDate": renewal_date,
        "website": "https://www.netflix.com/account"
    }
    
    user_name = "Test User"
    days_until = 7
    
    print(f"📋 Test Subscription Data:")
    print(f"   Name: {sample_subscription['name']}")
    print(f"   Amount: {sample_subscription['currency']} {sample_subscription['amount']}")
    print(f"   Billing Cycle: {sample_subscription['billingCycle']}")
    print(f"   Renewal Date: {renewal_date}")
    print(f"   Days Until Renewal: {days_until}")
    print()
    
    try:
        print("🚀 Sending test reminder email...")
        success = await email_service.send_reminder_email(
            to_email=to_email,
            user_name=user_name,
            subscription=sample_subscription,
            days_until=days_until
        )
        
        if success:
            print()
            print("✅ SUCCESS! Test reminder email sent successfully!")
            print(f"   Check your inbox at: {to_email}")
            print()
            print("📝 What to verify:")
            print("   ✓ Email was received")
            print("   ✓ Subject line is correct")
            print("   ✓ HTML formatting looks good")
            print("   ✓ All subscription details are correct")
            print("   ✓ Plain text version is readable")
            return True
        else:
            print()
            print("❌ FAILED! Email could not be sent.")
            print("   Check the error messages above for details.")
            return False
            
    except Exception as e:
        print()
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Get recipient email from command line argument
    recipient = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Run the async function
    success = asyncio.run(test_reminder_email(recipient))
    sys.exit(0 if success else 1)

