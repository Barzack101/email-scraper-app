import os
import json
import gspread
import requests
import re
import time
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- 1. CONFIGURAZIONE ---
creds_json = os.getenv('GOOGLE_CREDENTIALS')
info = json.loads(creds_json)
creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
client = gspread.authorize(creds)
sheet = client.open("ricerca_mail_categoria_sanita'").sheet1

def estrazione_documenti(url, cat, prov):
    print(f"Scansione database su: {url}")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        # Carichiamo la pagina cercando liste massive
        res = requests.get(url, headers=headers, timeout=45)
        # Cerchiamo email ovunque nel codice della pagina
        emails = re.findall(r'[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,4}', res.text)
        
        nuovi = []
        for email in set(emails):
            email = email.lower()
            if not any(x in email for x in ['aruba', 'pec', 'legalmail', 'postacert']):
                nome = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
                nuovi.append([datetime.now().strftime("%d/%m/%Y"), nome, email, cat, prov])
        return nuovi
    except:
        return []

# --- 2. LE SORGENTI "APERTE" (Portali con elenchi lunghi) ---
# Ho inserito i portali che solitamente non bloccano i bot e hanno liste testuali
targets = [
    ("https://www.regione.abruzzo.it/content/elenco-medici-e-pediatri", "MEDICI REGIONE", "ABRUZZO"),
    ("https://www.aslpe.it/pagine.zhtml?id=123", "MEDICI ASL", "PESCARA"),
    ("https://www.asl2abruzzo.it/area-riservata/servizi-online/medici-e-pediatri.html", "MEDICI ASL", "CHIETI"),
    ("https://www.elencofarmacie.it/abruzzo", "FARMACIE", "ABRUZZO"),
    ("https://www.paginegialle.it/abruzzo/medici-specialisti.html", "SPECIALISTI", "ABRUZZO"),
    ("https://www.paginegialle.it/abruzzo/farmacie.html", "FARMACIE", "ABRUZZO")
]

# --- 3. ESECUZIONE ---
dati_accumulati = []
for url, cat, prov in targets:
    dati_accumulati.extend(estrazione_documenti(url, cat, prov))

if dati_accumulati:
    email_esistenti = set(sheet.col_values(3))
    da_inviare = [d for d in dati_accumulati if d[2] not in email_esistenti]
    
    if da_inviare:
        # Carichiamo i dati a blocchi di 50 per evitare errori di timeout
        for i in range(0, len(da_inviare), 50):
            sheet.append_rows(da_inviare[i:i+50])
            time.sleep(2)
        print(f"SUCCESSO! Aggiunti {len(da_inviare)} contatti.")
    else:
        print("Nessun nuovo contatto trovato rispetto ai 43.")
