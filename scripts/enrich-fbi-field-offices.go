// enrich-fbi-field-offices.go — Scrapes FBI field offices from fbi.gov,
// cross-references with the database, and generates crm update commands
// to add FOIA contact emails for each office.
//
// Usage:
//   go run scripts/enrich-fbi-field-offices.go              # Dry-run: show matches
//   go run scripts/enrich-fbi-field-offices.go --apply      # Generate commands

package main

import (
	"database/sql"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"

	"golang.org/x/net/html"

	_ "github.com/mutecomm/go-sqlcipher/v4"
)

const (
	dbPath      = "databases/leads.db"
	envPath     = ".env"
	fbiURL      = "https://www.fbi.gov/contact-us/field-offices"
	httpTimeout = 30 * time.Second
)

var (
	phoneRe  = regexp.MustCompile(`\(\d{3}\)\s*\d{3}-\d{4}`)
	subRe    = regexp.MustCompile(`([a-z]+)\.fbi\.gov`)
	officeRe = regexp.MustCompile(`/contact-us/field-offices/([a-z-]+)`)
)

// FieldOffice represents a parsed FBI field office from the website.
type FieldOffice struct {
	Name      string
	CityKey   string // subdomain prefix for matching
	Subdomain string // e.g. "albany.fbi.gov"
	Phone     string
	URL       string
}

// DBLead represents a lead in the database without an email.
type DBLead struct {
	ID      string
	Company string
	OrgType string
	Phone   string
	CityKey string
}

// Match represents a succesful match between scraped office and DB lead.
type Match struct {
	Office         FieldOffice
	Lead           DBLead
	SuggestedEmail string
}

