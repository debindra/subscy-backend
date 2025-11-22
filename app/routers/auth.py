import os
import re
from fastapi import APIRouter, HTTPException, status, Header, Depends
from pydantic import BaseModel, EmailStr, Field, model_validator, field_validator
from typing import Optional, Literal
from app.core.supabase import supabase, supabase_admin
from app.core.dependencies import get_current_user

PASSWORD_REGEX = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$')
PASSWORD_ERROR_MESSAGE = (
    "Password must be at least 8 characters long and include uppercase, lowercase, "
    "number, and special character."
)


def ensure_password_strength(password: str) -> str:
    if not PASSWORD_REGEX.match(password):
        raise ValueError(PASSWORD_ERROR_MESSAGE)
    return password


router = APIRouter()


class SignUpDTO(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    fullName: Optional[str] = None
    accountType: Literal["personal", "business", "free", "pro", "family"] = "free"
    companyName: Optional[str] = None
    companyAddress: Optional[str] = None
    companyTaxId: Optional[str] = None
    companyPhone: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        return ensure_password_strength(value)

    @model_validator(mode="after")
    def validate_business_fields(self):
        if self.accountType == "business" and not self.companyName:
            raise ValueError("companyName is required for business accounts")

        return self


class SignInDTO(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenDTO(BaseModel):
    refreshToken: str


class ForgotPasswordDTO(BaseModel):
    email: EmailStr


class ResetPasswordDTO(BaseModel):
    token: str
    password: str = Field(..., min_length=8)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        return ensure_password_strength(value)


class ChangePasswordDTO(BaseModel):
    currentPassword: str
    newPassword: str = Field(..., min_length=8)

    @field_validator("newPassword")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        return ensure_password_strength(value)


class CreateAccountContextDTO(BaseModel):
    accountType: Literal["personal", "business", "free", "pro", "family"]
    companyName: Optional[str] = None
    companyAddress: Optional[str] = None
    companyTaxId: Optional[str] = None
    companyPhone: Optional[str] = None

    @model_validator(mode="after")
    def validate_business_fields(self):
        if self.accountType == "business" and not self.companyName:
            raise ValueError("companyName is required for business accounts")
        return self


class SwitchAccountContextDTO(BaseModel):
    accountContext: Literal["personal", "business"]


class Tokens(BaseModel):
    access_token: str
    refresh_token: str
    user: Optional[dict] = None


@router.post("/signup")
async def signup(dto: SignUpDTO):
    """Sign up a new user"""
    try:
        metadata = {
            "full_name": dto.fullName,
            "account_type": dto.accountType,
        }

        if dto.accountType == "business":
            business_metadata = {
                "company_name": dto.companyName,
                "company_address": dto.companyAddress,
                "company_tax_id": dto.companyTaxId,
                "company_phone": dto.companyPhone,
            }
            metadata.update({k: v for k, v in business_metadata.items() if v})

        response = supabase.auth.sign_up({
            "email": dto.email,
            "password": dto.password,
            "options": {
                "data": {
                    **{k: v for k, v in metadata.items() if v is not None},
                }
            }
        })
        
        if response.user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user"
            )
        
        result = {
            "user": {
                "id": response.user.id,
                "email": response.user.email,
                "user_metadata": response.user.user_metadata or {},
            },
            "session": {
                "access_token": response.session.access_token if response.session else None,
                "refresh_token": response.session.refresh_token if response.session else None,
            } if response.session else None,
        }

        if dto.accountType == "business":
            try:
                profile_payload = {
                    "userId": response.user.id,
                    "companyName": dto.companyName,
                    "companyAddress": dto.companyAddress,
                    "companyTaxId": dto.companyTaxId,
                    "companyPhone": dto.companyPhone,
                }
                profile_payload = {k: v for k, v in profile_payload.items() if v is not None or k == "companyName"}
                if "companyName" in profile_payload:
                    supabase.table("business_profiles").upsert(
                        profile_payload,
                        on_conflict="userId"
                    ).execute()
            except Exception:
                # If business profile creation fails, still return success but include warning
                result["warnings"] = ["Business profile metadata could not be saved. Please update profile in settings."]

        return result
    except Exception as e:
        error_message = str(e)
        if "User already registered" in error_message or "already registered" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already registered"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )


@router.post("/signin")
async def signin(dto: SignInDTO):
    """Sign in with email and password"""
    try:
        response = supabase.auth.sign_in_with_password({
            "email": dto.email,
            "password": dto.password,
        })
        
        if response.user is None or response.session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        return {
            "user": {
                "id": response.user.id,
                "email": response.user.email,
                "user_metadata": response.user.user_metadata or {},
            },
            "session": {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
            },
        }
    except Exception as e:
        error_message = str(e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )


@router.post("/signout")
async def signout(authorization: Optional[str] = Header(None)):
    """Sign out the current user"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No token provided"
        )
    
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    
    try:
        # Use admin client to sign out by token
        supabase_admin.auth.admin.sign_out(token)
        return {"message": "Signed out successfully"}
    except Exception as e:
        # Even if there's an error, return success for client-side cleanup
        return {"message": "Signed out successfully"}


@router.post("/refresh")
async def refresh(dto: RefreshTokenDTO):
    """Refresh access token using refresh token"""
    try:
        response = supabase.auth.refresh_session({
            "refresh_token": dto.refreshToken,
        })
        
        if response.session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "user": {
                "id": response.user.id,
                "email": response.user.email,
                "user_metadata": response.user.user_metadata or {},
            } if response.user else None,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/verify")
async def verify(authorization: Optional[str] = Header(None)):
    """Verify if the provided token is valid"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No token provided"
        )
    
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    
    try:
        response = supabase.auth.get_user(token)
        
        if response.user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        return {
            "id": response.user.id,
            "email": response.user.email,
            "user_metadata": response.user.user_metadata or {},
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


@router.post("/forgot-password")
async def forgot_password(dto: ForgotPasswordDTO):
    """Request a password reset email"""
    try:
        # Use Supabase client to send password reset email
        # We don't check if the email exists for security reasons (prevent email enumeration)
        # Supabase will handle sending the email if the user exists
        redirect_url = os.getenv("PASSWORD_RESET_REDIRECT_URL")  # Can be configured via environment variable
        
        # Use the regular client to send password reset email
        # This will send an email with a recovery link if the user exists
        response = supabase.auth.reset_password_for_email(
            dto.email,
            {
                "redirect_to": redirect_url
            } if redirect_url else {}
        )
        
        # Always return success to prevent email enumeration attacks
        # This prevents attackers from discovering which emails are registered
        return {
            "message": "If an account exists for this email, you will receive a password reset link shortly."
        }
    except Exception as e:
        # Even on error, return success message for security
        # This prevents attackers from discovering which emails are registered
        return {
            "message": "If an account exists for this email, you will receive a password reset link shortly."
        }


@router.post("/reset-password")
async def reset_password(dto: ResetPasswordDTO):
    """Reset password using a recovery token"""
    try:
        # The standard Supabase password reset flow works as follows:
        # 1. User requests password reset (forgot-password endpoint)
        # 2. User receives email with recovery link containing a token
        # 3. User clicks link, which redirects to frontend with token
        # 4. Frontend exchanges token for session using supabase.auth.verifyOtp()
        # 5. User updates password using the session
        
        # For API-based reset, we need to:
        # 1. Verify the recovery token
        # 2. Extract user ID from token
        # 3. Update the user's password using admin client
        
        # Try to verify the token and get user info
        # The token from the email is typically a recovery token that can be verified
        try:
            # Use the token to verify and get user
            # Supabase recovery tokens are JWTs that contain user information
            # We can use the admin client to verify and update
            user_response = supabase.auth.get_user(dto.token)
            
            if user_response.user is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired recovery token. Please request a new password reset email."
                )
            
            user_id = user_response.user.id
            
            # Update the user's password using admin client
            update_response = supabase_admin.auth.admin.update_user_by_id(
                user_id,
                {
                    "password": dto.password
                }
            )
            
            if update_response.user is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to update password. Please try again."
                )
            
            return {
                "message": "Password has been reset successfully. You can now sign in with your new password."
            }
        except HTTPException:
            raise
        except Exception as token_error:
            # If token verification fails, the token might be invalid or expired
            # Or it might need to be exchanged for a session first
            # In that case, we should guide the user to use the email link
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired recovery token. Please use the password reset link from your email, or request a new password reset email."
            )
    except HTTPException:
        raise
    except Exception as e:
        error_message = str(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to reset password. Please request a new password reset email."
        )


