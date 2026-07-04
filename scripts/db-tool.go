// db-tool.go — Database inspection utility for Counter-Terrorism CRM.
//
// Replaces: check-db.py, check-campaign-data.py, check-followups.py,
//           wave2-data.py, wave3-data.py, wave4-data.py
//
// Usage:
//   go run scripts/db-tool.go stats              # Database overview (replaces check-db.py)
//   go run scripts/db-tool.go campaign-check      # Campaign readiness (replaces check-campaign-data.py)
//   go run scripts/db-tool.go wave <n>            # Wave details 1-4 (replaces wave2-4-data.py)
//   go run scripts/db-tool.go followups           # Follow-up check (replaces check-followups.py)

package main

import (
	"database/sql"
	"fmt"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"time"

	_ "github.com/mutecomm/go-sqlcipher/v4"
)

const (
	dbPath  = "databases/leads.db"
	envPath = ".env"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Usage: go run scripts/db-tool.go <command>")
		fmt.Println()
		fmt.Println("Commands:")
		fmt.Println("  stats           Database overview (leads, emails, statuses)")
		fmt.Println("  campaign-check  Campaign readiness per wave")
	fmt.Println("  wave <1-4>      Detailed lead data for a wave")
	fmt.Println("  no-email        Leads without emails needing enrichment")
	fmt.Println("  followups       Follow-up tracking state")
		os.Exit(0)
	}

	db := openDB()
	defer db.Close()

	switch os.Args[1] {
	case "stats":
		cmdStats(db)
	case "campaign-check":
		cmdCampaignCheck(db)
	case "wave":
		if len(os.Args) < 3 {
			fmt.Fprintln(os.Stderr, "Usage: go run scripts/db-tool.go wave <1-4>")
			os.Exit(1)
		}
		cmdWave(db, os.Args[2])
	case "no-email":
		cmdNoEmail(db)
	case "followups":
		cmdFollowups(db)
	default:
		fmt.Fprintf(os.Stderr, "Unknown command: %s\n", os.Args[1])
		os.Exit(1)
	}
}

// ─── Stats (replaces check-db.py) ────────────────────────────────────────

