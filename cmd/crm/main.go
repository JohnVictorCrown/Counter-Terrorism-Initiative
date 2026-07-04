package main

import (
	"bufio"
	"bytes"
	"encoding/csv"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"syscall"
	"time"

	"golang.org/x/term"

	"counter-terrorism-initiative/internal/db"
	"counter-terrorism-initiative/internal/mail"
	"counter-terrorism-initiative/internal/models"
)

func main() {
	if len(os.Args) < 2 {
		runStats()
		return
	}

	cmd := os.Args[1]
	args := os.Args[2:]

	switch cmd {
	case "stats":
		runStats()
	case "list":
		runList(args)
	case "view":
		runView(args)
	case "add":
		runAdd()
	case "update":
		runUpdate(args)
	case "delete":
		runDelete(args)
	case "status":
		runStatus(args)
	case "log":
		runLog(args)
	case "followups":
		runFollowups()
	case "import":
		runImport(args)
	case "export":
		runExport(args)
	case "store-password":
		runStorePassword(args)
	case "run-dashboard":
		runDashboard()
	case "send-telegram":
		runSendTelegram()
	case "send-mail":
		runSendMail(args)
	case "campaign":
		runCampaign(args)
	case "help", "--help", "-h":
		printUsage()
	default:
		fmt.Fprintf(os.Stderr, "Unknown command: %s\n\n", cmd)
		printUsage()
		os.Exit(1)
	}
}

func printUsage() {
	fmt.Println(`WaterParty CRM — Go CLI for lead management & outreach tracking.

Usage:
    crm stats                     Dashboard overview
    crm list                      All leads
    crm list --tier 1             Filter by tier
    crm list --status cold        Filter by status
    crm list --search "Monashees" Search
    crm add                       Interactive add
    crm view <id>                 Lead detail
    crm update <id>               Interactive update
    crm delete <id>               Delete lead
    crm status <id> <new_status>  Quick status change
    crm log <id>                  Log activity
    crm followups                 Due follow-ups
    crm import --path file.csv    Import from CSV
    crm export --path file.csv    Export to CSV
    crm store-password            Store Gmail app password
    crm store-password --password "xxxx"  Store via flag
    crm run-dashboard              Launch the web dashboard and open browser
    crm send-telegram              Send email campaign to Telegram
    crm send-mail                 Send BCC email via Gmail SMTP
    crm send-mail --emails "a@b.com" --subject "Hi" --body "Hello" \\
    crm send-mail --body-file body.txt --attach file.pdf --confirm
    crm campaign                  Send segmented campaign to leads
    crm campaign --tier 1 --subject "Hi" --body "Hello"
    crm campaign --type "Intelligence" --vertical "USA" --dry-run
	`)
}

// ─── Stats ────────────────────────────────────────────────────────────────

func runStats() {
	s, err := db.GetStats()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	fmt.Println()
	fmt.Println(strings.Repeat("=", 50))
	fmt.Println("  WATERPARTY CRM — DASHBOARD")
	fmt.Println(strings.Repeat("=", 50))
	fmt.Printf("  Total leads:     %d\n", s.Total)
	fmt.Printf("  Follow-ups due:  %d\n", s.FollowupsDue)
	fmt.Println()
	fmt.Println("  By Tier:")
	for _, t := range s.ByTier {
		label := t.Name
		if l, ok := models.TierLabels[t.Name]; ok {
			label = l
		}
		fmt.Printf("    %s: %d\n", label, t.Count)
	}
	fmt.Println()
	fmt.Println("  By Status:")
	for _, st := range s.ByStatus {
		fmt.Printf("    %s: %d\n", st.Name, st.Count)
	}
	fmt.Println()
	if len(s.Recent) > 0 {
		fmt.Println("  Recent:")
		for _, r := range s.Recent {
			shortID := r.ID
			if len(shortID) > 8 {
				shortID = shortID[:8]
			}
			fmt.Printf("    [%s] %s — %s\n", shortID, r.Company, r.Status)
		}
	}
	fmt.Println()
}

// ─── List ─────────────────────────────────────────────────────────────────

func runList(args []string) {
	fs := newFlagSet("list")
	tier := fs.String("tier", "", "Filter by tier")
	status := fs.String("status", "", "Filter by status (or 'active' for non-closed)")
	search := fs.String("search", "", "Search term")
	vertical := fs.String("vertical", "", "Filter by vertical")
	ctype := fs.String("type", "", "Filter by type")
	verbose := fs.Bool("v", false, "Verbose output")
	fs.Parse(args)

	f := db.LeadFilter{
		Tier:     *tier,
		Status:   *status,
		Search:   *search,
		Vertical: *vertical,
		Type:     *ctype,
	}

	leads, err := db.GetLeads(f)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	if len(leads) == 0 {
		fmt.Println("No leads found.")
		return
	}

	fmt.Printf("\n%d lead(s):\n\n", len(leads))
	for _, lead := range leads {
		printLead(lead, *verbose)
	}
}

// ─── View ─────────────────────────────────────────────────────────────────

func runView(args []string) {
	if len(args) < 1 {
		fmt.Fprintln(os.Stderr, "Usage: crm view <id>")
		os.Exit(1)
	}
	id := args[0]

	lead, err := db.GetContact(id)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
	if lead == nil {
		fmt.Println("Lead not found.")
		return
	}

	printLead(*lead, true)

	outreach, err := db.GetOutreach(id)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	if len(outreach) > 0 {
		fmt.Printf("  All Activity (%d):\n", len(outreach))
		for _, o := range outreach {
			created := o.CreatedAt
			if len(created) > 10 {
				created = created[:10]
			}
			fmt.Printf("    [%s] %s: %s\n", created, o.ActivityType, o.Notes)
			if o.Outcome != "" {
				fmt.Printf("      Outcome: %s\n", o.Outcome)
			}
		}
	} else {
		fmt.Println("  No activity logged.")
	}
}

