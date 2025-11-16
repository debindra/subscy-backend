from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta
from app.core.dependencies import get_current_user
from app.core.supabase import supabase
from app.core.plan_limits import get_plan_limits

router = APIRouter()


class CreateSubscriptionDTO(BaseModel):
    name: str
    amount: float = Field(gt=0)
    currency: str = "USD"
    billingCycle: str = Field(pattern="^(monthly|yearly|quarterly|weekly)$")
    nextRenewalDate: str  # ISO date string
    category: str
    description: Optional[str] = None
    website: Optional[str] = None
    isActive: bool = True
    reminderEnabled: bool = True
    reminderDaysBefore: int = Field(default=7, ge=1)
    paymentMethod: Optional[str] = Field(None, pattern="^(credit_card|debit_card|paypal|bank_transfer|apple_pay|google_pay|other)$")
    lastFourDigits: Optional[str] = None
    cardBrand: Optional[str] = None
    isTrial: bool = False
    trialEndDate: Optional[str] = None  # ISO date string


class UpdateSubscriptionDTO(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = Field(None, gt=0)
    currency: Optional[str] = None
    billingCycle: Optional[str] = Field(None, pattern="^(monthly|yearly|quarterly|weekly)$")
    nextRenewalDate: Optional[str] = None  # ISO date string
    category: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    isActive: Optional[bool] = None
    reminderEnabled: Optional[bool] = None
    reminderDaysBefore: Optional[int] = Field(None, ge=1)
    paymentMethod: Optional[str] = Field(None, pattern="^(credit_card|debit_card|paypal|bank_transfer|apple_pay|google_pay|other)$")
    lastFourDigits: Optional[str] = None
    cardBrand: Optional[str] = None
    isTrial: Optional[bool] = None
    trialEndDate: Optional[str] = None  # ISO date string


@router.post("/")
async def create_subscription(
    dto: CreateSubscriptionDTO,
    current_user: dict = Depends(get_current_user)
):
    """Create a new subscription"""
    try:
        plan_limits = get_plan_limits(current_user.get("accountType", "personal"))
        max_subscriptions = plan_limits.get("max_subscriptions")

        if max_subscriptions is not None:
            count_response = supabase.table("subscriptions")\
                .select("id", count="exact")\
                .eq("userId", current_user["id"])\
                .execute()

            existing_count = getattr(count_response, "count", None)
            if existing_count is None:
                existing_count = len(count_response.data) if count_response.data else 0

            if existing_count >= max_subscriptions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Subscription limit reached for your current plan."
                )

        # Validate required date field
        if not dto.nextRenewalDate or not dto.nextRenewalDate.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="nextRenewalDate is required and cannot be empty"
            )

        subscription_data = {
            "userId": current_user["id"],
            "name": dto.name,
            "amount": dto.amount,
            "currency": dto.currency,
            "billingCycle": dto.billingCycle,
            "nextRenewalDate": dto.nextRenewalDate.strip(),
            "category": dto.category,
            "description": dto.description,
            "website": dto.website,
            "isActive": dto.isActive,
            "reminderEnabled": dto.reminderEnabled,
            "reminderDaysBefore": dto.reminderDaysBefore,
            "paymentMethod": dto.paymentMethod,
            "lastFourDigits": dto.lastFourDigits,
            "cardBrand": dto.cardBrand,
            "isTrial": dto.isTrial,
            "trialEndDate": dto.trialEndDate if dto.trialEndDate and dto.trialEndDate.strip() else None,
        }
        
        # Remove None values and empty strings for date fields
        subscription_data = {
            k: v for k, v in subscription_data.items() 
            if v is not None and not (k in ["trialEndDate", "nextRenewalDate"] and v == "")
        }
        
        response = supabase.table("subscriptions").insert(subscription_data).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create subscription"
            )
        
        return response.data[0]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/")
