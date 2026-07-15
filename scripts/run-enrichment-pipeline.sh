#!/usr/bin/env bash
# run-enrichment-pipeline.sh — FBI Enrichment Pipeline
# Runs both enrichment scripts (scrape + deep) and applies updates to the database.
#
# Usage:
#   bash scripts/run-enrichment-pipeline.sh              # Run full pipeline
#   bash scripts/run-enrichment-pipeline.sh --dry-run    # Preview only, no DB changes

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DRY_RUN=false

for arg in "$@"; do
    if [ "$arg" = "--dry-run" ]; then
        DRY_RUN=true
    fi
done

cd "$PROJECT_DIR"

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║          FBI ENRICHMENT PIPELINE                                   ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Project: $PROJECT_DIR"
if [ "$DRY_RUN" = true ]; then
    echo "Mode:    ⚠️  DRY RUN (preview only)"
else
    echo "Mode:    🔥 FULL RUN (will update database)"
fi
echo ""

# ─── Step 1: Field Office Scrape & Match ────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════════════════════"
echo "  STEP 1/3: FBI Field Office Scrape & Database Match"
echo "══════════════════════════════════════════════════════════════════════"
go run scripts/enrich-fbi-field-offices.go
echo ""

# ─── Step 2: Deep Enrichment ────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════════════════════"
echo "  STEP 2/3: Deep Enrichment (Subdomain Scraping)"
echo "══════════════════════════════════════════════════════════════════════"
go run scripts/enrich-fbi-deep.go
echo ""

# ─── Step 3: Apply Updates ──────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════════════════════"
echo "  STEP 3/3: Apply Updates to Database"
echo "══════════════════════════════════════════════════════════════════════"
if [ "$DRY_RUN" = true ]; then
    go run scripts/apply-fbi-enrichment.go
else
    go run scripts/apply-fbi-enrichment.go --apply
fi
echo ""

# ─── Final Summary ──────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║          PIPELINE COMPLETE                                         ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "  Steps:"
echo "    ✅ 1/3 FBI Field Office Scrape"
echo "    ✅ 2/3 Deep Enrichment"
echo "    ✅ 3/3 Database Updates"
echo ""
echo "  Next steps:"
echo "    • Start dashboard:  ./dashboard.exe"
echo "    • View CRM stats:   go run ./cmd/crm/ stats"
echo "    • Run enrichment with --dry-run to preview:"
echo "      bash scripts/run-enrichment-pipeline.sh --dry-run"
echo ""
