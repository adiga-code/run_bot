"""
Future REST API endpoints for workouts and session logs.
These will power the web platform and Telegram Mini App.
"""
# Example structure (not wired up in MVP):
#
# from fastapi import APIRouter, Depends
# from sqlalchemy.ext.asyncio import AsyncSession
# from services.workout_service import WorkoutService
# from services.session_log_service import SessionLogService
#
# router = APIRouter(prefix="/workouts", tags=["workouts"])
#
# @router.get("/{level}/{day}/{version}")
# async def get_workout(level: int, day: int, version: str, session: AsyncSession = Depends(get_session)):
#     svc = WorkoutService(session)
#     return await svc.get(level, day, version)
