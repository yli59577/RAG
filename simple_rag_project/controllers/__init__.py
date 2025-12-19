from controllers.auth import router as auth_router
from controllers.knowledge import router as knowledge_router
from controllers.chat import router as chat_router

__all__ = ["auth_router", "knowledge_router", "chat_router"]
