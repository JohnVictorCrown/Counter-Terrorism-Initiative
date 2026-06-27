#!/usr/bin/env python3
"""
send-mail.py — Send BCC emails via Gmail SMTP using credentials from SQLCipher-encrypted DB.

The Gmail app password is stored as plain text inside a SQLCipher-encrypted SQLite database.
The database encryption password comes from EMAIL_DB_PASSWORD in .env.

Usage:
    python marketing/send-mail.py \
        --emails "addr1@example.com,addr2@example.com" \
        --subject "Your Subject" \
        --body "Your email body text"

    python marketing/send-mail.py \
        --emails "addr1@example.com" \
        --subject "Pitch" \
        --body-file marketing/email-pitch-prospects.txt \
        --attach marketing/pitch-deck.pdf

Options:
    --emails      Comma-separated list of BCC recipients (required)
    --subject     Email subject line (required)
    --body        Email body text (required unless --body-file used)
    --body-file   Read email body from a text file
    --attach      File to attach (can be used multiple times)
    --from-name   Display name for sender (default: "John Victor @ WaterParty")
    --dry-run     Print what would be sent without actually sending
    --confirm     Show recipients and ask for confirmation before sending
"""

import argparse
import mimetypes
import smtplib
import ssl
import sys
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.encoders import encode_base64
from pathlib import Path

import sqlcipher3

DB_PATH = Path(__file__).resolve().parent / "mail-credentials.db"
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

GMAIL_ADDRESS = "water.enterprises.org@gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_TIMEOUT = 30


def load_db_password() -> str:
    """Read EMAIL_DB_PASSWORD from .env file."""
    if not ENV_PATH.exists():
        print(f"❌ .env file not found at {ENV_PATH}")
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