// ─── Add ──────────────────────────────────────────────────────────────────

func runAdd() {
	reader := bufio.NewReader(os.Stdin)

	fmt.Println("\nAdd new lead (press Enter to skip optional fields):")

	input := models.LeadInput{}

	input.Company = readLine(reader, "  Company *: ")
	if input.Company == "" {
		fmt.Println("Company is required.")
		return
	}

	input.ContactName = readLine(reader, "  Contact name: ")
	emailsStr := readLine(reader, "  Emails (comma-separated): ")
	if emailsStr != "" {
		for _, e := range strings.Split(emailsStr, ",") {
			e = strings.TrimSpace(e)
			if e != "" {
				input.Emails = append(input.Emails, e)
			}
		}
	}
	input.Phone = readLine(reader, "  Phone: ")
	input.Website = readLine(reader, "  Website: ")

	fmt.Println("  Tier: 1=VC  2=Corporate  3=Local  4=Grant  5=Venue  6=Media")
	tier := readLine(reader, "  Tier [3]: ")
	if tier == "" {
		tier = "3"
	}
	input.Tier = tier

	fmt.Println("  Valid types: " + strings.Join(models.ValidTypes, ", "))
	input.Type = readLine(reader, "  Type *: ")
	if input.Type == "" {
		fmt.Println("Type is required.")
		return
	}

	input.Vertical = readLine(reader, "  Vertical (country/region/topic): ")
	input.CheckSize = readLine(reader, "  Check size: ")
	input.PitchAngle = readLine(reader, "  Pitch angle: ")
	input.NextAction = readLine(reader, "  Next action: ")
	input.NextActionDate = readLine(reader, "  Next action date (YYYY-MM-DD): ")
	input.Notes = readLine(reader, "  Notes: ")

	lid, err := db.AddLead(input)
	if err != nil {
		fmt.Printf("  Error: %v\n", err)
		return
	}
	fmt.Printf("\nLead created: %s\n", lid)
}

// ─── Update ───────────────────────────────────────────────────────────────

func runUpdate(args []string) {
	if len(args) < 1 {
		fmt.Fprintln(os.Stderr, "Usage: crm update <id>")
		os.Exit(1)
	}
	id := args[0]

	lead, err := db.GetContact(id)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
	if lead == nil {
		fmt.Println("Lead not found.")
		return
	}

	reader := bufio.NewReader(os.Stdin)
	fmt.Printf("\nEditing: %s (leave blank to keep current value)\n\n", lead.Company)
	fmt.Printf("  Valid types: %s\n", strings.Join(models.ValidTypes, ", "))

	fields := []struct {
		Name    string
		Current string
	}{
		{"company", lead.Company},
		{"contact_name", lead.ContactName},
		{"emails", strings.Join(lead.Emails, ", ")},
		{"phone", lead.Phone},
		{"website", lead.Website},
		{"tier", lead.Tier},
		{"type", lead.Type},
		{"vertical", lead.Vertical},
		{"check_size", lead.CheckSize},
		{"pitch_angle", lead.PitchAngle},
		{"next_action", lead.NextAction},
		{"next_action_date", lead.NextActionDate},
		{"notes", lead.Notes},
	}

	data := make(map[string]string)
	for _, f := range fields {
		val := readLine(reader, fmt.Sprintf("  %s [%s]: ", f.Name, f.Current))
		if val != "" {
			data[f.Name] = val
		}
	}

	if len(data) > 0 {
		err := db.UpdateLead(id, data)
		if err != nil {
			fmt.Printf("  Error: %v\n", err)
			return
		}
		fmt.Println("Lead updated.")
	} else {
		fmt.Println("No changes.")
	}
}

// ─── Delete ───────────────────────────────────────────────────────────────

func runDelete(args []string) {
	if len(args) < 1 {
		fmt.Fprintln(os.Stderr, "Usage: crm delete <id>")
		os.Exit(1)
	}
	id := args[0]

	lead, err := db.GetContact(id)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
	if lead == nil {
		fmt.Println("Lead not found.")
		return
	}

	reader := bufio.NewReader(os.Stdin)
	confirm := readLine(reader, fmt.Sprintf("Delete '%s'? (y/N): ", lead.Company))
	if strings.ToLower(strings.TrimSpace(confirm)) == "y" {
		err := db.DeleteLead(id)
		if err != nil {
			fmt.Printf("Error: %v\n", err)
			return
		}
		fmt.Println("Deleted.")
	}
}

// ─── Status ───────────────────────────────────────────────────────────────

func runStatus(args []string) {
	if len(args) < 2 {
		fmt.Fprintln(os.Stderr, "Usage: crm status <id> <new_status>")
		fmt.Fprintf(os.Stderr, "Valid statuses: %s\n", strings.Join(models.Statuses, ", "))
		os.Exit(1)
	}
	id := args[0]
	status := args[1]

	valid := false
	for _, s := range models.Statuses {
		if s == status {
			valid = true
			break
		}
	}
	if !valid {
		fmt.Fprintf(os.Stderr, "Invalid status. Options: %s\n", strings.Join(models.Statuses, ", "))
		os.Exit(1)
	}

	err := db.UpdateLead(id, map[string]string{"status": status})
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	fmt.Printf("Status updated to '%s'.\n", status)
}

// ─── Log ──────────────────────────────────────────────────────────────────

