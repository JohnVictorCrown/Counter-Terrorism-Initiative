package db

import (
	"database/sql"
	"fmt"
	"net/url"
	"os"
	"path/filepath"
	"strings"

	"github.com/google/uuid"
	_ "github.com/mutecomm/go-sqlcipher/v4"

	"counter-terrorism-initiative/internal/models"
)

var (
	DBPath     = filepath.Join(".", "databases", "leads.db")
	MailDB     = filepath.Join(".", "databases", "mail-credentials.db")
	EnvPath    = filepath.Join(".", ".env")
	GmailAddr  = "john.victor.crown@gmail.com"
	SMTPServer = "smtp.gmail.com"
	SMTPPort   = 587
)

// leadCols is the explicit column list for leads (without email, since it moved to lead_emails).
const leadCols = "l.id, l.company, l.contact_name, l.phone, l.website, " +
	"COALESCE(l.tier, ''), l.type, l.vertical, " +
	"COALESCE(l.check_size, ''), COALESCE(l.pitch_angle, ''), " +
	"l.status, COALESCE(l.next_action, ''), COALESCE(l.next_action_date, ''), " +
	"l.notes, l.source, l.created_at, l.updated_at"

const leadColsShort = "l.id, l.company, l.contact_name, l.phone, l.website, " +
	"l.type, l.vertical, l.source, l.status, l.notes"

// leadFromClause is the FROM + LEFT JOIN for emails.
const leadFromClause = "FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id"

// leadGroupBy is the GROUP BY for the lead columns (needed when joining emails).
const leadGroupBy = "GROUP BY l.id"

func LoadEnvVar(key string) string {
	if data, err := os.ReadFile(EnvPath); err == nil {
		for _, line := range strings.Split(string(data), "\n") {
			line = strings.TrimSpace(line)
			if strings.HasPrefix(line, key+"=") {
				val := strings.SplitN(line, "=", 2)[1]
				val = strings.Trim(val, `"' `)
				if val != "" {
					return val
				}
			}
		}
	}
	return os.Getenv(key)
}

func LoadDBPassword() string {
	if data, err := os.ReadFile(EnvPath); err == nil {
		for _, line := range strings.Split(string(data), "\n") {
			line = strings.TrimSpace(line)
			if strings.HasPrefix(line, "EMAIL_DB_PASSWORD=") {
				val := strings.SplitN(line, "=", 2)[1]
				val = strings.Trim(val, `"' `)
				return val
			}
		}
	}
	if pw := os.Getenv("EMAIL_DB_PASSWORD"); pw != "" {
		return pw
	}
	return ""
}

func openDB(path string) (*sql.DB, error) {
	pw := LoadDBPassword()
	if pw == "" {
		return nil, fmt.Errorf("EMAIL_DB_PASSWORD not found")
	}
	passphrase := fmt.Sprintf("x'%x'", []byte(pw))
	dsn := fmt.Sprintf("%s?_pragma_key=%s&_pragma_journal_mode=WAL",
		path, url.QueryEscape(passphrase))
	db, err := sql.Open("sqlite3", dsn)
	if err != nil {
		return nil, fmt.Errorf("sql open: %w", err)
	}
	var count int
	if err := db.QueryRow("SELECT COUNT(*) FROM sqlite_master").Scan(&count); err != nil {
		db.Close()
		return nil, fmt.Errorf("pragma key: %w", err)
	}
	return db, nil
}

func GetDB() (*sql.DB, error) {
	return openDB(DBPath)
}

func LoadAppPassword() (string, error) {
	db, err := openDB(MailDB)
	if err != nil {
		return "", fmt.Errorf("open mail db: %w", err)
	}
	defer db.Close()

	var pw string
	err = db.QueryRow(
		"SELECT app_password FROM credentials WHERE email = ? ORDER BY id DESC LIMIT 1",
		GmailAddr,
	).Scan(&pw)
	if err == sql.ErrNoRows {
		return "", nil
	}
	return pw, err
}

func StoreAppPassword(email, appPassword string) error {
	db, err := openDB(MailDB)
	if err != nil {
		return fmt.Errorf("open mail db: %w", err)
	}
	defer db.Close()

	db.Exec("PRAGMA journal_mode=WAL")

	_, err = db.Exec(`
		CREATE TABLE IF NOT EXISTS credentials (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			email TEXT UNIQUE NOT NULL,
			app_password TEXT NOT NULL,
			created_at TEXT NOT NULL DEFAULT (datetime('now'))
		)
	`)
	if err != nil {
		return fmt.Errorf("create table: %w", err)
	}

	_, err = db.Exec(
		"INSERT OR REPLACE INTO credentials (email, app_password) VALUES (?, ?)",
		email, appPassword,
	)
	if err != nil {
		return fmt.Errorf("insert credentials: %w", err)
	}

	return nil
}

