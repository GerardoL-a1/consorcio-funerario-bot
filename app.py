
from flask import Flask, request, jsonify
from planes_info import planes_info, responder_plan
import requests

app = Flask(__name__)

NUMERO_REENVIO = "+525523604519"
TWILIO_MESSAGING_URL = "https://api.twilio.com/2010-04-01/Accounts/AC2ebbbb56dde3f32650225d802cd993fb7/Messages.json"
TWILIO_AUTH = ("AC2ebbbb56dde3f32650225d802cd993fb7", "923d6dee710839a29f1079e710e37fe4")

def contiene_emergencia(mensaje):
    claves = ["fallecido", "suceso", "ubicación", "contacto"]
    return sum(p in mensaje for p in claves) >= 3

# Respuesta base para todos los mensajes
def respuesta_bienvenida():
    return (
        "👋 *Bienvenido a Consorcio Funerario*\n\n"
        "Por favor selecciona una opción para continuar:\n\n"
        "1️⃣ Planes y Servicios\n"
        "2️⃣ Emergencias\n"
        "3️⃣ Ubicaciones\n\n"
        "_Responde con el número de la opción que deseas._"
    )

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    mensaje = data.get("mensaje", "").lower()
    telefono_cliente = data.get("from", "")

    respuesta = respuesta_bienvenida()

    if mensaje == "1":
        respuesta += "\n\n📋 *Planes y Servicios Disponibles*\n\n" \
                     "🔹 *Planes fijos:*\n" \
                     "- crédito de necesidad inmediata\n" \
                     "- servicio paquete fetal cremación\n" \
                     "- servicio paquete sencillo sepultura\n" \
                     "- servicio paquete básico sepultura\n" \
                     "- servicio cremación directa\n" \
                     "- servicio paquete de cremación\n" \
                     "- servicio paquete legal\n" \
                     "- servicio de refrigeración y conservación\n" \
                     "- red biker\n" \
                     "- red plus\n" \
                     "- red consorcio\n" \
                     "- red adulto mayor\n" \
                     "- cremación amigo fiel\n" \
                     "- servicio paquete de cremación de restos áridos\n" \
                     "- preventa de nichos a temporalidad\n\n" \
                     "🔹 *Servicios individuales:*\n" \
                     "- traslado\n" \
                     "- ataúd\n" \
                     "- urna\n" \
                     "- velación\n" \
                     "- boletas\n\n" \
                     "✍️ Escribe el nombre del plan o servicio para más información."

    elif mensaje == "2":
        respuesta += "\n\n🚨 *ATENCIÓN INMEDIATA*\n\n" \
                     "Por favor responde con los siguientes datos:\n\n" \
                     "🔹 Nombre completo del fallecido\n" \
                     "🔹 Suceso o causa del fallecimiento\n" \
                     "🔹 Ubicación actual del cuerpo\n" \
                     "🔹 Dos números de contacto\n\n" \
                     "📨 Esta información será enviada automáticamente a nuestro personal de atención."

    elif mensaje == "3":
        respuesta += "\n\n📍 *Ubicaciones de atención presencial:*\n\n" \
                     "1. Av. Tláhuac No. 5502, Col. El Rosario, CDMX\n" \
                     "2. Av. Zacatlán No. 60, Col. San Lorenzo Tezonco, CDMX\n" \
                     "3. Av. Zacatlán No. 10, Col. San Lorenzo Tezonco, CDMX\n\n" \
                     "¿Deseas que un asesor te contacte para agendar una cita? (Sí/No)"

    # Reenvío automático si es emergencia
    if contiene_emergencia(mensaje):
        texto_alerta = f"📨 *NUEVA EMERGENCIA*\nMensaje: {mensaje}\nDesde: {telefono_cliente}"
        requests.post(
            TWILIO_MESSAGING_URL,
            auth=TWILIO_AUTH,
            data={
                "To": NUMERO_REENVIO,
                "From": "whatsapp:+14155238886",
                "Body": texto_alerta
            }
        )

    # Checar si el mensaje coincide con un plan
    respuesta_plan = responder_plan(mensaje)
    if "🔍 No encontré" not in respuesta_plan:
        respuesta += f"\n\n📄 *Información del plan solicitado:*\n{respuesta_plan}"

    return jsonify({"respuesta": respuesta})

if __name__ == "__main__":
    app.run(debug=True)
