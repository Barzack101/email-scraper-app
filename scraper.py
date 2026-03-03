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

def estrazione_massiva(url, cat, prov):
    print(f"Tentativo di scarico massivo su: {url}")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
    try:
        # Aumentiamo il timeout per scaricare liste lunghe
        res = requests.get(url, headers=headers, timeout=40)
        emails = re.findall(r'[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,4}', res.text)
        
        risultati = []
        for email in set(emails):
            email = email.lower()
            if not any(x in email for x in ['aruba', 'pec', 'postacert', 'legalmail']):
                nome = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
                risultati.append([datetime.now().strftime("%d/%m/%Y"), nome, email, cat, prov])
        return risultati
    except:
        return []

# --- 2. LE "SORGENTI" REGIONALI E ISTITUZIONALI ---
# Questi siti contengono spesso elenchi lunghissimi in una sola pagina
targets = [
    # Liste Medici e Pediatri ASL Abruzzo (Trasparenza)
    ("https://sanita.regione.abruzzo.it/canale-medici", "MEDICI REGIONE", "ABRUZZO"),
    ("https://www.asl1abruzzo.it/index.php/medici-e-pediatri", "PEDIATRI/BASE", "L'AQUILA"),
    ("https://www.asl2abruzzo.it/contatti/centri-unici-di-prenotazione-cup.html", "SPECIALISTI", "CHIETI"),
    ("https://www.aslpe.it/pagine.zhtml?id=123", "MEDICI ASL", "PESCARA"),
    
    # Portali con elenchi specialistici molto lunghi
    ("https://www.elencofarmacie.it/abruzzo", "FARMACIE", "ABRUZZO"),
    ("https://www.paginegialle.it/abruzzo/medici-specialisti.html", "SPECIALISTI", "ABRUZZO"),
    ("https://www.aziendeabruzzo.it/settore/sanita", "AZIENDE SANITARIE", "ABRUZZO")
]

# --- 3. ESECUZIONE ---
accumulo = []
for url, cat, prov in targets:
    accumulo.extend(estrazione_massiva(url, cat, prov))

if accumulo:
    # Recuperiamo solo la colonna delle email per il controllo duplicati
    email_esistenti = set(sheet.col_values(3))
    da_inserire = [a for a in accumulo if a[2] not in email_esistenti]
    
    if da_inserire:
        # Inseriamo a blocchi per non sovraccaricare Google Sheets
        sheet.append_rows(da_inserire)
        print(f"SUCCESSO! Trovati {len(da_inserire)} nuovi contatti.")
    else:
        print("Nessun nuovo contatto trovato rispetto ai 43 precedenti.")
