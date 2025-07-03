
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from planes_info import responder_plan
import requests
import os

app = Flask(__name__)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_MESSAGING_URL = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
TWILIO_AUTH = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
NUMERO_REENVIO = "+525523604519"
sesiones = {}

@app.route("/", methods=["GET"])
def home():
    return "✅ Bot Consorcio Funerario funcionando."

MENSAJE_BIENVENIDA = (
    "👋 *Bienvenido a Consorcio Funerario*\n\n"
    "Gracias por escribirnos.\n\n"
    "Por favor indíquenos *en qué le gustaría recibir información o en qué podemos apoyarle*:\n"
    "- Atención inmediata por *emergencia*\n"
    "- Conocer nuestros *servicios funerarios*\n"
    "- Consultar nuestras *ubicaciones disponibles*\n\n"
    "📌 Puede escribir palabras como: *emergencia*, *planes*, *servicios*, *ubicación*, etc."
)

claves_planes = ["plan", "planes", "servicio", "servicios", "paquete", "información", "informacion"]
claves_emergencia = ["emergencia", "urgente", "fallecido", "murió", "murio", "accidente", "suceso"]
claves_ubicacion = ["ubicación", "ubicaciones", "sucursal", "sucursales", "dirección", "direccion"]
claves_volver = ["volver", "menú", "menu", "inicio"]
claves_saludo = ["hola", "buenas", "buenos días", "buenas tardes", "buenas noches", "que tal", "hey"]


def contiene(palabras, mensaje):
    return any(p in mensaje.lower() for p in palabras)


def responder(texto):
    respuesta = MessagingResponse()
    respuesta.message(texto)
    return str(respuesta)


@app.route("/webhook", methods=["POST"])
def webhook():
    mensaje = request.form.get("Body", "").strip()
    telefono = request.form.get("From", "")
    estado = sesiones.get(telefono, {})
    msj_lower = mensaje.lower()

    if contiene(claves_volver, msj_lower):
        sesiones[telefono] = {}
        return responder(MENSAJE_BIENVENIDA)

    if not estado:
        if contiene(claves_saludo, msj_lower):
            return responder(MENSAJE_BIENVENIDA)
        if contiene(claves_emergencia, msj_lower):
            sesiones[telefono] = {"menu": "emergencia"}
            return responder(
                "🚨 *ATENCIÓN INMEDIATA*\n\n"
                "Por favor responde con los siguientes datos:\n"
                "🔹 Nombre completo del fallecido\n"
                "🔹 Suceso o causa del fallecimiento\n"
                "🔹 Ubicación actual del cuerpo\n"
                "🔹 Dos números de contacto\n"
                "🔹 Nombre de la persona que nos está contactando"
            )
        elif contiene(claves_ubicacion, msj_lower):
            sesiones[telefono] = {"menu": "ubicacion"}
            return responder(
                "📍 *Ubicaciones disponibles:*\n"
                "1. Av. Tláhuac No. 5502, Col. El Rosario, CDMX\n"
                "2. Av. Zacatlán No. 60, Col. San Lorenzo Tezonco, CDMX\n"
                "3. Av. Zacatlán No. 10, Col. San Lorenzo Tezonco, CDMX\n\n"
                "¿Deseas agendar una cita en alguna de nuestras sucursales? (Sí / No)"
            )
        elif contiene(claves_planes, msj_lower):
            sesiones[telefono] = {"menu": "planes"}
            return responder(
                "📋 *Selecciona una categoría:*\n"
                "1. Planes de necesidad inmediata\n"
                "2. Planes a futuro\n"
                "3. Servicios individuales"
            )
        else:
            return responder(MENSAJE_BIENVENIDA)

    return responder(MENSAJE_BIENVENIDA)
