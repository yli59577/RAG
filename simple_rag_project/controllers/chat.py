"""對話 API - RAG 查詢"""
from typing import List
from fastapi import APIRouter
from pydantic import BaseModel

from utils.database import get_session
from services.chat_service import chat_service

router = APIRouter(prefix="/chat", tags=["對話"])


class QueryRequest(BaseModel):
    question: str
    category: str = None


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: List[dict]


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """RAG 查詢"""
    async with get_session() as session:
        result = await chat_service.simple_query(
            session=session,
            
            question=request.question,
            category=request.category
        )
        return result
