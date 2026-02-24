import os
import json
import gspread
import requests
from bs4 import BeautifulSoup
import re
from google.oauth2.service_account import Credentials

# --- CONFIGURAZIONE GOOGLE SHEETS ---
creds_json = os.getenv('GOOGLE_CREDENTIALS')
info = json.loads(creds_json)
creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
client = gspread.authorize(creds)
# ASSICURATI CHE IL NOME QUI SOTTO SIA IDENTICO AL TUO FOGLIO
sheet = client.open("emailscraper").sheet1 

# --- FUNZIONE PER TROVARE EMAIL ---
def estrai_email_da_url(url):
    print(f"Analizzando: {url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        # Cerchiamo pattern di email nel testo della pagina
        emails = re.findall(r'[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,}', response.text)
        return list(set(emails)) # Rimuove i duplicati
    except Exception as e:
        print(f"Errore su {url}: {e}")
        return []

# --- LISTA DEI SITI DA CUI PARTIRE ---
urls = [
    "https://www.asl.pe.it/Sezione.jsp?idSezione=863",
    "https://www.asl.pe.it/ListaMedici.jsp"
]

# --- ESECUZIONE ---
tutte_le_email = []
for sito in urls:
    risultati = estrai_email_da_url(sito)
    tutte_le_email.extend(risultati)

# Salva su Google Sheets
if tutte_le_email:
    for email in list(set(tutte_le_email)):
        sheet.append_row([email])
    print(f"Fatto! Ho trovato e salvato {len(set(tutte_le_email))} email.")
else:
    print("Nessuna email trovata in queste pagine.")
