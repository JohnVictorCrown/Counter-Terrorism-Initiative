# WaterParty — CRM Guide

## How to Import into Google Sheets

1. Go to **sheets.google.com** and create a new blank spreadsheet
2. Click **File → Import → Upload**
3. Upload `marketing/crm-spreadsheet.csv`
4. In the import dialog:
   - **Import location:** Replace current sheet
   - **Separator:** Comma
   - **Convert text to numbers/dates:** Yes
5. Click **Import**

Your CRM is ready with all 30+ contacts pre-loaded.

## How to Use

| Column | What to Do |
|---|---|
| **Email Sent (Date)** | Enter the date you sent the email (e.g., `2025-01-15`) |
| **Follow-up 1 (Date)** | Enter date of first follow-up (7 days after initial email) |
| **Follow-up 2 (Date)** | Enter date of second follow-up (7 days after first follow-up) |
| **Reply Received** | Enter `Y` or `N` |
| **Meeting Scheduled** | Enter `Y` or `N` |
| **Next Action** | Update with your next step |
| **Notes** | Keep notes on conversations, responses, contact names |

## Tips

- **Color code rows:** Green = meeting set, Yellow = replied but no meeting, Red = no reply
- **Filter by tier:** Use Data → Create a filter to focus on Tier 1 first
- **Sort by Email Sent:** See who hasn't been contacted yet
- **Add columns as needed:** Contact name, phone, LinkedIn URL
