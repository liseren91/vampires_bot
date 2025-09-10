#!/bin/bash
set -e

echo "Starting entrypoint script..."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
while ! pg_isready -h postgres -p 5432 -U bot_user; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 2
done

echo "PostgreSQL is ready!"

# Run database migrations
echo "Running database migrations..."
python init_db.py

# Wait a moment for database to be fully ready
echo "Waiting for database to be fully ready..."
sleep 3

# Seed database with sample data for development
echo "Seeding database with game data..."
python seed_database.py

# Alternative seeding options:
# python seed_direct.py        # Direct migration from SQLite (if needed)
# python seed_from_sql.py      # SQL dump method (if SQL dump exists)

echo "Starting the bot application..."
exec python app.py