func runLog(args []string) {
	if len(args) < 1 {
		fmt.Fprintln(os.Stderr, "Usage: crm log <id>")
		os.Exit(1)
	}
	id := args[0]

	lead, err := db.GetContact(id)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
	if lead == nil {
		fmt.Println("Lead not found.")
		return
	}

	reader := bufio.NewReader(os.Stdin)
	fmt.Printf("\nLog activity for: %s\n", lead.Company)
	fmt.Println("Types: email, call, meeting, note")
	activityType := readLine(reader, "  Type [email]: ")
	if activityType == "" {
		activityType = "email"
	}
	notes := readLine(reader, "  Notes: ")
	outcome := readLine(reader, "  Outcome: ")

	_, err = db.LogOutreach(id, activityType, notes, outcome)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	fmt.Println("Activity logged.")
}

// ─── Followups ────────────────────────────────────────────────────────────

func runFollowups() {
	leads, err := db.GetFollowupsDue()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	if len(leads) == 0 {
		fmt.Println("No follow-ups due today.")
		return
	}

	fmt.Printf("\n%d follow-up(s) due:\n\n", len(leads))
	for _, lead := range leads {
		shortID := lead.ID
		if len(shortID) > 8 {
			shortID = shortID[:8]
		}
		action := lead.NextAction
		if action == "" {
			action = "No action"
		}
		fmt.Printf("  [%s] %s — %s (%s)\n", shortID, lead.Company, action, lead.NextActionDate)
	}
}

// ─── Send Mail ────────────────────────────────────────────────────────────

func runSendMail(args []string) {
	fs := newFlagSet("send-mail")
	emailsStr := fs.String("emails", "", "Comma-separated BCC recipient emails (required)")
	subject := fs.String("subject", "", "Email subject line (required)")
	body := fs.String("body", "", "Email body text (required unless --body-file used)")
	bodyFile := fs.String("body-file", "", "Read email body from a text file")
	attach := fs.String("attach", "", "File to attach (comma-separated for multiple)")
	fromName := fs.String("from-name", "John Victor @ WaterParty", "Sender display name")
	dryRun := fs.Bool("dry-run", false, "Print what would be sent without actually sending")
	confirm := fs.Bool("confirm", false, "Show recipients and ask for confirmation before sending")
	fs.Parse(args)

	// Validate required flags
	if *emailsStr == "" {
		fmt.Fprintln(os.Stderr, "❌ --emails is required")
		fs.Usage()
		os.Exit(1)
	}
	if *subject == "" {
		fmt.Fprintln(os.Stderr, "❌ --subject is required")
		fs.Usage()
		os.Exit(1)
	}
	if *body == "" && *bodyFile == "" {
		fmt.Fprintln(os.Stderr, "❌ Either --body or --body-file is required")
		fs.Usage()
		os.Exit(1)
	}
	if *body != "" && *bodyFile != "" {
		fmt.Fprintln(os.Stderr, "❌ Use either --body or --body-file, not both")
		os.Exit(1)
	}

	// Read body content
	bodyText := *body
	if *bodyFile != "" {
		data, err := os.ReadFile(*bodyFile)
		if err != nil {
			fmt.Fprintf(os.Stderr, "❌ Cannot read body file '%s': %v\n", *bodyFile, err)
			os.Exit(1)
		}
		bodyText = string(data)
	}

	// Parse recipients
	recipients := strings.Split(*emailsStr, ",")
	var cleaned []string
	for _, r := range recipients {
		r = strings.TrimSpace(r)
		if r != "" {
			cleaned = append(cleaned, r)
		}
	}
	recipients = cleaned

	if len(recipients) == 0 {
		fmt.Fprintln(os.Stderr, "❌ No valid email addresses provided")
		os.Exit(1)
	}

	// Validate email formats
	var invalid []string
	for _, r := range recipients {
		if strings.Count(r, "@") != 1 || !strings.Contains(strings.Split(r, "@")[1], ".") || strings.Contains(r, " ") {
			invalid = append(invalid, r)
		}
	}
	if len(invalid) > 0 {
		fmt.Fprintf(os.Stderr, "❌ Invalid email addresses: %s\n", strings.Join(invalid, ", "))
		os.Exit(1)
	}

	// Parse attachments
	var attachments []string
	if *attach != "" {
		for _, a := range strings.Split(*attach, ",") {
			a = strings.TrimSpace(a)
			if a != "" {
				if _, err := os.Stat(a); os.IsNotExist(err) {
					fmt.Fprintf(os.Stderr, "❌ Attachment not found: %s\n", a)
					os.Exit(1)
				}
				attachments = append(attachments, a)
			}
		}
	}

	// Confirm mode
	if *confirm {
		fmt.Printf("\n📧 Ready to send to %d recipients via BCC:\n", len(recipients))
		for _, r := range recipients {
			fmt.Printf("   • %s\n", r)
		}
		fmt.Printf("\n   Subject: %s\n", *subject)
		for _, a := range attachments {
			info, _ := os.Stat(a)
			size := ""
			if info != nil {
				size = fmt.Sprintf(" (%.1f KB)", float64(info.Size())/1024)
			}
			fmt.Printf("   Attach:  %s%s\n", a, size)
		}
		preview := strings.ReplaceAll(bodyText, "\n", " ")
		if len(preview) > 100 {
			preview = preview[:100]
		}
		fmt.Printf("   Body preview: %s...\n", preview)

		reader := bufio.NewReader(os.Stdin)
		fmt.Print("\n   Send? (y/N): ")
		ans, _ := reader.ReadString('\n')
		if strings.TrimSpace(strings.ToLower(ans)) != "y" {
			fmt.Println("❌ Cancelled")
			os.Exit(0)
		}
		fmt.Println()
	}

	// Dry run
	if *dryRun {
		fmt.Println("\n🔍 DRY RUN — No email sent")
		fmt.Printf("   From:       %s <%s>\n", *fromName, db.GmailAddr)
		fmt.Printf("   Subject:    %s\n", *subject)
		fmt.Printf("   BCC (%d): %s\n", len(recipients), strings.Join(recipients, ", "))
		for _, a := range attachments {
			info, _ := os.Stat(a)
			size := ""
			if info != nil {
				size = fmt.Sprintf(" (%.1f KB)", float64(info.Size())/1024)
			}
			fmt.Printf("   Attach:     %s%s\n", a, size)
		}
		fmt.Printf("   Body:\n%s\n", bodyText)
		return
	}

	// Send
	result := mail.SendMailCLI(recipients, *subject, bodyText, *fromName, attachments)
	if !result.Success {
		fmt.Fprintf(os.Stderr, "❌ %s\n", result.Error)
		os.Exit(1)
	}

	attachInfo := ""
	if len(attachments) > 0 {
		attachInfo = fmt.Sprintf(" with %d attachment(s)", len(attachments))
	}
	fmt.Printf("✅ Email sent to %d recipients via BCC%s\n", result.Count, attachInfo)
	fmt.Printf("   Subject: %s\n", *subject)

	// Log to outreach_log
	for _, r := range recipients {
		db.LogEmail("", r, *subject, bodyText, "sent", "")
	}
}