func scanNameCount(db *sql.DB, query string) []models.NameCount {
	rows, err := db.Query(query)
	if err != nil {
		return nil
	}
	defer rows.Close()

	var result []models.NameCount
	for rows.Next() {
		var nc models.NameCount
		rows.Scan(&nc.Name, &nc.Count)
		result = append(result, nc)
	}
	return result
}

type ContactFilter struct {
	Search   string
	Vertical string
	Type     string
	Source   string
	SortBy   string
	SortDir  string
	Page     int
	PerPage  int
}

func GetContact(id string) (*models.Contact, error) {
	db, err := GetDB()
	if err != nil {
		return nil, err
	}
	defer db.Close()

	query := fmt.Sprintf(`SELECT %s, COALESCE(GROUP_CONCAT(le.email, '%s'), '')
		FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id
		WHERE l.id = ? GROUP BY l.id`,
		leadCols, models.EmailsSeparator)

	row := db.QueryRow(query, id)
	var c models.Contact
	var emailsStr string
	err = row.Scan(&c.ID, &c.Company, &c.ContactName, &c.Phone, &c.Website,
		&c.Tier, &c.Type, &c.Vertical, &c.CheckSize, &c.PitchAngle,
		&c.Status, &c.NextAction, &c.NextActionDate,
		&c.Notes, &c.Source, &c.CreatedAt, &c.UpdatedAt,
		&emailsStr)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	c.Emails = splitEmails(emailsStr)
	return &c, nil
}

func ListContacts(f ContactFilter) ([]models.Contact, int, error) {
	db, err := GetDB()
	if err != nil {
		return nil, 0, err
	}
	defer db.Close()

	allowedSorts := map[string]bool{"company": true, "type": true, "vertical": true, "source": true, "phone": true, "website": true, "status": true}
	if !allowedSorts[f.SortBy] {
		f.SortBy = "company"
	}
	sortDir := "ASC"
	if strings.ToLower(f.SortDir) == "desc" {
		sortDir = "DESC"
	}

	var clauses []string
	var params []any

	if f.Search != "" {
		s := "%" + f.Search + "%"
		clauses = append(clauses, "(l.company LIKE ? OR le.email LIKE ? OR l.phone LIKE ? OR l.website LIKE ? OR l.notes LIKE ? OR l.contact_name LIKE ?)")
		params = append(params, s, s, s, s, s, s)
	}
	if f.Vertical != "" {
		clauses = append(clauses, "l.vertical = ?")
		params = append(params, f.Vertical)
	}
	if f.Type != "" {
		clauses = append(clauses, "l.type = ?")
		params = append(params, f.Type)
	}
	if f.Source != "" {
		clauses = append(clauses, "l.source = ?")
		params = append(params, f.Source)
	}

	where := ""
	if len(clauses) > 0 {
		where = "WHERE " + strings.Join(clauses, " AND ")
	}

	// Count (use subquery to avoid double-count from join)
	countQ := fmt.Sprintf("SELECT COUNT(*) FROM (SELECT l.id FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id %s GROUP BY l.id)", where)
	var total int
	db.QueryRow(countQ, params...).Scan(&total)

	if f.Page < 1 {
		f.Page = 1
	}
	if f.PerPage < 1 {
		f.PerPage = 50
	}
	offset := (f.Page - 1) * f.PerPage

	query := fmt.Sprintf(`SELECT %s, COALESCE(GROUP_CONCAT(le.email, '%s'), '')
		%s %s GROUP BY l.id ORDER BY l.%s %s LIMIT ? OFFSET ?`,
		leadColsShort, models.EmailsSeparator,
		leadFromClause, where, f.SortBy, sortDir)
	params = append(params, f.PerPage, offset)

	rows, err := db.Query(query, params...)
	if err != nil {
		return nil, 0, fmt.Errorf("query: %w", err)
	}
	defer rows.Close()

	var contacts []models.Contact
	for rows.Next() {
		var c models.Contact
		var emailsStr string
		rows.Scan(&c.ID, &c.Company, &c.ContactName, &c.Phone, &c.Website,
			&c.Type, &c.Vertical, &c.Source, &c.Status, &c.Notes,
			&emailsStr)
		c.Emails = splitEmails(emailsStr)
		contacts = append(contacts, c)
	}

	return contacts, total, nil
}

// ─── CRM CLI CRUD ──────────────────────────────────────────────────────

