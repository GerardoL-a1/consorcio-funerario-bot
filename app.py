
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from planes_info import responder_plan
import requests
import os

app = Flask(__name__)

# Twilio config
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
    "Por favor selecciona una opción para continuar:\n"
    "1️⃣ Planes y Servicios\n"
    "2️⃣ Emergencias\n"
    "3️⃣ Ubicaciones"
)

contacto = ["hola", "holaaa", "ola", "holis", "buenas", "buen dia", "buenos dias", "saludos", "empezar", "iniciar", "info", "información", "ayuda"]
emergencia_claves = ["fallecido", "falleció", "suceso", "ubicación", "murio", "fallecio", "defuncion", "urgente", "emergencia", "perdimos", "hospital", "traslado"]

def contiene_emergencia(mensaje):
    return sum(p in mensaje.lower() for p in emergencia_claves) >= 1

def responder(texto):
    respuesta = MessagingResponse()
    respuesta.message(texto)
    return str(respuesta)

@app.route("/webhook", methods=["POST"])
def webhook():
    mensaje = request.form.get("Body", "").strip().lower()
    telefono = request.form.get("From", "")
    estado = sesiones.get(telefono, {})

    # Mostrar bienvenida solo si no hay sesión válida ni flujo
    if "menu" not in estado:
        if mensaje in ["1", "2", "3"]:
            sesiones[telefono] = {"menu": "temporal"}
        else:
            sesiones[telefono] = {"menu": "temporal"}
            return responder(MENSAJE_BIENVENIDA)

    if mensaje == "1":
        sesiones[telefono] = {"menu": "planes"}
        return responder(
            "📋 *Selecciona una categoría:*\n"
            "1. Planes de necesidad inmediata\n"
            "2. Planes a futuro\n"
            "3. Servicios individuales"
        )

    if estado.get("menu") == "planes":
        if mensaje == "1":
            sesiones[telefono]["submenu"] = "inmediato"
            return responder(
                "⏱️ *Planes de necesidad inmediata:*\n"
                "1. Crédito de necesidad inmediata\n"
                "2. Servicio paquete fetal cremación\n"
                "3. Servicio paquete sencillo sepultura\n"
                "4. Servicio paquete básico sepultura\n"
                "5. Servicio cremación directa\n"
                "6. Servicio paquete de cremación\n"
                "7. Servicio paquete legal\n"
                "8. Servicio de refrigeración y conservación\n\n"
                "Responde con el número del plan para ver detalles."
            )
        elif mensaje == "2":
            sesiones[telefono]["submenu"] = "futuro"
            return responder(
                "🕰️ *Planes a futuro:*\n"
                "1. Red Biker\n"
                "2. Red Plus\n"
                "3. Red Consorcio\n"
                "4. Red Adulto Mayor\n"
                "5. Preventa de Nichos a Temporalidad\n\n"
                "Responde con el número del plan para ver detalles."
            )
        elif mensaje == "3":
            sesiones[telefono]["submenu"] = "servicios"
            return responder(
                "🧰 *Servicios individuales:*\n"
                "1. Traslado\n"
                "2. Ataúd\n"
                "3. Urna\n"
                "4. Velación\n"
                "5. Boletas\n\n"
                "Responde con el número del servicio para ver detalles."
            )

    submenu = estado.get("submenu")
    if submenu:
        categorias = {
            "inmediato": [
                "crédito de necesidad inmediata", "servicio paquete fetal cremación",
                "servicio paquete sencillo sepultura", "servicio paquete básico sepultura",
                "servicio cremación directa", "servicio paquete de cremación",
                "servicio paquete legal", "servicio de refrigeración y conservación"
            ],
            "futuro": [
                "red biker", "red plus", "red consorcio",
                "red adulto mayor", "preventa de nichos a temporalidad"
            ],
            "servicios": ["traslado", "ataúd", "urna", "velación", "boletas"]
        }

        try:
            index = int(mensaje) - 1
            plan = categorias[submenu][index]
            respuesta = responder_plan(plan)
            if respuesta:
                return responder(respuesta + "\n\n📌 *¿Deseas consultar otro plan? Solo responde con otro número.*")
            else:
                return responder("🤖 Por favor escribe el nombre de un plan o servicio correctamente y si lo hiciste de manera correcta es posible que en estos momentos ese plan se encuentre en modificaciones.")
        except (ValueError, IndexError):
            return responder("❌ Opción no válida. Intenta nuevamente con un número correcto.")

    if mensaje == "2":
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

    if estado.get("menu") == "emergencia":
        if contiene_emergencia(mensaje) or len(mensaje.split()) >= 5:
            alerta = f"📨 *EMERGENCIA RECIBIDA*\nMensaje: {mensaje}\nDesde: {telefono}"
            requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
                "To": NUMERO_REENVIO,
                "From": "whatsapp:+14155238886",
                "Body": alerta
            })
            sesiones[telefono] = {}
            return responder("✅ Gracias. Hemos recibido tu emergencia. Un asesor te contactará de inmediato.")

    if mensaje == "3":
        sesiones[telefono] = {"menu": "ubicacion"}
        return responder(
            "📍 *Ubicaciones disponibles:*\n"
            "1. Av. Tláhuac No. 5502, Col. El Rosario, CDMX\n"
            "2. Av. Zacatlán No. 60, Col. San Lorenzo Tezonco, CDMX\n"
            "3. Av. Zacatlán No. 10, Col. San Lorenzo Tezonco, CDMX\n\n"
            "¿Deseas agendar una cita en alguna de nuestras sucursales? (Sí / No)"
        )

    if estado.get("menu") == "ubicacion" and mensaje in ["sí", "si"]:
        sesiones[telefono] = {"menu": "cita"}
        return responder(
            "📅 *Agendemos tu cita.*\n\n"
            "¿Qué día te gustaría visitarnos?\n"
            "¿En qué horario podrías acudir?\n\n"
            "Tu información será enviada a nuestro equipo."
        )

    if estado.get("menu") == "cita":
        aviso = f"📆 *CITA SOLICITADA*\nCliente: {telefono}\nDatos: {mensaje}"
        requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
            "To": NUMERO_REENVIO,
            "From": "whatsapp:+14155238886",
            "Body": aviso
        })
        sesiones[telefono] = {}
        return responder("✅ Gracias. Hemos registrado tu solicitud. Nuestro equipo te contactará pronto.")

    # Último intento por palabra clave directa
    posible = responder_plan(mensaje)
    if posible:
        return responder(posible)
    else:
        return responder("📌 Si necesitas ayuda, escribe *hola* o selecciona una opción del menú.")
        
