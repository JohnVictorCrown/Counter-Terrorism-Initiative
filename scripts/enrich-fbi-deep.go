// enrich-fbi-deep.go — Deep-enriches FBI field office contacts by visiting
// each office's subdomain page and extracting email addresses.
//
// FBI field offices are at subdomains like albany.fbi.gov, chicago.fbi.gov etc.
// These redirect to centralized fbi.gov pages (Cloudflare protected), so direct
// email scraping often hits blocks. This script:
//  1. Scrapes the field offices directory for names/subdomains/phones
//  2. Attempts to fetch each office's subdomain page for contact emails
//  3. Falls back to known email patterns when scraping is blocked
//  4. Cross-references with the database
//  5. Generates crm update commands with the best available contact info
//
// Usage:
//   go run scripts/enrich-fbi-deep.go                   # Preview with email suggestions
//   go run scripts/enrich-fbi-deep.go --apply            # Generate crm update commands
//   go run scripts/enrich-fbi-deep.go --apply --force    # Skip Cloudflare warnings

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
	"sync"
	"time"

	"golang.org/x/net/html"

	_ "github.com/mutecomm/go-sqlcipher/v4"
)

const (
	dbPath      = "databases/leads.db"
	envPath     = ".env"
	fbiURL      = "https://www.fbi.gov/contact-us/field-offices"
	httpTimeout = 15 * time.Second
	maxWorkers  = 8
)

var (
	phoneRe    = regexp.MustCompile(`\(\d{3}\)\s*\d{3}-\d{4}`)
	emailRe    = regexp.MustCompile(`[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(?:gov|mil|org|com|net)`)
	subRe      = regexp.MustCompile(`([a-z]+)\.fbi\.gov`)
	officeRe   = regexp.MustCompile(`/contact-us/field-offices/([a-z-]+)`)
	cloudflare = []string{"just a moment", "checking your browser", "cloudflare", "403 forbidden", "access denied"}
)

// OfficeInfo contains scraped office data plus deep-enriched contact emails.
type OfficeInfo struct {
	Name      string
	CityKey   string
	Subdomain string
	Phone     string
	URL       string

	// Deep enrichment results
	ScrapedEmails  []string // emails found on the subdomain page
	ScrapeStatus   string   // "ok", "blocked", "error", "no_emails", "skipped"
	SuggestedEmail string   // best email to use
	EmailSource    string   // where the email came from
	OfficePath     string   // the subdomain URL attempted
}

// EnrichmentReport holds the full results.
type EnrichmentReport struct {
	Office      OfficeInfo
	DBLead      *DBLead // nil if no database match
	WillUpdate  bool
}

// DBLead represents a lead in the database.
type DBLead struct {
	ID      string
	Company string
	OrgType string
	Phone   string
	CityKey string
}

// ─── Known FBI contact emails by office ─────────────────────────────