@router.post("/change-password")
async def change_password(
    dto: ChangePasswordDTO,
    current_user: dict = Depends(get_current_user)
):
    """Change password for authenticated user"""
    try:
        if dto.currentPassword == dto.newPassword:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from current password."
            )
        # First verify the current password by attempting to sign in
        try:
            verify_response = supabase.auth.sign_in_with_password({
                "email": current_user["email"],
                "password": dto.currentPassword,
            })
            
            if verify_response.user is None or verify_response.session is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Current password is incorrect"
                )
        except Exception as e:
            # If sign in fails, current password is wrong
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect"
            )
        
        # If current password is correct, update to new password using admin client
        try:
            update_response = supabase_admin.auth.admin.update_user_by_id(
                current_user["id"],
                {
                    "password": dto.newPassword
                }
            )
            
            if update_response.user is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to update password. Please try again."
                )
            
            return {
                "message": "Password has been changed successfully."
            }
        except Exception as update_error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update password. Please try again."
            )
    except HTTPException:
        raise
    except Exception as e:
        error_message = str(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to change password. Please try again."
        )


@router.get("/account-contexts")
async def get_account_contexts(current_user: dict = Depends(get_current_user)):
    """Get available account contexts for the current user"""
    try:
        metadata = current_user.get("user_metadata", {})
        current_account_type = metadata.get("account_type", "free")
        # Map legacy "personal" to "free"
        if current_account_type == "personal":
            current_account_type = "free"
        
        # Check if user has business profile (indicates they have business context)
        has_business_profile = False
        try:
            profile_response = supabase.table("business_profiles")\
                .select("id")\
                .eq("userId", current_user["id"])\
                .execute()
            has_business_profile = len(profile_response.data) > 0
        except Exception:
            pass
        
        available_contexts = []
        
        # Always include personal
        available_contexts.append({
            "context": "personal",
            "label": "Personal",
            "isActive": current_account_type == "free" or current_account_type == "personal"
        })
        
        # Include business if they have business profile or current account is business
        if has_business_profile or current_account_type == "business":
            available_contexts.append({
                "context": "business",
                "label": "Business",
                "isActive": current_account_type == "business"
            })
        
        return {
            "availableContexts": available_contexts,
            "currentContext": current_account_type
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get account contexts: {str(e)}"
        )


