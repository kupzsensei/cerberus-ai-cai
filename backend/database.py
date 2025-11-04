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
                model_name TEXT,
                server_name TEXT,
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
        await db.execute('''
            CREATE TABLE IF NOT EXISTS external_ai_servers (
                name TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                api_key TEXT NOT NULL
            )
        ''')
        await db.commit()

async def add_external_ai_server(name: str, type: str, api_key: str):
    """Adds a new external AI server to the database."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO external_ai_servers (name, type, api_key)
            VALUES (?, ?, ?)
            """,
            (name, type, api_key)
        )
        await db.commit()

async def get_external_ai_servers():
    """Retrieves all configured external AI servers from the database."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT name, type, api_key FROM external_ai_servers ORDER BY name") as cursor:
            servers = await cursor.fetchall()
            return [dict(row) for row in servers]

async def get_external_ai_server_by_name(name: str):
    """Retrieves a single external AI server from the database by name."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT name, type, api_key FROM external_ai_servers WHERE name = ?", (name,)) as cursor:
            server = await cursor.fetchone()
            if server:
                return dict(server)
            return None

async def delete_external_ai_server(name: str):
    """Deletes an external AI server from the database."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute("DELETE FROM external_ai_servers WHERE name = ?", (name,))
        await db.commit()

async def add_or_update_task(task_id: str, prompt: str, model_name: str, server_name: str):
    """
    Adds a new task, or resets an existing one, clearing the old processing time.
    """
    now = datetime.now(ADELAIDE_TZ)
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO tasks 
            (task_id, status, prompt, model_name, server_name, result, created_at, updated_at, processing_time_seconds) 
            VALUES (?, 'pending', ?, ?, ?, NULL, ?, ?, NULL)
            """,
            (task_id, prompt, model_name, server_name, now, now)
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
                ollama_server_name TEXT,
                ollama_model TEXT
            )
        ''')
        await db.commit()

async def initialize_research_jobs_db():
    """Initializes tables for research jobs, drafts, and logs."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS research_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                server_name TEXT,
                model_name TEXT,
                server_type TEXT,
                target_count INTEGER NOT NULL,
                status TEXT NOT NULL,
                accepted_count INTEGER DEFAULT 0,
                research_id INTEGER,
                drafts_count INTEGER DEFAULT 0,
                errors_count INTEGER DEFAULT 0,
                config_json TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                started_at TIMESTAMP,
                finished_at TIMESTAMP
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS research_drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                title TEXT,
                summary TEXT,
                date TEXT,
                targets TEXT,
                method TEXT,
                exploit_used TEXT,
                relevance TEXT,
                source_url TEXT,
                canonical_url TEXT,
                title_key TEXT,
                content_hash TEXT,
                markdown_snippet TEXT,
                qa_status TEXT,
                qa_message TEXT,
                link_ok INTEGER DEFAULT 0,
                is_duplicate INTEGER DEFAULT 0,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                FOREIGN KEY (job_id) REFERENCES research_jobs(id) ON DELETE CASCADE
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS research_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                ts TIMESTAMP NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES research_jobs(id) ON DELETE CASCADE
            )
        ''')
        await db.commit()

        # Safe ALTERs for existing DBs
        # research_jobs: accepted_count, research_id, config_json
        try:
            async with db.execute("PRAGMA table_info(research_jobs)") as cursor:
                cols = [row[1] for row in await cursor.fetchall()]
            if 'accepted_count' not in cols:
                await db.execute("ALTER TABLE research_jobs ADD COLUMN accepted_count INTEGER DEFAULT 0")
            if 'research_id' not in cols:
                await db.execute("ALTER TABLE research_jobs ADD COLUMN research_id INTEGER")
            if 'config_json' not in cols:
                await db.execute("ALTER TABLE research_jobs ADD COLUMN config_json TEXT")
        except Exception:
            pass
        # research_drafts: qa_message, link_ok, is_duplicate
        try:
            async with db.execute("PRAGMA table_info(research_drafts)") as cursor:
                cols = [row[1] for row in await cursor.fetchall()]
            if 'qa_message' not in cols:
                await db.execute("ALTER TABLE research_drafts ADD COLUMN qa_message TEXT")
            if 'link_ok' not in cols:
                await db.execute("ALTER TABLE research_drafts ADD COLUMN link_ok INTEGER DEFAULT 0")
            if 'is_duplicate' not in cols:
                await db.execute("ALTER TABLE research_drafts ADD COLUMN is_duplicate INTEGER DEFAULT 0")
        except Exception:
            pass
        await db.commit()

        # Helpful indexes for faster lookups and dedupe checks
        try:
            await db.execute("CREATE INDEX IF NOT EXISTS idx_research_drafts_job_id ON research_drafts(job_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_research_drafts_canonical_url ON research_drafts(canonical_url)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_research_drafts_title_key ON research_drafts(title_key)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_research_logs_job_id ON research_logs(job_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_research_jobs_status ON research_jobs(status)")
        except Exception:
            pass
        await db.commit()

