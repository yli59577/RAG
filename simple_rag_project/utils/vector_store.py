"""向量資料庫操作"""
from typing import List, Dict, Any
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer

from config import settings


class VectorStore:
    """Qdrant 向量資料庫封裝"""
    
    def __init__(self):
        try:
            # 嘗試連接到遠程 Qdrant
            self.client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
            # 測試連接
            self.client.get_collections()
            print(f"✅ 已連接到 Qdrant: {settings.qdrant_host}:{settings.qdrant_port}")
        except Exception as e:
            # 如果連接失敗，使用 In-Memory Qdrant
            print(f"⚠️  無法連接到遠程 Qdrant ({e})，使用 In-Memory 模式")
            self.client = QdrantClient(":memory:")
        
        self.embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        self.vector_size = 384  # all-MiniLM-L6-v2 的向量維度
    
    def ensure_collection(self, collection_name: str):
        """確保 Collection 存在"""
        collections = [c.name for c in self.client.get_collections().collections]
        if collection_name not in collections:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE)
            )
    
    def embed(self, text: str) -> List[float]:
        """文字轉向量"""
        return self.embedder.encode(text).tolist()
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批次文字轉向量"""
        return self.embedder.encode(texts).tolist()
    
    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadata_list: List[Dict[str, Any]] = None
    ) -> int:
        """
        新增文件到向量資料庫
        
        Args:
            collection_name: Collection 名稱
            documents: 文件內容列表
            metadata_list: 每個文件的 metadata
        
        Returns:
            新增的文件數量
        """
        self.ensure_collection(collection_name)
        
        if metadata_list is None:
            metadata_list = [{}] * len(documents)
        
        # 向量化
        vectors = self.embed_batch(documents)
        
        # 建立 Points
        points = [
            PointStruct(
                id=str(uuid4()),
                vector=vector,
                payload={"text": doc, **meta}
            )
            for doc, vector, meta in zip(documents, vectors, metadata_list)
        ]
        
        # 存入 Qdrant
        self.client.upsert(collection_name=collection_name, points=points)
        return len(points)
    
    def search(
        self,
        collection_name: str,
        query: str,
        top_k: int = 5,
        filter_conditions: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        搜尋相關文件
        
        Args:
            collection_name: Collection 名稱
            query: 查詢文字
            top_k: 返回前幾筆結果
            filter_conditions: 過濾條件 {"field": "value"}
        
        Returns:
            相關文件列表
        """
        query_vector = self.embed(query)
        
        # 建立過濾條件
        search_filter = None
        if filter_conditions:
            must_conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filter_conditions.items()
            ]
            search_filter = Filter(must=must_conditions)
        
        # 使用 query_points (qdrant-client >= 1.10)
        results = self.client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=top_k,
            query_filter=search_filter,
            with_payload=True
        )
        
        return [
            {
                "text": hit.payload.get("text", ""),
                "score": hit.score,
                "metadata": {k: v for k, v in hit.payload.items() if k != "text"}
            }
            for hit in results.points
        ]
    
    def delete_by_filename(self, collection_name: str, filename: str):
        """根據檔名刪除文件"""
        self.client.delete(
            collection_name=collection_name,
            points_selector=Filter(
                must=[FieldCondition(key="filename", match=MatchValue(value=filename))]
            )
        )


# 全域實例
vector_store = VectorStore()
