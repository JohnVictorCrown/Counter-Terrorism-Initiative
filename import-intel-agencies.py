#!/usr/bin/env python3
"""
Import comprehensive global intelligence agencies into the encrypted CRM.
Includes: phones, social media handles, emails, websites, detailed notes.
Skips duplicates (matched by company name).
"""

import sqlcipher3
import uuid
from pathlib import Path

DB_PATH = Path("leads.db")
ENV_PATH = Path(".env")

# ─── Database connection ────────────────────────────────────────────────────

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

def get_existing_companies(db):
    rows = db.execute("SELECT company FROM leads").fetchall()
    return {r["company"].strip().lower() for r in rows}

# ─── Agency Records ──────────────────────────────────────────────────────────

AGENCIES = [
    # ===== UNITED STATES =====
    {
        "company": "CIA - Central Intelligence Agency",
        "contact_name": "Office of Public Affairs",
        "email": "",
        "phone": "",
        "website": "https://www.cia.gov",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "USA",
        "notes": "Foreign intelligence & counter-terrorism. Report info: https://www.cia.gov/report-information/ . Secure Tor: ciadotgov4sjwlzihbbgxnqg3xiyrg7so2r2o3lt5wz5ypk4sxyjstad.onion . Mail: Washington D.C. 20505. Social: X/Twitter @CIA, Facebook @Central.Intelligence.Agency, LinkedIn linkedin.com/company/central-intelligence-agency, YouTube @ciagov. Careers: https://www.cia.gov/careers/ . Does NOT handle domestic threats. NOTE: CIA has NO public email for intelligence reporting. Use web portal or Tor.",
        "source": "intel-research"
    },
    {
        "company": "FBI - Federal Bureau of Investigation",
        "contact_name": "FBI Tips",
        "email": "",
        "phone": "1-800-CALL-FBI (1-800-225-5324)",
        "website": "https://www.fbi.gov",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "USA",
        "notes": "Domestic intelligence, counter-terrorism & law enforcement. Tip portal: https://tips.fbi.gov . Local field offices: https://www.fbi.gov/contact-us/field-offices . Social: X/Twitter @FBI, Facebook @FBI, YouTube @fbi. Anonymous reporting available. Primary US hub for terrorism tips.",
        "source": "intel-research"
    },
    {
        "company": "DIA - Defense Intelligence Agency",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.dia.mil",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "USA",
        "notes": "Military intelligence. DoD IG: https://diaoig.oversight.gov/contacts . Social: X/Twitter @DefenseIntel, Facebook @DefenseIntel, Instagram @defenseintel, YouTube @DefenseIntel. No public tip line. Reports via DoD IG for fraud/waste/abuse.",
        "source": "intel-research"
    },
    {
        "company": "NGA - National Geospatial-Intelligence Agency",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.nga.mil",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "USA",
        "notes": "Satellite imagery & geospatial intelligence. Social: X/Twitter @NGA_GEOINT, Facebook @NatlGEOINTAgency, Instagram @nga_geoint, LinkedIn linkedin.com/company/nga. Refers public to FBI for terrorism/intelligence tips.",
        "source": "intel-research"
    },

    # ===== UNITED KINGDOM =====
    {
        "company": "MI5 - Security Service (UK)",
        "contact_name": "",
        "email": "",
        "phone": "0800 789 321",
        "website": "https://www.mi5.gov.uk",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "UK",
        "notes": "Counter-terrorism, counter-espionage, domestic security. Contact form: https://www.mi5.gov.uk/contact-us . Anti-Terrorist Hotline: 0800 789 321. Voicemail: 0800 111 4645. Emergency: 999. Social: X/Twitter @MI5_Official, Instagram @mi5official. Primary UK terrorism reporting channel. Anonymous options available.",
        "source": "intel-research"
    },
    {
        "company": "MI6 / SIS - Secret Intelligence Service (UK)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.sis.gov.uk",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "UK",
        "notes": "Foreign intelligence. Social: Instagram @mi6, YouTube @mi6. No public tip line. Refers security threats to MI5 or local police. Emergency: 999.",
        "source": "intel-research"
    },
    {
        "company": "GCHQ - Government Communications Headquarters (UK)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.gchq.gov.uk",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "UK",
        "notes": "Signals intelligence & cybersecurity. Social: X/Twitter @GCHQ, Instagram @gchq. Primarily administrative/cyber security inquiries. No public tip portal.",
        "source": "intel-research"
    },

    # ===== CANADA =====
    {
        "company": "CSIS - Canadian Security Intelligence Service",
        "contact_name": "",
        "email": "",
        "phone": "1-800-420-5805",
        "website": "https://www.canada.ca/en/security-intelligence-service.html",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "Canada",
        "notes": "Civilian intelligence agency. Reporting form: https://www.canada.ca/en/security-intelligence-service/corporate/reporting-national-security-information.html . Social: X/Twitter @csiscanada, Facebook @csiscanada, YouTube @csisscrs. Reports suspicious activity threatening national security. Emergency: 911.",
        "source": "intel-research"
    },
    {
        "company": "CSE - Communications Security Establishment (Canada)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.cse-cst.gc.ca",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "Canada",
        "notes": "Signals intelligence & cybersecurity. Social: X/Twitter @cse_cst, Instagram @cse_cst, YouTube @communicationssecurityestablishment. Cyber security & foreign signals intelligence.",
        "source": "intel-research"
    },

    # ===== AUSTRALIA =====
    {
        "company": "ASIO - Australian Security Intelligence Organisation",
        "contact_name": "",
        "email": "",
        "phone": "1800 123 400",
        "website": "https://www.asio.gov.au",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "Australia",
        "notes": "Domestic intelligence & counter-terrorism. National Security Hotline: 1800 123 400 (24/7). Reporting: https://www.nationalsecurity.gov.au/what-can-i-do/report-suspicious-behaviour . Social: X/Twitter @ASIOGovAu, Facebook @asiogovau, Instagram @asiogovau. Emergency: 000 (Triple Zero).",
        "source": "intel-research"
    },
    {
        "company": "ASIS - Australian Secret Intelligence Service",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.asis.gov.au",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "Australia",
        "notes": "Foreign intelligence. No public tip line. Refers to ASIO for domestic threats. Emergency: 000.",
        "source": "intel-research"
    },
    {
        "company": "ASD - Australian Signals Directorate",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.asd.gov.au",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "Australia",
        "notes": "Signals intelligence & cyber security. Cyber reporting: https://www.cyber.gov.au . Social: X/Twitter @ASDGovAu, Facebook @cybergovau. Cyber threat reporting via ACSC (Australian Cyber Security Centre).",
        "source": "intel-research"
    },

    # ===== NEW ZEALAND =====
    {
        "company": "NZSIS - New Zealand Security Intelligence Service",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.nzsis.govt.nz",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "New Zealand",
        "notes": "Domestic intelligence. Report concern: https://www.nzsis.govt.nz/contact-us/reporting-a-national-security-concern . Clear online form for reporting foreign interference, espionage, terrorism. Emergency: 111.",
        "source": "intel-research"
    },
    {
        "company": "GCSB - Government Communications Security Bureau (NZ)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.gcsb.govt.nz",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "New Zealand",
        "notes": "Signals intelligence & cyber security. Foreign intelligence & cyber security. No public tip portal.",
        "source": "intel-research"
    },

    # ===== ISRAEL =====
    {
        "company": "Shin Bet / Shabak - Israel Security Agency",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.shabak.gov.il/en",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "Israel",
        "notes": "Domestic security & counter-terrorism. No direct public tip line. Urgent threats: call Israel Police at 100.",
        "source": "intel-research"
    },

    # ===== GERMANY =====
    {
        "company": "BND - Bundesnachrichtendienst (Germany)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.bnd.bund.de",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "Germany",
        "notes": "Foreign intelligence. Social: Instagram @bndkarriere (career account). For domestic threats, contact BfV. Emergency: 110.",
        "source": "intel-research"
    },
    {
        "company": "BfV - Federal Office for Protection of the Constitution (Germany)",
        "contact_name": "",
        "email": "hinweise@bfv.bund.de",
        "phone": "+49 (0)228 99 792-6000",
        "website": "https://www.verfassungsschutz.de",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "Germany",
        "notes": "Domestic intelligence & counter-terrorism. Reporting: https://www.verfassungsschutz.de/EN/service/contact/report-a-threat . Social: X/Twitter @BfV_Bund, Instagram @bfv_bund, LinkedIn linkedin.com/company/bundesamt-fuer-verfassungsschutz. Primary German domestic intelligence reporting channel. Emergency: 110.",
        "source": "intel-research"
    },

    # ===== FRANCE =====
    {
        "company": "DGSE - Direction Generale de la Securite Exterieure (France)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.defense.gouv.fr/dgse",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "France",
        "notes": "Foreign intelligence. No public tip portal. Emergency: 112 / 17 (Police Secours).",
        "source": "intel-research"
    },
    {
        "company": "DGSI - Direction Generale de la Securite Interieure (France)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.interieur.gouv.fr/dgsi",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "France",
        "notes": "Domestic intelligence & counter-terrorism. Reports via local police or national gendarmerie. Emergency: 112 / 17.",
        "source": "intel-research"
    },

    # ===== SPAIN =====
    {
        "company": "CNI - Centro Nacional de Inteligencia (Spain)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.cni.es",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "Spain",
        "notes": "National intelligence. Contact form: https://www.cni.es/en/contact . Administrative/institutional focus. Reports to local police.",
        "source": "intel-research"
    },

    # ===== NETHERLANDS =====
    {
        "company": "AIVD - General Intelligence and Security Service (Netherlands)",
        "contact_name": "",
        "email": "",
        "phone": "+31 79 320 5050",
        "website": "https://english.aivd.nl",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "Netherlands",
        "notes": "Domestic & foreign intelligence. 24/7 phone: +31 79 320 5050. Contact: https://english.aivd.nl/service/contact . Does NOT accept information via email (security concern). Call 24/7 line. Emergency: 112.",
        "source": "intel-research"
    },
    {
        "company": "MIVD - Military Intelligence and Security Service (Netherlands)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://english.mindef.nl/organisation/mivd",
        "tier": "1",
        "type": "Military",
        "vertical": "Netherlands",
        "notes": "Military intelligence. Reports via military channels.",
        "source": "intel-research"
    },

    # ===== SWEDEN =====
    {
        "company": "SAPO - Swedish Security Service",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.sakerhetspolisen.se",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "Sweden",
        "notes": "Domestic security & counter-terrorism. Tips portal: https://tips.sakerhetspolisen.se/tips/helpus?lang=en . Does not maintain official social media channels. Emergency: 112.",
        "source": "intel-research"
    },

    # ===== TURKIYE =====
    {
        "company": "MIT - National Intelligence Organization (Turkiye)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.mit.gov.tr",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "Turkiye",
        "notes": "National intelligence. Contact/Info form: https://www.mit.gov.tr/en/diger.html ('How You Can Help'). Protects identity of informants. Emergency: 112.",
        "source": "intel-research"
    },

    # ===== INDIA =====
    {
        "company": "RAW - Research and Analysis Wing (India)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "India",
        "notes": "Foreign intelligence. No public contact information available. Domestic threats contact IB or NIA.",
        "source": "intel-research"
    },
    {
        "company": "IB - Intelligence Bureau (India)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "India",
        "notes": "Domestic intelligence. No public contact information available.",
        "source": "intel-research"
    },
    {
        "company": "NIA - National Investigation Agency (India)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://nia.gov.in",
        "tier": "1",
        "type": "Government",
        "vertical": "India",
        "notes": "Counter-terrorism agency. Tip portal: https://nia.gov.in/contact-us . Social: X/Twitter @NIA_India, Facebook @NIAOfficeIndia. Official terror tip portal. Identity kept confidential. Emergency: 112.",
        "source": "intel-research"
    },

    # ===== CHINA =====
    {
        "company": "MSS - Ministry of State Security (China)",
        "contact_name": "",
        "email": "",
        "phone": "12339",
        "website": "",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "China",
        "notes": "National security & intelligence. Public hotline: 12339 for reporting espionage & national security threats. Online reporting portal also available.",
        "source": "intel-research"
    },

    # ===== SOUTH KOREA =====
    {
        "company": "NIS - National Intelligence Service (South Korea)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://eng.nis.go.kr",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "South Korea",
        "notes": "National intelligence & cybersecurity. No public reporting portal visible. Reports to local police. Emergency: 112.",
        "source": "intel-research"
    },

    # ===== SINGAPORE =====
    {
        "company": "ISD - Internal Security Department (Singapore)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.mha.gov.sg/isd",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "Singapore",
        "notes": "Domestic security. Social: Instagram @isd.singapore, Facebook @mhaisd. Reports to Singapore Police Force. Emergency: 999.",
        "source": "intel-research"
    },
    {
        "company": "SID - Security and Intelligence Division (Singapore)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.sid.gov.sg",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "Singapore",
        "notes": "External intelligence. No public reporting portal. Emergency: 999.",
        "source": "intel-research"
    },

    # ===== BRAZIL =====
    {
        "company": "Federal Police - Departamento de Policia Federal (Brazil)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.gov.br/pf",
        "tier": "1",
        "type": "Law Enforcement",
        "vertical": "Brazil",
        "notes": "Counter-terrorism & national security. Social: Instagram @policiafederal. Emergency: 190.",
        "source": "intel-research"
    },

    # ===== SOUTH AFRICA =====
    {
        "company": "SSA - State Security Agency (South Africa)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.ssa.gov.za",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "South Africa",
        "notes": "National intelligence. Social: X/Twitter @StateSecurityRS. Limited public contact information.",
        "source": "intel-research"
    },

    # ===== PAKISTAN =====
    {
        "company": "ISI - Inter-Services Intelligence (Pakistan)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "Pakistan",
        "notes": "Military intelligence. No public website, phone, or tip portal. Reports to local law enforcement or military authorities.",
        "source": "intel-research"
    },

    # ===== JAPAN =====
    {
        "company": "PSIA - Public Security Intelligence Agency (Japan)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.moj.go.jp/psia",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "Japan",
        "notes": "Domestic intelligence. Reports to local police. Emergency: 110.",
        "source": "intel-research"
    },
    {
        "company": "DIH - Cabinet Intelligence and Research Office (Japan)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "Japan",
        "notes": "Foreign intelligence coordination. No public portal.",
        "source": "intel-research"
    },

    # ===== ITALY =====
    {
        "company": "AISE - Agenzia Informazioni e Sicurezza Esterna (Italy)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "Italy",
        "notes": "Foreign intelligence. No public contact portal. Emergency: 112.",
        "source": "intel-research"
    },
    {
        "company": "AISI - Agenzia Informazioni e Sicurezza Interna (Italy)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "Italy",
        "notes": "Domestic intelligence. Reports to Polizia di Stato or Carabinieri. Emergency: 112.",
        "source": "intel-research"
    },

    # ===== NORWAY =====
    {
        "company": "PST - Norwegian Police Security Service",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.pst.no",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "Norway",
        "notes": "Domestic security & counter-terrorism. No official social media accounts. Emergency: 112.",
        "source": "intel-research"
    },
    {
        "company": "NIS - Norwegian Intelligence Service (E-tjenesten)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.forsvaret.no/etjenesten",
        "tier": "1",
        "type": "Intelligence",
        "vertical": "Norway",
        "notes": "Foreign & military intelligence. No official social media accounts.",
        "source": "intel-research"
    },

    # ===== ADDITIONAL NOTABLE AGENCIES =====
    {
        "company": "BVT - Federal Office for the Protection of the Constitution (Austria)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.bvt.gv.at",
        "tier": "2",
        "type": "Intelligence",
        "vertical": "Austria",
        "notes": "Domestic intelligence. Limited public contact. Emergency: 112.",
        "source": "intel-research"
    },
    {
        "company": "VSSE/ADIV - State Security Service (Belgium)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.vsse.be",
        "tier": "2",
        "type": "Intelligence",
        "vertical": "Belgium",
        "notes": "Both domestic & foreign intelligence. No official social media. Emergency: 112.",
        "source": "intel-research"
    },
    {
        "company": "PET - Danish Security and Intelligence Service",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.pet.dk",
        "tier": "2",
        "type": "Intelligence",
        "vertical": "Denmark",
        "notes": "Domestic intelligence & counter-terrorism. No official social media accounts. Emergency: 112.",
        "source": "intel-research"
    },
    {
        "company": "SUPO - Finnish Security Intelligence Service",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://supo.fi",
        "tier": "2",
        "type": "Intelligence",
        "vertical": "Finland",
        "notes": "Domestic intelligence. Explicitly states no official social media accounts. Emergency: 112.",
        "source": "intel-research"
    },
    {
        "company": "EYP - National Intelligence Service (Greece)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.ris.gov.gr",
        "tier": "2",
        "type": "Intelligence",
        "vertical": "Greece",
        "notes": "National intelligence service. Emergency: 112.",
        "source": "intel-research"
    },
    {
        "company": "IH - Information Office (Hungary)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.ih.gov.hu",
        "tier": "2",
        "type": "Intelligence",
        "vertical": "Hungary",
        "notes": "National intelligence service. Emergency: 112.",
        "source": "intel-research"
    },
    {
        "company": "BIN - State Intelligence Agency (Indonesia)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.bin.go.id",
        "tier": "2",
        "type": "Intelligence",
        "vertical": "Indonesia",
        "notes": "National intelligence. Social: X/Twitter @OfficialBIN_RI, Instagram @officialbin_ri, YouTube @OfficialBIN_RI.",
        "source": "intel-research"
    },
    {
        "company": "G2 - Military Intelligence (Ireland)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.military.ie",
        "tier": "2",
        "type": "Military",
        "vertical": "Ireland",
        "notes": "Military intelligence. Part of Irish Defence Forces. Emergency: 112.",
        "source": "intel-research"
    },
    {
        "company": "MEIO - Malaysian External Intelligence Organisation",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.meio.gov.my",
        "tier": "2",
        "type": "Intelligence",
        "vertical": "Malaysia",
        "notes": "Foreign intelligence. Emergency: 999.",
        "source": "intel-research"
    },
    {
        "company": "CNI - National Center for Intelligence (Mexico)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.gob.mx/cisen",
        "tier": "2",
        "type": "Intelligence",
        "vertical": "Mexico",
        "notes": "Domestic intelligence & national security. Emergency: 911.",
        "source": "intel-research"
    },
    {
        "company": "NICA - National Intelligence Coordinating Agency (Philippines)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.nica.gov.ph",
        "tier": "2",
        "type": "Intelligence",
        "vertical": "Philippines",
        "notes": "National intelligence coordination. Social: Facebook @nica.gov.ph. Emergency: 911.",
        "source": "intel-research"
    },
    {
        "company": "ABW - Internal Security Agency (Poland)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.abw.gov.pl",
        "tier": "2",
        "type": "Intelligence",
        "vertical": "Poland",
        "notes": "Domestic intelligence & counter-terrorism. No official social media accounts. Emergency: 112.",
        "source": "intel-research"
    },
    {
        "company": "SIS - Security Intelligence Service (Portugal)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.sis.pt",
        "tier": "2",
        "type": "Intelligence",
        "vertical": "Portugal",
        "notes": "National intelligence service. No official social media. Emergency: 112.",
        "source": "intel-research"
    },
    {
        "company": "SRI - Romanian Intelligence Service",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.sri.ro",
        "tier": "2",
        "type": "Intelligence",
        "vertical": "Romania",
        "notes": "Domestic intelligence. Emergency: 112.",
        "source": "intel-research"
    },
    {
        "company": "NDB - Federal Intelligence Service (Switzerland)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.ndb.admin.ch",
        "tier": "2",
        "type": "Intelligence",
        "vertical": "Switzerland",
        "notes": "National intelligence service. No official social media. Emergency: 112.",
        "source": "intel-research"
    },
    {
        "company": "NSB - National Security Bureau (Taiwan)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://www.nsb.gov.tw",
        "tier": "2",
        "type": "Intelligence",
        "vertical": "Taiwan",
        "notes": "National intelligence coordination & security. Emergency: 110.",
        "source": "intel-research"
    },
    {
        "company": "NIA - National Intelligence Agency (Thailand)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "",
        "tier": "2",
        "type": "Intelligence",
        "vertical": "Thailand",
        "notes": "National intelligence. Limited public information. Emergency: 191.",
        "source": "intel-research"
    },
    {
        "company": "SBU - Security Service of Ukraine",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "https://ssu.gov.ua",
        "tier": "2",
        "type": "Intelligence",
        "vertical": "Ukraine",
        "notes": "Domestic & foreign intelligence, counter-terrorism. Emergency: 102.",
        "source": "intel-research"
    },
    {
        "company": "SIA - State Intelligence Agency (UAE)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "",
        "tier": "2",
        "type": "Intelligence",
        "vertical": "UAE",
        "notes": "National intelligence. Limited public information. Emergency: 999.",
        "source": "intel-research"
    },
    {
        "company": "TC2 - General Department of Intelligence (Vietnam)",
        "contact_name": "",
        "email": "",
        "phone": "",
        "website": "",
        "tier": "2",
        "type": "Intelligence",
        "vertical": "Vietnam",
        "notes": "Military intelligence. Limited public information. Emergency: 113.",
        "source": "intel-research"
    },
]

