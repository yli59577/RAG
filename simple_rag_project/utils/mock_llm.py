"""
Mock LLM 服務 - 用於測試，不需要真實的 LLM
"""
from typing import AsyncIterator


class MockLLMService:
    """模擬 LLM 服務"""
    
    def __init__(self):
        self.responses = {
            "你好": "你好！我是一個 AI 助手。很高興認識你！",
            "你是誰": "我是一個簡單的 RAG 系統中的 AI 助手。我可以幫助你回答問題。",
            "你叫什麼名字": "我沒有特定的名字，你可以叫我助手或 AI。",
            "今天天氣": "我無法查詢實時天氣信息，但你可以查看天氣應用或網站。",
            "笑話": "為什麼程序員喜歡用黑色背景？因為光明會傷害他們的眼睛！😄",
            "介紹": "我是一個基於 RAG（檢索增強生成）技術的 AI 助手。我可以根據提供的文檔回答問題，也可以進行一般的對話。",
        }
    
    async def agenerate(self, prompt: str) -> str:
        """非同步生成回答"""
        # 簡單的關鍵詞匹配
        prompt_lower = prompt.lower()
        
        for keyword, response in self.responses.items():
            if keyword in prompt_lower:
                return response
        
        # 默認回答
        return f"我收到了你的問題：'{prompt[:50]}...'。很抱歉，我無法提供具體的回答，但我很樂意幫助你！"
    
    async def astream(self, prompt: str) -> AsyncIterator[str]:
        """串流生成回答"""
        response = await self.agenerate(prompt)
        # 逐字符流式返回
        for char in response:
            yield char
    
    async def rag_query_async(self, question: str, context: str) -> str:
        """RAG 問答（非同步）"""
        # 如果有上下文，使用上下文
        if context and "沒有找到相關資料" not in context:
            # 從上下文中提取信息
            return f"根據提供的文檔資料：\n\n{context[:500]}...\n\n總結：這份文檔主要介紹了網站的基本概念，包括網站的定義、結構、功能等內容。"
        else:
            return await self.agenerate(question)
    
    async def rag_query_stream(self, question: str, context: str) -> AsyncIterator[str]:
        """RAG 問答（串流）"""
        response = await self.rag_query_async(question, context)
        for char in response:
            yield char
    
    async def generate_title(self, content: str) -> str:
        """生成對話標題"""
        # 簡單的標題生成
        words = content.split()[:5]
        title = " ".join(words)
        if len(title) > 20:
            title = title[:20] + "..."
        return title or "新對話"


# 全域實例
mock_llm_service = MockLLMService()
