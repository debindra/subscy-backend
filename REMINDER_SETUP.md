# Reminder System Setup Guide

## Overview

The subscription reminder system sends automated email notifications to users before their subscriptions renew. The system runs a daily check at 9 AM to find subscriptions that need reminders based on their `reminderDaysBefore` setting.

## How It Works

1. **Daily Check**: A scheduled job runs every day at 9 AM
2. **Subscription Query**: Finds all active subscriptions with reminders enabled that renew within 30 days
3. **Reminder Matching**: For each subscription, checks if today matches the reminder date (renewalDate - reminderDaysBefore)
4. **Email Sending**: Sends HTML email reminders to users

## Environment Variables

Add these to your `.env` file:

```env
# SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_SECURE=false  # Set to true for SSL on port 465
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password  # Use App Password for Gmail
EMAIL_FROM=noreply@subscriptiontracker.com

# Supabase (should already be configured)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key  # Required for accessing auth.users
```

## Gmail Setup

1. Enable 2-Factor Authentication on your Gmail account
2. Generate an App Password:
   - Go to Google Account → Security → 2-Step Verification → App passwords
   - Generate a password for "Mail"
   - Use this password as `SMTP_PASS`

## Testing Reminders

### Manual Trigger

You can manually trigger a reminder check using the API:

```bash
POST /reminders/check
Authorization: Bearer <your-token>
```

This endpoint:
- Checks all subscriptions
- Sends reminders where needed
- Returns statistics

### Check Upcoming Reminders

```bash
GET /reminders/upcoming?days=7
Authorization: Bearer <your-token>
```

This returns subscriptions that will trigger reminders for the current user.

## Email Template

The reminder emails include:
- Subscription name
- Renewal date
- Amount and currency
- Billing cycle
- Days until renewal
- Link to manage subscription (if website URL provided)

Emails are sent in both HTML and plain text formats.

## Scheduling

The scheduler uses APScheduler and runs automatically when the app starts. The daily check runs at 9 AM server time.

To change the schedule, edit `backend-py/app/scheduler/reminder_scheduler.py`:

```python
trigger=CronTrigger(hour=9, minute=0)  # Change this
```

## Troubleshooting

### Reminders not sending

1. Check SMTP credentials are correct
2. Verify `SUPABASE_SERVICE_KEY` is set (required for user email lookup)
3. Check server logs for errors
4. Test SMTP connection manually

### User emails not found

- Ensure `SUPABASE_SERVICE_KEY` has admin privileges
- Verify users exist in Supabase Auth
- Check logs for specific user ID errors

### Scheduler not running

- Check app startup logs for scheduler initialization
- Verify APScheduler is installed: `pip install apscheduler==3.10.4`
- Check for exceptions in logs

## Dependencies

The reminder system requires these packages:
- `aiosmtplib==3.0.1` - Async SMTP client
- `apscheduler==3.10.4` - Job scheduler
- `jinja2==3.1.4` - Email template rendering

Install with:
```bash
pip install -r requirements.txt
```

