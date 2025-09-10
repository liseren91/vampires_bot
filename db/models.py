# db/models.py
from __future__ import annotations

from datetime import datetime, timezone
from math import ceil
from typing import Optional, Sequence, List
from sqlalchemy import Boolean, Table, Column

from sqlalchemy import (
    BigInteger,
    String,
    DateTime,
    ForeignKey,
    select,
    update,
    delete,
    func,
    Index, Enum, Integer, CheckConstraint, Float, UniqueConstraint, JSON, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session import Base
from enum import Enum as PyEnum


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ===========================
#   Assoc: User <-> District (scouting)
# ===========================
user_scouts_districts = Table(
    "user_scouts_districts",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("district_id", ForeignKey("districts.id", ondelete="CASCADE"), primary_key=True),
    Index("ix_user_scouts_user_district", "user_id", "district_id", unique=True),
)


# ===========================
#           User
# ===========================
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)

    username: Mapped[Optional[str]] = mapped_column(String(255))
    first_name: Mapped[Optional[str]] = mapped_column(String(255))
    last_name: Mapped[Optional[str]] = mapped_column(String(255))

    in_game_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    language_code: Mapped[Optional[str]] = mapped_column(String(16))

    money: Mapped[int] = mapped_column(default=2, nullable=False)
    influence: Mapped[int] = mapped_column(default=2, nullable=False)
    information: Mapped[int] = mapped_column(default=2, nullable=False)
    force: Mapped[int] = mapped_column(default=1, nullable=False)

    base_money: Mapped[int] = mapped_column(default=2, nullable=False)
    base_influence: Mapped[int] = mapped_column(default=2, nullable=False)
    base_information: Mapped[int] = mapped_column(default=2, nullable=False)
    base_force: Mapped[int] = mapped_column(default=1, nullable=False)

    # НОВОЕ
    ideology: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # -5..+5
    faction: Mapped[Optional[str]] = mapped_column(String(64))  # простой текст
    available_actions: Mapped[int] = mapped_column(Integer, default=5, nullable=False)  # сколько слотов
    max_available_actions: Mapped[int] = mapped_column(Integer, default=5, nullable=True)  # сколько слотов
    actions_refresh_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Один-ко-многим: User -> District
    districts: Mapped[List["District"]] = relationship(
        "District",
        back_populates="owner",
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,  # работает полноценно на Postgres (FK ON DELETE CASCADE)
    )
    scouts_districts: Mapped[List["District"]] = relationship(
        "District",
        secondary=user_scouts_districts,
        back_populates="scouting_by",
        lazy="selectin",
    )

    actions: Mapped[List["Action"]] = relationship(
        "Action", back_populates="owner", lazy="selectin",
        cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        CheckConstraint("ideology >= -5 AND ideology <= 5", name="ck_users_ideology_range"),
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_utc,
        onupdate=now_utc,
        nullable=False,
    )

    # ===== CRUD =====
    @classmethod
    async def create(
            cls,
            session,
            tg_id: int,
            username: Optional[str] = None,
            first_name: Optional[str] = None,
            last_name: Optional[str] = None,
            language_code: Optional[str] = None,
            **extra,
    ) -> "User":
        # Set default starting resources based on game_models_template CSV
        user = cls(
            tg_id=tg_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
            # Starting resources (can be overridden via extra)
            money=extra.get('money', 2),
            influence=extra.get('influence', 2),
            information=extra.get('information', 2),
            force=extra.get('force', 1),
            base_money=extra.get('base_money', 2),
            base_influence=extra.get('base_influence', 2),
            base_information=extra.get('base_information', 2),
            base_force=extra.get('base_force', 1),
            available_actions=extra.get('available_actions', 5),
            max_available_actions=extra.get('max_available_actions', 5),
            actions_refresh_at=extra.get('actions_refresh_at', now_utc()),
            **{k: v for k, v in extra.items() if k not in [
                'money', 'influence', 'information', 'force',
                'base_money', 'base_influence', 'base_information', 'base_force',
                'available_actions', 'max_available_actions', 'actions_refresh_at'
            ]},
        )
        session.add(user)
        # Ensure action slots are properly initialized
        user.ensure_action_slots_initialized()
        
        await session.commit()
        await session.refresh(user)
        return user
    
    def ensure_action_slots_initialized(self):
        """Ensure user has proper action slots initialized"""
        # Fix max_available_actions if not set
        if self.max_available_actions is None or self.max_available_actions <= 0:
            self.max_available_actions = 5
        
        # Fix available_actions if not set or less than expected for new user
        if self.available_actions is None or self.available_actions <= 0:
            self.available_actions = self.max_available_actions
        
        # Set actions_refresh_at if not set
        if self.actions_refresh_at is None:
            self.actions_refresh_at = now_utc()

    @classmethod
    async def get_by_tg_id(cls, session, tg_id: int) -> Optional["User"]:
        res = await session.execute(select(cls).where(cls.tg_id == tg_id))
        return res.scalars().first()

    @classmethod
    async def get_all(cls, session) -> Sequence["User"]:
        res = await session.execute(select(cls))
        return res.scalars().all()

    @classmethod
    async def update_by_tg_id(cls, session, tg_id: int, **kwargs) -> bool:
        kwargs["updated_at"] = now_utc()
        res = await session.execute(
            update(cls)
            .where(cls.tg_id == tg_id)
            .values(**kwargs)
            .execution_options(synchronize_session="fetch")
        )
        await session.commit()
        return (res.rowcount or 0) > 0

    @classmethod
    async def delete_by_tg_id(cls, session, tg_id: int) -> bool:
        res = await session.execute(delete(cls).where(cls.tg_id == tg_id))
        await session.commit()
        return (res.rowcount or 0) > 0

    # ===== Helpers =====
    @classmethod
    async def get_or_create(cls, session, tg_id: int, **defaults) -> "User":
        user = await cls.get_by_tg_id(session, tg_id)
        if user:
            return user
        return await cls.create(session, tg_id=tg_id, **defaults)

    @classmethod
    async def count_districts(cls, session, user_id: int) -> int:
        res = await session.execute(select(func.count(District.id)).where(District.owner_id == user_id))
        return int(res.scalar() or 0)