async def add_research_job(query: str, server_name: str, model_name: str, server_type: str, target_count: int, config: dict | None = None) -> int:
    now = datetime.utcnow()
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute(
            '''INSERT INTO research_jobs (query, server_name, model_name, server_type, target_count, status, drafts_count, errors_count, config_json, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, 'pending', 0, 0, ?, ?, ?)''',
            (query, server_name, model_name, server_type, target_count, json.dumps(config or {}), now, now)
        )
        await db.commit()
        cursor = await db.execute('SELECT last_insert_rowid()')
        row = await cursor.fetchone()
        return int(row[0])

async def get_research_job(job_id: int):
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM research_jobs WHERE id = ?', (job_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def update_research_job(job_id: int, **fields):
    if not fields:
        return
    fields['updated_at'] = datetime.utcnow()
    cols = ', '.join([f"{k} = ?" for k in fields.keys()])
    vals = list(fields.values()) + [job_id]
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute(f'UPDATE research_jobs SET {cols} WHERE id = ?', vals)
        await db.commit()

async def increment_research_job_counts(job_id: int, drafts_delta: int = 0, errors_delta: int = 0):
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute(
            'UPDATE research_jobs SET drafts_count = drafts_count + ?, errors_count = errors_count + ?, updated_at = ? WHERE id = ?',
            (drafts_delta, errors_delta, datetime.utcnow(), job_id)
        )
        await db.commit()

async def add_research_log(job_id: int, level: str, message: str):
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute(
            'INSERT INTO research_logs (job_id, ts, level, message) VALUES (?, ?, ?, ?)',
            (job_id, datetime.utcnow(), level, message)
        )
        await db.commit()

async def get_research_logs_since(job_id: int, last_id: int = 0):
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM research_logs WHERE job_id = ? AND id > ? ORDER BY id ASC', (job_id, last_id)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def add_research_draft(job_id: int, draft: dict) -> int:
    now = datetime.utcnow()
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute('''
            INSERT INTO research_drafts (job_id, title, summary, date, targets, method, exploit_used, relevance, source_url, canonical_url, title_key, content_hash, markdown_snippet, qa_status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            job_id,
            draft.get('title'),
            draft.get('summary'),
            draft.get('date'),
            draft.get('targets'),
            draft.get('method'),
            draft.get('exploit_used'),
            draft.get('relevance'),
            draft.get('source_url'),
            draft.get('canonical_url'),
            draft.get('title_key'),
            draft.get('content_hash'),
            draft.get('markdown_snippet'),
            draft.get('qa_status', 'pending'),
            now,
            now
        ))
        await db.commit()
        cursor = await db.execute('SELECT last_insert_rowid()')
        row = await cursor.fetchone()
        return int(row[0])

async def list_research_drafts(job_id: int, limit: int = 50, offset: int = 0):
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT id, title, date, qa_status, source_url, created_at
            FROM research_drafts WHERE job_id = ? ORDER BY id ASC LIMIT ? OFFSET ?
        ''', (job_id, limit, offset)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def list_research_drafts_full(job_id: int):
    """Returns all drafts for a job including markdown_snippet and QA fields."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT id, title, date, qa_status, qa_message, source_url, canonical_url, markdown_snippet, created_at
            FROM research_drafts WHERE job_id = ? ORDER BY id ASC
        ''', (job_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def update_research_draft(draft_id: int, **fields):
    if not fields:
        return
    fields['updated_at'] = datetime.utcnow()
    cols = ', '.join([f"{k} = ?" for k in fields.keys()])
    vals = list(fields.values()) + [draft_id]
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute(f'UPDATE research_drafts SET {cols} WHERE id = ?', vals)
        await db.commit()

async def add_research(query: str, result: str, generation_time: float, ollama_server_name: str, ollama_model: str):
    """Adds a new research entry to the database."""
    now = datetime.utcnow()
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute(
            """
            INSERT INTO research (query, result, created_at, generation_time, ollama_server_name, ollama_model)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (query, result, now, generation_time, ollama_server_name, ollama_model)
        )
        await db.commit()
        cursor = await db.execute('SELECT last_insert_rowid()')
        row = await cursor.fetchone()
        return int(row[0])

