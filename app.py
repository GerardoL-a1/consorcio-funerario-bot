
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
    "Por favor selecciona una opción para continuar:\n"
    "1️⃣ Planes y Servicios\n"
    "2️⃣ Emergencias\n"
    "3️⃣ Ubicaciones"
)

# Listas para reconocer comandos
contacto = ["hola", "holaaa", "ola", "holis", "buenas", "buen día", "saludos", "info", "ayuda"]
emergencia_claves = ["fallecido", "falleció", "murió", "hospital", "urgente", "emergencia", "traslado", "defunción"]
comandos_menu = [
    "menu", "menú", "meniu", "meenu", "men", "mn", "menuu", "inicio",
    "volver", "volber", "volv", "volverr", "regresar", "inicioo", "volber al menu"
]

def contiene_emergencia(mensaje):
    return any(p in mensaje.lower() for p in emergencia_claves)

def responder(texto):
    res = MessagingResponse()
    res.message(texto)
    return str(res)

def letra_a_indice(letra):
    return ord(letra.upper()) - 65

@app.route("/webhook", methods=["POST"])
def webhook():
    mensaje = request.form.get("Body", "").strip().lower()
    telefono = request.form.get("From", "")
    estado = sesiones.get(telefono, {})

    # Comando para regresar al menú principal
    if mensaje in comandos_menu:
        sesiones[telefono] = {}
        return responder(MENSAJE_BIENVENIDA)

    # Mostrar bienvenida si no hay flujo activo
    if "menu" not in estado:
        if mensaje not in ["1", "2", "3"]:
            sesiones[telefono] = {"menu": "principal"}
            return responder(MENSAJE_BIENVENIDA)
        else:
            sesiones[telefono] = {"menu": "principal"}

    # Menú principal
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
                "A. Crédito de necesidad inmediata\n"
                "B. Servicio paquete fetal cremación\n"
                "C. Servicio paquete sencillo sepultura\n"
                "D. Servicio paquete básico sepultura\n"
                "E. Servicio cremación directa\n"
                "F. Servicio paquete de cremación\n"
                "G. Servicio paquete legal\n"
                "H. Servicio de refrigeración y conservación\n\n"
                "Escribe la *letra* del plan que deseas consultar."
            )
        elif mensaje == "2":
            sesiones[telefono]["submenu"] = "futuro"
            return responder(
                "🕰️ *Planes a futuro:*\n"
                "I. Red Biker\n"
                "J. Red Plus\n"
                "K. Red Consorcio\n"
                "L. Red Adulto Mayor\n"
                "M. Preventa de Nichos a Temporalidad\n\n"
                "Escribe la *letra* del plan que deseas consultar."
            )
        elif mensaje == "3":
            sesiones[telefono]["submenu"] = "servicios"
            return responder(
                "🧰 *Servicios individuales:*\n"
                "N. Traslado\n"
                "O. Ataúd\n"
                "P. Urna\n"
                "Q. Velación\n"
                "R. Boletas\n\n"
                "Escribe la *letra* del servicio que deseas consultar."
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
            index = letra_a_indice(mensaje)
            plan = categorias[submenu][index]
            respuesta = responder_plan(plan)
            if respuesta:
                return responder(respuesta + "\n\n✉️ *¿Deseas consultar otro? Solo escribe otra letra.*")
            else:
                return responder("🤖 El plan existe pero está en mantenimiento. Intenta más tarde.")
        except (IndexError, ValueError):
            return responder("❌ Letra inválida. Intenta con una opción del menú.")

    # Emergencias
    if mensaje == "2":
        sesiones[telefono] = {"menu": "emergencia"}
        return responder(
            "🚨 *ATENCIÓN INMEDIATA*\n\n"
            "Responde con:\n"
            "🔹 Nombre del fallecido\n"
            "🔹 Qué ocurrió\n"
            "🔹 Ubicación del cuerpo\n"
            "🔹 Dos teléfonos de contacto\n"
            "🔹 Tu nombre"
        )

    if estado.get("menu") == "emergencia":
        if contiene_emergencia(mensaje) or len(mensaje.split()) >= 6:
            alerta = f"📨 *EMERGENCIA RECIBIDA*\nDesde: {telefono}\n\n{mensaje}"
            requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
                "To": NUMERO_REENVIO,
                "From": "whatsapp:+14155238886",
                "Body": alerta
            })
            sesiones[telefono] = {}
            return responder("✅ Gracias. Hemos recibido tu emergencia. Un asesor te contactará pronto.")

    # Ubicaciones y citas
    if mensaje == "3":
        sesiones[telefono] = {"menu": "ubicacion"}
        return responder(
            "📍 *Ubicaciones disponibles:*\n"
            "1. Av. Tláhuac No. 5502, Col. El Rosario, CDMX\n"
            "2. Av. Zacatlán No. 60, Col. San Lorenzo Tezonco\n"
            "3. Av. Zacatlán No. 10, Col. San Lorenzo Tezonco\n\n"
            "¿Deseas agendar una cita? (Sí / No)"
        )

    if estado.get("menu") == "ubicacion" and mensaje in ["sí", "si"]:
        sesiones[telefono] = {"menu": "cita"}
        return responder(
            "📅 *Agendemos tu cita.*\n\n"
            "¿Qué día te gustaría venir?\n"
            "¿En qué horario te acomoda?\n\n"
            "Tu respuesta será enviada a nuestro equipo."
        )

    if estado.get("menu") == "cita":
        aviso = f"📆 *CITA SOLICITADA*\nCliente: {telefono}\nDatos:\n{mensaje}"
        requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
            "To": NUMERO_REENVIO,
            "From": "whatsapp:+14155238886",
            "Body": aviso
        })
        sesiones[telefono] = {}
        return responder("✅ Gracias. Hemos registrado tu cita. Nos pondremos en contacto.")

    # Última opción: palabra clave directa
    posible = responder_plan(mensaje)
    if posible:
        return responder(posible)
    else:
        return responder("📌 Si necesitas ayuda, escribe *hola* o selecciona una opción del menú.")
