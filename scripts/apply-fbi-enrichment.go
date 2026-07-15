// apply-fbi-enrichment.go — Applies FBI field office enrichment directly:
// sets "foia@fbi.gov" as the email for all FBI leads matched to field offices.
//
// Usage:
//   go run scripts/apply-fbi-enrichment.go               # Dry-run: show what will be updated
//   go run scripts/apply-fbi-enrichment.go --apply        # Apply the updates

package main

import (
	"database/sql"
	"fmt"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	_ "github.com/mutecomm/go-sqlcipher/v4"
)

const (
	dbPath  = "databases/leads.db"
	envPath = ".env"
)

var (
	phoneRe  = regexp.MustCompile(`\(\d{3}\)\s*\d{3}-\d{4}`)
	subRe    = regexp.MustCompile(`([a-z]+)\.fbi\.gov`)
	officeRe = regexp.MustCompile(`/contact-us/field-offices/([a-z-]+)`)
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
	fmt.Println("  FBI FIELD OFFICE ENRICHMENT — APPLY")
	fmt.Println(strings.Repeat("═", 72))

	// ── Step 1: Find FBI leads without emails ──────────────────
	rows, err := db.Query(`
		SELECT COALESCE(l.id,''), l.company, COALESCE(l.type,''), COALESCE(l.phone,'')
		FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id
		WHERE l.company LIKE '%FBI%'
		AND l.vertical IN ('USA','United States')
		AND le.lead_id IS NULL
		ORDER BY l.company`)
	if err != nil {
		fmt.Fprintf(os.Stderr, "❌ Query failed: %v\n", err)
		os.Exit(1)
	}

	type fbiLead struct {
		ID      string
		Company string
		CityKey string
		Phone   string
	}

	var leads []fbiLead
	for rows.Next() {
		var ld fbiLead
		var orgType string
		if err := rows.Scan(&ld.ID, &ld.Company, &orgType, &ld.Phone); err != nil {
			continue
		}
		if ld.ID == "" {
			continue
		}
		// Extract city key from company name
		city := strings.TrimPrefix(ld.Company, "FBI - ")
		city = strings.TrimSuffix(city, " Field Office")
		city = strings.TrimSuffix(city, " Field Division")
		city = strings.TrimSpace(city)
		ld.CityKey = normalizeCityKey(city)
		leads = append(leads, ld)
	}
	rows.Close()

	fmt.Printf("\n📊 FBI leads without emails: %d\n", len(leads))

	if len(leads) == 0 {
		fmt.Println("\n✅ No FBI leads to update.")
		return
	}

	// ── Step 2: Show what will be updated ──────────────────────
	fmt.Println("\n" + strings.Repeat("─", 72))
	fmt.Println("  LEADS TO UPDATE")
	fmt.Println(strings.Repeat("─", 72))

	for i, ld := range leads {
		shortID := ld.ID
		if len(shortID) > 8 {
			shortID = shortID[:8]
		}
		phone := ld.Phone
		if phone == "" {
			phone = "(no phone)"
		}
		fmt.Printf("  [%02d] %-40s [%s] %s\n", i+1, ld.Company, shortID, phone)
	}

	fmt.Printf("\n  → Email: foia@fbi.gov\n")
	fmt.Printf("  → Notes: FOIA contact from fbi.gov\n")
	fmt.Printf("  → %d leads to update\n", len(leads))

	if !apply {
		fmt.Println("\n  ⚠️  DRY-RUN MODE — no changes made.")
		fmt.Println("  Run with --apply to execute the updates.")
		return
	}

	// ── Step 3: Apply the updates ──────────────────────────────
	fmt.Println("\n" + strings.Repeat("═", 72))
	fmt.Println("  APPLYING UPDATES")
	fmt.Println(strings.Repeat("═", 72))

	updated := 0
	for _, ld := range leads {
		// Add email to lead_emails table (id is auto-increment)
		_, err := db.Exec(
			"INSERT INTO lead_emails (lead_id, email, is_primary) VALUES (?, ?, 1)",
			ld.ID, "foia@fbi.gov",
		)
		if err != nil {
			fmt.Printf("  ❌ [%s] Failed to add email: %v\n", ld.ID[:8], err)
			continue
		}

		// Update notes to indicate FOIA source
		_, err = db.Exec(
			"UPDATE leads SET notes = CASE WHEN notes != '' THEN notes || ' | ' ELSE '' END || ?, updated_at = datetime('now') WHERE id = ?",
			"FOIA contact from fbi.gov", ld.ID,
		)
		if err != nil {
			fmt.Printf("  ⚠️  [%s] Email added but notes update failed: %v\n", ld.ID[:8], err)
		}

		shortID := ld.ID
		if len(shortID) > 8 {
			shortID = shortID[:8]
		}
		fmt.Printf("  ✅ [%02d/%d] %s [%s] → foia@fbi.gov\n", updated+1, len(leads), ld.Company, shortID)
		updated++
	}

	// ── Step 4: Verify ─────────────────────────────────────────
	var remaining int
	db.QueryRow(`
		SELECT COUNT(*) FROM leads l
		LEFT JOIN lead_emails le ON le.lead_id = l.id
		WHERE l.company LIKE '%FBI%'
		AND l.vertical IN ('USA','United States')
		AND le.lead_id IS NULL
	`).Scan(&remaining)

	var totalFBI int
	db.QueryRow("SELECT COUNT(*) FROM leads WHERE company LIKE '%FBI%' AND vertical IN ('USA','United States')").Scan(&totalFBI)

	var withEmail int
	db.QueryRow("SELECT COUNT(DISTINCT l.id) FROM leads l JOIN lead_emails le ON le.lead_id = l.id WHERE l.company LIKE '%FBI%' AND l.vertical IN ('USA','United States')").Scan(&withEmail)

	fmt.Println("\n" + strings.Repeat("═", 72))
	fmt.Println("  ✅ ENRICHMENT COMPLETE")
	fmt.Println(strings.Repeat("═", 72))
	fmt.Printf("  • Updated:       %d / %d leads\n", updated, len(leads))
	fmt.Printf("  • FBI total:     %d\n", totalFBI)
	fmt.Printf("  • With email:    %d\n", withEmail)
	fmt.Printf("  • Still missing: %d\n", remaining)

	if remaining == 0 {
		fmt.Println("\n  ✅ All FBI field offices now have foia@fbi.gov!")
	} else {
		fmt.Printf("\n  ⚠️  %d FBI leads still need enrichment.\n", remaining)
	}
	fmt.Println()
}

// ─── Helpers ─────────────────────────────────────────────────────────────

func normalizeCityKey(name string) string {
	s := strings.ToLower(name)
	s = strings.TrimSpace(s)
	replacements := map[string]string{
		"st. louis":       "stlouis",
		"st louis":        "stlouis",
		"salt lake city":  "saltlakecity",
		"kansas city":     "kansascity",
		"oklahoma city":   "oklahomacity",
		"new york":        "newyork",
		"new york city":   "newyork",
		"new haven":       "newhaven",
		"new orleans":     "neworleans",
		"los angeles":     "losangeles",
		"san francisco":   "sanfrancisco",
		"san diego":       "sandiego",
		"san antonio":     "sanantonio",
		"san juan":        "sanjuan",
		"las vegas":       "lasvegas",
		"little rock":     "littlerock",
		"el paso":         "elpaso",
		"washington dc":   "washingtondc",
		"washington d.c.": "washingtondc",
	}
	if r, ok := replacements[s]; ok {
		return r
	}
	return strings.NewReplacer(" ", "", "-", "", ".", "", ",", "", "'", "", "’", "").Replace(s)
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
