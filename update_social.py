import sqlcipher3
import uuid
from pathlib import Path

pw = None
with open('.env') as f:
    for line in f:
        line = line.strip()
        if line.startswith('EMAIL_DB_PASSWORD='):
            pw = line.split('=', 1)[1].strip().strip('"').strip("'")
            break

db = sqlcipher3.connect(str(Path('leads.db')))
hex_key = pw.encode().hex()
db.execute(f"PRAGMA key=\"x'{hex_key}'\"")
db.row_factory = sqlcipher3.Row

# Get existing HR contacts from web-research
rows = db.execute("""
    SELECT id, company, notes FROM leads 
    WHERE source = 'web-research'
    AND (company LIKE '%MNPCT%' OR company LIKE '%CNPCT%'
         OR company LIKE '%CNDH%' OR company LIKE '%Disque 100%'
         OR company LIKE '%PFDC%' OR company LIKE '%DPPE%'
         OR company LIKE '%ALEPE%' OR company LIKE '%Pastoral Carcer%'
         OR company LIKE '%Conectas%' OR company LIKE '%Justi%a Global%'
         OR company LIKE '%AJD%' OR company LIKE '%IDDD%'
         OR company LIKE '%ICRC%' OR company LIKE '%Amnesty%'
         OR company LIKE '%Human Rights Watch%' OR company LIKE '%IRCT%'
         OR company LIKE '%APT%' OR company LIKE '%OMCT%'
         OR company LIKE '%REDRESS%' OR company LIKE '%Physicians%'
         OR company LIKE '%Front Line%' OR company LIKE '%OHCHR%'
         OR company LIKE '%Special Rapporteur%' OR company LIKE '%IACHR%'
         OR company LIKE '%Inter-American Court%' OR company LIKE '%ECHR%')
""").fetchall()

print(f'Found {len(rows)} existing HR contacts')

social_updates = {
    'MNPCT': 'Social: Instagram @mnpctbrasil',
    'CNPCT': 'Social: Instagram @cnpctbrasil',
    'CNDH': 'Social: Instagram @cndhbrasil, Facebook @conselhodedireitoshumanos, YouTube @ConselhoNacionaldosDireitosHumanosCNDH',
    'Disque 100': 'Social: Instagram @mdhcbrasil, Twitter @mdhcbrasil',
    'PFDC': 'Social: Instagram @mpfederal, Twitter @mpfederal',
    'DPPE': 'Social: Instagram @defensoriape, Facebook @defensoriape',
    'ALEPE': 'Social: Instagram @assembleiape',
    'Pastoral Carcer': 'Social: Instagram @pcrnacional, Facebook @PastoralCarcerariaCNBB, YouTube @PastoralCarcerariaImprensa',
    'Conectas': 'Social: Instagram @conectas, LinkedIn /company/conectasdh',
    'Justi': 'Social: Instagram @justicaglobal, Facebook @justicaglobal, YouTube @JusticaGlobal, Twitter @justicaglobal',
    'AJD': 'Social: Instagram @ajd.brasil, Facebook @ajd.brasil, YouTube @ajd_brasil, Twitter @ajd_brasil',
    'IDDD': 'Social: Instagram @_direitodedefesa, Facebook @idireitodedefesa, LinkedIn /company/iddd, YouTube @IDDD',
    'ICRC': 'Social: Twitter @ICRC, Instagram @icrc, Facebook @ICRC, LinkedIn /company/icrc, YouTube @icrc',
    'Amnesty': 'Social: Twitter @amnesty, Instagram @amnesty, Facebook @amnesty, LinkedIn /company/amnesty-international, YouTube @AmnestyInternational',
    'Human Rights Watch': 'Social: Twitter @hrw, Instagram @humanrightswatch, Facebook @HumanRightsWatch, LinkedIn /company/human-rights-watch, YouTube @HumanRightsWatch',
    'IRCT': 'Social: Twitter @IRCT_torture, Facebook @IRCTtorture, LinkedIn /company/irct',
    'APT': 'Social: Twitter @APT_geneva, LinkedIn /company/association-for-the-prevention-of-torture-apt',
    'OMCT': 'Social: Twitter @OMCT_torture, Instagram @omct_torture, Facebook @omcttorture',
    'REDRESS': 'Social: Twitter @REDRESStorture, Facebook @REDRESStorture, LinkedIn /company/redress',
    'Physicians': 'Social: Twitter @P4HR, Instagram @phr, Facebook @PhysiciansforHumanRights',
    'Front Line': 'Social: Twitter @frontlinedef, Instagram @frontlinedefenders, Facebook @frontlinedefenders, YouTube @frontlinedefenders',
    'OHCHR': 'Social: Twitter @UNHumanRights, Instagram @unhumanrights, Facebook @unitednationshumanrights, YouTube @UNOHCHR',
    'Special Rapporteur': 'Social: Twitter @DrAliceJEdwards',
    'IACHR': 'Social: Twitter @IACHR, Instagram @cidh_oas, Facebook @CIDH.OEA, YouTube @CIDHIACHR',
    'Inter-American Court': 'Social: Twitter @CorteIDH, Facebook @CorteIDH, LinkedIn /company/corteidh, YouTube @CorteIDH',
    'ECHR': 'Social: Twitter @ECHR_CEDH, Facebook @ECHR.CEDH, LinkedIn /company/echr-cedh',
}

