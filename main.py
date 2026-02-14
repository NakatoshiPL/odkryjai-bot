import os
import re
import requests
import subprocess
import tweepy
import time
import random
from datetime import datetime
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

# 1. Inicjalizacja środowiska
load_dotenv()

# 1b. Manualny temat (opcjonalnie) - ustaw i uruchom jednorazowo
# Zostaw pusty string, aby automatycznie korzystać z RSS.
MANUALNY_TEKST = ""

# 1b.1 Tryb działania
# - "odkryjai": biznesowe posty w stylu Wyszarp
# - "marek": styl "Marek" z trikami
TRYB = "odkryjai"

# 1b.2 Konfiguracja automatu
SCIEZKA_BLOGA = os.getenv("SCIEZKA_BLOGA", "./odkryjai-www/src/content/blog/")
REPO_PATH = os.getenv("REPO_PATH", "./odkryjai-www")
GH_TOKEN = os.getenv("GH_TOKEN", "")
ENABLE_AUTO_PUSH = os.getenv("ENABLE_AUTO_PUSH", "false").lower() == "true"
ENABLE_DM = os.getenv("ENABLE_DM", "false").lower() == "true"
RUN_ONCE = os.getenv("RUN_ONCE", "false").lower() == "true"
X_USER_ACCESS_TOKEN = os.getenv("X_USER_ACCESS_TOKEN", "")
DM_REPLY_TEXT = os.getenv(
    "X_DM_REPLY_TEXT",
    "Dzieki za wiadomosc. Wiecej konkretow na odkryjai.pl"
)

# 1c. Prompt biznesowy odkryjai.pl
PROMPT_ODKRYJAI = (
    "Jestes ekspertem AI z odkryjai.pl. Styl: 45-letni weteran tech, cyniczny, "
    "konkretny, zero lania wody. Zastosuj metode Wyszarp: Klap (krotki news), "
    "Zysk (co z tego ma przedsiebiorca), Akcja (co ma zrobic teraz). "
    "Maks 240 znakow. Bez emoji. Zakoncz zawsze: odkryjai.pl - Nie oglądaj, zarabiaj."
)

# 1d. Sara - pigułka wiedzy na WWW
PROMPT_SARA = (
    "Jestes Sara z odkryjai.pl. Napisz krotka pigulke wiedzy w Markdown "
    "(bez blokow ```), max 180 slow. Struktura: "
    "## TL;DR (1-2 zdania), ## Konkrety (3-5 punktow), ## Co teraz (1 zdanie). "
    "Bez emoji. Na koncu dodaj linie: odkryjai.pl - Nie oglądaj, zarabiaj."
)

# 2. Funkcja wysyłająca post na X (OAuth 1.0a)
def publikuj_na_x(tekst):
    try:
        client_x = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        client_x.create_tweet(text=tekst)
        print(f"✅ [{time.strftime('%H:%M:%S')}] Wysłano na X!")
    except Exception as e:
        print(f"❌ BŁĄD X: {e}")

# 3. Ulepszony Research - Celujemy w oprogramowanie i tricki
def wyszarp_konkrety():
    try:
        # Zmieniamy kanały na takie, które dają "mięso" dla początkujących i twórców
        kanaly = [
            "new+ai+tools+for+creators+2026",
            "best+free+ai+software+productivity",
            "ai+automation+tricks+no+code",
            "trending+ai+apps+product+hunt",
            "easy+ai+workflows+for+beginners"
        ]
        query = random.choice(kanaly)
        url = f"https://news.google.com/rss/search?q={query}&hl=pl&gl=PL&ceid=PL:pl"
        
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item')
        
        if items:
            # Filtrujemy, żeby wywalić nudne newsy o giełdzie i korporacjach
            zakazane_slowa = ["stock", "shares", "investment", "quarterly", "siemens", "industrial"]
            titles = [i.title.text for i in items[:20] if not any(word in i.title.text.lower() for word in zakazane_slowa)]
            
            return random.choice(titles) if titles else items[0].title.text
        return "Nowe darmowe narzędzia AI do automatyzacji"
    except:
        return "Triki AI ułatwiające codzienną pracę"