async def get_all_research():
    """Retrieve all research entries from the database."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id, query, created_at, generation_time, ollama_server_name, ollama_model FROM research ORDER BY created_at DESC") as cursor:
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

async def initialize_local_storage_db():
    """Initializes the database and creates the local_storage_jobs table if it doesn't exist."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS local_storage_jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                prompt TEXT,
                model_name TEXT,
                server_name TEXT,
                server_type TEXT,
                filenames TEXT,
                result TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                processing_time_seconds REAL
            )
        ''')
        await db.commit()

async def initialize_email_scheduler_db():
    """Initializes the database and creates tables for email scheduling functionality."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        # Email server configuration table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS email_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                smtp_server TEXT NOT NULL,
                smtp_port INTEGER NOT NULL,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                sender_email TEXT NOT NULL,
                sender_name TEXT,
                use_tls BOOLEAN DEFAULT 1,
                use_ssl BOOLEAN DEFAULT 0,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        ''')
        
        # Email recipient groups table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS email_recipient_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        ''')
        
        # Email recipients table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS email_recipients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                name TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                FOREIGN KEY (group_id) REFERENCES email_recipient_groups (id) ON DELETE CASCADE
            )
        ''')
        
        # Scheduled research table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_research (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                frequency TEXT NOT NULL,  -- daily, weekly, monthly
                day_of_week INTEGER,      -- 0-6 (Monday-Sunday), NULL for daily
                day_of_month INTEGER,     -- 1-31, NULL for daily/weekly
                hour INTEGER NOT NULL,    -- 0-23
                minute INTEGER NOT NULL,  -- 0-59
                start_date TEXT,
                end_date TEXT,
                last_run TIMESTAMP,
                next_run TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                recipient_group_id INTEGER NOT NULL,
                date_range_days INTEGER NOT NULL,  -- Number of days to look back
                model_name TEXT,
                server_name TEXT,
                server_type TEXT,
                email_config_id INTEGER,  -- Reference to specific email configuration
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                FOREIGN KEY (recipient_group_id) REFERENCES email_recipient_groups (id) ON DELETE CASCADE,
                FOREIGN KEY (email_config_id) REFERENCES email_configs (id) ON DELETE SET NULL
            )
        ''')
        
        # Email delivery logs table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS email_delivery_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scheduled_research_id INTEGER NOT NULL,
                subject TEXT,
                recipients TEXT,  -- JSON array of emails
                status TEXT NOT NULL,  -- sent, failed
                error_message TEXT,
                sent_at TIMESTAMP,
                date_range_start TEXT,
                date_range_end TEXT,
                FOREIGN KEY (scheduled_research_id) REFERENCES scheduled_research (id) ON DELETE CASCADE
            )
        ''')
        
        # Migration: Add date_range_start and date_range_end columns if they don't exist
        try:
            # Check if the columns exist
            async with db.execute("PRAGMA table_info(email_delivery_logs)") as cursor:
                columns = await cursor.fetchall()
                column_names = [column[1] for column in columns]
                
                if "date_range_start" not in column_names:
                    # Add the column
                    await db.execute("ALTER TABLE email_delivery_logs ADD COLUMN date_range_start TEXT")
                    print("Added date_range_start column to email_delivery_logs table")
                    
                if "date_range_end" not in column_names:
                    # Add the column
                    await db.execute("ALTER TABLE email_delivery_logs ADD COLUMN date_range_end TEXT")
                    print("Added date_range_end column to email_delivery_logs table")
        except Exception as e:
            print(f"Error adding date range columns: {e}")
        
        # Migration: Add email_config_id column if it doesn't exist
        try:
            # Check if the column exists
            async with db.execute("PRAGMA table_info(scheduled_research)") as cursor:
                columns = await cursor.fetchall()
                column_names = [column[1] for column in columns]
                
                if "email_config_id" not in column_names:
                    # Add the column
                    await db.execute("ALTER TABLE scheduled_research ADD COLUMN email_config_id INTEGER REFERENCES email_configs(id) ON DELETE SET NULL")
                    print("Added email_config_id column to scheduled_research table")
        except Exception as e:
            print(f"Error adding email_config_id column: {e}")
        
        await db.commit()

async def add_local_storage_job(job_id: str, prompt: str, model_name: str, server_name: str, server_type: str, filenames: list):
    """Adds a new local storage job."""
    now = datetime.now(ADELAIDE_TZ)
    filenames_json = json.dumps(filenames)
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO local_storage_jobs 
            (job_id, status, prompt, model_name, server_name, server_type, filenames, result, created_at, updated_at, processing_time_seconds) 
            VALUES (?, 'pending', ?, ?, ?, ?, ?, NULL, ?, ?, NULL)
            """,
            (job_id, prompt, model_name, server_name, server_type, filenames_json, now, now)
        )
        await db.commit()

async def update_local_storage_job(job_id: str, status: str, result: dict = None, processing_time: float = None):
    """Updates a local storage job's status and result."""
    now = datetime.now(ADELAIDE_TZ)
    result_json = json.dumps(result) if result else None
    async with aiosqlite.connect(DATABASE_FILE) as db:
        if processing_time is not None:
            await db.execute(
                """
                UPDATE local_storage_jobs 
                SET status = ?, result = ?, updated_at = ?, processing_time_seconds = ?
                WHERE job_id = ?
                """,
                (status, result_json, now, round(processing_time, 2), job_id)
            )
        else:
            await db.execute(
                "UPDATE local_storage_jobs SET status = ?, result = ?, updated_at = ? WHERE job_id = ?",
                (status, result_json, now, job_id)
            )
        await db.commit()

async def get_local_storage_job(job_id: str):
    """Retrieves a single local storage job from the database."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM local_storage_jobs WHERE job_id = ?", (job_id,)) as cursor:
            job = await cursor.fetchone()
            if job:
                job_dict = dict(job)
                if job_dict.get('result'):
                    job_dict['result'] = json.loads(job_dict['result'])
                if job_dict.get('filenames'):
                    job_dict['filenames'] = json.loads(job_dict['filenames'])
                return job_dict
            return None

async def get_all_local_storage_jobs():
    """Retrieves all local storage jobs from the database."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM local_storage_jobs ORDER BY created_at DESC") as cursor:
            jobs = await cursor.fetchall()
            job_list = []
            for job in jobs:
                job_dict = dict(job)
                if job_dict.get('result'):
                    job_dict['result'] = json.loads(job_dict['result'])
                if job_dict.get('filenames'):
                    job_dict['filenames'] = json.loads(job_dict['filenames'])
                job_list.append(job_dict)
            return job_list

async def delete_local_storage_job(job_id: str):
    """Deletes a local storage job from the database."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute("DELETE FROM local_storage_jobs WHERE job_id = ?", (job_id,))
        await db.commit()

async def initialize_external_ai_db():
    """Initializes the database and creates the external_ai_servers table if it doesn't exist."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS external_ai_servers (
                name TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                api_key TEXT NOT NULL
            )
        ''')
        await db.commit()

