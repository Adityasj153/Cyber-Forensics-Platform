from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.audit import log_audit_event
from app.core.security import (
    create_access_token,
    create_user,
    get_user_by_username,
    verify_password,
)
from app.db.models.base_models import User, UserRole
from app.db.session import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str

    model_config = {"from_attributes": True}


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_username(db, body.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")

    user = await create_user(db, body.username, body.email, body.password, UserRole.VIEWER)
    await log_audit_event(db, action="user_registered", target_type="user", target_id=str(user.id))
    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        role=user.role.value,
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_username(db, body.username)
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(data={"sub": user.username, "role": user.role.value})
    await log_audit_event(db, action="user_login", target_type="user", target_id=str(user.id))
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return UserResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        role=current_user.role.value,
    )
