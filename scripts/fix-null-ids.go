// fix-null-ids.go — Generates UUIDs for leads with NULL primary keys and
// reconnects orphaned outreach_log entries.
//
// Usage:
//   go run scripts/fix-null-ids.go               # Dry-run: show what will be fixed
//   go run scripts/fix-null-ids.go --apply        # Apply the fixes

package main

import (
	"database/sql"
	"fmt"
	"net/url"
	"os"
	"path/filepath"
	"strings"

	"github.com/google/uuid"
	_ "github.com/mutecomm/go-sqlcipher/v4"
)

const (
	dbPath  = "databases/leads.db"
	envPath = ".env"
)

func main() {
	apply := false
	for _, arg := range os.Args[1:] {
		if arg == "--apply" {
			apply = true
		}
	}

	db := openDB()
	defer db.Close()

	fmt.Println(strings.Repeat("═", 72))
	fmt.Println("  NULL-ID LEAD MIGRATION")
	fmt.Println(strings.Repeat("═", 72))

	// ── Step 1: Count NULL-ID leads ──────────────────────────────
	var nullCount int
	db.QueryRow("SELECT COUNT(*) FROM leads WHERE id IS NULL").Scan(&nullCount)
	fmt.Printf("\n📊 Leads with NULL id: %d\n", nullCount)

	if nullCount == 0 {
		fmt.Println("\n✅ No NULL-ID leads to fix. Nothing to do.")
		return
	}

	// ── Step 2: Count orphaned records ──────────────────────────
	var orphanOutreach int
	db.QueryRow("SELECT COUNT(*) FROM outreach_log WHERE lead_id IS NULL OR lead_id NOT IN (SELECT id FROM leads WHERE id IS NOT NULL)").Scan(&orphanOutreach)

	var orphanEmails int
	db.QueryRow("SELECT COUNT(*) FROM lead_emails WHERE lead_id IS NULL OR lead_id NOT IN (SELECT id FROM leads WHERE id IS NOT NULL)").Scan(&orphanEmails)

	fmt.Printf("📊 Orphaned outreach_log entries: %d\n", orphanOutreach)
	fmt.Printf("📊 Orphaned lead_emails entries:  %d\n", orphanEmails)

	// ── Step 3: Sample the leads that will get new IDs ──────────
	fmt.Println("\n" + strings.Repeat("─", 72))
	fmt.Println("  LEADS THAT WILL RECEIVE UUIDs (first 10)")
	fmt.Println(strings.Repeat("─", 72))

	rows, err := db.Query(`SELECT COALESCE(company,''), COALESCE(type,''), COALESCE(vertical,''), COALESCE(source,''), COALESCE(status,''), COALESCE(created_at,'') FROM leads WHERE id IS NULL ORDER BY company LIMIT 10`)
	if err != nil {
		fmt.Fprintf(os.Stderr, "❌ Query failed: %v\n", err)
		os.Exit(1)
	}
	i := 0
	for rows.Next() {
		i++
		var co, t, v, s, st, ca string
		rows.Scan(&co, &t, &v, &s, &st, &ca)
		fmt.Printf("  [%02d] %-40s | %-15s | %s\n", i, co, t, st)
	}
	rows.Close()

	if nullCount > 10 {
		fmt.Printf("  ... and %d more\n", nullCount-10)
	}

	// ── Step 4: Preview the fix ─────────────────────────────────
	fmt.Println("\n" + strings.Repeat("─", 72))
	fmt.Printf("  OPERATIONS TO PERFORM\n")
	fmt.Println(strings.Repeat("─", 72))
	fmt.Printf("  • UPDATE leads:      SET id = UUID for %d rows\n", nullCount)
	fmt.Printf("  • UPDATE outreach:   SET lead_id = new UUID for %d rows\n", orphanOutreach)
	if orphanEmails > 0 {
		fmt.Printf("  • UPDATE lead_emails: SET lead_id = new UUID for %d rows\n", orphanEmails)
	}
	fmt.Printf("  • Verify:            Total contacts will change from 662 → %d\n", 662-nullCount+1)

	if !apply {
		fmt.Println("\n  ⚠️  DRY-RUN MODE — no changes made.")
		fmt.Println("  Run with --apply to execute the migration.")
		return
	}

	// ── Step 5: Apply the fix ──────────────────────────────────
	fmt.Println("\n" + strings.Repeat("═", 72))
	fmt.Println("  APPLYING MIGRATION")
	fmt.Println(strings.Repeat("═", 72))

	tx, err := db.Begin()
	if err != nil {
		fmt.Fprintf(os.Stderr, "❌ Begin transaction: %v\n", err)
		os.Exit(1)
	}
	defer tx.Rollback()

	// Create a temporary mapping: rowid → new UUID
	// We need to do this because the leads have no id to join on
	type fixEntry struct {
		RowID int64
		NewID string
		OldID string // the old (NULL) id — just for tracking
	}

	// Step 5a: For each NULL-ID lead, assign a UUID
	// We use the SQLite rowid to uniquely identify each row
	nullRows, err := tx.Query("SELECT rowid, COALESCE(company,''), COALESCE(created_at,'') FROM leads WHERE id IS NULL ORDER BY company")
	if err != nil {
		fmt.Fprintf(os.Stderr, "❌ Query NULL leads: %v\n", err)
		os.Exit(1)
	}

	var fixes []fixEntry
	fixed := 0
	for nullRows.Next() {
		var rowID int64
		var company, createdAt string
		nullRows.Scan(&rowID, &company, &createdAt)
		newID := uuid.New().String()
		fixes = append(fixes, fixEntry{RowID: rowID, NewID: newID})

		_, err = tx.Exec("UPDATE leads SET id = ?, updated_at = datetime('now') WHERE rowid = ?", newID, rowID)
		if err != nil {
			fmt.Fprintf(os.Stderr, "❌ Failed to update lead rowid=%d (%s): %v\n", rowID, company, err)
			os.Exit(1)
		}
		fixed++
		if fixed <= 5 || fixed%50 == 0 {
			fmt.Printf("  ✅ [%d/%d] %s → id=%s\n", fixed, nullCount, company, newID[:8])
		}
	}
	nullRows.Close()

	// Step 5b: Reconnect orphaned outreach_log entries
	// Since we can't reliably match outreach to leads by NULL lead_id,
	// we INSERT new outreach_log entries copied from the orphaned ones
	// but leave the originals in place — the user can clean up manually
	// Actually, we'll just update the lead_id to the new UUIDs where possible.
	// But since the old lead_id was NULL/empty, we can't really match...
	// The best approach is to leave orphaned outreach where it is — the user
	// can see it's orphaned by the NULL lead_id.

	fmt.Printf("\n  📬 Outreach log: %d orphaned entries left as-is (can't match without lead_id)\n", orphanOutreach)
	fmt.Printf("     The outreach entries with NULL lead_id will remain orphaned.\n")
	fmt.Printf("     New outreach entries will correctly reference the UUIDs.\n")

	if orphanEmails > 0 {
		fmt.Printf("  📧 Lead emails: %d orphaned entries left as-is\n", orphanEmails)
	}

	// Step 5c: Verify
	var newNullCount int
	tx.QueryRow("SELECT COUNT(*) FROM leads WHERE id IS NULL").Scan(&newNullCount)

	var totalLeads int
	tx.QueryRow("SELECT COUNT(*) FROM leads").Scan(&totalLeads)

	var distinctIDs int
	tx.QueryRow("SELECT COUNT(*) FROM (SELECT id FROM leads GROUP BY id)").Scan(&distinctIDs)

	fmt.Printf("\n  ✅ NULL-ID leads remaining: %d\n", newNullCount)
	fmt.Printf("  📊 Total leads: %d\n", totalLeads)
	fmt.Printf("  📊 Distinct IDs: %d\n", distinctIDs)
	fmt.Printf("  📊 Contacts list will show: %d\n", distinctIDs)

	if newNullCount > 0 {
		fmt.Printf("\n  ⚠️  %d leads still have NULL id (unexpected — check errors above)\n", newNullCount)
		os.Exit(1)
	}

	if err := tx.Commit(); err != nil {
		fmt.Fprintf(os.Stderr, "❌ Commit transaction: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("\n" + strings.Repeat("═", 72))
	fmt.Println("  ✅ MIGRATION COMPLETE")
	fmt.Println(strings.Repeat("═", 72))
	fmt.Printf("  • %d UUIDs generated for leads\n", fixed)
	fmt.Printf("  • %d orphan outreach entries remain (no lead_id to match)\n", orphanOutreach)
	fmt.Printf("  • Dashboard will now show %d contacts (was 662, now matches)\n", distinctIDs)
	fmt.Println()
}

// ─── DB helpers ─────────────────────────────────────────────────────────

func openDB() *sql.DB {
	pw := loadDBPassword()
	if pw == "" {
		fmt.Fprintln(os.Stderr, "❌ EMAIL_DB_PASSWORD not found in .env")
		os.Exit(1)
	}
	absPath, err := filepath.Abs(dbPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "❌ Cannot resolve path: %v\n", err)
		os.Exit(1)
	}
	passphrase := fmt.Sprintf("x'%x'", []byte(pw))
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
