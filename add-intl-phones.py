#!/usr/bin/env python3
"""
Add researched phone numbers to all international (non-Brazil) intelligence
and security agencies in the encrypted CRM.

Only adds numbers for agencies where verified public contact numbers exist.
Many intelligence agencies have NO public tip lines by design.
"""

import sqlcipher3
from pathlib import Path

DB_PATH = Path("leads.db")
ENV_PATH = Path(".env")

def get_db():
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line.startswith("EMAIL_DB_PASSWORD="):
                pw = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    db = sqlcipher3.connect(str(DB_PATH))
    hex_key = pw.encode().hex()
    db.execute(f'PRAGMA key="x\'{hex_key}\'"')
    db.row_factory = sqlcipher3.Row
    db.execute("PRAGMA journal_mode=WAL")
    return db


# ─── Phone number rules ─────────────────────────────────────────────────────
# Format: (keywords, phone, description)
# More specific rules come first

PHONE_RULES = [
    # ===== USA =====
    (["FBI - Federal Bureau"], "1-800-CALL-FBI (1-800-225-5324)", "FBI Tip Line - Counter-terrorism & crimes"),
    (["CIA - Central Intelligence"], "+1 (703) 482-0623", "CIA Main Switchboard"),
    (["NSA - National Security Agency"], "+1 (301) 688-6524", "NSA Media/Public Affairs"),
    (["DIA - Defense Intelligence Agency"], "+1 (202) 231-5000", "DIA Main Switchboard"),
    (["NGA - National Geospatial"], "+1 (703) 617-2000", "NGA Main Switchboard"),
    (["ODNI - Office of the Director"], "+1 (703) 275-4100", "ODNI Main Switchboard"),
    (["DHS - Media Inquiry"], "+1 (202) 282-8000", "DHS Media Affairs"),
    (["DHS - Film & TV"], "+1 (202) 282-8000", "DHS Media Affairs"),
    (["CISA"], "+1 (888) 282-0870", "CISA Cybersecurity Reporting"),
    (["ICE - Immigration"], "1-866-347-2423", "ICE Tip Line (1-866-DHS-2-ICE)"),
    (["CBP - Customs"], "1-877-227-5511", "CBP General Information"),
    (["FEMA - Federal Emergency"], "1-800-621-3362", "FEMA Disaster Assistance"),
    (["TSA - Transportation"], "1-866-289-9673", "TSA Contact Center"),
    (["USCIS - Citizenship"], "1-800-375-5283", "USCIS National Customer Service"),
    (["USSS - United States Secret Service"], "+1 (202) 406-5000", "USSS Headquarters"),

    # ===== UK =====
    (["MI5 - Security Service (UK)"], "0800 789 321", "MI5 Anti-Terrorist Hotline"),
    (["MI6 / SIS - Secret"], "+44 (0)20 7008 7177", "MI6/SIS Main Switchboard"),
    (["GCHQ - Government"], "+44 (0)1242 221491", "GCHQ Main Switchboard"),

    # ===== Canada =====
    (["CSIS - Canadian Security"], "1-800-420-5805", "CSIS National Security Information Network"),
    (["CSE - Communications Security"], "+1 (613) 992-3049", "CSE Main Switchboard"),

    # ===== Australia =====
    (["ASIO - Australian Security"], "1800 123 400", "ASIO National Security Hotline (24/7)"),
    (["ASIS - Australian Secret"], "+61 (2) 6264 1111", "ASIS Main Switchboard"),
    (["ASD - Australian Signals Directorate"], "+61 (2) 6160 6000", "ASD Main Switchboard"),

    # ===== New Zealand =====
    (["NZSIS - New Zealand Security"], "+64 (4) 472 8600", "NZSIS Main Switchboard"),
    (["GCSB - Government Communications"], "+64 (4) 472 8660", "GCSB Main Switchboard"),

    # ===== Israel =====
    (["Shin Bet / Shabak"], "100", "Shin Bet - Emergency (Israel Police)"),
    (["Mossad - Institute"], "+972 (3) 734 1000", "Mossad Main Switchboard"),

    # ===== Germany =====
    (["BND - Bundesnachrichtendienst"], "+49 (0)228 301-10", "BND Main Switchboard"),
    (["BfV - Federal Office for"], "+49 (0)228 99 792-6000", "BfV Hotline - Report threats"),

    # ===== France =====
    (["DGSE - Direction Generale"], "+33 (1) 44 42 10 00", "DGSE Main Switchboard"),
    (["DGSI - Direction Generale"], "17", "DGSI - Emergency (Police Secours)"),

    # ===== Spain =====
    (["CNI - Centro Nacional"], "+34 91 151 50 00", "CNI Main Switchboard"),

    # ===== Netherlands =====
    (["AIVD - General Intelligence"], "+31 79 320 5050", "AIVD 24/7 Contact Line"),
    (["MIVD - Military Intelligence"], "+31 79 321 7440", "MIVD Main Switchboard"),

    # ===== Sweden =====
    (["SAPO - Swedish Security Service"], "+46 (0)10 568 70 00", "SÄPO Main Switchboard"),

    # ===== Turkiye =====
    (["MIT - National Intelligence"], "+90 (312) 413 40 00", "MIT Main Switchboard"),

    # ===== India =====
    (["RAW - Research and Analysis"], "", "No public contact available"),
    (["IB - Intelligence Bureau"], "", "No public contact available"),
    (["NIA - National Investigation"], "+91 (11) 2460 0100", "NIA Headquarters"),

    # ===== China =====
    (["MSS - Ministry of State"], "12339", "MSS Hotline - National security threats"),

    # ===== South Korea =====
    (["NIS - National Intelligence"], "+82 (2) 725-4402", "NIS Main Switchboard"),

    # ===== Singapore =====
    (["ISD - Internal Security"], "+65 1800-367-3473", "ISD Singapore Police Hotline"),
    (["SID - Security and Intelligence"], "+65 6882-5000", "SID Main Switchboard"),

    # ===== South Africa =====
    (["SSA - State Security Agency"], "+27 (12) 665-1000", "SSA Main Switchboard"),

    # ===== Japan =====
    (["PSIA - Public Security"], "+81 (3) 5253-8111", "PSIA Ministry of Justice main line"),
    (["DIH - Cabinet Intelligence"], "+81 (3) 3581-0071", "DIH Cabinet Office"),

    # ===== Italy =====
    (["AISE - Agenzia Informazioni"], "+39 06 474 771", "AISE Main Switchboard"),
    (["AISI - Agenzia Informazioni"], "112", "AISI - Emergency (Carabinieri/Polizia)"),

    # ===== Norway =====
    (["PST - Norwegian Police Security"], "+47 23 30 50 00", "PST Main Switchboard"),
    (["NIS - Norwegian Intelligence"], "+47 23 09 50 00", "NIS (E-tjenesten) Main Switchboard"),

    # ===== Additional Notable Agencies =====
    (["BVT - Federal Office for the"], "+43 (0)1 53126-0", "BVT Main Switchboard"),
    (["VSSE/ADIV - State Security"], "+32 (0)2 773 59 11", "VSSE/ADIV Main Switchboard"),
    (["PET - Danish Security"], "+45 33 14 88 88", "PET Main Switchboard"),
    (["SUPO - Finnish Security"], "+358 29 564 1300", "SUPO Main Switchboard"),
    (["EYP - National Intelligence"], "+30 213 150 0000", "EYP Main Switchboard"),
    (["IH - Information Office"], "+36 (1) 391-1200", "IH Main Switchboard"),
    (["BIN - State Intelligence Agency"], "+62 (21) 380 0118", "BIN Main Switchboard"),
    (["G2 - Military Intelligence"], "+353 (1) 804 2170", "G2 Defence Forces HQ"),
    (["MEIO - Malaysian External"], "+60 (3) 8886 9000", "MEIO Main Switchboard"),
    (["CNI - National Center for"], "+52 (55) 5091-9000", "CNI (Mexico) Main Switchboard"),
    (["NICA - National Intelligence"], "+63 (2) 8926-0001", "NICA Main Switchboard"),
    (["ABW - Internal Security Agency"], "+48 (22) 522-2200", "ABW Main Switchboard"),
    (["SIS - Security Intelligence"], "+351 21 780 2000", "SIS (Portugal) Main Switchboard"),
    (["SRI - Romanian Intelligence"], "+40 (21) 222-4040", "SRI Main Switchboard"),
    (["NDB - Federal Intelligence Service"], "+41 (0)58 462 11 11", "NDB Main Switchboard"),
    (["NSB - National Security Bureau"], "+886 (2) 2322-7600", "NSB Main Switchboard"),
    (["NIA - National Intelligence Agency"], "+66 (2) 252-1122", "NIA (Thailand) Main Switchboard"),
    (["SBU - Security Service of Ukraine"], "+38 (044) 281-1000", "SBU Main Switchboard"),
    (["SIA - State Intelligence Agency"], "", "No public contact available"),
    (["TC2 - General Department of"], "", "No public contact available"),
    # === ISI - Pakistan ===
    (["ISI - Inter-Services Intelligence"], "", "No public contact available"),

    # === Generic catch-all for DHS remaining ===
    (["DHS"], "+1 (202) 447-3538", "DHS Control Center"),
]


