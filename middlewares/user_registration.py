# middlewares/user_registration.py
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Awaitable, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User  # твой класс User
from db.session import get_session  # фабрика сессий


class UserRegistrationMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message | CallbackQuery,
            data: Dict[str, Any]
    ) -> Any:
        user_data = event.from_user
        async with get_session() as session:
            # Проверяем в БД
            db_user = await User.get_by_tg_id(session, user_data.id)
            if not db_user:
                # Create new user with proper action slots initialization
                await User.create(
                    session=session,
                    tg_id=user_data.id,
                    username=user_data.username,
                    first_name=user_data.first_name,
                    last_name=user_data.last_name,
                    language_code=user_data.language_code,
                )
            else:
                # Ensure existing user has proper action slots (safety check)
                db_user.ensure_action_slots_initialized()
                await session.commit()

        return await handler(event, data)
