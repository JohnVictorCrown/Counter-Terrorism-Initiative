#!/usr/bin/env python3
"""
import-contacts.py — Parse .txt contact files, classify each, and import into encrypted CRM.

Classifies contacts as Brazilian Military, Brazilian Intelligence, Brazilian Federal/State Security,
US Military/Defense, US Intelligence, US Homeland Security, US Law Enforcement, or Israeli Intelligence.

Usage:
    python import-contacts.py
"""

import sqlcipher3
import uuid
import re
import sys
from pathlib import Path

DB_PATH = Path("leads.db")
ENV_PATH = Path(".env")

# ─── Classification Rules ───────────────────────────────────────────────────

def classify_email(email: str) -> dict:
    """Classify an email address and return structured metadata."""
    domain = email.lower().split("@")[-1].strip() if "@" in email else email.lower().strip()
    company = domain
    org_type = "Unknown"
    country = "Unknown"
    tier = "3"  # default: Local
    notes = ""

    # ── Brazilian Military (Army) ──
    if domain.endswith(".eb.mil.br"):
        org_type = "Military"
        country = "Brazil"
        company = extract_brazilian_army_unit(email, domain)
        tier = "2"
        notes = f"Brazilian Army - {domain}"

    # ── Brazilian Intelligence (ABIN) ──
    elif "abin.gov.br" in domain:
        org_type = "Intelligence"
        country = "Brazil"
        company = "ABIN - Brazilian Intelligence Agency"
        tier = "1"
        notes = f"Brazilian Intelligence Agency (ABIN) - {domain}"

    # ── Brazilian Ministry of Defense ──
    elif domain == "defesa.gov.br" or "defesa.gov.br" in domain:
        org_type = "Defense"
        country = "Brazil"
        company = "Brazilian Ministry of Defense"
        tier = "1"
        notes = "Brazilian Ministry of Defense"

    # ── Brazilian Ministry of Justice ──
    elif "mj.gov.br" in domain:
        org_type = "Government"
        country = "Brazil"
        company = "Brazilian Ministry of Justice"
        tier = "3"
        notes = f"Ministry of Justice - {domain}"

    # ── Brazilian Federal Police ──
    elif "pf.gov.br" in domain:
        org_type = "Law Enforcement"
        country = "Brazil"
        company = "Brazilian Federal Police (PF)"
        tier = "1"
        notes = "Brazilian Federal Police - Polícia Federal"

    # ── Brazilian Federal Highway Police ──
    elif "prf.gov.br" in domain:
        org_type = "Law Enforcement"
        country = "Brazil"
        company = "Brazilian Federal Highway Police (PRF)"
        tier = "2"
        notes = "Brazilian Federal Highway Police - Polícia Rodoviária Federal"

    # ── Brazilian State Security ──
    elif domain in ("sds.pe.gov.br",) or "sds.pe.gov.br" in domain:
        org_type = "Security"
        country = "Brazil"
        company = "SDS-PE - Secretaria de Defesa Social de Pernambuco"
        tier = "2"
        notes = "Pernambuco Public Security Secretariat"

    elif "pm.pe.gov.br" in domain:
        org_type = "Security"
        country = "Brazil"
        company = "PMPE - Polícia Militar de Pernambuco"
        tier = "2"
        notes = "Pernambuco Military Police"

    elif "sad.pe.gov.br" in domain:
        org_type = "Government"
        country = "Brazil"
        company = "SAD-PE - Secretaria de Administração de Pernambuco"
        tier = "3"
        notes = "Pernambuco Administration Secretariat"

    # ── Brazilian Army CCOMSEX ──
    elif "ccomex.eb.mil.br" in domain or "ccsomex.eb.mil.br" in domain:
        org_type = "Military"
        country = "Brazil"
        company = "Brazilian Army - CCOMSEX (Army Social Communication)"
        tier = "1"
        notes = "Brazilian Army Social Communication Center"

    # ── Brazilian Military Ordinariate ──
    elif "ordinariadomilitar.org.br" in domain:
        org_type = "Military"
        country = "Brazil"
        company = "Brazilian Military Ordinariate"
        tier = "3"
        notes = "Military Catholic Church - Brazil"

    # ── US Military ──
    elif any(domain.endswith(s) for s in [".af.mil", ".army.mil", ".navy.mil", ".usmc.mil", ".uscg.mil", ".spaceforce.mil", ".mil"]):
        org_type = "Military"
        country = "USA"
        company = extract_us_military_unit(email, domain)
        tier = "2"
        notes = f"US Military - {domain}"

    # ── US Department of Defense ──
    elif domain in ("defense.gov",) or "defense.gov" in domain:
        org_type = "Defense"
        country = "USA"
        company = "US Department of Defense"
        tier = "2"
        notes = "US Department of Defense"

    elif "dodig.mil" in domain:
        org_type = "Defense"
        country = "USA"
        company = "US DoD Inspector General"
        tier = "2"
        notes = "Department of Defense Office of Inspector General"

    # ── US Intelligence ──
    elif "dia.mil" in domain:
        org_type = "Intelligence"
        country = "USA"
        company = "DIA - Defense Intelligence Agency"
        tier = "1"
        notes = "US Defense Intelligence Agency"

    elif "dni.gov" in domain or "odni.gov" in domain:
        org_type = "Intelligence"
        country = "USA"
        company = "ODNI - Office of the Director of National Intelligence"
        tier = "1"
        notes = "US Office of the Director of National Intelligence"

    elif "nga.mil" in domain:
        org_type = "Intelligence"
        country = "USA"
        company = "NGA - National Geospatial-Intelligence Agency"
        tier = "1"
        notes = "US National Geospatial-Intelligence Agency"

    elif "nsa.gov" in domain:
        org_type = "Intelligence"
        country = "USA"
        company = "NSA - National Security Agency"
        tier = "1"
        notes = "US National Security Agency"

    # ── US Homeland Security ──
    elif "dhs.gov" in domain or any(d.endswith(".dhs.gov") for d in [domain]):
        org_type = "Homeland Security"
        country = "USA"
        company = extract_dhs_agency(email, domain)
        tier = "2"
        notes = f"US Department of Homeland Security - {domain}"

    # ── US Law Enforcement ──
    elif "usdoj.gov" in domain:
        org_type = "Law Enforcement"
        country = "USA"
        company = "US Department of Justice"
        tier = "2"
        notes = "US Department of Justice"

    # ── Israeli Intelligence ──
    elif "mail.gov.il" in domain or "gov.il" in domain:
        org_type = "Intelligence"
        country = "Israel"
        company = "Israeli Government / Mossad"
        tier = "1"
        notes = "Israeli government email domain - intelligence/defense"

    # ── Brazilian miscellaneous (.gov.br, .com.br, etc) ──
    elif "casadamilitarpe" in email.lower():
        org_type = "Military"
        country = "Brazil"
        company = "Casa Militar de Pernambuco"
        tier = "2"
        notes = "Pernambuco State Military House"

    elif domain.endswith(".gov.br") or domain.endswith(".com.br") or domain.endswith(".org.br"):
        org_type = "Government"
        country = "Brazil"
        company = domain
        tier = "3"
        notes = f"Brazilian government/organization - {domain}"

    # ── Brazilian Army TG / Tiros de Guerra ──
    elif any(k in email.lower() for k in ["tg0", "tirodeguerra"]):
        org_type = "Military"
        country = "Brazil"
        company = f"Brazilian Army - Shooting Range Unit ({domain})"
        tier = "3"
        notes = f"Brazilian Army TG (Tiro de Guerra) unit - {email}"

    return {
        "company": company,
        "org_type": org_type,
        "country": country,
        "tier": tier,
        "notes": notes,
        "email": email.strip().lower(),
    }


