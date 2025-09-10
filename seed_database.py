#!/usr/bin/env python3
"""
Database seeding script that creates sample data for development and testing
"""
import asyncio
import logging
import sys
import random
from datetime import datetime, timedelta
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from db.session import get_session
from db.models import User, District, Action, News, Politician, ControlLevel, ActionStatus, ActionType
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Real game data from Змейс Макрокарта Версия.md
GAME_DISTRICTS = [
    {"name": "Стари-Град", "base_money": 0, "base_influence": 2, "base_information": 1, "base_force": 0},
    {"name": "Лиман", "base_money": 0, "base_influence": 1, "base_information": 2, "base_force": 0},
    {"name": "Подбара", "base_money": 2, "base_influence": 0, "base_information": 0, "base_force": 1},
    {"name": "Ротквария", "base_money": 3, "base_influence": 1, "base_information": 0, "base_force": 0},
    {"name": "Петроварадин", "base_money": 0, "base_influence": 1, "base_information": 0, "base_force": 3},
    {"name": "Саймиште", "base_money": 2, "base_influence": 0, "base_information": 0, "base_force": 1},
    {"name": "Грбавица", "base_money": 0, "base_influence": 1, "base_information": 2, "base_force": 0},
    {"name": "Адамовичево", "base_money": 0, "base_influence": 2, "base_information": 1, "base_force": 0}
]

GAME_POLITICIANS = [
    {"name": "Слободан Милошевич", "role": "Глава государства, контроль над госаппаратом", "district_id": 1, "ideology": -5, "influence": 6, "bonuses": "+5 ОК за каждую заявку Атака/Защита (конечно же все на поддержку режима)"},
    {"name": "Зоран Джинджич", "role": "Оппозиционный лидер, экономические реформы", "district_id": 2, "ideology": 5, "influence": 7, "bonuses": "+5 ОК в районах с +3 и больше"},
    {"name": "Желько «Аркан» Ражнатович", "role": "Теневая экономика, чёрный рынок", "district_id": 3, "ideology": -2, "influence": 5, "bonuses": "+3 Силы при Защите Подбары, -3 Силы при атаке на Подбару"},
    {"name": "Борислав Милошевич", "role": "Влияние НАТО и ЕС", "district_id": 4, "ideology": 3, "influence": 4, "bonuses": "Способны вводить санкции, бонус к защите районов (решается через переписку с МГ)"},
    {"name": "Небойша Павкович", "role": "Контроль над армией, силовые структуры", "district_id": 5, "ideology": -4, "influence": 6, "bonuses": "+5 ОК при заявках на Защиту в любых районах"},
    {"name": "Миролюб Лабус", "role": "Влияние среди рабочих, забастовки", "district_id": 6, "ideology": 2, "influence": 4, "bonuses": "+3 Денег при Кооперативных заявках, -3 Денег при любых Атаках"},
    {"name": "Чедомир «Чеда» Йованович", "role": "Молодёжные протесты, уличные акции", "district_id": 7, "ideology": 4, "influence": 5, "bonuses": "+5 ОК при массовых акциях, штраф к силовому контролю"},
    {"name": "Патриарх Павле", "role": "Церковь, влияние на традиционалистов", "district_id": 8, "ideology": -1, "influence": 5, "bonuses": "+5 Влияния в цикл"}
]

SAMPLE_NEWS_ITEMS = [
    {
        "title": "Welcome to the Vampire Chronicles",
        "body": "The eternal struggle for power begins. Multiple factions vie for control over the city's districts, each with their own agenda and methods. Choose your allies wisely, for the night is dark and full of intrigue."
    },
    {
        "title": "District Control Mechanics Updated",
        "body": "New resource management systems have been implemented. Districts now generate resources based on control level and multipliers. Plan your actions carefully to maximize your influence."
    },
    {
        "title": "Political Influence System Active",
        "body": "Politicians across the city are now actively influencing district affairs. Building relationships with key figures can provide significant advantages in your quest for dominance."
    }
]

