#!/usr/bin/env python3
"""
WaterParty CRM — Python CLI for lead management & outreach tracking.

Uses a local SQLite database (leads.db) instead of CSV/plain-text files.
All contact data, email history, and pipeline state lives here.

Usage:
    python marketing/crm.py stats                    # Dashboard overview
    python marketing/crm.py list                     # All leads
    python marketing/crm.py list --tier 1            # Filter by tier
    python marketing/crm.py list --status cold       # Filter by status
    python marketing/crm.py list --search "Monashees" # Search
    python marketing/crm.py add                      # Interactive add
    python marketing/crm.py view <id>                # Lead detail
    python marketing/crm.py update <id>              # Interactive update
    python marketing/crm.py delete <id>              # Delete lead
    python marketing/crm.py status <id> <new_status> # Quick status change
    python marketing/crm.py log <id>                 # Log activity
    python marketing/crm.py followups                # Due follow-ups
    python marketing/crm.py import                   # Import from CSV
    python marketing/crm.py export                   # Export to CSV
"""

import sqlcipher3 as sqlite3
import sys
import os
import csv
from datetime import datetime, date
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "leads.db"
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

STATUSES = ["cold", "contacted", "replied", "meeting", "negotiating", "closed_won", "closed_lost"]
TIERS = {"1": "VC", "2": "Corporate", "3": "Local", "4": "Grant", "5": "Venue", "6": "Media"}


# ─── Database ────────────────────────────────────────────────────────────────

