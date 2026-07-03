Write-Output "=== Building with CGO_ENABLED=1 ==="
$env:CGO_ENABLED=1

Write-Output "`nBuilding dashboard.exe..."
go build -o dashboard.exe ./cmd/dashboard/ 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Output "  ✅ dashboard.exe built successfully"
} else {
    Write-Output "  ❌ dashboard.exe build FAILED"
    exit 1
}

Write-Output "`nBuilding crm.exe..."
go build -o crm.exe ./cmd/crm/ 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Output "  ✅ crm.exe built successfully"
} else {
    Write-Output "  ❌ crm.exe build FAILED"
    exit 1
}

Write-Output "`n=== Verifying CGO was used ==="
$crmInfo = go tool nm crm.exe 2>&1 | Select-String -Pattern "go-sqlcipher" -SimpleMatch
if ($crmInfo) {
    Write-Output "  ✅ sqlcipher symbols found - CGO linked correctly"
} else {
    Write-Output "  ⚠️  No sqlcipher symbols detected (might still work)"
}

Write-Output "`n=== Build complete! ==="
Write-Output "Run: .\dashboard.exe"
Write-Output "Then open http://localhost:5000"