# Индекс на username для быстрых фильтров (опционально)
Index("ix_users_username", User.username)


# ===========================
#         Districts
# ===========================


class ControlLevel(PyEnum):
    NONE = "NONE"
    MINIMAL = "MINIMAL"
    PARTIAL = "PARTIAL"
    SIGNIFICANT = "SIGNIFICANT"
    FULL = "FULL"


class District(Base):
    __tablename__ = "districts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Название района
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Владелец (может быть NULL для нейтральных районов)
    owner_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=True
    )
    owner: Mapped[Optional["User"]] = relationship(
        "User", back_populates="districts", lazy="selectin"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, nullable=False
    )

    # ==== Новые поля из UI ====

    # Очки контроля (Your Control: 0 points)
    control_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Уровень контроля (Level: ControlLevel.MINIMAL)
    control_level: Mapped[ControlLevel] = mapped_column(
        Enum(ControlLevel, name="control_level_enum"),
        default=ControlLevel.MINIMAL,
        nullable=False,
    )

    # Множитель ресурсов (Resource Multiplier: 40.0% => 0.4)
    resource_multiplier: Mapped[float] = mapped_column(
        Float, default=0.40, nullable=False
    )
    scouting_by: Mapped[List["User"]] = relationship(
        "User",
        secondary=user_scouts_districts,
        back_populates="scouts_districts",
        lazy="selectin",
    )

    # Базовые ресурсы (Base Resources)
    base_money: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    base_influence: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    base_information: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    base_force: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        # Один и тот же владелец не может иметь два района с одинаковым именем (если владелец есть)
        # Но нейтральные районы (owner_id=NULL) могут иметь одинаковые имена
        Index("ix_district_owner_name", "owner_id", "name"),
    )

    # ===== CRUD =====
    @classmethod
    async def create(
            cls,
            session,
            name: str,
            owner_id: Optional[int] = None,
            *,
            control_points: int = 0,
            control_level: ControlLevel = ControlLevel.MINIMAL,
            resource_multiplier: float = 0.40,
            base_money: int = 100,
            base_influence: int = 10,
            base_information: int = 5,
            base_force: int = 0,
    ) -> "District":
        obj = cls(
            name=name,
            owner_id=owner_id,
            control_points=control_points,
            control_level=control_level,
            resource_multiplier=resource_multiplier,
            base_money=base_money,
            base_influence=base_influence,
            base_information=base_information,
            base_force=base_force,
        )
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj

    @classmethod
    async def get_by_id(cls, session, district_id: int) -> "District | None":
        res = await session.execute(select(cls).where(cls.id == district_id))
        return res.scalars().first()

    @classmethod
    async def get_by_owner(cls, session, owner_id: Optional[int]):
        if owner_id is None:
            res = await session.execute(
                select(cls).where(cls.owner_id.is_(None)).order_by(cls.id)
            )
        else:
            res = await session.execute(
                select(cls).where(cls.owner_id == owner_id).order_by(cls.id)
            )
        return res.scalars().all()

    @classmethod
    async def rename(cls, session, district_id: int, new_name: str) -> "District | None":
        obj = await cls.get_by_id(session, district_id)
        if not obj:
            return None
        obj.name = new_name
        await session.commit()
        await session.refresh(obj)
        return obj

    @classmethod
    async def reassign_owner(cls, session, district_id: int, new_owner_id: int) -> "District | None":
        obj = await cls.get_by_id(session, district_id)
        if not obj:
            return None
        obj.owner_id = new_owner_id
        await session.commit()
        await session.refresh(obj)
        return obj

    @classmethod
    async def update_control(
            cls,
            session,
            district_id: int,
            *,
            control_points: int | None = None,
            control_level: ControlLevel | None = None,
            resource_multiplier: float | None = None,
    ) -> "District | None":
        obj = await cls.get_by_id(session, district_id)
        if not obj:
            return None
        if control_points is not None:
            obj.control_points = control_points
        if control_level is not None:
            obj.control_level = control_level
        if resource_multiplier is not None:
            obj.resource_multiplier = resource_multiplier
        await session.commit()
        await session.refresh(obj)
        return obj

    @classmethod
    async def set_base_resources(
            cls,
            session,
            district_id: int,
            *,
            money: int | None = None,
            influence: int | None = None,
            information: int | None = None,
            force: int | None = None,
    ) -> "District | None":
        obj = await cls.get_by_id(session, district_id)
        if not obj:
            return None
        if money is not None:
            obj.base_money = money
        if influence is not None:
            obj.base_influence = influence
        if information is not None:
            obj.base_information = information
        if force is not None:
            obj.base_force = force
        await session.commit()
        await session.refresh(obj)
        return obj

    @classmethod
    async def delete(cls, session, district_id: int) -> bool:
        res = await session.execute(delete(cls).where(cls.id == district_id))
        await session.commit()
        return (res.rowcount or 0) > 0

    # ===== Вспомогательное =====
    def effective_resources(self) -> dict[str, int]:
        """Рассчитать ресурсы с учётом мультипликатора."""
        mul = float(self.resource_multiplier)
        return {
            "money": ceil(self.base_money * mul),
            "influence": ceil(self.base_influence * mul),
            "information": ceil(self.base_information * mul),
            "force": ceil(self.base_force * mul),
        }


