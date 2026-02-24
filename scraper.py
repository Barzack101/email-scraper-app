import os
import json
import gspread
from google.oauth2.service_account import Credentials

# 1. Recuperiamo la "chiave" dalla cassaforte di GitHub
creds_json = os.getenv('GOOGLE_CREDENTIALS')
info = json.loads(creds_json)
creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])

# 2. Ci colleghiamo a Google Sheets
client = gspread.authorize(creds)
# SOSTITUISCI 'IlMioFoglio' con il nome esatto del tuo file Google Sheets!
sheet = client.open("emailscraper").sheet1 

# 3. Funzione per salvare le email
def salva_email(email_lista):
    for email in email_lista:
        sheet.append_row([email])
    print("Email salvate correttamente!")

# Esempio di test
salva_email(["test@esempio.it", "info@barzack.com"])