func cmdStats(db *sql.DB) {
	fmt.Println("=", strings.Repeat("=", 58))
	fmt.Println("  DATABASE OVERVIEW")
	fmt.Println("=", strings.Repeat("=", 58))

	var total int
	db.QueryRow("SELECT COUNT(*) FROM leads").Scan(&total)
	fmt.Printf("\n  Total leads: %d\n", total)

	var withEmail int
	db.QueryRow("SELECT COUNT(DISTINCT lead_id) FROM lead_emails").Scan(&withEmail)
	fmt.Printf("  With email:  %d\n", withEmail)

	var withPhone, withWebsite, withSocial int
	db.QueryRow("SELECT COUNT(*) FROM leads WHERE phone IS NOT NULL AND phone != ''").Scan(&withPhone)
	db.QueryRow("SELECT COUNT(*) FROM leads WHERE website IS NOT NULL AND website != ''").Scan(&withWebsite)
	db.QueryRow("SELECT COUNT(*) FROM leads WHERE notes LIKE '%Social:%'").Scan(&withSocial)
	fmt.Printf("  With phone:  %d\n", withPhone)
	fmt.Printf("  With website: %d\n", withWebsite)
	fmt.Printf("  With social:  %d\n", withSocial)

	fmt.Println("\n  --- Schema ---")
	rows, _ := db.Query("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
	for rows.Next() {
		var name, sql string
		rows.Scan(&name, &sql)
		fmt.Printf("\n  %s:\n", name)
		for _, line := range strings.Split(sql, "\n") {
			fmt.Printf("    %s\n", strings.TrimSpace(line))
		}
	}
	rows.Close()

	fmt.Println("\n  --- Tables ---")
	var leadCount, emailCount, logCount int
	db.QueryRow("SELECT COUNT(*) FROM leads").Scan(&leadCount)
	db.QueryRow("SELECT COUNT(*) FROM lead_emails").Scan(&emailCount)
	db.QueryRow("SELECT COUNT(*) FROM outreach_log").Scan(&logCount)
	fmt.Printf("  leads:         %d rows\n", leadCount)
	fmt.Printf("  lead_emails:   %d rows\n", emailCount)
	fmt.Printf("  outreach_log:  %d rows\n", logCount)

	fmt.Println("\n  --- By Status ---")
	statusRows, _ := db.Query("SELECT status, COUNT(*) FROM leads GROUP BY status ORDER BY COUNT(*) DESC")
	for statusRows.Next() {
		var s string
		var c int
		statusRows.Scan(&s, &c)
		fmt.Printf("  %-15s %d\n", s, c)
	}
	statusRows.Close()

	fmt.Println("\n  --- By Tier ---")
	tierRows, _ := db.Query("SELECT tier, COUNT(*) FROM leads GROUP BY tier ORDER BY tier")
	for tierRows.Next() {
		var t string
		var c int
		tierRows.Scan(&t, &c)
		fmt.Printf("  Tier %s: %d\n", t, c)
	}
	tierRows.Close()

	connStats := db
	recentSQL := `SELECT l.id, l.company, l.status, COALESCE(GROUP_CONCAT(le.email, '||'), '')
		FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id
		GROUP BY l.id ORDER BY l.created_at DESC LIMIT 5`
	recentRows, _ := connStats.Query(recentSQL)
	fmt.Println("\n  --- Recent ---")
	for recentRows.Next() {
		var id, company, status, emails string
		recentRows.Scan(&id, &company, &status, &emails)
		shortID := id
		if len(shortID) > 8 {
			shortID = shortID[:8]
		}
		fmt.Printf("  [%s] %s — %s\n", shortID, company, status)
	}
	recentRows.Close()
}

// ─── Campaign Check (replaces check-campaign-data.py) ───────────────────

func cmdCampaignCheck(db *sql.DB) {
	fmt.Println("=", strings.Repeat("=", 58))
	fmt.Println("  CAMPAIGN READINESS CHECK")
	fmt.Println("=", strings.Repeat("=", 58))

	type waveDef struct {
		name   string
		query  string
	}
	waves := []waveDef{
		{"Wave 1 — VC + Intel (Tier 1)", `
			SELECT COUNT(DISTINCT l.id), COUNT(DISTINCT le.lead_id)
			FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id
			WHERE l.tier = '1'`},
		{"Wave 2 — USA LE + Military", `
			SELECT COUNT(DISTINCT l.id), COUNT(DISTINCT le.lead_id)
			FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id
			WHERE l.vertical IN ('USA','United States')
			AND l.type IN ('Law Enforcement','Military','Intelligence','Homeland Security')`},
		{"Wave 3 — Brazil Military", `
			SELECT COUNT(DISTINCT l.id), COUNT(DISTINCT le.lead_id)
			FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id
			WHERE l.vertical LIKE '%Brazil%' AND l.type = 'Military'`},
		{"Wave 4 — Brazil HR + LE", `
			SELECT COUNT(DISTINCT l.id), COUNT(DISTINCT le.lead_id)
			FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id
			WHERE l.vertical LIKE '%Brazil%'
			AND (l.type = 'Law Enforcement' OR l.type = 'State Police'
			     OR l.type = 'Security' OR l.type LIKE '%Human Rights%'
			     OR l.type LIKE '%Anti-Torture%')`},
		{"Wave 5 — No email", `
			SELECT COUNT(DISTINCT l.id), 0
			FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id
			WHERE le.lead_id IS NULL`},
	}

	for _, w := range waves {
		var total, withEmail int
		db.QueryRow(w.query).Scan(&total, &withEmail)
		fmt.Printf("\n  %s:\n", w.name)
		fmt.Printf("    %d leads, %d with email\n", total, withEmail)
	}

	var totalLeads, totalEmails int
	db.QueryRow("SELECT COUNT(DISTINCT id), COUNT(DISTINCT lead_emails.lead_id) FROM leads LEFT JOIN lead_emails ON lead_emails.lead_id = leads.id").Scan(&totalLeads, &totalEmails)
	fmt.Printf("\n  Total: %d leads, %d with email\n", totalLeads, totalEmails)

	statusRows, _ := db.Query("SELECT status, COUNT(*) FROM leads GROUP BY status ORDER BY COUNT(*) DESC")
	fmt.Println("\n  Status distribution:")
	for statusRows.Next() {
		var s string
		var c int
		statusRows.Scan(&s, &c)
		fmt.Printf("    %s: %d\n", s, c)
	}
	statusRows.Close()

	// Sample Wave 1 emails
	sampleRows, _ := db.Query(`
		SELECT l.company, l.type, le.email
		FROM leads l JOIN lead_emails le ON le.lead_id = l.id
		WHERE l.tier = '1' LIMIT 10`)
	fmt.Println("\n  Sample Wave 1 emails (first 10):")
	for sampleRows.Next() {
		var company, orgType, email string
		sampleRows.Scan(&company, &orgType, &email)
		fmt.Printf("    %-35s | %-20s | %s\n", truncate(company, 35), truncate(orgType, 20), email)
	}
	sampleRows.Close()
}

// ─── Wave Detail (replaces wave2-4-data.py) ─────────────────────────────

func cmdWave(db *sql.DB, waveNum string) {
	fmt.Println("=", strings.Repeat("=", 58))
	fmt.Printf("  WAVE %s DETAILS\n", waveNum)
	fmt.Println("=", strings.Repeat("=", 58))

	var whereClause string
	switch waveNum {
	case "1":
		whereClause = "l.tier = '1'"
	case "2":
		whereClause = "l.vertical IN ('USA','United States') AND l.type IN ('Law Enforcement','Military','Intelligence','Homeland Security')"
	case "3":
		whereClause = "l.vertical LIKE '%Brazil%' AND l.type = 'Military'"
	case "4":
		whereClause = "l.vertical LIKE '%Brazil%' AND (l.type = 'Law Enforcement' OR l.type = 'State Police' OR l.type = 'Security' OR l.type LIKE '%Human Rights%' OR l.type LIKE '%Anti-Torture%')"
	default:
		fmt.Fprintf(os.Stderr, "Invalid wave: %s (must be 1-4)\n", waveNum)
		os.Exit(1)
	}

	var total, withEmail int
	db.QueryRow(fmt.Sprintf(`
		SELECT COUNT(DISTINCT l.id), COUNT(DISTINCT le.lead_id)
		FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id
		WHERE %s`, whereClause)).Scan(&total, &withEmail)
	fmt.Printf("\n  Total: %d leads, %d with email\n", total, withEmail)

	// Type + Tier breakdown
	typeRows, _ := db.Query(fmt.Sprintf(`
		SELECT l.type, l.tier, COUNT(DISTINCT l.id), COUNT(DISTINCT le.lead_id)
		FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id
		WHERE %s GROUP BY l.type, l.tier ORDER BY l.type, l.tier`, whereClause))
	fmt.Println("\n  Type + Tier breakdown:")
	for typeRows.Next() {
		var orgType, tier string
		var cnt, eml int
		typeRows.Scan(&orgType, &tier, &cnt, &eml)
		fmt.Printf("    %-25s | T%s | %d leads, %d with email\n", orgType, tier, cnt, eml)
	}
	typeRows.Close()

	// All leads with emails
	dataRows, _ := db.Query(fmt.Sprintf(`
		SELECT l.company, l.type, l.tier, le.email
		FROM leads l JOIN lead_emails le ON le.lead_id = l.id
		WHERE %s ORDER BY l.type, l.company`, whereClause))
	fmt.Println("\n  Leads with email:")
	hasData := false
	for dataRows.Next() {
		hasData = true
		var company, orgType, tier, email string
		dataRows.Scan(&company, &orgType, &tier, &email)
		fmt.Printf("    %-25s | T%s | %-40s | %s\n", orgType, tier, truncate(company, 40), email)
	}
	if !hasData {
		fmt.Println("    (none)")
	}
	dataRows.Close()

	// Without email
	noEmailRows, _ := db.Query(fmt.Sprintf(`
		SELECT l.company, l.type, l.tier
		FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id
		WHERE %s AND le.lead_id IS NULL ORDER BY l.type, l.company LIMIT 20`, whereClause))
	hasNone := false
	for noEmailRows.Next() {
		if !hasNone {
			fmt.Println("\n  Without email (first 20):")
			hasNone = true
		}
		var company, orgType, tier string
		noEmailRows.Scan(&company, &orgType, &tier)
		fmt.Printf("    T%s | %-25s | %s\n", tier, orgType, company)
	}
	noEmailRows.Close()
}

// ─── No-email (leads needing enrichment) ─────────────────────────────

func cmdNoEmail(db *sql.DB) {
	fmt.Println("=", strings.Repeat("=", 58))
	fmt.Println("  LEADS WITHOUT EMAILS — ENRICHMENT ANALYSIS")
	fmt.Println("=", strings.Repeat("=", 58))

	var totalNoEmail int
	db.QueryRow("SELECT COUNT(*) FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id WHERE le.lead_id IS NULL").Scan(&totalNoEmail)
	fmt.Printf("\n  Total leads without email: %d\n\n", totalNoEmail)

	// By vertical
	fmt.Println("  --- By Vertical ---")
	vr, _ := db.Query(`SELECT COALESCE(l.vertical,'(blank)'), COUNT(*) FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id WHERE le.lead_id IS NULL GROUP BY l.vertical ORDER BY COUNT(*) DESC`)
	for vr.Next() {
		var v string; var c int
		vr.Scan(&v, &c)
		fmt.Printf("    %-20s %d\n", v, c)
	}
	vr.Close()

	// By type
	fmt.Println("\n  --- By Type ---")
	tr, _ := db.Query(`SELECT COALESCE(l.type,'(blank)'), COUNT(*) FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id WHERE le.lead_id IS NULL GROUP BY l.type ORDER BY COUNT(*) DESC`)
	for tr.Next() {
		var t string; var c int
		tr.Scan(&t, &c)
		fmt.Printf("    %-25s %d\n", t, c)
	}
	tr.Close()

	// By tier
	fmt.Println("\n  --- By Tier ---")
	tierRes, _ := db.Query(`SELECT COALESCE(l.tier,'?'), COUNT(*) FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id WHERE le.lead_id IS NULL GROUP BY l.tier ORDER BY l.tier`)
	for tierRes.Next() {
		var t string; var c int
		tierRes.Scan(&t, &c)
		fmt.Printf("    Tier %s: %d\n", t, c)
	}
	tierRes.Close()

	// Pipeline wave mapping
	var wave2, wave4, other int
	db.QueryRow(`SELECT COUNT(*) FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id WHERE le.lead_id IS NULL AND l.vertical IN ('USA','United States') AND l.type IN ('Law Enforcement','Military','Intelligence','Homeland Security')`).Scan(&wave2)
	db.QueryRow(`SELECT COUNT(*) FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id WHERE le.lead_id IS NULL AND l.vertical LIKE '%Brazil%' AND (l.type = 'Law Enforcement' OR l.type = 'State Police' OR l.type = 'Security' OR l.type LIKE '%Human Rights%' OR l.type LIKE '%Anti-Torture%')`).Scan(&wave4)
	db.QueryRow(`SELECT COUNT(*) FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id WHERE le.lead_id IS NULL AND NOT ((l.vertical IN ('USA','United States') AND l.type IN ('Law Enforcement','Military','Intelligence','Homeland Security')) OR (l.vertical LIKE '%Brazil%' AND (l.type = 'Law Enforcement' OR l.type = 'State Police' OR l.type = 'Security' OR l.type LIKE '%Human Rights%' OR l.type LIKE '%Anti-Torture%')))`).Scan(&other)

	fmt.Println("\n  --- Pipeline Wave Mapping ---")
	fmt.Printf("    Wave 2 (USA LE + Military):  %d without email\n", wave2)
	fmt.Printf("    Wave 4 (Brazil HR + LE):     %d without email\n", wave4)
	fmt.Printf("    Other / Unmapped:            %d without email\n", other)

	// Sample leads with phone numbers (easier to enrich)
	fmt.Println("\n  --- Sample Leads That Need Enrichment (top 20 by tier) ---")
	sr, _ := db.Query(`SELECT l.company, COALESCE(l.vertical,'?'), COALESCE(l.type,'?'), COALESCE(l.tier,'?'), CASE WHEN l.phone IS NOT NULL AND l.phone != '' THEN '☎' ELSE '' END FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id WHERE le.lead_id IS NULL ORDER BY l.tier, l.vertical, l.type LIMIT 20`)
	hasSamples := false
	for sr.Next() {
		if !hasSamples {
			hasSamples = true
		}
		var co, v, t, tier, phone string
		sr.Scan(&co, &v, &t, &tier, &phone)
		fmt.Printf("    T%s | %-20s | %-25s | %s%s\n", tier, v, t, truncate(co, 40), phone)
	}
	sr.Close()
	if !hasSamples {
		fmt.Println("    (none)")
	}

	// Enrichment priority suggestions
	fmt.Println("\n  --- Enrichment Priority Recommendations ---")
	fmt.Println("")
	fmt.Println("  🥇 HIGH PRIORITY — Tier 1 agencies without email (34 leads):")
	fmt.Println("     Intelligence agencies, VC-level contacts with phone numbers")
	fmt.Println("     Source: Agency public affairs emails, LinkedIn, Bloomberg")
	fmt.Println("")
	fmt.Println("  🥈 MEDIUM PRIORITY — Wave 2 USA LE without email (152):")
	fmt.Println("     Mostly individual field offices with phone numbers")
	fmt.Println("     Source: Agency websites → Contact/FOIA pages, phone inquiry")
	fmt.Println("")
	fmt.Println("  🥉 LOWER PRIORITY — Wave 4 Brazil LE (52) + other (107):")
	fmt.Println("     Individual police units, global agencies")
	fmt.Println("     Source: Government websites, LinkedIn, public directories")
}

// ─── Followups (replaces check-followups.py) ────────────────────────────

func cmdFollowups(db *sql.DB) {
	fmt.Println("=", strings.Repeat("=", 58))
	fmt.Println("  FOLLOW-UP TRACKING CHECK")
	fmt.Println("=", strings.Repeat("=", 58))

	// Tier 1 leads
	rows, _ := db.Query(`
		SELECT l.id, l.company, l.type, l.status, COALESCE(l.next_action, ''), COALESCE(l.next_action_date, ''), le.email
		FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id AND le.is_primary = 1
		WHERE l.tier = '1'
		ORDER BY l.status, l.company`)
	fmt.Println("\n  Wave 1 leads:")
	var sent, cold int
	for rows.Next() {
		var id, company, orgType, status, action, date, email string
		rows.Scan(&id, &company, &orgType, &status, &action, &date, &email)
		if status == "contacted" {
			sent++
			if action == "" && date == "" {
				fmt.Printf("    %-35s | contacted | ⚠️  no follow-up set\n", truncate(company, 35))
			} else {
				fmt.Printf("    %-35s | contacted | next: %s (%s)\n", truncate(company, 35), truncate(action, 20), date)
			}
		} else {
			cold++
		}
	}
	rows.Close()
	fmt.Printf("    Contacted: %d | Cold: %d\n", sent, cold)

	// Outreach logs
	logRows, _ := db.Query(`
		SELECT o.created_at, o.activity_type, o.outcome, l.company
		FROM outreach_log o JOIN leads l ON o.lead_id = l.id
		WHERE l.tier = '1'
		ORDER BY o.created_at DESC LIMIT 10`)
	fmt.Println("\n  Recent outreach logs for Wave 1:")
	hasLogs := false
	for logRows.Next() {
		hasLogs = true
		var createdAt, activityType, outcome, company string
		logRows.Scan(&createdAt, &activityType, &outcome, &company)
		date := createdAt
		if len(date) > 10 {
			date = date[:10]
		}
		fmt.Printf("    [%s] %-10s | %-30s | %s\n", date, activityType, truncate(company, 30), truncate(outcome, 30))
	}
	if !hasLogs {
		fmt.Println("    (no outreach logs for Wave 1)")
	}
	logRows.Close()

	// Suggest follow-up dates
	fmt.Println("\n  Suggested follow-up dates:")
	today := time.Now()
	for _, d := range []int{3, 5, 7, 14} {
		future := today.AddDate(0, 0, d)
		fmt.Printf("    %2d-day follow-up: %s\n", d, future.Format("2006-01-02"))
	}

	// Leads without follow-up
	noFU, _ := db.Query(`
		SELECT COUNT(*) FROM leads
		WHERE status = 'contacted'
		AND (next_action IS NULL OR next_action = '')
		AND (next_action_date IS NULL OR next_action_date = '')`)
	var noFollowupCount int
	if noFU.Next() {
		noFU.Scan(&noFollowupCount)
	}
	noFU.Close()
	fmt.Printf("\n  Leads contacted but without follow-up set: %d\n", noFollowupCount)
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

func truncate(s string, maxLen int) string {
	if len(s) > maxLen {
		return s[:maxLen]
	}
	return s
}
