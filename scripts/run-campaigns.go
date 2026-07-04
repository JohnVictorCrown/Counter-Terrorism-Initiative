// run-campaigns.go
// Orchestrates all campaign waves sequentially via the crm campaign command.
//
// Usage:
//   go run scripts/run-campaigns.go                    # interactive (confirm each wave)
//   go run scripts/run-campaigns.go --dry-run           # preview all waves
//   go run scripts/run-campaigns.go --yes               # auto-confirm all waves
//   go run scripts/run-campaigns.go --followup 7        # 7-day follow-up on all waves
//   go run scripts/run-campaigns.go --wave 3            # run only Wave 3
//
// Requires: built crm.exe in the project root.

package main

import (
	"bufio"
	"flag"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

type Wave struct {
	Number   int
	Name     string
	File     string
	Subject  string
	Args     []string // additional campaign args like --tier, --vertical, --type
	Count    int      // estimated email count (for display)
}

func main() {
	dryRun := flag.Bool("dry-run", false, "Preview all waves without sending")
	yes := flag.Bool("yes", false, "Auto-confirm all waves (skip prompts)")
	days := flag.Int("followup", 7, "Days until follow-up (0 to disable)")
	waveFilter := flag.Int("wave", 0, "Run only a specific wave number (0 = all)")
	fromName := flag.String("from-name", "John Victor @ WaterParty", "Sender display name")
	flag.Parse()

	// Resolve crm binary path
	crmPath := findCRM()
	if crmPath == "" {
		fmt.Fprintln(os.Stderr, "❌ crm.exe not found. Run 'go build ./cmd/crm/' first.")
		os.Exit(1)
	}

	templatesDir := "campaigns"
	if _, err := os.Stat(templatesDir); os.IsNotExist(err) {
		templatesDir = filepath.Join("..", "campaigns")
		if _, err := os.Stat(templatesDir); os.IsNotExist(err) {
			fmt.Fprintf(os.Stderr, "❌ campaigns/ directory not found\n")
			os.Exit(1)
		}
	}

	waves := []Wave{
		{1, "VC + Intel (Tier 1)", "wave1-vc-intel.txt",
			"FOIA Request: Counter-Terrorism Operations Transparency Data",
			[]string{"--tier", "1"}, 29},
		{2, "USA LE + Military", "wave2-usa-le-military.txt",
			"Public Records Request: Law Enforcement & Military Transparency Data",
			[]string{"--vertical", "USA"}, 24},
		{3, "USA LE + Military (United States)", "wave2-usa-le-military.txt",
			"Public Records Request: Law Enforcement & Military Transparency Data",
			[]string{"--vertical", "United States"}, 5},
		{4, "Brazil Military", "wave3-brazil-military.txt",
			"Research Partnership: Military Public Communication Study",
			[]string{"--vertical", "Brazil", "--type", "Military"}, 233},
		{5, "Brazil Human Rights NGO", "wave4-brazil-le-hr.txt",
			"Research Collaboration: Human Rights & Security in Brazil",
			[]string{"--vertical", "Brazil", "--type", "Human Rights NGO"}, 8},
		{6, "Brazil Law Enforcement", "wave4-brazil-le-hr.txt",
			"Transparency & Accountability Research: Public Security in Brazil",
			[]string{"--vertical", "Brazil", "--type", "Law Enforcement"}, 26},
		{7, "Brazil Security", "wave4-brazil-le-hr.txt",
			"Collaboration on Security & Human Rights Research",
			[]string{"--vertical", "Brazil", "--type", "Security"}, 6},
	}

	// Filter by wave number
	var filtered []Wave
	for _, w := range waves {
		if *waveFilter == 0 || w.Number == *waveFilter {
			filtered = append(filtered, w)
		}
	}
	waves = filtered

	if len(waves) == 0 {
		fmt.Printf("No waves match filter --wave %d\n", *waveFilter)
		os.Exit(0)
	}

	// Show summary
	printSummary(crmPath, waves, *days, *dryRun)

	if !*yes && !*dryRun {
		fmt.Println()
		fmt.Print("📬 Run all these waves now? (y/N): ")
		reader := bufio.NewReader(os.Stdin)
		ans, _ := reader.ReadString('\n')
		if strings.TrimSpace(strings.ToLower(ans)) != "y" {
			fmt.Println("❌ Cancelled.")
			os.Exit(0)
		}
	}

	// Execute each wave
	totalSent := 0
	for i, w := range waves {
		fmt.Println()
		fmt.Println(strings.Repeat("═", 58))
		fmt.Printf("  📬 WAVE %d/%d: %s\n", i+1, len(waves), w.Name)
		fmt.Println(strings.Repeat("═", 58))
		fmt.Printf("  Template: %s/%s\n", templatesDir, w.File)
		fmt.Printf("  Subject:  %s\n", w.Subject)
		fmt.Printf("  Filter:   crm campaign %s\n", strings.Join(w.Args, " "))
		fmt.Println(strings.Repeat("─", 58))
		fmt.Println()

		bodyFile := filepath.Join(templatesDir, w.File)
		if _, err := os.Stat(bodyFile); os.IsNotExist(err) {
			fmt.Printf("  ⚠️  Template not found: %s — skipping wave %d\n", bodyFile, w.Number)
			continue
		}

		// Build command args
		args := []string{"campaign"}
		args = append(args, w.Args...)
		args = append(args,
			"--body-file", bodyFile,
			"--subject", w.Subject,
			"--from-name", *fromName,
		)
		if *dryRun {
			args = append(args, "--dry-run")
		} else if *yes {
			// With --yes, pass --confirm but pipe "y\n" as input
			args = append(args, "--confirm")
		} else {
			args = append(args, "--confirm")
		}
		if *days > 0 {
			args = append(args, "--followup", fmt.Sprintf("%d", *days))
		}

		cmd := exec.Command(crmPath, args...)
		if *yes {
			// Auto-confirm: pipe "y" to the campaign's --confirm prompt
			cmd.Stdin = strings.NewReader("y\n")
		} else {
			cmd.Stdin = os.Stdin
		}
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr

		if err := cmd.Run(); err != nil {
			fmt.Fprintf(os.Stderr, "\n  ❌ Wave %d failed: %v\n", w.Number, err)
			if !*yes {
				fmt.Print("  Continue with next wave? (Y/n): ")
				reader := bufio.NewReader(os.Stdin)
				ans, _ := reader.ReadString('\n')
				if strings.TrimSpace(strings.ToLower(ans)) == "n" {
					fmt.Println("  Stopping.")
					break
				}
			} else {
				fmt.Println("  Continuing to next wave...")
			}
			continue
		}

		totalSent++

		// Pause between waves (3s) unless it's the last one
		if i < len(waves)-1 && !*dryRun {
			fmt.Println()
			fmt.Printf("  ⏳ Waiting 3 seconds before next wave...\n")
			time.Sleep(3 * time.Second)
		}
	}

	// Final summary
	fmt.Println()
	fmt.Println(strings.Repeat("═", 58))
	if *dryRun {
		fmt.Printf("  🔍 DRY RUN COMPLETE — %d waves previewed\n", totalSent)
		fmt.Printf("  Run without --dry-run to send.\n")
	} else {
		completed := "✅"
		if totalSent < len(waves) {
			completed = "⚠️  Partial"
		}
		fmt.Printf("  %s CAMPAIGN SEQUENCE COMPLETE — %d waves sent\n", completed, totalSent)
		if *days > 0 {
			fmt.Printf("  Follow-up set to +%d days\n", *days)
		}
		fmt.Println()
		fmt.Println("  📋 Next: crm followups  — View due follow-ups")
		fmt.Println("            crm list --status replied  — Track replies")
		fmt.Println("            crm stats                  — Overall dashboard")
	}
	fmt.Println(strings.Repeat("═", 58))
	fmt.Println()
}

func printSummary(crmPath string, waves []Wave, days int, dryRun bool) {
	fmt.Println()
	fmt.Println(strings.Repeat("═", 58))
	fmt.Println("  📬 COUNTER-TERRORISM INITIATIVE — CAMPAIGN SEQUENCE")
	fmt.Println(strings.Repeat("═", 58))
	fmt.Println()
	if dryRun {
		fmt.Println("  🔍 DRY RUN MODE — No emails will be sent")
		fmt.Println()
	}
	fmt.Printf("  %-4s %-30s %-10s %s\n", "Wave", "Segment", "Emails", "Template")
	fmt.Println(strings.Repeat("─", 58))
	total := 0
	for _, w := range waves {
		countStr := fmt.Sprintf("%d", w.Count)
		if countStr == "0" {
			countStr = "?"
		}
		fmt.Printf("  %-4d %-30s %-10s %s\n", w.Number, w.Name, countStr, w.File)
		total += w.Count
	}
	fmt.Println(strings.Repeat("─", 58))
	fmt.Printf("  %-4s %-30s %-10s\n", "", fmt.Sprintf("%d waves total", len(waves)), fmt.Sprintf("~%d", total))
	if days > 0 {
		fmt.Printf("  Follow-up: +%d days\n", days)
	}
	fmt.Printf("  CRM path: %s\n", crmPath)
}

func findCRM() string {
	// Check current directory first
	if _, err := os.Stat("crm.exe"); err == nil {
		abs, _ := filepath.Abs("crm.exe")
		return abs
	}
	// Check project root (one level up from scripts/)
	if _, err := os.Stat(filepath.Join("..", "crm.exe")); err == nil {
		abs, _ := filepath.Abs(filepath.Join("..", "crm.exe"))
		return abs
	}
	// Search PATH
	if p, err := exec.LookPath("crm"); err == nil {
		return p
	}
	if p, err := exec.LookPath("crm.exe"); err == nil {
		return p
	}
	return ""
}
