"""資料庫連線管理"""
import asyncio
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from config import settings
from models import Base

# 建立非同步引擎
engine = create_async_engine(settings.database_url, echo=settings.debug)

# Session 工廠
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@asynccontextmanager
async def get_session():
    """取得資料庫 Session"""
    session = async_session()
    
    try:
        yield session
        await session.commit()

    except Exception:
        await session.rollback()
        raise

    finally:
        await session.close()

async def init_db():
    """初始化資料庫"""
    # 建立所有資料表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("資料表建立完成")


if __name__ == "__main__":
    asyncio.run(init_db())
