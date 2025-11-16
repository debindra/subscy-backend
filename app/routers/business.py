from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional

from app.core.dependencies import get_current_user
from app.core.supabase import supabase, supabase_admin
from app.core.plan_limits import get_plan_limits

router = APIRouter()


class BusinessProfileDTO(BaseModel):
    companyName: str = Field(..., min_length=2)
    companyAddress: Optional[str] = None
    companyTaxId: Optional[str] = None
    companyPhone: Optional[str] = None


@router.get("/profile")
async def get_business_profile(current_user: dict = Depends(get_current_user)):
    """Fetch the current user's business profile."""
    if current_user.get("accountType", "personal") != "business":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Business account required"
        )

    try:
        response = supabase.table("business_profiles")\
            .select("*")\
            .eq("userId", current_user["id"])\
            .single()\
            .execute()

        if response.data:
            return response.data
    except Exception:
        # Fallback to metadata if table lookup fails or no entry exists
        metadata = current_user.get("user_metadata", {})
        if metadata.get("company_name"):
            return {
                "userId": current_user["id"],
                "companyName": metadata.get("company_name"),
                "companyAddress": metadata.get("company_address"),
                "companyTaxId": metadata.get("company_tax_id"),
                "companyPhone": metadata.get("company_phone"),
            }

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Business profile not found"
    )


@router.put("/profile")
async def upsert_business_profile(
    dto: BusinessProfileDTO,
    current_user: dict = Depends(get_current_user)
):
    """Create or update the current user's business profile."""
    if current_user.get("accountType", "personal") != "business":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Business account required"
        )

    profile_payload = {
        "userId": current_user["id"],
        "companyName": dto.companyName,
        "companyAddress": dto.companyAddress,
        "companyTaxId": dto.companyTaxId,
        "companyPhone": dto.companyPhone,
    }

    try:
        response = supabase.table("business_profiles")\
            .upsert(profile_payload, on_conflict="userId")\
            .execute()

        # Refresh user metadata to stay in sync
        metadata = current_user.get("user_metadata", {}).copy()
        metadata.update({
            "account_type": "business",
            "company_name": dto.companyName,
            "company_address": dto.companyAddress,
            "company_tax_id": dto.companyTaxId,
            "company_phone": dto.companyPhone,
        })

        try:
            supabase_admin.auth.admin.update_user_by_id(
                current_user["id"],
                {
                    "user_metadata": {k: v for k, v in metadata.items() if v is not None},
                }
            )
        except Exception:
            # If metadata sync fails, continue – the profile table still has the source of truth.
            pass

        return response.data[0] if response.data else profile_payload
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/plan")
async def get_current_plan(current_user: dict = Depends(get_current_user)):
    """Return plan details and limits for the authenticated user."""
    account_type = current_user.get("accountType", "personal")
    plan_limits = get_plan_limits(account_type)

    return {
        "accountType": account_type,
        "limits": plan_limits,
    }

