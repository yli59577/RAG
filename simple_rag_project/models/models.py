"""資料庫模型定義"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey, JSON, Integer
from sqlalchemy.orm import relationship

from .base import Base


class User(Base):
    """使用者模型"""
    __tablename__ = "users"
    
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    
    # 關聯
    documents = relationship("Document", back_populates="owner")
    chat_histories = relationship("ChatHistory", back_populates="user")


class Document(Base):
    """文件模型"""
    __tablename__ = "documents"
    
    filename = Column(String(255), nullable=False)
    category = Column(String(100), index=True, default="default")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    
    # 關聯
    owner = relationship("User", back_populates="documents")


class ChatHistory(Base):
    """對話歷史模型"""
    __tablename__ = "chat_histories"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String(50), index=True, nullable=False)
    title = Column(String(200), default="新對話")
    messages = Column(JSON, default=list)  # [{"role": "user/assistant", "content": "..."}]
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 關聯
    user = relationship("User", back_populates="chat_histories")
