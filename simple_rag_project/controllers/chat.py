"""對話 API"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from utils.database import get_session
from services.chat_service import chat_service
from controllers.auth import get_current_user_id

router = APIRouter(prefix="/chat", tags=["對話"])


class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    category: Optional[str] = None
    streaming: bool = False


class QueryResponse(BaseModel):
    session_id: str
    answer: str
    sources: List[dict]


class ChatHistoryItem(BaseModel):
    session_id: str
    title: str
    message_count: int
    updated_at: str


class ChatDetail(BaseModel):
    session_id: str
    title: str
    messages: List[dict]
    created_at: str
    updated_at: str


class RenameRequest(BaseModel):
    new_title: str


class SimpleQueryRequest(BaseModel):
    question: str
    category: Optional[str] = None


@router.post("/query")
async def query(request: SimpleQueryRequest):
    """RAG 問答（不需認證）"""
    import traceback
    try:
        async with get_session() as session:
            result = await chat_service.simple_query(
                session=session,
                question=request.question,
                category=request.category
            )
            return result
    except Exception as e:
        print(f"[ERROR] /chat/query 錯誤: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query/auth")
async def query_with_auth(
    request: QueryRequest,
    user_id: int = Depends(get_current_user_id)
):
    """RAG 問答（需認證，支援歷史記錄）"""
    async with get_session() as session:
        if request.streaming:
            async def generate():
                stream = await chat_service.query(
                    session=session,
                    user_id=user_id,
                    question=request.question,
                    session_id=request.session_id,
                    category=request.category,
                    streaming=True
                )
                async for chunk in stream:
                    yield chunk
            
            return StreamingResponse(generate(), media_type="text/plain")
        else:
            result = await chat_service.query(
                session=session,
                user_id=user_id,
                question=request.question,
                session_id=request.session_id,
                category=request.category,
                streaming=False
            )
            return result


@router.get("/history", response_model=List[ChatHistoryItem])
async def get_history_list(user_id: int = Depends(get_current_user_id)):
    """取得對話歷史列表"""
    async with get_session() as session:
        return await chat_service.get_history_list(session, user_id)


@router.get("/history/{session_id}", response_model=ChatDetail)
async def get_history_detail(
    session_id: str,
    user_id: int = Depends(get_current_user_id)
):
    """取得對話詳情"""
    async with get_session() as session:
        result = await chat_service.get_history_detail(session, user_id, session_id)
        if not result:
            raise HTTPException(status_code=404, detail="對話不存在")
        return result


@router.delete("/history/{session_id}")
async def delete_history(
    session_id: str,
    user_id: int = Depends(get_current_user_id)
):
    """刪除對話歷史"""
    async with get_session() as session:
        await chat_service.delete_history(session, user_id, session_id)
    return {"message": "刪除成功"}


@router.put("/history/{session_id}/rename")
async def rename_history(
    session_id: str,
    request: RenameRequest,
    user_id: int = Depends(get_current_user_id)
):
    """重新命名對話"""
    async with get_session() as session:
        await chat_service.rename_history(session, user_id, session_id, request.new_title)
    return {"message": "重新命名成功"}
