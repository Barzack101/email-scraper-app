import os
import json
import gspread
import requests
import re
from google.oauth2.service_account import Credentials

# --- CONFIGURAZIONE MINIMALE ---
creds_json = os.getenv('GOOGLE_CREDENTIALS')
info = json.loads(creds_json)
creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
client = gspread.authorize(creds)
sheet = client.open("ricerca_mail_categoria_sanita'").sheet1

def estrai_veloce(url, cat, prov):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        emails = re.findall(r'[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,4}', res.text)
        return [[ "03/03/2026", e.split('@')[0].title(), e.lower(), cat, prov] for e in set(emails)]
    except: return []

# SITI CHE NON HANNO BLOCCHI (Contatti diretti)
targets = [
    ("https://www.ordinefarmacistichieti.it/uffici", "FARMACISTI", "CHIETI"),
    ("https://www.ordinemediciteramo.it/contatti", "MEDICI", "TERAMO"),
    ("https://www.ordinemedicipescara.it/segreteria", "MEDICI", "PESCARA"),
    ("https://www.aslpe.it/pagine.zhtml?id=2", "UFFICI ASL", "PESCARA")
]

nuovi = []
for u, c, p in targets: nuovi.extend(estrai_veloce(u, c, p))

if nuovi:
    esistenti = set(sheet.col_values(3))
    da_scrivere = [n for n in nuovi if n[2] not in esistenti]
    if da_scrivere: sheet.append_rows(da_scrivere)
