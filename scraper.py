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

# Il tuo foglio specifico per la sanità
NOME_FOGLIO = "ricerca_mail_categoria_sanita'"
sheet = client.open(NOME_FOGLIO).sheet1

def estrazione_mirata_asl(url, categoria):
    print(f"Scansione intensiva ASL Pescara: {url}")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.asl.pe.it/'
    }
    try:
        # Aumentiamo il timeout perché le liste ASL possono essere pesanti
        res = requests.get(url, headers=headers, timeout=60)
        res.raise_for_status()
        
        # Regex per trovare tutte le email nel codice della pagina
        emails = re.findall(r'[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,4}', res.text)
        
        risultati = []
        for email in set(emails):
            email = email.lower()
            # Escludiamo email tecniche o PEC per dare al cliente solo i contatti diretti
            if not any(x in email for x in ['aruba', 'pec', 'legalmail', 'postacert', 'hosting']):
                nome = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
                risultati.append([
                    datetime.now().strftime("%d/%m/%Y"), 
                    nome, 
                    email, 
                    categoria, 
                    "PESCARA"
                ])
        return risultati
    except Exception as e:
        print(f"Errore durante la scansione di {url}: {e}")
        return []

# --- 2. LE TUE SORGENTI SPECIFICHE ---
targets = [
    ("https://www.asl.pe.it/ListaMedici.jsp", "MEDICI SPECIALISTI"),
    ("https://www.asl.pe.it/Sezione.jsp?idSezione=863", "MEDICI CONVENZIONATI")
]

# --- 3. ESECUZIONE E CARICAMENTO ---
accumulo_dati = []
for url, cat in targets:
    accumulo_dati.extend(estrazione_mirata_asl(url, cat))

if accumulo_dati:
    # Recuperiamo le email già presenti per evitare i famosi "43" duplicati
    email_esistenti = set(sheet.col_values(3))
    da_inserire = [d for d in accumulo_dati if d[2] not in email_esistenti]
    
    if da_inserire:
        # Carichiamo i dati a blocchi per sicurezza
        for i in range(0, len(da_inserire), 50):
            sheet.append_rows(da_inserire[i:i+50])
            print(f"Inseriti {len(da_inserire[i:i+50])} nuovi contatti...")
            time.sleep(1)
        print(f"COMPLETATO! Totale nuovi medici aggiunti: {len(da_inserire)}")
    else:
        print("Nessun nuovo contatto trovato rispetto a quelli già nel foglio.")
else:
    print("Il sito non ha restituito email. Potrebbe servire una ricerca manuale sui PDF.")