# --- Email Configuration Functions ---

async def add_email_config(smtp_server: str, smtp_port: int, username: str, password: str, sender_email: str, sender_name: str = None, use_tls: bool = True, use_ssl: bool = False):
    """Adds a new email configuration."""
    now = datetime.now(ADELAIDE_TZ)
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute(
            """
            INSERT INTO email_configs 
            (smtp_server, smtp_port, username, password, sender_email, sender_name, use_tls, use_ssl, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (smtp_server, smtp_port, username, password, sender_email, sender_name, use_tls, use_ssl, now, now)
        )
        await db.commit()

async def get_email_configs():
    """Retrieves all email configurations."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM email_configs ORDER BY created_at DESC") as cursor:
            configs = await cursor.fetchall()
            return [dict(row) for row in configs]

async def get_email_config(config_id: int):
    """Retrieves a single email configuration by ID."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM email_configs WHERE id = ?", (config_id,)) as cursor:
            config = await cursor.fetchone()
            if config:
                return dict(config)
            return None

async def update_email_config(config_id: int, smtp_server: str = None, smtp_port: int = None, username: str = None, password: str = None, sender_email: str = None, sender_name: str = None, use_tls: bool = None, use_ssl: bool = None):
    """Updates an email configuration."""
    now = datetime.now(ADELAIDE_TZ)
    async with aiosqlite.connect(DATABASE_FILE) as db:
        # Build dynamic query based on provided fields
        fields = []
        values = []
        
        if smtp_server is not None:
            fields.append("smtp_server = ?")
            values.append(smtp_server)
        if smtp_port is not None:
            fields.append("smtp_port = ?")
            values.append(smtp_port)
        if username is not None:
            fields.append("username = ?")
            values.append(username)
        if password is not None:
            fields.append("password = ?")
            values.append(password)
        if sender_email is not None:
            fields.append("sender_email = ?")
            values.append(sender_email)
        if sender_name is not None:
            fields.append("sender_name = ?")
            values.append(sender_name)
        if use_tls is not None:
            fields.append("use_tls = ?")
            values.append(use_tls)
        if use_ssl is not None:
            fields.append("use_ssl = ?")
            values.append(use_ssl)
            
        if fields:
            query = f"UPDATE email_configs SET {', '.join(fields)}, updated_at = ? WHERE id = ?"
            values.extend([now, config_id])
            await db.execute(query, values)
            await db.commit()

async def delete_email_config(config_id: int):
    """Deletes an email configuration."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute("DELETE FROM email_configs WHERE id = ?", (config_id,))
        await db.commit()

