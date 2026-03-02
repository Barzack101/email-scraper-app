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
sheet = client.open("Logistica_Abruzzo").sheet1 

def cerca_email_nel_testo(testo):
    emails = re.findall(r'[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,4}', testo)
    return list(set(e.lower() for e in emails if not e.endswith(('.png', '.jpg', '.gif', '.pdf', '.svg', '.webp'))))

def analizza_sito_totale(url_principale):
    print(f"Scansione profonda avviata per: {url_principale}")
    email_trovate_sito = set()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url_principale, headers=headers, timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
        email_trovate_sito.update(cerca_email_nel_testo(response.text))
        
        # Cerchiamo link strategici
        pagine_target = []
        parole_chiave = ['contatt', 'chi siamo', 'about', 'info', 'dove', 'uffic', 'amministraz', 'legal', 'privacy']
        
        for link in soup.find_all('a', href=True):
            testo_link = link.text.lower()
            href = link['href']
            if any(p in testo_link for p in parole_chiave) or any(p in href.lower() for p in parole_chiave):
                pagine_target.append(urljoin(url_principale, href))
        
        # Analizziamo fino a 10 sottopagine per trovare l'impossibile
        for sub_url in list(set(pagine_target))[:10]:
            try:
                print(f"  --> Scavando in: {sub_url}")
                sub_res = requests.get(sub_url, headers=headers, timeout=12)
                email_trovate_sito.update(cerca_email_nel_testo(sub_res.text))
                time.sleep(0.5) 
            except:
                continue
                
    except Exception as e:
        print(f"Errore su {url_principale}: {e}")
        
    return list(email_trovate_sito)

# --- 2. LISTA BERSAGLI AMPLIATA (Toyota Lead) ---
urls = [
    "https://www.fatergroup.com", # Pescara - Magazzini enormi
    "https://www.denso.com", # San Salvo - Automotive/Logistica
    "https://www.pilkington.com", # San Salvo - Vetri/Logistica
    "https://www.tuaabruzzo.it", # Trasporti regionali
    "https://www.valagro.com", # Atessa - Chimica/Logistica
    "https://www.honda.it", # Atessa - Produzione/Logistica
    "https://www.alfagomma.com", # Castelnuovo Vomano
    "https://www.pampryl.it", # Conserve/Logistica
    "https://www.pasta-delverde.com", # Fara San Martino
    "https://www.dececco.it" # Fara San Martino / Pescara
]

# --- 3. ESECUZIONE ---
email_esistenti = set(sheet.col_values(2)) 
nuove_estratte = []

for sito in urls:
    trovate = analizza_sito_totale(sito)
    for email in trovate:
        if email not in email_esistenti:
            data_oggi = datetime.now().strftime("%d/%m/%Y")
            nuove_estratte.append([data_oggi, email, sito])
            email_esistenti.add(email) 

if nuove_estratte:
    sheet.append_rows(nuove_estratte)
    print(f"Missione compiuta: {len(nuove_estratte)} nuove email estratte!")
else:
    print("Nessun dato nuovo trovato in questo giro.")
