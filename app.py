#!/usr/bin/env python3
"""
CRM Web Dashboard — Flask app for browsing & searching all CRM contacts.
"""

import sqlcipher3
import os
import re
import smtplib
import ssl
from email.mime.text import MIMEText
from pathlib import Path
from flask import Flask, render_template, request, jsonify

# ─── Social Media Parser ───────────────────────────────────────────
SOCIAL_PLATFORMS = {
    "x/twitter": {"name": "X", "icon": "𝕏", "url": "https://x.com/"},
    "twitter": {"name": "Twitter", "icon": "𝕏", "url": "https://x.com/"},
    "x": {"name": "X", "icon": "𝕏", "url": "https://x.com/"},
    "instagram": {"name": "Instagram", "icon": "📷", "url": "https://instagram.com/"},
    "facebook": {"name": "Facebook", "icon": "📘", "url": "https://facebook.com/"},
    "youtube": {"name": "YouTube", "icon": "▶️", "url": "https://youtube.com/"},
    "linkedin": {"name": "LinkedIn", "icon": "💼", "url": "https://linkedin.com/company/"},
    "tiktok": {"name": "TikTok", "icon": "🎵", "url": "https://tiktok.com/@"},
    "telegram": {"name": "Telegram", "icon": "✈️", "url": "https://t.me/"},
    "whatsapp": {"name": "WhatsApp", "icon": "💬", "url": "https://wa.me/"},
}

def parse_social_media(notes):
    """Extract social media handles from the 'Social:' section of notes."""
    if not notes or "Social:" not in notes:
        return []
    
    idx = notes.index("Social:")
    social_text = notes[idx + 7:]
    # Stop at next meaningful section or end of string
    for sep in ["\n\n", "  \n", "\n- ", "\n* "]:
        if sep in social_text:
            social_text = social_text.split(sep)[0]
    # Split on period only if followed by space (to avoid breaking URLs with dots)
    parts = re.split(r'\.\s+', social_text, maxsplit=1)
    social_text = parts[0].strip()
    
    # Guard: check if it says "no social media" or similar
    if re.search(r'\b(no|none|not|n\'t)\b', social_text[:60].lower()):
        return []
    
    results = []
    # Find all platform-handle pairs using a more flexible pattern
    # Matches: "Platform @handle", "Platform: @handle", "Platform/Sub @handle", "Platform handle"
    pattern = r'([A-Za-z][A-Za-z/]+)\s*(?::\s*)?@?([A-Za-z0-9][A-Za-z0-9_.\-@/]+?)(?=[,\s]*(?:[A-Za-z][A-Za-z/]+\s*(?::\s*)?@|$))'
    
    matches = re.finditer(pattern, social_text)
    for m in matches:
        platform_raw = m.group(1).strip().lower()
        handle = m.group(2).strip().lstrip('@')
        
        # Skip if handle looks like a sentence word (too short or common word)
        if len(handle) < 2 or handle.lower() in ['the', 'and', 'for', 'are', 'via', 'using']:
            continue
            
        matched = False
        for key, info in SOCIAL_PLATFORMS.items():
            # Check if platform key matches
            key_parts = key.split('/')
            if any(kp in platform_raw or platform_raw in kp for kp in key_parts):
                full_url = info["url"] + handle
                if key == "youtube" and not handle.startswith("@"):
                    full_url = info["url"] + "@" + handle
                results.append({
                    "platform": info["name"],
                    "icon": info["icon"],
                    "handle": handle,
                    "url": full_url,
                })
                matched = True
                break
        
        if not matched:
            # Maybe it's a full URL
            if handle.startswith("http"):
                results.append({
                    "platform": platform_raw.title(),
                    "icon": "🔗",
                    "handle": handle,
                    "url": handle,
                })
    
    return results

app = Flask(__name__)

DB_PATH = Path(__file__).resolve().parent / "leads.db"
MAIL_DB_PATH = Path(__file__).resolve().parent / "mail-credentials.db"
ENV_PATH = Path(__file__).resolve().parent / ".env"

GMAIL_ADDRESS = "water.enterprises.org@gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