@router.post("/create-account-context")
async def create_account_context(
    dto: CreateAccountContextDTO,
    current_user: dict = Depends(get_current_user)
):
    """Create an additional account context for the user"""
    try:
        metadata = current_user.get("user_metadata", {})
        current_account_type = metadata.get("account_type", "free")
        # Map legacy "personal" to "free"
        if current_account_type == "personal":
            current_account_type = "free"
        
        # Check if user already has this account type
        if current_account_type == dto.accountType:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You already have a {dto.accountType} account"
            )
        
        # If creating business context, create business profile
        if dto.accountType == "business":
            try:
                profile_payload = {
                    "userId": current_user["id"],
                    "companyName": dto.companyName,
                    "companyAddress": dto.companyAddress,
                    "companyTaxId": dto.companyTaxId,
                    "companyPhone": dto.companyPhone,
                }
                profile_payload = {k: v for k, v in profile_payload.items() if v is not None}
                
                supabase.table("business_profiles").upsert(
                    profile_payload,
                    on_conflict="userId"
                ).execute()
                
                # Update user metadata to include business account info
                updated_metadata = metadata.copy()
                updated_metadata.update({
                    "has_business_context": True,
                    "company_name": dto.companyName,
                    "company_address": dto.companyAddress,
                    "company_tax_id": dto.companyTaxId,
                    "company_phone": dto.companyPhone,
                })
                
                supabase_admin.auth.admin.update_user_by_id(
                    current_user["id"],
                    {
                        "user_metadata": {k: v for k, v in updated_metadata.items() if v is not None}
                    }
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to create business profile: {str(e)}"
                )
        
        return {
            "message": f"{dto.accountType.capitalize()} account context created successfully",
            "accountType": dto.accountType
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create account context: {str(e)}"
        )


@router.post("/switch-account-context")
async def switch_account_context(
    dto: SwitchAccountContextDTO,
    current_user: dict = Depends(get_current_user)
):
    """Switch the active account context"""
    try:
        metadata = current_user.get("user_metadata", {})
        current_account_type = metadata.get("account_type", "free")
        # Map legacy "personal" to "free"
        if current_account_type == "personal":
            current_account_type = "free"
        
        # Validate that user has access to the requested context
        if dto.accountContext == "business":
            # Check if user has business profile
            try:
                profile_response = supabase.table("business_profiles")\
                    .select("id")\
                    .eq("userId", current_user["id"])\
                    .execute()
                if len(profile_response.data) == 0:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Business account context not available. Please create a business account first."
                    )
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Business account context not available"
                )
        
        # Update user metadata with new account type
        updated_metadata = metadata.copy()
        updated_metadata["account_type"] = dto.accountContext
        
        try:
            supabase_admin.auth.admin.update_user_by_id(
                current_user["id"],
                {
                    "user_metadata": updated_metadata
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to switch account context: {str(e)}"
            )
        
        return {
            "message": f"Switched to {dto.accountContext} account context",
            "accountContext": dto.accountContext
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to switch account context: {str(e)}"
        )


