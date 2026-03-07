import os, re, time, random
import requests
import pdfplumber
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from datetime import datetime

SNOV_CLIENT_ID = os.getenv('SNOV_CLIENT_ID', '')
SNOV_CLIENT_SECRET = os.getenv('SNOV_CLIENT_SECRET', '')

def get_snov_token():
    try:
        res = requests.post('https://api.snov.io/v1/oauth/access_token', data={
            'grant_type': 'client_credentials',
            'client_id': SNOV_CLIENT_ID,
            'client_secret': SNOV_CLIENT_SECRET
        }, timeout=10)
        return res.json().get('access_token')
    except Exception as e:
        print(f'Errore token Snov: {e}')
        return None

def cerca_email_snov(nome, cognome, token):
    if not token: return None
    try:
        res = requests.post('https://api.snov.io/v1/get-emails-from-name', json={
            'firstName': nome,
            'lastName': cognome,
            'domain': 'gmail.com'
        }, headers={'Authorization': f'Bearer {token}'}, timeout=15)
        data = res.json()
        emails = data.get('emails', [])
        if emails:
            return emails[0].get('email')
    except Exception as e:
        print(f'    Snov error: {e}')
    return None

SPECIALIZZAZIONI_PDF = [
    'ALLERGOLOGIA', 'AUDIOLOGIA E FONATRIA', 'BIOLOGIA', 'CARDIOLOGIA',
    'CHIRURGIA GENERALE', 'CHIRURGIA PLASTICA', 'CHIRURGIA VASCOLARE',
    'DERMATOLOGIA', 'DIABETOLOGIA', 'EMATOLOGIA', 'ENDOCRINOLOGIA',
    'FISIOCHINESITERAPIA', 'GASTROENTEROLOGIA', 'GERIATRIA',
    'MEDICINA DEL LAVORO', 'MEDICINA DELLO SPORT', 'MEDICINA INTERNA',
    'MEDICINA LEGALE', 'NEFROLOGIA', 'NEUROLOGIA', 'NEUROPSICHIATRIA INFANTILE',
    'OCULISTICA', 'ODONTOIATRIA', 'ORTOPEDIA', 'OSTETRICIA E GINECOLOGIA',
    'OTORINOLARINGOIATRIA', 'PEDIATRIA', 'PNEUMOLOGIA', 'PSICHIATRIA',
    'RADIOLOGIA', 'REUMATOLOGIA', 'UROLOGIA', 'ONCOLOGIA',
    'ANESTESIA', 'ANATOMIA PATOLOGICA', 'PSICOLOGIA'
]

SKIP_WORDS = [
    'COGNOME', 'NOME', 'PUNTEGGIO', 'SPECIALE', 'BOLLETTINO', 'REGIONE',
    'ABRUZZO', 'AZIENDA', 'SANITARIA', 'PESCARA', 'TERAMO', 'CHIETI',
    'AQUILA', 'AVEZZANO', 'SULMONA', 'LANCIANO', 'VASTO', 'DELIBERAZIONE',
    'DIRETTORE', 'GENERALE', 'GRADUATORIE', 'ESCLUSI', 'MOTIVAZIONE',
    'BRANCA', 'SEDE', 'LEGALE', 'RENATO', 'PAOLINI', 'VESTINI', 'DIRIGENTE',
    'RESPONSABILE', 'CONVENZIONATI', 'GESTIONE', 'SANITARI', 'APPROVAZIONE',
    'DEFINITIVE', 'VALEVOLI', 'ANNO', 'POWERED', 'TCPDF', 'ITALIANA',
    'UFFICIALE', 'DICEMBRE', 'GENNAIO', 'FEBBRAIO', 'MARZO', 'APRILE',
]

print('='*60)
print('STEP 1: Estrazione medici dal PDF ufficiale')
print('='*60)

medici_pdf = []
seen = set()
current_spec = None
current_asl = 'PESCARA'

