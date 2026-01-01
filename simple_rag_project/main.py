"""
Simple RAG System - FastAPI 入口
基於 sysbrain_bankend 專案架構設計的簡化版 RAG 系統
"""
import uvicorn  # ASGI 伺服器
import json  # JSON 序列化
from contextlib import asynccontextmanager  # 非同步上下文管理器
from fastapi import FastAPI  # FastAPI 框架
from fastapi.middleware.cors import CORSMiddleware  # CORS 中間件

from config import settings  # 應用設定
from utils.database import init_db  # 資料庫初始化
from controllers import knowledge_router, chat_router  # API 路由


class CustomJSONEncoder(json.JSONEncoder):
    def encode(self, o):
        if isinstance(o, str):
            return super().encode(o)
        return super().encode(o)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    # 啟動時初始化資料庫
    print("正在初始化資料庫...")
    await init_db()
    print("資料庫初始化完成！")
    yield
    # 關閉時清理資源
    print("應用程式關閉")


# 建立 FastAPI 應用
app = FastAPI(
    title="Simple RAG System",
    description="一個簡化版的 RAG (Retrieval-Augmented Generation) 系統",
    version="1.0.0",
    lifespan=lifespan,
    json_encoder=CustomJSONEncoder
)

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊路由
app.include_router(knowledge_router)
app.include_router(chat_router)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8001,
        reload=settings.debug
    )