SAMPLE_FACTIONS = [
    "The Crimson Court", "Shadow Syndicate", "Iron Brotherhood", 
    "Midnight Council", "Blood Aristocracy", "The Dark Parliament"
]

ACTION_TYPES_SAMPLE = [
    "attack", "defend", "scout", "communicate"
]

def get_action_description(kind):
    """Get action description based on game rules"""
    descriptions = {
        "attack": "Захват района (нейтрального или принадлежащего другому игроку). Использует Силу и Деньги, иногда Влияние для изменения позиции политика.",
        "defend": "Оборона района от атак других игроков. Использует Силу и Деньги, иногда Влияние для изменения позиции политика.",
        "scout": "Получение информации о том, кто и какими силами атакует район, кто проводит в нем ритуалы и движущихся по нему курьеров. Использует Информацию.",
        "communicate": "Распространение слухов через политические/общественные каналы. Использует Влияние."
    }
    return descriptions.get(kind, "Неизвестное действие")

async def clear_existing_data(session):
    """Clear existing data from all tables"""
    logger.info("Clearing existing data...")
    
    # Clear in reverse dependency order
    tables = ['news', 'actions', 'politicians', 'user_scouts_districts', 'districts', 'users']
    
    for table in tables:
        try:
            await session.execute(text(f"DELETE FROM {table}"))
            logger.info(f"Cleared table: {table}")
        except Exception as e:
            logger.warning(f"Could not clear table {table}: {e}")
    
    await session.commit()

