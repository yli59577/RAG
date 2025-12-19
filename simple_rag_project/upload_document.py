"""
上傳文檔到 RAG 系統
"""
import asyncio
import httpx
from pathlib import Path


async def upload_document(file_path: str, category: str = "default"):
    """上傳文檔"""
    file_path = Path(file_path)
    
    if not file_path.exists():
        print(f"❌ 文件不存在: {file_path}")
        return
    
    if not file_path.suffix.lower() == ".pdf":
        print("❌ 目前只支持 PDF 文件")
        return
    
    print(f"📤 正在上傳: {file_path.name}")
    
    async with httpx.AsyncClient() as client:
        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f, "application/pdf")}
                data = {"category": category}
                
                response = await client.post(
                    "http://localhost:8000/knowledge/upload",
                    files=files,
                    data=data,
                    timeout=300.0
                )
            
            response.raise_for_status()
            result = response.json()
            
            print(f"✅ 上傳成功！")
            print(f"   文件名: {result.get('filename')}")
            print(f"   分類: {result.get('category')}")
            print(f"   狀態: {result.get('status')}")
            print(f"   消息: {result.get('message')}")
            
        except Exception as e:
            print(f"❌ 上傳失敗: {e}")


async def main():
    """主函數"""
    print("=" * 60)
    print("RAG 系統 - 文檔上傳工具")
    print("=" * 60)
    
    # 上傳你的企劃書
    pdf_path = "./.tmp/uploads/第一組＿企劃書.pdf"
    
    if Path(pdf_path).exists():
        await upload_document(pdf_path, category="企劃書")
    else:
        print(f"❌ 找不到文件: {pdf_path}")
        print("\n請提供 PDF 文件路徑:")
        file_path = input("文件路徑: ").strip()
        if file_path:
            await upload_document(file_path)


if __name__ == "__main__":
    asyncio.run(main())
