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

def cerca_lead_chirurgico(url, categoria, provincia):
    print(f"Ricerca profonda: {categoria} - {provincia}")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    trovate = []
    try:
        res = requests.get(url, headers=headers, timeout=25)
        # Cerchiamo le email nel testo
        emails = re.findall(r'[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,4}', res.text)
        for email in list(set(emails)):
            if not email.endswith(('.png', '.jpg', '.pdf', '.gif', '.svg', '.webp')):
                nome_proposto = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
                trovate.append([datetime.now().strftime("%d/%m/%Y"), nome_proposta, email.lower(), categoria, provincia])
    except:
        pass
    return trovate

# --- 2. BERSAGLI: CLINICHE E POLIAMBULATORI (Dove si nascondono i medici) ---
targets = [
    # CHIETI E PESCARA (Centri Specialistici)
    ("https://www.paginegialle.it/chieti/ambulatori-e-consultori.html", "SPECIALISTI", "CHIETI"),
    ("https://www.paginegialle.it/pescara/ambulatori-e-consultori.html", "SPECIALISTI", "PESCARA"),
    ("https://www.paginegialle.it/abruzzo/centri-medici.html", "CENTRI MEDICI", "ABRUZZO"),
    
    # PEDIATRI (Ricerca dedicata)
    ("https://www.paginegialle.it/abruzzo/pediatri.html", "PEDIATRI", "ABRUZZO"),
    
    # ODONTOIATRI E DENTISTI (Categoria enorme)
    ("https://www.paginegialle.it/abruzzo/dentisti-medici-chirurghi-ed-odontoiatri.html", "ODONTOIATRI", "ABRUZZO"),
    
    # CLINICHE PRIVATE (Pierangeli, Spatocco, ecc. spesso appaiono qui)
    ("https://www.paginegialle.it/abruzzo/case-cura-e-cliniche-private.html", "CLINICHE", "ABRUZZO"),
    
    # LABORATORI DI ANALISI (Spesso hanno medici specialisti come direttori)
    ("https://www.paginegialle.it/abruzzo/laboratori-analisi-cliniche.html", "LABORATORI", "ABRUZZO")
]

# --- 3. ESECUZIONE ---
risultati_finali = []
for url, cat, prov in targets:
    risultati_finali.extend(cerca_lead_chirurgico(url, cat, prov))

if risultati_finali:
    email_esistenti = set(sheet.col_values(3))
    da_scrivere = [r for r in risultati_finali if r[2] not in email_esistenti]
    if da_scrivere:
        sheet.append_rows(da_scrivere)
        print(f"Aggiunti {len(da_scrivere)} nuovi contatti medici!")
