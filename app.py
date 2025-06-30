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

MENSAJE_BIENVENIDA = (
    "👋 *Bienvenido a Consorcio Funerario*"

"
    "Por favor selecciona una opción para continuar:
"
    "1️⃣ Planes y Servicios
"
    "2️⃣ Emergencias
"
    "3️⃣ Ubicaciones"
)

def contiene_emergencia(mensaje):
    claves = ["fallecido", "suceso", "ubicación", "contacto"]
    return sum(p in mensaje for p in claves) >= 3

@app.route("/webhook", methods=["POST"])
def webhook():
    mensaje = request.form.get("Body", "").strip().lower()
    telefono = request.form.get("From", "")

    # Si es nuevo usuario o reinicia con "hola", "inicio", etc.
    if mensaje in ["hola", "inicio", "empezar", "buenas"]:
        sesiones[telefono] = {}
        return MENSAJE_BIENVENIDA

    estado = sesiones.get(telefono, {})

    # MENÚ PRINCIPAL
    if mensaje == "1":
        sesiones[telefono] = {"menu": "planes"}
        return (
            "📋 *Selecciona una categoría:*
"
            "1. Planes de necesidad inmediata
"
            "2. Planes a futuro
"
            "3. Servicios individuales"
        )

    if estado.get("menu") == "planes":
        if mensaje == "1":
            sesiones[telefono] = {"submenu": "inmediato"}
            return (
                "⏱️ *Planes de necesidad inmediata:*
"
                "1. Crédito de necesidad inmediata
"
                "2. Servicio paquete fetal cremación
"
                "3. Servicio paquete sencillo sepultura
"
                "4. Servicio paquete básico sepultura
"
                "5. Servicio cremación directa
"
                "6. Servicio paquete de cremación
"
                "7. Servicio paquete legal
"
                "8. Servicio de refrigeración y conservación
"
                "Responde con el número del plan para más detalles."
            )
        elif mensaje == "2":
            sesiones[telefono] = {"submenu": "futuro"}
            return (
                "🕰️ *Planes a futuro:*
"
                "1. Red Biker
"
                "2. Red Plus
"
                "3. Red Consorcio
"
                "4. Red Adulto Mayor
"
                "5. Preventa de Nichos a Temporalidad
"
                "Responde con el número del plan para más detalles."
            )
        elif mensaje == "3":
            sesiones[telefono] = {"submenu": "servicios"}
            return (
                "🧰 *Servicios individuales:*
"
                "1. Traslado
"
                "2. Ataúd
"
                "3. Urna
"
                "4. Velación
"
                "5. Boletas
"
                "Responde con el número del servicio para más detalles."
            )

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
            return respuesta
        except:
            return "❌ Opción no válida. Intenta nuevamente con un número correcto."

    # ATENCIÓN A EMERGENCIAS
    if mensaje == "2":
        return (
            "🚨 *ATENCIÓN INMEDIATA*

"
            "Por favor responde con los siguientes datos:
"
            "🔹 Nombre completo del fallecido
"
            "🔹 Suceso o causa del fallecimiento
"
            "🔹 Ubicación actual del cuerpo
"
            "🔹 Dos números de contacto
"
            "🔹 Nombre de la persona que nos está contactando
"
        )

    if contiene_emergencia(mensaje):
        alerta = f"📨 *EMERGENCIA RECIBIDA*
Mensaje: {mensaje}
Desde: {telefono}"
        requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
            "To": NUMERO_REENVIO,
            "From": "whatsapp:+14155238886",
            "Body": alerta
        })

    # UBICACIONES
    if mensaje == "3":
        sesiones[telefono] = {"menu": "ubicacion"}
        return (
            "📍 *Ubicaciones disponibles:*
"
            "1. Av. Tláhuac No. 5502, Col. El Rosario, CDMX
"
            "2. Av. Zacatlán No. 60, Col. San Lorenzo Tezonco, CDMX
"
            "3. Av. Zacatlán No. 10, Col. San Lorenzo Tezonco, CDMX

"
            "¿Deseas agendar una cita en alguna de nuestras sucursales? (Sí / No)"
        )

    if estado.get("menu") == "ubicacion" and mensaje == "sí":
        sesiones[telefono] = {"menu": "cita"}
        return (
            "📅 *Agendemos tu cita.*

"
            "¿Qué día te gustaría visitarnos?
"
            "¿En qué horario podrías acudir?

"
            "Tu información será enviada a nuestro equipo."
        )

    if estado.get("menu") == "cita":
        aviso = f"📆 *CITA SOLICITADA*
Cliente: {telefono}
Datos: {mensaje}"
        requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
            "To": NUMERO_REENVIO,
            "From": "whatsapp:+14155238886",
            "Body": aviso
        })
        sesiones[telefono] = {}
        return "✅ Gracias. Hemos registrado tu solicitud. Nuestro equipo te contactará pronto."

    # RESPUESTA GENERAL
    return (
        "🤖 No entendí tu mensaje. Escribe 'hola' para comenzar de nuevo o selecciona una opción del menú principal."
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
