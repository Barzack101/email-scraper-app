import os
import json
import gspread
import requests
import re
import time
from google.oauth2.service_account import Credentials

# --- CONFIGURAZIONE GOOGLE SHEETS ---
creds_json = os.getenv('GOOGLE_CREDENTIALS')
info = json.loads(creds_json)
creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
client = gspread.authorize(creds)
sheet = client.open("emailscraper").sheet1 

# --- FUNZIONE PER TROVARE EMAIL ---
def estrai_email_da_url(url):
    print(f"Analizzando: {url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        # Cerchiamo pattern di email nel testo della pagina
        emails = re.findall(r'[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,}', response.text)
        return list(set(emails))
    except Exception as e:
        print(f"Errore su {url}: {e}")
        return []

# --- LISTA DEI SITI ---
urls = [
    "https://www.asl.pe.it/Sezione.jsp?idSezione=863",
    "https://www.asl.pe.it/ListaMedici.jsp"
]

# --- ESECUZIONE ---
tutte_le_email = []
for sito in urls:
    risultati = estrai_email_da_url(sito)
    tutte_le_email.extend(risultati)

# --- SALVATAGGIO INTELLIGENTE (TUTTO INSIEME) ---
if tutte_le_email:
    lista_unificata = list(set(tutte_le_email))
    # Prepariamo i dati nel formato richiesto: una lista di liste [[email1], [email2]]
    dati_da_inserire = [[email] for email in lista_unificata]
    
    # Usiamo append_rows (al plurale) per fare un'unica operazione di scrittura
    sheet.append_rows(dati_da_inserire)
    print(f"Successo! Caricate {len(lista_unificata)} email senza blocchi.")
else:
    print("Nessuna email trovata.")
