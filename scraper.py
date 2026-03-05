import os
import requests
import re
import gspread
import time
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- CONFIGURAZIONE GOOGLE SHEETS ---
creds_json = os.getenv('GOOGLE_CREDENTIALS')
creds = Credentials.from_service_account_info(json.loads(creds_json), 
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
        res = requests.get(search_url, headers=HEADERS, timeout=10)
        # Cerchiamo pattern email nel testo dei risultati di ricerca
        emails = re.findall(r'[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,4}', res.text)
        
        for email in set(emails):
            email = email.lower()
            if not any(x in email for x in ['aruba', 'pec', 'legalmail', 'google', 'sentry']):
                return email
    except:
        pass
    return None

# --- I NOMI ESTRATTI DAL TUO PDF ---
# Puoi aggiungere tutti i nomi che vuoi in questa lista
nomi_da_cercare = [
    "Pier Luigi Cariello", "Margherita Angelucci", "Fabiana Cecchini",
    "Giulia Maria D'Ambrosio", "Valentina Di Fabio", "Serena Di Filippo"
]

# --- ESECUZIONE ---
nuovi_contatti = []
for nome in nomi_da_cercare:
    email = trova_email_da_nome(nome)
    if email:
        print(f"✅ TROVATA: {email}")
        nuovi_contatti.append([datetime.now().strftime("%d/%m/%Y"), nome, email, "SPECIALISTA", "ABRUZZO"])
    else:
        print(f"❌ Non trovata per {nome}")
    time.sleep(2) # Pausa per non farci bloccare da Google

if nuovi_contatti:
    sheet.append_rows(nuovi_contatti)
    print(f"Aggiunti {len(nuovi_contatti)} contatti mirati!")
