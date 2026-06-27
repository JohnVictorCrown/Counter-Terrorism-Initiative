#!/usr/bin/env python3
"""
store-password.py — One-time setup: store Gmail app password in SQLCipher-encrypted SQLite.

The entire database file is encrypted with a password from EMAIL_DB_PASSWORD in .env.
The Gmail app password is stored as plain text INSIDE this encrypted database.

Usage:
    python marketing/store-password.py --password "xxxx xxxx xxxx xxxx"

    Or omit --password for a secure prompt:
    python marketing/store-password.py
"""

import sys
from pathlib import Path

import sqlcipher3

DB_PATH = Path(__file__).resolve().parent / "mail-credentials.db"
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

GMAIL_ADDRESS = "water.enterprises.org@gmail.com"


def load_db_password() -> str:
    """Read EMAIL_DB_PASSWORD from .env file."""
    if not ENV_PATH.exists():
        print(f"❌ .env file not found at {ENV_PATH}")
        print("   Create it and add: EMAIL_DB_PASSWORD=\"your_password\"")
        sys.exit(1)

    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line.startswith("EMAIL_DB_PASSWORD="):
                value = line.split("=", 1)[1].strip().strip('"').strip("'")
                if value:
                    return value

    print("❌ EMAIL_DB_PASSWORD not found in .env")
    sys.exit(1)


def store_password(email: str, app_password: str):
    """Store the app password in a SQLCipher-encrypted database.

    The DB itself is encrypted with EMAIL_DB_PASSWORD.
    The app password is stored as plain text inside.
    """
    db_pw = load_db_password()
    db_path = DB_PATH

    # Connect with encryption — the entire DB file is AES-256 encrypted
    conn = sqlcipher3.connect(str(db_path))
    conn.execute(f"PRAGMA key=\"x'{db_pw.encode().hex()}'\"")
    conn.execute("PRAGMA journal_mode=WAL")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            app_password TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    conn.execute(
        "INSERT OR REPLACE INTO credentials (email, app_password) VALUES (?, ?)",
        (email, app_password),
    )
    conn.commit()
    conn.close()

    print(f"✅ App password stored in SQLCipher-encrypted database: {db_path}")
    print(f"   Database encryption password: EMAIL_DB_PASSWORD from .env")
    print(f"   App password stored in plain text inside the encrypted DB")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Store Gmail app password in SQLCipher-encrypted SQLite"
    )
    parser.add_argument(
        "--password",
        help="Gmail app password (omit to be prompted securely)",
    )
    args = parser.parse_args()

    print("🔐 WaterParty — Store Gmail App Password")
    print(f"   Account: {GMAIL_ADDRESS}")
    print(f"   Database: SQLCipher AES-256 encrypted")
    print()

    if args.password:
        print("⚠️  Warning: --password is visible in process listings and shell history.")
        print("   Consider omitting it next time for a secure prompt.")
        print()
        app_password = args.password
    else:
        import getpass
        app_password = getpass.getpass("Enter Gmail app password: ")
        if not app_password:
            print("❌ Password cannot be empty")
            sys.exit(1)

        confirm = getpass.getpass("Confirm password: ")
        if app_password != confirm:
            print("❌ Passwords do not match")
            sys.exit(1)

    store_password(GMAIL_ADDRESS, app_password)

    print()
    print("📬 You can now use: python marketing/send-mail.py")
    print("   --emails \"addr1@example.com,addr2@example.com\"")
    print("   --subject \"Your Subject\"")
    print("   --body \"Your email body text\"")


if __name__ == "__main__":
    main()
