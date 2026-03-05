import os
import json
import gspread
import requests
import re
import time
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- CONFIGURAZIONE ---
creds_json = os.getenv('GOOGLE_CREDENTIALS')
info = json.loads(creds_json)
creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
client = gspread.authorize(creds)
sheet = client.open("ricerca_mail_categoria_sanita'").sheet1

def estrai_da_documento(url, cat, prov):
    print(f"Scansione database ufficiale: {prov}...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        res = requests.get(url, headers=headers, timeout=25)
        # Cerchiamo le email nei documenti (spesso sono scritte in chiaro nel codice sorgente)
        emails = re.findall(r'[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,4}', res.text)
        
        trovate = []
        for e in set(emails):
            e = e.lower()
            if not any(x in e for x in ['aruba', 'pec', 'legalmail', 'webmaster']):
                nome = e.split('@')[0].replace('.', ' ').title()
                trovate.append([datetime.now().strftime("%d/%m/%Y"), nome, e, cat, prov])
        return trovate
    except: return []

# BERSAGLI: LISTE UFFICIALI (Dove i medici sono elencati per obbligo di legge)
targets = [
    # Portale Sanità Regione Abruzzo (Tutte le categorie della foto)
    ("https://sanita.regione.abruzzo.it/canale-medici", "PERSONALE CONVENZIONATO", "ABRUZZO"),
    ("https://sanita.regione.abruzzo.it/index.php/pagine/personale-dipendente", "SPECIALISTI", "ABRUZZO"),
    # Liste ASL specifiche
    ("https://www.asl1abruzzo.it/index.php/medici-e-pediatri", "MEDICINA GENERALE", "L'AQUILA"),
    ("https://www.asl2abruzzo.it/area-riservata/servizi-online.html", "SPECIALISTI", "CHIETI"),
    ("https://www.aslteramo.it/servizi/medici-e-pediatri-di-famiglia/", "MEDICI DI BASE", "TERAMO"),
    # Liste PDF (Cerca stringhe email in pagine che linkano PDF pesanti)
    ("https://www.ordinemedicichieti.it/iscritti", "ALBO", "CHIETI"),
    ("https://omceo.te.it/uffici", "ALBO", "TERAMO")
]

# ESECUZIONE
dati_finali = []
for url, cat, prov in targets:
    dati_finali.extend(estrai_da_documento(url, cat, prov))

if dati_finali:
    email_esistenti = set(sheet.col_values(3))
    da_inviare = [d for d in dati_finali if d[2] not in email_esistenti]
    if da_inviare:
        print(f"Sbloccati {len(da_inviare)} nuovi contatti ufficiali!")
        sheet.append_rows(da_inviare)
    else:
        print("Il bot non riesce a leggere oltre. Passiamo al piano manuale per i PDF.")
