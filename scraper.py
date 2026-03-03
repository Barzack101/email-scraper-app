import os
import json
import gspread
import requests
import re
import time
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- 1. CONFIGURAZIONE ---
creds_json = os.getenv('GOOGLE_CREDENTIALS')
info = json.loads(creds_json)
creds = Credentials.from_service_account_info(
    info,
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
)
client = gspread.authorize(creds)
NOME_FOGLIO = "ricerca_mail_categoria_sanita'"
sheet = client.open(NOME_FOGLIO).sheet1

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'it-IT,it;q=0.9,en;q=0.8',
}

DELAY = 2  # secondi tra una richiesta e l'altra

# --- 2. EMAIL PATTERN E FILTRI ---
EMAIL_PATTERN = r'[a-zA-Z0-9.\-_+]+@[a-zA-Z0-9.\-_]+\.[a-z]{2,6}'

# Domini da escludere (provider generici, non contatti personali)
DOMINI_ESCLUDI = [
    'aruba', 'legalmail', 'pec.', 'pec@', 'postacert',
    'example.com', 'test.', 'noreply', 'no-reply',
    'privacy@', 'dpo@', 'protezione', 'webmaster',
    'sentry.io', 'w3.org', 'schema.org', 'googleapis',
    'jquery', 'bootstrap', 'cloudflare', 'facebook',
    'twitter', 'instagram', 'youtube', 'google.com',
    'microsoft', 'apple.com', 'adobe.com',
    'wix.com', 'wordpress', 'squarespace'
]

# Parole che indicano email professionali valide (più permissivo)
DOMINI_VALIDI_SANITA = [
    'gmail.com', 'libero.it', 'yahoo.it', 'yahoo.com',
    'hotmail.it', 'hotmail.com', 'outlook.it', 'outlook.com',
    'tiscali.it', 'virgilio.it', 'alice.it', 'tin.it',
    'fastwebnet.it', 'inwind.it', 'katamail.com',
    'medici', 'studio', 'clinic', 'farmacia', 'fisio',
    'infermier', 'salute', 'health', 'sanit'
]

def is_email_valida(email):
    """Filtra email spam/sistema, mantiene quelle potenzialmente professionali"""
    email_lower = email.lower()
    # Esclude domini tecnici/sistema
    if any(x in email_lower for x in DOMINI_ESCLUDI):
        return False
    # Esclude email troppo corte o chiaramente automatiche
    if len(email) < 8:
        return False
    return True

def estrai_email_da_pagina(url, categoria, provincia, profondita=1):
    """
    Scarica una pagina, estrae email e opzionalmente segue i link interni
    per trovare pagine con più contatti (es: /medici, /contatti, /staff)
    """
    trovate = []
    urls_da_visitare = [url]
    urls_visitati = set()
    base_domain = '/'.join(url.split('/')[:3])

    LINK_KEYWORDS = [
        'medic', 'dott', 'staff', 'equipe', 'specialisti',
        'contatt', 'infermier', 'farmac', 'fisio', 'terapist',
        'sanitari', 'personale', 'chi-siamo', 'chi_siamo',
        'professionisti', 'ambulatori', 'reparti', 'servizi'
    ]

    livello = 0
    while urls_da_visitare and livello <= profondita:
        batch = urls_da_visitare[:]
        urls_da_visitare = []

        for page_url in batch:
            if page_url in urls_visitati:
                continue
            urls_visitati.add(page_url)

            print(f"  → Scansione: {page_url}")
            try:
                res = requests.get(page_url, headers=HEADERS, timeout=20)
                res.raise_for_status()
            except Exception as e:
                print(f"    ✗ Errore: {e}")
                time.sleep(DELAY)
                continue

            # Estrai email dalla pagina
            emails_trovate = re.findall(EMAIL_PATTERN, res.text)
            for email in set(emails_trovate):
                email = email.lower().strip('.')
                if is_email_valida(email):
                    nome = email.split('@')[0].replace('.', ' ').replace('_', ' ').replace('-', ' ').title()
                    record = [
                        datetime.now().strftime("%d/%m/%Y"),
                        nome,
                        email,
                        categoria,
                        provincia
                    ]
                    if record not in trovate:
                        trovate.append(record)

            # Se siamo al primo livello, cerca link a pagine di staff/contatti
            if livello < profondita:
                links = re.findall(r'href=["\']([^"\']+)["\']', res.text)
                for link in links:
                    link_lower = link.lower()
                    if any(kw in link_lower for kw in LINK_KEYWORDS):
                        if link.startswith('http'):
                            full_url = link
                        elif link.startswith('/'):
                            full_url = base_domain + link
                        else:
                            full_url = base_domain + '/' + link
                        # Solo link dello stesso dominio
                        if base_domain in full_url and full_url not in urls_visitati:
                            urls_da_visitare.append(full_url)

            time.sleep(DELAY)

        livello += 1

    return trovate