def extract_brazilian_army_unit(email: str, domain: str) -> str:
    """Extract a readable Brazilian Army unit name from the email context."""
    email_lower = email.lower()
    # Try to identify specific units from the email prefix or domain
    if "comsoc" in email_lower:
        # Social Communication sections - extract unit if possible
        if "2rm" in domain or "2rm" in email_lower:
            return "Brazilian Army - 2nd Military Region (2ª RM)"
        if "7rm" in domain or "7rm" in email_lower:
            return "Brazilian Army - 7th Military Region (7ª RM)"
        if "aman" in email_lower:
            return "Brazilian Army - AMAN (Agulhas Negras Military Academy)"
        if "cml" in email_lower:
            return "Brazilian Army - CML (Eastern Military Command)"
        if "cmse" in email_lower:
            return "Brazilian Army - CMSE (Southeastern Military Command)"
        if "cma" in email_lower:
            return "Brazilian Army - CMA (Amazon Military Command)"
        if "cmo" in email_lower:
            return "Brazilian Army - CMO (Western Military Command)"
        if "cms" in email_lower:
            return "Brazilian Army - CMS (Southern Military Command)"
        if "eme" in email_lower:
            return "Brazilian Army - EME (General Staff)"
        if "coter" in email_lower:
            return "Brazilian Army - COTER (Land Operations Command)"
        if "esie" in email_lower:
            return "Brazilian Army - ESIE (Army Intelligence School)"
        if "ccfex" in email_lower:
            return "Brazilian Army - CCFEx (Army Cavalry School)"
        if "colog" in email_lower:
            return "Brazilian Army - COLOG (Logistics Command)"
        if "ctex" in email_lower:
            return "Brazilian Army - CTEx (Army Technology Center)"
        if "dct" in email_lower:
            return "Brazilian Army - DCT (Science & Technology Dept)"
        if "decex" in email_lower:
            return "Brazilian Army - DECEx (Army Education Dept)"
        if "dsg" in email_lower:
            return "Brazilian Army - DSG (Geographic Service Directorate)"
        if "cig" in email_lower:
            return "Brazilian Army - CIG (Army Information Center)"
        if "hce" in email_lower:
            return "Brazilian Army - HCE (Central Army Hospital)"
        if "hmab" in email_lower:
            return "Brazilian Army - HMAB (Brasília Army Hospital)"
        if "enadciber" in email_lower:
            return "Brazilian Army - ENADCIBER (National Cyber Defense School)"
        if "ceadex" in email_lower:
            return "Brazilian Army - CEADEx (Army Distance Learning Center)"
        if "cidex" in email_lower:
            return "Brazilian Army - CIDEx (Army Doctrine Center)"
        if "cpex" in email_lower:
            return "Brazilian Army - CPEx (Army Personnel Center)"
        if "dcmun" in email_lower:
            return "Brazilian Army - DCMun (Army Munitions Directorate)"
        if "depa" in email_lower:
            return "Brazilian Army - DEPA (Army Property Directorate)"
        if "dsau" in email_lower:
            return "Brazilian Army - DSAU (Army Health Directorate)"
        if "dmem" in email_lower:
            return "Brazilian Army - DSMEM (Army Memorial Directorate)"
        if "dpgo" in email_lower:
            return "Brazilian Army - DPGO (General Planning Directorate)"
        if "basecmp" in email_lower:
            return "Brazilian Army - Base CMP (Campo de Provas)"
        if "pmb" in email_lower:
            return "Brazilian Army - PMB (Brasília Military Police)"
        if "pmn" in email_lower:
            return "Brazilian Army - PMN (Northern Military Police)"
        if "pmrj" in email_lower:
            return "Brazilian Army - PMRJ (Rio de Janeiro Military Police)"
        if "pmzs" in email_lower:
            return "Brazilian Army - PMZS (Zona Sul Military Police)"
        # General comsoc
        unit_match = re.search(r'comsoc@([\w-]+)', email_lower)
        if unit_match:
            return f"Brazilian Army - {unit_match.group(1).upper()} (Social Communication)"
        return f"Brazilian Army - Social Communication ({domain})"
    
    if "rp@" in email_lower or "rp." in email_lower:
        return f"Brazilian Army - Public Relations ({domain})"
    if "imprensa" in email_lower:
        if "cml" in email_lower:
            return "Brazilian Army - CML Press Office"
        if "cmse" in email_lower:
            return "Brazilian Army - CMSE Press Office"
        if "cma" in email_lower:
            return "Brazilian Army - CMA Press Office"
        if "ccomex" in email_lower or "ccsomex" in email_lower:
            return "Brazilian Army - CCOMSEX Press Office"
        return f"Brazilian Army - Press Office ({domain})"
    if "protocolo" in email_lower:
        return f"Brazilian Army - Protocol ({domain})"
    if "ouvidoria" in email_lower:
        if ".eb.mil.br" in domain:
            return "Brazilian Army - Ombudsman Office"
        return "Brazilian Government - Ombudsman"
    if "sgex" in email_lower:
        return "Brazilian Army - SGEx (Army General Secretariat)"
    if "dcem" in email_lower:
        return "Brazilian Army - DCEM (Military Education Directorate)"
    if "dec" in email_lower:
        return "Brazilian Army - DEC (Education Command)"
    if "dic" in email_lower:
        return "Brazilian Army - DIC (IT Directorate)"
    if "cds" in email_lower:
        return "Brazilian Army - CDS (Southern Defense Center)"
    if "ciex" in email_lower:
        return "Brazilian Army - CIEx (Army Intelligence Center)"
    if "ciopesp" in email_lower:
        return "Brazilian Army - CIOPESP (Special Operations Center)"
    if "bpe" in email_lower:
        return "Brazilian Army - BPE (Special Police Battalion)"
    if "bpeb" in email_lower or "bpe " in email_lower:
        return "Brazilian Army - BPEB (Special Police Battalion)"
    if "bavt" in email_lower:
        return "Brazilian Army - BAvT (Army Aviation Battalion)"
    if "bmsa" in email_lower:
        return "Brazilian Army - BMSA (Health Battalion)"
    if "bdompsa" in email_lower:
        return "Brazilian Army - BDomPSA (Army Police Battalion)"
    if "bapr" in email_lower:
        return "Brazilian Army - BAPR (Army Police Battalion)"
    if "badm" in email_lower:
        return "Brazilian Army - BAdm (Administrative Battalion)"
    if "gac" in email_lower:
        return "Brazilian Army - GAC (Artillery Group)"
    if "gaaae" in email_lower:
        return "Brazilian Army - GAAAE (Air Defense Artillery Group)"
    if "rcmec" in email_lower or "rcg" in email_lower:
        return "Brazilian Army - RC (Cavalry Regiment)"
    if "bimtz" in email_lower:
        return "Brazilian Army - BI (Mechanized Infantry Battalion)"
    if "bpeb" in email_lower:
        return "Brazilian Army - BPEB (Special Police Battalion)"
    if "gpt" in email_lower or "gpte" in email_lower:
        return "Brazilian Army - GptE (Army Engineer Group)"
    if "blog" in email_lower or "blogl" in email_lower:
        return "Brazilian Army - B Log (Logistics Battalion)"
    if "bda" in email_lower:
        return "Brazilian Army - Bda (Brigade)"
    if "cgeo" in email_lower:
        return "Brazilian Army - CGeo (Geographic Company)"
    if "cta" in email_lower:
        return "Brazilian Army - CTA (Communications Company)"
    if "cia" in email_lower and "ecmb" in email_lower:
        return "Brazilian Army - CIAC (Armored Company)"
    if "dsup" in email_lower:
        return "Brazilian Army - DSup (Support Division)"
    if "de" in email_lower and domain.startswith("7"):
        return "Brazilian Army - 7th Division"
    if "divisao" in email_lower:
        return "Brazilian Army - Division"
    if "bef" in email_lower or "becmb" in email_lower:
        return "Brazilian Army - BECmb (Engineer Combat Battalion)"
    if "lqfex" in email_lower:
        return "Brazilian Army - LQFEx (Army Physical Chemistry Lab)"
    if "graficadoexercito" in email_lower:
        return "Brazilian Army - Graphic Services"
    if "idqbrn" in email_lower:
        return "Brazilian Army - IDQBRN (Nuclear/Bio/Chemical Defense Institute)"
    if "iefex" in email_lower:
        return "Brazilian Army - IEFEx (Army Finance Institute)"
    if "ipcfex" in email_lower:
        return "Brazilian Army - IPCFEx (Army Pension Institute)"
    if "ime" in email_lower:
        return "Brazilian Army - IME (Military Engineering Institute)"
    if "esie" in email_lower:
        return "Brazilian Army - ESIE (Army Intelligence School)"
    if "cro" in email_lower:
        return "Brazilian Army - CRO (Regional Communications Center)"
    if "tg" in email_lower or "tirodeguerra" in email_lower:
        return "Brazilian Army - TG (Shooting Range Unit)"
    if "aditancia" in email_lower or "adiex" in email_lower:
        return "Brazilian Army - Military Attaché"
    if "cmp" in email_lower:
        return "Brazilian Army - CMP (Military Command)"
    if "cmn" in email_lower or "cmne" in email_lower:
        return "Brazilian Army - CMN (Northeastern Military Command)"
    
    return f"Brazilian Army - Unit ({domain})"


