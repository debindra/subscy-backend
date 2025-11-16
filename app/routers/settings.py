from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import Optional
from app.core.dependencies import get_current_user
from app.core.supabase import supabase

router = APIRouter()


class UpdateSettingsDTO(BaseModel):
    monthlyBudget: Optional[float] = Field(None, ge=0)
    budgetAlertsEnabled: Optional[bool] = None
    budgetAlertThreshold: Optional[int] = Field(None, ge=1, le=100)


@router.get("/")
async def get_settings(current_user: dict = Depends(get_current_user)):
    """Get user settings"""
    try:
        response = supabase.table("user_settings")\
            .select("*")\
            .eq("userId", current_user["id"])\
            .execute()
        
        if not response.data or len(response.data) == 0:
            # Create default settings if none exist
            default_settings = {
                "userId": current_user["id"],
                "monthlyBudget": None,
                "budgetAlertsEnabled": True,
                "budgetAlertThreshold": 90,
            }
            
            create_response = supabase.table("user_settings")\
                .insert(default_settings)\
                .execute()
            
            if not create_response.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create default settings"
                )
            
            return create_response.data[0]
        
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.patch("/")
async def update_settings(
    dto: UpdateSettingsDTO,
    current_user: dict = Depends(get_current_user)
):
    """Update user settings"""
    try:
        # First get or create settings
        existing_response = supabase.table("user_settings")\
            .select("*")\
            .eq("userId", current_user["id"])\
            .execute()
        
        if not existing_response.data or len(existing_response.data) == 0:
            # Create default settings first
            default_settings = {
                "userId": current_user["id"],
                "monthlyBudget": None,
                "budgetAlertsEnabled": True,
                "budgetAlertThreshold": 90,
            }
            
            create_response = supabase.table("user_settings")\
                .insert(default_settings)\
                .execute()
            
            if not create_response.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create default settings"
                )
        
        # Prepare update data
        update_data = {}
        if dto.monthlyBudget is not None:
            update_data["monthlyBudget"] = dto.monthlyBudget
        if dto.budgetAlertsEnabled is not None:
            update_data["budgetAlertsEnabled"] = dto.budgetAlertsEnabled
        if dto.budgetAlertThreshold is not None:
            update_data["budgetAlertThreshold"] = dto.budgetAlertThreshold
        
        if not update_data:
            # Return existing settings if nothing to update
            existing_response = supabase.table("user_settings")\
                .select("*")\
                .eq("userId", current_user["id"])\
                .execute()
            return existing_response.data[0] if existing_response.data else None
        
        response = supabase.table("user_settings")\
            .update(update_data)\
            .eq("userId", current_user["id"])\
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update settings"
            )
        
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/budget-status")
async def get_budget_status(
    currentSpending: float = Query(...),
    current_user: dict = Depends(get_current_user)
):
    """Check budget status based on current spending"""
    try:
        # Get user settings
        settings_response = supabase.table("user_settings")\
            .select("*")\
            .eq("userId", current_user["id"])\
            .execute()
        
        if not settings_response.data or len(settings_response.data) == 0:
            # No budget set
            return {
                "withinBudget": True,
                "budgetAmount": None,
                "spendingAmount": currentSpending,
                "percentageUsed": None,
                "alertTriggered": False,
            }
        
        settings = settings_response.data[0]
        monthly_budget = settings.get("monthlyBudget")
        
        if monthly_budget is None:
            return {
                "withinBudget": True,
                "budgetAmount": None,
                "spendingAmount": currentSpending,
                "percentageUsed": None,
                "alertTriggered": False,
            }
        
        monthly_budget = float(monthly_budget)
        percentage_used = (currentSpending / monthly_budget) * 100
        within_budget = currentSpending <= monthly_budget
        budget_alerts_enabled = settings.get("budgetAlertsEnabled", True)
        budget_alert_threshold = settings.get("budgetAlertThreshold", 90)
        alert_triggered = budget_alerts_enabled and percentage_used >= budget_alert_threshold
        
        return {
            "withinBudget": within_budget,
            "budgetAmount": monthly_budget,
            "spendingAmount": currentSpending,
            "percentageUsed": round(percentage_used, 1),
            "alertTriggered": alert_triggered,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

