import logging
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from db.session import get_session
from db.models import User, Action, ActionStatus, ActionType
from screens.settings_action import SettingsActionScreen
from screens.ritual_screen import RitualScreen
from states.ritual import Ritual
from text_handlers import text_handler


@text_handler(Ritual.waiting_ritual)
async def handle_ritual_info(message: Message, state: FSMContext):
    try:
        raw = (message.text or "").strip()
        if not raw:
            raise ValueError("Пустая строка.")
        if len(raw) > 600:
            raise ValueError("Слишком длинно. Максимум 600 символов.")

        tg_id = message.from_user.id
        async with get_session() as session:
            user = await User.get_by_tg_id(session, tg_id)
            if not user:
                user = await User.create(
                    session=session,
                    tg_id=tg_id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name,
                    language_code=message.from_user.language_code,
                )

            # создаём Action ritual (без района), статус DRAFT, 
            # текст кладём в .text
            action = await Action.create(
                session,
                owner_id=user.id,
                kind="ritual",
                title="Ritual",
                district_id=None,
                type=ActionType.INDIVIDUAL,
                status=ActionStatus.DRAFT,
                force=0, money=0, influence=0, information=0
            )
            # обновим текст (если нет .text в create)
            await session.refresh(action)
            await session.execute(
                Action.__table__.update()
                .where(Action.id == action.id)
                .values(text=raw)
            )
            await session.commit()

        # показываем экран настройки заявки (там можно выставить расход 
        # информации и нажать Done)
        await SettingsActionScreen().run(
            message=message,
            actor=message.from_user,
            state=state,
            action_id=action.id,
            force_new=True
        )

    except Exception as e:
        logging.exception("Ritual input failed")
        await RitualScreen().run(
            message=message,
            actor=message.from_user,
            state=state,
            error_text=str(e) or "Неизвестная ошибка"
        )