def extract_us_military_unit(email: str, domain: str) -> str:
    """Extract a readable US military unit name."""
    email_lower = email.lower()
    domain_lower = domain.lower()
    
    if "af.mil" in domain_lower:
        if "pa.mediaops" in email_lower or "mediaops" in email_lower:
            return "US Air Force - Media Operations (PA)"
        return "US Air Force"
    if "army.mil" in domain_lower:
        if "cjtf-oir" in email_lower:
            return "US Army - CJTF-OIR (Combined Joint Task Force)"
        if "carlisle" in email_lower or "awc" in email_lower:
            return "US Army - Army War College"
        if "safe-pao" in email_lower:
            return "US Army - SAFE PAO (Public Affairs)"
        if "tagd-ask-hrc" in email_lower:
            return "US Army - HRC (Human Resources Command)"
        if "n-ncspecialstaff" in email_lower:
            return "US Army - National Capital Special Staff"
        return "US Army"
    if "navy.mil" in domain_lower:
        if "nmic" in email_lower:
            return "US Navy - NMIC (Naval Maritime Intelligence Center)"
        if "usff" in email_lower or "nflt" in email_lower:
            return "US Navy - Fleet Forces"
        return "US Navy"
    if "uscg.mil" in domain_lower:
        return "US Coast Guard - Media Relations"
    if "nga.mil" in domain_lower:
        return "NGA - National Geospatial-Intelligence Agency"
    if "nmic.navy.mil" in domain_lower:
        return "US Navy - NMIC"
    if "dia.mil" in domain_lower:
        return "DIA - Defense Intelligence Agency"
    return f"US Military - {domain}"


