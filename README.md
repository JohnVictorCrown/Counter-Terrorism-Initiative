# WaterParty CRM — Counter-Terrorism Initiative

A CRM system for lead management, outreach tracking, and email campaigns, with an encrypted SQLite database backend. Available as a **Go CLI**, a **Go web dashboard**, and **Python scripts**.

## 📁 Project Structure

```
├── cmd/
│   ├── crm/          # Go CRM CLI binary
│   └── dashboard/    # Go web dashboard binary (Fiber)
├── internal/
│   ├── db/           # Database layer (SQLCipher encryption)
│   ├── handlers/     # HTTP API handlers
│   ├── mail/         # SMTP email sending
│   ├── models/       # Data models
│   └── social/       # Social media parser
├── python/           # Python scripts (alternative to Go)
│   ├── app.py        # Flask web dashboard
│   ├── crm.py        # Python CRM CLI
│   ├── send-mail.py  # Send BCC emails
│   └── store-password.py  # Store Gmail app password
├── databases/
│   ├── leads.db      # Encrypted CRM database (SQLCipher AES-256)
│   └── mail-credentials.db  # Encrypted mail credentials
├── templates/        # HTML templates for the dashboard
├── static/           # Static assets (CSS, JS)
├── .env              # Environment variables (EMAIL_DB_PASSWORD, etc.)
├── Makefile          # Build automation
└── README.md         # This file
```

## 🔐 Requirements

### Go Binaries (recommended)