# ─── Main import ─────────────────────────────────────────────────────────────

def main():
    db = get_db()
    existing = get_existing_companies(db)

    print(f"🚀 Importing intelligence agencies into CRM...")
    print(f"   Agencies defined: {len(AGENCIES)}")
    print(f"   Existing companies in DB: {len(existing)}")
    print()

    inserted = 0
    skipped = 0

    for a in AGENCIES:
        key = a["company"].strip().lower()
        if key in existing:
            print(f"  ⏭️  SKIP (exists): {a['company']}")
            skipped += 1
            continue

        lid = str(uuid.uuid4())
        db.execute(
            """INSERT INTO leads
               (id, company, contact_name, email, phone, website,
                tier, type, vertical, status, notes, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'cold', ?, ?)""",
            (lid, a["company"], a["contact_name"], a["email"],
             a["phone"], a["website"], a["tier"], a["type"],
             a["vertical"], a["notes"], a["source"])
        )
        print(f"  ✅ INSERT: {a['company']}")
        inserted += 1

    db.commit()

    print(f"\n{'='*50}")
    print(f"  IMPORT COMPLETE")
    print(f"  Inserted: {inserted}")
    print(f"  Skipped (duplicates): {skipped}")
    print(f"{'='*50}")

    # Final stats
    total = db.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    intel_count = db.execute("SELECT COUNT(*) FROM leads WHERE type = 'Intelligence'").fetchone()[0]
    print(f"\n  Total leads in DB: {total}")
    print(f"  Intelligence agencies: {intel_count}")

    db.close()


if __name__ == "__main__":
    main()
