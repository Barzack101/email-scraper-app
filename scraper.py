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
NOME_FOGLIO = "ricerca_mail_categoria_sanita'"
sheet = client.open(NOME_FOGLIO).sheet1

def estrazione_diretta(url, categoria, provincia):
    print(f"Scansione mirata: {categoria} - {provincia}")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    trovate = []
    try:
        res = requests.get(url, headers=headers, timeout=30)
        # Cerchiamo tutte le email
        emails = re.findall(r'[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,4}', res.text)
        for email in list(set(emails)):
            email = email.lower()
            if not any(x in email for x in ['aruba', 'legalmail', 'pec', 'info@', 'servizi']):
                # Se non è una PEC, è probabilmente l'email del medico
                nome = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
                trovate.append([datetime.now().strftime("%d/%m/%Y"), nome, email, categoria, provincia])
    except:
        pass
    return trovate

# --- 2. BERSAGLI: CLINICHE E DISTRETTI (Dove i medici sono tanti) ---
targets = [
    ("https://www.aslpe.it/pagine.zhtml?id=123", "Medici Ospedalieri", "PESCARA"),
    ("https://www.asl2abruzzo.it/area-riservata/servizi-online.html", "Medici ASL", "CHIETI"),
    ("https://www.casadicurapierangeli.it/i-nostri-medici", "Specialisti", "PESCARA"),
    ("https://www.clinicaspatocco.it/i-nostri-medici", "Specialisti", "CHIETI"),
    ("https://www.villaserenapescara.it/medici", "Specialisti", "PESCARA"),
    ("https://www.asl1abruzzo.it/index.php/contatti", "Medici ASL", "L'AQUILA"),
    ("https://www.aslteramo.it/servizi/medici-e-pediatri-di-famiglia/", "Pediatri/Base", "TERAMO")
]

# --- 3. ESECUZIONE ---
dati_finali = []
for url, cat, prov in targets:
    dati_finali.extend(estrazione_diretta(url, cat, prov))

if dati_finali:
    email_esistenti = set(sheet.col_values(3))
    da_inviare = [d for d in dati_finali if d[2] not in email_esistenti]
    if da_inviare:
        sheet.append_rows(da_inviare)
        print(f"Fatto! Aggiunti {len(da_inviare)} contatti.")
    else:
        print("Nessun nuovo contatto trovato.")
