# Simple RAG System

一個簡化版的 RAG (Retrieval-Augmented Generation) 系統，基於 sysbrain_bankend 專案架構設計。

## 功能特色

- 📄 文件上傳與向量化
- 🔍 語義搜尋
- 🤖 多 LLM 支援 (Ollama/Azure/Gemini)
- 💬 對話歷史管理
- 🔐 使用者認證

## 技術架構

```
simple_rag_project/
├── main.py              # FastAPI 入口
├── config.py            # 環境設定
├── models/              # 資料庫模型
│   ├── __init__.py
│   ├── base.py
│   └── models.py
├── controllers/         # API 路由
│   ├── __init__.py
│   ├── auth.py
│   ├── chat.py
│   └── knowledge.py
├── services/            # 業務邏輯
│   ├── __init__.py
│   ├── auth_service.py
│   ├── chat_service.py
│   └── rag_service.py
├── utils/               # 工具函數
│   ├── __init__.py
│   ├── database.py
│   ├── llm.py
│   └── vector_store.py
├── .env.example
└── requirements.txt
```

## 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 設定環境變數

```bash
cp .env.example .env
# 編輯 .env 填入你的設定
```

### 3. 啟動服務

需要先啟動 PostgreSQL、Redis、Qdrant：

```bash
# 使用 Docker
docker run -d --name postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:15-alpine
docker run -d --name redis -p 6379:6379 redis:7-alpine
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant
```

### 4. 執行程式

```bash
python main.py
```

訪問 http://localhost:8000/docs 查看 API 文件

## API 端點

### 認證
- `POST /auth/login` - 登入
- `POST /auth/logout` - 登出

### 知識庫
- `POST /knowledge/upload` - 上傳文件
- `DELETE /knowledge/delete` - 刪除文件
- `GET /knowledge/list` - 列出文件

### 對話
- `POST /chat/query` - RAG 問答
- `GET /chat/history` - 取得對話歷史
- `DELETE /chat/history/{id}` - 刪除對話

## 核心流程

1. **文件上傳**: 上傳 PDF → 文字擷取 → 分塊 → 向量化 → 存入 Qdrant
2. **RAG 問答**: 使用者提問 → 向量搜尋 → 取得相關文件 → 組合 Prompt → LLM 生成回答
