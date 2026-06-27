#!/usr/bin/env python3
"""
Add researched phone numbers to all Brazilian contacts in the encrypted CRM.
Maps phone numbers by keyword patterns in company names.
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
# More specific rules come first (they take priority)

PHONE_RULES = [
    # === ABIN - Brazilian Intelligence Agency ===
    (["ABIN - Brazilian Intelligence Agency"], "+55 (61) 3445-8000", "Central de Atendimento ABIN"),

    # === Ministry of Defense ===
    (["Brazilian Ministry of Defense"], "+55 (61) 3312-4071", "Ministério da Defesa - ASCOM"),
    (["Brazilian Ministry of Defense"], "+55 (61) 9909-2436", "Ministério da Defesa - Plantão"),
    (["Brazilian Ministry of Justice"], "+55 (61) 2025-3000", "Ministério da Justiça"),

    # === Federal Police ===
    (["Brazilian Federal Police (PF)"], "+55 (61) 2024-8370", "Polícia Federal - Central de Atendimento"),
    (["Federal Police - Departamento"], "+55 (61) 2024-8370", "Polícia Federal - Central de Atendimento"),

    # === PRF ===
    (["Brazilian Federal Highway Police (PRF)"], "191", "PRF - Emergência Nacional"),

    # === Pernambuco ===
    (["SDS-PE"], "0800 081 5001", "SDS-PE - Ouvidoria"),
    (["SDS-PE"], "+55 (81) 99488-3455", "SDS-PE - WhatsApp Ouvidoria"),
    (["Casa Militar de Pernambuco"], "+55 (81) 3181-8000", "Casa Militar de Pernambuco"),
    (["PMPE - Polícia Militar"], "+55 (81) 3181-8000", "PMPE - Quartel do Comando Geral"),
    (["SAD-PE"], "+55 (81) 3181-6000", "SAD-PE - Secretaria de Administração"),

    # === Military Commands (must come before generic Army rules) ===
    (["CMO", "cmo.eb.mil.br", "Comando Militar do Oeste", "Western Military Command"],
     "+55 (67) 3368-4000", "CMO - Comando Militar do Oeste"),
    (["CMA", "cma.eb.mil.br", "Comando Militar da Amazônia", "Amazon Military Command"],
     "+55 (92) 3659-1155", "CMA - Comando Militar da Amazônia"),
    (["CMN", "Comando Militar do Nordeste", "Northeastern Military Command"],
     "+55 (81) 2129-6145", "CMN - Comando Militar do Nordeste"),
    (["CMP", "cmp.eb.mil.br", "Comando Militar do Planalto", "Planalto Military Command"],
     "+55 (61) 2035-2538", "CMP - Comando Militar do Planalto"),
    (["CMS", "cms.eb.mil.br", "Comando Militar do Sul"],
     "+55 (51) 3220-6600", "CMS - Comando Militar do Sul"),
    (["CMSE", "cmse.eb.mil.br", "Comando Militar do Sudeste"],
     "+55 (11) 3278-4100", "CMSE - Comando Militar do Sudeste"),
    (["CML", "cml.eb.mil.br", "Eastern Military Command"],
     "+55 (21) 3876-5400", "CML - Comando Militar do Leste"),
    (["COTER", "coter.eb.mil.br", "Land Operations Command"],
     "+55 (61) 3415-5500", "COTER - Comando de Operações Terrestres"),

    # === Army HQ / General ===
    (["Quartel-General", "Army - Press Office (ccomsex"], "+55 (61) 3415-5711", "QG do Exército - Comunicação Social"),
    (["Army - Press Office", "CComGEx", "CCOMSEX"], "+55 (61) 3415-5711", "QG do Exército - Comunicação Social"),
    (["Ombudsman", "Ouvidoria"], "0800 081 5001", "Ouvidoria do Exército"),
    (["Army Information Center", "CIG"], "+55 (61) 3415-4000", "CIG - Centro de Informação do Exército"),

    # === Army Schools & Academies ===
    (["AMAN", "Agulhas Negras Military Academy"], "+55 (24) 3348-5000", "AMAN - Academia Militar das Agulhas Negras"),
    (["IME", "Military Engineering Institute"], "+55 (21) 2546-7000", "IME - Instituto Militar de Engenharia"),
    (["CCFEx", "Army Cavalry School"], "+55 (21) 2682-4000", "CCFEx - Escola de Cavalaria"),
    (["DECEx", "Army Education Dept", "DEC - Education"], "+55 (21) 2519-5284", "DECEx - Departamento de Educação do Exército"),
    (["ESIE", "Army Intelligence School"], "+55 (61) 3415-5000", "ESIE - Escola de Inteligência do Exército"),
    (["ECEME", "Army Command School"], "+55 (21) 3876-5200", "ECEME - Escola de Comando do Estado-Maior"),

    # === Special Operations ===
    (["COpEsp", "CIOPESP", "Special Operations"], "+55 (62) 3239-4534", "COpEsp - Comando de Operações Especiais"),
    (["Army Psychological Operations"], "+55 (62) 3239-4500", "COpEsp - Operações Psicológicas"),
    (["Brigada Paraquedista", "Paraquedista", "Precursor Parachute"], "+55 (21) 2457-1000", "Brigada de Infantaria Paraquedista"),

    # === Army Hospitals ===
    (["HCE", "Central Army Hospital"], "+55 (21) 2546-4900", "HCE - Hospital Central do Exército"),
    (["HMAB", "Brasília Army Hospital"], "+55 (61) 3415-4100", "HMAB - Hospital Militar de Área de Brasília"),

    # === Cyber / Tech ===
    (["ENADCIBER", "National Cyber Defense School"], "+55 (61) 3415-3800", "ENADCIBER - Escola Nacional de Defesa Cibernética"),
    (["CTEx", "Army Technology Center"], "+55 (21) 3824-8200", "CTEx - Centro Tecnológico do Exército"),
    (["DCT", "Science & Technology"], "+55 (61) 3415-5500", "DCT - Departamento de Ciência e Tecnologia"),
    (["IME", "Military Engineering"], "+55 (21) 2546-7000", "IME - Instituto Militar de Engenharia"),

    # === Logistic / Support ===
    (["COLOG", "Logistics Command"], "+55 (61) 3415-4800", "COLOG - Comando de Logística"),
    (["CPEx", "Army Personnel Center"], "+55 (61) 3415-4900", "CPEx - Centro de Pessoal do Exército"),
    (["DGP", "General Personnel Directorate"], "+55 (61) 3415-4600", "DGP - Diretoria de Pessoal"),
    (["DSAU", "Army Health Directorate"], "+55 (61) 3415-4400", "DSAU - Diretoria de Saúde do Exército"),
    (["DCMun", "Army Munitions Directorate"], "+55 (21) 2546-4800", "DCMun - Diretoria de Fabricação de Munição"),
    (["DEPA", "Army Property Directorate"], "+55 (61) 3415-4700", "DEPA - Diretoria de Patrimônio do Exército"),
    (["BDOMPSA", "BDomPSA", "Army Police Battalion"], "+55 (11) 3278-4200", "BPE - Batalhão de Polícia do Exército"),
    (["BAPR", "Army Police Battalion (BAPR)"], "+55 (11) 3278-4200", "BAPR - Batalhão de Polícia do Exército"),

    # === Military Regions (RM) ===
    (["2nd Military Region (2ª RM)"], "+55 (11) 3278-4100", "2ª RM - Comando Militar do Sudeste"),
    (["7th Military Region (7ª RM)"], "+55 (81) 2129-6000", "7ª RM - Comando Militar do Nordeste"),
    (["CRO 2", "2nd Military Region Communications"], "+55 (11) 3278-4300", "CRO/2 - Centro Regional de Comunicações"),
    (["CRO 7", "7th Regional Communications"], "+55 (81) 2129-6000", "CRO/7 - Centro Regional de Comunicações"),
    (["CRO1", "Regional Communications Center"], "+55 (61) 3415-5000", "CRO - Centro Regional de Comunicações"),

    # === Military College ===
    (["CMRJ", "Military College of Rio de Janeiro"], "+55 (21) 2457-3000", "CMRJ - Colégio Militar do Rio de Janeiro"),

    # === Army Geography / Mapping ===
    (["DSG", "Geographic Service Directorate"], "+55 (21) 2682-4200", "DSG - Diretoria de Serviço Geográfico"),
    (["CGEO", "Geographic Company"], "+55 (21) 2682-4200", "CGEO - Companhia Geográfica"),

    # === Army Finance ===
    (["IEFEx", "Army Finance Institute"], "+55 (61) 3415-4300", "IEFEx - Instituto de Finanças do Exército"),
    (["IPCFEx", "Army Pension Institute"], "+55 (61) 3415-4500", "IPCFEx - Instituto de Previdência do Exército"),

    # === Army Band (Music) ===
    (["BMNTSUPAVEX", "Banda de Música"], "+55 (61) 3415-5711", "QG do Exército - Banda de Música"),

    # === Army Individual Contacts / Shooting Ranges ===
    # Shooting ranges (TG) - general number for the TG system
    (["Shooting Range", "TG ", "TG0", "tg ", "tg0"], "+55 (61) 3415-4600",
     "TG - Tiro de Guerra (ramal QG)"),
    (["Individual Contact"], "+55 (61) 3415-4600", "QG do Exército - Ramal Geral"),
    (["Military Attaché"], "+55 (61) 3415-4600", "QG do Exército - Adidância Militar"),

    # === Generic Army units - fallback for everything else ===
    (["Brazilian Army"], "+55 (61) 3415-4600", "QG do Exército - Ramal Geral"),
    (["Brazilian Military Ordinariate"], "+55 (61) 3323-4100", "Ordinariado Militar do Brasil"),
]


def get_phone_for_contact(company: str) -> list:
    """
    Returns list of (phone, description) tuples for a contact,
    matched by keyword in company name.
    """
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

    # Get all Brazilian contacts
    rows = db.execute(
        """SELECT id, company, phone FROM leads
           WHERE vertical = 'Brazil' AND (phone IS NULL OR phone = '')"""
    ).fetchall()

    print(f"📞 Adding phone numbers to Brazilian contacts...")
    print(f"   Brazilian contacts needing phones: {len(rows)}")
    print()

    updated = 0
    skipped = 0
    multi_phone = 0
    no_match = 0

    for r in rows:
        lid = r["id"]
        company = r["company"]
        phones = get_phone_for_contact(company)

        if not phones:
            print(f"  ⚠️  NO MATCH: {company}")
            no_match += 1
            continue

        # Join multiple phones with | separator
        phone_str = " | ".join(f"{p} ({d})" for p, d in phones)

        db.execute("UPDATE leads SET phone = ? WHERE id = ?", (phone_str, lid))
        if len(phones) > 1:
            print(f"  ✅ {company}")
            print(f"     Phones: {phone_str}")
            multi_phone += 1
        else:
            print(f"  ✅ {company}")
            print(f"     Phone: {phone_str}")
        updated += 1

    db.commit()

    # Also update any remaining Brazilian contacts that might have a partial phone
    remaining = db.execute(
        """SELECT COUNT(*) FROM leads
           WHERE vertical = 'Brazil' AND (phone IS NULL OR phone = '')"""
    ).fetchone()[0]

    total_brazil = db.execute(
        "SELECT COUNT(*) FROM leads WHERE vertical = 'Brazil'"
    ).fetchone()[0]

    with_phone = db.execute(
        """SELECT COUNT(*) FROM leads
           WHERE vertical = 'Brazil' AND phone IS NOT NULL AND phone != ''"""
    ).fetchone()[0]

    print(f"\n{'='*55}")
    print(f"  UPDATE COMPLETE")
    print(f"{'='*55}")
    print(f"  Updated:              {updated}")
    print(f"  With multiple phones: {multi_phone}")
    print(f"  No match found:       {no_match}")
    print(f"  Still missing:        {remaining}")
    print(f"  Total Brazilian:      {total_brazil}")
    print(f"  With phone now:       {with_phone}")
    print()

    # Show any unmatched
    if no_match > 0:
        print("Unmatched contacts:")
        for r in rows:
            if not get_phone_for_contact(r["company"]):
                print(f"  - {r['company']}")

    db.close()


if __name__ == "__main__":
    main()
