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

def cerca_lead_sanita(url, categoria, provincia):
    print(f"Rastrellamento intensivo: {categoria} a {provincia}...")
    nuovi_scovati = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        res = requests.get(url, headers=headers, timeout=25)
        # Cerchiamo blocchi di testo che contengono email
        emails = re.findall(r'[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,4}', res.text)
        
        for email in list(set(emails)):
            if not email.endswith(('.png', '.jpg', '.pdf', '.gif', '.svg')):
                # Creiamo Nome e Cognome dall'email
                nome_proposta = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
                nuovi_scovati.append([datetime.now().strftime("%d/%m/%Y"), nome_proposta, email.lower(), categoria, provincia])
    except:
        pass
    return nuovi_scovati

# --- 2. BERSAGLI AD ALTA DENSITÀ (Portali di Ricerca) ---
targets = [
    # ELENCHI SPECIALISTI ABRUZZO
    ("https://www.paginegialle.it/abruzzo/medici-specialisti.html", "SPECIALISTI", "ABRUZZO"),
    ("https://www.paginegialle.it/pescara/medici-specialisti.html", "SPECIALISTI", "PESCARA"),
    ("https://www.paginegialle.it/chieti/medici-specialisti.html", "SPECIALISTI", "CHIETI"),
    ("https://www.paginegialle.it/teramo/medici-specialisti.html", "SPECIALISTI", "TERAMO"),
    ("https://www.paginegialle.it/laquila/medici-specialisti.html", "SPECIALISTI", "L'AQUILA"),
    
    # FARMACIE E PEDIATRI (Molto facili da trovare)
    ("https://www.paginegialle.it/abruzzo/farmacie.html", "FARMACIE", "ABRUZZO"),
    ("https://www.paginegialle.it/abruzzo/pediatri.html", "PEDIATRI", "ABRUZZO"),
    
    # CLINICHE E CENTRI MEDICI (Contengono decine di specialisti ciascuno)
    ("https://www.paginegialle.it/abruzzo/centri-medici.html", "CENTRI MEDICI", "ABRUZZO"),
    ("https://www.paginegialle.it/pescara/cliniche-private.html", "CLINICHE", "PESCARA")
]

# --- 3. ESECUZIONE ---
accumulo = []
for url, cat, prov in targets:
    accumulo.extend(cerca_lead_sanita(url, cat, prov))

if accumulo:
    email_esistenti = set(sheet.col_values(3))
    finali = [a for a in accumulo if a[2] not in email_esistenti]
    if finali:
        sheet.append_rows(finali)
        print(f"Trovati {len(finali)} nuovi invitati per il convegno!")
