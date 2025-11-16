import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.services.reminder_service import reminder_service
import logging

logger = logging.getLogger(__name__)


class ReminderScheduler:
    """Scheduler for running reminder checks"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
    
    def start(self):
        """Start the scheduler"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        # Schedule daily reminder check at 9 AM
        self.scheduler.add_job(
            func=self._check_reminders,
            trigger=CronTrigger(hour=9, minute=0),  # 9 AM daily
            id="daily_reminder_check",
            name="Daily Subscription Reminder Check",
            replace_existing=True,
            max_instances=1
        )
        
        self.scheduler.start()
        self.is_running = True
        logger.info("Reminder scheduler started - will check for reminders daily at 9 AM")
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
        self.is_running = False
        logger.info("Reminder scheduler stopped")
    
    async def _check_reminders(self):
        """Internal method to check and send reminders"""
        logger.info("Starting daily reminder check...")
        try:
            stats = await reminder_service.check_and_send_reminders()
            logger.info(
                f"Reminder check completed: "
                f"Checked: {stats['checked']}, "
                f"Sent: {stats['sent']}, "
                f"Failed: {stats['failed']}"
            )
            if stats['errors']:
                for error in stats['errors']:
                    logger.error(f"Reminder error: {error}")
        except Exception as e:
            logger.error(f"Error in reminder check: {str(e)}", exc_info=True)
    
    async def trigger_manual_check(self):
        """Manually trigger a reminder check (for testing or on-demand)"""
        logger.info("Manual reminder check triggered")
        return await self._check_reminders()


# Singleton instance
reminder_scheduler = ReminderScheduler()