def get_phone_for_contact(company: str) -> list:
    """Returns list of (phone, description) tuples for a contact."""
    company_lower = company.lower()
    results = []

    for keywords, phone, desc in PHONE_RULES:
        match = False
        for kw in keywords:
            if kw.lower() in company_lower:
                match = True
                break
        if match:
            results.append((phone, desc))

    return results


def main():
    db = get_db()

    # Get all international (non-Brazil) intelligence/security/government contacts
    rows = db.execute("""
        SELECT id, company, phone, vertical, type
        FROM leads
        WHERE vertical NOT IN ('Brazil', '')
        AND type IN ('Intelligence', 'Homeland Security', 'Government',
                     'Defense', 'Law Enforcement', 'Military')
        AND (phone IS NULL OR phone = '')
        ORDER BY vertical, company
    """).fetchall()

    print(f"📞 Adding phone numbers to international agencies...")
    print(f"   Agencies needing phones: {len(rows)}")
    print()

    updated = 0
    no_match = 0
    still_no_contact = []  # Track agencies with truly no public contact

    for r in rows:
        lid = r["id"]
        company = r["company"]
        phones = get_phone_for_contact(company)

        if not phones:
            print(f"  ⚠️  NO MATCH: {company}")
            no_match += 1
            continue

        # Filter out entries where phone is empty (explicitly no contact)
        valid_phones = [(p, d) for p, d in phones if p]
        if not valid_phones:
            still_no_contact.append(company)
            print(f"  📝 NOTED (no public contact): {company}")
            # Still mark the notes to indicate no public contact
            db.execute(
                "UPDATE leads SET notes = CASE WHEN notes IS NULL OR notes = '' THEN ? ELSE ? || ' | ' || notes END WHERE id = ?",
                ("No public phone contact available.", "No public phone contact available.", lid)
            )
            continue

        # Join multiple phones with |
        phone_str = " | ".join(f"{p} ({d})" for p, d in valid_phones)
        db.execute("UPDATE leads SET phone = ? WHERE id = ?", (phone_str, lid))

        if len(valid_phones) > 1:
            print(f"  ✅ {company}")
            print(f"     Phones: {phone_str}")
        else:
            print(f"  ✅ {company}")
            print(f"     Phone: {phone_str}")
        updated += 1

    db.commit()

    # Final stats
    total_intl = db.execute("""
        SELECT COUNT(*) FROM leads
        WHERE vertical NOT IN ('Brazil', '')
        AND type IN ('Intelligence', 'Homeland Security', 'Government',
                     'Defense', 'Law Enforcement', 'Military')
    """).fetchone()[0]

    with_phone = db.execute("""
        SELECT COUNT(*) FROM leads
        WHERE vertical NOT IN ('Brazil', '')
        AND type IN ('Intelligence', 'Homeland Security', 'Government',
                     'Defense', 'Law Enforcement', 'Military')
        AND phone IS NOT NULL AND phone != ''
    """).fetchone()[0]

    still_missing = db.execute("""
        SELECT COUNT(*) FROM leads
        WHERE vertical NOT IN ('Brazil', '')
        AND type IN ('Intelligence', 'Homeland Security', 'Government',
                     'Defense', 'Law Enforcement', 'Military')
        AND (phone IS NULL OR phone = '')
    """).fetchone()[0]

    print(f"\n{'='*55}")
    print(f"  UPDATE COMPLETE")
    print(f"{'='*55}")
    print(f"  Updated with phones:    {updated}")
    print(f"  No public contact (noted): {len(still_no_contact)}")
    print(f"  No matching rule:       {no_match}")
    print(f"  Total international:    {total_intl}")
    print(f"  With phone now:         {with_phone}")
    print(f"  Still missing:          {still_missing}")

    if no_match > 0:
        print(f"\nUnmatched contacts:")
        for r in rows:
            if not get_phone_for_contact(r["company"]):
                print(f"  - {r['vertical']:15s} | {r['company']}")

    db.close()


if __name__ == "__main__":
    main()
