from fastapi import APIRouter, HTTPException, status, Header
from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import Optional, Literal
from app.core.supabase import supabase, supabase_admin

router = APIRouter()


class SignUpDTO(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    fullName: Optional[str] = None
    accountType: Literal["personal", "business"] = "personal"
    companyName: Optional[str] = None
    companyAddress: Optional[str] = None
    companyTaxId: Optional[str] = None
    companyPhone: Optional[str] = None

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


