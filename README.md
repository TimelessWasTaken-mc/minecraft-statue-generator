# Minecraft Statue Generator (Python-only) — Starter

This is a starter web app you can deploy to Render and open on your iPad.

Right now it:
- Accepts a Minecraft skin upload **or** a username
- Returns a ZIP with placeholder outputs (so the full pipeline works)

Next step is to replace the placeholder generator with your real statue logic.

## Local run (optional)
```bash
pip install -r requirements.txt
python app.py
```
Open: http://localhost:5000

## Deploy to Render
- Create a **Web Service**
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn wsgi:app`

