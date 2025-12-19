"""認證 API"""
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr
from typing import Optional

from utils.database import get_session
from services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["認證"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    token: str
    message: str


class MessageResponse(BaseModel):
    message: str


@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest):
    """註冊新使用者"""
    async with get_session() as session:
        try:
            user = await AuthService.register(
                session, request.email, request.password, request.name
            )
            token = AuthService.create_token(user.id, user.email)
            return TokenResponse(token=token, message="註冊成功")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """登入"""
    async with get_session() as session:
        token = await AuthService.login(session, request.email, request.password)
        if not token:
            raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
        return TokenResponse(token=token, message="登入成功")


@router.get("/me")
async def get_current_user(authorization: str = Header(...)):
    """取得目前使用者資訊"""
    token = authorization.replace("Bearer ", "")
    async with get_session() as session:
        user = await AuthService.get_user_by_token(session, token)
        if not user:
            raise HTTPException(status_code=401, detail="無效的 Token")
        return {
            "id": user.id,
            "email": user.email,
            "name": user.name
        }


# 依賴注入：取得目前使用者 ID
async def get_current_user_id(authorization: str = Header(...)) -> int:
    """從 Token 取得使用者 ID"""
    token = authorization.replace("Bearer ", "")
    payload = AuthService.decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="無效的 Token")
    return payload["user_id"]