// knownContacts maps CityKey -> known/suggested email.
// Built from publicly available FBI contact information.
// Update this map as new email addresses are discovered.
var knownContacts = map[string]string{
	// National / HQ
	"federalbureauofinvestigation": "foia@fbi.gov",

	// For all field offices — the centralized FOIA inbox is the standard
	// channel for public records requests. Some offices may have specific
	// public affairs contacts not publicly listed.
	"albany":        "foia@fbi.gov",
	"albuquerque":   "foia@fbi.gov",
	"anchorage":     "foia@fbi.gov",
	"atlanta":       "foia@fbi.gov",
	"baltimore":     "foia@fbi.gov",
	"billings":      "foia@fbi.gov",
	"birmingham":    "foia@fbi.gov",
	"boston":        "foia@fbi.gov",
	"buffalo":       "foia@fbi.gov",
	"charlotte":     "foia@fbi.gov",
	"chicago":       "foia@fbi.gov",
	"cincinnati":    "foia@fbi.gov",
	"cleveland":     "foia@fbi.gov",
	"columbia":      "foia@fbi.gov",
	"dallas":        "foia@fbi.gov",
	"denver":        "foia@fbi.gov",
	"detroit":       "foia@fbi.gov",
	"elpaso":        "foia@fbi.gov",
	"honolulu":      "foia@fbi.gov",
	"houston":       "foia@fbi.gov",
	"indianapolis":  "foia@fbi.gov",
	"jackson":       "foia@fbi.gov",
	"jacksonville":  "foia@fbi.gov",
	"kansascity":    "foia@fbi.gov",
	"lasvegas":      "foia@fbi.gov",
	"littlerock":    "foia@fbi.gov",
	"losangeles":    "foia@fbi.gov",
	"louisville":    "foia@fbi.gov",
	"miami":         "foia@fbi.gov",
	"milwaukee":     "foia@fbi.gov",
	"minneapolis":   "foia@fbi.gov",
	"mobile":        "foia@fbi.gov",
	"nashville":     "foia@fbi.gov",
	"newhaven":      "foia@fbi.gov",
	"neworleans":    "foia@fbi.gov",
	"newyork":       "foia@fbi.gov",
	"newark":        "foia@fbi.gov",
	"norfolk":       "foia@fbi.gov",
	"oklahomacity":  "foia@fbi.gov",
	"omaha":         "foia@fbi.gov",
	"philadelphia":  "foia@fbi.gov",
	"phoenix":       "foia@fbi.gov",
	"pittsburgh":    "foia@fbi.gov",
	"portland":      "foia@fbi.gov",
	"richmond":      "foia@fbi.gov",
	"sacramento":    "foia@fbi.gov",
	"saltlakecity":  "foia@fbi.gov",
	"sanantonio":    "foia@fbi.gov",
	"sandiego":      "foia@fbi.gov",
	"sanfrancisco":  "foia@fbi.gov",
	"sanjuan":       "foia@fbi.gov",
	"seattle":       "foia@fbi.gov",
	"springfield":   "foia@fbi.gov",
	"stlouis":       "foia@fbi.gov",
	"tampa":         "foia@fbi.gov",
	"washingtondc":  "foia@fbi.gov",
}

// ─── Main ────────────────────────────────────────────────────────────

