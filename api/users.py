"""
Future REST API endpoints for users.
These will power the web platform and Telegram Mini App.
Implement by injecting the same services used by the bot handlers.
"""
# Example structure (not wired up in MVP):
#
# from fastapi import APIRouter, Depends
# from sqlalchemy.ext.asyncio import AsyncSession
# from services.user_service import UserService
#
# router = APIRouter(prefix="/users", tags=["users"])
#
# @router.get("/{telegram_id}")
# async def get_user(telegram_id: int, session: AsyncSession = Depends(get_session)):
#     svc = UserService(session)
#     return await svc.get_or_raise(telegram_id)
