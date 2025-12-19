"""資料庫連線管理"""
import asyncio
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.sql import text

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
    # SQLite 會自動建立資料庫檔案，PostgreSQL 需要手動建立
    if "postgresql" in settings.database_url:
        db_name = settings.database_url.split("/")[-1]
        base_url = settings.database_url.rsplit("/", 1)[0]
        
        temp_engine = create_async_engine(f"{base_url}/postgres", isolation_level="AUTOCOMMIT")
        async with temp_engine.connect() as conn:
            result = await conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'"))
            if not result.scalar():
                await conn.execute(text(f"CREATE DATABASE {db_name}"))
                print(f"資料庫 '{db_name}' 建立成功")
        await temp_engine.dispose()
    
    # 建立所有資料表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("資料表建立完成")


if __name__ == "__main__":
    asyncio.run(init_db())
