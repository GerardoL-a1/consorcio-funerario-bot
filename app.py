
from flask import Flask, request, jsonify
from planes_info import planes_info, responder_plan
import requests

app = Flask(__name__)

NUMERO_REENVIO = "+525523604519"
TWILIO_MESSAGING_URL = "https://api.twilio.com/2010-04-01/Accounts/YOUR_ACCOUNT_SID/Messages.json"
TWILIO_AUTH = ("YOUR_ACCOUNT_SID", "YOUR_AUTH_TOKEN")

def contiene_emergencia(mensaje):
    claves = ["fallecido", "suceso", "ubicación", "contacto"]
    return sum(p in mensaje for p in claves) >= 3

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    mensaje = data.get("mensaje", "").lower()
    telefono_cliente = data.get("from", "")

    if mensaje in ["hola", "buenas", "buenos días", "buenas tardes", "inicio"]:
        return jsonify({"respuesta": (
            "👋 *Bienvenido a Consorcio Funerario*\n"
            "Por favor selecciona una opción para continuar:\n\n"
            "1️⃣ Planes y Servicios\n"
            "2️⃣ Emergencias\n"
            "3️⃣ Ubicaciones\n\n"
            "_Responde con el número de la opción que deseas._"
        )})

    if mensaje == "1":
        return jsonify({"respuesta": (
            "📋 *Planes y Servicios Disponibles*\n"
            "Puedes consultar cualquiera de nuestros planes o servicios individuales.\n\n"
            "🔹 Planes fijos:\n"
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
            "🔹 Servicios individuales:\n"
            "- traslado\n"
            "- ataúd\n"
            "- urna\n"
            "- velación\n"
            "- boletas\n\n"
            "✍️ Escribe el nombre del plan o servicio para más información."
        )})

    if mensaje == "2":
        return jsonify({"respuesta": (
            "🚨 *ATENCIÓN INMEDIATA*\n"
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

    if contiene_emergencia(mensaje):
        texto_alerta = (
            f"📨 *NUEVA EMERGENCIA*\n"
            f"Mensaje: {mensaje}\n"
            f"Desde: {telefono_cliente}"
        )
        requests.post(
            TWILIO_MESSAGING_URL,
            auth=TWILIO_AUTH,
            data={
                "To": NUMERO_REENVIO,
                "From": "whatsapp:+14155238886",
                "Body": texto_alerta
            }
        )

    respuesta_plan = responder_plan(mensaje)
    if "🔍 No encontré" not in respuesta_plan:
        return jsonify({"respuesta": respuesta_plan})

    return jsonify({"respuesta": "🤖 No entendí tu mensaje. Por favor escribe el nombre de un plan o servicio válido."})

if __name__ == "__main__":
    app.run(debug=True)
