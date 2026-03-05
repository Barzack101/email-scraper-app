import os
import json
import requests
import re
import gspread
import time
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- CONFIGURAZIONE GOOGLE SHEETS ---
creds_json = os.getenv('GOOGLE_CREDENTIALS')
# Sistemato: ora json è importato correttamente
info = json.loads(creds_json)
creds = Credentials.from_service_account_info(info, 
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
client = gspread.authorize(creds)
sheet = client.open("ricerca_mail_categoria_sanita'").sheet1

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}

def trova_email_da_nome(nome_completo):
    """Cerca su Google l'email associata al nome del medico"""
    print(f"Cercando email per: {nome_completo}...")
    query = f'"{nome_completo}" medico Abruzzo email'
    search_url = f"https://www.google.com/search?q={query}"
    
    try:
        res = requests.get(search_url, headers=HEADERS, timeout=15)
        # Cerchiamo pattern email nel testo dei risultati
        emails = re.findall(r'[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,4}', res.text)
        
        for email in set(emails):
            email = email.lower()
            # Filtri per evitare PEC e spam tecnico
            if not any(x in email for x in ['aruba', 'pec', 'legalmail', 'google', 'sentry', 'wix']):
                return email
    except:
        pass
    return None

# --- I NOMI DALLA TUA GRADUATORIA ASL 2 ---
nomi_da_cercare = [
    "Pier Luigi Cariello", "Margherita Angelucci", "Fabiana Cecchini",
    "Giulia Maria D'Ambrosio", "Valentina Di Fabio", "Serena Di Filippo",
    "Federica Di Sabatino", "Francesca Romana Di Sebastiano", "Alessia Di Tizio",
    "Benedetta Eleonora Gagliardi", "Laura Galanti", "Vittoria Gioffre",
    "Marialaura Greco", "Simona Gualtieri", "Sara Iaccarino", "Silvia Mascii",
    "Nicoletta Minni", "Benedetta Pellegrino", "Luciana Perruzza", "Eleonora Rossi"
]

# --- ESECUZIONE ---
nuovi_contatti = []
for nome in nomi_da_cercare:
    email = trova_email_da_nome(nome)
    if email:
        print(f"✅ TROVATA: {email}")
        nuovi_contatti.append([datetime.now().strftime("%d/%m/%Y"), nome, email, "SPECIALISTA GINECOLOGIA", "CHIETI"])
    else:
        print(f"❌ Non trovata per {nome}")
    # Pausa per non farci bloccare da Google durante la caccia
    time.sleep(3) 

if nuovi_contatti:
    # Controllo duplicati sul foglio
    email_esistenti = set(sheet.col_values(3))
    da_scrivere = [n for n in nuovi_contatti if n[2] not in email_esistenti]
    
    if da_scrivere:
        sheet.append_rows(da_scrivere)
        print(f"Fatto! Aggiunti {len(da_scrivere)} medici dalla graduatoria.")
    else:
        print("Questi nomi erano già nel database.")