# ===========================
#         Action
# ===========================

class ActionType(PyEnum):
    INDIVIDUAL = "individual"
    SUPPORT = "support"
    COLLECTIVE = "collective"

    SCOUT_DISTRICT = "scout_dist"
    SCOUT_INFO = "scout_info"

    RITUAL = "ritual"


class ActionStatus(PyEnum):
    DRAFT = "draft"
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"
    DELETED = "deleted"


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[ActionStatus] = mapped_column(
        Enum(ActionStatus, name="action_status_enum"),
        default=ActionStatus.DRAFT,
        nullable=False,
    )

    # Владелец
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    owner: Mapped["User"] = relationship("User", back_populates="actions", lazy="selectin")

    # (NEW) Необязательный район
    district_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("districts.id", ondelete="SET NULL"),
        index=True,
        nullable=True
    )
    district: Mapped[Optional["District"]] = relationship("District", lazy="selectin")

    # (NEW) Тип экшена
    type: Mapped[ActionType] = mapped_column(
        Enum(ActionType, name="action_type_enum"),
        default=ActionType.INDIVIDUAL,
        nullable=False
    )

    # (NEW) Self-FK для поддержки
    parent_action_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("actions.id", ondelete="CASCADE"),
        index=True,
        nullable=True
    )
    parent_action: Mapped[Optional["Action"]] = relationship(
        "Action",
        remote_side="Action.id",
        back_populates="support_actions",
        lazy="selectin"
    )
    support_actions: Mapped[List["Action"]] = relationship(
        "Action",
        back_populates="parent_action",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    # (NEW) Ресурсы
    force: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    money: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    influence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    information: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    candles: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Ideology direction for influence: 1 for + (reforms), -1 for - (conservative), 0 for no direction
    ideology_direction: Mapped[int] = mapped_column(Integer, default=0, nullable=False, server_default="0")

    estimated_power: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    on_point: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    won_on_point: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # For rituals: when the ritual should automatically complete
    ritual_end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_utc,
        onupdate=now_utc,
        nullable=False
    )

    text: Mapped[Optional[str]] = mapped_column(String(600), nullable=True)

    # простые CRUD
    @classmethod
    async def create(
            cls,
            session,
            *,
            owner_id: int,
            kind: str,
            title: Optional[str] = None,
            district_id: Optional[int] = None,
            type: ActionType = ActionType.INDIVIDUAL,
            parent_action_id: Optional[int] = None,
            status: ActionStatus = ActionStatus.PENDING,
            force: int = 0,
            money: int = 0,
            influence: int = 0,
            information: int = 0,
            ideology_direction: int = 0
    ) -> "Action":
        obj = cls(
            owner_id=owner_id,
            kind=kind,
            title=title,
            district_id=district_id,
            type=type,
            parent_action_id=parent_action_id,
            status=status,
            force=force,
            money=money,
            influence=influence,
            information=information,
            ideology_direction=ideology_direction
        )
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj

    @classmethod
    async def get_by_id(cls, session, action_id: int) -> Optional["Action"]:
        res = await session.execute(select(cls).where(cls.id == action_id))
        return res.scalars().first()

    @classmethod
    async def by_owner(cls, session, owner_id: int) -> Sequence["Action"]:
        res = await session.execute(select(cls).where(cls.owner_id == owner_id).order_by(cls.id.desc()))
        return res.scalars().all()

    @classmethod
    async def set_status(cls, session, action_id: int, status: ActionStatus) -> bool:
        res = await session.execute(
            update(cls).where(cls.id == action_id).values(status=status, updated_at=now_utc())
        )
        await session.commit()
        return (res.rowcount or 0) > 0

    @classmethod
    async def delete(cls, session, action_id: int) -> bool:
        res = await session.execute(delete(cls).where(cls.id == action_id))
        await session.commit()
        return (res.rowcount or 0) > 0