// ─── Campaign ───────────────────────────────────────────────────────────────

func runCampaign(args []string) {
	fs := newFlagSet("campaign")
	tier := fs.String("tier", "", "Filter by tier (1=VC, 2=Corporate, 3=Local)")
	ctype := fs.String("type", "", "Filter by organization type")
	vertical := fs.String("vertical", "", "Filter by vertical/country")
	status := fs.String("status", "cold", "Filter by status (default: cold)")
	subject := fs.String("subject", "", "Email subject line (required)")
	body := fs.String("body", "", "Email body text (required unless --body-file used)")
	bodyFile := fs.String("body-file", "", "Read email body from a text file")
	fromName := fs.String("from-name", "John Victor @ WaterParty", "Sender display name")
	dryRun := fs.Bool("dry-run", false, "Preview the campaign without sending")
	confirm := fs.Bool("confirm", false, "Show full segment summary and ask for confirmation")
	noStatusUpdate := fs.Bool("no-status-update", false, "Don't auto-update status to 'contacted'")
	fs.Parse(args)

	// Validate required flags
	if *subject == "" {
		fmt.Fprintln(os.Stderr, "❌ --subject is required")
		fs.Usage()
		os.Exit(1)
	}
	if *body == "" && *bodyFile == "" {
		fmt.Fprintln(os.Stderr, "❌ Either --body or --body-file is required")
		fs.Usage()
		os.Exit(1)
	}
	if *body != "" && *bodyFile != "" {
		fmt.Fprintln(os.Stderr, "❌ Use either --body or --body-file, not both")
		os.Exit(1)
	}

	// Read body content
	bodyText := *body
	if *bodyFile != "" {
		data, err := os.ReadFile(*bodyFile)
		if err != nil {
			fmt.Fprintf(os.Stderr, "❌ Cannot read body file '%s': %v\n", *bodyFile, err)
			os.Exit(1)
		}
		bodyText = string(data)
	}

	// Query leads matching the segment filter
	f := db.LeadFilter{
		Tier:     *tier,
		Status:   *status,
		Vertical: *vertical,
		Type:     *ctype,
	}

	leads, err := db.GetLeads(f)
	if err != nil {
		fmt.Fprintf(os.Stderr, "❌ Error querying leads: %v\n", err)
		os.Exit(1)
	}

	// Collect emails and segment stats
	var emailable []models.Contact
	emailSet := make(map[string]bool)
	var duplicateCount, noEmailCount int
	typeCount := make(map[string]int)
	tierCount := make(map[string]int)

	for _, lead := range leads {
		typeCount[lead.Type]++
		tierCount[lead.Tier]++

		// Use the primary (first) email for campaign sending
		email := ""
		if len(lead.Emails) > 0 {
			email = strings.TrimSpace(lead.Emails[0])
		}
		if email == "" || strings.EqualFold(email, "none") {
			noEmailCount++
			continue
		}
		if !strings.Contains(email, "@") || strings.Count(email, "@") != 1 {
			noEmailCount++
			continue
		}
		parts := strings.Split(email, "@")
		if len(parts) != 2 || !strings.Contains(parts[1], ".") {
			noEmailCount++
			continue
		}

		if emailSet[email] {
			duplicateCount++
			continue
		}
		emailSet[email] = true
		emailable = append(emailable, lead)
	}

	// Show campaign summary
	tierLabel := *tier
	if l, ok := models.TierLabels[*tier]; ok {
		tierLabel = l
	}

	fmt.Println()
	fmt.Println(strings.Repeat("═", 58))
	fmt.Println("  📬 CAMPAIGN SEGMENT SUMMARY")
	fmt.Println(strings.Repeat("═", 58))

	// Filter description
	var filterParts []string
	if *tier != "" {
		filterParts = append(filterParts, fmt.Sprintf("Tier: %s", tierLabel))
	}
	if *ctype != "" {
		filterParts = append(filterParts, fmt.Sprintf("Type: %s", *ctype))
	}
	if *vertical != "" {
		filterParts = append(filterParts, fmt.Sprintf("Vertical: %s", *vertical))
	}
	if *status != "" {
		filterParts = append(filterParts, fmt.Sprintf("Status: %s", *status))
	}
	filterDesc := "All leads"
	if len(filterParts) > 0 {
		filterDesc = strings.Join(filterParts, " | ")
	}
	fmt.Printf("  Filter: %s\n", filterDesc)
	fmt.Printf("  Total in segment:    %d leads\n", len(leads))
	fmt.Printf("  With valid email:    %d\n", len(emailable))
	fmt.Printf("  Without email:       %d\n", noEmailCount)
	if duplicateCount > 0 {
		fmt.Printf("  Duplicate emails:    %d\n", duplicateCount)
	}

	// Show type breakdown
	fmt.Println()
	fmt.Println("  Segment Composition:")
	for _, t := range sortedKeys(typeCount) {
		pct := typeCount[t] * 100 / len(leads)
		fmt.Printf("    %-20s %3d (%d%%)\n", t, typeCount[t], pct)
	}

	// Show tier breakdown
	fmt.Println()
	fmt.Println("  By Tier:")
	for _, t := range sortedKeys(tierCount) {
		label := t
		if l, ok := models.TierLabels[t]; ok {
			label = l
		}
		pct := tierCount[t] * 100 / len(leads)
		fmt.Printf("    %-12s %3d (%d%%)\n", label, tierCount[t], pct)
	}

	// Sample recipients
	if len(emailable) > 0 {
		fmt.Println()
		fmt.Printf("  First 5 recipients:\n")
		max := 5
		if len(emailable) < max {
			max = len(emailable)
		}
		for _, lead := range emailable[:max] {
			shortID := lead.ID
			if len(shortID) > 8 {
				shortID = shortID[:8]
			}
			// Display primary email for this lead
			displayEmail := ""
			if len(lead.Emails) > 0 {
				displayEmail = lead.Emails[0]
			}
			fmt.Printf("    • [%s] %-30s %s\n", shortID, lead.Company, displayEmail)
		}
		if len(emailable) > 5 {
			fmt.Printf("    • ... and %d more\n", len(emailable)-5)
		}
	}

	// Subject and body preview
	fmt.Println()
	fmt.Printf("  Subject: %s\n", *subject)
	preview := strings.ReplaceAll(bodyText, "\n", " ")
	if len(preview) > 100 {
		preview = preview[:100]
	}
	fmt.Printf("  Body preview: %s...\n", preview)

	if len(emailable) == 0 {
		fmt.Println()
		fmt.Println("⚠️  No leads with valid email addresses in this segment.")
		fmt.Println("   Use --dry-run to see the full breakdown, or adjust your filter.")
		os.Exit(0)
	}

	// Dry run
	if *dryRun {
		fmt.Println()
		fmt.Println("🔍 DRY RUN — No emails sent. Use --confirm to send.")
		return
	}

	// Confirm mode: ask before sending
	if *confirm {
		fmt.Println()
		fmt.Printf("📧 Ready to send to %d recipients via BCC.\n", len(emailable))
		if !*noStatusUpdate {
			fmt.Printf("   Status will be updated from '%s' to 'contacted'.\n", *status)
		}
		fmt.Println()
		reader := bufio.NewReader(os.Stdin)
		fmt.Print("  Send now? (y/N): ")
		ans, _ := reader.ReadString('\n')
		if strings.TrimSpace(strings.ToLower(ans)) != "y" {
			fmt.Println("❌ Campaign cancelled.")
			os.Exit(0)
		}
		fmt.Println()
	}

	// Extract just the email addresses for sending
	emails := make([]string, len(emailable))
	for i, lead := range emailable {
		if len(lead.Emails) > 0 {
			emails[i] = strings.TrimSpace(lead.Emails[0])
		}
	}

	// Send
	fmt.Printf("📨 Sending campaign to %d recipients...\n", len(emails))
	result := mail.SendMailCLI(emails, *subject, bodyText, *fromName, nil)
	if !result.Success {
		fmt.Fprintf(os.Stderr, "❌ %s\n", result.Error)
		os.Exit(1)
	}

	fmt.Printf("✅ Campaign sent to %d recipients\n", result.Count)
	fmt.Printf("   Subject: %s\n", *subject)

	// Log every email sent and update statuses
	updated := 0
	for _, lead := range emailable {
		sentEmail := ""
		if len(lead.Emails) > 0 {
			sentEmail = lead.Emails[0]
		}
		db.LogEmail(lead.ID, sentEmail, *subject, bodyText, "sent", "")

		if !*noStatusUpdate && lead.Status != "contacted" {
			_ = db.UpdateLead(lead.ID, map[string]string{
				"status": "contacted",
			})
			updated++
		}
	}

	if updated > 0 {
		fmt.Printf("   Status updated to 'contacted' for %d leads\n", updated)
	}
	fmt.Println()
	fmt.Println("📋 Next steps:")
	fmt.Println("   1. Track replies: crm list --status replied")
	fmt.Println("   2. Log follow-ups: crm log <id>")
	fmt.Println("   3. View due follow-ups: crm followups")
}

