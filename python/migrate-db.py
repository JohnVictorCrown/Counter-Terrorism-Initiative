#!/usr/bin/env python3
"""
migrate-db.py — Migrate SQLCipher databases from legacy v3 to v4 format.

Go's go-sqlcipher/v4 driver cannot read v3-format databases because it sets the
encryption key inside its Open() function using v4 defaults (SHA512/256K iterations)
before user code can set cipher_compatibility=3.

This script converts the databases to v4 format so Go can open them directly.

Strategy:
  1. Try PRAGMA cipher_migrate (in-place upgrade, if supported)
  2. Fallback: Create a new v4-format database and ATTACH+copy all data

Usage:
    python python/migrate-db.py
    python python/migrate-db.py --dry-run   # Preview without making changes
    python python/migrate-db.py --verbose   # Show detailed progress
"""

import os
import sys
import shutil
import tempfile
import argparse
from pathlib import Path

import sqlcipher3

# ─── Paths ────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASES_DIR = PROJECT_ROOT / "databases"
ENV_PATH = PROJECT_ROOT / ".env"

DATABASES = [
    {
        "name": "leads.db",
        "path": DATABASES_DIR / "leads.db",
        "verify_query": "SELECT COUNT(*) FROM leads",
        "verify_label": "leads",
    },
    {
        "name": "mail-credentials.db",
        "path": DATABASES_DIR / "mail-credentials.db",
        "verify_query": "SELECT COUNT(*) FROM credentials",
        "verify_label": "credential rows",
    },
]


def load_db_password() -> str:
    """Read EMAIL_DB_PASSWORD from .env file."""
    if not ENV_PATH.exists():
        print(f"❌ .env not found at {ENV_PATH}")
        print("   Create it with: EMAIL_DB_PASSWORD=\"your_password\"")
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


def open_with_v3_compat(db_path: Path, password: str):
    """Open a SQLCipher database using v3-compatible settings.

    This matches how Python's sqlcipher3 opens the database — by setting
    cipher_compatibility=3 BEFORE the key, so SQLCipher v4 derives the
    key using v3 defaults (SHA1, 64000 iterations).
    """
    conn = sqlcipher3.connect(str(db_path))
    conn.execute("PRAGMA cipher_compatibility = 3")
    conn.execute(f"PRAGMA key=\"x'{password.encode().hex()}'\"")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def open_with_v4_defaults(db_path: Path, password: str):
    """Open a SQLCipher database using v4 defaults (SHA512, 256K iterations).

    This is what Go's go-sqlcipher/v4 driver does inside its Open() function.
    """
    conn = sqlcipher3.connect(str(db_path))
    conn.execute(f"PRAGMA key=\"x'{password.encode().hex()}'\"")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def verify_db(conn, info: dict) -> bool:
    """Run a verification query and return True if data is readable."""
    try:
        c = conn.execute(info["verify_query"]).fetchone()
        count = c[0] if c else 0
        return True, count
    except Exception as e:
        return False, str(e)


def get_schema_sql(conn) -> list:
    """Get CREATE TABLE/INDEX statements from sqlite_master."""
    rows = conn.execute(
        "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND type IN ('table', 'index')"
    ).fetchall()
    return [r[0] for r in rows]


def migrate_via_attach(old_path: Path, new_path: Path, password: str, tables: list, verbose: bool) -> bool:
    """Migrate data by creating a new v4-format DB and ATTACH-copying all tables.

    Strategy:
      1. Open old DB with v3 compat (read-only) to get schema + verify access
      2. Create a new DB with v4 defaults
      3. From the new v4 connection, ATTACH the old DB with explicit v3 compat
      4. Copy data from attached old_db to main (new v4) schema
      5. Detach, verify new DB with v4 defaults
    """
    # Step 1: Open old DB with v3 compat to get schema
    if verbose:
        print(f"   Reading schema from old database...")
    old_conn = open_with_v3_compat(old_path, password)
    schema = get_schema_sql(old_conn)
    if verbose:
        print(f"   Found {len(schema)} schema statements")
    old_conn.close()

    # Step 2: Create new database with v4 defaults
    if verbose:
        print(f"   Creating new v4 database...")
    new_conn = sqlcipher3.connect(str(new_path))
    new_conn.execute(f"PRAGMA key=\"x'{password.encode().hex()}'\"")
    new_conn.execute("PRAGMA journal_mode=WAL")
    for stmt in schema:
        new_conn.execute(stmt)
    new_conn.commit()

    # Step 3: From new v4 connection, ATTACH old DB with v3 compat
    if verbose:
        print(f"   ATTACHing old database with v3 compatibility...")
    new_conn.execute(f"ATTACH DATABASE '{old_path}' AS old_db")
    # Set v3 compat BEFORE providing the key for the attached old DB
    new_conn.execute("PRAGMA old_db.cipher_compatibility = 3")
    new_conn.execute(f"PRAGMA old_db.key = \"x'{password.encode().hex()}'\"")

    # Step 4: Copy data from old to new
    if verbose:
        print(f"   Copying tables: {', '.join(tables)}")
    for table in tables:
        new_conn.execute(f"INSERT OR IGNORE INTO main.{table} SELECT * FROM old_db.{table}")
    new_conn.commit()
    new_conn.execute("DETACH DATABASE old_db")
    new_conn.close()

    if verbose:
        print(f"   Data copied successfully")
    return True


