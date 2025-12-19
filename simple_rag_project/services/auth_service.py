"""認證服務"""
import hashlib
import jwt
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models import User


class AuthService:
    """認證服務"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """密碼雜湊"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """驗證密碼"""
        return AuthService.hash_password(password) == hashed
    
    @staticmethod
    def create_token(user_id: int, email: str) -> str:
        """建立 JWT Token"""
        payload = {
            "user_id": user_id,
            "email": email,
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, settings.secret_key, algorithm="HS256")
    
    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """解碼 JWT Token"""
        try:
            return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    @staticmethod
    async def register(session: AsyncSession, email: str, password: str, name: str = None) -> User:
        """註冊新使用者"""
        # 檢查是否已存在
        existing = await session.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise ValueError("Email 已被註冊")
        
        user = User(
            email=email,
            password_hash=AuthService.hash_password(password),
            name=name
        )
        session.add(user)
        await session.flush()
        return user
    
    @staticmethod
    async def login(session: AsyncSession, email: str, password: str) -> Optional[str]:
        """登入並返回 Token"""
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if not user or not AuthService.verify_password(password, user.password_hash):
            return None
        
        return AuthService.create_token(user.id, user.email)
    
    @staticmethod
    async def get_user_by_token(session: AsyncSession, token: str) -> Optional[User]:
        """根據 Token 取得使用者"""
        payload = AuthService.decode_token(token)
        if not payload:
            return None
        
        result = await session.execute(select(User).where(User.id == payload["user_id"]))
        return result.scalar_one_or_none()
