"""Check Wave 1 follow-up state"""
import sqlcipher3
from datetime import datetime, timedelta

pw = open('.env').read().split('EMAIL_DB_PASSWORD=')[1].split()[0].strip('"\' \n\r')
conn = sqlcipher3.connect('databases/leads.db')
conn.execute('PRAGMA cipher_compatibility = 3')
conn.execute(f'PRAGMA key="x\'{pw.encode().hex()}\'"')

print("=" * 60)
print("  WAVE 1 — FOLLOW-UP TRACKING CHECK")
print("=" * 60)

# Wave 1 leads (Tier 1)
r = conn.execute("""
    SELECT l.id, l.company, l.type, l.status, l.next_action, l.next_action_date,
           le.email
    FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id AND le.is_primary = 1
    WHERE l.tier = '1'
    ORDER BY l.status, l.company
""").fetchall()

print(f"\nWave 1 leads: {len(r)}")
sent = [x for x in r if x[3] == 'contacted']
cold = [x for x in r if x[3] == 'cold']
print(f"  Status 'contacted': {len(sent)}")
print(f"  Status 'cold': {len(cold)}")

if sent:
    print(f"\nContacted leads ({len(sent)}):")
    for x in sent:
        action = x[4] or "(no follow-up set)"
        date = x[5] or "(no date)"
        print(f"  {x[1][:35]:35s} | next: {action:25s} | by: {date}")
        l_id = x[0][:8]
    print()

# Outreach logs
r = conn.execute("""
    SELECT o.created_at, o.activity_type, o.outcome, l.company
    FROM outreach_log o JOIN leads l ON o.lead_id = l.id
    WHERE l.tier = '1'
    ORDER BY o.created_at DESC
    LIMIT 10
""").fetchall()

print(f"Recent outreach logs for Wave 1:")
for x in r:
    print(f"  [{x[0][:10]}] {x[1]:10s} | {x[3][:30]:30s} | {x[2] or '-':30s}")

# Suggest follow-up dates
print(f"\n--- SUGGESTED FOLLOW-UP DATES ---")
today = datetime.now()
for i in [3, 5, 7, 14]:
    d = today + timedelta(days=i)
    print(f"  {i:2d}-day follow-up: {d.strftime('%Y-%m-%d')}")

# Leads without any follow-up set
no_followup = [x for x in sent if not x[4] and not x[5]]
print(f"\nLeads needing follow-up setup: {len(no_followup)}")

conn.close()
