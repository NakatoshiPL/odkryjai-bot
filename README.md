# OdkryjAI Bot

Automatyczny bot publikujacy na X/Twitter oraz zapisujacy pigułki wiedzy dla
odkryjai.pl.

## Szybki start (GitHub Actions)

1. W repozytorium GitHuba dodaj sekrety (Settings -> Secrets and variables -> Actions):
   - `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_SECRET`
   - `X_BEARER_TOKEN`, `X_CLIENT_ID`, `X_CLIENT_SECRET`, `X_USER_ACCESS_TOKEN`
   - `KEY_ODKRYJAI`, `GITHUB_TOKEN`
2. Dodaj zmienne (Settings -> Secrets and variables -> Actions -> Variables):
   - `SCIEZKA_BLOGA` (domyslnie `./odkryjai-www/src/content/blog/`)
   - `ENABLE_DM` oraz `ENABLE_AUTO_PUSH` (`true`/`false`)
3. Uruchom workflow `odkryjai_bot.yml` lub poczekaj na cron.

## Auto-push do repo www

Bot zapisuje pigułki do `./odkryjai-www/src/content/blog/` i robi push
z uzyciem `GITHUB_TOKEN`. Upewnij sie, ze token ma uprawnienia
`contents: write` w repozytorium `Nakatoshi`.

## Lokalnie

1. `pip install -r requirements.txt`
2. Skopiuj `.env.example` do `.env` i uzupelnij wartosci
3. `python main.py`
