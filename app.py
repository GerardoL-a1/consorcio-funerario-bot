from flask import Flask, request, jsonify
from planes_info import planes_info, responder_plan

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    mensaje = data.get("mensaje", "").lower()

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
            "Puedes consultar cualquier plan escribiendo su nombre. Ejemplos:\n"
            "- 'crédito de necesidad inmediata'\n"
            "- 'cremación directa'\n"
            "- 'paquete legal'\n"
            "\nEscribe el nombre del servicio que deseas consultar."
        )})

    if mensaje == "2":
        return jsonify({"respuesta": (
            "🚨 *ATENCIÓN INMEDIATA*\n"
            "Por favor responde con los siguientes datos para brindarte asistencia:\n\n"
            "🔹 Nombre completo del fallecido\n"
            "🔹 Suceso o causa del fallecimiento\n"
            "🔹 Ubicación actual del cuerpo\n"
            "🔹 Dos números de contacto\n\n"
            "Un asesor recibirá esta información de inmediato."
        )})

    if mensaje == "3":
        return jsonify({"respuesta": (
            "📍 *Ubicaciones de atención presencial:*\n\n"
            "1. Frente al Metro Sonco, CDMX\n"
            "2. Junto al Hospital General, CDMX\n"
            "3. Sucursal Centro Histórico\n\n"
            "¿Deseas que un asesor te contacte para agendar una cita o resolver dudas? (Sí/No)"
        )})

    respuesta_plan = responder_plan(mensaje)
    if "🔍 No encontré" not in respuesta_plan:
        return jsonify({"respuesta": respuesta_plan})

    return jsonify({"respuesta": "🤖 No entendí tu mensaje. Por favor escribe una opción válida o el nombre de un plan funerario."})

if __name__ == "__main__":
    app.run(debug=True)
