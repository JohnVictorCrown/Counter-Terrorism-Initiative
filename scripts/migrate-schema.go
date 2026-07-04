// migrate-schema.go
// Port of migrate-schema.py — adds UNIQUE(company, email) constraint and makes type NOT NULL.
//
// Usage: go run scripts/migrate-schema.go
//
// This script works on the current database schema (with lead_emails table).
// It removes the old UNIQUE(company, email) on leads (since email moved to lead_emails)
// and ensures type is NOT NULL.

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
	fmt.Println("🔧 Schema Migration: enforce type NOT NULL + UNIQUE constraints")
	fmt.Println()

	// Load password
	pw := loadDBPassword()
	if pw == "" {
		fmt.Fprintln(os.Stderr, "❌ EMAIL_DB_PASSWORD not found in .env")
		os.Exit(1)
	}

	// Open database
	db := openDB(dbPath, pw)
	defer db.Close()

	// Verify current state
	var total int
	db.QueryRow("SELECT COUNT(*) FROM leads").Scan(&total)
	fmt.Printf("  Current leads: %d\n", total)

	// Check for null/empty types
	var nullTypes int
	db.QueryRow("SELECT COUNT(*) FROM leads WHERE type IS NULL OR type = ''").Scan(&nullTypes)
	if nullTypes > 0 {
		fmt.Printf("  Setting default type for %d rows with empty type...\n", nullTypes)
		if _, err := db.Exec("UPDATE leads SET type = 'Unknown' WHERE type IS NULL OR type = ''"); err != nil {
			fmt.Fprintf(os.Stderr, "❌ Failed to update null types: %v\n", err)
			os.Exit(1)
		}
		fmt.Println("  ✅ Done")
	} else {
		fmt.Println("  No null types found — good")
	}

	// Check for duplicate (company, email) pairs (only relevant on old schema with email column)
	var hasEmailCol bool
	if err := db.QueryRow("SELECT COUNT(*) > 0 FROM pragma_table_info('leads') WHERE name = 'email'").Scan(&hasEmailCol); err != nil {
		var schema string
		db.QueryRow("SELECT sql FROM sqlite_master WHERE type='table' AND name='leads'").Scan(&schema)
		hasEmailCol = strings.Contains(schema, "email")
	}
	if hasEmailCol {
		rows, qErr := db.Query(`SELECT company, email, COUNT(*) FROM leads GROUP BY company, email HAVING COUNT(*) > 1`)
		if qErr != nil {
			fmt.Fprintf(os.Stderr, "⚠️  Could not check for duplicates: %v\n", qErr)
		} else {
			var dups []string
			for rows.Next() {
				var company, email string
				var count int
				rows.Scan(&company, &email, &count)
				dups = append(dups, fmt.Sprintf("  %s | %s | count=%d", company, email, count))
			}
			rows.Close()
			if len(dups) > 0 {
				fmt.Println("❌ Found duplicate (company, email) pairs that must be resolved first:")
				for _, d := range dups {
					fmt.Println(d)
				}
				os.Exit(1)
			}
			fmt.Println("  No duplicate (company, email) pairs — good")
		}
	} else {
		fmt.Println("  No email column on leads — duplicate check not applicable")
	}

	// Begin transaction for schema change
	tx, err := db.Begin()
	if err != nil {
		fmt.Fprintf(os.Stderr, "❌ Failed to begin transaction: %v\n", err)
		os.Exit(1)
	}
	defer tx.Rollback()

	// Create new leads table without email column and with updated constraints
	fmt.Println("  Creating new leads table with updated constraints...")

	// Define the new table columns (without email column if it was already migrated)
	createSQL := `CREATE TABLE leads_new (
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
	)`
	if hasEmailCol {
		createSQL = `CREATE TABLE leads_new (
			id TEXT PRIMARY KEY,
			company TEXT NOT NULL,
			contact_name TEXT DEFAULT '',
			email TEXT DEFAULT '',
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
			updated_at TEXT NOT NULL DEFAULT (datetime('now')),
			UNIQUE(company, email)
		)`
	}

	if _, err := tx.Exec(createSQL); err != nil {
		fmt.Fprintf(os.Stderr, "❌ Failed to create leads_new: %v\n", err)
		os.Exit(1)
	}

	// Copy existing data
	if hasEmailCol {
		if _, err := tx.Exec("INSERT INTO leads_new SELECT * FROM leads"); err != nil {
			fmt.Fprintf(os.Stderr, "❌ Failed to copy data: %v\n", err)
			os.Exit(1)
		}
	} else {
		// leads table no longer has email column; copy without it
		if _, err := tx.Exec(`INSERT INTO leads_new
			(id, company, contact_name, phone, website, tier, type,
			 vertical, check_size, pitch_angle, status, next_action,
			 next_action_date, notes, source, created_at, updated_at)
			SELECT
				id, company, contact_name, phone, website, tier, type,
				vertical, check_size, pitch_angle, status, next_action,
				next_action_date, notes, source, created_at, updated_at
			FROM leads`); err != nil {
			fmt.Fprintf(os.Stderr, "❌ Failed to copy data: %v\n", err)
			os.Exit(1)
		}
	}

	// Verify row count
	var newTotal int
	tx.QueryRow("SELECT COUNT(*) FROM leads_new").Scan(&newTotal)
	fmt.Printf("  Data copied: %d/%d rows\n", newTotal, total)

	if newTotal != total {
		fmt.Fprintf(os.Stderr, "❌ Row count mismatch! %d != %d\n", newTotal, total)
		os.Exit(1)
	}

	// Swap tables
	if _, err := tx.Exec("DROP TABLE leads"); err != nil {
		fmt.Fprintf(os.Stderr, "❌ Failed to drop old leads: %v\n", err)
		os.Exit(1)
	}
	if _, err := tx.Exec("ALTER TABLE leads_new RENAME TO leads"); err != nil {
		fmt.Fprintf(os.Stderr, "❌ Failed to rename leads_new: %v\n", err)
		os.Exit(1)
	}

	// Commit
	if err := tx.Commit(); err != nil {
		fmt.Fprintf(os.Stderr, "❌ Failed to commit: %v\n", err)
		os.Exit(1)
	}

	// Verify final state
	var final int
	db.QueryRow("SELECT COUNT(*) FROM leads").Scan(&final)
	fmt.Printf("  ✅ Migration complete. Final row count: %d\n", final)

	// Show schema
	var schema string
	db.QueryRow("SELECT sql FROM sqlite_master WHERE type='table' AND name='leads'").Scan(&schema)
	fmt.Printf("\n  New schema:\n")
	for _, line := range strings.Split(schema, "\n") {
		fmt.Printf("    %s\n", strings.TrimSpace(line))
	}
	fmt.Println("\n✅ Migration successful!")
}

// ─── Database helpers ─────────────────────────────────────────────────────

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

func openDB(path, password string) *sql.DB {
	absPath, err := filepath.Abs(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "❌ Cannot resolve path '%s': %v\n", path, err)
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

	// Verify the key works
	var count int
	if err := db.QueryRow("SELECT COUNT(*) FROM sqlite_master").Scan(&count); err != nil {
		fmt.Fprintf(os.Stderr, "❌ Database decryption failed (wrong password?): %v\n", err)
		os.Exit(1)
	}

	return db
}