// sortedKeys returns map keys sorted alphabetically (for deterministic output)
func sortedKeys(m map[string]int) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

// ─── Store Password ────────────────────────────────────────────────────────

func runStorePassword(args []string) {
	fs := newFlagSet("store-password")
	password := fs.String("password", "", "Gmail app password (omit for secure prompt)")
	fs.Parse(args)

	fmt.Println("🔐 WaterParty — Store Gmail App Password")
	fmt.Printf("   Account: %s\n", db.GmailAddr)
	fmt.Println("   Database: SQLCipher AES-256 encrypted")
	fmt.Println()

	var appPassword string
	if *password != "" {
		fmt.Println("⚠️  Warning: --password is visible in process listings and shell history.")
		fmt.Println("   Consider omitting it next time for a secure prompt.")
		fmt.Println()
		appPassword = *password
	} else {
		fmt.Print("Enter Gmail app password: ")
		pw1, _ := term.ReadPassword(int(syscall.Stdin))
		fmt.Println()
		appPassword = strings.TrimSpace(string(pw1))
		if appPassword == "" {
			fmt.Println("❌ Password cannot be empty")
			return
		}

		fmt.Print("Confirm password: ")
		pw2, _ := term.ReadPassword(int(syscall.Stdin))
		fmt.Println()
		if strings.TrimSpace(string(pw2)) != appPassword {
			fmt.Println("❌ Passwords do not match")
			return
		}
	}

	err := db.StoreAppPassword(db.GmailAddr, appPassword)
	if err != nil {
		fmt.Printf("❌ Error: %v\n", err)
		return
	}

	fmt.Println("✅ App password stored in SQLCipher-encrypted database: mail-credentials.db")
	fmt.Println("   Database encryption password: EMAIL_DB_PASSWORD from .env")
	fmt.Println("   App password stored in plain text inside the encrypted DB")
	fmt.Println()
	fmt.Println("📬 You can now use the dashboard at http://localhost:5000 to send emails.")
}

