
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
    "📌 Puede escribir palabras como: *emergencia*, *planes*, *nichos*, *traslado*, *ubicación*, etc."
)

claves_planes = ["plan", "planes", "servicio", "servicios", "paquete", "información", "informacion"]
claves_emergencia = ["emergencia", "urgente", "fallecido", "murió", "murio", "accidente", "suceso"]
claves_ubicacion = ["ubicación", "ubicaciones", "sucursal", "sucursales", "dirección", "direccion"]
claves_volver = ["volver", "menú", "menu", "inicio"]

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

    if estado.get("menu") == "emergencia":
        alerta = f"📨 *EMERGENCIA RECIBIDA*\nMensaje: {mensaje}\nDesde: {telefono}"
        requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
            "To": NUMERO_REENVIO,
            "From": "whatsapp:+14155238886",
            "Body": alerta
        })
        sesiones[telefono] = {}
        return responder("✅ Gracias. Hemos recibido tu emergencia. Un asesor te contactará de inmediato.")

    if estado.get("menu") == "ubicacion":
        if msj_lower in ["sí", "si"]:
            sesiones[telefono] = {"menu": "cita"}
            return responder(
                "📅 *Agendemos tu cita.*\n\n"
                "¿Qué día te gustaría visitarnos?\n"
                "¿En qué horario podrías acudir?\n\n"
                "Tu información será enviada a nuestro equipo."
            )
        else:
            sesiones[telefono] = {}
            return responder("✅ Gracias por consultar nuestras ubicaciones. Si necesitas otra información, escribe *menú*.")

    if estado.get("menu") == "cita":
        datos = f"📆 *CITA SOLICITADA*\nCliente: {telefono}\nDatos: {mensaje}"
        requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
            "To": NUMERO_REENVIO,
            "From": "whatsapp:+14155238886",
            "Body": datos
        })
        sesiones[telefono] = {}
        return responder("✅ Gracias. Hemos registrado tu solicitud. Nuestro equipo te contactará pronto.")

    if estado.get("menu") == "planes":
        if mensaje == "1":
            sesiones[telefono] = {"submenu": "inmediato"}
            return responder(
                "⏱️ *Planes de necesidad inmediata:*\n"
                "A. Crédito de necesidad inmediata\n"
                "B. Servicio paquete fetal cremación\n"
                "C. Servicio paquete sencillo sepultura\n"
                "D. Servicio paquete básico sepultura\n"
                "E. Servicio cremación directa\n"
                "F. Servicio paquete de cremación\n"
                "G. Servicio paquete legal\n"
                "H. Servicio de refrigeración y conservación\n\n"
                "Escribe la letra correspondiente para más información."
            )
        elif mensaje == "2":
            sesiones[telefono] = {"submenu": "futuro"}
            return responder(
                "🕰️ *Planes a futuro:*\n"
                "I. Red Biker\n"
                "J. Red Plus\n"
                "K. Red Consorcio\n"
                "L. Red Adulto Mayor\n"
                "M. Preventa de Nichos a Temporalidad\n\n"
                "Escribe la letra correspondiente para más información."
            )
        elif mensaje == "3":
            sesiones[telefono] = {"submenu": "servicios"}
            return responder(
                "🧰 *Servicios individuales:*\n"
                "N. Traslado\n"
                "O. Ataúd\n"
                "P. Urna\n"
                "Q. Velación\n"
                "R. Boletas\n"
                "S. Carroza local\n"
                "T. Carroza a panteón u horno crematorio\n"
                "U. Carroza legal\n"
                "V. Camión local\n"
                "W. Embalsamado\n"
                "X. Embalsamado legal\n"
                "Y. Embalsamado infecto-contagiosa\n"
                "Z. Trámites de inhumación\n"
                "AA. Trámites de cremación\n"
                "AB. Trámites legales\n"
                "AC. Trámites de traslado\n"
                "AD. Trámites de internación nacional\n"
                "AE. Trámites de internación internacional\n"
                "AF. Equipo de velación\n"
                "AG. Cirios\n"
                "AH. Capilla de gobierno\n"
                "AI. Capilla particular\n"
                "AJ. Traslado carretero por km\n"
                "AK. Traslado de terracería por km\n"
                "AL. Camión foráneo por km\n\n"
                "Escribe la letra correspondiente para más información."
            )

    if estado.get("submenu"):
        texto = responder_plan(msj_lower)
        if "No entendí tu mensaje" in texto:
            return responder("❌ No reconocimos tu selección. Intenta con otra letra o palabra clave del servicio que necesitas.")
        return responder(texto)

    return responder(MENSAJE_BIENVENIDA)
