from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from planes_info import responder_plan
import requests
import os
import threading
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
scheduler = BackgroundScheduler()
scheduler.start()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_MESSAGING_URL = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
TWILIO_AUTH = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
NUMERO_REENVIO = "+525523604519"
NUMEROS_VIP = ["whatsapp:+5215523604519", "whatsapp:+5215611234567"]

sesiones = {}
temporizadores = {}
usuarios_interesados = {}

alcance = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credenciales = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", alcance)
cliente = gspread.authorize(credenciales)
hoja = cliente.open("Clientes Consorcio Funerario").sheet1

MENSAJE_BIENVENIDA = (
    "👋 *Bienvenido a Consorcio Funerario*\n\n"
    "Gracias por escribirnos.\n\n"
    "Por favor indíquenos *en qué le gustaría recibir información o en qué podemos apoyarle*:\n"
    "- Atención inmediata por *emergencia*\n"
    "- Conocer nuestros *servicios funerarios*\n"
    "- Consultar nuestras *ubicaciones disponibles*\n\n"
    "📌 Puede escribir palabras como: *emergencia*, *planes*, *servicios*, *ubicación*, etc."
)

def contiene(palabras, mensaje):
    return any(p in mensaje.lower() for p in palabras)

def responder(texto):
    respuesta = MessagingResponse()
    respuesta.message(texto)
    return str(respuesta)

def registrar_interaccion(numero, mensaje, origen="Cliente"):
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hoja.append_row([fecha, numero, origen, mensaje])
    registrar_log("Interacción", numero, mensaje)

def registrar_log(tipo, numero, mensaje):
    with open("logs.txt", "a", encoding="utf-8") as f:
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{fecha}] [{tipo}] {numero}: {mensaje}\n")

def mensaje_inactividad(numero):
    if numero in sesiones:
        requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
            "To": numero,
            "From": "whatsapp:+14155238886",
            "Body": "⌛ ¿Aún estás ahí? Si necesitas ayuda, escribe *menú* para volver al inicio."
        })
        temporizadores.pop(numero, None)

@app.route("/", methods=["GET"])
def home():
    return "✅ Bot Consorcio Funerario funcionando."

# (Resto del webhook y funciones ya integradas seguirían en otra celda si se requiere)

if __name__ == '__main__':
    app.run(debug=True)