# 4. Marek - Agresywny filtr na durnoty
def stworz_post_marka(klucz_env, trendy, dodaj_link):
    api_key = os.getenv(klucz_env, "").strip()
    client = OpenAI(api_key=api_key)
    
    # Reklama pojawia się rzadziej, żeby nie spamować
    reklama = "triki na odkryjai.pl" if dodaj_link else ""
    
    # Bardzo surowy prompt dla Marka
    prompt = (
        "Jesteś Marek, 45-letni weteran technologii. Nienawidzisz bełkotu o 'przyszłości AI'. "
        "Twoim zadaniem jest wyciągnąć z newsa twardą wartość dla soloprzedsiębiorcy. "
        "ZASADY: MAKS 240 ZNAKÓW. ZAKAZ LIST I NUMEROWANIA (1, 2, 3). "
        f"Na podstawie newsa: {trendy}, podaj: "
        "KONKRETNY SOFT, JEDEN TRICK I WYNIK (ile czasu/kasy to oszczędza). "
        f"Styl: małe litery, cyniczny, konkretny, na końcu 🥃. {reklama} #AI #tips #proste"
    )
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": prompt}]
    )
    return response.choices[0].message.content

# 4b. Prompt biznesowy dla odkryjai.pl
def stworz_post_odkryjai(klucz_env, tekst_zrodlowy):
    api_key = os.getenv(klucz_env, "").strip()
    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": PROMPT_ODKRYJAI},
            {"role": "user", "content": tekst_zrodlowy}
        ]
    )
    return response.choices[0].message.content

def stworz_pigulke_sary(klucz_env, tekst_zrodlowy):
    api_key = os.getenv(klucz_env, "").strip()
    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": PROMPT_SARA},
            {"role": "user", "content": tekst_zrodlowy}
        ]
    )
    return response.choices[0].message.content

def przytnij_do_x(tekst, limit=280):
    if len(tekst) <= limit:
        return tekst
    return tekst[:limit - 1].rstrip() + "…"

def slugify(tekst):
    tekst = tekst.lower().strip()
    tekst = re.sub(r"[^a-z0-9\s-]", "", tekst)
    tekst = re.sub(r"\s+", "-", tekst)
    return tekst[:80].strip("-") or "wpis"

def zapisz_pigulke_md(tresc_md, temat):
    folder = os.path.abspath(SCIEZKA_BLOGA)
    os.makedirs(folder, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    tytul = temat.split(".")[0].strip()
    slug = slugify(tytul)
    nazwa = f"{ts}-{slug}.md"
    sciezka = os.path.join(folder, nazwa)

    frontmatter = (
        "---\n"
        f'title: "{tytul[:80]}"\n'
        f"date: {datetime.utcnow().isoformat()}Z\n"
        "tags: [\"ai\", \"odkryjai\"]\n"
        "---\n\n"
    )
    with open(sciezka, "w", encoding="utf-8") as f:
        f.write(frontmatter + tresc_md.strip() + "\n")
    print(f"📝 Zapisano pigułkę: {sciezka}")

def odpowiedz_na_dm():
    if not ENABLE_DM:
        return
    try:
        client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=X_USER_ACCESS_TOKEN or os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET") if not X_USER_ACCESS_TOKEN else None,
            wait_on_rate_limit=True
        )

        if not hasattr(client, "get_direct_messages") or not hasattr(client, "send_direct_message"):
            print("⚠️ DM: tweepy Client nie wspiera DM w tej wersji.")
            return

        dms = client.get_direct_messages(max_results=5)
        if not dms or not getattr(dms, "data", None):
            print("📭 DM: brak nowych wiadomości.")
            return

        last_dm = dms.data[0]
        sender_id = getattr(last_dm, "sender_id", None)
        if not sender_id:
            print("⚠️ DM: brak sender_id.")
            return

        client.send_direct_message(recipient_id=sender_id, text=DM_REPLY_TEXT)
        print("✅ DM: odpowiedz wyslana.")
    except Exception as e:
        print(f"❌ BŁĄD DM: {e}")