// ─── Run Dashboard ─────────────────────────────────────────────────────────

func runDashboard() {
	const host = "0.0.0.0"
	const port = 5000
	url := fmt.Sprintf("http://localhost:%d", port)

	fmt.Println(strings.Repeat("=", 55))
	fmt.Println("  🕵️  CRM Dashboard Launcher")
	fmt.Println(strings.Repeat("=", 55))
	fmt.Println()
	fmt.Printf("  Starting server on %s ...\n", url)
	fmt.Println()

	// Resolve path to the dashboard binary
	var serverBin string
	if exe, err := os.Executable(); err == nil {
		// Same directory as the CRM binary
		serverBin = filepath.Join(filepath.Dir(exe), "dashboard")
		if runtime.GOOS == "windows" {
			serverBin += ".exe"
		}
	}
	if _, err := os.Stat(serverBin); os.IsNotExist(err) {
		// Build the dashboard first
		fmt.Println("  Building dashboard binary...")
		build := exec.Command("go", "build", "./cmd/dashboard/")
		build.Stderr = os.Stderr
		if err := build.Run(); err != nil {
			fmt.Fprintf(os.Stderr, "❌ Failed to build dashboard: %v\n", err)
			os.Exit(1)
		}
		serverBin = "dashboard"
		if runtime.GOOS == "windows" {
			serverBin = "dashboard.exe"
		}
	}

	// Start the dashboard process
	cmd := exec.Command(serverBin)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Start(); err != nil {
		fmt.Fprintf(os.Stderr, "❌ Failed to start dashboard: %v\n", err)
		os.Exit(1)
	}

	// Wait briefly for the server to start, detect early exit
	done := make(chan error, 1)
	go func() {
		done <- cmd.Wait()
	}()

	select {
	case err := <-done:
		fmt.Fprintf(os.Stderr, "❌ Server failed to start: %v\n", err)
		os.Exit(1)
	case <-time.After(2 * time.Second):
		// Server appears to be running
	}

	// Open browser
	fmt.Println("  ✅ Server is running!")
	fmt.Printf("  🌐 Opening %s in your browser...\n", url)
	openBrowser(url)
	fmt.Println()
	fmt.Println("  Press Ctrl+C to stop the server.")
	fmt.Println()

	// Wait for interrupt signal
	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM)
	<-sig

	fmt.Println()
	fmt.Println("  Shutting down...")
	cmd.Process.Signal(syscall.SIGINT)
	cmd.Wait()
	fmt.Println("  ✅ Server stopped.")
}

// ─── Send Telegram ─────────────────────────────────────────────────────────

