"""RAG 服務 - 文件處理與向量化"""
import os
import re
import logging
import uuid
from pathlib import Path
from typing import List, Dict, Any, Tuple

import PyPDF2
import pdfplumber
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_text_splitters import RecursiveCharacterTextSplitter

from models import Document
from utils.vector_store import vector_store
from config import settings

logger = logging.getLogger(__name__)

class RAGService:
    """RAG 服務"""
    
    def __init__(self):
        self.upload_dir = settings.upload_dir
        os.makedirs(self.upload_dir, exist_ok=True)

    @staticmethod
    def extract_text_from_pdf(file_path: str) -> List[str]:
        """從 PDF 擷取文字（按頁分割）"""
        pages = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                with open(file_path, 'rb') as f:
                    pypdf = PyPDF2.PdfReader(f)
                    
                    for page_num, page in enumerate(pdf.pages):
                        text = ""
                        tables = page.extract_tables()
                        if tables and any(tables):
                            text = page.extract_text() or ""
                        else:
                            text = pypdf.pages[page_num].extract_text() or ""
                        
                        text = re.sub(r'\n{3,}', '\n\n', text)
                        pages.append(text.strip())
            
            logger.debug(f"成功從 PDF 提取 {len(pages)} 頁")
            return pages
        
        except Exception as e:
            logger.error(f"PDF 解析失敗: {e}")
            raise

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 100) -> List[str]:
        """將文字分塊"""
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
        """處理上傳的檔案"""
        file_ext = Path(filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(self.upload_dir, unique_filename)
        
        try:
            # 1. 儲存檔案
            with open(file_path, "wb") as f:
                f.write(file_content)
            logger.info(f"檔案已儲存: {unique_filename}")
            
            # 2. 建立資料庫記錄
            doc = Document(
                filename=filename,
                category=category,
                status="processing"
            )
            session.add(doc)
            await session.flush()
            logger.debug(f"資料庫記錄已建立: {doc.id}")
        
            # 3. 擷取文字
            if not filename.lower().endswith(".pdf"):
                return False, "目前只支援 PDF 檔案"
            
            try:
                pages = self.extract_text_from_pdf(file_path)
            
            except Exception as e:
                logger.error(f"PDF 解析失敗: {e}")
                await session.execute(
                    update(Document).where(Document.id == doc.id).values(status="failed")
                )
                await session.commit()
                return False, f"PDF 檔案損壞或無法讀取: {str(e)}"

            if not pages or all(not p for p in pages):
                await session.execute(
                    update(Document).where(Document.id == doc.id).values(status="failed")
                )
                await session.commit()
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
            
            logger.debug(f"生成了 {len(all_chunks)} 個文字區塊")
            
            # 5. 存入向量資料庫
            collection_name = "public"
            try:
                count = vector_store.add_documents(collection_name, all_chunks, all_metadata)
                if count == 0:
                    raise ValueError("向量化失敗：無法添加任何文件")
                logger.info(f"成功添加 {count} 個文字區塊到向量資料庫")
            except Exception as e:
                logger.error(f"向量化失敗: {e}")
                await session.execute(
                    update(Document).where(Document.id == doc.id).values(status="failed")
                )
                await session.commit()
                return False, f"向量化失敗: {str(e)}"
            
            # 6. 更新狀態
            await session.execute(
                update(Document)
                .where(Document.id == doc.id)
                .values(status="completed", chunk_count=count)
            )
            await session.commit()
            logger.info(f"檔案處理完成: {filename} ({count} 個區塊)")
            
            return True, f"成功處理 {count} 個文字區塊"
        
        except Exception as e:
            logger.error(f"處理檔案失敗: {e}")
            try:
                await session.execute(
                    update(Document).where(Document.id == doc.id).values(status="failed")
                )
                await session.commit()
            except:
                pass
            
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.debug(f"已刪除失敗的檔案: {unique_filename}")
                except:
                    pass
            
            return False, f"處理失敗: {str(e)}"
    
    def search(
        self,
        query: str,
        category: str = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """搜尋相關文件"""
        try:
            collection_name = "public"
            
            filter_conditions = {}
            if category:
                filter_conditions["category"] = category
            
            results = vector_store.search(
                collection_name=collection_name,
                query=query,
                top_k=top_k,
                filter_conditions=filter_conditions if filter_conditions else None
            )
            
            logger.debug(f"搜尋完成: 查詢='{query}', 結果數={len(results)}")
            return results
        
        except Exception as e:
            logger.error(f"搜尋失敗: {e}")
            return []


# 全域實例
rag_service = RAGService()
