"""Detailed Wave 2 data"""
import sqlcipher3

pw = open('.env').read().split('EMAIL_DB_PASSWORD=')[1].split()[0].strip('"\' \n\r')
conn = sqlcipher3.connect('databases/leads.db')
conn.execute('PRAGMA cipher_compatibility = 3')
conn.execute(f'PRAGMA key="x\'{pw.encode().hex()}\'"')

print("=" * 70)
print("  WAVE 2 — USA LAW ENFORCEMENT + MILITARY DETAILS")
print("=" * 70)

r = conn.execute("""
    SELECT l.company, l.type, l.tier, le.email, l.notes
    FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id
    WHERE l.vertical IN ('USA', 'United States')
      AND l.type IN ('Law Enforcement', 'Military', 'Intelligence', 'Homeland Security')
    ORDER BY l.type, l.company
""").fetchall()

print(f"\nTotal leads in segment: {len(r)}")
has_email = [x for x in r if x[3]]
no_email = [x for x in r if not x[3]]
print(f"With email: {len(has_email)}")
print(f"Without email: {len(no_email)}")

print("\n--- WITH EMAIL ---")
for x in has_email:
    t = x[3] or ""
    print(f"  [T{x[2]}] {x[1]:25s} | {x[0][:35]:35s} | {t}")

print("\n--- WITHOUT EMAIL ---")
for x in no_email:
    print(f"  [T{x[2]}] {x[1]:25s} | {x[0][:35]}")

# Type breakdown
print("\n--- TYPE BREAKDOWN ---")
r2 = conn.execute("""
    SELECT l.type, COUNT(DISTINCT l.id), COUNT(DISTINCT le.lead_id)
    FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id
    WHERE l.vertical IN ('USA', 'United States')
      AND l.type IN ('Law Enforcement', 'Military', 'Intelligence', 'Homeland Security')
    GROUP BY l.type ORDER BY COUNT(*) DESC
""").fetchall()
for x in r2:
    print(f"  {x[0]:25s} | {x[1]} leads, {x[2]} with email")

conn.close()
