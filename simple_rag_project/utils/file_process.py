"""檔案處理工具"""
import os
import re
import io
import shutil
import asyncio
import warnings
from typing import Literal, List
from uuid import uuid4

import tiktoken
import PyPDF2
import pdfplumber
from PIL import Image
from qdrant_client import models
from qdrant_client.models import VectorParams, Distance
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import settings
from utils.logging_colors import logger
from utils.vector_store import vector_store


class FileProcess:
    """檔案處理工具類"""
    
    @staticmethod
    async def page_overlap(
        document_list: List[str],
        next_page_fraction: float = 0.5
    ) -> List[str]:
        """
        為每一頁加上下一頁的部分內容作為重疊
        
        Parameters:
            document_list: 每頁全文
            next_page_fraction: 從下一頁開頭取用的比例 (0~1)
        
        Returns:
            加了重疊後的每頁內容
        """
        next_page_fraction = float(next_page_fraction)
        enc = tiktoken.get_encoding("cl100k_base")
        new_docs: List[str] = []

        for i, page_content in enumerate(document_list):
            next_overlap = ""

            if i < len(document_list) - 1:
                next_tokens = enc.encode(document_list[i + 1])
                if len(next_tokens) > 0:
                    next_overlap = enc.decode(next_tokens[:round(len(next_tokens) * next_page_fraction)])

            new_docs.append((page_content + next_overlap).strip())

        return new_docs


    @staticmethod
    async def convert_file_to_text(
        file_path: str,
        convert_method: Literal["PyPDF", "Langchain"] = "PyPDF"
    ) -> List[str]:
        """
        將檔案轉換為文字
        
        Parameters:
            file_path: 檔案路徑
            convert_method: 轉換方法
        
        Returns:
            文字內容列表 (每頁一個元素)
        """
        document_list = []
        
        if convert_method == "PyPDF":
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                with pdfplumber.open(file_path) as pdf:
                    pypdf = PyPDF2.PdfReader(open(file_path, 'rb'))
                    for page_num, page in enumerate(pdf.pages, start=1):
                        text = ""
                        tables_pdfplumber = page.extract_tables()
                        if tables_pdfplumber and any(tables_pdfplumber):
                            text += page.extract_text() + "\n"
                        else:
                            text = pypdf.pages[page_num - 1].extract_text()
                        
                        text = re.sub(r'\n{3,}', '\n\n', text)
                        document_list.append(text)
        
        elif convert_method == "Langchain":
            document_str = ""
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                with pdfplumber.open(file_path) as pdf:
                    pypdf = PyPDF2.PdfReader(open(file_path, 'rb'))
                    for page_num, page in enumerate(pdf.pages, start=1):
                        text = ""
                        tables_pdfplumber = page.extract_tables()
                        if tables_pdfplumber and any(tables_pdfplumber):
                            text += page.extract_text() + "\n"
                        else:
                            text = pypdf.pages[page_num - 1].extract_text()
                        
                        text = re.sub(r'\n{3,}', '\n\n', text)
                        document_str += text
            
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
            document_list = text_splitter.split_text(document_str)
        
        return document_list

    @staticmethod
    def render_pdf_page(file_path: str, page_number: int) -> Image:
        """
        渲染 PDF 頁面為圖片
        
        Parameters:
            file_path: PDF 檔案路徑
            page_number: 頁碼 (從 0 開始)
        
        Returns:
            PIL Image 物件
        """
        pdf = pdfplumber.open(file_path)
        image_container = io.BytesIO()
        pdf.pages[page_number].to_image(resolution=300).save(dest=image_container)
        return Image.open(image_container)

    @staticmethod
    async def process_and_upload_pdf(
        file_path: str,
        filename: str,
        collection_name: str = "documents",
        category: str = "default",
        convert_method: Literal["PyPDF", "Langchain"] = "PyPDF"
    ) -> dict:
        """
        處理 PDF 並上傳到向量資料庫
        
        Parameters:
            file_path: 檔案路徑
            filename: 檔案名稱
            collection_name: Qdrant collection 名稱
            category: 文件分類
            convert_method: 轉換方法
        
        Returns:
            處理結果
        """
        try:
            # 轉換文字
            document_list = await FileProcess.convert_file_to_text(file_path, convert_method)
            
            if not document_list:
                return {"success": False, "message": "無法提取文字", "chunks": 0}
            
            # 加入頁面重疊
            document_list = await FileProcess.page_overlap(document_list)
            
            # 準備 metadata
            metadata_list = []
            for page_num, text in enumerate(document_list):
                if text.strip():
                    metadata_list.append({
                        "filename": filename,
                        "page": page_num + 1,
                        "category": category
                    })
            
            # 過濾空白頁
            documents = [doc for doc in document_list if doc.strip()]
            
            if not documents:
                return {"success": False, "message": "文件內容為空", "chunks": 0}
            
            # 上傳到向量資料庫
            count = vector_store.add_documents(
                collection_name=collection_name,
                documents=documents,
                metadata_list=metadata_list
            )
            
            logger.info(f"檔案 {filename} 處理完成，共 {count} 個區塊")
            return {"success": True, "message": "上傳成功", "chunks": count}
        
        except Exception as e:
            logger.error(f"處理檔案 {filename} 時發生錯誤: {str(e)}")
            return {"success": False, "message": str(e), "chunks": 0}


# 全域實例
file_processor = FileProcess()
