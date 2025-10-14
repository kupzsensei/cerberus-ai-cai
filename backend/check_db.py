import sqlite3

# Connect to the database
conn = sqlite3.connect('tasks.db')
cursor = conn.cursor()

# Get all table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables in database:")
for table in tables:
    print(f"  - {table[0]}")

# Check if email_configs table exists and has data
if ('email_configs',) in tables:
    cursor.execute("SELECT COUNT(*) FROM email_configs;")
    count = cursor.fetchone()[0]
    print(f"\nEmail configs count: {count}")
    
    if count > 0:
        cursor.execute("SELECT * FROM email_configs;")
        configs = cursor.fetchall()
        print("Email configurations:")
        for config in configs:
            print(f"  - ID: {config[0]}, SMTP: {config[1]}, Port: {config[2]}, Username: {config[3]}, Sender: {config[5]}")
else:
    print("\nemail_configs table does not exist!")

conn.close()