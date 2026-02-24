import re

# Questo è un test: cerchiamo email in un testo finto
testo_di_prova = "Mandami una mail a info@test.it o a supporto@azienda.com"

# La formula per estrarre le email
email_estratte = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', testo_di_prova)

print("Email trovate:")
print(email_estratte)
