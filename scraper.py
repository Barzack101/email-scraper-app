import os
import json
import gspread
import requests
import re
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials

# --- 1. CONFIGURAZIONE ---
creds_json = os.getenv('GOOGLE_CREDENTIALS')
info = json.loads(creds_json)
creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
client = gspread.authorize(creds)
sheet = client.open("Logistica_Abruzzo").sheet1 

def cerca_email(testo):
    emails = re.findall(r'[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,4}', testo)
    return list(set(e.lower() for e in emails if not e.endswith(('.png', '.jpg', '.gif', '.pdf', '.svg', '.webp'))))

def esplora_e_estrai(url_dominio):
    print(f"Esplorazione autonoma avviata: {url_dominio}")
    trovate_totali = set()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        # 1. Analizza la Home
        res = requests.get(url_dominio, headers=headers, timeout=20)
        trovate_totali.update(cerca_email(res.text))
        
        # 2. Trova link a pagine contatti/info
        soup = BeautifulSoup(res.text, 'html.parser')
        links_interessanti = []
        parole_chiave = ['contatt', 'contatti', 'about', 'chi siamo', 'uffic', 'info', 'sede', 'legal', 'privacy']
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            testo = a.text.lower()
            # Verifica se il link sembra una pagina di contatti
            if any(p in testo for p in parole_chiave) or any(p in href.lower() for p in parole_chiave):
                full_url = urljoin(url_dominio, href)
                # Resta nello stesso dominio
                if urlparse(full_url).netloc == urlparse(url_dominio).netloc:
                    links_interessanti.append(full_url)
        
        # 3. Visita i link trovati (fino a 8 per non rallentare troppo)
        for link in list(set(links_interessanti))[:8]:
            try:
                print(f"  --> Controllo automatico: {link}")
                r = requests.get(link, headers=headers, timeout=12)
                trovate_totali.update(cerca_email(r.text))
                time.sleep(0.5)
            except:
                continue
                
    except Exception as e:
        print(f"Errore su {url_dominio}: {e}")
        
    return list(trovate_totali)

# --- 2. LISTA BERSAGLI (Solo domini principali) ---
urls = [
    "https://www.paginegialle.it/abruzzo/autotrasporti.html",
    "https://www.paginegialle.it/abruzzo/corrieri.html",
    "https://www.aziende.it/abruzzo/trasporti-e-logistica/",
    "https://www.kompass.com/it/y/it/r/abruzzo/it_13/", # Portale B2B internazionale molto sicuro
    "https://www.uif.it/elenco-aziende-abruzzo/", # Unione Industriali
    "https://www.portaleaziende.it/regione/abruzzo/settore/trasporti",
    "https://www.paginebianche.it/abruzzo/trasporti-merci.html"
]
# --- 3. SCRITTURA ---
email_esistenti = set(sheet.col_values(2)) 
nuove_estratte = []

for sito in urls:
    trovate = esplora_e_estrai(sito)
    for email in trovate:
        if email not in email_esistenti:
            data_oggi = datetime.now().strftime("%d/%m/%Y")
            nuove_estratte.append([data_oggi, email, sito])
            email_esistenti.add(email) 

if nuove_estratte:
    sheet.append_rows(nuove_estratte)
    print(f"Successo! Trovate {len(nuove_estratte)} nuove email.")
else:
    print("Nessun nuovo contatto trovato.")