# --- Email Recipient Group Functions ---

async def add_email_recipient_group(name: str, description: str = None):
    """Adds a new email recipient group."""
    now = datetime.now(ADELAIDE_TZ)
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute(
            """
            INSERT INTO email_recipient_groups (name, description, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (name, description, now, now)
        )
        await db.commit()

async def get_email_recipient_groups():
    """Retrieves all email recipient groups."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM email_recipient_groups ORDER BY name") as cursor:
            groups = await cursor.fetchall()
            return [dict(row) for row in groups]

async def get_email_recipient_group(group_id: int):
    """Retrieves a single email recipient group by ID."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM email_recipient_groups WHERE id = ?", (group_id,)) as cursor:
            group = await cursor.fetchone()
            if group:
                return dict(group)
            return None

async def update_email_recipient_group(group_id: int, name: str = None, description: str = None):
    """Updates an email recipient group."""
    now = datetime.now(ADELAIDE_TZ)
    async with aiosqlite.connect(DATABASE_FILE) as db:
        # Build dynamic query based on provided fields
        fields = []
        values = []
        
        if name is not None:
            fields.append("name = ?")
            values.append(name)
        if description is not None:
            fields.append("description = ?")
            values.append(description)
            
        if fields:
            query = f"UPDATE email_recipient_groups SET {', '.join(fields)}, updated_at = ? WHERE id = ?"
            values.extend([now, group_id])
            await db.execute(query, values)
            await db.commit()

async def delete_email_recipient_group(group_id: int):
    """Deletes an email recipient group."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute("DELETE FROM email_recipient_groups WHERE id = ?", (group_id,))
        await db.commit()

# --- Email Recipient Functions ---

