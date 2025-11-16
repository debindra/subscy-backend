from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from app.core.dependencies import get_current_user
from app.services.reminder_service import reminder_service

router = APIRouter()


@router.post("/check", tags=["reminders"])
async def trigger_reminder_check(current_user: dict = Depends(get_current_user)):
    """
    Manually trigger a reminder check.
    This endpoint checks all subscriptions that need reminders and sends emails.
    Note: In production, reminders are sent automatically via scheduled job.
    """
    try:
        stats = await reminder_service.check_and_send_reminders()
        return {
            "success": True,
            "message": "Reminder check completed",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking reminders: {str(e)}"
        )


@router.get("/upcoming", tags=["reminders"])
async def get_my_upcoming_reminders(
    days: int = 7,
    current_user: dict = Depends(get_current_user)
):
    """
    Get subscriptions that will trigger reminders for the current user
    within the specified number of days.
    """
    try:
        reminders = await reminder_service.get_upcoming_reminders(
            user_id=current_user["id"],
            days=days
        )
        return {
            "success": True,
            "reminders": reminders,
            "count": len(reminders)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching upcoming reminders: {str(e)}"
        )

