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

def cerca_intelligente(query, categoria, provincia):
    print(f"Ricerca Globale: {categoria} a {provincia}...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    trovate = []
    # Usiamo un motore di ricerca per trovare pagine che contengono elenchi medici
    search_url = f"https://www.google.com/search?q={query}+email+abruzzo"
    try:
        res = requests.get(search_url, headers=headers, timeout=20)
        # Regex per estrarre email dal testo della ricerca
        emails = re.findall(r'[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,4}', res.text)
        for email in list(set(emails)):
            if not email.endswith(('.png', '.jpg', '.pdf', '.gif', '.svg', 'google.com')):
                nome_proposta = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
                trovate.append([datetime.now().strftime("%d/%m/%Y"), nome_proposta, email.lower(), categoria, provincia])
    except:
        pass
    return trovate

# --- 2. BERSAGLI: TUTTE LE CATEGORIE DELLA TUA FOTO ---
# Espandiamo al massimo la ricerca
categorie = [
    ("Allergologo", "ALLERGOLOGIA"),
    ("Cardiologo", "CARDIOLOGIA"),
    ("Dermatologo", "DERMATOLOGIA"),
    ("Pediatra", "PEDIATRIA"),
    ("Medico di Medicina Generale", "MEDICO DI BASE"),
    ("Odontoiatra", "ODONTOIATRIA"),
    ("Farmacia", "FARMACIA")
]
province = ["PESCARA", "CHIETI", "TERAMO", "LAQUILA"]

# --- 3. ESECUZIONE ---
accumulo = []
for cat_nome, cat_label in categorie:
    for prov in province:
        query = f"{cat_nome}+{prov}"
        accumulo.extend(cerca_intelligente(query, cat_label, prov))
        time.sleep(1) # Pausa per non farci bloccare

if accumulo:
    email_esistenti = set(sheet.col_values(3))
    da_scrivere = [a for a in accumulo if a[2] not in email_esistenti]
    if da_scrivere:
        sheet.append_rows(da_scrivere)
        print(f"Successo! Trovati {len(da_scrivere)} nuovi contatti.")
    else:
        print("Nessun nuovo contatto trovato.")
