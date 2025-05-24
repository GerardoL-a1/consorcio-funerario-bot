
from flask import Flask, request
import openai
import os
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

openai.api_key = os.environ.get("OPENAI_API_KEY")

MENU_INICIAL = (
    "🌿 *Consorcio Funerario te da la bienvenida.*\n"
    "¿En qué podemos ayudarte?\n"
    "1️⃣ Promociones\n"
    "2️⃣ Planes funerarios\n"
    "3️⃣ Emergencias\n"
    "4️⃣ Ubicación\n\n"
    "Responde con el número de la opción."
)

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.values.get("Body", "").strip().lower()
    resp = MessagingResponse()
    msg = resp.message()

    if incoming_msg in ["hola", "buenas", "buenas tardes"]:
        msg.body(MENU_INICIAL)

    elif incoming_msg == "1":
        msg.body("📢 Nuestras promociones: Plan básico desde $193/mes. ¡Pregunta por disponibilidad esta semana!")

    elif incoming_msg == "2":
        msg.body("⚰️ Tenemos planes: Básico, Intermedio, Plus y Mi Última Voluntad. ¿Cuál te interesa conocer?")

    elif incoming_msg == "3":
        msg.body("🚨 Atención inmediata 24/7. Por favor escribe *EMERGENCIA* seguido del nombre y ubicación.")

    elif incoming_msg == "4":
        msg.body("📍 Estamos en Av. Tláhuac #5502, Iztapalapa, CDMX. También contamos con sucursales en San Lorenzo Tezonco.")

    else:
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente amable y profesional de una funeraria."},
                {"role": "user", "content": incoming_msg}
            ]
        )
        reply = completion.choices[0].message.content.strip()
    msg.body(reply)
    return str(resp), 200, {'Content-Type': 'application/xml'}

if __name__ == "__main__":
    app.run()