def extract_dhs_agency(email: str, domain: str) -> str:
    """Extract the specific DHS agency."""
    email_lower = email.lower()
    if "ice" in email_lower or "ice.dhs.gov" in domain:
        return "ICE - Immigration and Customs Enforcement"
    if "fema" in email_lower:
        return "FEMA - Federal Emergency Management Agency"
    if "tsa" in email_lower:
        return "TSA - Transportation Security Administration"
    if "usss" in email_lower:
        return "USSS - United States Secret Service"
    if "uscis" in email_lower:
        return "USCIS - Citizenship and Immigration Services"
    if "cbp" in email_lower:
        return "CBP - Customs and Border Protection"
    if "cisamedia" in email_lower:
        return "DHS - CISA (Cybersecurity & Infrastructure Security)"
    if "dhsfilmandtv" in email_lower:
        return "DHS - Film & TV Office"
    if "mediainquiry" in email_lower:
        return "DHS - Media Inquiry"
    return "US Department of Homeland Security"


# ─── Parse Text Files ───────────────────────────────────────────────────────

def parse_file(filepath: str) -> list[str]:
    """Parse email addresses from a text file, handling commas, newlines, and spaces."""
    path = Path(filepath)
    if not path.exists():
        print(f"File not found: {filepath}")
        return []
    
    content = path.read_text(encoding="utf-8")
    
    # Split by comma first, then by whitespace, filter valid emails
    parts = re.split(r'[,\s]+', content)
    emails = []
    for p in parts:
        p = p.strip().strip(',').strip()
        if not p:
            continue
        if "@" in p:
            emails.append(p.lower())
    
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for e in emails:
        if e not in seen:
            seen.add(e)
            unique.append(e)
    
    return unique