async def seed_sample_users(session):
    """Create sample users for development/testing"""
    logger.info("Creating sample users...")
    
    sample_users = []
    
    # Create admin user
    admin_user = User(
        tg_id=999999999,  # Fake telegram ID
        username="admin_vampire",
        first_name="Admin",
        last_name="Vampire",
        in_game_name="The Elder",
        language_code="en",
        money=1000,
        influence=500,
        information=300,
        force=200,
        base_money=1000,
        base_influence=500,
        base_information=300,
        base_force=200,
        ideology=0,
        faction="The Council of Elders",
        available_actions=10,
        max_available_actions=10,
        is_admin=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    session.add(admin_user)
    sample_users.append(admin_user)
    
    # Create sample players
    for i in range(1, 11):  # 10 sample players
        faction = random.choice(SAMPLE_FACTIONS)
        ideology = random.randint(-5, 5)
        
        user = User(
            tg_id=100000000 + i,  # Fake telegram IDs
            username=f"player_{i}",
            first_name=f"Player",
            last_name=f"{i}",
            in_game_name=f"Vampire Lord {chr(64 + i)}",  # A, B, C, etc.
            language_code="en",
            money=random.randint(50, 200),
            influence=random.randint(20, 100),
            information=random.randint(10, 80),
            force=random.randint(5, 60),
            base_money=random.randint(50, 150),
            base_influence=random.randint(20, 80),
            base_information=random.randint(10, 60),
            base_force=random.randint(5, 40),
            ideology=ideology,
            faction=faction,
            available_actions=random.randint(3, 8),
            max_available_actions=random.randint(5, 10),
            is_admin=False,
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
            updated_at=datetime.utcnow()
        )
        session.add(user)
        sample_users.append(user)
    
    await session.commit()
    await session.refresh(admin_user)  # Get the ID
    
    logger.info(f"Created {len(sample_users)} sample users")
    return sample_users

async def seed_game_districts(session):
    """Create game districts with no owners (neutral)"""
    logger.info("Creating game districts...")
    
    districts = []
    
    for district_data in GAME_DISTRICTS:
        district = District(
            name=district_data["name"],
            owner_id=None,  # All districts start neutral
            control_points=0,  # Start with no control points
            control_level=ControlLevel.MINIMAL,  # All start at minimal level
            resource_multiplier=1.0,  # Standard multiplier
            base_money=district_data["base_money"],
            base_influence=district_data["base_influence"],
            base_information=district_data["base_information"],
            base_force=district_data["base_force"],
            created_at=datetime.utcnow()
        )
        session.add(district)
        districts.append(district)
    
    await session.commit()
    logger.info(f"Created {len(districts)} game districts")
    return districts

async def seed_game_politicians(session, districts):
    """Create game politicians"""
    logger.info("Creating game politicians...")
    logger.info(f"Received {len(districts)} districts to work with")
    
    # Debug: print district IDs
    for i, district in enumerate(districts):
        logger.info(f"District {i+1}: {district.name} (ID: {district.id})")
    
    politicians = []
    
    for politician_data in GAME_POLITICIANS:
        # Get the actual district ID from the created districts list
        # politician_data["district_id"] is 1-based, but we need the actual DB ID
        district_index = politician_data["district_id"] - 1  # Convert to 0-based index
        actual_district = districts[district_index]
        
        logger.info(f"Creating politician {politician_data['name']} for district {actual_district.name} (ID: {actual_district.id})")
        
        politician = Politician(
            name=politician_data["name"],
            role_and_influence=politician_data["role"],
            district_id=actual_district.id,  # Use the actual district ID from DB
            ideology=politician_data["ideology"],
            influence=politician_data["influence"],
            bonuses_penalties=politician_data["bonuses"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(politician)
        politicians.append(politician)
    
    await session.commit()
    logger.info(f"Created {len(politicians)} game politicians")
    return politicians

async def seed_sample_actions(session, users, districts):
    """Create sample actions"""
    logger.info("Creating sample actions...")
    
    actions = []
    action_statuses = list(ActionStatus)
    action_types = list(ActionType)
    
    # Create various types of actions
    for i in range(50):  # 50 sample actions
        owner = random.choice(users)
        district = random.choice(districts) if random.random() > 0.3 else None
        action_type = random.choice(action_types)
        status = random.choice(action_statuses)
        kind = random.choice(ACTION_TYPES_SAMPLE)
        
        # Create some support actions (child actions)
        parent_action = None
        if i > 10 and random.random() > 0.8:  # 20% chance for support action
            parent_action = random.choice(actions[:i])
            action_type = ActionType.SUPPORT
        
        # Set resources based on action type according to game rules
        force = 0
        money = 0
        influence = 0
        information = 0
        
        if kind == "attack":
            # Attack uses Force and Money primarily, sometimes Influence
            force = random.randint(1, 4)
            money = random.randint(1, 3)
            if random.random() < 0.3:  # 30% chance to use influence
                influence = random.randint(1, 2)
        elif kind == "defend":
            # Defend uses Force and Money primarily, sometimes Influence  
            force = random.randint(1, 4)
            money = random.randint(1, 3)
            if random.random() < 0.3:  # 30% chance to use influence
                influence = random.randint(1, 2)
        elif kind == "scout":
            # Scout uses Information primarily
            information = random.randint(1, 3)
        elif kind == "communicate":
            # Communicate uses Influence primarily
            influence = random.randint(1, 3)
        
        # Calculate estimated power based on resources used (from game rules)
        estimated_power = (force * 10) + (money * 5) + influence + information
        
        # Get Russian action names
        action_names = {
            "attack": "Атака",
            "defend": "Защита", 
            "scout": "Разведка",
            "communicate": "Коммуникация"
        }
        action_name = action_names.get(kind, kind.title())
        
        action = Action(
            kind=kind,
            title=f"{action_name} в районе {district.name}" if district else f"Общегородская {action_name}",
            status=status,
            owner_id=owner.id,
            district_id=district.id if district else None,
            type=action_type,
            parent_action_id=parent_action.id if parent_action else None,
            force=force,
            money=money,
            influence=influence,
            information=information,
            estimated_power=estimated_power,
            on_point=random.random() > 0.7,  # 30% chance
            text=f"Action description for {kind}. {get_action_description(kind)}",
            created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 168)),  # Last week
            updated_at=datetime.utcnow()
        )
        session.add(action)
        actions.append(action)
    
    await session.commit()
    logger.info(f"Created {len(actions)} sample actions")
    return actions

async def seed_sample_news(session, actions):
    """Create sample news items"""
    logger.info("Creating sample news...")
    
    news_items = []
    
    # Create general news
    for news_data in SAMPLE_NEWS_ITEMS:
        news = News(
            title=news_data["title"],
            body=news_data["body"],
            media_urls=[],
            action_id=None,
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 7)),
            updated_at=datetime.utcnow()
        )
        session.add(news)
        news_items.append(news)
    
    # Create some action-related news
    for i in range(5):
        action = random.choice(actions)
        news = News(
            title=f"Action Report: {action.title}",
            body=f"Recent activity detected in relation to {action.title}. Status: {action.status.value}. Resources allocated: Money {action.money}, Influence {action.influence}.",
            media_urls=[],
            action_id=action.id,
            created_at=action.created_at + timedelta(hours=random.randint(1, 24)),
            updated_at=datetime.utcnow()
        )
        session.add(news)
        news_items.append(news)
    
    await session.commit()
    logger.info(f"Created {len(news_items)} sample news items")
    return news_items

