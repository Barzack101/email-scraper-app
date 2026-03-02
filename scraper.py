import os
import json
import gspread
import requests
import re
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- 1. CONFIGURAZIONE E ACCESSO ---
creds_json = os.getenv('GOOGLE_CREDENTIALS')
info = json.loads(creds_json)
creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
client = gspread.authorize(creds)
sheet = client.open("emailscraper").sheet1 

def estrai_email_da_url(url):
    print(f"Analizzando: {url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        # Cerchiamo di ottenere la pagina
        response = requests.get(url, headers=headers, timeout=15)
        # Cerchiamo le email
        emails = re.findall(r'[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,4}', response.text)
        # Pulizia: tutto minuscolo e niente file spazzatura
        return list(set(e.lower() for e in emails if not e.endswith(('.png', '.jpg', '.gif', '.pdf'))))
    except Exception as e:
        print(f"Errore su {url}: {e}")
        return []

# --- 2. LISTA SITI ---
urls = [
    "https://www.asl.pe.it/Sezione.jsp?idSezione=818"
    "https://www.poloautomotive.it/i-soci/",
    "https://www.agenziaprivacy.it/elenco-aziende-abruzzo/"
    "https://www.confindustriaabruzzo.it/chi-siamo/le-territoriali.html"
]

# --- 3. LOGICA ANTI-DUPLICATI ---
# Leggiamo cosa c'è già (partiamo dalla riga 2)
email_esistenti = set(sheet.col_values(2)) 
nuove_estratte = []

for sito in urls:
    trovate = estrai_email_da_url(sito)
    for email in trovate:
        if email not in email_esistenti:
            data_oggi = datetime.now().strftime("%d/%m/%Y")
            nuove_estratte.append([data_oggi, email, sito])
            email_esistenti.add(email) 

# --- 4. SCRITTURA ---
if nuove_estratte:
    sheet.append_rows(nuove_estratte)
    print(f"Successo: aggiunte {len(nuove_estratte)} nuove email.")
else:
    print("Nessun nuovo contatto trovato.")