def cerca_su_paginegialle(categoria_ricerca, provincia, max_pagine=10):
    """
    Cerca professionisti sanitari su Pagine Gialle con paginazione.
    Fonte molto ricca di contatti email diretti.
    """
    trovate = []
    categoria_enc = categoria_ricerca.replace(' ', '+')
    provincia_enc = provincia.replace("'", '').replace(' ', '+').lower()

    for pagina in range(1, max_pagine + 1):
        if pagina == 1:
            url = f"https://www.paginegialle.it/ricerca/{categoria_enc}/{provincia_enc}"
        else:
            url = f"https://www.paginegialle.it/ricerca/{categoria_enc}/{provincia_enc}/p-{pagina}"

        print(f"  → Pagine Gialle p.{pagina}: {categoria_ricerca} - {provincia}")
        try:
            res = requests.get(url, headers=HEADERS, timeout=20)
            if res.status_code == 404:
                break
            res.raise_for_status()
        except Exception as e:
            print(f"    ✗ Errore: {e}")
            time.sleep(DELAY)
            break

        emails = re.findall(EMAIL_PATTERN, res.text)
        nuove = 0
        for email in set(emails):
            email = email.lower().strip('.')
            if is_email_valida(email):
                nome = email.split('@')[0].replace('.', ' ').replace('_', ' ').replace('-', ' ').title()
                record = [
                    datetime.now().strftime("%d/%m/%Y"),
                    nome,
                    email,
                    categoria_ricerca,
                    provincia
                ]
                if record not in trovate:
                    trovate.append(record)
                    nuove += 1

        print(f"    ✓ Trovate {nuove} email in questa pagina (totale: {len(trovate)})")

        # Se la pagina non ha risultati, smetti
        if nuove == 0 and pagina > 2:
            break

        time.sleep(DELAY)

    return trovate


def cerca_su_tuttocitta(categoria_ricerca, provincia):
    """
    TuttoCittà è un'altra directory ricca di professionisti con email.
    """
    trovate = []
    cat_enc = categoria_ricerca.replace(' ', '-').lower()
    prov_enc = provincia.replace("'", '').replace(' ', '-').lower()

    for pagina in range(1, 8):
        url = f"https://www.tuttocitta.it/cerca/{cat_enc}/{prov_enc}?page={pagina}"
        print(f"  → TuttoCittà p.{pagina}: {categoria_ricerca} - {provincia}")
        try:
            res = requests.get(url, headers=HEADERS, timeout=20)
            res.raise_for_status()
        except Exception as e:
            print(f"    ✗ Errore: {e}")
            time.sleep(DELAY)
            break

        emails = re.findall(EMAIL_PATTERN, res.text)
        nuove = 0
        for email in set(emails):
            email = email.lower().strip('.')
            if is_email_valida(email):
                nome = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
                record = [datetime.now().strftime("%d/%m/%Y"), nome, email, categoria_ricerca, provincia]
                if record not in trovate:
                    trovate.append(record)
                    nuove += 1

        if nuove == 0 and pagina > 2:
            break
        time.sleep(DELAY)

    return trovate


# --- 3. SITI DIRETTI ABRUZZO (multi-livello) ---
SITI_DIRETTI = [
    # ASL Abruzzo
    ("https://www.aslpe.it", "Medici ASL", "PESCARA"),
    ("https://www.asl2abruzzo.it", "Medici ASL", "CHIETI"),
    ("https://www.asl1abruzzo.it", "Medici ASL", "L'AQUILA"),
    ("https://www.aslteramo.it", "Medici ASL", "TERAMO"),

    # Ospedali e cliniche private
    ("https://www.casadicurapierangeli.it", "Specialisti", "PESCARA"),
    ("https://www.clinicaspatocco.it", "Specialisti", "CHIETI"),
    ("https://www.villaserenapescara.it", "Specialisti", "PESCARA"),
    ("https://www.ospedalespiritosanto.it", "Medici Ospedalieri", "PESCARA"),

    # Ordini professionali Abruzzo
    ("https://www.omceope.it", "Medici di Base", "PESCARA"),
    ("https://www.omceochieti.it", "Medici di Base", "CHIETI"),
    ("https://www.omceoteramo.it", "Medici di Base", "TERAMO"),
    ("https://www.omceoaq.it", "Medici di Base", "L'AQUILA"),

    # Associazioni fisioterapisti/infermieri
    ("https://www.aifi.it/fisioterapisti-abruzzo", "Fisioterapisti", "ABRUZZO"),
    ("https://www.ipasvi.it/abruzzo", "Infermieri", "ABRUZZO"),

    # Farmacie
    ("https://www.farmacistiabruzzo.it", "Farmacisti", "ABRUZZO"),
]

