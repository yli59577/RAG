"""對話服務"""
from typing import List, Dict, Any, AsyncIterator
from uuid import uuid4

from sqlalchemy import select, update, delete
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
        簡單 RAG 問答（不需認證）
        """
        results = []
        context = "（沒有找到相關資料）"
        
        try:
            # 嘗試搜尋相關文件
            print(f"\n[DEBUG] 開始搜尋: question='{question}'")
            results = rag_service.search(
                query=question,
                category=category,
                top_k=5
            )
            
            print(f"[DEBUG] 搜尋結果數量: {len(results)}")
            if results:
                for i, r in enumerate(results):
                    print(f"[DEBUG] 結果 {i}: score={r.get('score'):.4f}, text_len={len(r.get('text', ''))}")
            
            # 組合 Context
            if results:
                context_parts = []
                for i, r in enumerate(results, 1):
                    meta = r.get("metadata", {})
                    source = f"[來源: {meta.get('filename', '未知')}, 頁{meta.get('page', '?')}]"
                    context_parts.append(f"[資料 {i}] {source}\n{r['text']}")
                context = "\n\n".join(context_parts)
                print(f"[DEBUG] 使用 RAG 上下文，長度: {len(context)}")
            else:
                print("[DEBUG] 沒有搜尋到任何結果，使用默認上下文")
        except Exception as e:
            # 如果搜尋失敗（例如 collection 不存在），直接使用 LLM
            print(f"[ERROR] RAG 搜尋失敗: {e}，使用純 LLM 回答")
            import traceback
            traceback.print_exc()
            context = "（沒有找到相關資料）"
        
        # 生成回答
        answer = await llm_service.rag_query_async(question, context)
        
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
    
    async def query(
        self,
        session: AsyncSession,
        user_id: int,
        question: str,
        session_id: str = None,
        category: str = None,
        streaming: bool = False
    ) -> AsyncIterator[str] | Dict[str, Any]:
        """
        RAG 問答
        
        Args:
            session: 資料庫 Session
            user_id: 使用者 ID
            question: 問題
            session_id: 對話 Session ID（新對話則為 None）
            category: 搜尋類別
            streaming: 是否串流回應
        
        Returns:
            串流模式返回 AsyncIterator，否則返回完整回應
        """
        # 1. 搜尋相關文件
        results = rag_service.search(
            query=question,
            user_id=user_id,
            category=category,
            top_k=5
        )
        
        # 2. 組合 Context
        if results:
            context_parts = []
            for i, r in enumerate(results, 1):
                meta = r.get("metadata", {})
                source = f"[來源: {meta.get('filename', '未知')}, 頁{meta.get('page', '?')}]"
                context_parts.append(f"[資料 {i}] {source}\n{r['text']}")
            context = "\n\n".join(context_parts)
        else:
            context = "（沒有找到相關資料）"
        
        # 3. 取得或建立對話歷史
        if session_id:
            result = await session.execute(
                select(ChatHistory).where(
                    ChatHistory.session_id == session_id,
                    ChatHistory.user_id == user_id
                )
            )
            chat_history = result.scalar_one_or_none()
        else:
            session_id = str(uuid4())
            chat_history = None
        
        # 4. 生成回答
        if streaming:
            async def stream_response():
                full_answer = ""
                async for chunk in llm_service.rag_query_stream(question, context):
                    full_answer += chunk
                    yield chunk
                
                # 串流結束後儲存對話
                await self._save_chat(
                    session, user_id, session_id, question, full_answer, chat_history
                )
            
            return stream_response()
        else:
            answer = await llm_service.rag_query_async(question, context)
            
            # 儲存對話
            await self._save_chat(session, user_id, session_id, question, answer, chat_history)
            
            return {
                "session_id": session_id,
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
    
    async def _save_chat(
        self,
        session: AsyncSession,
        user_id: int,
        session_id: str,
        question: str,
        answer: str,
        existing_history: ChatHistory = None
    ):
        """儲存對話歷史"""
        new_messages = [
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer}
        ]
        
        if existing_history:
            # 更新現有對話
            messages = existing_history.messages + new_messages
            await session.execute(
                update(ChatHistory)
                .where(ChatHistory.id == existing_history.id)
                .values(messages=messages)
            )
        else:
            # 建立新對話
            title = await llm_service.generate_title(f"Q: {question}\nA: {answer[:200]}")
            chat = ChatHistory(
                user_id=user_id,
                session_id=session_id,
                title=title,
                messages=new_messages
            )
            session.add(chat)
    
    async def get_history_list(
        self,
        session: AsyncSession,
        user_id: int
    ) -> List[Dict[str, Any]]:
        """取得對話歷史列表"""
        result = await session.execute(
            select(ChatHistory)
            .where(ChatHistory.user_id == user_id)
            .order_by(ChatHistory.updated_at.desc())
        )
        histories = result.scalars().all()
        
        return [
            {
                "session_id": h.session_id,
                "title": h.title,
                "message_count": len(h.messages),
                "updated_at": h.updated_at.isoformat()
            }
            for h in histories
        ]
    
    async def get_history_detail(
        self,
        session: AsyncSession,
        user_id: int,
        session_id: str
    ) -> Dict[str, Any] | None:
        """取得對話詳情"""
        result = await session.execute(
            select(ChatHistory).where(
                ChatHistory.session_id == session_id,
                ChatHistory.user_id == user_id
            )
        )
        history = result.scalar_one_or_none()
        
        if not history:
            return None
        
        return {
            "session_id": history.session_id,
            "title": history.title,
            "messages": history.messages,
            "created_at": history.created_at.isoformat(),
            "updated_at": history.updated_at.isoformat()
        }
    
    async def delete_history(
        self,
        session: AsyncSession,
        user_id: int,
        session_id: str
    ) -> bool:
        """刪除對話歷史"""
        await session.execute(
            delete(ChatHistory).where(
                ChatHistory.session_id == session_id,
                ChatHistory.user_id == user_id
            )
        )
        return True
    
    async def rename_history(
        self,
        session: AsyncSession,
        user_id: int,
        session_id: str,
        new_title: str
    ) -> bool:
        """重新命名對話"""
        await session.execute(
            update(ChatHistory)
            .where(
                ChatHistory.session_id == session_id,
                ChatHistory.user_id == user_id
            )
            .values(title=new_title)
        )
        return True


# 全域實例
chat_service = ChatService()
