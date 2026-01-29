# Comma – Single-file demo (GitHub Pages)

Dette repoet er laget for **uhyre enkel publisering** på GitHub Pages.

## Publiser på 2 minutter

1. Lag et nytt repo på GitHub (tomt).
2. Last opp innholdet i denne zip-en.
3. Gå til **Settings → Pages**:
   - Source: **GitHub Actions**
4. Ferdig: GitHub Pages bygger og publiserer automatisk.

## Lokal kjøring (valgfritt)

Kjør en enkel webserver:
```bash
python -m http.server 8000
```
Åpne:
- http://localhost:8000/

## Ekte OpenAI API (valgfritt, lokalt)

GitHub Pages kan ikke skjule API-nøkler. Derfor ligger API-proxyen som lokal utviklingsopsjon:

1. Sett nøkkel:
```bash
export OPENAI_API_KEY="sk-..."
```

2. Start proxy:
```bash
python server.py
```

3. Åpne:
- http://localhost:8000/

Inne i appen: huk av **Bruk API**.

> På GitHub Pages bør **Bruk API** være AV (default).
