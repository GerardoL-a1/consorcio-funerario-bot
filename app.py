
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
            "👋 *Bienvenido a Consorcio Funerario*
"
            "Por favor selecciona una opción para continuar:

"
            "1️⃣ Planes y Servicios
"
            "2️⃣ Emergencias
"
            "3️⃣ Ubicaciones

"
            "_Responde con el número de la opción que deseas._"
        )})

    if mensaje == "1":
        return jsonify({"respuesta": (
            "📋 *Planes y Servicios Disponibles*
"
            "Puedes consultar cualquiera de nuestros planes o servicios individuales.

"
            "🔹 Planes fijos:
"
            "- crédito de necesidad inmediata
"
            "- servicio paquete fetal cremación
"
            "- servicio paquete sencillo sepultura
"
            "- servicio paquete básico sepultura
"
            "- servicio cremación directa
"
            "- servicio paquete de cremación
"
            "- servicio paquete legal
"
            "- servicio de refrigeración y conservación
"
            "- red biker
"
            "- red plus
"
            "- red consorcio
"
            "- red adulto mayor
"
            "- cremación amigo fiel
"
            "- servicio paquete de cremación de restos áridos
"
            "- preventa de nichos a temporalidad

"
            "🔹 Servicios individuales:
"
            "- traslado
"
            "- ataúd
"
            "- urna
"
            "- velación
"
            "- boletas

"
            "✍️ Escribe el nombre del plan o servicio para más información."
        )})

    if mensaje == "2":
        return jsonify({"respuesta": (
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
            "📨 Esta información será enviada automáticamente a nuestro personal de atención."
        )})

    if mensaje == "3":
        return jsonify({"respuesta": (
            "📍 *Ubicaciones de atención presencial:*
"
            "1. Av. Tláhuac No. 5502, Col. El Rosario, CDMX
"
            "2. Av. Zacatlán No. 60, Col. San Lorenzo Tezonco, CDMX
"
            "3. Av. Zacatlán No. 10, Col. San Lorenzo Tezonco, CDMX

"
            "¿Deseas que un asesor te contacte para agendar una cita? (Sí/No)"
        )})

    if contiene_emergencia(mensaje):
        texto_alerta = f"📨 *NUEVA EMERGENCIA*
Mensaje: {mensaje}
Desde: {telefono_cliente}"
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