def load_db_password() -> str:
    """Read EMAIL_DB_PASSWORD from .env file."""
    if ENV_PATH.exists():
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if line.startswith("EMAIL_DB_PASSWORD="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    pw = os.environ.get("EMAIL_DB_PASSWORD")
    if pw:
        return pw
    print("ERROR: EMAIL_DB_PASSWORD not found in .env or environment")
    sys.exit(1)


def get_db():
    db_pw = load_db_password()
    db = sqlite3.connect(str(DB_PATH))
    hex_key = db_pw.encode().hex()
    db.execute(f"PRAGMA key=\"x'{hex_key}'\"")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    return db


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS leads (
            id TEXT PRIMARY KEY,
            company TEXT NOT NULL,
            contact_name TEXT DEFAULT '',
            email TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            website TEXT DEFAULT '',
            tier TEXT DEFAULT '3',
            type TEXT DEFAULT '',
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
        );
        CREATE TABLE IF NOT EXISTS outreach_log (
            id TEXT PRIMARY KEY,
            lead_id TEXT NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
            activity_type TEXT NOT NULL,
            notes TEXT DEFAULT '',
            outcome TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    db.commit()
    db.close()


# ─── CRUD ────────────────────────────────────────────────────────────────────

def add_lead(data: dict) -> str:
    import uuid
    lid = str(uuid.uuid4())
    db = get_db()
    db.execute(
        """INSERT INTO leads (id, company, contact_name, email, phone, website,
           tier, type, vertical, check_size, pitch_angle, status,
           next_action, next_action_date, notes, source)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (lid, data.get("company", ""), data.get("contact_name", ""),
         data.get("email", ""), data.get("phone", ""), data.get("website", ""),
         data.get("tier", "3"), data.get("type", ""), data.get("vertical", ""),
         data.get("check_size", ""), data.get("pitch_angle", ""),
         data.get("status", "cold"), data.get("next_action", ""),
         data.get("next_action_date", ""), data.get("notes", ""),
         data.get("source", ""))
    )
    db.commit()
    db.close()
    return lid


def get_leads(filters: dict = None) -> list:
    db = get_db()
    clauses = []
    params = []
    filters = filters or {}
    if filters.get("tier"):
        clauses.append("tier = ?"); params.append(filters["tier"])
    if filters.get("status"):
        if filters["status"] == "active":
            clauses.append("status NOT IN ('closed_won','closed_lost')")
        else:
            clauses.append("status = ?"); params.append(filters["status"])
    if filters.get("vertical"):
        clauses.append("vertical = ?"); params.append(filters["vertical"])
    if filters.get("type"):
        clauses.append("type = ?"); params.append(filters["type"])
    if filters.get("search"):
        s = f"%{filters['search']}%"
        clauses.append("(company LIKE ? OR contact_name LIKE ? OR email LIKE ?)")
        params.extend([s, s, s])
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = db.execute(f"SELECT * FROM leads {where} ORDER BY updated_at DESC", params).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_lead(lid: str) -> dict:
    db = get_db()
    row = db.execute("SELECT * FROM leads WHERE id = ?", (lid,)).fetchone()
    db.close()
    return dict(row) if row else None


def update_lead(lid: str, data: dict):
    fields = []
    params = []
    for key, val in data.items():
        if key in ("id", "created_at"):
            continue
        fields.append(f"{key} = ?")
        params.append(val)
    if not fields:
        return
    fields.append("updated_at = datetime('now')")
    params.append(lid)
    db = get_db()
    db.execute(f"UPDATE leads SET {', '.join(fields)} WHERE id = ?", params)
    db.commit()
    db.close()


def delete_lead(lid: str):
    db = get_db()
    db.execute("DELETE FROM outreach_log WHERE lead_id = ?", (lid,))
    db.execute("DELETE FROM leads WHERE id = ?", (lid,))
    db.commit()
    db.close()


# ─── Outreach ────────────────────────────────────────────────────────────────

def log_outreach(lid: str, activity_type: str, notes: str = "", outcome: str = ""):
    import uuid
    oid = str(uuid.uuid4())
    db = get_db()
    db.execute(
        "INSERT INTO outreach_log (id, lead_id, activity_type, notes, outcome) VALUES (?, ?, ?, ?, ?)",
        (oid, lid, activity_type, notes, outcome))
    db.commit()
    db.close()
    return oid


def get_outreach(lid: str) -> list:
    db = get_db()
    rows = db.execute(
        "SELECT * FROM outreach_log WHERE lead_id = ? ORDER BY created_at DESC", (lid,)).fetchall()
    db.close()
    return [dict(r) for r in rows]


# ─── Stats ───────────────────────────────────────────────────────────────────

def get_stats() -> dict:
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    by_tier = db.execute("SELECT tier, COUNT(*) FROM leads GROUP BY tier").fetchall()
    by_status = db.execute("SELECT status, COUNT(*) FROM leads GROUP BY status").fetchall()
    followups = db.execute(
        """SELECT COUNT(*) FROM leads WHERE next_action_date != ''
           AND next_action_date <= date('now')
           AND status NOT IN ('closed_won','closed_lost')"""
    ).fetchone()[0]
    recent = db.execute("SELECT * FROM leads ORDER BY created_at DESC LIMIT 5").fetchall()
    db.close()
    return {
        "total": total,
        "by_tier": [dict(tier=t, count=c) for t, c in by_tier],
        "by_status": [dict(status=s, count=c) for s, c in by_status],
        "followups_due": followups,
        "recent": [dict(r) for r in recent],
    }


# ─── Import / Export ─────────────────────────────────────────────────────────

def import_csv(csv_path: str) -> int:
    import uuid
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        db = get_db()
        for row in reader:
            company = (row.get("Company") or "").strip()
            if not company:
                continue
            lid = str(uuid.uuid4())
            db.execute(
                """INSERT INTO leads (id, company, contact_name, email, phone, website,
                   tier, type, vertical, check_size, pitch_angle, status,
                   next_action, next_action_date, notes, source)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (lid, company,
                 (row.get("Contact Name") or row.get("Contact") or "").strip(),
                 (row.get("Email") or row.get("Contact Email") or "").strip(),
                 (row.get("Phone") or "").strip(),
                 (row.get("Website") or "").strip(),
                 (row.get("Tier") or "3").strip()[0] if row.get("Tier") else "3",
                 (row.get("Type") or "").strip(),
                 (row.get("Vertical") or "").strip(),
                 (row.get("Check Size") or row.get("Check Size") or "").strip(),
                 (row.get("Our Angle") or row.get("Pitch Angle") or "").strip(),
                 "cold",
                 (row.get("Next Action") or "").strip(),
                 (row.get("Email Sent") or row.get("Email Sent (Date)") or "").strip(),
                 (row.get("Notes") or "").strip(),
                 "csv_import")
            )
            count += 1
        db.commit()
        db.close()
    return count


def export_csv(output_path: str):
    leads = get_leads()
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        if not leads:
            return
        writer = csv.DictWriter(f, fieldnames=leads[0].keys())
        writer.writeheader()
        writer.writerows(leads)
    print(f"Exported {len(leads)} leads to {output_path}")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def print_lead(lead: dict, verbose: bool = False):
    tier_label = TIERS.get(lead.get("tier", ""), f"Tier {lead['tier']}")
    print(f"  [{lead['id'][:8]}] {lead['company']}")
    print(f"         Contact: {lead.get('contact_name') or '-'}  |  {lead.get('email') or '-'}")
    print(f"         Tier: {tier_label}  |  Type: {lead.get('type') or '-'}  |  Vertical: {lead.get('vertical') or '-'}")
    print(f"         Status: {lead['status']}  |  Check: {lead.get('check_size') or '-'}")
    if lead.get("next_action"):
        print(f"         Next: {lead['next_action']}  ({lead.get('next_action_date') or 'no date'})")
    if verbose:
        print(f"         Website: {lead.get('website') or '-'}")
        print(f"         Phone: {lead.get('phone') or '-'}")
        print(f"         Pitch: {lead.get('pitch_angle') or '-'}")
        print(f"         Notes: {lead.get('notes') or '-'}")
        print(f"         Created: {lead['created_at']}  |  Updated: {lead['updated_at']}")
        outreach = get_outreach(lead["id"])
        if outreach:
            print(f"         Activity ({len(outreach)}):")
            for o in outreach[:5]:
                print(f"           [{o['created_at'][:10]}] {o['activity_type']}: {o.get('notes') or ''}")
    print()


def cmd_stats():
    s = get_stats()
    print(f"\n{'='*50}")
    print(f"  WATERPARTY CRM — DASHBOARD")
    print(f"{'='*50}")
    print(f"  Total leads:     {s['total']}")
    print(f"  Follow-ups due:  {s['followups_due']}")
    print()
    print("  By Tier:")
    for t in s["by_tier"]:
        label = TIERS.get(t["tier"], f"Tier {t['tier']}")
        print(f"    {label}: {t['count']}")
    print()
    print("  By Status:")
    for st in s["by_status"]:
        print(f"    {st['status']}: {st['count']}")
    print()
    if s["recent"]:
        print("  Recent:")
        for r in s["recent"]:
            print(f"    [{r['id'][:8]}] {r['company']} — {r['status']}")
    print()


def cmd_list(args):
    filters = {}
    if args.tier: filters["tier"] = args.tier
    if args.status: filters["status"] = args.status
    if args.search: filters["search"] = args.search
    if args.vertical: filters["vertical"] = args.vertical
    if args.type: filters["type"] = args.type
    leads = get_leads(filters)
    if not leads:
        print("No leads found.")
        return
    print(f"\n{len(leads)} lead(s):\n")
    for lead in leads:
        print_lead(lead, verbose=args.verbose)


def cmd_view(args):
    lead = get_lead(args.id)
    if not lead:
        print("Lead not found.")
        return
    print_lead(lead, verbose=True)
    outreach = get_outreach(args.id)
    if outreach:
        print(f"  All Activity ({len(outreach)}):")
        for o in outreach:
            print(f"    [{o['created_at']}] {o['activity_type']}: {o.get('notes') or ''}")
            if o.get("outcome"):
                print(f"      Outcome: {o['outcome']}")
    else:
        print("  No activity logged.")


def cmd_add(args=None):
    print("\nAdd new lead (press Enter to skip optional fields):")
    data = {}
    data["company"] = input("  Company *: ").strip()
    if not data["company"]:
        print("Company is required.")
        return
    data["contact_name"] = input("  Contact name: ").strip()
    data["email"] = input("  Email: ").strip()
    data["phone"] = input("  Phone: ").strip()
    data["website"] = input("  Website: ").strip()
    print("  Tier: 1=VC  2=Corporate  3=Local  4=Grant  5=Venue  6=Media")
    data["tier"] = input("  Tier [3]: ").strip() or "3"
    data["type"] = input("  Type (VC, Sponsor, Partner...): ").strip()
    data["vertical"] = input("  Vertical (fintech, beverage...): ").strip()
    data["check_size"] = input("  Check size: ").strip()
    data["pitch_angle"] = input("  Pitch angle: ").strip()
    data["next_action"] = input("  Next action: ").strip()
    data["next_action_date"] = input("  Next action date (YYYY-MM-DD): ").strip()
    data["notes"] = input("  Notes: ").strip()
    lid = add_lead(data)
    print(f"\nLead created: {lid}")


def cmd_update(args):
    lead = get_lead(args.id)
    if not lead:
        print("Lead not found.")
        return
    print(f"\nEditing: {lead['company']} (leave blank to keep current value)\n")
    fields = ["company", "contact_name", "email", "phone", "website",
              "tier", "type", "vertical", "check_size", "pitch_angle",
              "next_action", "next_action_date", "notes"]
    data = {}
    for f in fields:
        current = lead.get(f, "")
        val = input(f"  {f} [{current}]: ").strip()
        if val:
            data[f] = val
    if data:
        update_lead(args.id, data)
        print("Lead updated.")
    else:
        print("No changes.")


def cmd_delete(args):
    lead = get_lead(args.id)
    if not lead:
        print("Lead not found.")
        return
    confirm = input(f"Delete '{lead['company']}'? (y/N): ").strip().lower()
    if confirm == "y":
        delete_lead(args.id)
        print("Deleted.")


def cmd_status(args):
    if args.status not in STATUSES:
        print(f"Invalid status. Options: {', '.join(STATUSES)}")
        return
    update_lead(args.id, {"status": args.status})
    print(f"Status updated to '{args.status}'.")


def cmd_log(args):
    lead = get_lead(args.id)
    if not lead:
        print("Lead not found.")
        return
    print(f"\nLog activity for: {lead['company']}")
    print("Types: email, call, meeting, note")
    activity_type = input("  Type [email]: ").strip() or "email"
    notes = input("  Notes: ").strip()
    outcome = input("  Outcome: ").strip()
    log_outreach(args.id, activity_type, notes, outcome)
    print("Activity logged.")


def cmd_followups():
    leads = get_leads({"status": "active"})
    due = [l for l in leads if l.get("next_action_date") and l["next_action_date"] <= str(date.today())]
    if not due:
        print("No follow-ups due today.")
        return
    print(f"\n{len(due)} follow-up(s) due:\n")
    for lead in due:
        print(f"  [{lead['id'][:8]}] {lead['company']} — {lead.get('next_action') or 'No action'} ({lead['next_action_date']})")


def cmd_import(args):
    path = args.path or str(Path(__file__).resolve().parent / "crm-spreadsheet.csv")
    count = import_csv(path)
    print(f"Imported {count} leads.")


def cmd_export(args):
    path = args.path or str(Path(__file__).resolve().parent / "leads-export.csv")
    export_csv(path)


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    import argparse

    init_db()

    parser = argparse.ArgumentParser(description="WaterParty CRM")
    parser.add_argument("command", nargs="?", default="stats",
                        choices=["stats", "list", "view", "add", "update",
                                 "delete", "status", "log", "followups",
                                 "import", "export"])
    parser.add_argument("id", nargs="?", help="Lead ID")
    parser.add_argument("status", nargs="?", help="New status")
    parser.add_argument("--tier", help="Filter by tier")
    parser.add_argument("--status", dest="f_status", help="Filter by status")
    parser.add_argument("--vertical", help="Filter by vertical")
    parser.add_argument("--type", help="Filter by type")
    parser.add_argument("--search", help="Search")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--path", help="File path for import/export")

    args = parser.parse_args()

    cmd_map = {
        "stats": lambda: cmd_stats(),
        "list": lambda: cmd_list(args),
        "view": lambda: cmd_view(args),
        "add": lambda: cmd_add(args),
        "update": lambda: cmd_update(args),
        "delete": lambda: cmd_delete(args),
        "status": lambda: cmd_status(args),
        "log": lambda: cmd_log(args),
        "followups": lambda: cmd_followups(),
        "import": lambda: cmd_import(args),
        "export": lambda: cmd_export(args),
    }

    cmd_map.get(args.command, cmd_stats)()


if __name__ == "__main__":
    main()
