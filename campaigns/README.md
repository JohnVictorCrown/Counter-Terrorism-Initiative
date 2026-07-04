# 📬 Campaign Templates

This directory contains email templates for each outreach wave.
Use them with the `crm campaign` command:

## How to Use

### 1. Preview a segment
```powershell
.\crm.exe campaign --tier 1 --body-file campaigns\wave1-vc-intel.txt --subject "Your Subject" --dry-run
```

### 2. Send with confirmation
```powershell
.\crm.exe campaign --tier 1 --body-file campaigns\wave1-vc-intel.txt --subject "Your Subject" --confirm
```

### 3. Send immediately (no prompt)
```powershell
.\crm.exe campaign --tier 1 --body-file campaigns\wave1-vc-intel.txt --subject "Your Subject"
```

## Campaigns

| File | Wave | Segment | Leads | Emailable | Language |
|------|------|---------|-------|-----------|----------|
| `wave1-vc-intel.txt` | 1 | VC + Intelligence (Tier 1) | 63 | ~40 | English |
| `wave2-usa-le-military.txt` | 2 | USA Law Enforcement + Military | 181 | 29 | English |
| `wave3-brazil-military.txt` | 3 | Brazilian Military (Tier 2-3) | 233 | 233 | Portuguese |
| `wave4-brazil-le-hr.txt` | 4 | Brazil LE + Human Rights | 92 | 40 | Portuguese |
| Need enrichment | 5 | Remaining (no email) | ~93 | 0 | — |

## Tips

- **Always run `--dry-run` first** to preview the segment size and recipients
- **Always run `--confirm`** on first send to verify everything looks right
- Use `--no-status-update` if you want to keep status as "cold" (e.g., for test sends)
- After sending, track replies with: `.\crm.exe list --status replied`
- Log follow-ups with: `.\crm.exe log <lead-id>`
