import os
import re
import requests
import subprocess
import sys
import tweepy
import time
import random
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# --- KONFIGURACJA ---

MANUALNY_TEKST = os.getenv("MANUALNY_TEKST", "").strip()
TRYB = os.getenv("TRYB", "odkryjai")

SCIEZKA_BLOGA = os.getenv("SCIEZKA_BLOGA", "./odkryjai-pl/src/content/blog/")
REPO_PATH = os.getenv("REPO_PATH", "./odkryjai-pl")
GH_TOKEN = os.getenv("GH_TOKEN", "") or os.getenv("GITHUB_TOKEN", "")
ENABLE_AUTO_PUSH = os.getenv("ENABLE_AUTO_PUSH", "false").lower() == "true"
ENABLE_DM = os.getenv("ENABLE_DM", "false").lower() == "true"
RUN_ONCE = os.getenv("RUN_ONCE", "false").lower() == "true"

PROMPT_ODKRYJAI = (
    "Jestes ekspertem AI z odkryjai.pl. Styl: 45-letni weteran tech, cyniczny, "
    "konkretny, zero lania wody. Zastosuj metode Wyszarp: Klap (krotki news), "
    "Zysk (co z tego ma przedsiebiorca), Akcja (co ma zrobic teraz). "
    "ZASADY: maks 240 znakow, bez emoji, bez list numerowanych, "
    "bez znakow nowej linii — pisz ciagle w jednym akapicie. "
    "Zakoncz zawsze: odkryjai.pl - Nie ogladaj, zarabiaj."
)

PROMPT_SARA = (
    "Jestes Sara z odkryjai.pl. Napisz krotka pigulke wiedzy w Markdown, "
    "max 180 slow. Struktura: ## TL;DR (1-2 zdania), ## Konkrety (3-5 punktow), "
    "## Co teraz (1 zdanie). Bez emoji. "
    "Na koncu dodaj linie: odkryjai.pl - Nie ogladaj, zarabiaj."
)

DM_REPLY_TEXT = os.getenv(
    "X_DM_REPLY_TEXT",
    "Dzieki za wiadomosc. Wiecej konkretow na odkryjai.pl"
)

# --- FUNKCJE ---

def log(msg):
    ts = time.strftime("%H:%M:%S")
    try:
        print(f"[{ts}] {msg}", flush=True)
    except UnicodeEncodeError:
        print(f"[{ts}] {msg.encode('ascii', 'replace').decode()}", flush=True)


def publikuj_na_x(tekst):
    keys = {
        "X_API_KEY": os.getenv("X_API_KEY", ""),
        "X_API_SECRET": os.getenv("X_API_SECRET", ""),
        "X_ACCESS_TOKEN": os.getenv("X_ACCESS_TOKEN", ""),
        "X_ACCESS_SECRET": os.getenv("X_ACCESS_SECRET", ""),
    }
    missing = [k for k, v in keys.items() if not v.strip()]
    if missing:
        log(f"BLAD X: brak kluczy {', '.join(missing)}")
        return False

    try:
        client_x = tweepy.Client(
            consumer_key=keys["X_API_KEY"].strip(),
            consumer_secret=keys["X_API_SECRET"].strip(),
            access_token=keys["X_ACCESS_TOKEN"].strip(),
            access_token_secret=keys["X_ACCESS_SECRET"].strip(),
        )
        client_x.create_tweet(text=tekst)
        log("OK: Wyslano na X!")
        return True
    except tweepy.errors.Forbidden as e:
        detail = ""
        if hasattr(e, "response") and e.response is not None:
            detail = e.response.text
        log(f"BLAD X 403: {detail or 'Forbidden — sprawdz uprawnienia app (Read+Write) i regeneruj Access Token.'}")
        return False
    except tweepy.errors.Unauthorized as e:
        log("BLAD X 401: Unauthorized — klucze sa niepoprawne lub wygasly.")
        return False
    except Exception as e:
        log(f"BLAD X: {e}")
        return False


def wyszarp_konkrety():
    try:
        kanaly = [
            "new+ai+tools+for+creators+2026",
            "best+free+ai+software+productivity",
            "ai+automation+tricks+no+code",
            "trending+ai+apps+product+hunt",
            "easy+ai+workflows+for+beginners",
            "ai+tools+solopreneur+2026",
            "free+ai+apps+business+automation",
        ]
        query = random.choice(kanaly)
        url = f"https://news.google.com/rss/search?q={query}&hl=pl&gl=PL&ceid=PL:pl"

        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.content, "xml")
        items = soup.find_all("item")

        if items:
            zakazane = ["stock", "shares", "investment", "quarterly", "siemens", "industrial"]
            titles = [
                i.title.text for i in items[:25]
                if not any(w in i.title.text.lower() for w in zakazane)
            ]
            return random.choice(titles) if titles else items[0].title.text
        return "Nowe darmowe narzedzia AI do automatyzacji"
    except Exception:
        return "Triki AI ulatwiajace codzienna prace"


def generuj_post(klucz_env, tekst_zrodlowy):
    api_key = os.getenv(klucz_env, "").strip()
    if not api_key:
        log(f"BLAD: brak klucza {klucz_env}")
        return None
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": PROMPT_ODKRYJAI},
            {"role": "user", "content": tekst_zrodlowy},
        ],
    )
    return response.choices[0].message.content