func main() {
	apply := false
	for _, arg := range os.Args[1:] {
		if arg == "--apply" {
			apply = true
		}
	}

	fmt.Println("=" + strings.Repeat("=", 72))
	fmt.Println("  FBI FIELD OFFICE ENRICHMENT")
	fmt.Println("=" + strings.Repeat("=", 72))

	fmt.Print("\n📡 Fetching FBI field offices page... ")
	offices, err := scrapeFBIFieldOffices()
	if err != nil {
		fmt.Fprintf(os.Stderr, "\n❌ Failed to scrape: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("found %d field offices\n", len(offices))

	fmt.Print("🗄️  Querying database... ")
	db := openDB()
	defer db.Close()

	dbLeads := queryDBFBILeads(db)
	fmt.Printf("found %d FBI leads without emails\n", len(dbLeads))

	fmt.Print("🔗 Matching offices to leads... ")
	
	officeByKey := make(map[string]FieldOffice)
	for _, o := range offices {
		officeByKey[o.CityKey] = o
	}

	var matches []Match
	var unmatchedLeads []DBLead

	for _, lead := range dbLeads {
		if office, ok := officeByKey[lead.CityKey]; ok {
			matches = append(matches, Match{
				Office:         office,
				Lead:           lead,
				SuggestedEmail: "foia@fbi.gov",
			})
		} else {
			unmatchedLeads = append(unmatchedLeads, lead)
		}
	}

	matchedOfficeKeys := make(map[string]bool)
	for _, m := range matches {
		matchedOfficeKeys[m.Office.CityKey] = true
	}
	var unmatchedOffices []FieldOffice
	for _, o := range offices {
		if !matchedOfficeKeys[o.CityKey] {
			unmatchedOffices = append(unmatchedOffices, o)
		}
	}

	fmt.Printf("%d matched, %d offices unmatched, %d leads unmatched\n",
		len(matches), len(unmatchedOffices), len(unmatchedLeads))

	fmt.Println("\n" + strings.Repeat("═", 72))
	fmt.Println("  MATCHED FIELD OFFICES")
	fmt.Println(strings.Repeat("═", 72))

	sort.Slice(matches, func(i, j int) bool {
		return matches[i].Office.Name < matches[j].Office.Name
	})

	for _, m := range matches {
		shortID := m.Lead.ID
		if len(shortID) > 8 {
			shortID = shortID[:8]
		}
		fmt.Printf("\n  📍 %s (%s)\n", m.Office.Name, m.Office.Subdomain)
		fmt.Printf("     Phone:    %s\n", m.Office.Phone)
		fmt.Printf("     Database: %s [%s]\n", m.Lead.Company, shortID)
		fmt.Printf("     📬 Email:  %s\n", m.SuggestedEmail)
	}

	if len(unmatchedLeads) > 0 {
		fmt.Println("\n" + strings.Repeat("─", 72))
		fmt.Printf("  ❌ UNMATCHED DATABASE LEADS (%d)\n", len(unmatchedLeads))
		fmt.Println(strings.Repeat("─", 72))
		for _, lead := range unmatchedLeads {
			shortID := lead.ID
			if len(shortID) > 8 {
				shortID = shortID[:8]
			}
			fmt.Printf("  %s [%s] (key: %q)\n", lead.Company, shortID, lead.CityKey)
		}
	}

	if len(unmatchedOffices) > 0 {
		fmt.Println("\n" + strings.Repeat("─", 72))
		fmt.Printf("  📋 UNMATCHED FBI OFFICES (%d) — not in database\n", len(unmatchedOffices))
		fmt.Println(strings.Repeat("─", 72))
		for _, o := range unmatchedOffices {
			fmt.Printf("  %s (%s) [key: %s]\n", o.Name, o.Subdomain, o.CityKey)
		}
	}

	if apply {
		fmt.Println("\n" + strings.Repeat("═", 72))
		fmt.Println("  CRM UPDATE COMMANDS")
		fmt.Println(strings.Repeat("═", 72))
		fmt.Println()

		for _, m := range matches {
			fmt.Printf("# Update %s (%s):\n", m.Lead.Company, m.Office.Subdomain)
			fmt.Printf("crm update %s\n", m.Lead.ID)
			fmt.Printf("# When prompted for 'emails', enter: %s\n", m.SuggestedEmail)
			fmt.Printf("# When prompted for 'notes', enter: FOIA contact from fbi.gov\n")
			fmt.Println()
		}

		fmt.Printf("📋 %d FBI offices to update\n", len(matches))
	}

	fmt.Println("\n" + strings.Repeat("═", 72))
	fmt.Println("  SUMMARY")
	fmt.Println(strings.Repeat("═", 72))
	fmt.Printf("  Offices on fbi.gov:  %d\n", len(offices))
	fmt.Printf("  Leads in database:   %d\n", len(dbLeads))
	fmt.Printf("  Matched:             %d\n", len(matches))
	fmt.Printf("  Unmatched leads:     %d (need manual enrichment)\n", len(unmatchedLeads))
	fmt.Printf("  Unmatched offices:   %d (not in database)\n", len(unmatchedOffices))
	fmt.Println("  Email: foia@fbi.gov (centralized FOIA)")

	if !apply {
		fmt.Println("\n  Run with --apply to generate crm update commands.")
	}
}

// scrapeFBIFieldOffices fetches and parses the FBI field offices page.
func scrapeFBIFieldOffices() ([]FieldOffice, error) {
	client := &http.Client{Timeout: httpTimeout}
	req, err := http.NewRequest("GET", fbiURL, nil)
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")

	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("HTTP GET: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("HTTP %d: %s", resp.StatusCode, resp.Status)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read body: %w", err)
	}

	return parseOffices(string(body))
}

// parseOffices parses the FBI field offices HTML using a tokenizer approach.
//
// Page structure (Plone CMS):
//   <a href="https://www.fbi.gov/contact-us/field-offices/albany">Albany</a>
//   <div class="description">
//     <p>Address</p>
//     <p>City, State ZIP</p>
//     <p><a href="https://albany.fbi.gov">albany.fbi.gov</a></p>
//     <p>(518) 465-7551</p>
//   </div>
//
// Strategy: walk the HTML tree to find:
//   1. <a> with href containing /contact-us/field-offices/<city> → office name
//   2. Nearby following <a> with .fbi.gov → subdomain
//   3. Nearby text matching phone pattern
func parseOffices(htmlContent string) ([]FieldOffice, error) {
	type linkInfo struct {
		text string
		href string
		node *html.Node
	}

	// First pass: collect all relevant <a> elements in document order
	// by doing an in-order traversal
	doc, err := html.Parse(strings.NewReader(htmlContent))
	if err != nil {
		return nil, fmt.Errorf("parse HTML: %w", err)
	}

	// Collect all a-nodes with their text and href, in document order
	var allLinks []linkInfo
	var collectLinks func(*html.Node)
	collectLinks = func(n *html.Node) {
		if n.Type == html.ElementNode && n.Data == "a" {
			var href string
			for _, attr := range n.Attr {
				if attr.Key == "href" {
					href = attr.Val
				}
			}
			if href != "" {
				text := extractText(n)
				allLinks = append(allLinks, linkInfo{text: text, href: href, node: n})
			}
		}
		for c := n.FirstChild; c != nil; c = c.NextSibling {
			collectLinks(c)
		}
	}
	collectLinks(doc)

	// Classify links: office links vs subdomain links vs other
	type officeLink struct {
		name       string
		url        string
		idx        int // index in allLinks
	}
	type subdomainLink struct {
		subdomain string
		url       string
		idx       int
	}

	var offices []officeLink
	var subdomains []subdomainLink

	for i, l := range allLinks {
		if strings.Contains(l.href, "/contact-us/field-offices/") &&
			!strings.Contains(l.href, "alphabetical") && l.text != "" {
			offices = append(offices, officeLink{name: l.text, url: l.href, idx: i})
		}
		if strings.Contains(l.href, ".fbi.gov") &&
			!strings.Contains(l.href, "/field-offices") {
			if m := subRe.FindStringSubmatch(l.href); len(m) > 1 {
				subdomains = append(subdomains, subdomainLink{
					subdomain: m[1] + ".fbi.gov",
					url:       l.href,
					idx:       i,
				})
			}
		}
	}

	// Match: for each office link, find the nearest subdomain link that
	// comes after it in document order but before the next office link
	type match struct {
		office     officeLink
		subdomain  subdomainLink
		phone      string
	}

	var matches []match

	for oi, ol := range offices {
		// Determine end boundary: next office link or end of document
		end := len(allLinks)
		if oi+1 < len(offices) {
			end = offices[oi+1].idx
		}

		// Find subdomain between ol.idx and end
		var bestSub subdomainLink
		for _, sd := range subdomains {
			if sd.idx > ol.idx && sd.idx < end {
				bestSub = sd
				break // first one after the office link
			}
		}

		// Find the office link's HTML node for phone extraction
		var officeNode *html.Node
		for _, l := range allLinks {
			if l.href == ol.url && l.text == ol.name {
				officeNode = l.node
				break
			}
		}
		phone := extractPhoneBetween(officeNode, ol.url, doc)

		matches = append(matches, match{
			office:    ol,
			subdomain: bestSub,
			phone:     phone,
		})
	}

	// Build FieldOffice slice
	var result []FieldOffice
	for _, m := range matches {
		var cityKey string
		if m.subdomain.url != "" {
			if sub := subRe.FindStringSubmatch(m.subdomain.url); len(sub) > 1 {
				cityKey = sub[1]
			}
		}
		if cityKey == "" {
			cityKey = normalizeCityKey(m.office.name)
		}
		if cityKey == "" {
			if matchURL := officeRe.FindStringSubmatch(m.office.url); len(matchURL) > 1 {
				cityKey = strings.ReplaceAll(matchURL[1], "-", "")
			}
		}

		officeURL := m.office.url
		if !strings.HasPrefix(officeURL, "http") {
			officeURL = "https://www.fbi.gov" + officeURL
		}

		result = append(result, FieldOffice{
			Name:      m.office.name,
			CityKey:   cityKey,
			Subdomain: m.subdomain.url,
			Phone:     m.phone,
			URL:       officeURL,
		})
	}

	// Deduplicate by CityKey, preferring entries with a subdomain or phone
	seen := make(map[string]int) // CityKey → index in deduped
	var deduped []FieldOffice
	for _, r := range result {
		if r.CityKey == "" {
			continue
		}
		if idx, ok := seen[r.CityKey]; ok {
			e := &deduped[idx]
			// Prefer the entry with more complete information
			if e.Subdomain == "" && r.Subdomain != "" {
				deduped[idx] = r
			} else if e.Phone == "" && r.Phone != "" {
				deduped[idx] = r
			} else if e.Name == "" && r.Name != "" {
				deduped[idx] = r
			}
		} else {
			seen[r.CityKey] = len(deduped)
			deduped = append(deduped, r)
		}
	}

	if len(deduped) == 0 {
		return nil, fmt.Errorf("no field office entries found on page")
	}

	sort.Slice(deduped, func(i, j int) bool {
		return deduped[i].Name < deduped[j].Name
	})

	return deduped, nil
}

// extractPhoneBetween searches the DOM between the office link and subdomain link
// (or until end of container) for a phone number.
func extractPhoneBetween(officeNode *html.Node, officeHref string, root *html.Node) string {
	// Collect all text nodes between office link and subdomain link
	var texts []string
	var collecting bool

	var walk func(*html.Node)
	walk = func(n *html.Node) {
		if n.Type == html.TextNode && collecting {
			t := strings.TrimSpace(n.Data)
			if t != "" {
				texts = append(texts, t)
			}
		}
		if n == officeNode {
			collecting = true
		}

		if n.Type == html.ElementNode && n.Data == "a" && collecting && n != officeNode {
			var href string
			for _, attr := range n.Attr {
				if attr.Key == "href" {
					href = attr.Val
				}
			}
			// If we hit another office link, stop collecting
			if strings.Contains(href, "/contact-us/field-offices/") && href != officeHref {
				collecting = false
				return
			}
		}
		for c := n.FirstChild; c != nil; c = c.NextSibling {
			walk(c)
		}
	}
	walk(root)

	for _, t := range texts {
		if m := phoneRe.FindString(t); m != "" {
			return m
		}
	}
	return ""
}

// parseOfficesFallback tries a tokenizer-based approach if the tree parser finds nothing.
func parseOfficesFallback(htmlContent string) ([]FieldOffice, error) {
	z := html.NewTokenizer(strings.NewReader(htmlContent))
	var offices []FieldOffice
	var current FieldOffice
	inOffice := false

	for {
		tt := z.Next()
		if tt == html.ErrorToken {
			break
		}

		switch tt {
		case html.StartTagToken, html.SelfClosingTagToken:
			name, _ := z.TagName()
			tagName := string(name)

			if tagName == "a" {
				var href string
				for {
					k, v, m := z.TagAttr()
					if string(k) == "href" {
						href = string(v)
					}
					if !m {
						break
					}
				}
				if strings.Contains(href, ".fbi.gov") && !strings.Contains(href, "/field-offices") {
					if m := subRe.FindStringSubmatch(href); len(m) > 1 {
						if current.Name == "" {
							current.CityKey = m[1]
							current.Subdomain = href
							inOffice = true
						}
					}
				}
			}

		case html.TextToken:
			text := strings.TrimSpace(string(z.Text()))
			if text == "" {
				continue
			}

			if inOffice {
				if current.Name == "" && len(text) > 2 && !strings.Contains(text, ".gov") {
					current.Name = text
				} else if current.Phone == "" {
					if m := phoneRe.FindString(text); m != "" {
						current.Phone = m
					}
				}
			}
		}

		// Save completed entries
		if current.Name != "" && current.Subdomain != "" && current.Phone != "" && z.Next() == html.StartTagToken {
			offices = append(offices, current)
			current = FieldOffice{}
			inOffice = false
		}
	}

	if len(offices) == 0 {
		return nil, fmt.Errorf("no field office entries found on page (tried both parsers)")
	}
	return offices, nil
}

// extractText extracts all text content from a node and its children.
func extractText(n *html.Node) string {
	var text string
	var visit func(*html.Node)
	visit = func(node *html.Node) {
		if node.Type == html.TextNode {
			t := strings.TrimSpace(node.Data)
			if t != "" {
				text += t + " "
			}
		}
		for c := node.FirstChild; c != nil; c = c.NextSibling {
			visit(c)
		}
	}
	visit(n)
	return strings.TrimSpace(text)
}

// normalizeCityKey converts a city name to a subdomain-like key.
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

// queryDBFBILeads queries the database for FBI leads without emails.
func queryDBFBILeads(db *sql.DB) []DBLead {
	rows, err := db.Query(`
		SELECT l.id, l.company, COALESCE(l.type,''), COALESCE(l.phone,'')
		FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id
		WHERE l.vertical IN ('USA','United States')
		AND l.company LIKE '%FBI%'
		AND le.lead_id IS NULL
		ORDER BY l.company`)
	if err != nil {
		fmt.Fprintf(os.Stderr, "❌ Query failed: %v\n", err)
		return nil
	}
	defer rows.Close()

	var leads []DBLead
	for rows.Next() {
		var ld DBLead
		if err := rows.Scan(&ld.ID, &ld.Company, &ld.OrgType, &ld.Phone); err != nil {
			continue
		}
		city := strings.TrimPrefix(ld.Company, "FBI - ")
		city = strings.TrimSuffix(city, " Field Office")
		city = strings.TrimSuffix(city, " Field Division")
		city = strings.TrimSpace(city)
		if city == "" || city == ld.Company {
			city = ld.Company
		}
		ld.CityKey = normalizeCityKey(city)
		leads = append(leads, ld)
	}
	return leads
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