- **Go 1.25+** — [go.dev/dl](https://go.dev/dl)
- **GCC (MinGW-w64)** — Required for SQLCipher CGO support

  Install in PowerShell **as Administrator**:
  ```powershell
  # Via Chocolatey
  Set-ExecutionPolicy Bypass -Scope Process -Force
  iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))
  choco install mingw -y
  ```

  Or download from: [MinGW-w64](https://github.com/niXman/mingw-builds-binaries/releases)

### Python Scripts (alternative)

- **Python 3.10+**
- **SQLCipher** — Install with:
  ```powershell
  pip install sqlcipher3
  ```
- Flask (for dashboard only):
  ```powershell
  pip install flask
  ```

## 🚀 Quick Start

### 1. Set up environment

Create a `.env` file in the project root:
```ini
EMAIL_DB_PASSWORD="your_strong_password"
TELEGRAM_BOT_TOKEN="your_bot_token"      # Optional — for Telegram campaigns
TELEGRAM_CHAT_ID="your_chat_id"          # Optional — for Telegram campaigns
```

### 2. Build Go binaries

With GCC installed, run:
```powershell
cd "C:\Users\John Victor\Documents\Development\Counter-Terrorism Initiative"
make
```

Or manually:
```powershell
$env:CGO_ENABLED=1
go build -o crm.exe ./cmd/crm/
go build -o dashboard.exe ./cmd/dashboard/
```

### 3. View CRM stats

```powershell
.\crm.exe stats
```

### 4. Launch the web dashboard

```powershell
.\dashboard.exe
```

Open **http://localhost:5000** in your browser.

## 📖 Usage

### CRM CLI (`crm.exe`)

```powershell
.\crm.exe stats                         # Dashboard overview
.\crm.exe list                          # All leads
.\crm.exe list --tier 1                 # Filter by tier
.\crm.exe list --status cold            # Filter by status
.\crm.exe list --search "Monashees"     # Search contacts
.\crm.exe view <id>                     # Lead detail
.\crm.exe add                           # Interactive add
.\crm.exe update <id>                   # Interactive update
.\crm.exe delete <id>                   # Delete lead
.\crm.exe status <id> <new_status>      # Quick status change
.\crm.exe log <id>                      # Log activity
.\crm.exe followups                     # Due follow-ups
.\crm.exe import --path file.csv        # Import from CSV
.\crm.exe export --path file.csv        # Export to CSV
```

### Email Sending

```powershell
# Store Gmail app password first (one-time)
.\crm.exe store-password

# Send email
.\crm.exe send-mail --emails "addr@example.com" --subject "Hi" --body "Hello"

# With file attachment
.\crm.exe send-mail --emails "a@b.com,c@d.com" --subject "Pitch" ^
    --body "See attached" --attach "deck.pdf,budget.xlsx"

# Dry run (preview without sending)
.\crm.exe send-mail --emails "a@b.com" --subject "Hi" --body "Hello" --dry-run

# Confirm before sending
.\crm.exe send-mail --emails "a@b.com" --subject "Hi" --body "Hello" --confirm

# Read body from file
.\crm.exe send-mail --emails "a@b.com" --subject "Hi" --body-file body.txt
```

### Dashboard

```powershell
# Via built binary
.\dashboard.exe

# Via go run (no build needed)
go run ./cmd/dashboard/

# Via CRM CLI launcher
.\crm.exe run-dashboard
```

### Python Scripts (alternative)

Run from the project root:
```powershell
python python/crm.py stats              # CRM stats
python python/app.py                    # Flask dashboard at http://localhost:5000
python python/store-password.py          # Store Gmail app password
python python/send-mail.py --emails "a@b.com" --subject "Hi" --body "Hello"
```

## 🔧 Makefile Commands

```powershell
make                  # Build both crm.exe + dashboard.exe (default)
make crm              # Build crm.exe only
make dashboard        # Build dashboard.exe only
make run-crm ARGS="stats"     # Run CRM via 'go run'
make run-dashboard            # Run dashboard via 'go run'
make vet                      # Run go vet on all packages
make clean                    # Remove built binaries
make help                     # Show help
```

### Make Variables

```powershell
make CGO_ENABLED=1    # Enable CGO (default, required for SQLCipher)
make CGO_ENABLED=0    # Disable CGO (pure-Go only, no DB decryption)
```

## 🗃️ Database

Both `leads.db` and `mail-credentials.db` are **SQLCipher AES-256 encrypted** SQLite databases. They are stored in the `databases/` folder.

- **Encryption key**: `EMAIL_DB_PASSWORD` from `.env` file
- **Cipher**: AES-256-CBC (SQLCipher v3 compatible)
- **KDF**: PBKDF2-HMAC-SHA1, 64000 iterations

The databases were created by Python's `sqlcipher3` library (SQLCipher v3). When opening with Go's `go-sqlcipher/v4`, it must first set `PRAGMA cipher_compatibility = 3` before setting the encryption key.

## 🐛 Troubleshooting

### "C compiler 'gcc' not found" / CGO Error

```
Error: pragma key: Binary was compiled with 'CGO_ENABLED=0', go-sqlite3 requires cgo
```

**Fix**: Install MinGW-w64 and rebuild:
```powershell
choco install mingw -y
$env:CGO_ENABLED=1; go build -o crm.exe ./cmd/crm/
```

### Dashboard shows empty page / no data loads

1. Check that `dashboard.exe` was built with CGO enabled (see above)
2. Ensure `.env` has the correct `EMAIL_DB_PASSWORD`
3. Verify `databases/leads.db` exists and has data:
   ```powershell
   python -c "import sqlcipher3; pw=open('.env').read().split('EMAIL_DB_PASSWORD=')[1].split()[0].strip(); conn=sqlcipher3.connect('databases/leads.db'); conn.execute('PRAGMA key=\"x\\'%s\\'\"' % pw.encode().hex()); print(conn.execute('SELECT COUNT(*) FROM leads').fetchone()[0], 'leads'); conn.close()"
   ```
4. Kill any old dashboard process and restart:
   ```powershell
   taskkill /F /IM dashboard.exe 2>$null
   .\dashboard.exe
   ```

### "file is not a database" / HMAC check failed

The encryption password in `.env` may not match the one used to create the database, or the database was created by a different version of SQLCipher. Recreate the database from the Python scripts.

## 📬 Sending Email via Gmail

1. Generate a Gmail app password:
   - Go to https://myaccount.google.com/apppasswords
   - Create an app password for "Mail"
2. Store it:
   ```powershell
   .\crm.exe store-password
   ```
3. Send emails through the dashboard or CLI.

## 🔒 Security Notes

- Database files (.db) are AES-256 encrypted at rest with your `EMAIL_DB_PASSWORD`
- The Gmail app password is stored encrypted inside the database
- Never commit `.env` or `.db` files to version control
- The `--password` flag on the CLI may be visible in process listings
