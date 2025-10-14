import sqlite3

# Connect to the database
conn = sqlite3.connect('tasks.db')
cursor = conn.cursor()

# Check scheduled research configurations
cursor.execute('SELECT * FROM scheduled_research LIMIT 5;')
scheduled_research = cursor.fetchall()
print('Scheduled research configs:')
for sr in scheduled_research:
    print(f'  ID: {sr[0]}, Name: {sr[1]}, Email Config ID: {sr[14] if len(sr) > 14 else "N/A"}')

print()

# Check email configs
cursor.execute('SELECT id FROM email_configs;')
email_configs = cursor.fetchall()
print(f'Email config IDs in DB: {[ec[0] for ec in email_configs]}')

conn.close()