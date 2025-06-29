from flask import Flask, request, jsonify
from planes_info import responder_plan
import requests
import os

app = Flask(__name__)

# Configuración segura
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_MESSAGING_URL = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
TWILIO_AUTH = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

NUMERO_REENVIO = "+525523604519"

def contiene_emergencia(mensaje):
    claves = ["fallecido", "suceso", "ubicación", "contacto", "encargado"]
    return sum(p in mensaje for p in claves) >= 3

@app.route("/webhook", methods=["POST"])
def webhook():
    mensaje = request.form.get("Body", "").strip().lower()
    telefono_cliente = request.form.get("From", "")

    if mensaje in ["hola", "inicio", "menú", "volver", "buenas", "buenos días", "buenas tardes"]:
        return jsonify({"respuesta": (
            "👋 *Bienvenido a Consorcio Funerario*\n\n"
            "Por favor selecciona una opción para continuar:\n\n"
            "1️⃣ Planes de Necesidad Inmediata\n"
            "2️⃣ Planes a Futuro\n"
            "3️⃣ Servicios Individuales\n"
            "4️⃣ Emergencias\n"
            "5️⃣ Ubicaciones\n\n"
            "_Responde con el número de la opción que deseas._"
        )})

    if mensaje == "1":
        return jsonify({"respuesta": (
            "⚡ *Planes de Necesidad Inmediata:*\n\n"
            "IM1. Crédito de necesidad inmediata\n"
            "IM2. Paquete fetal cremación\n"
            "IM3. Paquete sencillo sepultura\n"
            "IM4. Paquete básico sepultura\n"
            "IM5. Cremación directa\n"
            "IM6. Paquete de cremación\n"
            "IM7. Paquete legal\n"
            "IM8. Refrigeración y conservación\n\n"
            "✍️ Escribe el *código (ej. IM5)* o el *nombre del plan* para más información."
        )})

    if mensaje == "2":
        return jsonify({"respuesta": (
            "📅 *Planes a Futuro:*\n\n"
            "PF1. Red Biker\n"
            "PF2. Red Plus\n"
            "PF3. Red Consorcio\n"
            "PF4. Red Adulto Mayor\n"
            "PF5. Cremación Amigo Fiel\n"
            "PF6. Cremación de restos áridos\n"
            "PF7. Preventa de Nichos\n\n"
            "✍️ Escribe el *código (ej. PF1)* o el *nombre del plan* para más información."
        )})

    if mensaje == "3":
        return jsonify({"respuesta": (
            "🛠️ *Servicios Individuales:*\n\n"
            "SI1. Traslado\n"
            "SI2. Ataúd\n"
            "SI3. Urna\n"
            "SI4. Velación\n"
            "SI5. Boletas\n\n"
            "✍️ Escribe el *código (ej. SI3)* o el *nombre del servicio* para más información."
        )})

    if mensaje == "4":
        return jsonify({"respuesta": (
            "🚨 *ATENCIÓN INMEDIATA*\n\n"
            "Por favor responde con los siguientes datos:\n\n"
            "🔹 *Tu nombre completo (quien nos contacta)*\n"
            "🔹 Nombre del fallecido\n"
            "🔹 Suceso o causa del fallecimiento\n"
            "🔹 Ubicación actual del cuerpo\n"
            "🔹 Dos números de contacto\n\n"
            "📨 Esta información será enviada automáticamente a nuestro personal de atención."
        )})

    if mensaje == "5":
        return jsonify({"respuesta": (
            "📍 *Ubicaciones de atención presencial:*\n\n"
            "1. Av. Tláhuac No. 5502, Col. El Rosario, CDMX\n"
            "2. Av. Zacatlán No. 60, Col. San Lorenzo Tezonco, CDMX\n"
            "3. Av. Zacatlán No. 10, Col. San Lorenzo Tezonco, CDMX\n\n"
            "¿Te gustaría agendar una cita? (Sí / No)"
        )})

    # Flujo especial: agendar cita
    if mensaje == "sí" or mensaje == "si":
        return jsonify({"respuesta": (
            "📆 *Agenda tu cita presencial:*\n\n"
            "¿Qué día te gustaría visitarnos? (Ej. Martes)\n"
            "¿En qué horario aproximado nos visitarás?\n"
            "¿Qué ubicación prefieres? (1, 2 o 3)\n\n"
            "✅ Te responderemos confirmando disponibilidad."
        )})

    # Flujo de emergencia: reenvío automático
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
            print("❌ Error al reenviar mensaje de emergencia:", str(e))

    # Intentar responder por plan/servicio
    respuesta_plan = responder_plan(mensaje)
    if "🔍 No encontré" not in respuesta_plan:
        return jsonify({"respuesta": respuesta_plan})

    # Si no se encuentra el plan ni hay coincidencias
    return jsonify({"respuesta": (
        "🤖 No entendí tu mensaje. Por favor escribe el *nombre* o *código* de un plan o servicio correctamente. "
        "Si lo hiciste bien y no responde, puede que esté en revisión temporal."
    )})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
