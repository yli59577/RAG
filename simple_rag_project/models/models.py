"""資料庫模型定義"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, Integer, CheckConstraint

from .base import Base


class Document(Base):
    """文件模型"""
    __tablename__ = "documents"
    
    filename = Column(String(255), nullable=False)
    category = Column(String(100), index=True, default="default")
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')", name="check_document_status"),
        CheckConstraint("chunk_count >= 0", name="check_chunk_count_positive"),
    )
    
    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename='{self.filename}', status='{self.status}')>"


class ChatHistory(Base):
    """對話歷史模型"""
    __tablename__ = "chat_histories"
    
    session_id = Column(String(50), index=True, nullable=False, unique=True)
    title = Column(String(200), default="新對話")
    messages = Column(JSON, default=list)  # [{"role": "user/assistant", "content": "..."}]
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<ChatHistory(id={self.id}, session_id='{self.session_id}', messages_count={len(self.messages) if self.messages else 0})>"