func runSendTelegram() {
	token := db.LoadEnvVar("TELEGRAM_BOT_TOKEN")
	chatID := db.LoadEnvVar("TELEGRAM_CHAT_ID")

	if token == "" {
		fmt.Fprintln(os.Stderr, "Erro: TELEGRAM_BOT_TOKEN nao definido.")
		fmt.Fprintln(os.Stderr, "      Adicione ao arquivo .env ou exporte como variavel de ambiente.")
		os.Exit(1)
	}
	if chatID == "" {
		fmt.Fprintln(os.Stderr, "Erro: TELEGRAM_CHAT_ID nao definido.")
		fmt.Fprintln(os.Stderr, "      Adicione ao arquivo .env ou exporte como variavel de ambiente.")
		fmt.Fprintln(os.Stderr, "")
		fmt.Fprintln(os.Stderr, "      Para encontrar seu CHAT_ID:")
		fmt.Fprintln(os.Stderr, "      1. Envie qualquer mensagem para o seu bot no Telegram")
		fmt.Fprintln(os.Stderr, "      2. Execute: curl -s https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getUpdates")
		fmt.Fprintln(os.Stderr, "      3. Procure por 'chat': {'id': SEU_NUMERO_AQUI} na resposta")
		os.Exit(1)
	}

	contactList := "contact@monashees.com, contato@domo.vc, info@canary.com.br, biz@cesar.org.br"

	emailMonashees := `EMAIL 1 — Monashees (VC - English)
To: contact@monashees.com
Subject: WaterParty — Tinder for parties, launching in Recife

Hi Monashees team,

I'm reaching out from Water Enterprises (Stellarium Foundation). We built WaterParty — a Tinder-style app for discovering parties and events, with integrated payments (tipping + crowdfunding) and auto-currency detection via GPS.

Why it matters: The global nightlife market is $150B+. No app combines discovery + chat + payments in one place. We do.

Traction: Production-ready MVP (React 19, Bun, Turso, Stripe). Cross-platform (iOS + Android). Multi-currency GPS detection. WebSocket real-time.

Launch strategy: Recife first (4M pop, 100K+ students, Porto Digital). Prove density, expand city-by-city.

The ask: Raising $250K-$500K pre-seed to acquire our first 25K users and expand to new cities.

Attached: pitch deck + exec summary. Would love 15 min to show the demo.

Best,
John Victor
Water Enterprises / Stellarium Foundation
water.enterprises.org@gmail.com`

	emailDomo := `EMAIL 2 — DOMO.VC (VC - English)
To: contato@domo.vc
Subject: WaterParty — Tinder for parties, launching in Recife

Hi DOMO team,

I'm reaching out from Water Enterprises. We built WaterParty — a Tinder-style app for discovering parties and events, with integrated payments and auto-currency detection.

The ask: Raising $250K-$500K pre-seed launching in Recife.

Attached: pitch deck + exec summary. Would love to show you the demo.

Best,
John Victor
water.enterprises.org@gmail.com`

	emailCesar := `EMAIL 3 — CESAR Recife (Local - Portugues)
To: biz@cesar.org.br
Assunto: WaterParty — App de descoberta de festas, lancando em Recife

Ola equipe CESAR,

Sou da Water Enterprises e estamos lancando o WaterParty em Recife — um app estilo Tinder para descobrir festas e eventos, com pagamentos integrados e deteccao automatica de moeda por GPS.

Tracao: MVP pronto (React 19, Bun, Turso, Stripe). iOS + Android.

Pedido: Captando R$ 1M-R$ 2M pre-seed.

Gostaria de saber mais sobre programas de incubacao com o CESAR Labs.

Abraco,
John Victor
water.enterprises.org@gmail.com`

	message := fmt.Sprintf(`WATERPARTY EMAIL CAMPAIGN

CONTATOS PARA ENVIAR EMAIL:
%s

---

%s

---

%s

---

%s`, contactList, emailMonashees, emailDomo, emailCesar)

	url := fmt.Sprintf("https://api.telegram.org/bot%s/sendMessage", token)

	payload := map[string]string{
		"chat_id": chatID,
		"text":    message,
	}

	body, _ := json.Marshal(payload)

	fmt.Println("Enviando campanha de email do WaterParty para o Telegram...")
	fmt.Printf("  Chat ID: %s\n", chatID)
	fmt.Printf("  Tamanho da mensagem: %d caracteres\n", len(message))
	fmt.Println()

	req, err := http.NewRequest("POST", url, bytes.NewReader(body))
	if err != nil {
		fmt.Fprintf(os.Stderr, "Erro ao criar requisicao: %v\n", err)
		os.Exit(1)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Erro de conexao: %v\n", err)
		os.Exit(1)
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)

	if resp.StatusCode != http.StatusOK {
		fmt.Printf("Erro HTTP %d:\n%s\n", resp.StatusCode, string(respBody))
		os.Exit(1)
	}

	var result struct {
		OK     bool `json:"ok"`
		Result struct {
			MessageID int `json:"message_id"`
		} `json:"result"`
	}
	if err := json.Unmarshal(respBody, &result); err != nil {
		fmt.Fprintf(os.Stderr, "Erro ao decodificar resposta: %v\n", err)
		os.Exit(1)
	}

	if result.OK {
		fmt.Println("OK! Campanha enviada com sucesso!")
		fmt.Printf("  Message ID: %d\n", result.Result.MessageID)
	} else {
		fmt.Println("Falha ao enviar:")
		fmt.Println(string(respBody))
		os.Exit(1)
	}
}

func openBrowser(url string) {
	var err error
	switch runtime.GOOS {
	case "windows":
		err = exec.Command("cmd", "/c", "start", url).Start()
	case "darwin":
		err = exec.Command("open", url).Start()
	default:
		err = exec.Command("xdg-open", url).Start()
	}
	if err != nil {
		fmt.Printf("  ⚠️  Could not open browser automatically: %v\n", err)
		fmt.Printf("  🖥️  Open manually: %s\n", url)
	}
}

// ─── Import ───────────────────────────────────────────────────────────────

