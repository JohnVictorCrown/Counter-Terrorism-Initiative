# Counter-Terrorism Initiative — Agents & Systems

A decentralized intelligence coordination and lead management platform. Built for human rights defenders tracking security, government, and civil society contacts across Latin America.

**WaterParty CRM** is the official CRM tool within this initiative — a Go-based CLI and web dashboard for managing 662+ contacts across 3 tiers.

---

## 🧠 System Architecture

```
┌─────────────────────────────────────────────┐
│              USER INTERFACES                  │
│  ┌──────────────┐  ┌──────────────────┐      │
│  │ Go CLI       │  │ Web Dashboard    │      │
│  │ (crm.exe)    │  │ (dashboard.exe)  │      │
│  └──────┬───────┘  └──────┬───────────┘      │
│         │                 │                  │
│         └─────────────────┼──────────────────┘
│                           │
│                    ┌──────▼──────┐
│                    │  DB LAYER   │
│                    │  (SQLCipher)│
│                    │  AES-256    │
│                    └──────┬──────┘
│                           │
│              ┌────────────┴────────────┐
│              │                         │
│     ┌────────▼────────┐     ┌─────────▼───────┐
│     │  leads.db       │     │ mail-credentials│
│     │  (662 contacts) │     │ .db (accounts)  │
│     └─────────────────┘     └─────────────────┘
└─────────────────────────────────────────────────┘
```

**Stack:** Go 1.25+, Fiber v2, SQLCipher v4 AES-256, HTML/CSS/JS dashboard

---

## 1. CRM CLI (`cmd/crm/main.go`)

**Role:** Primary command-line interface for all lead management, outreach, and email operations.

### Commands

| Command | Purpose |
|---------|---------|
| `stats` | Dashboard overview (totals, tiers, statuses, data quality) |
| `list` | Filterable lead listing |
| `view <id>` | Lead detail + outreach history |
| `add` | Interactive lead creation |
| `update <id>` | Field-level updates |
| `delete <id>` | Remove lead + cascade outreach logs |
| `status <id> <s>` | Quick status change |
| `log <id>` | Log email/call/meeting/note |
| `followups` | Due follow-ups (past due date) |
| `import --path` | CSV import with column mapping |
| `export --path` | CSV export |
| `store-password` | Set Gmail app password (secure prompt) |
| `send-mail` | BCC email with attachments |
| `run-dashboard` | Launch web dashboard + open browser |
| `send-telegram` | Push email campaign to Telegram |

### Dependencies
- `internal/db/` — All CRUD operations
- `internal/mail/` — SMTP email sending
- `golang.org/x/term` — Secure password input

---

## 2. Web Dashboard (`cmd/dashboard/main.go`)

**Role:** Real-time web UI for contact management, email campaigns, and reporting.

**Stack:** Fiber v2 (Go), HTML templates, CSS, Vanilla JS

### API Endpoints (`/api/`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/stats` | GET | Aggregated statistics with data quality metrics |
| `/api/contacts` | GET | Paginated, filterable, sortable list |
| `/api/contacts/:id` | GET | Single contact + social parse |
| `/api/filters` | GET | Distinct verticals, types, sources |
| `/api/export-csv` | GET | CSV download with filters |
| `/api/export-selected-csv` | POST | CSV of checked rows |
| `/api/send-email` | POST | Single email (JSON or FormData) |
| `/api/send-bulk-email` | POST | BCC to multiple recipients |
| `/api/email-log` | GET | Email history by contact |

### Pages

| Route | Purpose |
|-------|---------|
| `/` | SPA dashboard (search, filter, select, compose) |
| `/report` | Print-friendly report with charts |

### Frontend Features
- Dark theme UI
- Real-time search with debounce
- Multi-select with bulk action bar (email, CSV export)
- Inline compose modal with file attachment
- Email history timeline
- Sortable columns
- Print-ready report page

---

## 3. Database Layer (`internal/db/db.go`)

**Role:** All database interaction — encrypted with SQLCipher AES-256. ~620 lines of Go.

### Key Functions

| Function | Purpose |
|----------|---------|
| `openDB(path)` | Connect with `_pragma_key` DSN |
| `GetDB()` | Open `leads.db` |
| `GetStats()` | Aggregated stats (tiers, statuses, data quality) |
| `GetContact(id)` | Single lead detail |
| `ListContacts(filter)` | Paginated, filtered, sorted list |
| `GetLeads(filter)` | Full lead list with filters |
| `AddLead(input)` | Create new lead (UUID) |
| `UpdateLead(id, data)` | Partial update |
| `DeleteLead(id)` | Remove + cascade outreach_log |
| `LogOutreach(id, type, notes, outcome)` | Log activity |
| `GetOutreach(id)` | Activity history |
| `GetFollowupsDue()` | Past-due follow-ups |
| `LoadAppPassword()` | Read Gmail password from `mail-credentials.db` |
| `StoreAppPassword(email, pw)` | Write Gmail password |
| `LogEmail(...)` | Record sent email in outreach_log |
| `GetEmailLog(id, limit)` | Email history |
| `GetFilters()` | Distinct verticals/types/sources |
| `ExportCSV(filter)` | Filtered CSV export |
| `ExportSelectedCSV(ids)` | Selected-row CSV export |
| `GetReportData(filter)` | Report data with chart items |
| `LoadEnvVar(key)` | Read `.env` or env vars |
| `GetContactEmail(id)` | Quick email + company lookup |

