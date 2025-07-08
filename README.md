# Consorcio Funerario Bot

Bot de atención automatizada por WhatsApp para emergencias y servicios funerarios, implementado en Flask + Twilio.

## Archivos necesarios

- `app.py`
- `planes_info.py`
- `Procfile`
- `requirements.txt`
- `credenciales.json` (debe subirse manualmente a Render)

## Variables de entorno necesarias

- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`

## Deploy en Render

1. Crear un nuevo Web Service (Python 3).
2. Usar los comandos:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
3. Subir `credenciales.json` desde la terminal de Render.

---