# ─── Insert into Database ──────────────────────────────────────────────────

def load_db_password() -> str:
    """Read EMAIL_DB_PASSWORD from .env file."""
    if not ENV_PATH.exists():
        print(f"ERROR: .env file not found at {ENV_PATH}")
        sys.exit(1)
    
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line.startswith("EMAIL_DB_PASSWORD="):
                value = line.split("=", 1)[1].strip().strip('"').strip("'")
                if value:
                    return value
    
    print("ERROR: EMAIL_DB_PASSWORD not found in .env")
    sys.exit(1)


def insert_leads(leads: list[dict]):
    """Insert leads into the encrypted database."""
    db_pw = load_db_password()
    db = sqlcipher3.connect(str(DB_PATH))
    hex_key = db_pw.encode().hex()
    db.execute(f'PRAGMA key="x\'{hex_key}\'"')
    db.execute("PRAGMA journal_mode=WAL")
    
    count = 0
    for lead in leads:
        lid = str(uuid.uuid4())
        try:
            db.execute(
                """INSERT INTO leads 
                   (id, company, contact_name, email, tier, type, vertical, notes, source, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (lid, lead["company"], "", lead["email"], lead["tier"],
                 lead["org_type"], lead["country"], lead["notes"],
                 "intel_file_import", "cold")
            )
            count += 1
        except Exception as e:
            print(f"  Error inserting {lead['email']}: {e}")
    
    db.commit()
    db.close()
    return count


# ─── Main ──────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  COUNTER-TERRORISM INITIATIVE — Contact Import")
    print("=" * 60)
    
    # Parse files
    files = [
        "all_defense_intel_law_emails_comma.txt",
        "brazilian_army_emails_final_list.txt",
    ]
    
    all_emails = []
    for f in files:
        emails = parse_file(f)
        all_emails.extend(emails)
        print(f"\n📄 {f}: {len(emails)} email(s) found")
    
    # Deduplicate across files
    seen = set()
    unique_emails = []
    for e in all_emails:
        if e not in seen:
            seen.add(e)
            unique_emails.append(e)
    
    print(f"\n📊 Total unique emails: {len(unique_emails)}")
    
    # Classify each
    classified = {"Military": [], "Intelligence": [], "Defense": [],
                  "Homeland Security": [], "Law Enforcement": [],
                  "Security": [], "Government": [], "Unknown": []}
    
    leads = []
    for email in sorted(unique_emails):
        info = classify_email(email)
        leads.append(info)
        org_type = info["org_type"]
        if org_type not in classified:
            org_type = "Unknown"
        classified[org_type] = classified.get(org_type, [])
        classified[org_type].append(info)
    
    # Print summary
    print(f"\n{'='*60}")
    print("  CLASSIFICATION BREAKDOWN")
    print(f"{'='*60}")
    for cat, items in sorted(classified.items()):
        if items:
            countries = list(set(i["country"] for i in items))
            print(f"\n  {cat} ({len(items)}) — {', '.join(countries)}:")
            for i in items[:5]:
                print(f"    • {i['email']:45s} → {i['company'][:40]}")
            if len(items) > 5:
                print(f"    ... and {len(items) - 5} more")
    
    # Confirm and insert
    print(f"\n{'='*60}")
    total_contacts = len(leads)
    print(f"  Ready to import {total_contacts} contacts into encrypted CRM database.")
    print(f"{'='*60}")
    
    confirm = input("\n  Proceed with import? (y/N): ").strip().lower()
    if confirm != "y":
        print("  ❌ Import cancelled.")
        return
    
    inserted = insert_leads(leads)
    print(f"\n  ✅ Successfully imported {inserted} contacts into leads.db")
    
    # Verify
    db_pw = load_db_password()
    db = sqlcipher3.connect(str(DB_PATH))
    hex_key = db_pw.encode().hex()
    db.execute(f'PRAGMA key="x\'{hex_key}\'"') 
    total = db.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    by_type = db.execute("SELECT type, COUNT(*) FROM leads GROUP BY type ORDER BY COUNT(*) DESC").fetchall()
    by_country = db.execute("SELECT vertical, COUNT(*) FROM leads GROUP BY vertical ORDER BY COUNT(*) DESC").fetchall()
    db.close()
    
    print(f"\n  📊 Database now has {total} total contacts")
    print(f"\n  By Organization Type:")
    for t, c in by_type:
        print(f"    {t}: {c}")
    print(f"\n  By Country:")
    for c, cnt in by_country:
        print(f"    {c}: {cnt}")


if __name__ == "__main__":
    main()
