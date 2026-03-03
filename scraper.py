import os
import json
import gspread
import requests
import re
import time
from datetime import datetime
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials

# --- 1. CONFIGURAZIONE ---
creds_json = os.getenv('GOOGLE_CREDENTIALS')
info = json.loads(creds_json)
creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
client = gspread.authorize(creds)
sheet = client.open("Logistica_Abruzzo").sheet1 

def estrai_da_portale(url, categoria, provincia):
    print(f"Scansione: {categoria} a {provincia}...")
    dati_trovati = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=20)
        # Cerchiamo blocchi che sembrano Email e Nomi
        emails = re.findall(r'[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,4}', res.text)
        for email in list(set(emails)):
            if not email.endswith(('.png', '.jpg', '.pdf')):
                # Pulizia nome dall'email (es. mario.rossi@... -> Mario Rossi)
                nome = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
                dati_trovati.append([datetime.now().strftime("%d/%m/%Y"), nome, email.lower(), categoria, provincia])
    except:
        pass
    return dati_trovati

# --- 2. TUTTI I SITI POSSIBILI (Divisi per Categoria e Provincia) ---
# Qui il bot cercherà ovunque ci sia un elenco pubblico in Abruzzo
targets = [
    ("https://www.ordinemedicipescara.it/iscritti", "Medici/Odontoiatri", "PESCARA"),
    ("https://www.ordinemedicichieti.it/iscritti", "Medici/Odontoiatri", "CHIETI"),
    ("https://www.ordinemediciteramo.it/iscritti", "Medici/Odontoiatri", "TERAMO"),
    ("https://www.ordinemedicilaquila.it/iscritti", "Medici/Odontoiatri", "L'AQUILA"),
    ("https://www.fofi.it/ordine-farmacisti-pescara", "Farmacisti", "PESCARA"),
    ("https://www.fofi.it/ordine-farmacisti-chieti", "Farmacisti", "CHIETI"),
    ("https://www.paginegialle.it/abruzzo/veterinari.html", "Veterinari", "ABRUZZO"),
    ("https://www.dottori.it/abruzzo/pediatri", "Pediatri", "ABRUZZO"),
    ("https://www.miodottore.it/abruzzo/specialisti", "Specialisti", "ABRUZZO")
]

# --- 3. SCRITTURA ORDINATA ---
nuova_lista = []
for url, cat, prov in targets:
    nuova_lista.extend(estrai_da_portale(url, cat, prov))

if nuova_lista:
    sheet.append_rows(nuova_lista)
    print(f"Trovati {len(nuova_lista)} nuovi invitati!")
