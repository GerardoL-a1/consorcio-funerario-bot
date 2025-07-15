import os
import requests

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_MESSAGING_URL = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
TWILIO_AUTH = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
NUMERO_REENVIO = os.getenv("NUMERO_REENVIO", "+525523604519")

def reenviar_mensaje(destino, mensaje):
    requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
        "To": destino,
        "From": "whatsapp:+14155238886",
        "Body": mensaje
    })

def mensaje_inactividad(numero):
    reenviar_mensaje(numero, "⌛ ¿Aún estás ahí? Si necesitas ayuda, escribe la palabra *menú* para volver al inicio.")