### Tables

**`leads`** — 18 columns
| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | UUID |
| `company` | TEXT | Organization name |
| `contact_name` | TEXT | Primary contact |
| `email` | TEXT | Email address |
| `phone` | TEXT | Phone number |
| `website` | TEXT | Website URL |
| `tier` | TEXT | 1=VC, 2=Corporate, 3=Local, 4=Grant, 5=Venue, 6=Media |
| `type` | TEXT | Organization type (NGO, VC, etc.) |
| `vertical` | TEXT | Country/region/topic |
| `check_size` | TEXT | Funding check size |
| `pitch_angle` | TEXT | Outreach pitch |
| `status` | TEXT | Pipeline status (cold → emailed → replied → etc.) |
| `next_action` | TEXT | Follow-up action |
| `next_action_date` | TEXT | Due date (YYYY-MM-DD) |
| `notes` | TEXT | Free text + `Social:` entries |
| `source` | TEXT | Import source |
| `created_at` | TEXT | Auto timestamp |
| `updated_at` | TEXT | Auto timestamp |

**`outreach_log`** — 6 columns
| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | UUID |
| `lead_id` | TEXT | FK to leads.id |
| `activity_type` | TEXT | email, call, meeting, note |
| `notes` | TEXT | Activity details |
| `outcome` | TEXT | Result/sent status |
| `created_at` | TEXT | Auto timestamp |

**`credentials`** — 4 columns (in `mail-credentials.db`)
| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment |
| `email` | TEXT UNIQUE | Gmail address |
| `app_password` | TEXT | Gmail app password |
| `created_at` | TEXT | Auto timestamp |

### Security
- Connection via DSN: `path?_pragma_key=<encoded>&_pragma_journal_mode=WAL`
- Password read from `.env` at runtime
- Key format: `PRAGMA key = "x'hex_encoded_password'"`
- Database is SQLCipher v4 (SHA512/256K KDF iterations)

---

## 4. SMTP Mail Sender (`internal/mail/sender.go`)

**Role:** Send emails via Gmail SMTP with optional attachments.

### Functions

| Function | Purpose |
|----------|---------|
| `SendEmail(to, subject, body, fileData, fileName)` | Single email with optional attachment |
| `SendBulkEmail(emails, subject, body)` | BCC to list of recipients |
| `SendMailCLI(recipients, subject, body, fromName, attachments)` | CLI email with multipart MIME |

### Security
- TLS 1.2+ on port 587
- App password stored encrypted in `mail-credentials.db`
- 20MB attachment limit
- Email validation before sending

---

## 5. HTTP API Handlers (`internal/handlers/api.go`)

**Role:** Bridge between Fiber HTTP and database/mail layers.

### Key Features
- JSON API with error wrapping
- Form-data support for file uploads
- BCC bulk sending with async logging
- CSV export with BOM for Excel compatibility
- Social media link extraction from notes
- Pagination with total/totalPages metadata

---

## 6. Page Handlers (`internal/handlers/pages.go`)

**Role:** Server-side HTML rendering for non-API routes.

- `Index` — Serves SPA shell (`templates/index.html`)
- `GetReport` — Renders print-friendly report with chart data, truncates long notes

---

## 7. Data Models (`internal/models/types.go`)

**Role:** Type definitions shared across all subsystems.

### Types
`Contact`, `LeadInput`, `Stats`, `NameCount`, `ChartItem`, `ContactsResponse`, `FiltersResponse`, `OutreachLog`, `EmailLogResponse`, `SendEmailRequest`, `SendBulkEmailRequest`, `ExportSelectedRequest`, `ReportData`, `SocialEntry`

### Constants
- `ValidTypes` — 15 org types (Military, Law Enforcement, Intelligence, State Police, Security, Government, Homeland Security, Defense, Human Rights NGO, Anti-Torture Org, Government HR Body, International HR Body, Humanitarian Org, Legal Defense, Faith-Based HR)
- `Statuses` — 7 pipeline stages (cold, contacted, replied, meeting, negotiating, closed_won, closed_lost)
- `TierLabels` — 6 tier labels (VC, Corporate, Local, Grant, Venue, Media)

---

## 8. Social Media Parser (`internal/social/parser.go`)

**Role:** Extract social media links from unstructured notes text.

### Platforms Parsed
X/Twitter, Instagram, Facebook, YouTube, LinkedIn, TikTok, Telegram, WhatsApp

### Pattern
Looks for `Social:` prefix in notes, then parses `Platform: @handle` pairs using regex.

