import os, re, time, random
import requests
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from datetime import datetime

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36',
]

def get_headers():
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'it-IT,it;q=0.9',
    }

def pausa():
    time.sleep(random.uniform(2, 4))

EMAIL_PATTERN = r'[a-zA-Z0-9.\-_+]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,6}'

DOMINI_ESCLUDI = [
    'example.com','noreply','no-reply','privacy','webmaster',
    'sentry','w3.org','schema.org','googleapis','facebook',
    'twitter','youtube','google.','microsoft','apple.com',
    'wordpress','fontawesome','gstatic',
]

def is_email_valida(email):
    el = email.lower()
    if any(x in el for x in DOMINI_ESCLUDI): return False
    if len(email) < 8: return False
    if el.endswith(('.js','.css','.png','.jpg','.svg','.php')): return False
    return True

# Città italiane principali
CITTA = [
    'Milano', 'Roma', 'Napoli', 'Torino', 'Bologna', 'Firenze',
    'Venezia', 'Genova', 'Palermo', 'Bari', 'Pescara', 'Chieti',
    'Teramo', "L'Aquila", 'Ancona', 'Perugia', 'Verona', 'Padova',
    'Trieste', 'Brescia', 'Modena', 'Parma', 'Reggio Emilia', 'Catania'
]

# Tipi di agenzie da cercare
TIPI_AGENZIA = [
    'agenzia comunicazione',
    'agenzia marketing',
    'agenzia eventi',
    'agenzia pubblicitaria',
    'agenzia digital marketing',
    'studio comunicazione',
]

agenzie = []
email_set = set()

print('='*60)
print('RICERCA AGENZIE MARKETING E COMUNICAZIONE - ITALIA')
print(f'Inizio: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}')
print('='*60)

for tipo in TIPI_AGENZIA:
    for citta in CITTA:
        query = f'{tipo} {citta} email contatti'
        url = f'https://www.google.com/search?q={query.replace(" ", "+")}'
        
        print(f'  Cerco: {tipo} - {citta}')
        
        try:
            res = requests.get(url, headers=get_headers(), timeout=20)
            testo = res.text
            
            # Estrai email
            emails_trovate = re.findall(EMAIL_PATTERN, testo)
            
            # Estrai nomi agenzia (cerca tag title e h3)
            titoli = re.findall(r'<h3[^>]*>([^<]+)</h3>', testo)
            
            for email in emails_trovate:
                email = email.lower().strip('.')
                if not is_email_valida(email): continue
                if email in email_set: continue
                email_set.add(email)
                
                # Cerca il nome agenzia vicino all'email
                idx = testo.find(email)
                contesto = testo[max(0,idx-300):idx+300]
                contesto_pulito = re.sub(r'<[^>]+>', ' ', contesto)
                
                agenzie.append({
                    'nome': contesto_pulito[:60].strip(),
                    'email': email,
                    'tipo': tipo.title(),
                    'citta': citta,
                    'linkedin': f'https://www.linkedin.com/search/results/companies/?keywords={tipo.replace(" ", "%20")}%20{citta.replace(" ", "%20")}',
                    'google': f'https://www.google.com/search?q={tipo.replace(" ", "+")}+{citta.replace(" ", "+")}'
                })
                print(f'    ✓ {email} - {citta}')
        
        except Exception as e:
            print(f'    Errore: {e}')
        
        pausa()

print(f'\nTOTALE AGENZIE TROVATE: {len(agenzie)}')

# Crea Excel
wb = Workbook()
ws = wb.active
ws.title = "Agenzie da Contattare"

header_fill = PatternFill(start_color='1a3a5c', end_color='1a3a5c', fill_type='solid')
header_font = Font(bold=True, color='FFFFFF', size=11)
green_fill = PatternFill(start_color='d4edda', end_color='d4edda', fill_type='solid')
yellow_fill = PatternFill(start_color='fff3cd', end_color='fff3cd', fill_type='solid')

intestazioni = ['#', 'Nome/Contesto', 'Email', 'Tipo Agenzia', 'Città', 'Stato', 'LinkedIn', 'Google', 'Note']

for col, titolo in enumerate(intestazioni, 1):
    cella = ws.cell(row=1, column=col, value=titolo)
    cella.font = header_font
    cella.fill = header_fill
    cella.alignment = Alignment(horizontal='center')

ws.row_dimensions[1].height = 22
ws.freeze_panes = 'A2'

for i, a in enumerate(agenzie, 1):
    row = i + 1
    ws.cell(row=row, column=1, value=i).fill = green_fill
    ws.cell(row=row, column=2, value=a['nome']).fill = green_fill
    ws.cell(row=row, column=3, value=a['email']).fill = green_fill
    ws.cell(row=row, column=4, value=a['tipo']).fill = green_fill
    ws.cell(row=row, column=5, value=a['citta']).fill = green_fill
    
    # Colonna stato (da compilare manualmente)
    stato = ws.cell(row=row, column=6, value='Da contattare')
    stato.fill = yellow_fill
    stato.font = Font(bold=True)
    
    # Link LinkedIn
    li = ws.cell(row=row, column=7, value='LinkedIn')
    li.hyperlink = a['linkedin']
    li.font = Font(color='0A66C2', underline='single')
    li.fill = green_fill
    
    # Link Google
    g = ws.cell(row=row, column=8, value='Google')
    g.hyperlink = a['google']
    g.font = Font(color='0563C1', underline='single')
    g.fill = green_fill
    
    ws.cell(row=row, column=9, value='').fill = green_fill

# Larghezze
ws.column_dimensions['A'].width = 5
ws.column_dimensions['B'].width = 35
ws.column_dimensions['C'].width = 35
ws.column_dimensions['D'].width = 25
ws.column_dimensions['E'].width = 15
ws.column_dimensions['F'].width = 18
ws.column_dimensions['G'].width = 12
ws.column_dimensions['H'].width = 12
ws.column_dimensions['I'].width = 25

nome_file = f'agenzie_da_contattare_{datetime.now().strftime("%d%m%Y")}.xlsx'
wb.save(nome_file)
print(f'\nFile salvato: {nome_file}')
print(f'Totale agenzie: {len(agenzie)}')
