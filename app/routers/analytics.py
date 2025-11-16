from fastapi import APIRouter, Query, Depends, HTTPException, status
from typing import Optional
from datetime import datetime, timedelta
from app.core.dependencies import get_current_user
from app.core.supabase import supabase
from app.core.plan_limits import get_plan_limits

router = APIRouter()


@router.get("/spending")
async def get_spending_summary(current_user: dict = Depends(get_current_user)):
    """Get spending summary (monthly and yearly totals) grouped by currency"""
    try:
        response = supabase.table("subscriptions")\
            .select("*")\
            .eq("userId", current_user["id"])\
            .eq("isActive", True)\
            .execute()
        
        subscriptions = response.data if response.data else []
        
        summary_map: dict[str, dict[str, float | int]] = {}

        for sub in subscriptions:
            currency = sub.get("currency", "USD") or "USD"
            amount = float(sub.get("amount", 0))
            billing_cycle = sub.get("billingCycle", "monthly")

            if currency not in summary_map:
                summary_map[currency] = {
                    "monthlyTotal": 0.0,
                    "yearlyTotal": 0.0,
                    "totalSubscriptions": 0,
                }

            summary = summary_map[currency]

            if billing_cycle == "monthly":
                summary["monthlyTotal"] += amount
                summary["yearlyTotal"] += amount * 12
            elif billing_cycle == "yearly":
                summary["monthlyTotal"] += amount / 12
                summary["yearlyTotal"] += amount
            elif billing_cycle == "quarterly":
                summary["monthlyTotal"] += amount / 3
                summary["yearlyTotal"] += amount * 4
            elif billing_cycle == "weekly":
                summary["monthlyTotal"] += amount * 4.33
                summary["yearlyTotal"] += amount * 52
            else:
                summary["monthlyTotal"] += amount
                summary["yearlyTotal"] += amount * 12

            summary["totalSubscriptions"] += 1

        result = [
            {
                "currency": currency,
                "monthlyTotal": round(values["monthlyTotal"], 2),
                "yearlyTotal": round(values["yearlyTotal"], 2),
                "totalSubscriptions": values["totalSubscriptions"],
            }
            for currency, values in sorted(summary_map.items())
        ]

        return result
    except Exception as e:
        raise Exception(f"Error getting spending summary: {str(e)}")


@router.get("/by-category")
async def get_spending_by_category(current_user: dict = Depends(get_current_user)):
    """Get spending breakdown by category"""
    try:
        response = supabase.table("subscriptions")\
            .select("*")\
            .eq("userId", current_user["id"])\
            .eq("isActive", True)\
            .execute()
        
        subscriptions = response.data if response.data else []
        
        category_map = {}
        
        for sub in subscriptions:
            amount = float(sub.get("amount", 0))
            billing_cycle = sub.get("billingCycle", "monthly")
            category = sub.get("category", "Uncategorized")
            
            monthly_amount = 0.0
            if billing_cycle == "monthly":
                monthly_amount = amount
            elif billing_cycle == "yearly":
                monthly_amount = amount / 12
            elif billing_cycle == "quarterly":
                monthly_amount = amount / 3
            elif billing_cycle == "weekly":
                monthly_amount = amount * 4.33
            
            if category not in category_map:
                category_map[category] = 0.0
            category_map[category] += monthly_amount
        
        result = [
            {"category": category, "amount": round(amount, 2)}
            for category, amount in category_map.items()
        ]
        
        return result
    except Exception as e:
        raise Exception(f"Error getting spending by category: {str(e)}")


@router.get("/monthly-trend")
async def get_monthly_trend(
    months: Optional[int] = Query(12, ge=1, le=24),
    current_user: dict = Depends(get_current_user)
):
    """Get monthly spending trend over the specified number of months"""
    try:
        account_type = current_user.get("accountType", "personal")
        plan_limits = get_plan_limits(account_type)
        trend_limits = plan_limits.get("analytics", {}).get("monthly_trend", {})

        if not trend_limits.get("enabled", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Upgrade to access monthly trend analytics."
            )

        max_months = trend_limits.get("max_months")
        if max_months is not None and months and months > max_months:
            months = max_months

        response = supabase.table("subscriptions")\
            .select("*")\
            .eq("userId", current_user["id"])\
            .execute()
        
        subscriptions = response.data if response.data else []
        
        monthly_data = []
        today = datetime.now()
        
        for i in range(months - 1, -1, -1):
            # Calculate month start
            month_offset = today.month - i
            year_offset = 0
            while month_offset <= 0:
                month_offset += 12
                year_offset -= 1
            while month_offset > 12:
                month_offset -= 12
                year_offset += 1
            
            month_start = datetime(today.year + year_offset, month_offset, 1)
            
            # Calculate last day of month
            if month_offset == 12:
                month_end = datetime(month_start.year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = datetime(month_start.year, month_start.month + 1, 1) - timedelta(days=1)
            
            month_name = month_start.strftime("%b %Y")
            
            month_total = 0.0
            
            for sub in subscriptions:
                created_at_str = sub.get("createdAt")
                if not created_at_str:
                    continue
                
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                is_active = sub.get("isActive", True)
                
                # Count subscriptions that existed by the end of this month and are active
                if created_at <= month_end.replace(tzinfo=created_at.tzinfo) and is_active:
                    amount = float(sub.get("amount", 0))
                    billing_cycle = sub.get("billingCycle", "monthly")
                    
                    if billing_cycle == "monthly":
                        month_total += amount
                    elif billing_cycle == "yearly":
                        month_total += amount / 12
                    elif billing_cycle == "quarterly":
                        month_total += amount / 3
                    elif billing_cycle == "weekly":
                        month_total += amount * 4.33
            
            monthly_data.append({
                "month": month_name,
                "total": round(month_total, 2),
            })
        
        return monthly_data
    except Exception as e:
        raise Exception(f"Error getting monthly trend: {str(e)}")


@router.get("/stats")
async def get_subscription_stats(current_user: dict = Depends(get_current_user)):
    """Get subscription statistics"""
    try:
        response = supabase.table("subscriptions")\
            .select("*")\
            .eq("userId", current_user["id"])\
            .execute()
        
        subscriptions = response.data if response.data else []
        
        active = sum(1 for sub in subscriptions if sub.get("isActive", True))
        inactive = len(subscriptions) - active
        categories = len(set(sub.get("category", "Uncategorized") for sub in subscriptions))
        
        return {
            "total": len(subscriptions),
            "active": active,
            "inactive": inactive,
            "categories": categories,
        }
    except Exception as e:
        raise Exception(f"Error getting subscription stats: {str(e)}")


