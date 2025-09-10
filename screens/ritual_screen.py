import logging
from aiogram import types
from aiogram.fsm.context import FSMContext

from screens.base import BaseScreen
from states.ritual import Ritual
from keyboards.presets import communicate_kb
from db.session import get_session
from db.models import User


class RitualScreen(BaseScreen):
    """
    Просит прислать информацию о ритуале.
    Ставит FSM в Ritual.waiting_ritual.
    """
    async def _pre_render(
        self,
        message: types.Message,
        actor: types.User | None = None,
        state: FSMContext | None = None,
        error_text: str | None = None,
        **kwargs
    ):
        tg_user = actor or message.from_user
        tg_id = tg_user.id
        logging.info("RitualScreen for tg_id=%s", tg_id)

        # Load user from database to get current information
        async with get_session() as session:
            db_user = await User.get_by_tg_id(session, tg_id)
            if not db_user:
                db_user = await User.create(
                    session=session,
                    tg_id=tg_id,
                    username=tg_user.username,
                    first_name=tg_user.first_name,
                    last_name=tg_user.last_name,
                    language_code=tg_user.language_code,
                )

        if state:
            await state.set_state(Ritual.waiting_ritual)

        ctx = {
            "title": "🕯️ Начать ритуал",
            "lines": [
                "Пришлите место проведения ритуала вместе с ссылкой на "
                "актуальное положение на гугл-картах одним сообщением.",
                "Эта заявка создаст действие «ritual» (без района).",
                "Текст будет записан и после этого вы попадёте в экран "
                "настройки заявки.",
                f"💡 У вас доступно: {db_user.available_actions} слотов действий",
            ],
            "hint": "Отправьте информацию о ритуале (от 1 до 600 символов):",
            "error_text": error_text,   # опционально показываем ошибку
        }

        return {
            "ritual": ctx,
            "keyboard": communicate_kb()
        }