def load_db_password():
    if ENV_PATH.exists():
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if line.startswith("EMAIL_DB_PASSWORD="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    pw = os.environ.get("EMAIL_DB_PASSWORD")
    if pw:
        return pw
    return ""

def load_app_password() -> str:
    """Load the Gmail app password from the encrypted mail-credentials.db."""
    db_pw = load_db_password()
    conn = sqlcipher3.connect(str(MAIL_DB_PATH))
    hex_key = db_pw.encode().hex()
    conn.execute('PRAGMA key="x\'' + hex_key + '\'"')
    cursor = conn.execute(
        "SELECT app_password FROM credentials WHERE email = ? ORDER BY id DESC LIMIT 1",
        (GMAIL_ADDRESS,),
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return row[0]

from contextlib import contextmanager

@contextmanager
def get_db():
    pw = load_db_password()
    db = sqlcipher3.connect(str(DB_PATH))
    db.execute("PRAGMA key=\"x'%s'\"" % pw.encode().hex())
    db.row_factory = sqlcipher3.Row
    try:
        yield db
    finally:
        db.close()


# ─── API Routes ──────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stats")
def api_stats():
    with get_db() as db:
        total = db.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        
        by_vertical = []
        for r in db.execute("SELECT COALESCE(vertical, 'Unknown') as v, COUNT(*) as cnt FROM leads GROUP BY v ORDER BY cnt DESC LIMIT 10").fetchall():
            by_vertical.append({"name": r["v"], "count": r["cnt"]})
        
        by_type = []
        for r in db.execute("SELECT COALESCE(type, 'Unknown') as t, COUNT(*) as cnt FROM leads GROUP BY t ORDER BY cnt DESC").fetchall():
            by_type.append({"name": r["t"], "count": r["cnt"]})
        
        by_source = []
        for r in db.execute("SELECT COALESCE(source, 'Unknown') as s, COUNT(*) as cnt FROM leads GROUP BY s ORDER BY cnt DESC").fetchall():
            by_source.append({"name": r["s"], "count": r["cnt"]})
        
        with_email = db.execute("SELECT COUNT(*) FROM leads WHERE email IS NOT NULL AND email != ''").fetchone()[0]
        with_phone = db.execute("SELECT COUNT(*) FROM leads WHERE phone IS NOT NULL AND phone != ''").fetchone()[0]
        with_website = db.execute("SELECT COUNT(*) FROM leads WHERE website IS NOT NULL AND website != ''").fetchone()[0]
        with_social = db.execute("SELECT COUNT(*) FROM leads WHERE notes LIKE '%Social:%'").fetchone()[0]
    
    return jsonify({
        "total": total,
        "by_vertical": by_vertical,
        "by_type": by_type,
        "by_source": by_source,
        "with_email": with_email,
        "with_phone": with_phone,
        "with_website": with_website,
        "with_social": with_social,
    })


@app.route("/api/contacts")
def api_contacts():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    search = request.args.get("search", "").strip()
    vertical = request.args.get("vertical", "").strip()
    contact_type = request.args.get("type", "").strip()
    source = request.args.get("source", "").strip()
    sort_by = request.args.get("sort_by", "company")
    sort_dir = request.args.get("sort_dir", "asc")
    
    allowed_sorts = ["company", "type", "vertical", "source", "phone", "email", "website", "status"]
    if sort_by not in allowed_sorts:
        sort_by = "company"
    sort_dir_sql = "ASC" if sort_dir != "desc" else "DESC"
    
    clauses = []
    params = []
    
    if search:
        s = f"%{search}%"
        clauses.append("(company LIKE ? OR email LIKE ? OR phone LIKE ? OR website LIKE ? OR notes LIKE ? OR contact_name LIKE ?)")
        params.extend([s, s, s, s, s, s])
    
    if vertical:
        clauses.append("vertical = ?")
        params.append(vertical)
    
    if contact_type:
        clauses.append("type = ?")
        params.append(contact_type)
    
    if source:
        clauses.append("source = ?")
        params.append(source)
    
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    
    with get_db() as db:
        count_row = db.execute(f"SELECT COUNT(*) FROM leads {where}", params).fetchone()
        total = count_row[0]
        
        offset = (page - 1) * per_page
        rows = db.execute(
            f"SELECT id, company, contact_name, email, phone, website, type, vertical, source, status, notes FROM leads {where} ORDER BY {sort_by} {sort_dir_sql} LIMIT ? OFFSET ?",
            params + [per_page, offset]
        ).fetchall()
        
        contacts = []
        for r in rows:
            c = {k: r[k] for k in r.keys()}
            c["social"] = parse_social_media(r["notes"]) if r["notes"] else []
            if c.get("notes") and len(c["notes"]) > 120:
                c["notes"] = c["notes"][:120] + "..."
            contacts.append(c)
    
    return jsonify({
        "contacts": contacts,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, (total + per_page - 1) // per_page),
    })


@app.route("/api/contacts/<contact_id>")
def api_contact_detail(contact_id):
    with get_db() as db:
        row = db.execute("SELECT * FROM leads WHERE id = ?", (contact_id,)).fetchone()
    if not row:
        return jsonify({"error": "Not found"}), 404
    result = {k: row[k] for k in row.keys()}
    result["social"] = parse_social_media(row["notes"]) if row["notes"] else []
    return jsonify(result)


@app.route("/api/filters")
def api_filters():
    with get_db() as db:
        verticals = []
        types = []
        sources = []
        
        for r in db.execute("SELECT DISTINCT COALESCE(vertical, 'Unknown') as v FROM leads ORDER BY v").fetchall():
            if r["v"] and r["v"] != "Unknown":
                verticals.append(r["v"])
        
        for r in db.execute("SELECT DISTINCT COALESCE(type, 'Unknown') as t FROM leads WHERE type IS NOT NULL AND type != '' ORDER BY t").fetchall():
            types.append(r["t"])
        
        for r in db.execute("SELECT DISTINCT COALESCE(source, 'Unknown') as s FROM leads WHERE source IS NOT NULL AND source != '' ORDER BY s").fetchall():
            sources.append(r["s"])
    
    return jsonify({"verticals": verticals, "types": types, "sources": sources})


@app.route("/api/send-email", methods=["POST"])
def api_send_email():
    """Send an email to a contact via Gmail SMTP."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    contact_id = data.get("contact_id", "").strip()
    subject = data.get("subject", "").strip()
    body = data.get("body", "").strip()
    custom_email = data.get("email", "").strip()

    if not subject or not body:
        return jsonify({"error": "Subject and body are required"}), 400

    # Resolve recipient email
    to_email = custom_email
    if not to_email and contact_id:
        with get_db() as db:
            row = db.execute("SELECT email, company FROM leads WHERE id = ?", (contact_id,)).fetchone()
        if not row:
            return jsonify({"error": "Contact not found"}), 404
        to_email = row["email"] if row["email"] else ""

    if not to_email:
        return jsonify({"error": "No email address provided or found for this contact"}), 400

    # Validate email format
    if to_email.count("@") != 1 or "." not in to_email.split("@")[1]:
        return jsonify({"error": f"Invalid email address: {to_email}"}), 400

    # Load Gmail password
    password = load_app_password()
    if not password:
        return jsonify({"error": "Gmail app password not found. Run store-password.py first."}), 500

    # Build and send the email
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = f"John Victor @ WaterParty <{GMAIL_ADDRESS}>"
    msg["To"] = to_email
    msg["Subject"] = subject

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(GMAIL_ADDRESS, password)
            server.sendmail(GMAIL_ADDRESS, [to_email], msg.as_string())

        return jsonify({"success": True, "to": to_email, "subject": subject})

    except smtplib.SMTPAuthenticationError:
        return jsonify({"error": "SMTP authentication failed. Gmail app password may need updating."}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to send email: {str(e)}"}), 500


@app.route("/api/send-bulk-email", methods=["POST"])
def api_send_bulk_email():
    """Send a bulk email to multiple recipients via BCC."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    emails = data.get("emails", [])
    subject = data.get("subject", "").strip()
    body = data.get("body", "").strip()

    if not isinstance(emails, list) or len(emails) == 0:
        return jsonify({"error": "At least one email is required"}), 400
    if not subject or not body:
        return jsonify({"error": "Subject and body are required"}), 400

    # Validate emails
    valid_emails = []
    for e in emails:
        e = e.strip()
        if e.count("@") == 1 and "." in e.split("@")[1]:
            valid_emails.append(e)

    if not valid_emails:
        return jsonify({"error": "No valid email addresses"}), 400

    password = load_app_password()
    if not password:
        return jsonify({"error": "Gmail app password not found. Run store-password.py first."}), 500

    # Build email with BCC
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = f"John Victor @ WaterParty <{GMAIL_ADDRESS}>"
    msg["To"] = GMAIL_ADDRESS
    msg["Subject"] = subject
    msg["Bcc"] = ", ".join(valid_emails)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(GMAIL_ADDRESS, password)
            server.sendmail(GMAIL_ADDRESS, valid_emails, msg.as_string())

        return jsonify({"success": True, "sent": len(valid_emails), "subject": subject})

    except smtplib.SMTPAuthenticationError:
        return jsonify({"error": "SMTP authentication failed. Gmail app password may need updating."}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to send email: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
