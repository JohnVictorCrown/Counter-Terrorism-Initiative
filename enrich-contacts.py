#!/usr/bin/env python3
"""
enrich-contacts.py — Enrich all CRM contacts with:
  - Proper reclassification of "Unknown" type contacts
  - Contact names extracted from email addresses
  - Website URLs for each organization
  - Detailed notes about each contact/organization
  - Better company names with unit details

Usage:
    python enrich-contacts.py
"""

import sqlcipher3
import re
import sys
from pathlib import Path

DB_PATH = Path("leads.db")
ENV_PATH = Path(".env")

# ─── Database Connection ────────────────────────────────────────────────────

def load_db_password() -> str:
    if not ENV_PATH.exists():
        print(f"ERROR: .env file not found at {ENV_PATH}")
        sys.exit(1)
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line.startswith("EMAIL_DB_PASSWORD="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    print("ERROR: EMAIL_DB_PASSWORD not found in .env")
    sys.exit(1)


def get_db():
    db_pw = load_db_password()
    db = sqlcipher3.connect(str(DB_PATH))
    hex_key = db_pw.encode().hex()
    db.execute(f'PRAGMA key="x\'{hex_key}\'"')
    db.execute("PRAGMA journal_mode=WAL")
    db.row_factory = sqlcipher3.Row
    return db


# ─── Contact Name Extraction ────────────────────────────────────────────────

def extract_contact_name(email: str) -> str:
    """Extract a person's name from an email address if possible."""
    local = email.split("@")[0].lower() if "@" in email else ""
    
    # Remove common military/role prefixes
    # Remove common military/role prefixes
    clean = re.sub(
        r'^(comsoc|rp|imprensa|comsocial|comsoctg|s5|protocolo|ouvidoria|'
        r'aux|assessor|adj|adjunto|ch|cmt|dir|dom|dpe|dgo|'
        r'secretaria|atendimento|contato|faleconosco|relacoespublicas|'
        r'divcomsoc|esimex|prodivcml|r\.institucional|'
        r'comsocdsm|comsocopsico|comsocpomn|comsoccro|'
        r'batalhao|comando|comandos|'
        r'tg0\d{2,}|tg\d{2,}|tirodeguerra0\d{2,}|'
        r'^\d+[a-z]+)', '', local)
    
    # Remove trailing numbers and common suffixes
    clean = re.sub(r'[\d_\.-]+$', '', clean)
    clean = re.sub(r'@gmail|@yahoo|@eb\.mil\.br|@hotmail|@outlook', '', clean)
    clean = clean.strip('._-')
    
    if not clean or len(clean) < 3:
        return ""
    
    # Try to convert to a proper name
    # Split by dots, hyphens, underscores
    parts = re.split(r'[\._\-]+', clean)
    parts = [p for p in parts if len(p) > 1 and not p.isdigit()]
    
    if not parts or len(parts) < 2:
        # Single part might be a first name or surname
        if len(parts) == 1 and len(parts[0]) > 2:
            return parts[0].capitalize()
        return ""
    
    # Capitalize each part
    name_parts = []
    for p in parts:
        if p.lower() in ('da', 'de', 'do', 'das', 'dos', 'e'):
            name_parts.append(p.lower())
        else:
            name_parts.append(p.capitalize())
    
    return " ".join(name_parts)


# ─── Organization Websites ──────────────────────────────────────────────────

ORG_WEBSITES = {
    # Brazilian Intelligence
    "abin.gov.br": "https://www.gov.br/abin",
    # Brazilian Defense
    "defesa.gov.br": "https://www.gov.br/defesa",
    "eb.mil.br": "https://www.eb.mil.br",
    "ime.eb.br": "https://www.ime.eb.br",
    # Brazilian Federal Police
    "pf.gov.br": "https://www.gov.br/pf",
    "prf.gov.br": "https://www.gov.br/prf",
    # Brazilian State Security
    "sds.pe.gov.br": "https://www.sds.pe.gov.br",
    "pm.pe.gov.br": "https://www.pm.pe.gov.br",
    "sad.pe.gov.br": "https://www.sad.pe.gov.br",
    # Brazilian Justice
    "mj.gov.br": "https://www.gov.br/mj",
    # US Intelligence
    "dni.gov": "https://www.dni.gov",
    "odni.gov": "https://www.odni.gov",
    "nga.mil": "https://www.nga.mil",
    "nsa.gov": "https://www.nsa.gov",
    "dia.mil": "https://www.dia.mil",
    # US Defense
    "defense.gov": "https://www.defense.gov",
    "dodig.mil": "https://www.dodig.mil",
    "af.mil": "https://www.af.mil",
    "army.mil": "https://www.army.mil",
    "navy.mil": "https://www.navy.mil",
    "uscg.mil": "https://www.uscg.mil",
    "mail.mil": "https://www.mail.mil",
    "nmic.navy.mil": "https://www.nmic.navy.mil",
    # US Homeland Security
    "dhs.gov": "https://www.dhs.gov",
    "ice.dhs.gov": "https://www.ice.gov",
    "fema.dhs.gov": "https://www.fema.gov",
    "tsa.dhs.gov": "https://www.tsa.gov",
    "usss.dhs.gov": "https://www.secretservice.gov",
    "uscis.dhs.gov": "https://www.uscis.gov",
    "cbp.dhs.gov": "https://www.cbp.gov",
    "hq.dhs.gov": "https://www.dhs.gov",
    # US Justice
    "usdoj.gov": "https://www.justice.gov",
    # Israel
    "gov.il": "https://www.gov.il",
    "mail.gov.il": "https://www.gov.il",
    # Brazilian Military Ordinariate
    "ordinariadomilitar.org.br": "https://ordinariadomilitar.org.br",
}


def get_website(email: str, domain: str, org_type: str) -> str:
    """Get the appropriate website URL for an organization."""
    # Direct lookup by domain
    if domain in ORG_WEBSITES:
        return ORG_WEBSITES[domain]
    
    # Check partial matches
    for key, url in ORG_WEBSITES.items():
        if key in domain or domain in key:
            return url
    
    # Fallback by org type
    if "eb.mil.br" in domain:
        return "https://www.eb.mil.br"
    if "gov.br" in domain:
        return f"https://www.{domain}"
    if ".mil" in domain:
        return f"https://www.{domain}"
    if ".gov" in domain:
        return f"https://www.{domain}"
    if org_type == "Military" and ".mil" not in domain:
        return "https://www.eb.mil.br"
    if org_type == "Intelligence":
        return "https://www.gov.br/abin" if "br" in domain else "https://www.dni.gov"
    return ""


# ─── Classification of Unknown Contacts ────────────────────────────────────

def classify_gmail_contact(email: str, local: str) -> dict:
    """Classify a Gmail/Yahoo contact based on the email prefix patterns."""
    result = {
        "type": "Military",
        "vertical": "Brazil",
        "tier": "3",
        "company": "",
        "notes": "",
        "website": "https://www.eb.mil.br",
    }
    
    # Social Communication (Comunicação Social)
    if local.startswith("comsoc"):
        if "badmgujp" in local:
            result["company"] = "Brazilian Army - BAdMGuJP (Administrative Battalion - Juiz de Fora)"
            result["notes"] = "Brazilian Army Administrative Battalion of Juiz de Fora - Social Communication"
        elif "lqfex" in local:
            result["company"] = "Brazilian Army - LQFEx (Physical Chemistry Laboratory)"
            result["notes"] = "Brazilian Army Physical Chemistry Laboratory - Social Communication"
        elif "11cgcfex" in local:
            result["company"] = "Brazilian Army - 11th Group of Campaign Artillery"
            result["notes"] = "Brazilian Army 11th Campaign Artillery Group - Social Communication"
        elif "15rcmec" in local:
            result["company"] = "Brazilian Army - 15th Mechanized Cavalry Regiment"
            result["notes"] = "Brazilian Army 15th Mechanized Cavalry Regiment - Social Communication"
        elif "2de" in local:
            result["company"] = "Brazilian Army - 2nd Division (2ª DE)"
            result["notes"] = "Brazilian Army 2nd Division - Social Communication"
        elif "7cgcfex" in local:
            result["company"] = "Brazilian Army - 7th Group of Campaign Artillery"
            result["notes"] = "Brazilian Army 7th Campaign Artillery Group - Social Communication"
        elif "cro7" in local:
            result["company"] = "Brazilian Army - CRO 7 (7th Regional Communications Center)"
            result["notes"] = "Brazilian Army 7th Regional Communications Center"
        elif "dsup" in local:
            result["company"] = "Brazilian Army - DSup (Support Division)"
            result["notes"] = "Brazilian Army Support Division - Social Communication"
        elif "hmab" in local or "comsocial.hmab" in local:
            result["company"] = "Brazilian Army - HMAB (Brasília Army Hospital)"
            result["tier"] = "2"
            result["notes"] = "Brazilian Army Hospital of Brasília - Social Communication"
        elif "opsico" in local:
            result["company"] = "Brazilian Army - Army Psychological Operations"
            result["tier"] = "1"
            result["notes"] = "Brazilian Army Psychological Operations (PsyOps) - Social Communication"
        elif "pomn" in local:
            result["company"] = "Brazilian Army - POMN (Northern Military Police)"
            result["notes"] = "Brazilian Army Northern Military Police - Social Communication"
        elif "rp4bil" in local:
            result["company"] = "Brazilian Army - 4th Logistics Battalion"
            result["notes"] = "Brazilian Army 4th Logistics Battalion - Social Communication"
        elif "dec" in local:
            result["company"] = "Brazilian Army - DEC (Education Command)"
            result["notes"] = "Brazilian Army Education Command - Social Communication"
        elif "dsm" in local:
            result["company"] = "Brazilian Army - DSM (Health Division)"
            result["notes"] = "Brazilian Army Health Division - Social Communication"
        elif "gmail" in local:
            result["company"] = "Brazilian Army - Social Communication (Gmail account)"
            result["notes"] = "Brazilian Army Social Communication personnel"
        else:
            result["company"] = "Brazilian Army - Social Communication Unit"
            result["notes"] = "Brazilian Army Social Communication (Comunicação Social)"
    
    # Public Relations (Relações Públicas)
    elif local.startswith("rp") or "rp." in local or local.startswith("relacoespublicas"):
        rp_result = classify_rp_contact(local)
        result["company"] = rp_result["company"]
        result["notes"] = rp_result["notes"]
        if rp_result.get("tier"):
            result["tier"] = rp_result["tier"]
    
    # Shooting Range Units (Tiros de Guerra)
    elif local.startswith("tg") or local.startswith("tirodeguerra"):
        tg_result = classify_tg_contact(local)
        result["company"] = tg_result["company"]
        result["notes"] = tg_result["notes"]
    
    # Press / Media contacts
    elif "imprensa" in local:
        if "casamilitarpe" in local:
            result["company"] = "Casa Militar de Pernambuco"
            result["vertical"] = "Brazil"
            result["tier"] = "2"
            result["notes"] = "Pernambuco State Military House - Press Office"
            result["website"] = "https://www.casamilitar.pe.gov.br"
        else:
            result["company"] = "Brazilian Army - Press Office"
            result["notes"] = "Brazilian Army Press / Media Relations"
            result["tier"] = "2"
    
    # Individual military personnel with named email accounts
    elif "esimex" in local:
        result["company"] = "Brazilian Army - ESIMEx (Army Instruction School)"
        result["notes"] = "Brazilian Army Instruction School - Social Communication Section"
        result["tier"] = "2"
    
    elif "divcomsocdgp" in local:
        result["company"] = "Brazilian Army - DGP (General Personnel Directorate)"
        result["notes"] = "Brazilian Army General Personnel Directorate - Social Communication Division"
        result["tier"] = "2"
    
    elif "faleconosco.cmrj" in local:
        result["company"] = "Brazilian Army - CMRJ (Military College of Rio de Janeiro)"
        result["notes"] = "Brazilian Army Military College of Rio de Janeiro - Contact"
        result["tier"] = "3"
    
    elif "dabst.dir" in local:
        result["company"] = "Brazilian Army - DABST (Directory)"
        result["notes"] = "Brazilian Army Administrative Directorate - Director's Office"
        result["tier"] = "3"
    
    elif "ocs16blog" in local:
        result["company"] = "Brazilian Army - 16th Communications Company Blog"
        result["notes"] = "Brazilian Army 16th Communications Company - Blog/Social Media"
        result["tier"] = "3"
    
    elif "prodivcml" in local:
        result["company"] = "Brazilian Army - CML (Eastern Military Command) - Public Relations"
        result["notes"] = "Brazilian Army Eastern Military Command - Public Relations Division"
        result["tier"] = "2"
    
    elif "r.institucionalcml" in local:
        result["company"] = "Brazilian Army - CML (Eastern Military Command) - Institutional Relations"
        result["notes"] = "Brazilian Army Eastern Military Command - Institutional Relations"
        result["tier"] = "2"
    
    elif "dec.comsoc" in local:
        result["company"] = "Brazilian Army - DEC (Education Command) - Social Communication"
        result["notes"] = "Brazilian Army Education Command - Social Communication"
        result["tier"] = "2"
    
    elif "s5.ciaprecpqdt" in local:
        result["company"] = "Brazilian Army - S5/CIAPRECPQDT (Precursor Parachute Company)"
        result["notes"] = "Brazilian Army Precursor Parachute Company - S5 Section"
        result["tier"] = "2"
    
    # Named individuals who are clearly military
    elif any(name in local for name in ["assuires", "maciodamasceno", "batalhaobrasilia"]):
        if "assuires" in local:
            result["company"] = "Brazilian Army - Individual Contact (Assuires Filho)"
            result["notes"] = "Brazilian Army personnel contact"
        elif "batalhaobrasilia" in local:
            result["company"] = "Brazilian Army - Batalhão Brasília (Brasília Battalion)"
            result["tier"] = "2"
            result["notes"] = "Brazilian Army Brasília Battalion"
        elif "maciodamasceno" in local:
            result["company"] = "Brazilian Army - Individual Contact"
            result["notes"] = "Brazilian Army personnel contact"
        else:
            result["company"] = "Brazilian Army - Individual Contact"
            result["notes"] = "Brazilian Army personnel"
    
    # Specific named military units
    elif "biaaaaepqdt21" in local:
        result["company"] = "Brazilian Army - 21st Airborne Artillery Group"
        result["tier"] = "2"
        result["notes"] = "Brazilian Army 21st Airborne Artillery Group"
    
    elif "bmntsupaaae1" in local:
        result["company"] = "Brazilian Army - 1st Air Defense Artillery Group Support"
        result["tier"] = "2"
        result["notes"] = "Brazilian Army 1st Air Defense Artillery Group Support"
    
    elif "cajati.tg" in local:
        result["company"] = "Brazilian Army - TG Cajati (Cajati Shooting Range)"
        result["notes"] = "Brazilian Army Shooting Range Unit - Cajati, SP"
    
    elif "5gpte.comsoc" in local:
        result["company"] = "Brazilian Army - 5th Engineer Group"
        result["tier"] = "2"
        result["notes"] = "Brazilian Army 5th Engineer Group - Social Communication"
    
    elif "11bpevilamilitar" in local:
        result["company"] = "Brazilian Army - 11th BPE (Special Police Battalion) - Military Village"
        result["tier"] = "2"
        result["notes"] = "Brazilian Army 11th Special Police Battalion - Military Village"
    
    elif "7divisaoexercito" in local:
        result["company"] = "Brazilian Army - 7th Division (7ª DE)"
        result["tier"] = "2"
        result["notes"] = "Brazilian Army 7th Infantry Division"
    
    else:
        # Generic military gmail contact
        result["company"] = "Brazilian Army - Individual Contact"
        result["notes"] = "Brazilian Army personnel (Gmail contact)"
    
    return result


def classify_rp_contact(local: str) -> dict:
    """Classify Public Relations (RP) contacts."""
    result = {"company": "", "notes": "", "tier": "3"}
    
    if "2ciacoml" in local:
        result["company"] = "Brazilian Army - 2nd Communications Company / CML"
        result["notes"] = "Brazilian Army 2nd Communications Company, Eastern Military Command - Public Relations"
        result["tier"] = "2"
    elif "bdompsa" in local:
        result["company"] = "Brazilian Army - BDomPSA (Army Police Battalion)"
        result["notes"] = "Brazilian Army Police Battalion - Public Relations"
        result["tier"] = "2"
    elif "ccomgex" in local:
        result["company"] = "Brazilian Army - CComGEx (Army General Communications Command)"
        result["notes"] = "Brazilian Army General Communications Command - Public Relations"
        result["tier"] = "2"
    elif "10esquadrao" in local:
        result["company"] = "Brazilian Army - 10th Squadron"
        result["notes"] = "Brazilian Army 10th Squadron - Public Relations"
        result["tier"] = "3"
    elif "111ciaapmb" in local:
        result["company"] = "Brazilian Army - 111th Cia APMB (Military Police Company)"
        result["notes"] = "Brazilian Army 111th Military Police Company - Public Relations"
        result["tier"] = "2"
    elif "11bpe" in local:
        result["company"] = "Brazilian Army - 11th BPE (Special Police Battalion)"
        result["notes"] = "Brazilian Army 11th Special Police Battalion - Public Relations"
        result["tier"] = "2"
    elif "2cia" in local:
        result["company"] = "Brazilian Army - 2nd Company"
        result["notes"] = "Brazilian Army 2nd Company - Public Relations"
        result["tier"] = "3"
    elif "2gacl" in local:
        result["company"] = "Brazilian Army - 2nd GACL (Light Artillery Group)"
        result["notes"] = "Brazilian Army 2nd Light Artillery Group - Public Relations"
        result["tier"] = "2"
    elif "3esqdcmec" in local:
        result["company"] = "Brazilian Army - 3rd Mechanized Cavalry Squadron"
        result["notes"] = "Brazilian Army 3rd Mechanized Cavalry Squadron - Public Relations"
        result["tier"] = "2"
    elif "5cgeo" in local:
        result["company"] = "Brazilian Army - 5th Geographic Company"
        result["notes"] = "Brazilian Army 5th Geographic Company - Public Relations"
        result["tier"] = "3"
    elif "ccfex" in local:
        result["company"] = "Brazilian Army - CCFEx (Army Cavalry School)"
        result["notes"] = "Brazilian Army Cavalry School - Public Relations"
        result["tier"] = "2"
    elif "bescom" in local:
        result["company"] = "Brazilian Army - BEsCom (Army Communications Battalion)"
        result["notes"] = "Brazilian Army Communications Battalion - Public Relations"
        result["tier"] = "2"
    elif "cro2rm" in local:
        result["company"] = "Brazilian Army - CRO 2 (2nd Military Region Communications Center)"
        result["notes"] = "Brazilian Army 2nd Military Region Communications Center - Public Relations"
        result["tier"] = "2"
    else:
        result["company"] = "Brazilian Army - Public Relations (RP)"
        result["notes"] = "Brazilian Army Public Relations contact"
    
    return result


def classify_tg_contact(local: str) -> dict:
    """Classify Tiro de Guerra (Shooting Range) contacts."""
    result = {"company": "", "notes": ""}
    locations = {
        "itabapoana": "Itabapoana, RJ",
        "itaperuna": "Itaperuna, RJ",
        "porciuncula": "Porciúncula, RJ",
        "sapadua": "Santo Antônio de Pádua, RJ",
        "sjbv": "São João da Barra, RJ",
    }
    
    for key, loc in locations.items():
        if key in local:
            result["company"] = f"Brazilian Army - TG {loc.split(',')[0]} (Shooting Range)"
            result["notes"] = f"Brazilian Army Tiro de Guerra - {loc}"
            return result
    
    result["company"] = "Brazilian Army - TG (Tiro de Guerra - Shooting Range Unit)"
    result["notes"] = "Brazilian Army Shooting Range Unit"
    return result


# ─── Enrichment Pipeline ────────────────────────────────────────────────────

def enrich_contact(row: dict) -> dict:
    """Build enrichment updates for a single contact."""
    email = row["email"]
    local = email.split("@")[0].lower() if "@" in email else ""
    domain = email.split("@")[-1].lower() if "@" in email else email.lower()
    org_type = row["type"]
    vertical = row["vertical"]
    tier = row["tier"]
    company = row["company"]
    notes = row.get("notes") or ""
    contact_name = row.get("contact_name") or ""
    website = row.get("website") or ""
    
    updates = {}
    
    # ── Reclassify Unknown contacts ──
    if org_type == "Unknown":
        if domain in ("gmail.com", "yahoo.com", "yahoo.com.br", "hotmail.com", "outlook.com", "outlook.com.br"):
            info = classify_gmail_contact(email, local)
            updates["type"] = info["type"]
            updates["vertical"] = info["vertical"]
            updates["tier"] = info["tier"]
            updates["company"] = info["company"]
            updates["notes"] = info["notes"]
            if info.get("website"):
                updates["website"] = info["website"]
        elif domain == "eb.mil.br" or domain == "ime.eb.br":
            updates["type"] = "Military"
            updates["vertical"] = "Brazil"
            updates["tier"] = "2"
            updates["company"] = classify_eb_mil_br(email, local, domain)
            updates["notes"] = f"Brazilian Army - {updates.get('company', domain)}"
            updates["website"] = "https://www.eb.mil.br"
        elif "ig.com.br" in domain:
            updates["type"] = "Military"
            updates["vertical"] = "Brazil"
            updates["tier"] = "3"
            updates["company"] = "Brazilian Army - Individual Contact"
            updates["notes"] = "Brazilian Army personnel (personal email)"
            updates["website"] = "https://www.eb.mil.br"
    
    # ── Add contact names from email ──
    if not contact_name and org_type != "Unknown":
        name = extract_contact_name(email)
        if name:
            updates["contact_name"] = name
    
    # ── Add website if missing ──
    if not website and org_type != "Unknown":
        url = get_website(email, domain, org_type)
        if url:
            updates["website"] = url
    
    # ── Enrich company names for Brazilian Military ──
    if org_type != "Unknown" and not company:
        if "eb.mil.br" in domain:
            updates["company"] = f"Brazilian Army - Unit ({domain})"
            updates["website"] = "https://www.eb.mil.br"
    
    # ── Add detailed notes if missing ──
    if not notes and org_type != "Unknown":
        if org_type == "Intelligence":
            if "abin" in domain:
                updates["notes"] = "ABIN - Brazilian Intelligence Agency (Agência Brasileira de Inteligência)"
            elif "dni" in domain:
                updates["notes"] = "ODNI - US Office of the Director of National Intelligence"
            elif "nga" in domain:
                updates["notes"] = "NGA - US National Geospatial-Intelligence Agency"
            elif "nsa" in domain:
                updates["notes"] = "NSA - US National Security Agency"
            elif "dia" in domain:
                updates["notes"] = "DIA - US Defense Intelligence Agency"
            elif "gov.il" in domain:
                updates["notes"] = "Israeli Government/Intelligence - Mossad"
        elif org_type == "Homeland Security":
            updates["notes"] = f"US Department of Homeland Security - {domain}"
        elif org_type == "Law Enforcement":
            if "pf.gov.br" in domain:
                updates["notes"] = "Brazilian Federal Police (Polícia Federal)"
            elif "prf.gov.br" in domain:
                updates["notes"] = "Brazilian Federal Highway Police (Polícia Rodoviária Federal)"
            elif "usdoj" in domain:
                updates["notes"] = "US Department of Justice"
        elif org_type == "Defense":
            if "defesa.gov.br" in domain:
                updates["notes"] = "Brazilian Ministry of Defense (Ministério da Defesa)"
            elif "defense.gov" in domain:
                updates["notes"] = "US Department of Defense"
            elif "dodig" in domain:
                updates["notes"] = "US Department of Defense - Office of Inspector General"
        elif org_type == "Security":
            if "sds.pe.gov.br" in domain:
                updates["notes"] = "Pernambuco State Public Security Secretariat"
            elif "pm.pe.gov.br" in domain:
                updates["notes"] = "Pernambuco State Military Police"
        elif org_type == "Government":
            if "mj.gov.br" in domain:
                updates["notes"] = "Brazilian Ministry of Justice and Public Security"
        elif org_type == "Military":
            if "eb.mil.br" in domain:
                if not updates.get("company"):
                    updates["company"] = f"Brazilian Army - Unit ({domain})"
                if not updates.get("notes"):
                    updates["notes"] = f"Brazilian Army - {domain}"
            elif ".mil" in domain or ".af.mil" in domain:
                if not updates.get("notes"):
                    updates["notes"] = f"US Military - {domain}"
    
    return updates


def classify_eb_mil_br(email: str, local: str, domain: str) -> str:
    """Classify eb.mil.br contacts that ended up as Unknown."""
    email_lower = email.lower()
    if "ciopesp" in email_lower:
        return "Brazilian Army - CIOPESP (Special Operations Center)"
    elif "ouvidoria" in email_lower:
        return "Brazilian Army - Ombudsman Office (Ouvidoria)"
    elif "lisboa" in email_lower or "jesus" in email_lower:
        return "Brazilian Army - Individual Contact (Lisboa Jesus)"
    elif "sales" in email_lower or "cristian" in email_lower:
        return "Brazilian Army - Individual Contact (Cristian Sales)"
    elif "scoms" in email_lower and "ime" in domain:
        return "Brazilian Army - IME (Military Engineering Institute)"
    return f"Brazilian Army - Unit ({domain})"


# ─── Main Enrichment Runner ────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  COUNTER-TERRORISM INITIATIVE — Contact Enrichment")
    print("=" * 60)
    
    db = get_db()
    
    # Get all contacts
    rows = db.execute("SELECT * FROM leads").fetchall()
    print(f"\n📊 Total contacts to enrich: {len(rows)}")
    
    stats = {
        "reclassified": 0,
        "names_added": 0,
        "websites_added": 0,
        "notes_added": 0,
        "unknown_fixed": 0,
    }
    
    for row in rows:
        lead = dict(row)
        updates = enrich_contact(lead)
        
        if not updates:
            continue
        
        # Build SET clause
        set_parts = []
        params = []
        for field, value in updates.items():
            if value and value != lead.get(field, ""):
                set_parts.append(f"{field} = ?")
                params.append(value)
                
                if field == "type" and lead.get("type") == "Unknown":
                    stats["unknown_fixed"] += 1
                elif field == "contact_name":
                    stats["names_added"] += 1
                elif field == "website":
                    stats["websites_added"] += 1
                elif field == "notes" and not lead.get("notes"):
                    stats["notes_added"] += 1
                
                if field == "type":
                    stats["reclassified"] += 1
        
        if set_parts:
            set_parts.append("updated_at = datetime('now')")
            params.append(lead["id"])
            db.execute(
                f"UPDATE leads SET {', '.join(set_parts)} WHERE id = ?",
                params
            )
    
    db.commit()
    db.close()
    
    # Print summary
    print(f"\n{'='*60}")
    print("  ENRICHMENT RESULTS")
    print(f"{'='*60}")
    print(f"  Unknown contacts reclassified:  {stats['unknown_fixed']}")
    print(f"  Contact names extracted:        {stats['names_added']}")
    print(f"  Website URLs added:             {stats['websites_added']}")
    print(f"  Detailed notes added:           {stats['notes_added']}")
    print(f"  Total fields updated:           {stats['reclassified']}")
    
    # Verify
    db = get_db()
    remaining_unknown = db.execute("SELECT COUNT(*) FROM leads WHERE type = 'Unknown'").fetchone()[0]
    total = db.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    
    print(f"\n  📊 Database now has {total} contacts")
    print(f"  Remaining Unknown: {remaining_unknown}")
    
    if remaining_unknown > 0:
        print("\n  Remaining Unknown contacts:")
        rows = db.execute("SELECT email, company FROM leads WHERE type = 'Unknown'").fetchall()
        for r in rows:
            print(f"    • {r[0]:45s} {r[1]}")
    
    # Show enriched samples
    print(f"\n{'='*60}")
    print("  SAMPLES OF ENRICHED CONTACTS")
    print(f"{'='*60}")
    
    for label, query in [
        ("Intelligence", "SELECT email, company, contact_name, website, notes FROM leads WHERE type = 'Intelligence'"),
        ("Brazilian Military (sampled)", "SELECT email, company, contact_name FROM leads WHERE type = 'Military' AND vertical = 'Brazil' AND contact_name != '' LIMIT 5"),
        ("Homeland Security", "SELECT email, company, website FROM leads WHERE type = 'Homeland Security'"),
        ("Brazilian Police", "SELECT email, company, website FROM leads WHERE type = 'Law Enforcement'"),
    ]:
        rows = db.execute(query).fetchall()
        if rows:
            print(f"\n  --- {label} ---")
            for r in rows:
                vals = [str(x) for x in r]
                print(f"    {' | '.join(vals)}")
    
    db.close()
    
    print(f"\n{'='*60}")
    print("  ✅ Enrichment complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