func runImport(args []string) {
	fs := newFlagSet("import")
	path := fs.String("path", "crm-spreadsheet.csv", "Path to CSV file")
	fs.Parse(args)

	count, err := importCSV(*path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("Imported %d leads.\n", count)
}

func importCSV(path string) (int, error) {
	if _, err := os.Stat(path); os.IsNotExist(err) {
		return 0, fmt.Errorf("file not found: %s", path)
	}

	f, err := os.Open(path)
	if err != nil {
		return 0, err
	}
	defer f.Close()

	reader := csv.NewReader(f)
	headers, err := reader.Read()
	if err != nil {
		return 0, fmt.Errorf("read headers: %w", err)
	}

	// Build column index
	colMap := make(map[string]int)
	for i, h := range headers {
		colMap[strings.TrimSpace(h)] = i
	}

	get := func(row []string, names ...string) string {
		for _, name := range names {
			if idx, ok := colMap[name]; ok && idx < len(row) {
				return strings.TrimSpace(row[idx])
			}
		}
		return ""
	}

	var imported, skipped int
	for {
		row, err := reader.Read()
		if err != nil {
			break
		}

		company := get(row, "Company")
		if company == "" {
			continue
		}

		orgType := get(row, "Type")
		if orgType == "" {
			skipped++
			fmt.Printf("  Skipped '%s' — type is required\n", company)
			continue
		}

		tier := get(row, "Tier")
		if tier == "" {
			tier = "3"
		} else if len(tier) > 0 {
			tier = string(tier[0])
		}

		contactName := get(row, "Contact Name", "Contact")
	emailRaw := get(row, "Email", "Contact Email")
	var emails []string
	for _, e := range strings.Split(emailRaw, ",") {
		e = strings.TrimSpace(e)
		if e != "" {
			emails = append(emails, e)
		}
	}
	phone := get(row, "Phone")
	website := get(row, "Website")
	vertical := get(row, "Vertical")
	checkSize := get(row, "Check Size")
	pitchAngle := get(row, "Our Angle", "Pitch Angle")
	nextAction := get(row, "Next Action")
	emailSent := get(row, "Email Sent", "Email Sent (Date)")
	notes := get(row, "Notes")

	_, err = db.AddLead(models.LeadInput{
		Company:        company,
		ContactName:    contactName,
		Emails:         emails,
		Phone:          phone,
		Website:        website,
		Tier:           tier,
		Type:           orgType,
		Vertical:       vertical,
		CheckSize:      checkSize,
		PitchAngle:     pitchAngle,
		Status:         "cold",
		NextAction:     nextAction,
		NextActionDate: emailSent,
		Notes:          notes,
		Source:         "csv_import",
	})
	if err != nil {
		fmt.Printf("  Error importing '%s': %v\n", company, err)
		continue
	}
		imported++
	}

	if skipped > 0 {
		fmt.Printf("  Warning: %d row(s) skipped because type column was empty\n", skipped)
	}

	return imported, nil
}

// ─── Export ───────────────────────────────────────────────────────────────

func runExport(args []string) {
	fs := newFlagSet("export")
	path := fs.String("path", "leads-export.csv", "Output CSV path")
	fs.Parse(args)

	leads, err := db.GetLeads(db.LeadFilter{})
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	f, err := os.Create(*path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error creating file: %v\n", err)
		os.Exit(1)
	}
	defer f.Close()

	writer := csv.NewWriter(f)
	defer writer.Flush()

	// Write header
	writer.Write([]string{
		"ID", "Company", "Contact Name", "Email", "Phone", "Website",
		"Tier", "Type", "Vertical", "Check Size", "Pitch Angle",
		"Status", "Next Action", "Next Action Date", "Notes", "Source",
		"Created At", "Updated At",
	})

	for _, lead := range leads {
		writer.Write([]string{
			lead.ID, lead.Company, lead.ContactName, strings.Join(lead.Emails, ", "),
			lead.Phone, lead.Website, lead.Tier, lead.Type, lead.Vertical,
			lead.CheckSize, lead.PitchAngle, lead.Status, lead.NextAction,
			lead.NextActionDate, lead.Notes, lead.Source,
			lead.CreatedAt, lead.UpdatedAt,
		})
	}

	fmt.Printf("Exported %d leads to %s\n", len(leads), *path)
}

// ─── Helpers ──────────────────────────────────────────────────────────────

func readLine(reader *bufio.Reader, prompt string) string {
	fmt.Print(prompt)
	text, _ := reader.ReadString('\n')
	return strings.TrimSpace(text)
}

func printLead(lead models.Contact, verbose bool) {
	shortID := lead.ID
	if len(shortID) > 8 {
		shortID = shortID[:8]
	}

	tierLabel := lead.Tier
	if l, ok := models.TierLabels[lead.Tier]; ok {
		tierLabel = l
	}

	emailsStr := "-"
	if len(lead.Emails) > 0 {
		emailsStr = strings.Join(lead.Emails, ", ")
	}

	fmt.Printf("  [%s] %s\n", shortID, lead.Company)
	fmt.Printf("         Contact: %s  |  %s\n", defaultStr(lead.ContactName, "-"), emailsStr)
	fmt.Printf("         Tier: %s  |  Type: %s  |  Vertical: %s\n", tierLabel, defaultStr(lead.Type, "-"), defaultStr(lead.Vertical, "-"))
	fmt.Printf("         Status: %s  |  Check: %s\n", lead.Status, defaultStr(lead.CheckSize, "-"))
	if lead.NextAction != "" {
		dateStr := lead.NextActionDate
		if dateStr == "" {
			dateStr = "no date"
		}
		fmt.Printf("         Next: %s  (%s)\n", lead.NextAction, dateStr)
	}

	if verbose {
		fmt.Printf("         Website: %s\n", defaultStr(lead.Website, "-"))
		fmt.Printf("         Phone: %s\n", defaultStr(lead.Phone, "-"))
		fmt.Printf("         Pitch: %s\n", defaultStr(lead.PitchAngle, "-"))
		fmt.Printf("         Notes: %s\n", defaultStr(lead.Notes, "-"))
		fmt.Printf("         Created: %s  |  Updated: %s\n", lead.CreatedAt, lead.UpdatedAt)

		outreach, err := db.GetOutreach(lead.ID)
		if err == nil && len(outreach) > 0 {
			fmt.Printf("         Activity (%d):\n", len(outreach))
			max := 5
			if len(outreach) < max {
				max = len(outreach)
			}
			for _, o := range outreach[:max] {
				created := o.CreatedAt
				if len(created) > 10 {
					created = created[:10]
				}
				fmt.Printf("           [%s] %s: %s\n", created, o.ActivityType, o.Notes)
			}
		}
	}
	fmt.Println()
}

func defaultStr(s, def string) string {
	if s == "" {
		return def
	}
	return s
}

func newFlagSet(name string) *flag.FlagSet {
	fs := flag.NewFlagSet(name, flag.ExitOnError)
	fs.Usage = func() {
		fmt.Fprintf(os.Stderr, "Usage: crm %s [options]\n\n", name)
		fs.PrintDefaults()
	}
	return fs
}