def auto_push_repo():
    if not ENABLE_AUTO_PUSH:
        return
    repo = os.path.abspath(REPO_PATH)
    if not os.path.isdir(os.path.join(repo, ".git")):
        print("⚠️ Auto-push: brak .git w REPO_PATH.")
        return

    def run_git(args):
        return subprocess.run(
            ["git"] + args,
            cwd=repo,
            capture_output=True,
            text=True,
            check=False
        )

    status = run_git(["status", "--porcelain"])
    if not status.stdout.strip():
        print("✅ Auto-push: brak zmian.")
        return

    run_git(["add", "."])
    msg = f"Auto update: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
    commit = run_git(["commit", "-m", msg])
    if commit.returncode != 0 and "nothing to commit" not in commit.stdout:
        print("⚠️ Auto-push: commit nieudany.")
        return

    remote = os.getenv("GIT_REMOTE", "origin")
    if GH_TOKEN:
        url = run_git(["remote", "get-url", remote]).stdout.strip()
        if url.startswith("https://"):
            safe_url = url.replace("https://", f"https://x-access-token:{GH_TOKEN}@")
            run_git(["push", safe_url, "HEAD"])
            print("✅ Auto-push: wyslano z tokenem.")
            return

    run_git(["push", remote, "HEAD"])
    print("✅ Auto-push: wyslano.")

# --- START MASZYNY ODKRYJAI ---

print("🚀 START: BOT ODKRYJAI")
print(f"⚙️ Tryb: {TRYB}")

while True:
    try:
        manualny_tryb = bool(MANUALNY_TEKST)
        # KROK 1: Research mięsa z różnych kanałów
        info = MANUALNY_TEKST if manualny_tryb else wyszarp_konkrety()
        print(f"\n🔍 Analiza newsa: {info}")

        # KROK 2: Decyzja o reklamie (20% szans)
        promocja = random.random() < 0.20
        
        # KROK 3: Generowanie posta
        if TRYB == "odkryjai":
            marek_txt = stworz_post_odkryjai("KEY_ODKRYJAI", info)
        else:
            marek_txt = (
                stworz_post_odkryjai("KEY_ODKRYJAI", info)
                if manualny_tryb
                else stworz_post_marka("KEY_ODKRYJAI", info, promocja)
            )

        marek_txt = przytnij_do_x(marek_txt)
        print(f"🤖 POST: {marek_txt}")

        # KROK 4: Publikacja na X
        publikuj_na_x(marek_txt)
        print("✅ POST WYSŁANY")

        # KROK 4b: DM (opcjonalnie)
        odpowiedz_na_dm()

        # KROK 4c: Sara zapisuje pigułkę na WWW
        try:
            pigulka = stworz_pigulke_sary("KEY_ODKRYJAI", info)
            zapisz_pigulke_md(pigulka, info)
        except Exception as e:
            print(f"⚠️ Sara: nie zapisano pigułki ({e})")

        # KROK 4d: Auto-push do repo (opcjonalnie)
        auto_push_repo()

        if RUN_ONCE:
            print("✅ RUN_ONCE: zakonczono po jednym cyklu.")
            break

        if manualny_tryb:
            MANUALNY_TEKST = ""
            print("✅ Manualny temat wyczyszczony. Powrot do RSS.")
        
        # KROK 5: Losowa przerwa (45-80 min) - symulacja człowieka
        minuty = random.randint(45, 80)
        print(f"💤 Marek odpoczywa przez {minuty} minut...")
        time.sleep(minuty * 60)

    except Exception as e:
        print(f"⚠️ Awaria: {e}.")
        if RUN_ONCE:
            print("RUN_ONCE: koniec po błędzie (bez pętli retry).")
            raise
        print("Reset za 5 minut...")
        time.sleep(300)