with pdfplumber.open('bollettino-speciale-numero-288-del-31-12-2025.pdf') as pdf:
    for page_num, page in enumerate(pdf.pages):
        words = page.extract_words()
        text = ' '.join([w['text'] for w in words])
        text_upper = text.upper()

        if 'ASL PESCARA' in text_upper and page_num > 40:
            current_asl = 'PESCARA'
        if 'LANCIANO' in text_upper and 'CHIETI' in text_upper:
            current_asl = 'CHIETI'
        if 'AVEZZANO' in text_upper and 'SULMONA' in text_upper:
            current_asl = "L'AQUILA"
        if 'ASL TERAMO' in text_upper or ('TERAMO' in text_upper and 'DELIBERAZIONE' in text_upper):
            current_asl = 'TERAMO'

        best_spec = None
        best_len = 0
        for spec in SPECIALIZZAZIONI_PDF:
            if spec in text_upper and len(spec) > best_len:
                best_spec = spec
                best_len = len(spec)
        if best_spec:
            current_spec = best_spec

        pattern = r'([A-Z][A-ZÀÈÉÌÒÙ\']+(?:\s+[A-ZÀÈÉÌÒÙ][A-ZÀÈÉÌÒÙ\']+){1,3})\s+(\d+[\.,]\d+)'
        for match in re.finditer(pattern, text):
            nome_raw = match.group(1).strip()
            parole = nome_raw.split()
            if len(parole) < 2 or len(parole) > 4: continue
            if any(sw in nome_raw for sw in SKIP_WORDS): continue
            if len(nome_raw) < 8: continue
            key = (nome_raw, current_spec, current_asl)
            if key in seen: continue
            seen.add(key)
            if current_spec:
                medici_pdf.append({
                    'nome': nome_raw,
                    'specializzazione': current_spec,
                    'asl': current_asl
                })

print(f'Estratti {len(medici_pdf)} medici dal PDF')

print('\n' + '='*60)
print('STEP 2: Ricerca email con Snov.io')
print('='*60)

token = get_snov_token()
print(f'Token Snov: {"OK" if token else "ERRORE"}')

risultati = []
trovate_count = 0

for i, medico in enumerate(medici_pdf):
    nome_completo = medico['nome']
    spec = medico['specializzazione']
    asl = medico['asl']

    parole = nome_completo.split()
    cognome = parole[0]
    nome = ' '.join(parole[1:]) if len(parole) > 1 else parole[0]

    print(f'[{i+1}/{len(medici_pdf)}] {nome_completo} - {spec}', end=' ... ')

    email = cerca_email_snov(nome, cognome, token)

    if email:
        trovate_count += 1
        print(f'TROVATA: {email}')
    else:
        print('non trovata')

    risultati.append({
        'nome': nome_completo,
        'email': email or '',
        'specializzazione': spec,
        'provincia': asl,
        'fonte': 'Bollettino Ufficiale Regione Abruzzo 2026'
    })

    time.sleep(0.5)

    if (i + 1) % 50 == 0:
        print(f'\n>>> Checkpoint: {trovate_count} email trovate su {i+1} medici\n')

print(f'\nEmail trovate: {trovate_count}/{len(medici_pdf)}')

print('\n' + '='*60)
print('STEP 3: Creazione Excel finale')
print('='*60)

wb = Workbook()
ws1 = wb.active
ws1.title = "Con Email"
ws2 = wb.create_sheet("Tutti i Medici")

header_fill = PatternFill(start_color='1a3a5c', end_color='1a3a5c', fill_type='solid')
header_font = Font(bold=True, color='FFFFFF', size=11)
green_fill = PatternFill(start_color='d4edda', end_color='d4edda', fill_type='solid')
gray_fill = PatternFill(start_color='f8f9fa', end_color='f8f9fa', fill_type='solid')

intestazioni = ['Data', 'Nome Completo', 'Email', 'Specializzazione', 'Provincia', 'Fonte']

for ws in [ws1, ws2]:
    for col, titolo in enumerate(intestazioni, 1):
        cella = ws.cell(row=1, column=col, value=titolo)
        cella.font = header_font
        cella.fill = header_fill
        cella.alignment = Alignment(horizontal='center')
    ws.row_dimensions[1].height = 22
    ws.freeze_panes = 'A2'

oggi = datetime.now().strftime('%d/%m/%Y')
riga1 = 2
riga2 = 2

for r in risultati:
    fill = green_fill if r['email'] else gray_fill
    row_data = [oggi, r['nome'], r['email'], r['specializzazione'], r['provincia'], r['fonte']]
    for col, val in enumerate(row_data, 1):
        ws2.cell(row=riga2, column=col, value=val).fill = fill
    riga2 += 1
    if r['email']:
        for col, val in enumerate(row_data, 1):
            ws1.cell(row=riga1, column=col, value=val).fill = green_fill
        riga1 += 1

for ws in [ws1, ws2]:
    ws.column_dimensions['A'].width = 12
    ws.column_dimensions['B'].width = 30
    ws.column_dimensions['C'].width = 38
    ws.column_dimensions['D'].width = 35
    ws.column_dimensions['E'].width = 15
    ws.column_dimensions['F'].width = 30

nome_file = f'medici_abruzzo_completo_{datetime.now().strftime("%d%m%Y")}.xlsx'
wb.save(nome_file)
print(f'\nFile salvato: {nome_file}')
print(f'Foglio "Con Email": {riga1-2} contatti')
print(f'Foglio "Tutti i Medici": {riga2-2} record totali')
