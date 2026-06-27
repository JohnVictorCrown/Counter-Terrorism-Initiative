#!/usr/bin/env python3
"""
Add social media handles and additional email contacts to all international
intelligence and security agencies in the encrypted CRM.
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
    return db

# ─── Social Media Updates ────────────────────────────────────────────────────
# Format: (search_term, social_media_string)

UPDATES = [
    # ==================== USA ====================
    ("CIA - Central Intelligence Agency",
     "Social: X/Twitter @CIA, Facebook @Central.Intelligence.Agency, LinkedIn linkedin.com/company/central-intelligence-agency, YouTube @ciagov"),
    ("FBI - Federal Bureau of Investigation",
     "Social: X/Twitter @FBI, Facebook @FBI, YouTube @fbi"),
    ("NSA - National Security Agency",
     "Social: X/Twitter @NSAGov, Facebook @NSAUSGov, Instagram @nsausgov"),
    ("DIA - Defense Intelligence Agency",
     "Social: X/Twitter @DefenseIntel, Facebook @DefenseIntel, Instagram @defenseintel, YouTube @DefenseIntel"),
    ("NGA - National Geospatial-Intelligence Agency",
     "Social: X/Twitter @NGA_GEOINT, Facebook @NatlGEOINTAgency, Instagram @nga_geoint, LinkedIn linkedin.com/company/nga"),
    ("ODNI - Office of the Director of National Intelligence",
     "Social: X/Twitter @ODNIgov, Facebook @dni.gov"),
    ("DHS - Media Inquiry",
     "Social: X/Twitter @DHSgov. Social Media Directory: https://www.dhs.gov/social-media-directory"),
    ("DHS - Film & TV Office",
     "Social: X/Twitter @DHSgov. Social Media Directory: https://www.dhs.gov/social-media-directory"),
    ("CISA",
     "Social: X/Twitter @CISAgov, Facebook @CISA, LinkedIn linkedin.com/company/cisa, YouTube @CISAgov"),
    ("ICE - Immigration and Customs Enforcement",
     "Social: X/Twitter @ICEgov, Facebook @ICEgov"),
    ("CBP - Customs and Border Protection",
     "Social: X/Twitter @CBP, Facebook @CBPatrol, Instagram @cbppatrol, YouTube @CBPgov"),
    ("FEMA - Federal Emergency Management Agency",
     "Social: X/Twitter @fema, Facebook @FEMA, Instagram @fema, YouTube @FEMA"),
    ("TSA - Transportation Security Administration",
     "Social: X/Twitter @TSA, Facebook @TSA, Instagram @tsa, YouTube @TSA"),
    ("USCIS - Citizenship and Immigration Services",
     "Social: X/Twitter @USCIS, Facebook @USCIS, Instagram @uscis, YouTube @USCIS"),
    ("USSS - United States Secret Service",
     "Social: X/Twitter @SecretService, Facebook @UnitedStatesSecretService, Instagram @usss_secret_service"),

    # ==================== UK ====================
    ("MI5 - Security Service (UK)",
     "Social: X/Twitter @MI5_Official, Instagram @mi5official"),
    ("MI6 / SIS - Secret Intelligence Service (UK)",
     "Social: Instagram @mi6, YouTube @mi6"),
    ("GCHQ - Government Communications Headquarters (UK)",
     "Social: X/Twitter @GCHQ, Instagram @gchq"),

    # ==================== Canada ====================
    ("CSIS - Canadian Security Intelligence Service",
     "Social: X/Twitter @csiscanada, Facebook @csiscanada, YouTube @csisscrs"),
    ("CSE - Communications Security Establishment (Canada)",
     "Social: X/Twitter @cse_cst, Instagram @cse_cst, YouTube @communicationssecurityestablishment"),

    # ==================== Australia ====================
    ("ASIO - Australian Security Intelligence Organisation",
     "Social: X/Twitter @ASIOGovAu, Facebook @asiogovau, Instagram @asiogovau"),
    ("ASIS - Australian Secret Intelligence Service",
     "Social: X/Twitter @ASISgovau"),  # Found on ASIS website
    ("ASD - Australian Signals Directorate",
     "Social: X/Twitter @ASDGovAu, Facebook @cybergovau"),

    # ==================== New Zealand ====================
    ("NZSIS - New Zealand Security Intelligence Service",
     "Social: No official social media accounts. Reports via web form at nzsis.govt.nz"),
    ("GCSB - Government Communications Security Bureau (NZ)",
     "Social: No official social media accounts"),

    # ==================== Israel ====================
    ("Shin Bet / Shabak - Israel Security Agency",
     "Social: No official social media accounts. Emergency: call Israel Police 100"),
    ("Mossad",  # Will match "Israeli Government / Mossad" and "Mossad - Institute"
     "Social: Official website mossad.gov.il. Contact form via website. No official public social media."),

    # ==================== Germany ====================
    ("BND - Bundesnachrichtendienst (Germany)",
     "Social: Instagram @bndkarriere (career account). Website: bnd.bund.de"),
    ("BfV - Federal Office for Protection of the Constitution (Germany)",
     "Social: X/Twitter @BfV_Bund, Instagram @bfv_bund, LinkedIn linkedin.com/company/bundesamt-fuer-verfassungsschutz"),

    # ==================== France ====================
    ("DGSE - Direction Generale de la Securite Exterieure (France)",
     "Social: Official website defense.gouv.fr/dgse. No public social media accounts."),
    ("DGSI - Direction Generale de la Securite Interieure (France)",
     "Social: No official social media accounts. Emergency: 17"),

    # ==================== Spain ====================
    ("CNI - Centro Nacional de Inteligencia (Spain)",
     "Social: Official website cni.es. Contact form: cni.es/en/contact. No public social media."),

    # ==================== Netherlands ====================
    ("AIVD - General Intelligence and Security Service (Netherlands)",
     "Social: Official website english.aivd.nl. No public social media accounts. Call +31 79 320 5050 24/7"),
    ("MIVD - Military Intelligence and Security Service (Netherlands)",
     "Social: Official website english.mindef.nl. No public social media."),

    # ==================== Sweden ====================
    ("SAPO - Swedish Security Service",
     "Social: Does not maintain official social media channels. Tips portal: tips.sakerhetspolisen.se"),

    # ==================== Turkiye ====================
    ("MIT - National Intelligence Organization (Turkiye)",
     "Social: Official website mit.gov.tr. Contact form: mit.gov.tr/en/diger.html. No public social media."),

    # ==================== India ====================
    ("RAW - Research and Analysis Wing (India)",
     "Social: No public contact available. No official social media."),
    ("IB - Intelligence Bureau (India)",
     "Social: No public contact available. No official social media."),
    ("NIA - National Investigation Agency (India)",
     "Social: X/Twitter @NIA_India, Facebook @NIAOfficeIndia. Tip portal: nia.gov.in/contact-us"),

    # ==================== China ====================
    ("MSS - Ministry of State Security (China)",
     "Social: No official social media. Hotline: 12339"),

    # ==================== South Korea ====================
    ("NIS - National Intelligence Service (South Korea)",
     "Social: Official website eng.nis.go.kr. No public social media."),

    # ==================== Singapore ====================
    ("ISD - Internal Security Department (Singapore)",
     "Social: Instagram @isd.singapore, Facebook @mhaisd"),
    ("SID - Security and Intelligence Division (Singapore)",
     "Social: Official website sid.gov.sg. No public social media."),

    # ==================== South Africa ====================
    ("SSA - State Security Agency (South Africa)",
     "Social: X/Twitter @StateSecurityRS. Website: ssa.gov.za"),

    # ==================== Japan ====================
    ("PSIA - Public Security Intelligence Agency (Japan)",
     "Social: Official website moj.go.jp/psia. No public social media."),
    ("DIH - Cabinet Intelligence and Research Office (Japan)",
     "Social: No public portal or social media."),

    # ==================== Italy ====================
    ("AISE - Agenzia Informazioni e Sicurezza Esterna (Italy)",
     "Social: No public contact portal or social media."),
    ("AISI - Agenzia Informazioni e Sicurezza Interna (Italy)",
     "Social: No public social media. Reports via Polizia di Stato (112)."),

    # ==================== Norway ====================
    ("PST - Norwegian Police Security Service",
     "Social: Official website pst.no. No official social media accounts."),
    ("NIS - Norwegian Intelligence Service (E-tjenesten)",
     "Social: Official website forsvaret.no/etjenesten. No official social media."),

    # ==================== Additional Notable ====================
    ("BVT - Federal Office for the Protection of the Constitution (Austria)",
     "Social: Official website bvt.gv.at. No official social media."),
    ("VSSE/ADIV - State Security Service (Belgium)",
     "Social: Official website vsse.be. No official social media."),
    ("PET - Danish Security and Intelligence Service",
     "Social: Official website pet.dk. No official social media accounts."),
    ("SUPO - Finnish Security Intelligence Service",
     "Social: Official website supo.fi. Explicitly states no official social media accounts."),
    ("EYP - National Intelligence Service (Greece)",
     "Social: Official website ris.gov.gr. No public social media."),
    ("IH - Information Office (Hungary)",
     "Social: Official website ih.gov.hu. No public social media."),
    ("BIN - State Intelligence Agency (Indonesia)",
     "Social: X/Twitter @OfficialBIN_RI, Instagram @officialbin_ri, YouTube @OfficialBIN_RI"),
    ("G2 - Military Intelligence (Ireland)",
     "Social: Official website military.ie. No public social media."),
    ("MEIO - Malaysian External Intelligence Organisation",
     "Social: Official website meio.gov.my. No public social media."),
    ("CNI - National Center for Intelligence (Mexico)",
     "Social: Official website gob.mx/cisen. No verified official social media."),
    ("NICA - National Intelligence Coordinating Agency (Philippines)",
     "Social: Facebook @nica.gov.ph. Website: nica.gov.ph"),
    ("ABW - Internal Security Agency (Poland)",
     "Social: Official website abw.gov.pl. No official social media accounts."),
    ("SIS - Security Intelligence Service (Portugal)",
     "Social: Official website sis.pt. No official social media."),
    ("SRI - Romanian Intelligence Service",
     "Social: Official website sri.ro. No public social media accounts."),
    ("NDB - Federal Intelligence Service (Switzerland)",
     "Social: Official website ndb.admin.ch. No official social media."),
    ("NSB - National Security Bureau (Taiwan)",
     "Social: Official website nsb.gov.tw. No public social media."),
    ("NIA - National Intelligence Agency (Thailand)",
     "Social: No official website or social media publicly available."),
    ("SBU - Security Service of Ukraine",
     "Social: Official website ssu.gov.ua. No verified international social media."),
    ("SIA - State Intelligence Agency (UAE)",
     "Social: No public contact or social media available."),
    ("TC2 - General Department of Intelligence (Vietnam)",
     "Social: No public contact or social media available."),
    ("ISI - Inter-Services Intelligence (Pakistan)",
     "Social: No public website, phone, or social media. Reports via local law enforcement."),

    # ==================== US Military / Other ====================
    ("Brazilian Federal Police (PF)",
     "Social: Instagram @policiafederal, X/Twitter @policiafederal, Facebook @policiafederal, YouTube @policiafederal"),
    ("ABIN - Brazilian Intelligence Agency",
     "Social: Official website gov.br/abin. Social links available on website."),
    ("Federal Police - Departamento de Policia Federal (Brazil)",
     "Social: Instagram @policiafederal, X/Twitter @policiafederal, Facebook @policiafederal"),
    ("Brazilian Federal Highway Police (PRF)",
     "Social: X/Twitter @PRFBrasil, Instagram @prf, Facebook @PRFoficial, YouTube @PRFBrasil"),
]


def main():
    db = get_db()

    print("🌐 Adding social media to international agencies...")
    print()

    updated = 0
    not_found = 0
    already_had = 0

    for search_term, social_notes in UPDATES:
        rows = db.execute(
            "SELECT id, company, notes FROM leads WHERE company LIKE ?",
            (f"%{search_term}%",)
        ).fetchall()

        if not rows:
            # Try a shorter search
            short = search_term.split("(")[0].strip()[:35]
            rows = db.execute(
                "SELECT id, company, notes FROM leads WHERE company LIKE ?",
                (f"%{short}%",)
            ).fetchall()

        if not rows:
            print(f"  ⚠️  NOT FOUND: {search_term[:50]}")
            not_found += 1
            continue

        for r in rows:
            lid = r["id"]
            company = r["company"]
            current_notes = r["notes"] or ""

            if "Social:" in current_notes:
                already_had += 1
                continue

            # Append social media to notes
            new_notes = current_notes.strip()
            if new_notes:
                if not new_notes.endswith(".") and not new_notes.endswith(")"):
                    new_notes += "."
                new_notes = new_notes + " " + social_notes
            else:
                new_notes = social_notes

            db.execute("UPDATE leads SET notes = ? WHERE id = ?", (new_notes.strip(), lid))
            print(f"  ✅ {company[:55]:55s} | {social_notes[:60]}...")
            updated += 1

    db.commit()

    # Final stats
    total_intl = db.execute("""
        SELECT COUNT(*) FROM leads
        WHERE vertical NOT IN ('Brazil', '')
        AND type IN ('Intelligence', 'Homeland Security', 'Government',
                     'Defense', 'Law Enforcement', 'Military')
    """).fetchone()[0]

    with_social = db.execute("""
        SELECT COUNT(*) FROM leads
        WHERE vertical NOT IN ('Brazil', '')
        AND type IN ('Intelligence', 'Homeland Security', 'Government',
                     'Defense', 'Law Enforcement', 'Military')
        AND notes LIKE '%Social:%'
    """).fetchone()[0]

    print(f"\n{'='*55}")
    print(f"  UPDATE COMPLETE")
    print(f"{'='*55}")
    print(f"  Social media added:   {updated}")
    print(f"  Already had social:   {already_had}")
    print(f"  Not found:            {not_found}")
    print(f"\n  Total international:  {total_intl}")
    print(f"  With social media:    {with_social}")

    db.close()


if __name__ == "__main__":
    main()
