from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from app.core.supabase import supabase

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    x_account_context: Optional[str] = Header(None, alias="X-Account-Context")
) -> dict:
    """
    Verify JWT token and return current user.
    Similar to AuthGuard in TypeScript backend.
    Supports account context switching via X-Account-Context header.
    """
    token = credentials.credentials
    
    try:
        # Verify token with Supabase
        response = supabase.auth.get_user(token)
        
        if response.user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        metadata = response.user.user_metadata or {}
        
        # Determine account context: header takes precedence, then metadata, then default to free
        # Support legacy "personal" and "business" types, but default new users to "free"
        account_context = None
        if x_account_context and x_account_context in ["personal", "business", "free", "pro", "family"]:
            account_context = x_account_context
            # Validate business context access
            if account_context == "business":
                try:
                    profile_response = supabase.table("business_profiles")\
                        .select("id")\
                        .eq("userId", response.user.id)\
                        .execute()
                    if len(profile_response.data) == 0:
                        # Fall back to metadata account type if business not available
                        account_context = metadata.get("account_type", "free")
                except Exception:
                    account_context = metadata.get("account_type", "free")
        else:
            # Map legacy "personal" to "free" for backward compatibility
            account_type_from_metadata = metadata.get("account_type", "free")
            if account_type_from_metadata == "personal":
                account_context = "free"
            else:
                account_context = account_type_from_metadata

        return {
            "id": response.user.id,
            "email": response.user.email,
            "accountType": account_context,
            "accountContext": account_context,  # Alias for consistency
            "user_metadata": metadata,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