class News(Base):
    __tablename__ = "news"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # 1) Заголовок
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    # 2) Текст новости (можно длинный)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    # 3) Медиафайлы как список ссылок (может быть пустым)
    #    Для SQLite JSON хранится как TEXT, для Postgres — как native JSONB.
    media_urls: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    # 4) Привязка к действию (опционально)
    action_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("actions.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    action: Mapped[Optional["Action"]] = relationship(
        "Action", lazy="selectin"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_utc,
        onupdate=now_utc,
        nullable=False,
    )

    __table_args__ = (
        Index("ix_news_action_created", "action_id", "created_at"),
    )

    # ===== CRUD / helpers =====
    @classmethod
    async def create(
            cls,
            session,
            *,
            title: str,
            body: str,
            media_urls: Optional[list[str]] = None,
            action_id: Optional[int] = None,
    ) -> "News":
        obj = cls(
            title=title,
            body=body,
            media_urls=media_urls or [],
            action_id=action_id,
        )
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj

    @classmethod
    async def get_by_id(cls, session, news_id: int) -> Optional["News"]:
        res = await session.execute(select(cls).where(cls.id == news_id))
        return res.scalars().first()

    @classmethod
    async def latest(
            cls,
            session,
            *,
            limit: int = 20,
            action_id: Optional[int] = None,
    ) -> list["News"]:
        stmt = select(cls).order_by(cls.created_at.desc()).limit(limit)
        if action_id is not None:
            stmt = select(cls).where(cls.action_id == action_id).order_by(cls.created_at.desc()).limit(limit)
        res = await session.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def update(
            cls,
            session,
            news_id: int,
            **values,
    ) -> bool:
        values["updated_at"] = now_utc()
        res = await session.execute(
            update(cls)
            .where(cls.id == news_id)
            .values(**values)
            .execution_options(synchronize_session="fetch")
        )
        await session.commit()
        return (res.rowcount or 0) > 0

    @classmethod
    async def delete(cls, session, news_id: int) -> bool:
        res = await session.execute(delete(cls).where(cls.id == news_id))
        await session.commit()
        return (res.rowcount or 0) > 0


