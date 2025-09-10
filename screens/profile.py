import logging
from aiogram import types
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from db.session import get_session
from db.models import User, District, now_utc
from datetime import datetime, timezone, timedelta
from keyboards.spec import KeyboardParams, KeyboardSpec
from .base import BaseScreen
from keyboards.presets import main_menu_kb


def ideology_bar(value: int, size: int = 11) -> str:
    """Рисуем шкалу ▪/⬛️ по -size..+size. Здесь просто 0..size c зелёной точкой."""
    filled = max(0, min(size, value + 5))
    return "▪" * filled + "💠" + "▪" * (size - filled - 1)


class ProfileScreen(BaseScreen):
    def _calculate_next_refresh_minutes(self, actions_refresh_at):
        """Calculate minutes until next action refresh"""
        if actions_refresh_at is None:
            # If no refresh time set, assume next refresh is in 3 hours (game cycle length)
            return 180
        
        now = now_utc()
        
        # If the last refresh was recent (within last 3 hours), calculate time until next 3-hour cycle
        time_since_refresh = now - actions_refresh_at
        if time_since_refresh < timedelta(hours=3):
            # Next refresh is 3 hours after the last refresh
            next_refresh = actions_refresh_at + timedelta(hours=3)
            minutes_until_next = int((next_refresh - now).total_seconds() / 60)
            return max(0, minutes_until_next)
        else:
            # If it's been more than 3 hours, actions should be refreshed already
            return 0

    async def _pre_render(self, message: types.Message, actor: types.User | None = None, **kwargs):
        tg_id = actor.id if actor else (message.from_user.id if message else None)
        logging.info("StatusScreen for tg_id=%s", tg_id)

        async with get_session() as session:
            user = await User.get_by_tg_id(session, tg_id)
            if user is None:
                # на всякий: создадим, чтобы экран всегда работал
                user = await User.create(
                    session=session,
                    tg_id=tg_id,
                    username=(actor or message.from_user).username,
                    first_name=(actor or message.from_user).first_name,
                    last_name=(actor or message.from_user).last_name,
                    language_code=(actor or message.from_user).language_code,
                )

            # Load actual districts owned by user with their details
            owned_districts = (await session.execute(
                select(District).where(District.owner_id == user.id).order_by(District.name)
            )).scalars().all()
            
            districts_count = len(owned_districts)

        # --- Статистика действий ---
        pending_count = sum(1 for a in user.actions if a.status == "pending")
        done_count = sum(1 for a in user.actions if a.status == "done")
        failed_count = sum(1 for a in user.actions if a.status == "failed")

        # --- Последние действия (по created_at, максимум 5) ---
        recent_actions = [
            f"({a.status})"
            for a in sorted(user.actions, key=lambda x: x.created_at, reverse=True)[:5]
        ]

        # --- Calculate total district bonuses ---
        total_district_bonuses = {
            "money": sum(d.base_money or 0 for d in owned_districts),
            "influence": sum(d.base_influence or 0 for d in owned_districts),
            "information": sum(d.base_information or 0 for d in owned_districts),
            "force": sum(d.base_force or 0 for d in owned_districts),
        }

        # --- Prepare district information ---
        district_info = []
        for district in owned_districts:
            bonuses = []
            if district.base_money: bonuses.append(f"+{district.base_money} 💰")
            if district.base_influence: bonuses.append(f"+{district.base_influence} 🪙")
            if district.base_information: bonuses.append(f"+{district.base_information} 🧠")
            if district.base_force: bonuses.append(f"+{district.base_force} 💪")
            
            district_info.append({
                "name": district.name,
                "bonuses": ", ".join(bonuses) if bonuses else "нет бонусов"
            })

        profile = {
            "name": user.in_game_name or user.username or str(user.tg_id),
            "faction": user.faction,
            "ideology_value": user.ideology,
            "ideology_label": user.ideology,
            "ideology_bar": ideology_bar(user.ideology, size=11),
            "resources": {
                "force": user.force,
                "money": user.money,
                "influence": user.influence,
                "information": user.information,
            },
            "applications": {
                "available": user.available_actions,
                "max_available": user.max_available_actions,
                "next_update_minutes": self._calculate_next_refresh_minutes(user.actions_refresh_at),
                "fast_actions": kwargs.get("fast_actions_left", 3),
            },
            "districts": {
                "count": districts_count,
                "has_any": districts_count > 0,
                "list": district_info,
                "total_bonuses": total_district_bonuses,
            },
            "actions_stats": {
                "pending": pending_count,
                "done": done_count,
                "failed": failed_count,
            },
            "recent_actions": recent_actions,
        }

        return {
            "profile": profile,
            "keyboard": KeyboardSpec(
                            type="inline",
                            name="profile_menu",
                            options=["back"],
                            params=KeyboardParams(max_in_row=2),
                        ),
        }
