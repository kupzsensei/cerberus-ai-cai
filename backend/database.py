# database.py
import aiosqlite
import json
from datetime import datetime
import pytz

ADELAIDE_TZ = pytz.timezone('Australia/Adelaide')
DATABASE_FILE = "" # This will be loaded from config

def configure_database(db_file: str):
    """Sets the database file path from the config."""
    global DATABASE_FILE
    DATABASE_FILE = db_file

async def initialize_db():
    """Initializes the database and creates the tasks table if it doesn't exist."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                prompt TEXT,
                ollama_model TEXT,
                result TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                processing_time_seconds REAL 
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS ollama_servers (
                name TEXT PRIMARY KEY,
                url TEXT NOT NULL
            )
        ''')
        await db.commit()

async def add_or_update_task(task_id: str, prompt: str, ollama_model: str):
    """
    Adds a new task, or resets an existing one, clearing the old processing time.
    """
    now = datetime.now(ADELAIDE_TZ)
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO tasks 
            (task_id, status, prompt, ollama_model, result, created_at, updated_at, processing_time_seconds) 
            VALUES (?, 'pending', ?, ?, NULL, ?, ?, NULL)
            """,
            (task_id, prompt, ollama_model, now, now)
        )
        await db.commit()

async def update_task(task_id: str, status: str, result: dict = None, processing_time: float = None):
    """Updates a task's status and result, and optionally the processing time."""
    now = datetime.now(ADELAIDE_TZ)
    result_json = json.dumps(result) if result else None
    async with aiosqlite.connect(DATABASE_FILE) as db:
        if processing_time is not None:
            # When processing is finished, update everything including the time
            await db.execute(
                """
                UPDATE tasks 
                SET status = ?, result = ?, updated_at = ?, processing_time_seconds = ?
                WHERE task_id = ?
                """,
                (status, result_json, now, round(processing_time, 2), task_id)
            )
        else:
            # For intermediate statuses like 'in_progress', just update the status
            await db.execute(
                "UPDATE tasks SET status = ?, result = ?, updated_at = ? WHERE task_id = ?",
                (status, result_json, now, task_id)
            )
        await db.commit()

async def get_task(task_id: str):
    """Retrieves a single task from the database."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)) as cursor:
            task = await cursor.fetchone()
            if task:
                task_dict = dict(task)
                if task_dict.get('result'):
                    task_dict['result'] = json.loads(task_dict['result'])
                return task_dict
            return None

async def get_all_tasks():
    """Retrieves all tasks from the database."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tasks ORDER BY created_at DESC") as cursor:
            tasks = await cursor.fetchall()
            task_list = []
            for task in tasks:
                task_dict = dict(task)
                if task_dict.get('result'):
                    task_dict['result'] = json.loads(task_dict['result'])
                task_list.append(task_dict)
            return task_list

async def delete_task(task_id: str):
    """Deletes a task from the database."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
        await db.commit()

async def add_ollama_server(name: str, url: str):
    """Adds a new Ollama server to the database."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO ollama_servers (name, url)
            VALUES (?, ?)
            """,
            (name, url)
        )
        await db.commit()

async def get_ollama_servers():
    """Retrieves all configured Ollama servers from the database."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT name, url FROM ollama_servers ORDER BY name") as cursor:
            servers = await cursor.fetchall()
            return [dict(row) for row in servers]

async def get_ollama_server_by_name(name: str):
    """Retrieves a single Ollama server from the database by name."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT name, url FROM ollama_servers WHERE name = ?", (name,)) as cursor:
            server = await cursor.fetchone()
            if server:
                return dict(server)
            return None

async def delete_ollama_server(name: str):
    """Deletes an Ollama server from the database."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute("DELETE FROM ollama_servers WHERE name = ?", (name,))
        await db.commit()

async def initialize_research_db():
    """Initializes the database and creates the research table if it doesn't exist."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS research (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                result TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                generation_time REAL,
                ollama_server_name TEXT
            )
        ''')
        await db.commit()

async def add_research(query: str, result: str, generation_time: float, ollama_server_name: str):
    """Adds a new research entry to the database."""
    now = datetime.utcnow()
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute(
            """
            INSERT INTO research (query, result, created_at, generation_time, ollama_server_name)
            VALUES (?, ?, ?, ?, ?)
            """,
            (query, result, now, generation_time, ollama_server_name)
        )
        await db.commit()

async def get_all_research():
    """Retrieve all research entries from the database."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id, query, created_at, generation_time, ollama_server_name FROM research ORDER BY created_at DESC") as cursor:
            research_list = await cursor.fetchall()
            return [dict(row) for row in research_list]

async def get_research_by_id(research_id: int):
    """Retrieves a single research entry from the database by ID."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM research WHERE id = ?", (research_id,)) as cursor:
            research_entry = await cursor.fetchone()
            if research_entry:
                return dict(research_entry)
            return None

async def delete_research(research_id: int):
    """Deletes a research entry from the database."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute("DELETE FROM research WHERE id = ?", (research_id,))
        await db.commit()