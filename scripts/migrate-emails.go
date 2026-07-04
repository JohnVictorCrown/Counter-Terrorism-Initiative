// migrate-emails.go
// Port of migrate-emails.py — moves email column from leads to lead_emails table.
//
// Usage: go run scripts/migrate-emails.go

package main

import (
	"database/sql"
	"fmt"
	"net/url"
	"os"
	"path/filepath"
	"strings"

	_ "github.com/mutecomm/go-sqlcipher/v4"
)

const (
	dbPath  = "databases/leads.db"
	envPath = ".env"
)

func main() {
	fmt.Println("📧 Migration: Move emails to lead_emails table")
	fmt.Println()

	pw := loadDBPassword()
	if pw == "" {
		fmt.Fprintln(os.Stderr, "❌ EMAIL_DB_PASSWORD not found in .env")
		os.Exit(1)
	}

	db := openDB(pw)
	defer db.Close()

	// Check if lead_emails already exists
	var tableExists int
	err := db.QueryRow("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='lead_emails'").Scan(&tableExists)
	if err == nil && tableExists > 0 {
		fmt.Println("  lead_emails table already exists, skipping...")
		return
	}

	var total, withEmail int
	db.QueryRow("SELECT COUNT(*) FROM leads").Scan(&total)
	db.QueryRow("SELECT COUNT(*) FROM leads WHERE email IS NOT NULL AND email != ''").Scan(&withEmail)
	fmt.Printf("  Leads: %d, with email: %d\n", total, withEmail)

	// Check if email column exists
	var hasEmail bool
	err = db.QueryRow("SELECT COUNT(*) > 0 FROM pragma_table_info('leads') WHERE name = 'email'").Scan(&hasEmail)
	if err != nil {
		var schema string
		db.QueryRow("SELECT sql FROM sqlite_master WHERE type='table' AND name='leads'").Scan(&schema)
		hasEmail = strings.Contains(schema, "email")
	}
	if !hasEmail {
		fmt.Println("  Email column already removed from leads — nothing to migrate")
		// Still create the lead_emails table if it doesn't exist
		db.Exec(`CREATE TABLE IF NOT EXISTS lead_emails (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			lead_id TEXT NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
			email TEXT NOT NULL,
			is_primary INTEGER NOT NULL DEFAULT 0,
			created_at TEXT NOT NULL DEFAULT (datetime('now'))
		)`)
		fmt.Println("  Created lead_emails table (empty)")
		return
	}

	// Create lead_emails table
	_, err = db.Exec(`CREATE TABLE lead_emails (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		lead_id TEXT NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
		email TEXT NOT NULL,
		is_primary INTEGER NOT NULL DEFAULT 0,
		created_at TEXT NOT NULL DEFAULT (datetime('now'))
	)`)
	if err != nil {
		fmt.Fprintf(os.Stderr, "❌ Failed to create lead_emails: %v\n", err)
		os.Exit(1)
	}
	fmt.Println("  Created lead_emails table")

	// Migrate existing emails
	result, err := db.Exec(
		"INSERT INTO lead_emails (lead_id, email, is_primary) " +
		"SELECT id, email, 1 FROM leads WHERE email IS NOT NULL AND email != ''")
	if err != nil {
		fmt.Fprintf(os.Stderr, "❌ Failed to migrate emails: %v\n", err)
		os.Exit(1)
	}
	migrated, _ := result.RowsAffected()
	fmt.Printf("  Migrated %d emails to lead_emails\n", migrated)

	// Verify
	var count int
	db.QueryRow("SELECT COUNT(*) FROM lead_emails").Scan(&count)
	fmt.Printf("  Verification: %d emails in lead_emails table\n", count)

	// Drop email column
	_, err = db.Exec("ALTER TABLE leads DROP COLUMN email")
	if err != nil {
		fmt.Printf("  Note: Could not DROP COLUMN directly: %v\n", err)
		fmt.Println("  Using table recreation fallback...")
		fallbackDropEmail(db)
	} else {
		fmt.Println("  Dropped email column from leads table")
	}

	var finalLeads, finalEmails int
	db.QueryRow("SELECT COUNT(*) FROM leads").Scan(&finalLeads)
	db.QueryRow("SELECT COUNT(*) FROM lead_emails").Scan(&finalEmails)
	fmt.Printf("  Final: %d leads, %d emails\n", finalLeads, finalEmails)
	fmt.Println("\n✅ Migration complete!")
}

func fallbackDropEmail(db *sql.DB) {
	_, err := db.Exec(`CREATE TABLE leads_new (
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
	)`)
	if err != nil {
		fmt.Fprintf(os.Stderr, "❌ Fallback failed: %v\n", err)
		os.Exit(1)
	}

	_, err = db.Exec(`INSERT INTO leads_new
		(id, company, contact_name, phone, website, tier, type,
		 vertical, check_size, pitch_angle, status, next_action,
		 next_action_date, notes, source, created_at, updated_at)
		SELECT id, company, contact_name, phone, website, tier, type,
			vertical, check_size, pitch_angle, status, next_action,
			next_action_date, notes, source, created_at, updated_at
		FROM leads`)
	if err != nil {
		fmt.Fprintf(os.Stderr, "❌ Fallback copy failed: %v\n", err)
		os.Exit(1)
	}

	db.Exec("DROP TABLE leads")
	_, err = db.Exec("ALTER TABLE leads_new RENAME TO leads")
	if err != nil {
		fmt.Fprintf(os.Stderr, "❌ Fallback rename failed: %v\n", err)
		os.Exit(1)
	}
	fmt.Println("  Recreated leads table without email column")
}

func loadDBPassword() string {
	data, err := os.ReadFile(envPath)
	if err != nil {
		return ""
	}
	for _, line := range strings.Split(string(data), "\n") {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "EMAIL_DB_PASSWORD=") {
			val := strings.SplitN(line, "=", 2)[1]
			val = strings.Trim(val, `"' `)
			if val != "" {
				return val
			}
		}
	}
	return os.Getenv("EMAIL_DB_PASSWORD")
}

func openDB(password string) *sql.DB {
	absPath, err := filepath.Abs(dbPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "❌ Cannot resolve path: %v\n", err)
		os.Exit(1)
	}
	passphrase := fmt.Sprintf("x'%x'", []byte(password))
	dsn := fmt.Sprintf("%s?_pragma_key=%s&_pragma_journal_mode=WAL",
		absPath, url.QueryEscape(passphrase))
	db, err := sql.Open("sqlite3", dsn)
	if err != nil {
		fmt.Fprintf(os.Stderr, "❌ Failed to open database: %v\n", err)
		os.Exit(1)
	}
	var count int
	if err := db.QueryRow("SELECT COUNT(*) FROM sqlite_master").Scan(&count); err != nil {
		fmt.Fprintf(os.Stderr, "❌ Database decryption failed: %v\n", err)
		os.Exit(1)
	}
	return db
}
