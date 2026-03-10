import os
import tweepy
from dotenv import load_dotenv

load_dotenv()

keys = {
    "X_API_KEY": os.getenv("X_API_KEY", ""),
    "X_API_SECRET": os.getenv("X_API_SECRET", ""),
    "X_ACCESS_TOKEN": os.getenv("X_ACCESS_TOKEN", ""),
    "X_ACCESS_SECRET": os.getenv("X_ACCESS_SECRET", ""),
}

missing = [k for k, v in keys.items() if not v.strip()]
if missing:
    print(f"BRAK KLUCZY: {', '.join(missing)}")
    exit(1)

print("Klucze OK. Wysylam tweet testowy...")

client = tweepy.Client(
    consumer_key=keys["X_API_KEY"].strip(),
    consumer_secret=keys["X_API_SECRET"].strip(),
    access_token=keys["X_ACCESS_TOKEN"].strip(),
    access_token_secret=keys["X_ACCESS_SECRET"].strip(),
)

try:
    resp = client.create_tweet(text="Test API z bota odkryjai.pl")
    print(f"OK! Tweet ID: {resp.data['id']}")
except tweepy.errors.Forbidden as e:
    detail = e.response.text if hasattr(e, "response") and e.response else ""
    print(f"403 Forbidden: {detail}")
except tweepy.errors.Unauthorized:
    print("401 Unauthorized: klucze sa zle lub wygasly.")
except Exception as e:
    print(f"BLAD: {e}")
