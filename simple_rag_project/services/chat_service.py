"""對話服務"""
from typing import Dict, Any
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import ChatHistory
from services.rag_service import rag_service
from utils.llm import llm_service


class ChatService:
    """對話服務"""
    
    async def simple_query(
        self,
        session: AsyncSession,
        question: str,
        category: str = None
    ) -> Dict[str, Any]:
        """
        簡單 RAG 問答
        """
        results = []
        context = "（沒有找到相關資料）"
        
        try:
            results = rag_service.search(
                query=question,
                category=category,
                top_k=5
            ) 
            
            if results:
                context_parts = []
                for i, r in enumerate(results, 1):
                    meta = r.get("metadata", {})
                    source = f"[來源: {meta.get('filename', '未知')}, 頁{meta.get('page', '?')}]"
                    context_parts.append(f"[資料 {i}] {source}\n{r['text']}")
                context = "\n\n".join(context_parts)
        except Exception as e:
            print(f"[ERROR] RAG 搜尋失敗: {e}") 
            context = "（沒有找到相關資料）"
        
        
        # 生成回答
        answer = await llm_service.rag_query_async(question, context)
        
        # 儲存對話歷史
        session_id = str(uuid4())
        chat = ChatHistory(
            session_id=session_id,
            title=question[:50],
            messages=[
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer}
            ]
        )
        session.add(chat)
        await session.commit()
        
        return {
            "question": question,
            "answer": answer,
            "sources": [
                {
                    "filename": r.get("metadata", {}).get("filename"),
                    "page": r.get("metadata", {}).get("page"),
                    "score": r.get("score")
                }
                for r in results
            ]
        }
  

# 全域實例
chat_service = ChatService()
