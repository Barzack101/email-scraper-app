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

# COLLEGAMENTO AL NUOVO FOGLIO PER IL CONVEGNO
sheet = client.open("ricerca_mail_categoria_sanita'").sheet1 

# Prepara le intestazioni se il foglio è vuoto
try:
    if not sheet.cell(1, 1).value:
        sheet.update('A1:E1', [["DATA", "NOME E COGNOME", "EMAIL", "SPECIALIZZAZIONE", "PROVINCIA"]])
except:
    pass

def estrai_dati_medici(url, categoria, provincia):
    print(f"Ricerca in corso: {categoria} - {provincia}...")
    risultati = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        res = requests.get(url, headers=headers, timeout=20)
        # Cerchiamo tutte le email nella pagina
        emails = re.findall(r'[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,4}', res.text)
        
        for email in list(set(emails)):
            if not email.endswith(('.png', '.jpg', '.pdf', '.gif')):
                # Creiamo il Nome e Cognome partendo dall'email (es. mario.rossi -> Mario Rossi)
                nome_pulito = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
                risultati.append([datetime.now().strftime("%d/%m/%Y"), nome_pulito, email.lower(), categoria, provincia])
    except Exception as e:
        print(f"Errore su {url}: {e}")
    return risultati

# --- 2. BERSAGLI PER TUTTE LE CATEGORIE (ABRUZZO) ---
targets = [
    # ORDINI PROVINCIALI (Per Medici di Base, Pediatri, Odontoiatri)
    ("https://www.ordinemedicipescara.it", "Medici/Odontoiatri", "PESCARA"),
    ("https://www.ordinemedicichieti.it", "Medici/Odontoiatri", "CHIETI"),
    ("https://www.ordinemediciteramo.it", "Medici/Odontoiatri", "TERAMO"),
    ("https://www.ordinemedicilaquila.it", "Medici/Odontoiatri", "L'AQUILA"),
    
    # FARMACISTI
    ("https://www.fofi.it", "Farmacisti", "ABRUZZO"),
    
    # SPECIALISTI (Allergologi, Dermatologi, ecc. da portali grandi)
    ("https://www.miodottore.it/abruzzo", "Specialisti Vari", "ABRUZZO"),
    ("https://www.dottori.it/abruzzo", "Specialisti Vari", "ABRUZZO"),
    
    # VETERINARI E ALTRI
    ("https://www.paginegialle.it/abruzzo/veterinari.html", "Veterinari", "ABRUZZO"),
    ("https://www.paginegialle.it/abruzzo/centri-medici.html", "Centri Medici", "ABRUZZO")
]

# --- 3. ESECUZIONE ---
nuovi_contatti = []
for url, cat, prov in targets:
    nuovi_contatti.extend(estrai_dati_medici(url, cat, prov))

if nuovi_contatti:
    sheet.append_rows(nuovi_contatti)
    print(f"Operazione completata! Aggiunti {len(nuovi_contatti)} nominativi per il convegno.")
else:
    print("Nessun nuovo dato trovato in questo giro.")
