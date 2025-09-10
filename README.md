# Vampires Bot

A sophisticated Telegram bot for managing vampire-themed role-playing game activities, built with Python, aiogram 3.x, and PostgreSQL.

## Features

- **User Management**: Registration, profiles, and role-based permissions
- **District Management**: Territory control with resource management
- **Action System**: Individual, collective, and support actions
- **Scouting System**: Intelligence gathering and reconnaissance
- **News System**: Game updates and notifications  
- **Political System**: NPC politicians with influence mechanics
- **Template-based UI**: Multilingual support with Jinja2 templates

## Quick Start with Docker

### Prerequisites

- Docker and Docker Compose installed
- Git

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd vampires_bot
   ```

2. **Configure environment**:
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env with your bot token
   # BOT_TOKEN=your_bot_token_here
   # BOT_NAME=@your_bot_username
   ```

3. **Start the services**:
   ```bash
   docker-compose up -d
   ```

4. **View logs**:
   ```bash
   docker-compose logs -f vampires_bot
   ```

### Configuration

The bot is configured via environment variables in `.env`:

- `BOT_TOKEN`: Your Telegram bot token from @BotFather
- `BOT_NAME`: Your bot's username (e.g., @your_bot)
- `DATABASE_URL`: PostgreSQL connection string (automatically configured in Docker)
- `LOG_LEVEL`: Logging level (INFO, DEBUG, WARNING, ERROR)
- `DEFAULT_LOCALIZATION`: Default language (ru, en)
- `TEMPLATE_ROOT`: Template directory path

### Database

The setup includes:
- **PostgreSQL 15**: Primary database with persistent volumes
- **Automatic migrations**: Alembic handles schema creation and updates
- **Health checks**: Ensures database is ready before bot starts

Database connection details (for development):
- Host: `localhost:5432`
- Database: `vampires_bot`
- User: `bot_user`
- Password: `bot_password`

## Architecture

### Core Components

- **Models** (`db/models.py`): SQLAlchemy models for users, districts, actions, news, politicians
- **Screens** (`screens/`): UI rendering with Jinja2 templates  
- **Options** (`options/`): Button handlers and menu logic
- **Routes** (`routes/`): Message and callback routing
- **Middlewares** (`middlewares/`): User registration, timing, etc.
- **Services** (`services/`): Business logic for notifications, messaging

### Key Models

- **User**: Player profiles with resources (money, influence, information, force)
- **District**: Controllable territories with resource generation
- **Action**: Player activities (individual, collective, support actions)
- **News**: Game events and announcements
- **Politician**: NPCs with influence and ideological alignments

### Template System

- Located in `templates/ru/`
- Jinja2 templating with internationalization support
- Separate templates for screens and keyboard layouts
- Supports dynamic content based on user state

## Development

### Local Development

For development outside Docker:

1. **Install dependencies**:
   ```bash
   poetry install
   ```

2. **Set up database**:
   ```bash
   # Start only PostgreSQL
   docker-compose up -d postgres
   
   # Run migrations
   python init_db.py
   ```

3. **Run the bot**:
   ```bash
   python app.py
   ```

### Database Migrations

Create new migrations:
```bash
alembic revision --autogenerate -m "Your migration message"
```

Apply migrations:
```bash
alembic upgrade head
```

### Project Structure

```
vampires_bot/
├── app.py                 # Main application entry point
├── config.py              # Configuration management
├── init_db.py            # Database initialization script
├── entrypoint.sh         # Docker entrypoint script
├── docker-compose.yml    # Docker services configuration
├── Dockerfile            # Bot container definition
├── db/                   # Database layer
│   ├── models.py         # SQLAlchemy models
│   ├── session.py        # Database session management
│   └── config.py         # Database configuration
├── screens/              # UI screens
├── options/              # Button handlers and menu logic
├── routes/               # Message routing
├── middlewares/          # Request middlewares
├── services/             # Business logic services
├── templates/ru/         # Jinja2 templates (Russian)
├── keyboards/            # Keyboard layout definitions
├── states/               # FSM state definitions
├── text_handlers/        # Text input handlers
└── utils/                # Utility functions
```

## Commands

The bot supports these commands:
- `/start` - Initialize user and show main menu
- Additional commands defined in the options system

## Deployment

### Production Deployment

1. **Environment Setup**:
   - Use strong passwords for PostgreSQL
   - Set appropriate log levels
   - Configure proper backup strategies

2. **Security Considerations**:
   - Keep bot token secure
   - Use environment variables for sensitive data
   - Regular security updates

3. **Monitoring**:
   - Check bot logs: `docker-compose logs vampires_bot`
   - Monitor database: `docker-compose logs postgres`
   - Health checks are built into the containers

### Backup

Database backups:
```bash
# Create backup
docker-compose exec postgres pg_dump -U bot_user vampires_bot > backup.sql

# Restore backup
docker-compose exec -T postgres psql -U bot_user vampires_bot < backup.sql
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with appropriate tests
4. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions:
- Check the logs: `docker-compose logs`
- Review the configuration in `.env`
- Ensure your bot token is valid and the bot is not already running elsewhere
