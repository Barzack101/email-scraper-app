import os
import json
import gspread
import requests
import re
import time
from datetime import datetime
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials

# --- 1. CONFIGURAZIONE ---
creds_json = os.getenv('GOOGLE_CREDENTIALS')
info = json.loads(creds_json)
creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
client = gspread.authorize(creds)
NOME_FOGLIO = "ricerca_mail_categoria_sanita'"
sheet = client.open(NOME_FOGLIO).sheet1

def cerca_email_profondo(url_base, categoria, provincia):
    print(f"Investigando {categoria} a {provincia}...")
    trovate = set()
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url_base, headers=headers, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 1. Cerca nella pagina principale
        trovate.update(re.findall(r'[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,4}', res.text))
        
        # 2. Trova link interni (Albo, Iscritti, Contatti)
        links = []
        parole_chiave = ['albo', 'iscritti', 'elenco', 'contatt', 'anagrafica', 'specialisti']
        for a in soup.find_all('a', href=True):
            if any(p in a.text.lower() for p in parole_chiave) or any(p in a['href'].lower() for p in parole_chiave):
                links.append(urljoin(url_base, a['href']))
        
        # 3. Scansiona le prime 15 sottopagine trovate
        for link in list(set(links))[:15]:
            try:
                sub_res = requests.get(link, headers=headers, timeout=10)
                trovate.update(re.findall(r'[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,4}', sub_res.text))
                time.sleep(0.5)
            except: continue
    except: pass
    
    risultati_finali = []
    for email in trovate:
        if not email.endswith(('.png', '.jpg', '.pdf', '.gif', '.svg')):
            nome = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
            risultati_finali.append([datetime.now().strftime("%d/%m/%Y"), nome, email.lower(), categoria, provincia])
    return risultati_finali

# --- 2. BERSAGLI (Aggiornati per massimizzare i risultati) ---
targets = [
    ("https://www.ordinemedicipescara.it", "Medici", "PESCARA"),
    ("https://www.ordinemedicichieti.it", "Medici", "CHIETI"),
    ("https://www.ordinemediciteramo.it", "Medici", "TERAMO"),
    ("https://www.ordinemedicilaquila.it", "Medici", "L'AQUILA"),
    ("https://www.ordinemediciveterinaripe.it", "Veterinari", "PESCARA"),
    ("https://www.ordinefarmacistipescara.it", "Farmacisti", "PESCARA"),
    ("https://www.paginegialle.it/abruzzo/medici-specialisti.html", "Specialisti", "ABRUZZO"),
    ("https://www.paginegialle.it/abruzzo/farmacie.html", "Farmacie", "ABRUZZO")
]

# --- 3. ESECUZIONE ---
nuovi = []
for url, cat, prov in targets:
    nuovi.extend(cerca_email_profondo(url, cat, prov))

if nuovi:
    email_esistenti = set(sheet.col_values(3))
    da_inserire = [n for n in nuovi if n[2] not in email_esistenti]
    if da_inserire:
        sheet.append_rows(da_inserire)
        print(f"Boom! Trovati {len(da_inserire)} nuovi contatti.")