func AddLead(input models.LeadInput) (string, error) {
	orgType := strings.TrimSpace(input.Type)
	if orgType == "" {
		return "", fmt.Errorf("type is required. Choose from: %s", strings.Join(models.ValidTypes, ", "))
	}

	id := uuid.New().String()
	db, err := GetDB()
	if err != nil {
		return "", err
	}
	defer db.Close()

	tx, err := db.Begin()
	if err != nil {
		return "", fmt.Errorf("begin tx: %w", err)
	}
	defer tx.Rollback()

	_, err = tx.Exec(
		`INSERT INTO leads (id, company, contact_name, phone, website,
		   tier, type, vertical, check_size, pitch_angle, status,
		   next_action, next_action_date, notes, source)
		   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		id, input.Company, input.ContactName,
		input.Phone, input.Website,
		defaultStr(input.Tier, "3"), orgType, input.Vertical,
		input.CheckSize, input.PitchAngle,
		defaultStr(input.Status, "cold"), input.NextAction,
		input.NextActionDate, input.Notes, input.Source,
	)
	if err != nil {
		return "", fmt.Errorf("insert lead: %w", err)
	}

	// Insert emails
	for i, email := range input.Emails {
		email = strings.TrimSpace(email)
		if email == "" {
			continue
		}
		isPrimary := 0
		if i == 0 {
			isPrimary = 1
		}
		_, err = tx.Exec(
			"INSERT INTO lead_emails (lead_id, email, is_primary) VALUES (?, ?, ?)",
			id, email, isPrimary,
		)
		if err != nil {
			return "", fmt.Errorf("insert email '%s': %w", email, err)
		}
	}

	if err := tx.Commit(); err != nil {
		return "", fmt.Errorf("commit: %w", err)
	}
	return id, nil
}

// UpdateLead updates lead fields. If data contains "emails", it replaces all
// emails for that lead (delete old + insert new).
func UpdateLead(lid string, data map[string]string) error {
	if t, ok := data["type"]; ok && strings.TrimSpace(t) == "" {
		return fmt.Errorf("type cannot be empty. Choose from: %s", strings.Join(models.ValidTypes, ", "))
	}

	// Extract emails from data if present
	var newEmails []string
	if emailsStr, ok := data["emails"]; ok {
		delete(data, "emails")
		for _, e := range strings.Split(emailsStr, ",") {
			e = strings.TrimSpace(e)
			if e != "" {
				newEmails = append(newEmails, e)
			}
		}
	}

	fields := make([]string, 0, len(data))
	params := make([]any, 0, len(data)+1)

	for key, val := range data {
		if key == "id" || key == "created_at" {
			continue
		}
		fields = append(fields, key+" = ?")
		params = append(params, val)
	}

	if len(fields) == 0 && newEmails == nil {
		return nil
	}

	db, err := GetDB()
	if err != nil {
		return err
	}
	defer db.Close()

	tx, err := db.Begin()
	if err != nil {
		return fmt.Errorf("begin tx: %w", err)
	}
	defer tx.Rollback()

	// Update lead fields
	if len(fields) > 0 {
		fields = append(fields, "updated_at = datetime('now')")
		params = append(params, lid)
		query := fmt.Sprintf("UPDATE leads SET %s WHERE id = ?", strings.Join(fields, ", "))
		_, err = tx.Exec(query, params...)
		if err != nil {
			return fmt.Errorf("update lead: %w", err)
		}
	}

	// Update emails if provided
	if newEmails != nil {
		_, err = tx.Exec("DELETE FROM lead_emails WHERE lead_id = ?", lid)
		if err != nil {
			return fmt.Errorf("delete old emails: %w", err)
		}
		for i, email := range newEmails {
			isPrimary := 0
			if i == 0 {
				isPrimary = 1
			}
			_, err = tx.Exec(
				"INSERT INTO lead_emails (lead_id, email, is_primary) VALUES (?, ?, ?)",
				lid, email, isPrimary,
			)
			if err != nil {
				return fmt.Errorf("insert email '%s': %w", email, err)
			}
		}
	}

	return tx.Commit()
}

func DeleteLead(lid string) error {
	db, err := GetDB()
	if err != nil {
		return err
	}
	defer db.Close()

	db.Exec("DELETE FROM outreach_log WHERE lead_id = ?", lid)
	_, err = db.Exec("DELETE FROM leads WHERE id = ?", lid)
	return err
}

func LogOutreach(lid, activityType, notes, outcome string) (string, error) {
	id := uuid.New().String()
	db, err := GetDB()
	if err != nil {
		return "", err
	}
	defer db.Close()

	_, err = db.Exec(
		"INSERT INTO outreach_log (id, lead_id, activity_type, notes, outcome) VALUES (?, ?, ?, ?, ?)",
		id, lid, activityType, notes, outcome,
	)
	return id, err
}

func GetOutreach(lid string) ([]models.OutreachLog, error) {
	db, err := GetDB()
	if err != nil {
		return nil, err
	}
	defer db.Close()

	rows, err := db.Query("SELECT id, lead_id, activity_type, notes, outcome, created_at FROM outreach_log WHERE lead_id = ? ORDER BY created_at DESC", lid)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var logs []models.OutreachLog
	for rows.Next() {
		var l models.OutreachLog
		rows.Scan(&l.ID, &l.LeadID, &l.ActivityType, &l.Notes, &l.Outcome, &l.CreatedAt)
		logs = append(logs, l)
	}
	return logs, nil
}

type LeadFilter struct {
	Search   string
	Tier     string
	Status   string
	Vertical string
	Type     string
}

func GetLeads(f LeadFilter) ([]models.Contact, error) {
	db, err := GetDB()
	if err != nil {
		return nil, err
	}
	defer db.Close()

	var clauses []string
	var params []any

	if f.Tier != "" {
		clauses = append(clauses, "l.tier = ?")
		params = append(params, f.Tier)
	}
	if f.Status != "" {
		if f.Status == "active" {
			clauses = append(clauses, "l.status NOT IN ('closed_won','closed_lost')")
		} else {
			clauses = append(clauses, "l.status = ?")
			params = append(params, f.Status)
		}
	}
	if f.Vertical != "" {
		clauses = append(clauses, "l.vertical = ?")
		params = append(params, f.Vertical)
	}
	if f.Type != "" {
		clauses = append(clauses, "l.type = ?")
		params = append(params, f.Type)
	}
	if f.Search != "" {
		s := "%" + f.Search + "%"
		clauses = append(clauses, "(l.company LIKE ? OR l.contact_name LIKE ? OR le.email LIKE ?)")
		params = append(params, s, s, s)
	}

	where := ""
	if len(clauses) > 0 {
		where = "WHERE " + strings.Join(clauses, " AND ")
	}

	query := fmt.Sprintf(`SELECT %s, COALESCE(GROUP_CONCAT(le.email, '%s'), '')
		%s %s %s ORDER BY l.updated_at DESC`,
		leadCols, models.EmailsSeparator,
		leadFromClause, where, leadGroupBy)

	rows, err := db.Query(query, params...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	return scanContacts(rows), nil
}

func GetFollowupsDue() ([]models.Contact, error) {
	db, err := GetDB()
	if err != nil {
		return nil, err
	}
	defer db.Close()

	query := fmt.Sprintf(`SELECT %s, COALESCE(GROUP_CONCAT(le.email, '%s'), '')
		%s WHERE l.next_action_date != ''
		AND l.next_action_date <= date('now')
		AND l.status NOT IN ('closed_won','closed_lost')
		%s ORDER BY l.next_action_date ASC`,
		leadCols, models.EmailsSeparator,
		leadFromClause, leadGroupBy)

	rows, err := db.Query(query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	return scanContacts(rows), nil
}

func GetStats() (*models.Stats, error) {
	db, err := GetDB()
	if err != nil {
		return nil, err
	}
	defer db.Close()

	var total int
	db.QueryRow("SELECT COUNT(*) FROM leads").Scan(&total)

	byTier := scanNameCount(db, "SELECT tier, COUNT(*) FROM leads GROUP BY tier ORDER BY tier")
	byStatus := scanNameCount(db, "SELECT status, COUNT(*) FROM leads GROUP BY status ORDER BY COUNT(*) DESC")

	var followupsDue int
	db.QueryRow(`SELECT COUNT(*) FROM leads WHERE next_action_date != ''
		AND next_action_date <= date('now')
		AND status NOT IN ('closed_won','closed_lost')`).Scan(&followupsDue)

	recentRows := queryRecentLeads(db)
	recent := scanContacts(recentRows)

	byVertical := scanNameCount(db, "SELECT COALESCE(vertical, 'Unknown') as v, COUNT(*) as cnt FROM leads GROUP BY v ORDER BY cnt DESC LIMIT 10")
	byType := scanNameCount(db, "SELECT COALESCE(type, 'Unknown') as t, COUNT(*) as cnt FROM leads GROUP BY t ORDER BY cnt DESC")
	bySource := scanNameCount(db, "SELECT COALESCE(source, 'Unknown') as s, COUNT(*) as cnt FROM leads GROUP BY s ORDER BY cnt DESC")

	var withEmail, withPhone, withWebsite, withSocial, emailsSent int
	db.QueryRow("SELECT COUNT(DISTINCT lead_id) FROM lead_emails").Scan(&withEmail)
	db.QueryRow("SELECT COUNT(*) FROM leads WHERE phone IS NOT NULL AND phone != ''").Scan(&withPhone)
	db.QueryRow("SELECT COUNT(*) FROM leads WHERE website IS NOT NULL AND website != ''").Scan(&withWebsite)
	db.QueryRow("SELECT COUNT(*) FROM leads WHERE notes LIKE '%Social:%'").Scan(&withSocial)
	db.QueryRow("SELECT COUNT(*) FROM outreach_log WHERE outcome LIKE 'sent%'").Scan(&emailsSent)

	return &models.Stats{
		Total:         total,
		ByTier:        byTier,
		ByStatus:      byStatus,
		FollowupsDue:  followupsDue,
		Recent:        recent,
		ByVertical:    byVertical,
		ByType:        byType,
		BySource:      bySource,
		WithEmail:     withEmail,
		WithPhone:     withPhone,
		WithWebsite:   withWebsite,
		WithSocial:    withSocial,
		EmailsSent:    emailsSent,
	}, nil
}

func queryRecentLeads(db *sql.DB) *sql.Rows {
	query := fmt.Sprintf(`SELECT %s, COALESCE(GROUP_CONCAT(le.email, '%s'), '')
		%s %s ORDER BY l.created_at DESC LIMIT 5`,
		leadCols, models.EmailsSeparator,
		leadFromClause, leadGroupBy)
	rows, err := db.Query(query)
	if err != nil {
		return nil
	}
	return rows
}

// isUniqueConstraintError checks if an error is a SQLite UNIQUE constraint violation.
func isUniqueConstraintError(err error) bool {
	return err != nil && strings.Contains(err.Error(), "UNIQUE constraint failed")
}

func defaultStr(s, def string) string {
	if s == "" {
		return def
	}
	return s
}

// splitEmails splits a GROUP_CONCAT'd emails string into a slice.
// Returns nil (not empty slice) when the string is empty.
func splitEmails(s string) []string {
	if s == "" {
		return nil
	}
	parts := strings.Split(s, models.EmailsSeparator)
	// Filter out any empty parts from leading/trailing separators
	var result []string
	for _, p := range parts {
		if p != "" {
			result = append(result, p)
		}
	}
	if len(result) == 0 {
		return nil
	}
	return result
}

func scanContacts(rows *sql.Rows) []models.Contact {
	if rows == nil {
		return nil
	}
	defer rows.Close()
	var contacts []models.Contact
	for rows.Next() {
		var c models.Contact
		var emailsStr string
		rows.Scan(
			&c.ID, &c.Company, &c.ContactName, &c.Phone,
			&c.Website, &c.Tier, &c.Type, &c.Vertical, &c.CheckSize,
			&c.PitchAngle, &c.Status, &c.NextAction, &c.NextActionDate,
			&c.Notes, &c.Source, &c.CreatedAt, &c.UpdatedAt,
			&emailsStr,
		)
		c.Emails = splitEmails(emailsStr)
		contacts = append(contacts, c)
	}
	return contacts
}

func GetFilters() (*models.FiltersResponse, error) {
	db, err := GetDB()
	if err != nil {
		return nil, err
	}
	defer db.Close()

	fr := &models.FiltersResponse{}

	rows, _ := db.Query("SELECT DISTINCT COALESCE(vertical, 'Unknown') FROM leads ORDER BY vertical")
	for rows != nil && rows.Next() {
		var v string
		rows.Scan(&v)
		if v != "" && v != "Unknown" {
			fr.Verticals = append(fr.Verticals, v)
		}
	}
	if rows != nil {
		rows.Close()
	}

	rows, _ = db.Query("SELECT DISTINCT COALESCE(type, 'Unknown') FROM leads WHERE type IS NOT NULL AND type != '' ORDER BY type")
	for rows != nil && rows.Next() {
		var t string
		rows.Scan(&t)
		fr.Types = append(fr.Types, t)
	}
	if rows != nil {
		rows.Close()
	}

	rows, _ = db.Query("SELECT DISTINCT COALESCE(source, 'Unknown') FROM leads WHERE source IS NOT NULL AND source != '' ORDER BY source")
	for rows != nil && rows.Next() {
		var s string
		rows.Scan(&s)
		fr.Sources = append(fr.Sources, s)
	}
	if rows != nil {
		rows.Close()
	}

	return fr, nil
}

func ExportCSV(f ContactFilter) ([]models.Contact, error) {
	db, err := GetDB()
	if err != nil {
		return nil, err
	}
	defer db.Close()

	allowedSorts := map[string]bool{"company": true, "type": true, "vertical": true, "source": true, "phone": true, "website": true, "status": true}
	if !allowedSorts[f.SortBy] {
		f.SortBy = "company"
	}
	sortDir := "ASC"
	if strings.ToLower(f.SortDir) == "desc" {
		sortDir = "DESC"
	}

	var clauses []string
	var params []any

	if f.Search != "" {
		s := "%" + f.Search + "%"
		clauses = append(clauses, "(l.company LIKE ? OR le.email LIKE ? OR l.phone LIKE ? OR l.website LIKE ? OR l.notes LIKE ? OR l.contact_name LIKE ?)")
		params = append(params, s, s, s, s, s, s)
	}
	if f.Vertical != "" {
		clauses = append(clauses, "l.vertical = ?")
		params = append(params, f.Vertical)
	}
	if f.Type != "" {
		clauses = append(clauses, "l.type = ?")
		params = append(params, f.Type)
	}
	if f.Source != "" {
		clauses = append(clauses, "l.source = ?")
		params = append(params, f.Source)
	}

	where := ""
	if len(clauses) > 0 {
		where = "WHERE " + strings.Join(clauses, " AND ")
	}

	query := fmt.Sprintf(`SELECT %s, COALESCE(GROUP_CONCAT(le.email, '%s'), '')
		%s %s %s ORDER BY l.%s %s`,
		leadColsShort, models.EmailsSeparator,
		leadFromClause, where, leadGroupBy, f.SortBy, sortDir)
	rows, err := db.Query(query, params...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var contacts []models.Contact
	for rows.Next() {
		var c models.Contact
		var emailsStr string
		rows.Scan(&c.ID, &c.Company, &c.ContactName, &c.Phone, &c.Website,
			&c.Type, &c.Vertical, &c.Source, &c.Status, &c.Notes,
			&emailsStr)
		c.Emails = splitEmails(emailsStr)
		contacts = append(contacts, c)
	}
	return contacts, nil
}

func ExportSelectedCSV(ids []string) ([]models.Contact, error) {
	db, err := GetDB()
	if err != nil {
		return nil, err
	}
	defer db.Close()

	if len(ids) == 0 {
		return nil, nil
	}

	placeholders := make([]string, len(ids))
	params := make([]any, len(ids))
	for i, id := range ids {
		placeholders[i] = "?"
		params[i] = id
	}

	query := fmt.Sprintf(`SELECT %s, COALESCE(GROUP_CONCAT(le.email, '%s'), '')
		%s WHERE l.id IN (%s) %s ORDER BY l.company ASC`,
		leadColsShort, models.EmailsSeparator,
		leadFromClause, strings.Join(placeholders, ","), leadGroupBy)

	rows, err := db.Query(query, params...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var contacts []models.Contact
	for rows.Next() {
		var c models.Contact
		var emailsStr string
		rows.Scan(&c.ID, &c.Company, &c.ContactName, &c.Phone, &c.Website,
			&c.Type, &c.Vertical, &c.Source, &c.Status, &c.Notes,
			&emailsStr)
		c.Emails = splitEmails(emailsStr)
		contacts = append(contacts, c)
	}
	return contacts, nil
}

func LogEmail(contactID, emailTo, subject, bodyPreview, status, errorMsg string) {
	db, err := GetDB()
	if err != nil {
		return
	}
	defer db.Close()

	id := uuid.New().String()
	notes := fmt.Sprintf("To: %s | Subject: %s", emailTo, subject)
	if bodyPreview != "" {
		preview := bodyPreview
		if len(preview) > 80 {
			preview = preview[:80]
		}
		preview = strings.ReplaceAll(preview, "\n", " ")
		notes += fmt.Sprintf(" | Body: %s...", preview)
	}
	outcome := status
	if errorMsg != "" {
		errMsg := errorMsg
		if len(errMsg) > 100 {
			errMsg = errMsg[:100]
		}
		outcome += fmt.Sprintf(" | %s", errMsg)
	}

	db.Exec("INSERT INTO outreach_log (id, lead_id, activity_type, notes, outcome) VALUES (?, ?, ?, ?, ?)",
		id, contactID, "email", notes, outcome)
}

func GetEmailLog(contactID string, limit int) ([]models.OutreachLog, int, error) {
	db, err := GetDB()
	if err != nil {
		return nil, 0, err
	}
	defer db.Close()

	if limit < 1 {
		limit = 50
	}

	var rows *sql.Rows
	if contactID != "" {
		rows, err = db.Query("SELECT id, lead_id, activity_type, notes, outcome, created_at FROM outreach_log WHERE lead_id = ? ORDER BY created_at DESC LIMIT ?", contactID, limit)
	} else {
		rows, err = db.Query("SELECT o.id, o.lead_id, o.activity_type, o.notes, o.outcome, o.created_at, COALESCE(l.company, '') FROM outreach_log o LEFT JOIN leads l ON o.lead_id = l.id ORDER BY o.created_at DESC LIMIT ?", limit)
	}
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()

	var logs []models.OutreachLog
	for rows.Next() {
		var l models.OutreachLog
		if contactID != "" {
			rows.Scan(&l.ID, &l.LeadID, &l.ActivityType, &l.Notes, &l.Outcome, &l.CreatedAt)
		} else {
			rows.Scan(&l.ID, &l.LeadID, &l.ActivityType, &l.Notes, &l.Outcome, &l.CreatedAt, &l.Company)
		}
		logs = append(logs, l)
	}

	var totalSent int
	db.QueryRow("SELECT COUNT(*) FROM outreach_log WHERE outcome LIKE 'sent%'").Scan(&totalSent)

	return logs, totalSent, nil
}

func GetReportData(f ContactFilter) (*models.ReportData, error) {
	db, err := GetDB()
	if err != nil {
		return nil, err
	}
	defer db.Close()

	var clauses []string
	var params []any

	if f.Search != "" {
		s := "%" + f.Search + "%"
		clauses = append(clauses, "(l.company LIKE ? OR le.email LIKE ? OR l.phone LIKE ? OR l.website LIKE ? OR l.notes LIKE ? OR l.contact_name LIKE ?)")
		params = append(params, s, s, s, s, s, s)
	}
	if f.Vertical != "" {
		clauses = append(clauses, "l.vertical = ?")
		params = append(params, f.Vertical)
	}
	if f.Type != "" {
		clauses = append(clauses, "l.type = ?")
		params = append(params, f.Type)
	}
	if f.Source != "" {
		clauses = append(clauses, "l.source = ?")
		params = append(params, f.Source)
	}

	where := ""
	if len(clauses) > 0 {
		where = "WHERE " + strings.Join(clauses, " AND ")
	}

	// Build simple WHERE clauses (without search terms that may reference le.email)
	// for aggregate stats (totalCount, byVertical, byType, bySource, byPhone, etc.)
	var simpleClauses []string
	var simpleParams []any
	if f.Vertical != "" {
		simpleClauses = append(simpleClauses, "vertical = ?")
		simpleParams = append(simpleParams, f.Vertical)
	}
	if f.Type != "" {
		simpleClauses = append(simpleClauses, "type = ?")
		simpleParams = append(simpleParams, f.Type)
	}
	if f.Source != "" {
		simpleClauses = append(simpleClauses, "source = ?")
		simpleParams = append(simpleParams, f.Source)
	}
	simpleWhere := ""
	if len(simpleClauses) > 0 {
		simpleWhere = "WHERE " + strings.Join(simpleClauses, " AND ")
	}

	var totalCount int
	db.QueryRow("SELECT COUNT(*) FROM leads "+simpleWhere, simpleParams...).Scan(&totalCount)

	// Contact list query uses the full where (with JOIN for email search support)
	contactQuery := fmt.Sprintf(`SELECT %s, COALESCE(GROUP_CONCAT(le.email, '%s'), '')
		%s %s %s ORDER BY l.company ASC LIMIT 150`,
		leadColsShort, models.EmailsSeparator,
		leadFromClause, where, leadGroupBy)
	contactRows, err := db.Query(contactQuery, params...)
	if err != nil {
		return nil, err
	}
	defer contactRows.Close()

	var contacts []models.Contact
	for contactRows.Next() {
		var c models.Contact
		var emailsStr string
		contactRows.Scan(&c.ID, &c.Company, &c.ContactName, &c.Phone, &c.Website,
			&c.Type, &c.Vertical, &c.Source, &c.Status, &c.Notes,
			&emailsStr)
		c.Emails = splitEmails(emailsStr)
		contacts = append(contacts, c)
	}

	byVerticalRows, _ := db.Query("SELECT COALESCE(vertical, 'Unknown') as v, COUNT(*) as cnt FROM leads "+simpleWhere+" GROUP BY v ORDER BY cnt DESC LIMIT 8", simpleParams...)
	byVertical := scanChartItems(byVerticalRows)

	byTypeRows, _ := db.Query("SELECT COALESCE(type, 'Unknown') as t, COUNT(*) as cnt FROM leads "+simpleWhere+" GROUP BY t ORDER BY cnt DESC LIMIT 8", simpleParams...)
	byType := scanChartItems(byTypeRows)

	bySourceRows, _ := db.Query("SELECT COALESCE(source, 'Unknown') as s, COUNT(*) as cnt FROM leads "+simpleWhere+" GROUP BY s ORDER BY cnt DESC LIMIT 8", simpleParams...)
	bySource := scanChartItems(bySourceRows)

	maxCount := 1
	for _, items := range [][]models.ChartItem{byVertical, byType, bySource} {
		for _, item := range items {
			if item.Count > maxCount {
				maxCount = item.Count
			}
		}
	}

	if maxCount == 0 {
		maxCount = 1
	}
	for i := range byVertical {
		byVertical[i].Pct = float64(byVertical[i].Count) / float64(maxCount) * 100
	}
	for i := range byType {
		byType[i].Pct = float64(byType[i].Count) / float64(maxCount) * 100
	}
	for i := range bySource {
		bySource[i].Pct = float64(bySource[i].Count) / float64(maxCount) * 100
	}

	var withEmail, withPhone, withWebsite, withSocial int

	// Count with email: use lead_emails join (can use full where with le.email references)
	cleanWhere := strings.ReplaceAll(where, "l.", "")
	db.QueryRow("SELECT COUNT(DISTINCT le.lead_id) FROM lead_emails le JOIN leads l ON l.id = le.lead_id "+cleanWhere, params...).Scan(&withEmail)

	// Phone/website/social counts use simpleWhere (no search, safe for FROM leads)
	if simpleWhere != "" {
		db.QueryRow("SELECT COUNT(*) FROM leads "+simpleWhere+" AND phone IS NOT NULL AND phone != ''", simpleParams...).Scan(&withPhone)
		db.QueryRow("SELECT COUNT(*) FROM leads "+simpleWhere+" AND website IS NOT NULL AND website != ''", simpleParams...).Scan(&withWebsite)
		db.QueryRow("SELECT COUNT(*) FROM leads "+simpleWhere+" AND notes LIKE '%Social:%'", simpleParams...).Scan(&withSocial)
	} else {
		db.QueryRow("SELECT COUNT(*) FROM leads WHERE phone IS NOT NULL AND phone != ''").Scan(&withPhone)
		db.QueryRow("SELECT COUNT(*) FROM leads WHERE website IS NOT NULL AND website != ''").Scan(&withWebsite)
		db.QueryRow("SELECT COUNT(*) FROM leads WHERE notes LIKE '%Social:%'").Scan(&withSocial)
	}

	titleParts := []string{}
	if f.Search != "" {
		titleParts = append(titleParts, fmt.Sprintf("Search: \"%s\"", f.Search))
	}
	if f.Vertical != "" {
		titleParts = append(titleParts, "Vertical: "+f.Vertical)
	}
	if f.Type != "" {
		titleParts = append(titleParts, "Type: "+f.Type)
	}
	if f.Source != "" {
		titleParts = append(titleParts, "Source: "+f.Source)
	}
	title := "All Contacts"
	if len(titleParts) > 0 {
		title = strings.Join(titleParts, " — ")
	}

	return &models.ReportData{
		Title:       title,
		TotalCount:  totalCount,
		WithEmail:   withEmail,
		WithPhone:   withPhone,
		WithWebsite: withWebsite,
		WithSocial:  withSocial,
		ByVertical:  byVertical,
		ByType:      byType,
		BySource:    bySource,
		Contacts:    contacts,
		GeneratedAt: "",
	}, nil
}

func scanChartItems(rows *sql.Rows) []models.ChartItem {
	if rows == nil {
		return nil
	}
	defer rows.Close()
	var items []models.ChartItem
	for rows.Next() {
		var ci models.ChartItem
		rows.Scan(&ci.Name, &ci.Count)
		items = append(items, ci)
	}
	return items
}

// GetContactEmail returns the primary email and company name for a lead.
func GetContactEmail(id string) (string, string, error) {
	db, err := GetDB()
	if err != nil {
		return "", "", err
	}
	defer db.Close()

	var email, company string
	err = db.QueryRow(`
		SELECT le.email, l.company
		FROM lead_emails le
		JOIN leads l ON l.id = le.lead_id
		WHERE le.lead_id = ?
		ORDER BY le.is_primary DESC, le.id ASC
		LIMIT 1`, id).Scan(&email, &company)
	if err == sql.ErrNoRows {
		return "", "", nil
	}
	return email, company, err
}

// GetLeadEmails returns all email addresses for a lead.
func GetLeadEmails(leadID string) ([]string, error) {
	db, err := GetDB()
	if err != nil {
		return nil, err
	}
	defer db.Close()

	rows, err := db.Query(
		"SELECT email FROM lead_emails WHERE lead_id = ? ORDER BY is_primary DESC, id ASC",
		leadID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var emails []string
	for rows.Next() {
		var e string
		rows.Scan(&e)
		emails = append(emails, e)
	}
	return emails, nil
}
