import os
import json
import gspread
import requests
import re
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- CONFIGURAZIONE ---
creds_json = os.getenv('GOOGLE_CREDENTIALS')
info = json.loads(creds_json)
creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
client = gspread.authorize(creds)
sheet = client.open("ricerca_mail_categoria_sanita'").sheet1

def estrazione_rapida(url, cat, prov):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        emails = re.findall(r'[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,4}', res.text)
        return [[datetime.now().strftime("%d/%m/%Y"), e.split('@')[0].replace('.',' ').title(), e.lower(), cat, prov] for e in set(emails) if not e.endswith(('.png','.jpg'))]
    except: return []

# BERSAGLI STATICI (Meno protetti)
targets = [
    ("https://www.ordinemedicichieti.it/contatti", "Segreteria Medici", "CHIETI"),
    ("https://www.ordinemediciteramo.it/uffici", "Segreteria Medici", "TERAMO"),
    ("https://www.ordinefarmacistipescara.it/contatti", "Farmacisti", "PESCARA"),
    ("https://www.ordinefarmacistilaquila.it/contatti", "Farmacisti", "L'AQUILA"),
    ("http://www.fofi.it/ordine-farmacisti-chieti/contatti", "Farmacisti", "CHIETI")
]

nuovi = []
for u, c, p in targets: nuovi.extend(estrazione_rapida(u, c, p))

if nuovi:
    esistenti = set(sheet.col_values(3))
    da_mettere = [n for n in nuovi if n[2] not in esistenti]
    if da_mettere: sheet.append_rows(da_mettere)
