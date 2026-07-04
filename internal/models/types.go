package models

// EmailsString is the separator used when encoding/decoding emails in GROUP_CONCAT
const EmailsSeparator = "||"

type SocialEntry struct {
	Platform string `json:"platform"`
	Icon     string `json:"icon"`
	Handle   string `json:"handle"`
	URL      string `json:"url"`
}

// ─── CRM Constants ─────────────────────────────────────────────────────

var ValidTypes = []string{
	"Military", "Law Enforcement", "Intelligence", "State Police",
	"Security", "Government", "Homeland Security", "Defense",
	"Human Rights NGO", "Anti-Torture Org", "Government HR Body",
	"International HR Body", "Humanitarian Org", "Legal Defense",
	"Faith-Based HR",
}

var Statuses = []string{
	"cold", "contacted", "replied", "meeting", "negotiating",
	"closed_won", "closed_lost",
}

var TierLabels = map[string]string{
	"1": "VC",
	"2": "Corporate",
	"3": "Local",
	"4": "Grant",
	"5": "Venue",
	"6": "Media",
}

// ─── LeadInput for create/update ────────────────────────────────────────

type LeadInput struct {
	Company        string
	ContactName    string
	Emails         []string
	Phone          string
	Website        string
	Tier           string
	Type           string
	Vertical       string
	CheckSize      string
	PitchAngle     string
	Status         string
	NextAction     string
	NextActionDate string
	Notes          string
	Source         string
}

type Contact struct {
	ID             string        `json:"id"`
	Company        string        `json:"company"`
	ContactName    string        `json:"contact_name"`
	Emails         []string      `json:"emails"`
	Phone          string        `json:"phone"`
	Website        string        `json:"website"`
	Tier           string        `json:"tier"`
	Type           string        `json:"type"`
	Vertical       string        `json:"vertical"`
	CheckSize      string        `json:"check_size"`
	PitchAngle     string        `json:"pitch_angle"`
	Status         string        `json:"status"`
	NextAction     string        `json:"next_action"`
	NextActionDate string        `json:"next_action_date"`
	Notes          string        `json:"notes"`
	Source         string        `json:"source"`
	CreatedAt      string        `json:"created_at"`
	UpdatedAt      string        `json:"updated_at"`
	Social         []SocialEntry `json:"social,omitempty"`
}

type Stats struct {
	Total       int          `json:"total"`
	ByVertical  []NameCount  `json:"by_vertical"`
	ByType      []NameCount  `json:"by_type"`
	BySource    []NameCount  `json:"by_source"`
	WithEmail   int          `json:"with_email"`
	WithPhone   int          `json:"with_phone"`
	WithWebsite int          `json:"with_website"`
	WithSocial  int          `json:"with_social"`
	EmailsSent  int          `json:"emails_sent"`
	// CLI-only fields
	FollowupsDue int       `json:"followups_due"`
	ByTier       []NameCount `json:"by_tier"`
	ByStatus     []NameCount `json:"by_status"`
	Recent       []Contact   `json:"recent"`
}

type NameCount struct {
	Name  string `json:"name"`
	Count int    `json:"count"`
}

type ChartItem struct {
	Name  string  `json:"name"`
	Count int     `json:"count"`
	Pct   float64 `json:"pct"`
}

type ContactsResponse struct {
	Contacts   []Contact `json:"contacts"`
	Total      int       `json:"total"`
	Page       int       `json:"page"`
	PerPage    int       `json:"per_page"`
	TotalPages int       `json:"total_pages"`
}

type FiltersResponse struct {
	Verticals []string `json:"verticals"`
	Types     []string `json:"types"`
	Sources   []string `json:"sources"`
}

type OutreachLog struct {
	ID           string `json:"id"`
	LeadID       string `json:"lead_id"`
	ActivityType string `json:"activity_type"`
	Notes        string `json:"notes"`
	Outcome      string `json:"outcome"`
	CreatedAt    string `json:"created_at"`
	Company      string `json:"company,omitempty"`
}

type EmailLogResponse struct {
	Logs      []OutreachLog `json:"logs"`
	TotalSent int           `json:"total_sent"`
}

type SendEmailRequest struct {
	ContactID string `json:"contact_id" form:"contact_id"`
	Subject   string `json:"subject" form:"subject"`
	Body      string `json:"body" form:"body"`
	Email     string `json:"email" form:"email"`
}

type SendBulkEmailRequest struct {
	Emails  []string `json:"emails"`
	Subject string   `json:"subject"`
	Body    string   `json:"body"`
}

type ExportSelectedRequest struct {
	IDs []string `json:"ids"`
}

type ReportData struct {
	Title       string
	TotalCount  int
	WithEmail   int
	WithPhone   int
	WithWebsite int
	WithSocial  int
	ByVertical  []ChartItem
	ByType      []ChartItem
	BySource    []ChartItem
	Contacts    []Contact
	GeneratedAt string
}
