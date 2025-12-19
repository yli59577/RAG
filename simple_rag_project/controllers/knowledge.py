"""知識庫 API"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from pydantic import BaseModel

from utils.database import get_session
from services.rag_service import rag_service
from controllers.auth import get_current_user_id

router = APIRouter(prefix="/knowledge", tags=["知識庫"])


class DocumentResponse(BaseModel):
    id: int
    filename: str
    category: str
    status: str
    chunk_count: int
    created_at: str


class UploadResponse(BaseModel):
    success: bool
    message: str
    filename: Optional[str] = None


class SearchResult(BaseModel):
    text: str
    score: float
    filename: Optional[str] = None
    page: Optional[int] = None


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form(default="default")
):
    """上傳文件（不需認證）"""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="目前只支援 PDF 檔案")
    
    content = await file.read()
    
    async with get_session() as session:
        success, message = await rag_service.process_file(
            session=session,
            file_content=content,
            filename=file.filename,
            category=category,
            user_id=None
        )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return UploadResponse(success=True, message=message, filename=file.filename)


@router.delete("/delete/{filename}")
async def delete_document(
    filename: str,
    user_id: int = Depends(get_current_user_id)
):
    """刪除文件"""
    async with get_session() as session:
        await rag_service.delete_document(session, filename, user_id)
    return {"message": "刪除成功"}


@router.get("/list", response_model=List[DocumentResponse])
async def list_documents(
    category: Optional[str] = None,
    user_id: int = Depends(get_current_user_id)
):
    """列出文件"""
    async with get_session() as session:
        docs = await rag_service.list_documents(session, user_id, category)
    return docs


@router.get("/search", response_model=List[SearchResult])
async def search_documents(
    query: str,
    category: Optional[str] = None,
    top_k: int = 5
):
    """搜尋文件（不需認證）"""
    results = rag_service.search(
        query=query,
        category=category,
        top_k=top_k
    )
    
    return [
        SearchResult(
            text=r["text"],
            score=r["score"],
            filename=r.get("metadata", {}).get("filename"),
            page=r.get("metadata", {}).get("page")
        )
        for r in results
    ]