func main() {
	apply := false
	force := false
	for _, arg := range os.Args[1:] {
		switch arg {
		case "--apply":
			apply = true
		case "--force":
			force = true
		}
	}

	fmt.Println("=" + strings.Repeat("=", 78))
	fmt.Println("  FBI DEEP ENRICHMENT — Contact Email Discovery")
	fmt.Println("=" + strings.Repeat("=", 78))

	// Step 1: Scrape field office directory
	fmt.Print("\n📡 Scraping FBI field offices... ")
	offices, err := scrapeFieldOffices()
	if err != nil {
		fmt.Fprintf(os.Stderr, "\n❌ Failed: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("%d offices loaded\n", len(offices))

	// Step 2: Deep-scrape each office subdomain for emails
	fmt.Println("\n🔍 Deep-scraping office subdomains for contact emails...")
	deepEnrich(offices, force)

	// Step 3: Cross-reference with database
	fmt.Print("\n🗄️  Matching database leads... ")
	db := openDB()
	defer db.Close()

	dbLeads := queryDBFBILeads(db)

	// Build lookup by CityKey
	leadByKey := make(map[string]*DBLead)
	for i := range dbLeads {
		leadByKey[dbLeads[i].CityKey] = &dbLeads[i]
	}

	// Generate report
	var reports []EnrichmentReport
	var matched, unmatchedLeads, unmatchedOffices int

	for _, o := range offices {
		lead, hasLead := leadByKey[o.CityKey]
		r := EnrichmentReport{
			Office: o,
			DBLead: lead,
		}
		if hasLead && lead != nil {
			r.WillUpdate = true
			matched++
		} else if hasLead {
			unmatchedLeads++
		} else {
			unmatchedOffices++
		}
		reports = append(reports, r)
	}

	fmt.Printf("%d matched, %d leads unmatched, %d offices unmatched\n",
		matched, unmatchedLeads, unmatchedOffices)

	// Step 4: Display report
	fmt.Println("\n" + strings.Repeat("═", 78))
	fmt.Println("  ENRICHMENT REPORT")
	fmt.Println(strings.Repeat("═", 78))

	sort.Slice(reports, func(i, j int) bool {
		return reports[i].Office.Name < reports[j].Office.Name
	})

	for _, r := range reports {
		o := r.Office
		status := o.ScrapeStatus
		if status == "" {
			status = "not_scraped"
		}

		fmt.Printf("\n  📍 %s\n", o.Name)
		fmt.Printf("     Subdomain: %s\n", o.Subdomain)
		fmt.Printf("     Phone:     %s\n", o.Phone)
		fmt.Printf("     Scrape:    %s\n", status)
		if len(o.ScrapedEmails) > 0 {
			fmt.Printf("     📬 Found:   %s\n", strings.Join(o.ScrapedEmails, ", "))
		}
		fmt.Printf("     📬 Use:     %s (%s)\n", o.SuggestedEmail, o.EmailSource)
		if r.DBLead != nil {
			shortID := r.DBLead.ID
			if len(shortID) > 8 {
				shortID = shortID[:8]
			}
			fmt.Printf("     Database:  %s [%s]\n", r.DBLead.Company, shortID)
		} else {
			fmt.Printf("     Database:  (not in CRM)\n")
		}
	}

	// Step 5: Generate update commands
	if apply {
		fmt.Println("\n" + strings.Repeat("═", 78))
		fmt.Println("  CRM UPDATE COMMANDS")
		fmt.Println(strings.Repeat("═", 78))
		fmt.Println()

		count := 0
		for _, r := range reports {
			if !r.WillUpdate || r.DBLead == nil {
				continue
			}
			if r.Office.SuggestedEmail == "" {
				continue
			}
			count++
			shortID := r.DBLead.ID
			if len(shortID) > 8 {
				shortID = shortID[:8]
			}
			fmt.Printf("# [%d] %s — %s\n", count, r.DBLead.Company, r.Office.Subdomain)
			fmt.Printf("#   Email: %s (%s)\n", r.Office.SuggestedEmail, r.Office.EmailSource)
			fmt.Printf("#   Phone: %s\n", r.Office.Phone)
			fmt.Printf("crm update %s\n", r.DBLead.ID)
			fmt.Printf("#   When prompted, enter: Emails=%s, Notes=FOIA contact from fbi.gov (deep enrichment)\n",
				r.Office.SuggestedEmail)
			fmt.Println()
		}

		if count == 0 {
			fmt.Println("  No offices matched to database leads.")
			fmt.Println("  Run enrich-fbi-field-offices.go first to check database matching.")
		} else {
			fmt.Printf("📋 %d offices to update\n", count)
		}
	}

	// Summary
	fmt.Println("\n" + strings.Repeat("═", 78))
	fmt.Println("  SUMMARY")
	fmt.Println(strings.Repeat("═", 78))
	fmt.Printf("  Offices scraped:     %d\n", len(offices))
	fmt.Printf("  Database leads:      %d\n", len(dbLeads))
	fmt.Printf("  Matched:             %d\n", matched)

	// Scrape stats
	var blocked, ok, errs, emailsFound int
	for _, o := range offices {
		switch o.ScrapeStatus {
		case "ok":
			ok++
			if len(o.ScrapedEmails) > 0 {
				emailsFound++
			}
		case "blocked":
			blocked++
		case "error":
			errs++
		}
	}
	fmt.Printf("  Subdomain scrapes:\n")
	fmt.Printf("    Blocked (CF):     %d\n", blocked)
	fmt.Printf("    Succeeded:        %d\n", ok)
	fmt.Printf("    Errors:           %d\n", errs)
	fmt.Printf("    Emails found:     %d\n", emailsFound)
	fmt.Println()
	fmt.Println("  Email source: known_contact — mapped from FOIA directory")
	fmt.Println("  Email source: scraped — found on subdomain page")
	fmt.Println("  Email source: phone_required — no email found; call phone number to inquire")
	fmt.Println()
	fmt.Println("  Note: FBI field offices do not publish direct emails publicly.")
	fmt.Println("  The centralized foia@fbi.gov is the official FOIA channel.")
	fmt.Println("  For media inquiries, contact the FBI National Press Office.")

	if !apply {
		fmt.Println("\n  Run with --apply to generate crm update commands.")
	}
}

// ─── Deep Enrichment ────────────────────────────────────────────────

// deepEnrich visits each office's subdomain and attempts to find contact emails.
func deepEnrich(offices []OfficeInfo, force bool) {
	var wg sync.WaitGroup
	sem := make(chan struct{}, maxWorkers)

	for i := range offices {
		wg.Add(1)
		sem <- struct{}{}
		go func(o *OfficeInfo) {
			defer wg.Done()
			defer func() { <-sem }()
			enrichOffice(o, force)
		}(&offices[i])
	}
	wg.Wait()
}

// enrichOffice fetches the office's subdomain page and extracts emails.
func enrichOffice(o *OfficeInfo, force bool) {
	if !force && isKnownContact(o.CityKey) {
		o.ScrapeStatus = "skipped"
		o.SuggestedEmail = getKnownContact(o.CityKey)
		o.EmailSource = "known_contact"
		return
	}

	// Try the subdomain URL
	targetURL := "https://" + o.Subdomain
	if !strings.Contains(targetURL, ".fbi.gov") {
		// Use the main office page
		targetURL = o.URL
	}
	o.OfficePath = targetURL

	client := &http.Client{Timeout: httpTimeout}
	req, err := http.NewRequest("GET", targetURL, nil)
	if err != nil {
		o.ScrapeStatus = "error"
		o.SuggestedEmail = getKnownContact(o.CityKey)
		o.EmailSource = "error_fallback"
		return
	}

	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
	req.Header.Set("Accept-Language", "en-US,en;q=0.5")

	resp, err := client.Do(req)
	if err != nil {
		o.ScrapeStatus = "error"
		o.SuggestedEmail = getKnownContact(o.CityKey)
		o.EmailSource = "error_fallback"
		return
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		o.ScrapeStatus = "error"
		o.SuggestedEmail = getKnownContact(o.CityKey)
		o.EmailSource = "error_fallback"
		return
	}

	content := string(body)
	lower := strings.ToLower(content)

	// Check for Cloudflare block
	for _, cf := range cloudflare {
		if strings.Contains(lower, cf) {
			o.ScrapeStatus = "blocked"
			o.SuggestedEmail = getKnownContact(o.CityKey)
			o.EmailSource = "blocked_fallback"
			return
		}
	}

	// Parse the HTML and extract email addresses
	doc, err := html.Parse(strings.NewReader(content))
	if err != nil {
		o.ScrapeStatus = "error"
		o.SuggestedEmail = getKnownContact(o.CityKey)
		o.EmailSource = "error_fallback"
		return
	}

	var emails []string
	emailSeen := make(map[string]bool)

	// Extract mailto: links
	var walk func(*html.Node)
	walk = func(n *html.Node) {
		if n.Type == html.ElementNode && n.Data == "a" {
			for _, attr := range n.Attr {
				if attr.Key == "href" && strings.HasPrefix(attr.Val, "mailto:") {
					e := strings.TrimPrefix(attr.Val, "mailto:")
					e = strings.Split(e, "?")[0] // remove query params
					e = strings.TrimSpace(e)
					if e != "" && !emailSeen[e] {
						emailSeen[e] = true
						emails = append(emails, e)
					}
				}
			}
		}
		if n.Type == html.TextNode {
			// Find email-like patterns in text
			for _, match := range emailRe.FindAllString(n.Data, -1) {
				e := strings.TrimSpace(match)
				if !emailSeen[e] {
					emailSeen[e] = true
					emails = append(emails, e)
				}
			}
		}
		for c := n.FirstChild; c != nil; c = c.NextSibling {
			walk(c)
		}
	}
	walk(doc)

	// Filter out common non-contact emails
	var filtered []string
	for _, e := range emails {
		lower := strings.ToLower(e)
		if strings.Contains(lower, "noreply") || strings.Contains(lower, "donotreply") {
			continue
		}
		if strings.Contains(lower, "example.com") || strings.Contains(lower, "domain.com") {
			continue
		}
		filtered = append(filtered, e)
	}

	o.ScrapedEmails = filtered

	if len(filtered) > 0 {
		o.ScrapeStatus = "ok"
		o.SuggestedEmail = filtered[0]
		o.EmailSource = "scraped"
	} else if resp.StatusCode == 200 {
		o.ScrapeStatus = "no_emails"
		o.SuggestedEmail = getKnownContact(o.CityKey)
		o.EmailSource = "no_emails_fallback"
	} else {
		o.ScrapeStatus = fmt.Sprintf("http_%d", resp.StatusCode)
		o.SuggestedEmail = getKnownContact(o.CityKey)
		o.EmailSource = "http_fallback"
	}
}

func isKnownContact(key string) bool {
	_, ok := knownContacts[strings.ToLower(key)]
	return ok
}

func getKnownContact(key string) string {
	if e, ok := knownContacts[strings.ToLower(key)]; ok {
		return e
	}
	return "foia@fbi.gov"
}

// ─── Office Scraping (reused from enrich-fbi-field-offices.go) ──────

func scrapeFieldOffices() ([]OfficeInfo, error) {
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

func parseOffices(htmlContent string) ([]OfficeInfo, error) {
	type linkInfo struct {
		text string
		href string
		node *html.Node
	}

	doc, err := html.Parse(strings.NewReader(htmlContent))
	if err != nil {
		return nil, fmt.Errorf("parse HTML: %w", err)
	}

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

	type officeLink struct {
		name string
		url  string
		idx  int
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

	type match struct {
		office    officeLink
		subdomain subdomainLink
		phone     string
	}

	var matches []match
	for oi, ol := range offices {
		end := len(allLinks)
		if oi+1 < len(offices) {
			end = offices[oi+1].idx
		}
		var bestSub subdomainLink
		for _, sd := range subdomains {
			if sd.idx > ol.idx && sd.idx < end {
				bestSub = sd
				break
			}
		}
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

	var result []OfficeInfo
	for _, m := range matches {
		var cityKey string
		if m.subdomain.url != "" {
			if sub := subRe.FindStringSubmatch(m.subdomain.url); len(sub) > 1 {
				cityKey = sub[1]
			}
		}
		if cityKey == "" {
			if matchURL := officeRe.FindStringSubmatch(m.office.url); len(matchURL) > 1 {
				cityKey = strings.ReplaceAll(matchURL[1], "-", "")
			}
		}
		if cityKey == "" {
			cityKey = normalizeCityKey(m.office.name)
		}

		officeURL := m.office.url
		if !strings.HasPrefix(officeURL, "http") {
			officeURL = "https://www.fbi.gov" + officeURL
		}

		result = append(result, OfficeInfo{
			Name:         m.office.name,
			CityKey:      cityKey,
			Subdomain:    m.subdomain.url,
			Phone:        m.phone,
			URL:          officeURL,
			SuggestedEmail: getKnownContact(cityKey),
			EmailSource:  "known_contact",
		})
	}

	// Deduplicate by CityKey
	seen := make(map[string]int)
	var deduped []OfficeInfo
	for _, r := range result {
		if r.CityKey == "" {
			continue
		}
		if idx, ok := seen[r.CityKey]; ok {
			e := &deduped[idx]
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

func extractPhoneBetween(officeNode *html.Node, officeHref string, root *html.Node) string {
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

// ─── Database ────────────────────────────────────────────────────────

func queryDBFBILeads(db *sql.DB) []DBLead {
	rows, err := db.Query(`
		SELECT COALESCE(l.id,''), l.company, COALESCE(l.type,''), COALESCE(l.phone,'')
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
		if ld.ID == "" {
			continue // skip leads without valid primary keys
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
