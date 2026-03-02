import os
import json
import gspread
import requests
import re
import time
from datetime import datetime
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials

# --- 1. CONFIGURAZIONE ---
creds_json = os.getenv('GOOGLE_CREDENTIALS')
info = json.loads(creds_json)
creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
client = gspread.authorize(creds)

# APRIAMO IL NUOVO FOGLIO
sheet = client.open("Logistica_Abruzzo").sheet1 

def cerca_email_nel_testo(testo):
    emails = re.findall(r'[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,4}', testo)
    return list(set(e.lower() for e in emails if not e.endswith(('.png', '.jpg', '.gif', '.pdf', '.svg'))))

def analizza_sito_profondo(url_principale):
    print(f"Investigando: {url_principale}")
    email_trovate_sito = set()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.get(url_principale, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        email_trovate_sito.update(cerca_email_nel_testo(response.text))
        
        pagine_interessanti = []
        for link in soup.find_all('a', href=True):
            testo_link = link.text.lower()
            href = link['href']
            if any(parola in testo_link for parola in ['contatt', 'chi siamo', 'about', 'info', 'dove']):
                pagine_interessanti.append(urljoin(url_principale, href))
        
        for sub_url in list(set(pagine_interessanti))[:3]:
            try:
                sub_res = requests.get(sub_url, headers=headers, timeout=10)
                email_trovate_sito.update(cerca_email_nel_testo(sub_res.text))
                time.sleep(1)
            except:
                continue
    except Exception as e:
        print(f"Errore su {url_principale}: {e}")
    return list(email_trovate_sito)

# --- 2. LISTA SITI LOGISTICA ABRUZZO ---
urls = [
    "https://www.dinino.it/contatti/",
    "https://www.laspina.it/contatti/",
    "https://www.tuaabruzzo.it/index.php?id=21",
    "https://www.sangritana.it/contatti/",
    "https://www.interportoabruzzo.it/contatti/",
    "https://www.magazzinigabriele.it/contatti/",
    "https://www.clai-logistica.it/contatti/",
    "https://www.smet.it/contatti/",
    "https://www.brioni.com/it/it/contatti",
    "https://www.valdisangro.it/aziende-consortili/"
]

# --- 3. SCRITTURA ---
email_esistenti = set(sheet.col_values(2)) 
nuove_estratte = []

for sito in urls:
    trovate = analizza_sito_profondo(sito)
    for email in trovate:
        if email not in email_esistenti:
            data_oggi = datetime.now().strftime("%d/%m/%Y")
            nuove_estratte.append([data_oggi, email, sito])
            email_esistenti.add(email) 

if nuove_estratte:
    sheet.append_rows(nuove_estratte)
    print(f"Fatto! Aggiunti {len(nuove_estratte)} nuovi contatti.")
else:
    print("Nessuna nuova email trovata.")
