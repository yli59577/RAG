"""LLM 服務封裝"""
from typing import AsyncIterator, Literal

from langchain_ollama import ChatOllama
from langchain_openai import AzureChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from config import settings


# RAG Prompt 模板
RAG_PROMPT = """你是一個專業的助手。請根據以下參考資料用繁體中文回答使用者的問題。
必須用繁體中文回答，不要用英文。
如果參考資料中沒有相關資訊，請誠實說明你不知道答案。

=== 參考資料 ===
{context}

=== 使用者問題 ===
{question}

=== 回答（必須用繁體中文）==="""

TITLE_PROMPT = """請根據以下對話內容，生成一個簡短的標題（不超過20個字）。
只需要回覆標題，不要有其他內容。

對話內容：
{content}

標題："""


class LLMService:
    """LLM 服務"""
    
    def __init__(self, llm_type: str = None, model_name: str = None):
        self.llm_type = llm_type or settings.llm_type
        self.model_name = model_name
        self.llm = self._create_llm()
    
    def _create_llm(self):
        """建立 LLM 實例"""
        match self.llm_type:
            case "mock":
                # 返回 None，使用 mock 服務
                return None
            case "ollama":
                return ChatOllama(
                    model=self.model_name or settings.ollama_model,
                    base_url=settings.ollama_url,
                    temperature=0.7
                )
            case "azure":
                return AzureChatOpenAI(
                    azure_endpoint=settings.azure_openai_endpoint,
                    api_key=settings.azure_openai_api_key,
                    azure_deployment=settings.azure_openai_deployment,
                    api_version="2024-05-01-preview"
                )
            case "gemini":
                return ChatGoogleGenerativeAI(
                    model="gemini-1.5-flash",
                    google_api_key=settings.gemini_api_key
                )
            case _:
                raise ValueError(f"不支援的 LLM 類型: {self.llm_type}")
    
    def generate(self, prompt: str) -> str:
        """同步生成回答"""
        response = self.llm.invoke(prompt)
        return response.content
    
    async def agenerate(self, prompt: str) -> str:
        """非同步生成回答"""
        if self.llm_type == "mock":
            from utils.mock_llm import mock_llm_service
            return await mock_llm_service.agenerate(prompt)
        
        response = await self.llm.ainvoke(prompt)
        return response.content
    
    async def astream(self, prompt: str) -> AsyncIterator[str]:
        """串流生成回答"""
        if self.llm_type == "mock":
            from utils.mock_llm import mock_llm_service
            async for chunk in mock_llm_service.astream(prompt):
                yield chunk
        else:
            async for chunk in self.llm.astream(prompt):
                if chunk.content:
                    yield chunk.content
    
    def rag_query(self, question: str, context: str) -> str:
        """RAG 問答（同步）"""
        prompt = RAG_PROMPT.format(context=context, question=question)
        return self.generate(prompt)
    
    async def rag_query_async(self, question: str, context: str) -> str:
        """RAG 問答（非同步）"""
        prompt = RAG_PROMPT.format(context=context, question=question)
        return await self.agenerate(prompt)
    
    async def rag_query_stream(self, question: str, context: str) -> AsyncIterator[str]:
        """RAG 問答（串流）"""
        prompt = RAG_PROMPT.format(context=context, question=question)
        async for chunk in self.astream(prompt):
            yield chunk
    
    async def generate_title(self, content: str) -> str:
        """生成對話標題"""
        if self.llm_type == "mock":
            from utils.mock_llm import mock_llm_service
            return await mock_llm_service.generate_title(content)
        
        prompt = TITLE_PROMPT.format(content=content[:500])
        title = await self.agenerate(prompt)
        return title.strip()[:50]


# 預設 LLM 實例
llm_service = LLMService()