# --- 4. RICERCHE SU DIRECTORY ---
# (categoria_ricerca, provincia, fonte)
RICERCHE_DIRECTORY = [
    # Medici di base
    ("medico di base", "pescara"),
    ("medico di base", "chieti"),
    ("medico di base", "teramo"),
    ("medico di base", "l aquila"),
    # Specialisti
    ("medico specialista", "pescara"),
    ("medico specialista", "chieti"),
    ("medico specialista", "teramo"),
    ("cardiologo", "pescara"),
    ("cardiologo", "chieti"),
    ("dermatologo", "pescara"),
    ("ginecologo", "pescara"),
    ("ortopedico", "pescara"),
    ("ortopedico", "chieti"),
    ("pediatra", "pescara"),
    ("pediatra", "teramo"),
    ("oculista", "pescara"),
    # Infermieri
    ("infermiere professionale", "pescara"),
    ("infermiere professionale", "chieti"),
    ("assistenza domiciliare infermieristica", "abruzzo"),
    # Farmacisti / Farmacie
    ("farmacia", "pescara"),
    ("farmacia", "chieti"),
    ("farmacia", "teramo"),
    ("farmacia", "l aquila"),
    # Fisioterapisti
    ("fisioterapista", "pescara"),
    ("fisioterapista", "chieti"),
    ("fisioterapista", "teramo"),
    ("fisioterapista", "l aquila"),
    ("centro fisioterapico", "pescara"),
    ("centro fisioterapico", "chieti"),
    # Altre figure sanitarie
    ("psicologo", "pescara"),
    ("psicologo", "chieti"),
    ("nutrizionista", "pescara"),
    ("logopedista", "pescara"),
    ("veterinario", "pescara"),
    ("veterinario", "chieti"),
]

# --- 5. ESECUZIONE ---
print("=" * 60)
print("AVVIO RICERCA EMAIL OPERATORI SANITARI - ABRUZZO")
print("=" * 60)

dati_finali = []
email_set = set()  # Per deduplicare in memoria

def aggiungi_se_nuova(records):
    for r in records:
        if r[2] not in email_set:
            email_set.add(r[2])
            dati_finali.append(r)

# --- 5a. Siti diretti (con crawling multi-livello) ---
print("\n[FASE 1] Scansione siti diretti Abruzzo...")
for url, cat, prov in SITI_DIRETTI:
    risultati = estrai_email_da_pagina(url, cat, prov, profondita=2)
    aggiungi_se_nuova(risultati)
    print(f"  ✓ {cat} - {prov}: {len(risultati)} email trovate")

# --- 5b. Pagine Gialle ---
print("\n[FASE 2] Ricerca su Pagine Gialle...")
for cat, prov in RICERCHE_DIRECTORY:
    risultati = cerca_su_paginegialle(cat, prov.upper(), max_pagine=8)
    aggiungi_se_nuova(risultati)
    print(f"  ✓ {cat} - {prov.upper()}: {len(risultati)} email trovate")

# --- 5c. TuttoCittà ---
print("\n[FASE 3] Ricerca su TuttoCittà...")
for cat, prov in RICERCHE_DIRECTORY[:15]:  # Prime 15 categorie per non sovraccaricare
    risultati = cerca_su_tuttocitta(cat, prov.upper())
    aggiungi_se_nuova(risultati)
    print(f"  ✓ {cat} - {prov.upper()}: {len(risultati)} email trovate")

# --- 6. SALVATAGGIO SU GOOGLE SHEETS ---
print(f"\n{'=' * 60}")
print(f"TOTALE EMAIL RACCOLTE (pre-dedup foglio): {len(dati_finali)}")
print("=" * 60)

if dati_finali:
    print("Caricamento email già presenti nel foglio...")
    email_esistenti = set(sheet.col_values(3))
    da_inviare = [d for d in dati_finali if d[2] not in email_esistenti]

    if da_inviare:
        # Invia in batch da 50 per evitare timeout
        BATCH_SIZE = 50
        totale_inviati = 0
        for i in range(0, len(da_inviare), BATCH_SIZE):
            batch = da_inviare[i:i + BATCH_SIZE]
            sheet.append_rows(batch)
            totale_inviati += len(batch)
            print(f"  → Inviati {totale_inviati}/{len(da_inviare)} contatti...")
            time.sleep(1)

        print(f"\n✅ FATTO! Aggiunti {len(da_inviare)} nuovi contatti al foglio.")
    else:
        print("⚠️  Nessun nuovo contatto da aggiungere (tutti già presenti).")
else:
    print("⚠️  Nessuna email raccolta. Controlla la connessione o i siti target.")