def generuj_pigulke(klucz_env, tekst_zrodlowy):
    api_key = os.getenv(klucz_env, "").strip()
    if not api_key:
        log(f"BLAD: brak klucza {klucz_env}")
        return None
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": PROMPT_SARA},
            {"role": "user", "content": tekst_zrodlowy},
        ],
    )
    return response.choices[0].message.content


def przytnij_do_x(tekst, limit=280):
    tekst = tekst.replace("\n", " ").strip()
    tekst = re.sub(r"\s{2,}", " ", tekst)
    if len(tekst) <= limit:
        return tekst
    return tekst[: limit - 1].rstrip() + "…"


def slugify(tekst):
    tekst = tekst.lower().strip()
    tekst = re.sub(r"[^a-z0-9\s-]", "", tekst)
    tekst = re.sub(r"\s+", "-", tekst)
    return tekst[:80].strip("-") or "wpis"


def zapisz_pigulke_md(tresc_md, temat):
    folder = os.path.abspath(SCIEZKA_BLOGA)
    os.makedirs(folder, exist_ok=True)
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%d-%H%M%S")
    tytul = temat.split(".")[0].strip()[:80]
    slug = slugify(tytul)
    nazwa = f"{ts}-{slug}.md"
    sciezka = os.path.join(folder, nazwa)

    frontmatter = (
        "---\n"
        f'title: "{tytul}"\n'
        f"date: {now.isoformat()}\n"
        'tags: ["ai", "odkryjai"]\n'
        "---\n\n"
    )
    with open(sciezka, "w", encoding="utf-8") as f:
        f.write(frontmatter + tresc_md.strip() + "\n")
    log(f"Pigulka zapisana: {sciezka}")


def odpowiedz_na_dm():
    if not ENABLE_DM:
        return
    try:
        client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True,
        )
        dms = client.get_direct_messages(max_results=5)
        if not dms or not getattr(dms, "data", None):
            log("DM: brak nowych wiadomosci.")
            return
        last_dm = dms.data[0]
        sender_id = getattr(last_dm, "sender_id", None)
        if sender_id:
            client.send_direct_message(recipient_id=sender_id, text=DM_REPLY_TEXT)
            log("DM: odpowiedz wyslana.")
    except Exception as e:
        log(f"DM BLAD: {e}")


def auto_push_repo():
    if not ENABLE_AUTO_PUSH:
        return
    repo = os.path.abspath(REPO_PATH)
    if not os.path.isdir(os.path.join(repo, ".git")):
        log(f"Auto-push: brak .git w {repo}")
        return

    def run_git(args):
        return subprocess.run(
            ["git"] + args, cwd=repo, capture_output=True, text=True, check=False
        )

    status = run_git(["status", "--porcelain"])
    if not status.stdout.strip():
        log("Auto-push: brak zmian.")
        return

    run_git(["add", "."])
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    commit = run_git(["commit", "-m", f"Auto update: {now} UTC"])
    if commit.returncode != 0 and "nothing to commit" not in commit.stdout:
        log(f"Auto-push: commit nieudany — {commit.stderr.strip()}")
        return

    remote = os.getenv("GIT_REMOTE", "origin")
    if GH_TOKEN:
        url = run_git(["remote", "get-url", remote]).stdout.strip()
        if url.startswith("https://"):
            safe_url = url.replace("https://", f"https://x-access-token:{GH_TOKEN}@")
            push = run_git(["push", safe_url, "HEAD"])
            if push.returncode == 0:
                log("Auto-push: wyslano z tokenem.")
            else:
                log(f"Auto-push BLAD: {push.stderr.strip()}")
            return

    push = run_git(["push", remote, "HEAD"])
    if push.returncode == 0:
        log("Auto-push: wyslano.")
    else:
        log(f"Auto-push BLAD: {push.stderr.strip()}")


# --- GLOWNA PETLA ---

def main():
    log("START: BOT ODKRYJAI")
    log(f"Tryb: {TRYB} | RUN_ONCE: {RUN_ONCE} | AUTO_PUSH: {ENABLE_AUTO_PUSH}")

    manualny_tekst = MANUALNY_TEKST

    while True:
        try:
            manualny_tryb = bool(manualny_tekst)
            info = manualny_tekst if manualny_tryb else wyszarp_konkrety()
            log(f"Analiza: {info[:120]}...")

            post = generuj_post("KEY_ODKRYJAI", info)
            if not post:
                log("BLAD: brak posta z AI.")
            else:
                post = przytnij_do_x(post)
                log(f"POST: {post}")
                if publikuj_na_x(post):
                    log("POST WYSLANY na X.")
                else:
                    log("POST NIE WYSLANY na X.")

            odpowiedz_na_dm()

            try:
                pigulka = generuj_pigulke("KEY_ODKRYJAI", info)
                if pigulka:
                    zapisz_pigulke_md(pigulka, info)
            except Exception as e:
                log(f"Sara BLAD: {e}")

            auto_push_repo()

            if RUN_ONCE or manualny_tryb:
                log("Zakonczono cykl.")
                break

            minuty = random.randint(45, 80)
            log(f"Przerwa: {minuty} minut...")
            time.sleep(minuty * 60)

        except Exception as e:
            log(f"Awaria: {e}")
            if RUN_ONCE:
                log("RUN_ONCE: koniec po bledzie.")
                sys.exit(1)
            log("Reset za 5 minut...")
            time.sleep(300)


if __name__ == "__main__":
    main()
