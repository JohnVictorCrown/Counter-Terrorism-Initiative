#!/usr/bin/env python3
"""
Import all police and security forces of Pernambuco, Brazil into the encrypted CRM.
Includes: Federal Police (PF/PE), Civil Police (PCPE), Military Police (PMPE),
PRF, Scientific Police, Fire Department (CBMPE), BOPE, and specialized delegacies.
Skips duplicates by company name.
"""

import sqlcipher3
import uuid
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

def get_existing_companies(db):
    rows = db.execute("SELECT company FROM leads").fetchall()
    return {r["company"].strip().lower() for r in rows}

# ─── Pernambuco Police & Security Forces ────────────────────────────────────

AGENCIES = [
    # === Federal Police in Pernambuco ===
    {
        "company": "PF/PE - Polícia Federal em Pernambuco (Superintendência Regional)",
        "contact_name": "Plantão da Superintendência",
        "email": "gabin.srpe@pf.gov.br",
        "phone": "+55 (81) 3725-6600 (Plantão) | +55 (81) 3725-6655 | +55 (81) 3725-6623",
        "website": "https://www.gov.br/pf/pt-br/acesso-a-informacao/institucional/quem-e-quem/superintendencias-e-delegacias/pernambuco/superintendencia-regional-em-pernambuco",
        "tier": "1",
        "type": "Law Enforcement",
        "vertical": "Brazil",
        "notes": "Superintendência Regional da Polícia Federal em Pernambuco. Endereço: Av. Cais do Apolo, 321, Bairro do Recife, Recife-PE. Atendimento: Passaportes, crimes federais, imigração. Emergency: 190.",
        "source": "pernambuco-police"
    },
    {
        "company": "PF/PE - Delegacia de Imigração (Polícia Federal PE)",
        "contact_name": "",
        "email": "",
        "phone": "+55 (81) 3725-6600",
        "website": "https://www.gov.br/pf/pt-br/pernambuco",
        "tier": "2",
        "type": "Law Enforcement",
        "vertical": "Brazil",
        "notes": "Delegacia de Imigração da Polícia Federal em Pernambuco. Controle migratório e passaportes. Endereço: Av. Cais do Apolo, 321, Recife-PE.",
        "source": "pernambuco-police"
    },

    # === Civil Police of Pernambuco ===
    {
        "company": "PCPE - Polícia Civil de Pernambuco (Chefia)",
        "contact_name": "Chefia da Polícia Civil",
        "email": "",
        "phone": "+55 (81) 3184-3823 | +55 (81) 3184-3824",
        "website": "https://www2.pc.pe.gov.br",
        "tier": "1",
        "type": "Law Enforcement",
        "vertical": "Brazil",
        "notes": "Polícia Civil de Pernambuco - Chefia. Hotline de Denúncias: 197 (24h). Endereço: Recife-PE. Responsável por investigações criminais no estado.",
        "source": "pernambuco-police"
    },
    {
        "company": "PCPE - DHPP (Departamento de Homicídios e Proteção à Pessoa - PE)",
        "contact_name": "",
        "email": "",
        "phone": "+55 (81) 3184-3000",
        "website": "https://www2.pc.pe.gov.br",
        "tier": "1",
        "type": "Law Enforcement",
        "vertical": "Brazil",
        "notes": "Departamento de Homicídios e Proteção à Pessoa - Polícia Civil de Pernambuco. Investiga homicídios, latrocínios e crimes violentos contra a pessoa. Endereço: Recife-PE.",
        "source": "pernambuco-police"
    },
    {
        "company": "PCPE - DEAM (Delegacia Especializada de Atendimento à Mulher - Recife)",
        "contact_name": "",
        "email": "",
        "phone": "+55 (81) 3624-1983",
        "website": "https://www2.pc.pe.gov.br",
        "tier": "1",
        "type": "Law Enforcement",
        "vertical": "Brazil",
        "notes": "Delegacia Especializada de Atendimento à Mulher - Recife/PE. Denúncia nacional: 180. Endereço: Rua do Pombal, s/n, Santo Amaro, Recife-PE. Atendimento especializado a vítimas de violência doméstica.",
        "source": "pernambuco-police"
    },
    {
        "company": "PCPE - DECON (Delegacia do Consumidor - PE)",
        "contact_name": "",
        "email": "",
        "phone": "+55 (81) 3184-3600",
        "website": "https://www2.pc.pe.gov.br",
        "tier": "2",
        "type": "Law Enforcement",
        "vertical": "Brazil",
        "notes": "Delegacia de Crimes contra o Consumidor - Pernambuco. Proteção ao consumidor e crimes contra as relações de consumo.",
        "source": "pernambuco-police"
    },
    {
        "company": "PCPE - DEA (Delegacia de Crimes Ambientais - PE)",
        "contact_name": "",
        "email": "",
        "phone": "+55 (81) 3184-3700",
        "website": "https://www2.pc.pe.gov.br",
        "tier": "2",
        "type": "Law Enforcement",
        "vertical": "Brazil",
        "notes": "Delegacia de Crimes contra o Meio Ambiente - Pernambuco. Investigação de crimes ambientais, desmatamento, poluição e fauna.",
        "source": "pernambuco-police"
    },
    {
        "company": "PCPE - DPCA (Delegacia de Proteção à Criança e ao Adolescente - PE)",
        "contact_name": "",
        "email": "",
        "phone": "+55 (81) 3184-3400",
        "website": "https://www2.pc.pe.gov.br",
        "tier": "2",
        "type": "Law Enforcement",
        "vertical": "Brazil",
        "notes": "Delegacia de Proteção à Criança e ao Adolescente - Pernambuco. Denúncia: 100 (Disque Direitos Humanos). Atendimento especializado a crianças e adolescentes vítimas de violência.",
        "source": "pernambuco-police"
    },

    # === PRF in Pernambuco ===
    {
        "company": "PRF/PE - Polícia Rodoviária Federal em Pernambuco (Superintendência)",
        "contact_name": "Superintendência Regional PRF/PE",
        "email": "",
        "phone": "+55 (81) 3201-0700 | +55 (81) 3201-0896 | Emergência: 191",
        "website": "https://www.gov.br/prf/pt-br/canais-de-atendimento/unidades-prf/pernambuco",
        "tier": "1",
        "type": "Law Enforcement",
        "vertical": "Brazil",
        "notes": "Superintendência Regional da Polícia Rodoviária Federal em Pernambuco. Endereço: Av. Antônio de Góes, 820, Pina, Recife-PE, CEP: 51010-000. Emergência em rodovias federais: 191 (24h).",
        "source": "pernambuco-police"
    },

    # === Military Police of Pernambuco ===
    {
        "company": "PMPE - BOPE (Batalhão de Operações Policiais Especiais - PE)",
        "contact_name": "Comando do BOPE",
        "email": "bope@pm.pe.gov.br",
        "phone": "+55 (81) 3181-1850",
        "website": "http://www.pm.pe.gov.br",
        "tier": "1",
        "type": "Security",
        "vertical": "Brazil",
        "notes": "Batalhão de Operações Policiais Especiais da PMPE. Força de elite para operações de alto risco, resgate de reféns e combate ao crime organizado. Endereço: Av. Central, nº 3770, Mangueira, Recife-PE, CEP: 50850-268.",
        "source": "pernambuco-police"
    },
    {
        "company": "PMPE - GATI (Grupo de Apoio Tático Itinerante - PE)",
        "contact_name": "",
        "email": "",
        "phone": "190 (Emergência PMPE)",
        "website": "http://www.pm.pe.gov.br",
        "tier": "2",
        "type": "Security",
        "vertical": "Brazil",
        "notes": "Grupo de Apoio Tático Itinerante da PMPE. Patrulhamento tático em áreas de alto risco. Não possui canal direto ao público - acionamento via 190. Subordinado ao Comando de Policiamento da Capital (CPC).",
        "source": "pernambuco-police"
    },
    {
        "company": "PMPE - CIPEsp (Comando de Operações Especiais - PE)",
        "contact_name": "",
        "email": "",
        "phone": "+55 (81) 3181-1850",
        "website": "http://www.pm.pe.gov.br",
        "tier": "1",
        "type": "Security",
        "vertical": "Brazil",
        "notes": "Comando de Operações Especiais da PMPE. Coordena as unidades especiais da PMPE incluindo BOPE, GATI, Choque e ROCAM. Endereço: Av. Central, s/n, Mangueira, Recife-PE.",
        "source": "pernambuco-police"
    },
    {
        "company": "PMPE - RPMon (Regimento de Polícia Montada - PE)",
        "contact_name": "",
        "email": "",
        "phone": "+55 (81) 3181-8000",
        "website": "http://www.pm.pe.gov.br",
        "tier": "2",
        "type": "Security",
        "vertical": "Brazil",
        "notes": "Regimento de Polícia Montada da PMPE - Cavalaria. Atua em policiamento ostensivo, controle de multidões e áreas de difícil acesso.",
        "source": "pernambuco-police"
    },
    {
        "company": "PMPE - BPChoque (Batalhão de Polícia de Choque - PE)",
        "contact_name": "",
        "email": "",
        "phone": "+55 (81) 3181-8000",
        "website": "http://www.pm.pe.gov.br",
        "tier": "2",
        "type": "Security",
        "vertical": "Brazil",
        "notes": "Batalhão de Polícia de Choque da PMPE. Controle de distúrbios civis, grandes eventos e operações de garantia da lei e da ordem.",
        "source": "pernambuco-police"
    },
    {
        "company": "PMPE - BPTran (Batalhão de Polícia de Trânsito - PE)",
        "contact_name": "",
        "email": "",
        "phone": "+55 (81) 3181-8000",
        "website": "http://www.pm.pe.gov.br",
        "tier": "2",
        "type": "Security",
        "vertical": "Brazil",
        "notes": "Batalhão de Polícia de Trânsito da PMPE. Policiamento e fiscalização de trânsito na Região Metropolitana do Recife.",
        "source": "pernambuco-police"
    },
    {
        "company": "PMPE - BPMA (Batalhão de Polícia Militar Ambiental - PE)",
        "contact_name": "",
        "email": "",
        "phone": "+55 (81) 3181-8000",
        "website": "http://www.pm.pe.gov.br",
        "tier": "2",
        "type": "Security",
        "vertical": "Brazil",
        "notes": "Batalhão de Polícia Militar Ambiental de Pernambuco. Fiscalização e proteção ambiental, combate a crimes ambientais.",
        "source": "pernambuco-police"
    },

    # === Scientific Police ===
    {
        "company": "Polícia Científica de Pernambuco (PCPE - Instituto de Criminalística)",
        "contact_name": "Gerência Geral de Polícia Científica",
        "email": "ggpoc@sds.pe.gov.br",
        "phone": "+55 (81) 3183-5037",
        "website": "https://www.policiacientifica.pe.gov.br",
        "tier": "2",
        "type": "Law Enforcement",
        "vertical": "Brazil",
        "notes": "Polícia Científica de Pernambuco. Perícia criminal, medicina legal, identificação criminal. Endereço: Rua São Geraldo, 111, 1º andar, Santo Amaro, Recife-PE. Subordinada à SDS-PE.",
        "source": "pernambuco-police"
    },
    {
        "company": "Polícia Científica de PE - IML (Instituto Médico Legal - Recife)",
        "contact_name": "",
        "email": "",
        "phone": "+55 (81) 3183-5000",
        "website": "https://www.policiacientifica.pe.gov.br",
        "tier": "2",
        "type": "Law Enforcement",
        "vertical": "Brazil",
        "notes": "Instituto Médico Legal de Recife/PE. Perícias médico-legais, necropsias, exames de lesão corporal. Subordinado à Polícia Científica de Pernambuco.",
        "source": "pernambuco-police"
    },
    {
        "company": "Polícia Científica de PE - IIML (Instituto de Identificação - PE)",
        "contact_name": "",
        "email": "",
        "phone": "+55 (81) 3183-5037",
        "website": "https://www.policiacientifica.pe.gov.br",
        "tier": "2",
        "type": "Law Enforcement",
        "vertical": "Brazil",
        "notes": "Instituto de Identificação de Pernambuco. Emissão de carteiras de identidade (RG) e identificação criminal.",
        "source": "pernambuco-police"
    },

    # === Fire Department ===
    {
        "company": "CBMPE - Corpo de Bombeiros Militar de Pernambuco",
        "contact_name": "Comando Geral do CBMPE",
        "email": "faleconosco@bombeiros.pe.gov.br",
        "phone": "Emergência: 193 | Administrativo: +55 (81) 3182-9177 | +55 (81) 3182-9176",
        "website": "https://www.bombeiros.pe.gov.br",
        "tier": "1",
        "type": "Security",
        "vertical": "Brazil",
        "notes": "Corpo de Bombeiros Militar de Pernambuco. Emergência: 193 (incêndios, resgates, desastres). Endereço: Rua João de Barros, 339, Boa Vista, Recife-PE, CEP: 50050-180. Email SAC: sac@bombeiros.pe.gov.br",
        "source": "pernambuco-police"
    },

    # === Secretariat of Social Defense ===
    {
        "company": "SDS-PE - Secretaria de Defesa Social de Pernambuco (Gabinete)",
        "contact_name": "Gabinete do Secretário",
        "email": "ouvidoria@sds.pe.gov.br",
        "phone": "+55 (81) 3183-5044 | Ouvidoria: 0800 081 5001 | +55 (81) 3183-5373",
        "website": "https://www.sds.pe.gov.br",
        "tier": "1",
        "type": "Government",
        "vertical": "Brazil",
        "notes": "Secretaria de Defesa Social de Pernambuco. Órgão central do sistema de segurança pública do estado. Coordena PMPE, PCPE, CBMPE e Polícia Científica. Endereço: Rua São Geraldo, 111, Santo Amaro, Recife-PE, CEP: 52040-020.",
        "source": "pernambuco-police"
    },
    {
        "company": "SDS-PE - CIODS (Centro Integrado de Operações de Defesa Social - PE)",
        "contact_name": "Central de Atendimento",
        "email": "",
        "phone": "190 (PM) | 197 (PC) | 193 (Bombeiros)",
        "website": "https://www.sds.pe.gov.br",
        "tier": "1",
        "type": "Government",
        "vertical": "Brazil",
        "notes": "Centro Integrado de Operações de Defesa Social de Pernambuco. Central de atendimento de emergências unificada. Emergência: 190 (Polícia Militar), 197 (Polícia Civil - Denúncias), 193 (Bombeiros).",
        "source": "pernambuco-police"
    },

    # === Emergency Hotlines ===
    {
        "company": "Emergência - Polícia Militar de Pernambuco (190)",
        "contact_name": "CIODS - Central de Atendimento",
        "email": "",
        "phone": "190 (Emergência 24h)",
        "website": "",
        "tier": "1",
        "type": "Security",
        "vertical": "Brazil",
        "notes": "Número de emergência da Polícia Militar de Pernambuco. Discar 190 para ocorrências policiais urgentes em todo o estado. Atendimento 24 horas pelo CIODS.",
        "source": "pernambuco-police"
    },
    {
        "company": "Disque-Denúncia - Polícia Civil de Pernambuco (197)",
        "contact_name": "Central de Denúncias",
        "email": "",
        "phone": "197 (Disque-Denúncia 24h)",
        "website": "",
        "tier": "1",
        "type": "Law Enforcement",
        "vertical": "Brazil",
        "notes": "Disque-Denúncia da Polícia Civil de Pernambuco (197). Canal anônimo para denúncias de crimes. Atendimento 24 horas. Anonimato garantido.",
        "source": "pernambuco-police"
    },
    {
        "company": "Disque 100 - Direitos Humanos (Pernambuco/BR)",
        "contact_name": "Disque Direitos Humanos",
        "email": "",
        "phone": "100 (Disque Direitos Humanos - Nacional)",
        "website": "https://www.gov.br/mdh/pt-br/disque100",
        "tier": "2",
        "type": "Government",
        "vertical": "Brazil",
        "notes": "Disque 100 - Canal nacional de denúncias de violações de direitos humanos. Atende crianças, adolescentes, idosos, pessoas com deficiência, LGBTQIA+ e mulheres. Atendimento 24h. Anonimato garantido.",
        "source": "pernambuco-police"
    },
    {
        "company": "Disque 180 - Central de Atendimento à Mulher (Pernambuco/BR)",
        "contact_name": "Central de Atendimento à Mulher",
        "email": "",
        "phone": "180 (Central de Atendimento à Mulher - Nacional)",
        "website": "",
        "tier": "2",
        "type": "Government",
        "vertical": "Brazil",
        "notes": "Disque 180 - Central de Atendimento à Mulher. Denúncias de violência doméstica e orientação jurídica. Atendimento 24h. Anonimato garantido.",
        "source": "pernambuco-police"
    },
]

