import os
import json
import gspread
import requests
import re
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from google.oauth2.service_account import Credentials

# --- 1. CONFIGURAZIONE ---
creds_json = os.getenv('GOOGLE_CREDENTIALS')
info = json.loads(creds_json)
creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
client = gspread.authorize(creds)
sheet = client.open("ricerca_mail_categoria_sanita'").sheet1

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}

# --- 2. LE CATEGORIE DELLA TUA FOTO ---
CATEGORIE_TARGET = [
    "Allergologia", "Dermatologia", "Gastroenterologia", "Malattie Respiratorie",
    "Medicina Interna", "Reumatologia", "Cardiochirurgia", "Chirurgia Generale",
    "Otorinolaringoiatria", "Anatomia Patologica", "Medicina del Lavoro",
    "Medico di Famiglia", "Direzione Medica", "Farmacista"
]

PROVINCE = ["PESCARA", "CHIETI", "TERAMO", "LAQUILA"]

def estrazione_rapida(url, cat, prov):
    try:
        res = requests.get(url, headers=HEADERS, timeout=12)
        emails = re.findall(r'[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,6}', res.text)
        nuovi = []
        for e in set(emails):
            e = e.lower()
            if not any(x in e for x in ['aruba', 'pec', 'legalmail', 'webmaster', 'dpo']):
                nome = e.split('@')[0].replace('.', ' ').title()
                nuovi.append([datetime.now().strftime("%d/%m/%Y"), nome, e, cat, prov])
        return nuovi
    except: return []

# --- 3. GENERAZIONE TARGET (Oltre 50 link di ricerca) ---
targets = []
for cat in CATEGORIE_TARGET:
    for prov in PROVINCE:
        # Pagine Gialle filtrata per specialità e provincia
        targets.append((f"https://www.paginegialle.it/ricerca/{cat.replace(' ', '%20')}/{prov.lower()}", cat, prov))
        # TuttoCittà
        targets.append((f"https://www.tuttocitta.it/cerca/{cat.replace(' ', '-')}/{prov.lower()}", cat, prov))

# Aggiungiamo i tuoi link vincenti della ASL Pescara
targets.append(("https://www.asl.pe.it/ListaMedici.jsp", "SPECIALISTI", "PESCARA"))
targets.append(("https://www.asl.pe.it/Sezione.jsp?idSezione=863", "CONVENZIONATI", "PESCARA"))

# --- 4. ESECUZIONE MASSIVA (Parallelismo) ---
print(f"Avvio ricerca su {len(targets)} combinazioni...")
dati_finali = []
with ThreadPoolExecutor(max_workers=8) as executor:
    risultati = list(executor.map(lambda t: estrazione_rapida(*t), targets))
    for r in risultati: dati_finali.extend(r)

# --- 5. SALVATAGGIO ---
if dati_finali:
    email_esistenti = set(sheet.col_values(3))
    da_inviare = [d for d in dati_finali if d[2] not in email_esistenti]
    if da_inviare:
        print(f"Trovati {len(da_inviare)} NUOVI contatti. Caricamento...")
        for i in range(0, len(da_inviare), 50):
            sheet.append_rows(da_inviare[i:i+50])
            time.sleep(1)
        print("✅ Caricamento completato!")
    else: print("Nessun nuovo contatto trovato.")
