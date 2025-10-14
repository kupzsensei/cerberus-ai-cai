import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
import database
from utils import config

# Get the database file that's being used by the application
db_file = config.get("database_file", "tasks.db")
database.configure_database(db_file)

print(f"Database file being used: {db_file}")
print(f"Full path: {os.path.abspath(db_file)}")

async def check_db():
    configs = await database.get_email_configs()
    print(f"Number of email configs found: {len(configs)}")
    for config in configs:
        print(f"  - ID: {config['id']}, Server: {config['smtp_server']}, Username: {config['username']}")

asyncio.run(check_db())