### Output
Returns `SocialEntry` structs with Platform, Icon, Handle, and URL for each found entry.

---

## 📊 Data Stores

### `databases/leads.db` — 662 Contacts

| Dimension | Count |
|-----------|-------|
| **Tier 1 (VC)** | 63 |
| **Tier 2 (Corporate)** | 251 |
| **Tier 3 (Local)** | 348 |
| **Status** | All 662 are "cold" |
| **With email** | ~Varies — reported in stats |
| **With phone** | ~Varies — reported in stats |
| **With website** | ~Varies — reported in stats |
| **With social entries** | ~Varies — reported in stats |
| **Emails sent** | Tracked in outreach_log |

**Encryption:** SQLCipher AES-256 (v4, SHA512/256K KDF)

### `databases/mail-credentials.db` — 1 Account

| Column | Value |
|--------|-------|
| Email | `john.victor.crown@gmail.com` |
| App Password | Encrypted in DB |
| Rows | 2 (history) |

**Encryption:** Same SQLCipher AES-256 (v4)

### `.env` — Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `EMAIL_DB_PASSWORD` | ✅ Yes | Database encryption key |
| `TELEGRAM_BOT_TOKEN` | ❌ Optional | Telegram bot for campaign push |
| `TELEGRAM_CHAT_ID` | ❌ Optional | Telegram chat destination |

---

## 🔄 Workflows

### Lead Lifecycle
```
CSV Import → Add Lead (cold) → Contact via email → 
Log Outreach → Update Status → Follow-up → 
Negotiate → Close Won / Close Lost
```

### Email Campaign Flow
```
Dashboard → Select Contacts → Compose Email →
BCC via Gmail SMTP → Log to outreach_log →
Update Stats → Track replies
```

### Telegram Campaign Flow
```
crm send-telegram → Build campaign message →
POST to Telegram Bot API → 
Message delivered to configured chat
```

---

## 🛠️ Build System (Makefile)

| Target | Action |
|--------|--------|
| `make` | Build both binaries (CGO_ENABLED=1) |
| `make crm` | Build `crm.exe` |
| `make dashboard` | Build `dashboard.exe` |
| `make run-crm ARGS="stats"` | Run CRM via `go run` |
| `make run-dashboard` | Run dashboard via `go run` |
| `make vet` | `go vet` all packages |
| `make clean` | Remove built binaries |
| `make help` | Show all targets |

### Variables
- `CGO_ENABLED=1` — Enable CGO (required for SQLCipher)
- `CGO_ENABLED=0` — Disable CGO (pure-Go only, no DB access)
- `ARGS="stats"` — Arguments for `run-crm`

**Dependency:** GCC/MinGW-w64 required for CGO (SQLCipher). Install via Chocolatey.

---

## ⚡ Quick Reference

```powershell
make                              # Build everything (requires GCC)
.\crm.exe stats                    # Dashboard stats (662 leads)
.\dashboard.exe                    # Web UI at http://localhost:5000
.\crm.exe store-password           # Set up Gmail app password
.\crm.exe send-mail --emails "a@b" --subject "Hi" --body "Hello"   # Send email
```

### First-Time Setup
1. Create `.env` with `EMAIL_DB_PASSWORD`
2. Install GCC: `choco install mingw -y`
3. `make` — build Go binaries
4. `.\crm.exe stats` — verify 662 leads
5. `.\dashboard.exe` — launch web UI

---

## 🔐 Security Model

| Layer | Protection |
|-------|-----------|
| **Databases** | AES-256 at rest (SQLCipher v4) |
| **Passwords** | Never in code — `.env` only (gitignored) |
| **Email Auth** | App password stored encrypted in `mail-credentials.db` |
| **SMTP** | TLS 1.2+ on port 587 |
| **Key Derivation** | SHA512 / 256K PBKDF2 iterations |
| **Key Format** | `PRAGMA key = "x'hex_encoded_password'"` via DSN `_pragma_key` |
| **CGO Required** | SQLCipher binds to C library — binary won't decrypt without GCC |

---

## 📁 Project Map

```
Counter-Terrorism Initiative/
├── cmd/
│   ├── crm/          main.go              # Go CLI binary (15 commands)
│   └── dashboard/    main.go              # Go web server (Fiber, :5000)
├── internal/
│   ├── db/           db.go                # SQLCipher DB layer (20+ functions)
│   ├── handlers/     api.go, pages.go     # HTTP handlers + server-side render
│   ├── mail/         sender.go            # Gmail SMTP with attachments
│   ├── models/       types.go             # Data types + constants
│   └── social/       parser.go            # Social link extraction from notes
├── databases/
│   ├── leads.db                           # 662 encrypted contacts
│   └── mail-credentials.db                # Encrypted Gmail credentials
├── templates/        index.html, report.html
├── static/           style.css
├── .env                                   # EMAIL_DB_PASSWORD (gitignored)
├── Makefile                               # Build automation
├── agents.md                              # This file
└── README.md                              # Full documentation
```