def try_cipher_migrate(db_path: Path, password: str, verbose: bool) -> bool:
    """Attempt in-place migration using PRAGMA cipher_migrate."""
    if verbose:
        print(f"   Trying PRAGMA cipher_migrate...")

    conn = open_with_v3_compat(db_path, password)

    try:
        conn.execute("PRAGMA cipher_migrate")
        conn.commit()
        if verbose:
            print(f"   ✅ PRAGMA cipher_migrate succeeded")
        conn.close()
        return True
    except Exception as e:
        if verbose:
            print(f"   ⚠️  PRAGMA cipher_migrate failed: {e}")
        conn.close()
        return False


def migrate_database(info: dict, password: str, dry_run: bool, verbose: bool) -> bool:
    """Migrate a single database to v4 format. Returns True on success."""
    db_path = info["path"]
    name = info["name"]

    print(f"\n{'─' * 60}")
    print(f"📁 {name}")

    if not db_path.exists():
        print(f"   ⚠️  Not found — skipping")
        return False

    # Step 1: Open with v3 compat and verify data is readable
    if verbose:
        print(f"   Opening with v3 compatibility...")

    try:
        conn = open_with_v3_compat(db_path, password)
        ok, result = verify_db(conn, info)
        if not ok:
            print(f"   ❌ Cannot read database with v3 compat: {result}")
            conn.close()
            return False

        old_count = result
        print(f"   📊 Contains {old_count} {info['verify_label']}")
        conn.close()
    except Exception as e:
        print(f"   ❌ Failed to open database: {e}")
        return False

    if dry_run:
        print(f"   🔍 DRY RUN — no changes made")
        return True

    # Step 2: Try PRAGMA cipher_migrate
    migrated = try_cipher_migrate(db_path, password, verbose)

    if not migrated:
        # Step 3: Fallback to ATTACH-based migration
        if verbose:
            print(f"   Using ATTACH-based migration fallback...")

        try:
            conn = open_with_v3_compat(db_path, password)
            # Get list of tables (excluding sqlite internal ones)
            conn2 = open_with_v3_compat(db_path, password)
            tables = [r[0] for r in conn2.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()]
            conn2.close()

            if not tables:
                print(f"   ⚠️  No tables found in database")
                return False

            # Create temp file for new v4 database
            fd, tmp_path = tempfile.mkstemp(
                suffix=f"-{name}", dir=str(DATABASES_DIR)
            )
            os.close(fd)
            tmp_path = Path(tmp_path)

            if verbose:
                print(f"   Creating new v4 database at {tmp_path.name}...")
                print(f"   Copying tables: {', '.join(tables)}")

            migrate_via_attach(db_path, tmp_path, password, tables, verbose)

            # Verify the new database is readable with v4 defaults
            if verbose:
                print(f"   Verifying new database with v4 defaults...")

            new_conn = open_with_v4_defaults(tmp_path, password)
            ok, result = verify_db(new_conn, info)
            new_conn.close()

            if not ok:
                print(f"   ❌ New database verification failed: {result}")
                tmp_path.unlink(missing_ok=True)
                return False

            new_count = result
            print(f"   ✅ New v4 database verified: {new_count} {info['verify_label']}")

            # Replace old file with new
            backup_path = db_path.with_suffix(".db.bak")
            if backup_path.exists():
                backup_path.unlink()

            shutil.move(str(db_path), str(backup_path))
            shutil.move(str(tmp_path), str(db_path))

            print(f"   ✅ Replaced {name} with v4-format copy")
            print(f"   📦 Old file backed up as {backup_path.name}")

        except Exception as e:
            print(f"   ❌ Migration failed: {e}")
            return False
    else:
        # Verify the migrated database is readable with v4 defaults
        if verbose:
            print(f"   Verifying migrated database with v4 defaults...")

        try:
            conn = open_with_v4_defaults(db_path, password)
            ok, result = verify_db(conn, info)
            conn.close()

            if ok:
                new_count = result
                print(f"   ✅ v4 format verified: {new_count} {info['verify_label']}")
            else:
                print(f"   ⚠️  Migrated but verification gave: {result}")
        except Exception as e:
            print(f"   ⚠️  Migrated but v4 open gave: {e}")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Migrate SQLCipher databases from v3 to v4 format"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview what would be done without making changes"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show detailed progress"
    )
    args = parser.parse_args()

    print("🔐 WaterParty — SQLCipher Database Migration")
    print(f"{'=' * 60}")

    password = load_db_password()

    if args.dry_run:
        print("\n🔍 DRY RUN MODE — no changes will be made\n")
    else:
        print(f"\n📦 Backups will be saved with .db.bak extension\n")

    success_count = 0
    for db_info in DATABASES:
        ok = migrate_database(db_info, password, args.dry_run, args.verbose)
        if ok:
            success_count += 1

    print(f"\n{'=' * 60}")
    print(f"📊 Results: {success_count}/{len(DATABASES)} databases migrated")
    if args.dry_run:
        print("🔍 This was a dry run. Run without --dry-run to apply changes.")
    print(f"\n✅ Migration complete")
    print(f"   Run 'make migrate' again if you need to re-migrate after restoring backups.")


if __name__ == "__main__":
    main()