def main():
    db = get_db()
    existing = get_existing_companies(db)

    print(f"🚀 Importing Pernambuco Police & Security Forces into CRM...")
    print(f"   Agencies to add: {len(AGENCIES)}")
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

    print(f"\n{'='*55}")
    print(f"  IMPORT COMPLETE")
    print(f"{'='*55}")
    print(f"  Inserted: {inserted}")
    print(f"  Skipped (duplicates): {skipped}")
    print()

    # Final stats
    pe_count = db.execute(
        "SELECT COUNT(*) FROM leads WHERE (company LIKE '%Pernambuco%' OR company LIKE '%PMPE%' OR company LIKE '%SDS%' OR company LIKE '%CBMPE%' OR company LIKE '%BOPE%' OR company LIKE '%PCPE%' OR company LIKE '%PF/PE%' OR company LIKE '%PRF/PE%' OR company LIKE '%Disque%' OR company LIKE '%190%' OR company LIKE '%Polícia Científica%') AND source = 'pernambuco-police'"
    ).fetchone()[0]

    print(f"  Total Pernambuco security contacts now: {pe_count}")

    # Show what's in PE now
    pe_rows = db.execute(
        """SELECT company, type, phone FROM leads
           WHERE source = 'pernambuco-police'
           ORDER BY type, company"""
    ).fetchall()

    print(f"\n  All Pernambuco Police Contacts:")
    print(f"  {'='*55}")
    for r in pe_rows:
        p_short = (r["phone"][:40] + "...") if len(r["phone"] or "") > 40 else (r["phone"] or "-")
        print(f"  [{r['type'][:16]:16s}] {r['company'][:45]:45s}")
        print(f"  {'':18s} 📞 {p_short}")

    db.close()


if __name__ == "__main__":
    main()
