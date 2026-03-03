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

def estrai_asl_regionale(url, categoria, provincia):
    print(f"Scansione: {categoria} - {provincia}...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
    try:
        res = requests.get(url, headers=headers, timeout=45)
        emails = re.findall(r'[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,4}', res.text)
        
        nuovi = []
        for email in set(emails):
            email = email.lower()
            if not any(x in email for x in ['aruba', 'pec', 'legalmail', 'postacert']):
                nome = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
                nuovi.append([datetime.now().strftime("%d/%m/%Y"), nome, email, categoria, provincia])
        return nuovi
    except: return []

# --- 2. MAPPA DEI DATABASE ABRUZZESI ---
targets = [
    # PESCARA (I tuoi link vincenti)
    ("https://www.asl.pe.it/ListaMedici.jsp", "SPECIALISTI", "PESCARA"),
    ("https://www.asl.pe.it/Sezione.jsp?idSezione=863", "CONVENZIONATI", "PESCARA"),
    
    # CHIETI / VASTO / LANCIANO
    ("https://www.asl2abruzzo.it/contatti.html", "MEDICI ASL", "CHIETI"),
    ("https://www.asl2abruzzo.it/area-riservata/servizi-online/medici-e-pediatri.html", "PEDIATRI/BASE", "CHIETI"),
    
    # L'AQUILA / AVEZZANO / SULMONA
    ("https://www.asl1abruzzo.it/index.php/medici-e-pediatri", "SPECIALISTI", "L'AQUILA"),
    ("https://www.asl1abruzzo.it/index.php/contatti", "UFFICI MEDICI", "L'AQUILA"),
    
    # TERAMO
    ("https://www.aslteramo.it/servizi/medici-e-pediatri-di-famiglia/", "MEDICI DI BASE", "TERAMO"),
    ("https://www.aslteramo.it/trasparenza/personale/personale-non-a-tempo-indeterminato/", "SPECIALISTI", "TERAMO"),
    
    # REGIONE ABRUZZO (Il portale unico)
    ("https://sanita.regione.abruzzo.it/canale-medici", "ELENCO REGIONALE", "ABRUZZO")
]

# --- 3. ESECUZIONE ---
accumulo_totale = []
for url, cat, prov in targets:
    accumulo_totale.extend(estrai_asl_regionale(url, cat, prov))

if accumulo_totale:
    email_esistenti = set(sheet.col_values(3))
    da_inserire = [d for d in accumulo_totale if d[2] not in email_esistenti]
    
    if da_inserire:
        for i in range(0, len(da_inserire), 50):
            sheet.append_rows(da_inserire[i:i+50])
            time.sleep(1)
        print(f"LAVORO COMPLETATO! Aggiunti {len(da_inserire)} nuovi contatti.")
