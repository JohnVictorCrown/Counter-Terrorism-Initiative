"""
Migration: Move email column from leads table to a separate lead_emails table.
Creates lead_emails table, migrates existing emails, drops email column from leads.
"""

import sqlcipher3
import sys

def main():
    pw = open('.env').read().split('EMAIL_DB_PASSWORD=')[1].split()[0].strip('"\' \n\r')
    conn = sqlcipher3.connect('databases/leads.db')
    conn.execute('PRAGMA cipher_compatibility = 3')
    conn.execute(f'PRAGMA key="x\'{pw.encode().hex()}\'"')
    conn.execute('PRAGMA journal_mode=WAL')

    # Check current state
    r = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='lead_emails'").fetchone()
    if r:
        print("lead_emails table already exists, skipping...")
        conn.close()
        return

    total = conn.execute('SELECT COUNT(*) FROM leads').fetchone()[0]
    with_email = conn.execute("SELECT COUNT(*) FROM leads WHERE email != '' AND email IS NOT NULL").fetchone()[0]
    print(f"Leads: {total}, with email: {with_email}")

    # Create lead_emails table
    conn.execute('''
        CREATE TABLE lead_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id TEXT NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
            email TEXT NOT NULL,
            is_primary INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    ''')
    print("Created lead_emails table")

    # Migrate existing emails
    migrated = conn.execute(
        "INSERT INTO lead_emails (lead_id, email, is_primary) "
        "SELECT id, email, 1 FROM leads WHERE email != '' AND email IS NOT NULL"
    ).rowcount
    print(f"Migrated {migrated} emails to lead_emails")

    # Verify
    count = conn.execute('SELECT COUNT(*) FROM lead_emails').fetchone()[0]
    print(f"Verification: {count} emails in lead_emails table")

    # Drop email column from leads (SQLite 3.35+ supports ALTER TABLE DROP COLUMN)
    try:
        conn.execute("ALTER TABLE leads DROP COLUMN email")
        print("Dropped email column from leads table")
    except Exception as e:
        print(f"Note: Could not DROP COLUMN directly: {e}")
        # Fallback: recreate leads table without email
        print("Using table recreation fallback...")
        conn.execute('''
            CREATE TABLE leads_new (
                id TEXT PRIMARY KEY,
                company TEXT NOT NULL,
                contact_name TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                website TEXT DEFAULT '',
                tier TEXT DEFAULT '3',
                type TEXT NOT NULL DEFAULT '',
                vertical TEXT DEFAULT '',
                check_size TEXT DEFAULT '',
                pitch_angle TEXT DEFAULT '',
                status TEXT DEFAULT 'cold',
                next_action TEXT DEFAULT '',
                next_action_date TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                source TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        ''')
        conn.execute('''
            INSERT INTO leads_new (id, company, contact_name, phone, website, tier, type,
                vertical, check_size, pitch_angle, status, next_action, next_action_date,
                notes, source, created_at, updated_at)
            SELECT id, company, contact_name, phone, website, tier, type,
                vertical, check_size, pitch_angle, status, next_action, next_action_date,
                notes, source, created_at, updated_at FROM leads
        ''')
        conn.execute('DROP TABLE leads')
        conn.execute('ALTER TABLE leads_new RENAME TO leads')
        print("Recreated leads table without email column")

    final_leads = conn.execute('SELECT COUNT(*) FROM leads').fetchone()[0]
    final_emails = conn.execute('SELECT COUNT(*) FROM lead_emails').fetchone()[0]
    print(f"Final: {final_leads} leads, {final_emails} emails")

    conn.commit()
    conn.close()
    print("\n✅ Migration complete!")

if __name__ == '__main__':
    main()
