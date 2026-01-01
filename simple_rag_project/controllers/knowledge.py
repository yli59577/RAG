"""知識庫 API - 文件上傳"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from utils.database import get_session
from services.rag_service import rag_service

router = APIRouter(prefix="/knowledge", tags=["知識庫"])


class UploadResponse(BaseModel):
    success: bool
    message: str
    filename: str


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form(default="default")
):
    """上傳 PDF 文件"""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="只支援 PDF 檔案")
    
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