updated = 0
for row in rows:
    company = row['company']
    notes = row['notes'] or ''
    if 'Social:' in notes:
        continue
    social_text = None
    for key, val in social_updates.items():
        if key in company:
            social_text = val
            break
    if social_text:
        new_notes = notes + '\n\n' + social_text
        db.execute('UPDATE leads SET notes = ?, updated_at = datetime(\'now\') WHERE id = ?', (new_notes, row['id']))
        updated += 1

db.commit()
print(f'Updated {updated} entries with social media')

# Add new institutions
new_contacts = [
    {
        'company': 'GAJOP - Gabinete de Assessoria Juridica as Organizacoes Populares (PE)',
        'email': 'secretaria@gajop.org',
        'phone': '(81) 3040-1004',
        'notes': 'GAJOP - Organizacao de assessoria juridica popular e direitos humanos em Pernambuco. Atuacao em justica criminal, seguranca publica e combate a tortura. Social: Instagram @gajop_ong',
    },
    {
        'company': 'CENDHEC - Centro de Direitos Humanos e Cidadania (PE)',
        'email': 'cendhec@cendhec.org.br',
        'phone': '(81) 3227-4560',
        'notes': 'Centro de Direitos Humanos e Cidadania (CENDHEC) - Recife/PE. Atuacao em direitos humanos, assessoria juridica e educacao popular. Social: Instagram @cendhec',
    },
    {
        'company': 'SOS Corpo - Instituto Feminista para a Democracia (PE)',
        'email': 'sos@soscorpo.org',
        'phone': '(81) 3087-2086',
        'notes': 'SOS Corpo - Instituto Feminista para a Democracia. Recife/PE. Atuacao em direitos das mulheres, violencia de genero e direitos humanos. Social: Instagram @soscorpo.feminista',
    },
    {
        'company': 'CPT NE2 - Comissao Pastoral da Terra - Nordeste II (PE/PB/AL)',
        'email': 'cptne2@cptne2.org.br',
        'phone': '(81) 3222-3868',
        'notes': 'Comissao Pastoral da Terra - Regional Nordeste II. Atuacao em direitos humanos no campo, combate ao trabalho escravo e violencia no campo. Social: Facebook @cptne2',
    },
    {
        'company': 'Terra de Direitos',
        'email': 'comunicacao@terradedireitos.org.br',
        'phone': '',
        'notes': 'Terra de Direitos - Organizacao de direitos humanos com atuacao em direitos economicos, sociais, culturais e ambientais (DESCA). Site: terradedireitos.org.br. Social: Instagram @terradedireitos',
    },
    {
        'company': 'Rede Justica Criminal',
        'email': '',
        'phone': '',
        'notes': 'Rede Justica Criminal - Coalizao de organizacoes contra o encarceramento em massa e pela reforma do sistema de justica criminal. Site: redejusticacriminal.org. Social: Instagram @redejusticacriminal',
    },
    {
        'company': 'Fundacao Margarida Maria Alves (PB)',
        'email': '',
        'phone': '',
        'notes': 'Fundacao Margarida Maria Alves - Assessoria popular e direitos humanos no Nordeste. Referencia em direitos humanos na regiao. Social: Instagram @fundacaomargaridaalves',
    },
    {
        'company': 'OAB-PE - Comissao de Direitos Humanos (Ordem dos Advogados do Brasil - PE)',
        'email': '',
        'phone': '(81) 3424-8700',
        'notes': 'Comissao de Direitos Humanos da OAB - Seccional Pernambuco. Atuacao na defesa dos direitos humanos e combate a tortura no estado. Social: Instagram @oabpernambuco',
    },
    {
        'company': 'MDHC - Ministerio dos Direitos Humanos e da Cidadania',
        'email': '',
        'phone': 'Disque 100',
        'notes': 'Ministerio dos Direitos Humanos e da Cidadania do Brasil. Orgao federal responsavel pela formulacao de politicas de direitos humanos. Site: gov.br/mdh. Social: Instagram @mdhcbrasil, Facebook @mindireitoshumanos, Twitter @mdhcbrasil, YouTube @mdhcbrasil',
    },
    {
        'company': 'Freedom From Torture (London)',
        'email': '',
        'phone': '+44 (0)20 7697 7788',
        'vertical': 'UK',
        'notes': 'Freedom From Torture (formerly Medical Foundation). Reabilitacao de sobreviventes de tortura e documentacao forense. Social: Twitter @freefromtorture, Instagram @freedomfromtorture, Facebook @freedomfromtorture, YouTube @FreedomFromTorture',
    },
    {
        'company': 'FIDH - International Federation for Human Rights (Paris)',
        'email': '',
        'phone': '+33 1 43 55 25 18',
        'vertical': 'France',
        'notes': 'Federacao Internacional de Direitos Humanos (FIDH). Rede global de 184 organizacoes em 112 paises. Social: Twitter @fidh_en, Instagram @fidh, Facebook @FIDH.humanrights, LinkedIn /company/fidh',
    },
    {
        'company': 'UN HRC - United Nations Human Rights Council (Geneva)',
        'email': '',
        'phone': '',
        'vertical': 'Switzerland',
        'notes': 'Conselho de Direitos Humanos das Nacoes Unidas. Orgao intergovernamental da ONU. Social: Twitter @UN_HRC',
    },
    {
        'company': 'World Coalition Against the Death Penalty (Paris)',
        'email': '',
        'phone': '+33 1 43 55 25 18',
        'vertical': 'France',
        'notes': 'World Coalition Against the Death Penalty. Coalizao global contra a pena de morte. Social: Twitter @WCADP, Instagram @worldcoalitionagainstdeathpenalty, Facebook @WorldCoalition',
    },
    {
        'company': 'UN Human Rights - Regional Office for South America - ROSA (Santiago)',
        'email': 'rosa@ohchr.org',
        'phone': '',
        'vertical': 'Chile',
        'notes': 'Escritorio Regional do ACNUDH/OHCHR para a America do Sul. Sede em Santiago, Chile. Social: Twitter @UNHumanRights, Instagram @unhumanrights',
    },
    {
        'company': 'Tortura Nunca Mais - Grupo Tortura Nunca Mais (GTNM)',
        'email': '',
        'phone': '',
        'notes': 'Grupo Tortura Nunca Mais (GTNM). Movimento de memoria, verdade e justica contra a tortura no Brasil. Grupos estaduais em RJ, SP, PE, BA, MG, RS.',
    },
    {
        'company': 'OAB Nacional - Comissao Nacional de Direitos Humanos',
        'email': '',
        'phone': '(61) 2104-9000',
        'notes': 'Comissao Nacional de Direitos Humanos do Conselho Federal da OAB. Atuacao em direitos humanos, combate a tortura e violencia policial. Social: Instagram @oabnacional',
    },
]

inserted = 0
for c in new_contacts:
    contact_id = str(uuid.uuid4())
    vertical = c.get('vertical', 'Brazil')
    try:
        db.execute("""
            INSERT INTO leads (id, company, contact_name, email, phone, website, type, vertical, source, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'cold', ?)
        """, (
            contact_id,
            c['company'],
            '',
            c.get('email', ''),
            c.get('phone', ''),
            '',
            'Security',
            vertical,
            'web-research',
            c['notes'],
        ))
        inserted += 1
        em = c.get('email', '') or '-'
        print(f"  + {c['company'][:50]:50} | {em:30} | {c.get('phone', '') or '-'}")
    except Exception as e:
        print(f"  X Failed: {c['company'][:50]}: {e}")

db.commit()
db.close()
print(f'\nDone: Updated {updated} with social media, added {inserted} new institutions')
