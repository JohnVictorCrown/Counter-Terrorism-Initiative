#!/usr/bin/env python3
"""
Add missing emails, social media handles, and enriched notes to all
Pernambuco police contacts in the encrypted CRM.
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

# ─── Updates per contact ────────────────────────────────────────────────────
# Format: (company_search_string, email, social_media_notes_append)

UPDATES = [
    # === PF/PE ===
    (
        "PF/PE - Polícia Federal em Pernambuco (Superintendência Regional)",
        "gabin.srpe@pf.gov.br",
        "Social: Instagram @pfpernambuco, Twitter/X @policiafederal, Facebook @policiafederal, YouTube @policiafederal"
    ),
    (
        "PF/PE - Delegacia de Imigração (Polícia Federal PE)",
        "",
        "Social: Instagram @pfpernambuco, Twitter/X @policiafederal, Facebook @policiafederal"
    ),

    # === PCPE ===
    (
        "PCPE - Polícia Civil de Pernambuco (Chefia)",
        "",
        "Social: Instagram @policiacivildepernambuco, Facebook @pc.pernambuco. Portal Ouvidoria: ouvidoria.pe.gov.br"
    ),
    (
        "PCPE - DHPP (Departamento de Homicídios e Proteção à Pessoa - PE)",
        "",
        "Social: Instagram @policiacivildepernambuco. Denúncias: 197 ou https://197denuncias.pe.gov.br"
    ),
    (
        "PCPE - DEAM (Delegacia Especializada de Atendimento à Mulher - Recife)",
        "",
        "Social: Instagram @policiacivildepernambuco. Denúncia nacional: 180. Portal 197 Mulher: http://197mulher.pe.gov.br"
    ),
    (
        "PCPE - DECON (Delegacia do Consumidor - PE)",
        "",
        "Social: Instagram @policiacivildepernambuco. Denúncias: 197."
    ),
    (
        "PCPE - DEA (Delegacia de Crimes Ambientais - PE)",
        "",
        "Social: Instagram @policiacivildepernambuco. Denúncias: 197."
    ),
    (
        "PCPE - DPCA (Delegacia de Proteção à Criança e ao Adolescente - PE)",
        "",
        "Social: Instagram @policiacivildepernambuco. Denúncia nacional: 100. Denúncias PE: 197."
    ),

    # === PRF ===
    (
        "PRF/PE - Polícia Rodoviária Federal em Pernambuco (Superintendência)",
        "",
        "Social: Instagram @prf, Facebook @PRFoficial, Twitter/X @PRFBrasil, YouTube @PRFBrasil"
    ),

    # === PMPE ===
    (
        "PMPE - BOPE (Batalhão de Operações Policiais Especiais - PE)",
        "1cioe@pm.pe.gov.br",
        "Social: Instagram @pmpeoficial, Twitter/X @pmpeoficial, Facebook @PoliciaMilitarPeOficial. Website: http://www.pm.pe.gov.br/bope/"
    ),
    (
        "PMPE - GATI (Grupo de Apoio Tático Itinerante - PE)",
        "",
        "Social: Instagram @pmpeoficial, Twitter/X @pmpeoficial, Facebook @PoliciaMilitarPeOficial"
    ),
    (
        "PMPE - CIPEsp (Comando de Operações Especiais - PE)",
        "",
        "Social: Instagram @pmpeoficial, Twitter/X @pmpeoficial, Facebook @PoliciaMilitarPeOficial"
    ),
    (
        "PMPE - RPMon (Regimento de Polícia Montada - PE)",
        "",
        "Social: Instagram @pmpeoficial, Twitter/X @pmpeoficial, Facebook @PoliciaMilitarPeOficial"
    ),
    (
        "PMPE - BPChoque (Batalhão de Polícia de Choque - PE)",
        "",
        "Social: Instagram @pmpeoficial, Twitter/X @pmpeoficial, Facebook @PoliciaMilitarPeOficial"
    ),
    (
        "PMPE - BPTran (Batalhão de Polícia de Trânsito - PE)",
        "",
        "Social: Instagram @pmpeoficial, Twitter/X @pmpeoficial, Facebook @PoliciaMilitarPeOficial"
    ),
    (
        "PMPE - BPMA (Batalhão de Polícia Militar Ambiental - PE)",
        "",
        "Social: Instagram @pmpeoficial, Twitter/X @pmpeoficial, Facebook @PoliciaMilitarPeOficial"
    ),
    (
        "PMPE - Polícia Militar de Pernambuco (existing)",
        "dpjm@pm.pe.gov.br",
        "Social: Instagram @pmpeoficial, Twitter/X @pmpeoficial, Facebook @PoliciaMilitarPeOficial"
    ),

    # === Scientific Police ===
    (
        "Polícia Científica de Pernambuco (PCPE - Instituto de Criminalística)",
        "ggpoc@sds.pe.gov.br",
        "Social: Facebook @PoliciaCientificaPernambuco, Instagram @sdspeoficial"
    ),
    (
        "Polícia Científica de PE - IML (Instituto Médico Legal - Recife)",
        "",
        "Social: Facebook @PoliciaCientificaPernambuco, Instagram @sdspeoficial"
    ),
    (
        "Polícia Científica de PE - IIML (Instituto de Identificação - PE)",
        "",
        "Social: Facebook @PoliciaCientificaPernambuco, Instagram @sdspeoficial"
    ),

    # === CBMPE ===
    (
        "CBMPE - Corpo de Bombeiros Militar de Pernambuco",
        "faleconosco@bombeiros.pe.gov.br",
        "Social: Instagram @cbmpeoficial, Twitter/X @cbmpeoficial, Facebook @cbmpeoficial. Email SAC: sac@bombeiros.pe.gov.br"
    ),

    # === SDS ===
    (
        "SDS-PE - Secretaria de Defesa Social de Pernambuco (Gabinete)",
        "ouvidoria@sds.pe.gov.br",
        "Social: Instagram @sdspeoficial, Facebook @sdspeoficial. Ouvidoria WhatsApp: +55 (81) 99488-3455. Portal: https://www.ouvidoria.pe.gov.br"
    ),
    (
        "SDS-PE - CIODS (Centro Integrado de Operações de Defesa Social - PE)",
        "",
        "Coordenado pela SDS-PE. Social: Instagram @sdspeoficial, Facebook @sdspeoficial"
    ),
    (
        "SDS-PE - Secretaria de Defesa Social de Pernambuco (existing)",
        "",
        "Social: Instagram @sdspeoficial, Facebook @sdspeoficial. Ouvidoria WhatsApp: +55 (81) 99488-3455"
    ),

    # === Hotlines ===
    (
        "Emergência - Polícia Militar de Pernambuco (190)",
        "",
        "Número nacional de emergência da PM. Acionamento via CIODS/SDS-PE."
    ),
    (
        "Disque-Denúncia - Polícia Civil de Pernambuco (197)",
        "",
        "Portal de denúncias: https://197denuncias.pe.gov.br. Anonimato garantido. Linha também disponível para medidas protetivas (197 Mulher): http://197mulher.pe.gov.br"
    ),
    (
        "Disque 100 - Direitos Humanos (Pernambuco/BR)",
        "",
        "Canal nacional de denúncias de violações de direitos humanos. Atendimento 24h. Anonimato garantido."
    ),
    (
        "Disque 180 - Central de Atendimento à Mulher (Pernambuco/BR)",
        "",
        "Canal nacional de denúncias de violência doméstica e orientação jurídica. Atendimento 24h. Anonimato garantido."
    ),
]


def main():
    db = get_db()

    print("📧 Enriquecendo contatos da polícia de Pernambuco com emails e redes sociais...")
    print()

    updated_email = 0
    updated_social = 0
    not_found = 0

    for search_term, email, social_notes in UPDATES:
        # First try exact match
        rows = db.execute(
            "SELECT id, company, email, notes FROM leads WHERE company LIKE ?",
            (f"%{search_term}%",)
        ).fetchall()

        if not rows:
            # Try shorter search
            short_search = search_term.split("(")[0].strip()[:40]
            rows = db.execute(
                "SELECT id, company, email, notes FROM leads WHERE company LIKE ?",
                (f"%{short_search}%",)
            ).fetchall()

        if not rows:
            print(f"  ⚠️  NOT FOUND: {search_term[:50]}")
            not_found += 1
            continue

        for r in rows:
            lid = r["id"]
            company = r["company"]
            current_email = r["email"] or ""
            current_notes = r["notes"] or ""

            changes = []

            # Update email if empty
            if email and not current_email.strip():
                db.execute("UPDATE leads SET email = ? WHERE id = ?", (email, lid))
                changes.append(f"email: {email}")
                updated_email += 1

            # Append social media to notes
            if social_notes:
                if "Social:" not in current_notes:
                    new_notes = current_notes.strip()
                    if new_notes and not new_notes.endswith("."):
                        new_notes += "."
                    new_notes = new_notes + " " + social_notes if new_notes else social_notes
                    db.execute("UPDATE leads SET notes = ? WHERE id = ?", (new_notes.strip(), lid))
                    changes.append("social media added")
                    updated_social += 1
                else:
                    changes.append("social already in notes")

            if changes:
                print(f"  ✅ {company[:50]:50s} | {', '.join(changes)}")

    db.commit()

    # Final stats
    pe_rows = db.execute(
        """SELECT company, email, notes FROM leads
           WHERE source = 'pernambuco-police' OR
           (source IS NOT NULL AND source LIKE '%pernambuco%') OR
           (company LIKE '%PMPE%' AND company LIKE '%Polícia Militar%')
           ORDER BY company"""
    ).fetchall()

    with_email = sum(1 for r in pe_rows if r["email"] and r["email"].strip())
    with_social = sum(1 for r in pe_rows if "Social:" in (r["notes"] or ""))

    print(f"\n{'='*55}")
    print(f"  UPDATE COMPLETE")
    print(f"{'='*55}")
    print(f"  Emails added:      {updated_email}")
    print(f"  Social media added: {updated_social}")
    print(f"  Not found:          {not_found}")
    print(f"\n  Final state:")
    print(f"  With email:        {with_email}/{len(pe_rows)}")
    print(f"  With social media: {with_social}/{len(pe_rows)}")
    print()
    print("  Sample enriched contacts:")
    for r in pe_rows[:5]:
        print(f"    {r['company'][:45]:45s}")
        print(f"      Email: {r['email'] or '-'}")
        notes = r['notes'] or ''
        social_part = ''
        if 'Social:' in notes:
            idx = notes.index('Social:')
            social_part = notes[idx:idx+80]
        print(f"      Social: {social_part or '-'}")
        print()

    db.close()


if __name__ == "__main__":
    main()