async def list_subscriptions(current_user: dict = Depends(get_current_user)):
    """Get all subscriptions for the current user"""
    try:
        response = supabase.table("subscriptions")\
            .select("*")\
            .eq("userId", current_user["id"])\
            .order("nextRenewalDate", desc=False)\
            .execute()
        
        return response.data if response.data else []
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/upcoming")
async def get_upcoming_renewals(
    current_user: dict = Depends(get_current_user),
    days: int = 7
):
    """Get upcoming renewals within the specified number of days"""
    try:
        today = datetime.now().date()
        future_date = today + timedelta(days=days)
        
        response = supabase.table("subscriptions")\
            .select("*")\
            .eq("userId", current_user["id"])\
            .eq("isActive", True)\
            .eq("reminderEnabled", True)\
            .gte("nextRenewalDate", today.isoformat())\
            .lte("nextRenewalDate", future_date.isoformat())\
            .order("nextRenewalDate", desc=False)\
            .execute()
        
        return response.data if response.data else []
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{id}")
async def get_subscription(
    id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific subscription by ID"""
    try:
        response = supabase.table("subscriptions")\
            .select("*")\
            .eq("id", id)\
            .eq("userId", current_user["id"])\
            .execute()
        
        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )
        
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.patch("/{id}")
async def update_subscription(
    id: str,
    dto: UpdateSubscriptionDTO,
    current_user: dict = Depends(get_current_user)
):
    """Update a subscription"""
    try:
        # First verify the subscription exists and belongs to the user
        existing = supabase.table("subscriptions")\
            .select("*")\
            .eq("id", id)\
            .eq("userId", current_user["id"])\
            .execute()
        
        if not existing.data or len(existing.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )
        
        # Prepare update data
        update_data = {}
        if dto.name is not None:
            update_data["name"] = dto.name
        if dto.amount is not None:
            update_data["amount"] = dto.amount
        if dto.currency is not None:
            update_data["currency"] = dto.currency
        if dto.billingCycle is not None:
            update_data["billingCycle"] = dto.billingCycle
        if dto.category is not None:
            update_data["category"] = dto.category
        if dto.description is not None:
            update_data["description"] = dto.description
        if dto.website is not None:
            update_data["website"] = dto.website
        if dto.isActive is not None:
            update_data["isActive"] = dto.isActive
        if dto.reminderEnabled is not None:
            update_data["reminderEnabled"] = dto.reminderEnabled
        if dto.reminderDaysBefore is not None:
            update_data["reminderDaysBefore"] = dto.reminderDaysBefore
        if dto.paymentMethod is not None:
            update_data["paymentMethod"] = dto.paymentMethod
        if dto.lastFourDigits is not None:
            update_data["lastFourDigits"] = dto.lastFourDigits
        if dto.cardBrand is not None:
            update_data["cardBrand"] = dto.cardBrand
        if dto.nextRenewalDate is not None:
            # Ensure nextRenewalDate is not empty
            if dto.nextRenewalDate and dto.nextRenewalDate.strip():
                update_data["nextRenewalDate"] = dto.nextRenewalDate
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="nextRenewalDate cannot be empty"
                )
        if dto.isTrial is not None:
            update_data["isTrial"] = dto.isTrial
        if dto.trialEndDate is not None:
            # Convert empty string to None for date fields
            update_data["trialEndDate"] = dto.trialEndDate if dto.trialEndDate and dto.trialEndDate.strip() else None
        
        if not update_data:
            return existing.data[0]
        
        response = supabase.table("subscriptions")\
            .update(update_data)\
            .eq("id", id)\
            .eq("userId", current_user["id"])\
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update subscription"
            )
        
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{id}")
async def delete_subscription(
    id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a subscription"""
    try:
        # First verify the subscription exists and belongs to the user
        existing = supabase.table("subscriptions")\
            .select("*")\
            .eq("id", id)\
            .eq("userId", current_user["id"])\
            .execute()
        
        if not existing.data or len(existing.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )
        
        response = supabase.table("subscriptions")\
            .delete()\
            .eq("id", id)\
            .eq("userId", current_user["id"])\
            .execute()
        
        return {"message": "Subscription deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


