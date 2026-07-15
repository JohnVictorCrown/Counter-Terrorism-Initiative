// cleanup-orphans.go — Deletes orphaned outreach_log entries that have
// NULL or empty lead_id (cannot be linked to any contact).
//
// Usage:
//   go run scripts/cleanup-orphans.go             # Dry-run: show what will be deleted
//   go run scripts/cleanup-orphans.go --apply     # Delete the orphaned records

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
	apply := false
	for _, arg := range os.Args[1:] {
		if arg == "--apply" {
			apply = true
		}
	}

	db := openDB()
	defer db.Close()

	fmt.Println(strings.Repeat("═", 72))
	fmt.Println("  ORPHANED OUTREACH LOG CLEANUP")
	fmt.Println(strings.Repeat("═", 72))

	// ── Step 1: Count orphaned records ─────────────────────────
	var total int
	db.QueryRow("SELECT COUNT(*) FROM outreach_log WHERE lead_id IS NULL OR lead_id = ''").Scan(&total)

	if total == 0 {
		fmt.Println("\n✅ No orphaned outreach_log entries found. Nothing to do.")
		return
	}

	fmt.Printf("\n📊 Orphaned outreach_log entries: %d\n", total)

	// ── Step 2: Breakdown by outcome and activity ──────────────
	fmt.Println("\n" + strings.Repeat("─", 72))
	fmt.Println("  BREAKDOWN")
	fmt.Println(strings.Repeat("─", 72))

	fmt.Println("  By outcome:")
	rows, _ := db.Query("SELECT COALESCE(outcome,'?'), COUNT(*) FROM outreach_log WHERE lead_id IS NULL OR lead_id = '' GROUP BY outcome ORDER BY COUNT(*) DESC")
	for rows.Next() {
		var s string; var c int
		rows.Scan(&s, &c)
		fmt.Printf("    %-20s: %d\n", s, c)
	}
	rows.Close()

	fmt.Println("  By activity type:")
	rows, _ = db.Query("SELECT COALESCE(activity_type,'?'), COUNT(*) FROM outreach_log WHERE lead_id IS NULL OR lead_id = '' GROUP BY activity_type ORDER BY COUNT(*) DESC")
	for rows.Next() {
		var s string; var c int
		rows.Scan(&s, &c)
		fmt.Printf("    %-20s: %d\n", s, c)
	}
	rows.Close()

	// ── Step 3: Date range ─────────────────────────────────────
	var minDate, maxDate string
	db.QueryRow("SELECT MIN(COALESCE(created_at,'')), MAX(COALESCE(created_at,'')) FROM outreach_log WHERE lead_id IS NULL OR lead_id = ''").Scan(&minDate, &maxDate)
	fmt.Printf("  Date range: %s → %s\n", minDate, maxDate)

	// ── Step 4: Sample records ─────────────────────────────────
	fmt.Println("\n" + strings.Repeat("─", 72))
	fmt.Println("  SAMPLE RECORDS (first 8)")
	fmt.Println(strings.Repeat("─", 72))

	rows, _ = db.Query("SELECT COALESCE(activity_type,''), COALESCE(notes,''), COALESCE(outcome,''), COALESCE(created_at,'') FROM outreach_log WHERE lead_id IS NULL OR lead_id = '' ORDER BY created_at DESC LIMIT 8")
	i := 0
	for rows.Next() {
		i++
		var at, notes, outcome, ca string
		rows.Scan(&at, &notes, &outcome, &ca)
		n := notes
		if len(n) > 90 {
			n = n[:90] + "..."
		}
		fmt.Printf("  [%02d] %s | %s | %s\n", i, ca, outcome, n)
	}
	rows.Close()

	// ── Step 5: Action ─────────────────────────────────────────
	fmt.Println("\n" + strings.Repeat("─", 72))
	fmt.Println("  OPERATION")
	fmt.Println(strings.Repeat("─", 72))
	fmt.Printf("  DELETE FROM outreach_log WHERE lead_id IS NULL OR lead_id = ''\n")
	fmt.Printf("  → %d records will be removed\n", total)

	if !apply {
		fmt.Println("\n  ⚠️  DRY-RUN MODE — no changes made.")
		fmt.Println("  Run with --apply to execute the deletion.")
		return
	}

	result, err := db.Exec("DELETE FROM outreach_log WHERE lead_id IS NULL OR lead_id = ''")
	if err != nil {
		fmt.Fprintf(os.Stderr, "\n❌ Delete failed: %v\n", err)
		os.Exit(1)
	}

	deleted, _ := result.RowsAffected()

	// Verify
	var remaining int
	db.QueryRow("SELECT COUNT(*) FROM outreach_log WHERE lead_id IS NULL OR lead_id = ''").Scan(&remaining)

	var allOutreach int
	db.QueryRow("SELECT COUNT(*) FROM outreach_log").Scan(&allOutreach)

	fmt.Println("\n" + strings.Repeat("═", 72))
	fmt.Println("  ✅ CLEANUP COMPLETE")
	fmt.Println(strings.Repeat("═", 72))
	fmt.Printf("  • Deleted:   %d records\n", deleted)
	fmt.Printf("  • Remaining: %d orphaned records\n", remaining)
	fmt.Printf("  • Total outreach_log: %d records\n", allOutreach)

	if remaining == 0 {
		fmt.Println("\n  ✅ All orphaned outreach_log entries have been removed.")
	} else {
		fmt.Printf("\n  ⚠️  %d orphaned records still remain.\n", remaining)
	}
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
