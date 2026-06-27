"""
Enrich contacts missing email addresses.
Adds available public emails or notes explaining the official contact method.
"""

import sqlcipher3
from pathlib import Path

# Connect
pw = None
with open('.env') as f:
    for line in f:
        line = line.strip()
        if line.startswith('EMAIL_DB_PASSWORD='):
            pw = line.split('=', 1)[1].strip().strip('"').strip("'")
            break

db = sqlcipher3.connect(str(Path('leads.db')))
db.row_factory = sqlcipher3.Row
hex_key = pw.encode().hex()
db.execute(f'PRAGMA key="x\'{hex_key}\'"')

# Updates: (search_term, email_to_set, notes_to_append)
# Notes only appended if email is being set (to document contact method)
UPDATES = [
    # === FIVE EYES ===
    ("MI5 - Security Service (UK)", "", 
     "Contact via secure online form at mi5.gov.uk/contact-us or call 0800 111 4645. No public email."),
    ("MI6 / SIS - Secret Intelligence Service (UK)", "",
     "Media enquiries via FCDO Press Office at pressoffice@fcdo.gov.uk or 020 7008 3100. No public contact email."),
    ("GCHQ - Government Communications Headquarters (UK)", "media@gchq.gov.uk",
     ""),
    ("CSE - Communications Security Establishment (Canada)", "media@cse-cst.gc.ca",
     ""),
    ("CSIS - Canadian Security Intelligence Service", "media@csis-scrs.gc.ca",
     ""),
    ("ASIO - Australian Security Intelligence Organisation", "media@asio.gov.au",
     ""),
    ("ASIS - Australian Secret Intelligence Service (Australia)", "",
     "Contact via phone: +61 2 6261 3100 (Recruitment) or +61 2 6261 9907 (Graduate enquiries). No public email."),
    ("ASD - Australian Signals Directorate", "asd.media@defence.gov.au",
     "Cyber incident reporting: cyber.gov.au/report-and-recover"),
    ("NZSIS - New Zealand Security Intelligence Service", "media@nzic.govt.nz",
     "Public tips: 0800 SIS 224. Web form at nzsis.govt.nz"),
    ("GCSB - Government Communications Security Bureau (NZ)", "media@nzic.govt.nz",
     ""),

    # === EUROPE ===
    ("BND - Bundesnachrichtendienst (Germany)", "",
     "Contact via official website form at bnd.bund.de. No public email."),
    ("BfV - Bundesamt fur Verfassungsschutz (Germany)", "hinweise@bfv.bund.de",
     ""),
    ("DGSE - Direction Generale de la Securite Exterieure (France)", "",
     "Contact via dgse.gouv.fr. No public contact email."),
    ("DGSI - Direction Generale de la Securite Interieure (France)", "assistance@interieur.gouv.fr",
     ""),
    ("CNI - Centro Nacional de Inteligencia (Spain)", "",
     "Contact via cni.es/en/contact. No public email."),
    ("AIVD - Algemene Inlichtingen- en Veiligheidsdienst (Netherlands)", "",
     "Contact via phone: +31 79 320 5050 (24/7) or post. No public email for security reasons."),
    ("MIVD - Militaire Inlichtingen- en Veiligheidsdienst (Netherlands)", "",
     "Contact Ministry of Defence Press Office at persvoorlichting@mindef.nl. No public email."),
    ("SAPO - Swedish Security Service", "sakerhetspolisen@sakerhetspolisen.se",
     ""),
    ("PET - Politiets Efterretningstjeneste (Denmark)", "pet@pet.dk",
     "Press: presse@pet.dk"),
    ("SUPO - Suojelupoliisi (Finland)", "kirjaamo@supo.fi",
     "Media: media@supo.fi"),
    ("BVT - Bundesamt fur Verfassungsschutz und Terrorismusbekampfung (Austria)", "",
     "Contact via bvt.gv.at. No public email."),
    ("NDB - Nachrichtendienst des Bundes (Switzerland)", "",
     "Contact via ndb.admin.ch. No public email."),
    ("VSSE/ADIV - Veiligheid van de Staat (Belgium)", "",
     "Contact via vsse.be. No public email."),
    ("EYP - Ethniki Ypiresia Pliroforion (Greece)", "",
     "Contact via eyp.gr. No public email."),
    ("IH - Informacios Hivatal (Hungary)", "",
     "Contact via ih.gov.hu. No public email."),
    ("AISE - Agenzia Informazioni e Sicurezza Esterna (Italy)", "",
     "Contact via governo.it. No public email."),
    ("AISI - Agenzia Informazioni e Sicurezza Interna (Italy)", "",
     "Contact via governo.it. No public email."),
    ("ABW - Agencja Bezpieczenstwa Wewnetrznego (Poland)", "",
     "Contact via abw.gov.pl. No public email."),
    ("SIS - Servico de Informacoes de Seguranca (Portugal)", "",
     "Contact via sis.pt. No public email."),
    ("SRI - Serviciul Roman de Informatii (Romania)", "",
     "Contact via sri.ro. No public email."),

    # === MIDDLE EAST / ASIA ===
    ("Shin Bet / Shabak (Israel)", "",
     "Contact via shabak.gov.il/en/pages/contactus. No public email."),
    ("Mossad - Institute for Intelligence (Israel)", "",
     "Contact via mossad.gov.il/en/contact-us. No public email."),
    ("MIT - National Intelligence Organization (Turkey)", "",
     "Contact via mit.gov.tr/en/yardim.html. No public email."),
    ("MSS - Ministry of State Security (China)", "",
     "National security tip hotline: 12339. No public email."),
    ("RAW - Research and Analysis Wing (India)", "",
     "No official public email address or website."),
    ("IB - Intelligence Bureau (India)", "",
     "No official public email address or website."),
    ("NIA - National Investigation Agency (India)", "nri@nia.gov.in",
     ""),
    ("ISI - Inter-Services Intelligence (Pakistan)", "",
     "No official public email address or website."),
    ("SBU - Security Service of Ukraine", "",
     "Contact via sbu.gov.ua. No public email."),
    ("NIS - National Intelligence Service (South Korea)", "",
     "Contact via nis.go.kr. No public email."),
    ("NSB - National Security Bureau (Taiwan)", "",
     "Contact via nsb.gov.tw. No public email."),
    ("BIN - Badan Intelijen Negara (Indonesia)", "",
     "Contact via bin.go.id. No public email."),
    ("MEIO - Malaysian External Intelligence Organisation", "",
     "Contact via meio.gov.my. No public email."),
    ("ISD - Internal Security Department (Singapore)", "",
     "Contact via isd.gov.sg. No public email."),
    ("SID - Security and Intelligence Division (Singapore)", "",
     "Contact via mindef.gov.sg. No public email."),
    ("NIA - National Intelligence Agency (Thailand)", "",
     "Contact via nia.go.th. No public email."),
    ("TC2 - General Department of Intelligence (Vietnam)", "",
     "No official public contact information available."),
    ("NICA - National Intelligence Coordinating Agency (Philippines)", "",
     "Contact via nica.gov.ph. No public email."),
    ("SIA - State Intelligence Agency (UAE)", "",
     "Contact via sia.gov.ae. No public email."),
    ("CNI - Centro Nacional de Inteligencia (Mexico)", "",
     "Contact via cni-mexico.gob.mx. No public email."),
    ("NIS - Norwegian Intelligence Service", "",
     "Contact via forsvaret.no. No public email."),
    ("PST - Politiets Sikkerhetstjeneste (Norway)", "",
     "Contact via pst.no. No public email."),
    ("SSA - State Security Agency (South Africa)", "",
     "Contact via ssa.gov.za. No public email."),
    ("G2 - Military Intelligence (Ireland)", "",
     "Contact via defence.ie. No public email."),
    ("PSIA - Public Security Intelligence Agency (Japan)", "",
     "Contact via moj.go.jp/psia. No public email."),
    ("DIH - Cabinet Intelligence and Research Office (Japan)", "",
     "Contact via cas.go.jp. No public email."),
    ("ODNI - Office of the Director of National Intelligence (USA)", "odni-pre-pub@odni.gov",
     ""),

    # === PERNAMBUCO POLICE ===
    ("PCPE - Policia Civil de Pernambuco (Chefia)", "",
     "Contact via fale-conosco form at pc.pe.gov.br. Tip line: 197."),
    ("PCPE - DHPP (Departamento de Homicidios)", "",
     "Contact via PC/PE Chefia or Disque-Denuncia 197. No direct departmental email."),
    ("PCPE - DEAM (Delegacia da Mulher)", "",
     "Contact via PC/PE Chefia or Disque-Denuncia 197. No direct departmental email."),
    ("PCPE - DECON (Delegacia do Consumidor)", "",
     "Contact via PC/PE Chefia or Disque-Denuncia 197. No direct departmental email."),
    ("PCPE - DEA (Delegacia de Crimes Ambientais)", "",
     "Contact via PC/PE Chefia or Disque-Denuncia 197. No direct departmental email."),
    ("PCPE - DPCA (Delegacia da Crianca)", "",
     "Contact via PC/PE Chefia or Disque-Denuncia 197. No direct departmental email."),
    ("PF/PE - Delegacia de Imigracao", "umig.cru.pe@pf.gov.br",
     ""),
    ("PRF/PE - Policia Rodoviaria Federal em Pernambuco", "atendimento.pe@prf.gov.br",
     "Emergency: 191"),
    ("PMPE - BPChoque (Batalhao de Choque)", "",
     "Contact via PMPE HQ (dpjm@pm.pe.gov.br) or SDS-PE. No direct battalion email."),
    ("PMPE - BPMA (Batalhao Ambiental)", "",
     "Contact via PMPE HQ (dpjm@pm.pe.gov.br) or SDS-PE. No direct battalion email."),
    ("PMPE - BPTran (Batalhao de Transito)", "",
     "Contact via PMPE HQ (dpjm@pm.pe.gov.br) or SDS-PE. No direct battalion email."),
    ("PMPE - CIPEsp (Comando de Operacoes Especiais)", "",
     "Contact via PMPE HQ (dpjm@pm.pe.gov.br) or SDS-PE. No direct command email."),
    ("PMPE - GATI (Grupo de Apoio Tatito)", "",
     "Contact via PMPE HQ (dpjm@pm.pe.gov.br) or SDS-PE. No direct unit email."),
    ("PMPE - RPMon (Regimento de Policia Montada)", "",
     "Contact via PMPE HQ (dpjm@pm.pe.gov.br) or SDS-PE. No direct regiment email."),
    ("IIML", "",
     "Contact via Policia Cientifica PE at policiacientifica.pe.gov.br. Phone: (81) 3183-5037."),
    ("IML", "",
     "Contact via Policia Cientifica PE at policiacientifica.pe.gov.br. Phone: (81) 3183-5000."),
    ("CIODS", "",
     "Emergency: 190 (PM), 193 (Fire), 197 (Civil Police). SDS-PE phone: (81) 3183-5044. No direct email."),
    ("Disque-Den\u00fancia", "",
     "Online portal: 197denuncias.pe.gov.br. Call: 197."),
    ("Emerg\u00eancia - Pol\u00edcia Militar", "",
     "Emergency number: 190. Contact PMPE via dpjm@pm.pe.gov.br for administrative matters."),
    ("Disque 100 - Direitos Humanos", "",
     "National human rights hotline. Call: 100. Website: gov.br/mdh."),
    ("Disque 180 - Central de Atendimento", "",
     "National women's hotline. Call: 180. Website: gov.br/mulheres."),

    # === USA ===
    ("FBI - Federal Bureau of Investigation", "",
     "Tip line: 1-800-CALL-FBI (1-800-225-5324). Tips online at tips.fbi.gov."),


]

