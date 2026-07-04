"""Check current database state"""
import sqlcipher3

pw = open('.env').read().split('EMAIL_DB_PASSWORD=')[1].split()[0].strip('"\' \n\r')
conn = sqlcipher3.connect('databases/leads.db')
conn.execute('PRAGMA cipher_compatibility = 3')
conn.execute(f'PRAGMA key="x\'{pw.encode().hex()}\'"')

tables = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
for name, sql in tables:
    print(f"=== {name} ===")
    for line in sql.split('\n'):
        print(f"  {line.strip()}")
    print()

total = conn.execute('SELECT COUNT(*) FROM leads').fetchone()[0]
print(f"leads rows: {total}")

try:
    c = conn.execute('SELECT COUNT(*) FROM lead_emails').fetchone()[0]
    print(f"lead_emails rows: {c}")
except Exception as e:
    print(f"lead_emails: does not exist ({e})")

# Check if email column still exists
try:
    conn.execute('SELECT email FROM leads LIMIT 1')
    print("email column on leads: YES (still exists)")
except:
    print("email column on leads: NO (already dropped)")

conn.close()