async def seed_scout_relationships(session, users, districts):
    """Create sample scouting relationships"""
    logger.info("Creating sample scout relationships...")
    
    relationships = 0
    
    # Create some scouting relationships
    for user in users[:5]:  # First 5 users scout districts
        num_scouts = random.randint(1, 3)
        scouted_districts = random.sample(districts, min(num_scouts, len(districts)))
        
        for district in scouted_districts:
            # Don't scout your own district
            if district.owner_id != user.id:
                await session.execute(
                    text("INSERT INTO user_scouts_districts (user_id, district_id) VALUES (:user_id, :district_id)"),
                    {'user_id': user.id, 'district_id': district.id}
                )
                relationships += 1
    
    await session.commit()
    logger.info(f"Created {relationships} scout relationships")

async def main():
    """Main seeding function"""
    logger.info("Starting database seeding with real game data...")
    
    async with get_session() as session:
        try:
            # Clear existing data
            await clear_existing_data(session)
            
            # Create real game data 
            districts = await seed_game_districts(session)
            politicians = await seed_game_politicians(session, districts)
            
            # No sample users or actions - only real game data
            
            # Create some basic news
            news_items = []
            news = News(
                title="Загадочное ограбление в Старом Граде",
                body="Нови-Сад — Сегодня ранним утром полиция оцепила район Старого Града после того, как поступило сообщение о необычном ограблении, произошедшем минувшей ночью. По предварительной информации, объектом нападения стал не банк или ювелирный магазин, а частная коллекция, находившаяся в старинном доме на одной из узких улочек.\n\nПреступники действовали бесшумно и, по словам свидетелей, не оставили никаких следов взлома. Из дома была похищена не денежная сумма и не драгоценности, а несколько загадочных артефактов, имеющих, по словам владельца, не столько материальную, сколько историческую и оккультную ценность. Среди похищенного упоминаются «Ключ Безмолвия» и «Зеркало Эхо». Эксперты затрудняются оценить стоимость украденного, поскольку подобные предметы никогда не фигурировали на чёрном рынке.\n\nСледствие рассматривает произошедшее как тщательно спланированную операцию. Местная пресса уже окрестила преступление «Ограблением-призраком», подчёркивая его таинственность. Полиция призывает жителей сохранять спокойствие и сообщать любую информацию, которая может помочь в расследовании.",
                media_urls=[],
                action_id=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(news)
            news_items.append(news)
            await session.commit()
            
            logger.info("Database seeding completed successfully!")
            logger.info("Real game data created:")
            logger.info(f"  - {len(districts)} districts (all neutral)")
            logger.info(f"  - {len(politicians)} politicians")
            logger.info(f"  - {len(news_items)} news items")
            logger.info("  - No sample users or actions (only real players will be created when they join)")
            logger.info("")
            logger.info("Districts created:")
            for d in districts:
                logger.info(f"  - {d.name}: +{d.base_money} Денег, +{d.base_influence} Влияния, +{d.base_information} Информации, +{d.base_force} Силы")
            
        except Exception as e:
            logger.error(f"Error during seeding: {e}")
            await session.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(main())