updated = 0
not_found = []

for search_term, email, note_suffix in UPDATES:
    # Find matching contacts
    rows = db.execute(
        "SELECT id, company, email, notes FROM leads WHERE company LIKE ? AND (email IS NULL OR email = '')",
        (f'%{search_term}%',)
    ).fetchall()

    if not rows:
        # Try a shorter search
        shorter = search_term.split('(')[0].strip()
        rows = db.execute(
            "SELECT id, company, email, notes FROM leads WHERE company LIKE ? AND (email IS NULL OR email = '')",
            (f'%{shorter}%',)
        ).fetchall()

    if not rows:
        not_found.append(search_term)
        continue

    for row in rows:
        current_notes = row['notes'] or ''
        new_notes = current_notes

        if email:
            db.execute("UPDATE leads SET email = ? WHERE id = ?", (email, row['id']))
        
        if note_suffix and note_suffix not in current_notes:
            if new_notes and not new_notes.endswith(('.', '!', '?')):
                new_notes += '.'
            if new_notes:
                new_notes += ' ' + note_suffix
            else:
                new_notes = note_suffix
            db.execute("UPDATE leads SET notes = ? WHERE id = ?", (new_notes, row['id']))

        updated += 1

db.commit()

print(f"✅ Updated {updated} contacts with emails/contact notes")
print(f"❌ Not found ({len(not_found)}):")
for nf in not_found:
    print(f"   - {nf}")

# Final summary
print()
cur = db.execute("SELECT COUNT(*) FROM leads WHERE (email IS NULL OR email = '') AND vertical NOT IN ('Brazil', '') AND type IN ('Intelligence', 'Homeland Security', 'Government', 'Defense', 'Law Enforcement', 'Military')")
still_missing_intl = cur.fetchone()[0]
cur = db.execute("SELECT COUNT(*) FROM leads WHERE (email IS NULL OR email = '') AND vertical = 'Brazil' AND source = 'pernambuco-police'")
still_missing_pe = cur.fetchone()[0]
print(f"Still missing emails: {still_missing_intl} international + {still_missing_pe} Pernambuco police")
db.close()
