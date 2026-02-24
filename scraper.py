import re
import requests

def estrai_email(url):
    print(f"Sto analizzando il sito: {url}")
    try:
        # 1. Scarichiamo la pagina
        risposta = requests.get(url, timeout=10)
        testo = risposta.text
        
        # 2. Cerchiamo le email con la Regex
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        email_trovate = re.findall(pattern, testo)
        
        # 3. Puliamo i duplicati
        return list(set(email_trovate))
    except Exception as e:
        return f"Errore durante l'analisi: {e}"

# PROVA PRATICA
sito = "https://www.esempio.it" # Cambia questo con un sito vero per testare
risultati = estrai_email(sito)
print(f"Email trovate: {risultati}")
