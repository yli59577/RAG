"""RAG 服務 - 文件處理與向量化"""
import os
import re
from typing import List, Dict, Any, Tuple

import PyPDF2
import pdfplumber
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_text_splitters import RecursiveCharacterTextSplitter

from models import Document
from utils.vector_store import vector_store
from config import settings


class RAGService:
    """RAG 服務"""
    
    def __init__(self):
        self.upload_dir = settings.upload_dir
        os.makedirs(self.upload_dir, exist_ok=True)
    
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> List[str]:
        """
        從 PDF 擷取文字（按頁分割）
        
        Returns:
            每頁的文字內容列表
        """
        pages = []
        
        with pdfplumber.open(file_path) as pdf:
            pypdf = PyPDF2.PdfReader(open(file_path, 'rb'))
            
            for page_num, page in enumerate(pdf.pages):
                text = ""
                # 嘗試用 pdfplumber 擷取（較好處理表格）
                tables = page.extract_tables()
                if tables and any(tables):
                    text = page.extract_text() or ""
                else:
                    # 用 PyPDF2 擷取
                    text = pypdf.pages[page_num].extract_text() or ""
                
                # 清理多餘換行
                text = re.sub(r'\n{3,}', '\n\n', text)
                pages.append(text.strip())
        
        return pages
    
    @staticmethod
    def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 100) -> List[str]:
        """
        將文字分塊
        
        Args:
            text: 原始文字
            chunk_size: 每塊大小
            chunk_overlap: 重疊大小
        
        Returns:
            分塊後的文字列表
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", ".", " ", ""]
        )
        return splitter.split_text(text)
    
    async def process_file(
        self,
        session: AsyncSession,
        file_content: bytes,
        filename: str,
        category: str = "default",
        user_id: int = None
    ) -> Tuple[bool, str]:
        """
        處理上傳的檔案
        
        Args:
            session: 資料庫 Session
            file_content: 檔案內容
            filename: 檔案名稱
            category: 分類
            user_id: 使用者 ID
        
        Returns:
            (成功與否, 訊息)
        """
        # 1. 儲存檔案
        file_path = os.path.join(self.upload_dir, filename)
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # 2. 建立資料庫記錄
        doc = Document(
            filename=filename,
            category=category,
            user_id=user_id,
            status="processing"
        )
        session.add(doc)
        await session.flush()
        
        try:
            # 3. 擷取文字
            if filename.lower().endswith(".pdf"):
                pages = self.extract_text_from_pdf(file_path)
            else:
                return False, "目前只支援 PDF 檔案"
            
            if not pages or all(not p for p in pages):
                await session.execute(
                    update(Document).where(Document.id == doc.id).values(status="failed")
                )
                return False, "無法擷取文字內容"
            
            # 4. 分塊並向量化
            all_chunks = []
            all_metadata = []
            
            for page_num, page_text in enumerate(pages, 1):
                if not page_text:
                    continue
                
                chunks = self.chunk_text(page_text)
                for chunk in chunks:
                    all_chunks.append(chunk)
                    all_metadata.append({
                        "filename": filename,
                        "page": page_num,
                        "category": category
                    })
            
            # 5. 存入向量資料庫
            collection_name = f"user_{user_id}" if user_id else "public"
            count = vector_store.add_documents(collection_name, all_chunks, all_metadata)
            
            # 6. 更新狀態
            await session.execute(
                update(Document)
                .where(Document.id == doc.id)
                .values(status="completed", chunk_count=count)
            )
            
            return True, f"成功處理 {count} 個文字區塊"
        
        except Exception as e:
            await session.execute(
                update(Document).where(Document.id == doc.id).values(status="failed")
            )
            return False, f"處理失敗: {str(e)}"
    
    async def delete_document(
        self,
        session: AsyncSession,
        filename: str,
        user_id: int = None
    ) -> bool:
        """刪除文件"""
        # 從資料庫刪除
        await session.execute(
            delete(Document).where(
                Document.filename == filename,
                Document.user_id == user_id
            )
        )
        
        # 從向量資料庫刪除
        collection_name = f"user_{user_id}" if user_id else "public"
        vector_store.delete_by_filename(collection_name, filename)
        
        # 刪除檔案
        file_path = os.path.join(self.upload_dir, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        return True
    
    async def list_documents(
        self,
        session: AsyncSession,
        user_id: int = None,
        category: str = None
    ) -> List[Dict[str, Any]]:
        """列出文件"""
        query = select(Document)
        
        if user_id:
            query = query.where(Document.user_id == user_id)
        if category:
            query = query.where(Document.category == category)
        
        result = await session.execute(query.order_by(Document.created_at.desc()))
        docs = result.scalars().all()
        
        return [
            {
                "id": doc.id,
                "filename": doc.filename,
                "category": doc.category,
                "status": doc.status,
                "chunk_count": doc.chunk_count,
                "created_at": doc.created_at.isoformat()
            }
            for doc in docs
        ]
    
    def search(
        self,
        query: str,
        user_id: int = None,
        category: str = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """搜尋相關文件"""
        collection_name = f"user_{user_id}" if user_id else "public"
        
        filter_conditions = {}
        if category:
            filter_conditions["category"] = category
        
        return vector_store.search(
            collection_name=collection_name,
            query=query,
            top_k=top_k,
            filter_conditions=filter_conditions if filter_conditions else None
        )


# 全域實例
rag_service = RAGService()