async def add_email_recipient(group_id: int, email: str, name: str = None):
    """Adds a new email recipient to a group."""
    now = datetime.now(ADELAIDE_TZ)
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute(
            """
            INSERT INTO email_recipients (group_id, email, name, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (group_id, email, name, now, now)
        )
        await db.commit()

async def get_email_recipients(group_id: int):
    """Retrieves all email recipients for a group."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM email_recipients WHERE group_id = ? ORDER BY email", (group_id,)) as cursor:
            recipients = await cursor.fetchall()
            return [dict(row) for row in recipients]

async def get_email_recipient(recipient_id: int):
    """Retrieves a single email recipient by ID."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM email_recipients WHERE id = ?", (recipient_id,)) as cursor:
            recipient = await cursor.fetchone()
            if recipient:
                return dict(recipient)
            return None

async def update_email_recipient(recipient_id: int, email: str = None, name: str = None):
    """Updates an email recipient."""
    now = datetime.now(ADELAIDE_TZ)
    async with aiosqlite.connect(DATABASE_FILE) as db:
        # Build dynamic query based on provided fields
        fields = []
        values = []
        
        if email is not None:
            fields.append("email = ?")
            values.append(email)
        if name is not None:
            fields.append("name = ?")
            values.append(name)
            
        if fields:
            query = f"UPDATE email_recipients SET {', '.join(fields)}, updated_at = ? WHERE id = ?"
            values.extend([now, recipient_id])
            await db.execute(query, values)
            await db.commit()

async def delete_email_recipient(recipient_id: int):
    """Deletes an email recipient."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute("DELETE FROM email_recipients WHERE id = ?", (recipient_id,))
        await db.commit()

# --- Scheduled Research Functions ---

