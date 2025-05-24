from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

MENU_INICIAL = (
    "🌿 *Consorcio Funerario te da la bienvenida.*\n"
    "¿En qué podemos ayudarte?\n\n"
    "1️⃣ Promociones\n"
    "2️⃣ Planes funerarios\n"
    "3️⃣ Emergencias\n"
    "4️⃣ Ubicación\n"
    "Escribe el número de la opción que deseas."
)

# Base de datos simplificada (puedes ampliarla luego)
base_respuestas = [
    {
        "intenciones": ["hola", "buenos días", "buenas tardes", "buenas"],
        "respuesta": MENU_INICIAL
    },
    {
        "intenciones": ["qué servicios tienen", "hacen cremación", "traslados", "servicios funerarios"],
        "respuesta": "Ofrecemos servicios funerarios integrales como cremación, embalsamado, traslado local y nacional, sala de velación, entre otros."
    },
    {
        "intenciones": ["cuánto cuesta", "qué planes", "hay mensualidades"],
        "respuesta": "Tenemos planes desde $7,540 MXN, con opción de pago en mensualidades desde $193."
    },
    {
        "intenciones": ["promoción", "planes a futuro", "tranquilidad individual", "familiar"],
        "respuesta": "Contamos con planes Tranquilidad Individual y Tranquilidad Familiar. Pregunta por nuestras promociones actuales."
    },
    {
        "intenciones": ["falleció", "urgente", "emergencia", "ayuda urgente"],
        "respuesta": "Lamentamos su pérdida. Para atención inmediata, por favor llame al 55 23 68 07 34. Estamos para servirle."
    }
]

@app.route("/webhook", methods=["POST"])
def whatsapp():
    incoming_msg = request.values.get("Body", "").strip().lower()
    resp = MessagingResponse()
    msg = resp.message()

    respuesta = None

    # Opciones directas por número
    if incoming_msg in ["1", "promociones"]:
        respuesta = "Actualmente tenemos promociones en planes desde $193/mes. ¿Te gustaría que un asesor te contacte?"
    elif incoming_msg in ["2", "planes", "planes funerarios"]:
        respuesta = "Nuestros planes: Básico, Intermedio, Plus y Mi Última Voluntad. ¿Cuál te interesa conocer?"
    elif incoming_msg in ["3", "emergencia", "urgente"]:
        respuesta = "⛑ Atención inmediata 24/7. Por favor escribe *EMERGENCIA* seguido del nombre y ubicación."
    elif incoming_msg in ["4", "ubicación"]:
        respuesta = "📍 Estamos en Av. Tláhuac #5502, Iztapalapa, CDMX. También contamos con sucursales en San Lorenzo Tezonco."
    else:
        for entrada in base_respuestas:
            for intento in entrada["intenciones"]:
                if intento in incoming_msg:
                    respuesta = entrada["respuesta"]
                    break
            if respuesta:
                break

    if not respuesta:
        respuesta = "Gracias por su mensaje. Un asesor se comunicará con usted en breve."

    msg.body(respuesta)
    return str(resp), 200, {'Content-Type': 'application/xml'}

if __name__ == "__main__":
    app.run()
