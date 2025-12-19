"""SQLAlchemy Base Model"""
from sqlalchemy import Column, Integer
from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    """所有模型的基礎類別"""
    
    @declared_attr.directive
    @classmethod
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
    
    id = Column(Integer, primary_key=True, autoincrement=True)