async def add_scheduled_research(
    name: str, 
    frequency: str, 
    hour: int, 
    minute: int, 
    recipient_group_id: int, 
    date_range_days: int,
    description: str = None,
    day_of_week: int = None,
    day_of_month: int = None,
    start_date: str = None,
    end_date: str = None,
    model_name: str = None,
    server_name: str = None,
    server_type: str = None,
    email_config_id: int = None  # New parameter
):
    """Adds a new scheduled research configuration."""
    now = datetime.now(ADELAIDE_TZ)
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute(
            """
            INSERT INTO scheduled_research 
            (name, description, frequency, day_of_week, day_of_month, hour, minute, start_date, end_date,
             recipient_group_id, date_range_days, model_name, server_name, server_type, email_config_id,
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, description, frequency, day_of_week, day_of_month, hour, minute, start_date, end_date,
             recipient_group_id, date_range_days, model_name, server_name, server_type, email_config_id,
             now, now)
        )
        await db.commit()

async def get_scheduled_research_list():
    """Retrieves all scheduled research configurations."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT sr.*, erg.name as recipient_group_name, ec.smtp_server as email_config_smtp_server
            FROM scheduled_research sr
            LEFT JOIN email_recipient_groups erg ON sr.recipient_group_id = erg.id
            LEFT JOIN email_configs ec ON sr.email_config_id = ec.id
            ORDER BY sr.created_at DESC
        """) as cursor:
            research_list = await cursor.fetchall()
            return [dict(row) for row in research_list]

async def get_scheduled_research(research_id: int):
    """Retrieves a single scheduled research configuration by ID."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT sr.*, erg.name as recipient_group_name, ec.smtp_server as email_config_smtp_server
            FROM scheduled_research sr
            LEFT JOIN email_recipient_groups erg ON sr.recipient_group_id = erg.id
            LEFT JOIN email_configs ec ON sr.email_config_id = ec.id
            WHERE sr.id = ?
        """, (research_id,)) as cursor:
            research = await cursor.fetchone()
            if research:
                return dict(research)
            return None

async def update_scheduled_research(
    research_id: int,
    name: str = None,
    description: str = None,
    frequency: str = None,
    day_of_week: int = None,
    day_of_month: int = None,
    hour: int = None,
    minute: int = None,
    start_date: str = None,
    end_date: str = None,
    is_active: bool = None,
    recipient_group_id: int = None,
    date_range_days: int = None,
    model_name: str = None,
    server_name: str = None,
    server_type: str = None,
    email_config_id: int = None  # New parameter
):
    """Updates a scheduled research configuration."""
    now = datetime.now(ADELAIDE_TZ)
    async with aiosqlite.connect(DATABASE_FILE) as db:
        # Build dynamic query based on provided fields
        fields = []
        values = []
        
        if name is not None:
            fields.append("name = ?")
            values.append(name)
        if description is not None:
            fields.append("description = ?")
            values.append(description)
        if frequency is not None:
            fields.append("frequency = ?")
            values.append(frequency)
        if day_of_week is not None:
            fields.append("day_of_week = ?")
            values.append(day_of_week)
        if day_of_month is not None:
            fields.append("day_of_month = ?")
            values.append(day_of_month)
        if hour is not None:
            fields.append("hour = ?")
            values.append(hour)
        if minute is not None:
            fields.append("minute = ?")
            values.append(minute)
        if start_date is not None:
            fields.append("start_date = ?")
            values.append(start_date)
        if end_date is not None:
            fields.append("end_date = ?")
            values.append(end_date)
        if is_active is not None:
            fields.append("is_active = ?")
            values.append(is_active)
        if recipient_group_id is not None:
            fields.append("recipient_group_id = ?")
            values.append(recipient_group_id)
        if date_range_days is not None:
            fields.append("date_range_days = ?")
            values.append(date_range_days)
        if model_name is not None:
            fields.append("model_name = ?")
            values.append(model_name)
        if server_name is not None:
            fields.append("server_name = ?")
            values.append(server_name)
        if server_type is not None:
            fields.append("server_type = ?")
            values.append(server_type)
        if email_config_id is not None:  # New parameter
            fields.append("email_config_id = ?")
            values.append(email_config_id)
            
        if fields:
            query = f"UPDATE scheduled_research SET {', '.join(fields)}, updated_at = ? WHERE id = ?"
            values.extend([now, research_id])
            await db.execute(query, values)
            await db.commit()

async def delete_scheduled_research(research_id: int):
    """Deletes a scheduled research configuration."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute("DELETE FROM scheduled_research WHERE id = ?", (research_id,))
        await db.commit()

async def update_scheduled_research_run_times(research_id: int, last_run: datetime = None, next_run: datetime = None):
    """Updates the last run and next run times for a scheduled research."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        fields = []
        values = []
        
        if last_run is not None:
            fields.append("last_run = ?")
            values.append(last_run)
        if next_run is not None:
            fields.append("next_run = ?")
            values.append(next_run)
            
        if fields:
            query = f"UPDATE scheduled_research SET {', '.join(fields)} WHERE id = ?"
            values.append(research_id)
            await db.execute(query, values)
            await db.commit()

# --- Email Delivery Log Functions ---

async def add_email_delivery_log(
    scheduled_research_id: int,
    subject: str,
    recipients: list,
    status: str,
    sent_at: datetime = None,
    error_message: str = None,
    date_range_start: str = None,
    date_range_end: str = None
):
    """Adds a new email delivery log entry."""
    recipients_json = json.dumps(recipients)
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute(
            """
            INSERT INTO email_delivery_logs 
            (scheduled_research_id, subject, recipients, status, error_message, sent_at, date_range_start, date_range_end)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (scheduled_research_id, subject, recipients_json, status, error_message, sent_at, date_range_start, date_range_end)
        )
        await db.commit()

async def get_email_delivery_logs(scheduled_research_id: int = None, limit: int = 50):
    """Retrieves email delivery logs, optionally filtered by scheduled research ID."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        if scheduled_research_id:
            query = """
                SELECT * FROM email_delivery_logs 
                WHERE scheduled_research_id = ? 
                ORDER BY sent_at DESC 
                LIMIT ?
            """
            params = (scheduled_research_id, limit)
        else:
            query = "SELECT * FROM email_delivery_logs ORDER BY sent_at DESC LIMIT ?"
            params = (limit,)
            
        async with db.execute(query, params) as cursor:
            logs = await cursor.fetchall()
            result = []
            for log in logs:
                log_dict = dict(log)
                if log_dict.get('recipients'):
                    log_dict['recipients'] = json.loads(log_dict['recipients'])
                result.append(log_dict)
            return result
