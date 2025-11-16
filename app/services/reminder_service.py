from datetime import datetime, timedelta, date
from typing import List, Dict
from app.core.supabase import supabase_admin
from app.services.email_service import email_service


class ReminderService:
    """Service for checking and sending subscription renewal reminders"""
    
    async def check_and_send_reminders(self) -> Dict[str, any]:
        """
        Check all subscriptions that need reminders and send emails.
        Returns statistics about the reminder process.
        """
        stats = {
            "checked": 0,
            "sent": 0,
            "failed": 0,
            "errors": []
        }
        
        try:
            today = date.today()
            
            # Get all active subscriptions with reminders enabled
            # We'll check for subscriptions renewing within the next 30 days
            # and match them against their reminderDaysBefore setting
            response = supabase_admin.table("subscriptions")\
                .select("*")\
                .eq("isActive", True)\
                .eq("reminderEnabled", True)\
                .gte("nextRenewalDate", today.isoformat())\
                .lte("nextRenewalDate", (today + timedelta(days=30)).isoformat())\
                .execute()
            
            subscriptions = response.data if response.data else []
            stats["checked"] = len(subscriptions)
            
            if not subscriptions:
                print(f"No subscriptions found needing reminders on {today.isoformat()}")
                return stats
            
            # Get user emails - we'll need to join with auth.users
            # Since we can't directly join, we'll collect unique user IDs and fetch user emails
            user_ids = set(sub.get("userId") for sub in subscriptions if sub.get("userId"))
            
            # Fetch user emails from Supabase Auth
            user_emails = {}
            user_names = {}
            
            for user_id in user_ids:
                try:
                    # Get user from Supabase Auth using admin client
                    # Note: This requires service role key
                    try:
                        user_response = supabase_admin.auth.admin.get_user_by_id(user_id)
                        if user_response and hasattr(user_response, 'user') and user_response.user:
                            email = user_response.user.email
                            user_emails[user_id] = email
                            # Get user name from metadata or email
                            user_data = getattr(user_response.user, 'user_metadata', {}) or {}
                            user_names[user_id] = user_data.get("name") or user_data.get("full_name") or email.split("@")[0]
                    except (AttributeError, Exception) as auth_error:
                        # Fallback: try to get user from auth.users table directly
                        try:
                            user_response = supabase_admin.table("auth.users").select("email, raw_user_meta_data").eq("id", user_id).execute()
                            if user_response.data and len(user_response.data) > 0:
                                user_data = user_response.data[0]
                                email = user_data.get("email")
                                if email:
                                    user_emails[user_id] = email
                                    meta = user_data.get("raw_user_meta_data", {}) or {}
                                    user_names[user_id] = meta.get("name") or meta.get("full_name") or email.split("@")[0]
                        except Exception as table_error:
                            print(f"Error fetching user {user_id} from table: {str(table_error)}")
                            raise auth_error
                except Exception as e:
                    print(f"Error fetching user {user_id}: {str(e)}")
                    stats["errors"].append(f"Error fetching user {user_id}: {str(e)}")
                    continue
            
            # Process each subscription
            for subscription in subscriptions:
                try:
                    user_id = subscription.get("userId")
                    if not user_id or user_id not in user_emails:
                        stats["failed"] += 1
                        stats["errors"].append(f"User email not found for subscription {subscription.get('id')}")
                        continue
                    
                    # Calculate days until renewal
                    renewal_date_str = subscription.get("nextRenewalDate")
                    if not renewal_date_str:
                        continue
                    
                    # Parse renewal date
                    if "T" in renewal_date_str:
                        renewal_date = datetime.fromisoformat(renewal_date_str.replace("Z", "+00:00")).date()
                    else:
                        renewal_date = datetime.strptime(renewal_date_str, "%Y-%m-%d").date()
                    
                    days_until = (renewal_date - today).days
                    reminder_days_before = subscription.get("reminderDaysBefore", 7)
                    
                    # Check if we should send reminder today
                    if days_until == reminder_days_before:
                        # Send reminder email
                        user_email = user_emails[user_id]
                        user_name = user_names.get(user_id, "User")
                        
                        success = await email_service.send_reminder_email(
                            to_email=user_email,
                            user_name=user_name,
                            subscription=subscription,
                            days_until=days_until
                        )
                        
                        if success:
                            stats["sent"] += 1
                            print(f"Reminder sent: {subscription.get('name')} to {user_email} ({days_until} days)")
                        else:
                            stats["failed"] += 1
                            stats["errors"].append(f"Failed to send reminder for subscription {subscription.get('id')}")
                            
                except Exception as e:
                    stats["failed"] += 1
                    error_msg = f"Error processing subscription {subscription.get('id', 'unknown')}: {str(e)}"
                    stats["errors"].append(error_msg)
                    print(error_msg)
                    continue
            
            print(f"Reminder check completed: {stats['sent']} sent, {stats['failed']} failed")
            return stats
            
        except Exception as e:
            error_msg = f"Error in reminder check: {str(e)}"
            stats["errors"].append(error_msg)
            print(error_msg)
            return stats
    
    async def get_upcoming_reminders(self, user_id: str, days: int = 7) -> List[Dict]:
        """Get subscriptions that will trigger reminders within the specified days"""
        today = date.today()
        future_date = today + timedelta(days=days)
        
        response = supabase_admin.table("subscriptions")\
            .select("*")\
            .eq("userId", user_id)\
            .eq("isActive", True)\
            .eq("reminderEnabled", True)\
            .gte("nextRenewalDate", today.isoformat())\
            .lte("nextRenewalDate", future_date.isoformat())\
            .execute()
        
        subscriptions = response.data if response.data else []
        
        # Filter to only those that will trigger reminders
        reminders = []
        for sub in subscriptions:
            renewal_date_str = sub.get("nextRenewalDate")
            if not renewal_date_str:
                continue
            
            if "T" in renewal_date_str:
                renewal_date = datetime.fromisoformat(renewal_date_str.replace("Z", "+00:00")).date()
            else:
                renewal_date = datetime.strptime(renewal_date_str, "%Y-%m-%d").date()
            
            days_until = (renewal_date - today).days
            reminder_days_before = sub.get("reminderDaysBefore", 7)
            
            if days_until == reminder_days_before:
                reminders.append(sub)
        
        return reminders


# Singleton instance
reminder_service = ReminderService()

