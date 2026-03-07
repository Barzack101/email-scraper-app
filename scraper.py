

import os, re, time, random
import requests
import pdfplumber
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from datetime import datetime

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    SELENIUM_OK = True
except:
    SELENIUM_OK = False

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36',
]

EMAIL_PATTERN = r'[a-zA-Z0-9.\-_+]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,6}'
DOMINI_ESCLUDI = [
    'example.com','noreply','no-reply','privacy','dpo@','webmaster','sentry',
    'w3.org','schema.org','googleapis','jquery','bootstrap','cloudflare',
    'facebook','twitter','youtube','google.','microsoft','apple.com','wix',
    'wordpress','jsdelivr','cdnjs','fontawesome','gstatic','doubleclick',
]

def is_email_valida(email):
    el = email.lower()
    if any(x in el for x in DOMINI_ESCLUDI): return False
    if len(email) < 8: return False
    if el.endswith(('.js','.css','.png','.jpg','.svg','.php')): return False
    if el.count('@') != 1: return False
    return True

def crea_browser():
    if not SELENIUM_OK: return None
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_argument(f'--user-agent={random.choice(USER_AGENTS)}')
    options.add_argument('--window-size=1920,1080')
    try:
        driver = webdriver.Chrome(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    except Exception as e:
        print(f'Browser non disponibile: {e}')
        return None

def cerca_email_google(nome, specializzazione, provincia, driver):
    if not driver: return None
    query = f'"{nome}" {specializzazione.lower()} {provincia.lower()} email contatti'
    url = f'https://www.google.com/search?q={query.replace(" ", "+")}'
    try:
        driver.get(url)
        time.sleep(random.uniform(3, 5))
        testo = driver.page_source
        emails = re.findall(EMAIL_PATTERN, testo)
        for email in emails:
            email = email.lower().strip('.')
            if is_email_valida(email):
                return email
    except Exception as e:
        print(f'    Errore Google: {e}')
    return None

def cerca_email_sito(nome, specializzazione, provincia, driver):
    if not driver: return None
    urls = [
        f'https://www.dottori.it/cerca?q={nome.replace(" ", "+")}&city={provincia.lower()}',
        f'https://www.miodottore.it/cerca?q={nome.replace(" ", "+")}',
    ]
    for url in urls:
        try:
            driver.get(url)
            time.sleep(random.uniform(2, 4))
            testo = driver.page_source
            if nome.split()[0].lower() in testo.lower():
                emails = re.findall(EMAIL_PATTERN, testo)
                for email in emails:
                    email = email.lower().strip('.')
                    if is_email_valida(email):
                        return email
        except:
            pass
    return None

# ============================================================
# STEP 1: Estrai medici dal PDF
# ============================================================
print('='*60)
print('STEP 1: Estrazione medici dal PDF ufficiale')
print('='*60)

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

# ============================================================
# STEP 2: Cerca email per ogni medico
# ============================================================
print('\n' + '='*60)
print('STEP 2: Ricerca email per ogni medico')
print('='*60)

print('Avvio browser...')
driver = crea_browser()
print('Browser OK' if driver else 'Solo requests disponibile')

risultati = []
trovate_count = 0

for i, medico in enumerate(medici_pdf):
    nome = medico['nome']
    spec = medico['specializzazione']
    asl = medico['asl']
    
    print(f'[{i+1}/{len(medici_pdf)}] {nome} - {spec}', end=' ... ')
    
    email = None
    if driver:
        email = cerca_email_sito(nome, spec, asl, driver)
    if not email and driver:
        email = cerca_email_google(nome, spec, asl, driver)
    
    if email:
        trovate_count += 1
        print(f'TROVATA: {email}')
    else:
        print('non trovata')
    
    risultati.append({
        'nome': nome,
        'email': email or '',
        'specializzazione': spec,
        'provincia': asl,
        'fonte': 'Bollettino Ufficiale Regione Abruzzo 2026'
    })
    
    time.sleep(random.uniform(2, 4))
    
    if (i + 1) % 50 == 0:
        print(f'\n>>> Checkpoint: {trovate_count} email trovate su {i+1} medici\n')

if driver:
    driver.quit()

print(f'\nEmail trovate: {trovate_count}/{len(medici_pdf)}')

# ============================================================
# STEP 3: Unione con email esistenti
# ============================================================
print('\n' + '='*60)
print('STEP 3: Unione con email esistenti')
print('='*60)

email_esistenti = []
for excel_path in ['email_sanitari_abruzzo_07032026.xlsx']:
    if os.path.exists(excel_path):
        wb_old = load_workbook(excel_path)
        ws_old = wb_old.active
        for row in ws_old.iter_rows(min_row=2, values_only=True):
            if row[2]:
                email_esistenti.append({
                    'nome': row[1] or '',
                    'email': row[2],
                    'specializzazione': row[3] or '',
                    'provincia': row[4] or '',
                    'fonte': 'Scraper automatico'
                })
        print(f'Caricate {len(email_esistenti)} email esistenti')

tutte_email = set()
finali = []

for r in email_esistenti:
    if r['email'] and r['email'] not in tutte_email:
        tutte_email.add(r['email'])
        finali.append(r)

for r in risultati:
    if r['email'] and r['email'] not in tutte_email:
        tutte_email.add(r['email'])
        finali.append(r)
    elif not r['email']:
        finali.append(r)

print(f'Totale record: {len(finali)} | Con email: {sum(1 for r in finali if r["email"])}')

# ============================================================
# STEP 4: Crea Excel finale
# ============================================================
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

for r in finali:
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
