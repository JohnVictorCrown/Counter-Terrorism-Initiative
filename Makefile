.PHONY: all crm dashboard run-crm run-dashboard vet clean help

# ─── Configuration ──────────────────────────────────────────────────────────
# These variables can be overridden:  make CGO_ENABLED=0
CGO_ENABLED ?= 1
GO          ?= go
GOFLAGS     ?= -v

# ─── Default ────────────────────────────────────────────────────────────────
all: crm dashboard
	@echo ""
	@echo "✅ Both binaries built. Run:"
	@echo "   .\\crm.exe stats          — View CRM stats"
	@echo "   .\\dashboard.exe          — Launch web dashboard"
	@echo ""

# ─── Build Targets ──────────────────────────────────────────────────────────

# Build the CRM CLI binary (requires CGO for SQLCipher)
crm:
	@echo "🔨 Building crm.exe (CGO_ENABLED=$(CGO_ENABLED))..."
	CGO_ENABLED=$(CGO_ENABLED) $(GO) build $(GOFLAGS) -o crm.exe ./cmd/crm/
	@echo "✅ crm.exe built successfully"
	@echo "   Usage: .\\crm.exe stats"

# Build the dashboard web server binary (requires CGO for SQLCipher)
dashboard:
	@echo "🔨 Building dashboard.exe (CGO_ENABLED=$(CGO_ENABLED))..."
	CGO_ENABLED=$(CGO_ENABLED) $(GO) build $(GOFLAGS) -o dashboard.exe ./cmd/dashboard/
	@echo "✅ dashboard.exe built successfully"
	@echo "   Usage: .\\dashboard.exe  →  http://localhost:5000"

# ─── Run Targets ────────────────────────────────────────────────────────────

# Run CRM CLI with an optional argument:  make run-crm ARGS="stats"
run-crm:
	@cd "$(CURDIR)" && CGO_ENABLED=$(CGO_ENABLED) $(GO) run ./cmd/crm/ $(ARGS)

# Run the dashboard web server:  make run-dashboard
run-dashboard:
	@cd "$(CURDIR)" && CGO_ENABLED=$(CGO_ENABLED) $(GO) run ./cmd/dashboard/

# ─── Utility Targets ─────────────────────────────────────────────────────────

# Run go vet on all packages
vet:
	CGO_ENABLED=$(CGO_ENABLED) $(GO) vet ./cmd/crm/ ./cmd/dashboard/ ./internal/...
	@echo "✅ go vet passed"

# Remove built binaries
clean:
	@echo "🧹 Cleaning..."
	-rm -f crm.exe dashboard.exe
	@echo "✅ Cleaned"

# Show help
help:
	@echo "Counter-Terrorism Initiative — Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  make              Build both crm.exe + dashboard.exe (default)"
	@echo "  make crm          Build crm.exe CLI only"
	@echo "  make dashboard    Build dashboard.exe web server only"
	@echo "  make run-crm ARGS=\"stats\"   Run CRM via 'go run'"
	@echo "  make run-dashboard          Run dashboard via 'go run'"
	@echo "  make vet                   Run go vet on all packages"
	@echo "  make clean                 Remove built binaries"
	@echo "  make help                  Show this help"
	@echo ""
	@echo "Variables:"
	@echo "  CGO_ENABLED=1    Enable CGO (default, required for SQLCipher)"
	@echo "  CGO_ENABLED=0    Disable CGO (only for pure-Go builds)"
	@echo "  ARGS=\"stats\"     Arguments passed to run-crm"
	@echo ""

# ─── CGO Note ───────────────────────────────────────────────────────────────
# SQLCipher encryption requires CGO. If 'gcc' is not installed, run in
# PowerShell as Administrator:
#   Set-ExecutionPolicy Bypass -Scope Process -Force
#   iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))
#   choco install mingw -y
#
# Then rebuild:  make CGO_ENABLED=1
