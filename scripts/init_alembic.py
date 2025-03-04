import os
import shutil
import subprocess
from pathlib import Path

def run_command(command):
    """Run a shell command and print the output"""
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in iter(process.stdout.readline, b''):
        print(line.decode('utf-8').strip())
    process.stdout.close()
    return process.wait()

def init_alembic():
    """Initialize Alembic directory structure"""
    # Get the project root directory
    BASE_DIR = Path(__file__).resolve().parent.parent
    
    # Check if alembic directory exists
    alembic_dir = BASE_DIR / "alembic"
    if alembic_dir.exists():
        print(f"Removing existing alembic directory: {alembic_dir}")
        shutil.rmtree(alembic_dir)
    
    # Initialize alembic
    print("Initializing alembic...")
    run_command("alembic init alembic")
    
    # Update env.py with our custom code
    env_py = alembic_dir / "env.py"
    with open(env_py, "r") as f:
        env_content = f.read()
    
    # Replace the content with our custom env.py
    env_content = """from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Import all models so they're registered with the metadata
from app.models import Base
import app.models.agency  # This ensures the Agency model is registered

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get the database URL from the environment
import os
from dotenv import load_dotenv
from pathlib import Path

# Get the project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Override sqlalchemy.url with the one from environment if available
db_url = os.getenv("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    \"\"\"Run migrations in 'offline' mode.\"\"\"
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    \"\"\"Run migrations in 'online' mode.\"\"\"
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
"""
    
    with open(env_py, "w") as f:
        f.write(env_content)
    
    print("Alembic initialization complete!")

if __name__ == "__main__":
    init_alembic() 