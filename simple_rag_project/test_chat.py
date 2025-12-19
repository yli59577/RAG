"""
簡單的聊天測試腳本
"""
import asyncio
import httpx
import json


async def chat(question: str):
    """發送聊天請求"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8000/chat/query",
                json={"question": question},
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()
            return result
        except Exception as e:
            return {"error": str(e)}


async def main():
    """主函數"""
    print("=" * 60)
    print("Simple RAG Chat System - 聊天測試")
    print("=" * 60)
    print("輸入 'quit' 或 'exit' 退出\n")
    
    while True:
        try:
            question = input("你: ").strip()
            
            if not question:
                continue
            
            if question.lower() in ['quit', 'exit']:
                print("再見！")
                break
            
            print("\n助手: 正在思考...", end="", flush=True)
            result = await chat(question)
            print("\r" + " " * 30 + "\r", end="")  # 清除 "正在思考..."
            
            if "error" in result:
                print(f"錯誤: {result['error']}\n")
            else:
                print(f"助手: {result.get('answer', '無回應')}\n")
                
                # 顯示來源（如果有）
                sources = result.get('sources', [])
                if sources:
                    print("📚 參考來源:")
                    for i, source in enumerate(sources, 1):
                        filename = source.get('filename', '未知')
                        page = source.get('page', '?')
                        score = source.get('score', 0)
                        print(f"  {i}. {filename} (第 {page} 頁, 相關度: {score:.2f})")
                    print()
        
        except KeyboardInterrupt:
            print("\n\n再見！")
            break
        except Exception as e:
            print(f"發生錯誤: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())
