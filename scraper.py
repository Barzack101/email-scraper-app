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

def cerca_lead_aggressivo(url, categoria, provincia):
    print(f"Rastrellamento in corso: {categoria} - {provincia}")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    trovate = []
    try:
        res = requests.get(url, headers=headers, timeout=30)
        # Regex potenziata per trovare email anche dentro stringhe sporche
        emails = re.findall(r'[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,4}', res.text)
        
        for email in list(set(emails)):
            email = email.lower()
            if not email.endswith(('.png', '.jpg', '.pdf', '.gif', '.svg', '.webp', 'example.com')):
                # Proviamo a dividere nome e cognome
                parti = email.split('@')[0].replace('.', ' ').replace('_', ' ').split()
                nome_cognome = " ".join([p.capitalize() for p in parti]) if len(parti) >= 2 else parti[0].capitalize()
                
                trovate.append([datetime.now().strftime("%d/%m/%Y"), nome_cognome, email, categoria, provincia])
    except Exception as e:
        print(f"Salto {url} per errore tecnico.")
    return trovate

# --- 2. BERSAGLI: PORTALI DI TRASPARENZA E ASSOCIAZIONI ---
targets = [
    # Portali con elenchi medici per provincia
    ("https://www.miodottore.it/allergologo/abruzzo", "ALLERGOLOGI", "ABRUZZO"),
    ("https://www.miodottore.it/pediatra/abruzzo", "PEDIATRI", "ABRUZZO"),
    ("https://www.miodottore.it/cardiologo/abruzzo", "CARDIOLOGI", "ABRUZZO"),
    ("https://www.miodottore.it/dermatologo/abruzzo", "DERMATOLOGI", "ABRUZZO"),
    
    # Aziende Sanitarie e Cliniche (dove i medici lavorano)
    ("https://www.aslpe.it/pagine.zhtml?id=123", "MEDICI ASL", "PESCARA"),
    ("https://www.asl2abruzzo.it/contatti.html", "MEDICI ASL", "CHIETI"),
    ("https://www.clinicaspatocco.it/i-nostri-medici", "SPECIALISTI", "CHIETI"),
    ("https://www.casadicurapierangeli.it/medici", "SPECIALISTI", "PESCARA"),
    
    # Ordini Farmacisti (per completare la categoria)
    ("https://www.ordinefarmacistichieti.it/iscritti", "FARMACISTI", "CHIETI"),
    ("https://www.ordinefarmacistiteramo.it/iscritti", "FARMACISTI", "TERAMO")
]

# --- 3. ESECUZIONE ---
accumulo_totale = []
for url, cat, prov in targets:
    accumulo_totale.extend(cerca_lead_aggressivo(url, cat, prov))

if accumulo_totale:
    # Evitiamo duplicati nel foglio
    email_esistenti = set(sheet.col_values(3))
    da_inviare = [r for r in accumulo_totale if r[2] not in email_esistenti]
    
    if da_inviare:
        sheet.append_rows(da_inviare)
        print(f"Operazione riuscita! Aggiunti {len(da_inviare)} nominativi.")
    else:
        print("Nessun dato nuovo trovato in questo portale.")
