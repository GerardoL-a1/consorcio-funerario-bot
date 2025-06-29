
from flask import Flask, request, jsonify
from planes_info import planes_info, responder_plan
import requests
import os

app = Flask(__name__)

# Claves seguras desde variables de entorno
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_MESSAGING_URL = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
TWILIO_AUTH = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

NUMERO_REENVIO = "+525523604519"

MENSAJE_BIENVENIDA = (
    "👋 *Bienvenido a Consorcio Funerario*\n\n"
    "Por favor selecciona una opción para continuar:\n\n"
    "1️⃣ Planes y Servicios\n"
    "2️⃣ Emergencias\n"
    "3️⃣ Ubicaciones\n\n"
    "_Responde con el número de la opción que deseas._"
)

def contiene_emergencia(mensaje):
    claves = ["fallecido", "suceso", "ubicación", "contacto"]
    return sum(p in mensaje for p in claves) >= 3

@app.route("/webhook", methods=["POST"])
def webhook():
    mensaje = request.form.get("Body", "").strip().lower()
    telefono_cliente = request.form.get("From", "")

    if mensaje in ["hola", "buenas", "buenos días", "buenas tardes", "inicio"]:
        return jsonify({"respuesta": MENSAJE_BIENVENIDA})

    if mensaje == "1":
        return jsonify({"respuesta": (
            "📋 *Planes y Servicios Disponibles*\n\n"
            "Puedes consultar cualquiera de nuestros planes o servicios individuales.\n\n"
            "🔹 *Planes fijos:*\n"
            "- crédito de necesidad inmediata\n"
            "- servicio paquete fetal cremación\n"
            "- servicio paquete sencillo sepultura\n"
            "- servicio paquete básico sepultura\n"
            "- servicio cremación directa\n"
            "- servicio paquete de cremación\n"
            "- servicio paquete legal\n"
            "- servicio de refrigeración y conservación\n"
            "- red biker\n"
            "- red plus\n"
            "- red consorcio\n"
            "- red adulto mayor\n"
            "- cremación amigo fiel\n"
            "- servicio paquete de cremación de restos áridos\n"
            "- preventa de nichos a temporalidad\n\n"
            "🔹 *Servicios individuales:*\n"
            "- traslado\n"
            "- ataúd\n"
            "- urna\n"
            "- velación\n"
            "- boletas\n\n"
            "✍️ Escribe el nombre del plan o servicio para más información."
        )})

    if mensaje == "2":
        return jsonify({"respuesta": (
            "🚨 *ATENCIÓN INMEDIATA*\n\n"
            "Por favor responde con los siguientes datos:\n\n"
            "🔹 Nombre completo del fallecido\n"
            "🔹 Suceso o causa del fallecimiento\n"
            "🔹 Ubicación actual del cuerpo\n"
            "🔹 Dos números de contacto\n\n"
            "📨 Esta información será enviada automáticamente a nuestro personal de atención."
        )})

    if mensaje == "3":
        return jsonify({"respuesta": (
            "📍 *Ubicaciones de atención presencial:*\n\n"
            "1. Av. Tláhuac No. 5502, Col. El Rosario, CDMX\n"
            "2. Av. Zacatlán No. 60, Col. San Lorenzo Tezonco, CDMX\n"
            "3. Av. Zacatlán No. 10, Col. San Lorenzo Tezonco, CDMX\n\n"
            "¿Deseas que un asesor te contacte para agendar una cita? (Sí/No)"
        )})

    # 🔴 Lógica de emergencia + reenvío
    if contiene_emergencia(mensaje):
        texto_alerta = f"📨 *NUEVA EMERGENCIA*\nMensaje: {mensaje}\nDesde: {telefono_cliente}"
        try:
            requests.post(
                TWILIO_MESSAGING_URL,
                auth=TWILIO_AUTH,
                data={
                    "To": NUMERO_REENVIO,
                    "From": "whatsapp:+14155238886",
                    "Body": texto_alerta
                }
            )
        except Exception as e:
            print("Error al reenviar mensaje de emergencia:", str(e))

    # 🔎 Revisión de palabra clave para planes o servicios
    respuesta_plan = responder_plan(mensaje)
    if "🔍 No encontré" not in respuesta_plan:
        return jsonify({"respuesta": respuesta_plan})

    # ❌ Si no se encuentra el plan ni hay coincidencias
    return jsonify({"respuesta": (
        "🤖 No entendí tu mensaje. Por favor escribe el nombre de un plan o servicio correctamente "
        "y si lo hiciste de manera correcta es posible que en estos momentos ese plan se encuentre en modificaciones."
    )})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
