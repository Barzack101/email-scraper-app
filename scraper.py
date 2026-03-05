import os
import json
import requests
import re
import gspread
import time
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- CONFIGURAZIONE ---
creds_json = os.getenv('GOOGLE_CREDENTIALS')
info = json.loads(creds_json)
creds = Credentials.from_service_account_info(info, 
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
client = gspread.authorize(creds)
sheet = client.open("ricerca_mail_categoria_sanita'").sheet1

def scansione_massiva(url, cat, prov):
    print(f"Scansione profonda: {prov} - {cat}")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
    try:
        res = requests.get(url, headers=headers, timeout=20)
        # Cerchiamo email ovunque nel codice della pagina
        emails = re.findall(r'[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,4}', res.text)
        
        nuovi = []
        for e in set(emails):
            e = e.lower()
            if not any(x in e for x in ['aruba', 'pec', 'legalmail', 'sentry', 'wix']):
                nome = e.split('@')[0].replace('.', ' ').replace('_', ' ').title()
                nuovi.append([datetime.now().strftime("%d/%m/%Y"), nome, e, cat, prov])
        return nuovi
    except:
        return []

# --- BERSAGLI AD ALTO VOLUME (Tutto l'Abruzzo) ---
# Questi link puntano a elenchi che spesso contengono centinaia di nomi
targets = [
    ("https://sanita.regione.abruzzo.it/canale-medici", "REGIONALE", "ABRUZZO"),
    ("https://www.asl.pe.it/ListaMedici.jsp", "SPECIALISTI", "PESCARA"),
    ("https://www.asl2abruzzo.it/contatti/centri-unici-di-prenotazione-cup.html", "CUP/SPECIALISTI", "CHIETI"),
    ("https://www.asl1abruzzo.it/index.php/medici-e-pediatri", "BASE", "L'AQUILA"),
    ("https://www.aslteramo.it/servizi/medici-e-pediatri-di-famiglia/", "BASE", "TERAMO"),
    ("https://www.clinicaspatocco.it/i-nostri-medici", "PRIVATO", "CHIETI"),
    ("https://www.villaserenapescara.it/medici", "PRIVATO", "PESCARA")
]

# ESECUZIONE
dati_finali = []
for url, cat, prov in targets:
    risultati = scansione_massiva(url, cat, prov)
    dati_finali.extend(risultati)
    time.sleep(1)

if dati_finali:
    email_esistenti = set(sheet.col_values(3))
    da_inviare = [d for d in dati_finali if d[2] not in email_esistenti]
    
    if da_inviare:
        print(f"SBLOCCATI {len(da_inviare)} NUOVI CONTATTI!")
        for i in range(0, len(da_inviare), 50):
            sheet.append_rows(da_inviare[i:i+50])
            time.sleep(1)
    else:
        print("Nessun nuovo contatto trovato. I database sono già stati scaricati.")
