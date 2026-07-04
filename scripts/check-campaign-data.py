"""Check campaign readiness by wave"""
import sqlcipher3

pw = open('.env').read().split('EMAIL_DB_PASSWORD=')[1].split()[0].strip('"\' \n\r')
conn = sqlcipher3.connect('databases/leads.db')
conn.execute('PRAGMA cipher_compatibility = 3')
conn.execute(f'PRAGMA key="x\'{pw.encode().hex()}\'"')

print("=" * 60)
print("  CAMPAIGN READINESS CHECK")
print("=" * 60)

# Wave 1: Tier 1 (VC + Intel)  
r = conn.execute("""
    SELECT COUNT(DISTINCT l.id), COUNT(DISTINCT le.lead_id)
    FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id
    WHERE l.tier = '1'
""").fetchone()
print(f"\nWave 1 — VC + Intel (Tier 1): {r[0]} leads, {r[1]} with email")

# Wave 2: USA Law Enforcement + Military
r = conn.execute("""
    SELECT COUNT(DISTINCT l.id), COUNT(DISTINCT le.lead_id)
    FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id
    WHERE l.vertical IN ('USA', 'United States')
      AND l.type IN ('Law Enforcement', 'Military', 'Intelligence', 'Homeland Security')
""").fetchone()
print(f"Wave 2 — USA LE + Military: {r[0]} leads, {r[1]} with email")

# Wave 3: Brazil Military
r = conn.execute("""
    SELECT COUNT(DISTINCT l.id), COUNT(DISTINCT le.lead_id)
    FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id
    WHERE l.vertical LIKE '%Brazil%' AND l.type = 'Military'
""").fetchone()
print(f"Wave 3 — Brazil Military: {r[0]} leads, {r[1]} with email")

# Wave 4: Brazil HR + LE
r = conn.execute("""
    SELECT COUNT(DISTINCT l.id), COUNT(DISTINCT le.lead_id)
    FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id
    WHERE l.vertical LIKE '%Brazil%'
      AND (l.type = 'Law Enforcement' OR l.type = 'State Police'
           OR l.type = 'Security' OR l.type LIKE '%Human Rights%'
           OR l.type LIKE '%Anti-Torture%')
""").fetchone()
print(f"Wave 4 — Brazil HR + LE: {r[0]} leads, {r[1]} with email")

# Wave 5: No email
r = conn.execute("""
    SELECT COUNT(DISTINCT l.id)
    FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id
    WHERE le.lead_id IS NULL
""").fetchone()
print(f"Wave 5 — No email (needs enrichment): {r[0]} leads")

# Overall
r = conn.execute("SELECT COUNT(DISTINCT l.id), COUNT(DISTINCT le.lead_id) FROM leads l LEFT JOIN lead_emails le ON le.lead_id = l.id").fetchone()
print(f"\nTotal: {r[0]} leads, {r[1]} with email")

# Status distribution
r = conn.execute("SELECT status, COUNT(*) FROM leads GROUP BY status ORDER BY COUNT(*) DESC").fetchall()
print("\nStatus distribution:")
for x in r:
    print(f"  {x[0]}: {x[1]}")

# Check sample emails for Wave 1
print("\nSample Wave 1 emails (first 10):")
r = conn.execute("""
    SELECT l.company, l.type, le.email
    FROM leads l JOIN lead_emails le ON le.lead_id = l.id
    WHERE l.tier = '1'
    LIMIT 10
""").fetchall()
for x in r:
    print(f"  {x[0][:35]:35s} | {x[1][:20]:20s} | {x[2]}")

conn.close()