class Politician(Base):
    __tablename__ = "politicians"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Имя политика (обязательное)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Роль и влияние (произвольный текст)
    role_and_influence: Mapped[str] = mapped_column(Text, nullable=False)

    # Район (опционально)
    district_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("districts.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    district: Mapped[Optional["District"]] = relationship("District", lazy="selectin")

    # Склонность/идеология (-5..+5)
    ideology: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Влияние (может быть отрицательным)
    influence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Бонусы и штрафы (опционально)
    bonuses_penalties: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, onupdate=now_utc, nullable=False
    )

    __table_args__ = (
        CheckConstraint("ideology >= -5 AND ideology <= 5", name="ck_politicians_ideology_range"),
        Index("ix_politicians_district_name", "district_id", "name"),
    )

    # ===== CRUD / helpers =====
    @classmethod
    async def create(
            cls,
            session,
            *,
            name: str,
            role_and_influence: str,
            district_id: Optional[int] = None,
            ideology: int = 0,
            influence: int = 0,
            bonuses_penalties: Optional[str] = None,
    ) -> "Politician":
        obj = cls(
            name=name,
            role_and_influence=role_and_influence,
            district_id=district_id,
            ideology=ideology,
            influence=influence,
            bonuses_penalties=bonuses_penalties,
        )
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj

    @classmethod
    async def get_by_id(cls, session, politician_id: int) -> Optional["Politician"]:
        res = await session.execute(select(cls).where(cls.id == politician_id))
        return res.scalars().first()

    @classmethod
    async def by_district(cls, session, district_id: int) -> list["Politician"]:
        res = await session.execute(
            select(cls).where(cls.district_id == district_id).order_by(cls.name)
        )
        return list(res.scalars().all())

    @classmethod
    async def list_all(cls, session) -> list["Politician"]:
        res = await session.execute(select(cls).order_by(cls.name))
        return list(res.scalars().all())

    @classmethod
    async def update(cls, session, politician_id: int, **values) -> bool:
        values["updated_at"] = now_utc()
        res = await session.execute(
            update(cls)
            .where(cls.id == politician_id)
            .values(**values)
            .execution_options(synchronize_session="fetch")
        )
        await session.commit()
        return (res.rowcount or 0) > 0

    @classmethod
    async def delete(cls, session, politician_id: int) -> bool:
        res = await session.execute(delete(cls).where(cls.id == politician_id))
        await session.commit()
        return (res.rowcount or 0) > 0
