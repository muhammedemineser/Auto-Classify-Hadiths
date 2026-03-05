from google import genai
from google.genai import types

# Konfiguration deines API-Keys
client = genai.Client(api_key="AIzaSyAgdUfiHmSSuIBUVWfpYXQh1EsTNZ-VRZ8")

# # Liste der Cache-Namen
# cache_names = [
# "cachedContents/hvrdkb1ypyhpmyp7q3gl27gnbudrdy81sjp13med",
# "cachedContents/fvlovsdrupqvypt4qssyv7jzn4yo8jikgg74zad9"
# ]

# def delete_caches(names):
#     for name in names:
#         try:
#             # Zugriff auf die Cache-Ressource und Löschen
#             client.caches.delete(name=name)
#             print(f"Erfolgreich gelöscht: {name}")
#         except Exception as e:
#             print(f"Fehler beim Löschen von {name}: {e}")
#         else:
#             print(f"Erfolgreich gelöscht: {name}")

# if __name__ == "__main__":
#     delete_caches(cache_names)

# Listet alle Caches auf
found_any = False
for c in client.caches.list():
    found_any = True
    print("-" * 30)
    print(f"Name: {c.name}")
    print(f"Modell: {c.model}")
    print(f"Erstellt: {c.create_time}")
    print(f"Läuft ab: {c.expire_time}")
    client.caches.delete(name=c.name)

    print("-" * 30)

if not found_any:
    print("Keine aktiven Caches gefunden. Alles sauber!")