def load_app_password() -> str:
    """Open the SQLCipher-encrypted DB and read the plain-text app password."""
    if not DB_PATH.exists():
        print(f"❌ Credentials DB not found at {DB_PATH}")
        print("   Run: python marketing/store-password.py")
        sys.exit(1)

    db_pw = load_db_password()

    try:
        conn = sqlcipher3.connect(str(DB_PATH))
        hex_key = db_pw.encode().hex()
        conn.execute('PRAGMA key="x\'' + hex_key + '\'"')

        cursor = conn.execute(
            "SELECT app_password FROM credentials WHERE email = ? ORDER BY id DESC LIMIT 1",
            (GMAIL_ADDRESS,),
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            print(f"❌ No credentials found for {GMAIL_ADDRESS}")
            print("   Run: python marketing/store-password.py")
            sys.exit(1)

        return row[0]

    except sqlcipher3.DatabaseError as e:
        if "file is not a database" in str(e) or "decryption" in str(e).lower():
            print(f"❌ Failed to decrypt database. EMAIL_DB_PASSWORD may be wrong.")
            print("   Run: python marketing/store-password.py to recreate the DB")
            sys.exit(1)
        raise


def attach_file(msg: MIMEMultipart, file_path: str) -> None:
    """Attach a file to the email message."""
    path = Path(file_path)
    if not path.exists():
        print(f"❌ Attachment not found: {path}")
        sys.exit(1)

    content_type, encoding = mimetypes.guess_type(str(path))
    if content_type is None:
        content_type = "application/octet-stream"

    main_type, sub_type = content_type.split("/", 1)

    with open(path, "rb") as f:
        attachment = MIMEBase(main_type, sub_type)
        attachment.set_payload(f.read())
        encode_base64(attachment)

    attachment.add_header(
        "Content-Disposition",
        "attachment",
        filename=path.name,
    )
    msg.attach(attachment)


def send_email(
    bcc_recipients: list[str],
    subject: str,
    body: str,
    from_name: str = "John Victor @ WaterParty",
    attachments: list[str] | None = None,
    dry_run: bool = False,
) -> int:
    """Send an email with BCC to the given recipients, optionally with attachments."""
    password = load_app_password()

    msg = MIMEMultipart("mixed")
    msg["From"] = f"{from_name} <{GMAIL_ADDRESS}>"
    msg["To"] = GMAIL_ADDRESS
    msg["Subject"] = subject

    # Attach the body as alternative (plain text)
    body_part = MIMEMultipart("alternative")
    body_part.attach(MIMEText(body, "plain", "utf-8"))
    msg.attach(body_part)

    # Attach files if provided
    if attachments:
        for fpath in attachments:
            attach_file(msg, fpath)

    if dry_run:
        print("\n🔍 DRY RUN — No email sent")
        print(f"   From:       {from_name} <{GMAIL_ADDRESS}>")
        print(f"   Subject:    {subject}")
        print(f"   BCC ({len(bcc_recipients)}): {', '.join(bcc_recipients)}")
        if attachments:
            for fpath in attachments:
                fsize = Path(fpath).stat().st_size
                print(f"   Attach:     {fpath} ({fsize / 1024:.1f} KB)")
        print(f"   Body:\n{body}\n")
        return len(bcc_recipients)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=SMTP_TIMEOUT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(GMAIL_ADDRESS, password)
            server.sendmail(GMAIL_ADDRESS, bcc_recipients, msg.as_string())

        attach_info = ""
        if attachments:
            attach_info = f" with {len(attachments)} attachment(s)"
        print(f"✅ Email sent to {len(bcc_recipients)} recipients via BCC{attach_info}")
        print(f"   Subject: {subject}")
        return len(bcc_recipients)

    except smtplib.SMTPAuthenticationError:
        print("❌ SMTP authentication failed. Check your Gmail app password.")
        print("   If it changed, run: python marketing/store-password.py")
        sys.exit(1)
    except smtplib.SMTPRecipientsRefused as e:
        print(f"❌ Some recipients were refused: {e}")
        sys.exit(1)
    except TimeoutError:
        print(f"❌ Connection timed out after {SMTP_TIMEOUT}s. Check your internet.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        sys.exit(1)


def validate_email(email: str) -> bool:
    """Simple email validation."""
    email = email.strip()
    if email.count("@") != 1:
        return False
    local, domain = email.split("@")
    if not local or not domain:
        return False
    if "." not in domain:
        return False
    if " " in email:
        return False
    return True


def main():
    """Parse CLI args and send the email."""
    parser = argparse.ArgumentParser(
        description="Send BCC emails via Gmail SMTP using SQLCipher-encrypted credentials.",
    )
    parser.add_argument("--emails", required=True,
                        help="Comma-separated list of BCC recipient email addresses")
    parser.add_argument("--subject", required=True, help="Email subject line")
    parser.add_argument("--body", help="Email body text (required unless --body-file is used)")
    parser.add_argument("--body-file", help="Read email body from a text file")
    parser.add_argument("--attach", action="append", default=[],
                        help="File to attach (can be used multiple times)")
    parser.add_argument("--from-name", default="John Victor @ WaterParty",
                        help="Display name for sender (default: John Victor @ WaterParty)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be sent without actually sending")
    parser.add_argument("--confirm", action="store_true",
                        help="Show recipients and ask for confirmation before sending")

    args = parser.parse_args()

    if args.body and args.body_file:
        print("❌ Use either --body or --body-file, not both")
        sys.exit(1)

    if args.body_file:
        body_file = Path(args.body_file)
        if not body_file.exists():
            print(f"❌ Body file not found: {body_file}")
            sys.exit(1)
        body = body_file.read_text(encoding="utf-8")
    elif args.body:
        body = args.body
    else:
        print("❌ Either --body or --body-file is required")
        sys.exit(1)

    recipients = [e.strip() for e in args.emails.split(",") if e.strip()]
    if not recipients:
        print("❌ No valid email addresses provided")
        sys.exit(1)

    invalid = [r for r in recipients if not validate_email(r)]
    if invalid:
        print(f"❌ Invalid email addresses: {', '.join(invalid)}")
        sys.exit(1)

    attachments = args.attach if args.attach else None

    if args.confirm:
        print(f"\n📧 Ready to send to {len(recipients)} recipients via BCC:")
        for r in recipients:
            print(f"   • {r}")
        print(f"\n   Subject: {args.subject}")
        if attachments:
            for fpath in attachments:
                fsize = Path(fpath).stat().st_size
                print(f"   Attach:    {fpath} ({fsize / 1024:.1f} KB)")
        preview = body[:100].replace("\n", " ")
        print(f"   Body preview: {preview}...")
        confirm = input("\n   Send? (y/N): ").strip().lower()
        if confirm != "y":
            print("❌ Cancelled")
            sys.exit(0)

    send_email(
        bcc_recipients=recipients,
        subject=args.subject,
        body=body,
        from_name=args.from_name,
        attachments=attachments,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
