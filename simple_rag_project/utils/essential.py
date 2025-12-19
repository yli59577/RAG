"""核心工具函數"""
import os
import re
import json
import asyncio
import aiofiles
from typing import Literal, Tuple
from datetime import datetime, timedelta

from config import settings
from utils.logging_colors import logger


class Essential:
    """核心工具類"""
    
    # RAG 文件前綴模板
    rag_document_prefix = "**********\n[段落資訊]\n檔案名稱: {}\n頁碼: {}\n**********\n\n"
    
    # RAG 日誌前綴模板
    rag_logger_prefix = """
-----------------------------------
[Index]: {}
[Top-K]: {}
[Question]: {}
[filename]: {}, Page-Number: {}
[Result]: {}
-----------------------------------
"""

    @staticmethod
    async def try_lock(lock_path: str) -> bool:
        """嘗試建立 lock file"""
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return True
        except FileExistsError:
            return False
    
    @staticmethod
    async def release_lock(lock_path: str):
        """釋放鎖"""
        try:
            os.remove(lock_path)
        except FileNotFoundError:
            pass
    
    @staticmethod
    async def read_json_config(config_path: str) -> dict:
        """讀取 JSON 設定檔"""
        lock_path = f".{config_path}.lock"
        data = None
        
        while data is None:
            got_lock = await Essential.try_lock(lock_path)
            if not got_lock:
                await asyncio.sleep(0.1)
                continue
            
            try:
                async with aiofiles.open(config_path, "r", encoding="utf-8") as f:
                    content = await f.read()
                    data = json.loads(content)
            except Exception:
                pass
            finally:
                await Essential.release_lock(lock_path)
        
        return data
    
    @staticmethod
    async def write_json_config(config_path: str, data: dict) -> bool:
        """寫入 JSON 設定檔"""
        lock_path = f".{config_path}.lock"
        
        got_lock = await Essential.try_lock(lock_path)
        if not got_lock:
            return False
        
        try:
            async with aiofiles.open(config_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(data, indent=4, ensure_ascii=False))
            return True
        except Exception:
            return False
        finally:
            await Essential.release_lock(lock_path)

    @staticmethod
    def format_rag_context(results: list, max_length: int = 4000) -> str:
        """
        格式化 RAG 搜尋結果為上下文字串
        
        Parameters:
            results: 搜尋結果列表
            max_length: 最大長度限制
        
        Returns:
            格式化後的上下文字串
        """
        context_parts = []
        total_length = 0
        
        for i, result in enumerate(results):
            text = result.get("text", "")
            metadata = result.get("metadata", {})
            filename = metadata.get("filename", "未知")
            page = metadata.get("page", "未知")
            
            prefix = Essential.rag_document_prefix.format(filename, page)
            chunk = prefix + text
            
            if total_length + len(chunk) > max_length:
                break
            
            context_parts.append(chunk)
            total_length += len(chunk)
        
        return "\n\n".join(context_parts)

    @staticmethod
    def detect_forbidden_words(text: str, forbidden_list: list) -> str | None:
        """
        檢測禁詞
        
        Parameters:
            text: 要檢測的文字
            forbidden_list: 禁詞列表
        
        Returns:
            命中的禁詞，若無則回傳 None
        """
        if not forbidden_list:
            return None
        
        regex = re.compile("|".join(word.strip() for word in forbidden_list if word.strip()), re.I)
        matches = regex.search(text)
        
        return matches.group(0) if matches else None
