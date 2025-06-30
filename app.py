
from flask import Flask, request, jsonify
from planes_info import responder_plan
import requests
import os

app = Flask(__name__)

# Claves seguras desde variables de entorno
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_MESSAGING_URL = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
TWILIO_AUTH = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

NUMERO_REENVIO = "+525523604519"

# Estados de sesión por número
sesiones = {}

# Ruta raíz para evitar errores 404
@app.route("/", methods=["GET"])
def home():
    return "✅ Consorcio Funerario Bot está corriendo correctamente."

MENSAJE_BIENVENIDA = (
    "👋 *Bienvenido a Consorcio Funerario*\n\n"
    "Por favor selecciona una opción para continuar:\n"
    "1️⃣ Planes y Servicios\n"
    "2️⃣ Emergencias\n"
    "3️⃣ Ubicaciones"
)

def contiene_emergencia(mensaje):
    claves = ["fallecido", "suceso", "ubicación", "contacto"]
    return sum(p in mensaje for p in claves) >= 3

@app.route("/webhook", methods=["POST"])
def webhook():
    mensaje = request.form.get("Body", "").strip().lower()
    telefono = request.form.get("From", "")
    estado = sesiones.get(telefono, {})

    if mensaje in ["hola", "inicio", "empezar", "buenas"]:
        sesiones[telefono] = {}
        return jsonify({"respuesta": MENSAJE_BIENVENIDA})

    # MENÚ PRINCIPAL
    if mensaje == "1":
        sesiones[telefono] = {"menu": "planes"}
        return jsonify({"respuesta": (
            "📋 *Selecciona una categoría:*\n"
            "1. Planes de necesidad inmediata\n"
            "2. Planes a futuro\n"
            "3. Servicios individuales"
        )})

    if estado.get("menu") == "planes":
        if mensaje == "1":
            sesiones[telefono] = {"submenu": "inmediato"}
            return jsonify({"respuesta": (
                "⏱️ *Planes de necesidad inmediata:*\n"
                "1. Crédito de necesidad inmediata\n"
                "2. Servicio paquete fetal cremación\n"
                "3. Servicio paquete sencillo sepultura\n"
                "4. Servicio paquete básico sepultura\n"
                "5. Servicio cremación directa\n"
                "6. Servicio paquete de cremación\n"
                "7. Servicio paquete legal\n"
                "8. Servicio de refrigeración y conservación\n"
                "Responde con el número del plan para más detalles."
            )})
        elif mensaje == "2":
            sesiones[telefono] = {"submenu": "futuro"}
            return jsonify({"respuesta": (
                "🕰️ *Planes a futuro:*\n"
                "1. Red Biker\n"
                "2. Red Plus\n"
                "3. Red Consorcio\n"
                "4. Red Adulto Mayor\n"
                "5. Preventa de Nichos a Temporalidad\n"
                "Responde con el número del plan para más detalles."
            )})
        elif mensaje == "3":
            sesiones[telefono] = {"submenu": "servicios"}
            return jsonify({"respuesta": (
                "🧰 *Servicios individuales:*\n"
                "1. Traslado\n"
                "2. Ataúd\n"
                "3. Urna\n"
                "4. Velación\n"
                "5. Boletas\n"
                "Responde con el número del servicio para más detalles."
            )})

    if estado.get("submenu"):
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
            plan = categorias[estado["submenu"]][index]
            respuesta = responder_plan(plan)
            return jsonify({"respuesta": respuesta})
        except (ValueError, IndexError):
            return jsonify({"respuesta": "❌ Opción no válida. Intenta nuevamente con un número correcto."})

    # ATENCIÓN A EMERGENCIAS
    if mensaje == "2":
        return jsonify({"respuesta": (
            "🚨 *ATENCIÓN INMEDIATA*\n\n"
            "Por favor responde con los siguientes datos:\n"
            "🔹 Nombre completo del fallecido\n"
            "🔹 Suceso o causa del fallecimiento\n"
            "🔹 Ubicación actual del cuerpo\n"
            "🔹 Dos números de contacto\n"
            "🔹 Nombre de la persona que nos está contactando"
        )})

    if contiene_emergencia(mensaje):
        alerta = f"📨 *EMERGENCIA RECIBIDA*\nMensaje: {mensaje}\nDesde: {telefono}"
        requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
            "To": NUMERO_REENVIO,
            "From": "whatsapp:+14155238886",
            "Body": alerta
        })

    # UBICACIONES
    if mensaje == "3":
        sesiones[telefono] = {"menu": "ubicacion"}
        return jsonify({"respuesta": (
            "📍 *Ubicaciones disponibles:*\n"
            "1. Av. Tláhuac No. 5502, Col. El Rosario, CDMX\n"
            "2. Av. Zacatlán No. 60, Col. San Lorenzo Tezonco, CDMX\n"
            "3. Av. Zacatlán No. 10, Col. San Lorenzo Tezonco, CDMX\n\n"
            "¿Deseas agendar una cita en alguna de nuestras sucursales? (Sí / No)"
        )})

    if estado.get("menu") == "ubicacion" and mensaje == "sí":
        sesiones[telefono] = {"menu": "cita"}
        return jsonify({"respuesta": (
            "📅 *Agendemos tu cita.*\n\n"
            "¿Qué día te gustaría visitarnos?\n"
            "¿En qué horario podrías acudir?\n\n"
            "Tu información será enviada a nuestro equipo."
        )})

    if estado.get("menu") == "cita":
        aviso = f"📆 *CITA SOLICITADA*\nCliente: {telefono}\nDatos: {mensaje}"
        requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
            "To": NUMERO_REENVIO,
            "From": "whatsapp:+14155238886",
            "Body": aviso
        })
        sesiones[telefono] = {}
        return jsonify({"respuesta": "✅ Gracias. Hemos registrado tu solicitud. Nuestro equipo te contactará pronto."})

    # RESPUESTA GENERAL
    return jsonify({"respuesta": (
        "🤖 No entendí tu mensaje. Escribe 'hola' para comenzar de nuevo o selecciona una opción del menú principal."
    )})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port
    
