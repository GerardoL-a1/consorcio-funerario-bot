
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from planes_info import responder_plan
import requests
import os
import re

app = Flask(__name__)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_MESSAGING_URL = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
TWILIO_AUTH = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

NUMERO_REENVIO = "+525523604519"
sesiones = {}

@app.route("/", methods=["GET"])
def home():
    return "✅ Bot Consorcio Funerario funcionando."

MENSAJE_BIENVENIDA = (
    "👋 *Bienvenido a Consorcio Funerario*\n\n"
    "Gracias por escribirnos.\n\n"
    "Por favor indíquenos *en qué podemos apoyarle o brindarle información*:\n"
    "- Atención inmediata por *emergencia*\n"
    "- Conocer nuestros *servicios funerarios*\n"
    "- Consultar nuestras *ubicaciones disponibles*\n\n"
    "📌 Puede escribir palabras como: *emergencia*, *planes*, *nichos*, *traslado*, *ubicación*, etc."
)

claves_planes = ["planes", "servicios", "funerarios", "plan", "sepultura", "cremacion", "legal", "biker", "plus", "consorcio", "adulto", "nichos", "fetal"]
claves_emergencia = ["emergencia", "fallecido", "falleció", "murio", "hospital", "traslado", "recoleccion", "suceso", "defuncion"]
claves_ubicacion = ["ubicación", "sucursal", "donde", "direccion", "ubicaciones", "están"]
claves_menu = ["menú", "menu", "volver", "inicio", "regresar", "empezar"]

submenus = {
    "inmediato": {
        "letras": list("ABCDEFGH"),
        "planes": [
            "crédito de necesidad inmediata", "servicio paquete fetal cremación",
            "servicio paquete sencillo sepultura", "servicio paquete básico sepultura",
            "servicio cremación directa", "servicio paquete de cremación",
            "servicio paquete legal", "servicio de refrigeración y conservación"
        ]
    },
    "futuro": {
        "letras": list("IJKLM"),
        "planes": [
            "red biker", "red plus", "red consorcio",
            "red adulto mayor", "preventa de nichos a temporalidad"
        ]
    },
    "servicios": {
        "letras": list("NOPQRSTUVWXYZ"),
        "planes": [
            "traslado", "ataúd", "urna", "velación", "boletas",
            "carroza local", "carroza a panteón u horno crematorio", "carroza legal", "camión local",
            "embalsamado", "embalsamado legal", "embalsamado infecto-contagiosa", "trámites de inhumación",
            "trámites de cremación", "trámites legales", "trámites de traslado",
            "trámites de internación nacional", "trámites de internación internacional",
            "equipo de velación", "cirios", "capilla de gobierno", "capilla particular",
            "traslado carretero por km", "traslado de terracería por km", "camión foráneo por km"
        ]
    }
}

def contiene(palabras, mensaje):
    return any(p in mensaje.lower() for p in palabras)

def normaliza(texto):
    return re.sub(r"[^a-z0-9áéíóúñ ]", "", texto.lower())

def buscar_plan_por_clave(mensaje):
    mensaje = normaliza(mensaje)
    for categoria in submenus.values():
        for plan in categoria["planes"]:
            if any(p in mensaje for p in plan.split()):
                return responder_plan(plan)
    return None

def responder(texto):
    r = MessagingResponse()
    r.message(texto)
    return str(r)

@app.route("/webhook", methods=["POST"])
def webhook():
    mensaje = request.form.get("Body", "").strip().lower()
    telefono = request.form.get("From", "")
    estado = sesiones.get(telefono, {})

    if contiene(claves_menu, mensaje):
        sesiones[telefono] = {}
        return responder(MENSAJE_BIENVENIDA)

    if "menu" not in estado:
        if contiene(claves_emergencia, mensaje):
            sesiones[telefono] = {"menu": "emergencia"}
        elif contiene(claves_planes, mensaje):
            sesiones[telefono] = {"menu": "planes"}
        elif contiene(claves_ubicacion, mensaje):
            sesiones[telefono] = {"menu": "ubicacion"}
        else:
            sesiones[telefono] = {"menu": "principal"}
            return responder(MENSAJE_BIENVENIDA)

    if estado.get("menu") == "emergencia":
        if len(mensaje.split()) >= 5 or contiene(claves_emergencia, mensaje):
            alerta = f"📨 *EMERGENCIA RECIBIDA*\nDesde: {telefono}\n\n{mensaje}"
            requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
                "To": NUMERO_REENVIO,
                "From": "whatsapp:+14155238886",
                "Body": alerta
            })
            sesiones[telefono] = {}
            return responder("✅ Gracias. Hemos recibido tu emergencia. Un asesor te contactará de inmediato.")
        else:
            return responder("📝 Por favor, indícanos: nombre del fallecido, ubicación y contacto.")

    if estado.get("menu") == "ubicacion":
        sesiones[telefono] = {"menu": "ubicacion-confirmada"}
        return responder(
            "📍 *Ubicaciones disponibles:*\n"
            "1. Av. Tláhuac No. 5502, Col. El Rosario, CDMX\n"
            "2. Av. Zacatlán No. 60, Col. San Lorenzo Tezonco\n"
            "3. Av. Zacatlán No. 10, Col. San Lorenzo Tezonco\n\n"
            "¿Deseas agendar una cita? (Sí / No)"
        )

    if estado.get("menu") == "ubicacion-confirmada" and mensaje in ["sí", "si"]:
        sesiones[telefono] = {"menu": "cita"}
        return responder("📅 Indícanos día y horario para agendar tu cita.")

    if estado.get("menu") == "cita":
        aviso = f"📆 *CITA SOLICITADA*\nCliente: {telefono}\nDatos: {mensaje}"
        requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
            "To": NUMERO_REENVIO,
            "From": "whatsapp:+14155238886",
            "Body": aviso
        })
        sesiones[telefono] = {}
        return responder("✅ Cita registrada. Un asesor te contactará para confirmar.")

    if estado.get("menu") == "planes":
        for clave, grupo in submenus.items():
            if mensaje in [clave, clave[:3]]:
                sesiones[telefono] = {"submenu": clave}
                letras = grupo["letras"]
                nombres = grupo["planes"]
                lista = "\n".join([f"{letras[i]}. {nombres[i].capitalize()}" for i in range(len(letras))])
                return responder(f"📋 *{clave.upper()}*\n{lista}\n\nSelecciona la letra o escribe palabras clave como 'biker', 'nichos', etc.")

    if "submenu" in estado:
        grupo = submenus.get(estado["submenu"])
        letras = grupo["letras"]
        nombres = grupo["planes"]
        letra = mensaje.strip().upper()[:1]
        if letra in letras:
            plan = nombres[letras.index(letra)]
            respuesta = responder_plan(plan)
            if respuesta:
                return responder(respuesta + "\n\n✉️ Puedes consultar otro o escribir *menú*.")
        else:
            posible = buscar_plan_por_clave(mensaje)
            if posible:
                return responder(posible + "\n\n✉️ Puedes consultar otro o escribir *menú*.")
            else:
                intentos = estado.get("intentos", 0) + 1
                sesiones[telefono]["intentos"] = intentos
                if intentos == 1:
                    return responder("❌ No reconocimos tu selección. Intenta otra letra o palabra clave del servicio que necesitas.")
                elif intentos == 2:
                    return responder("📌 El plan o servicio que mencionas podría estar en mantenimiento o no disponible actualmente. Si deseas más ayuda, puedes escribirnos directamente.")
                else:
                    if "submenu" in sesiones[telefono]:
                        submenu = sesiones[telefono]["submenu"]
                        letras = submenus[submenu]["letras"]
                        nombres = submenus[submenu]["planes"]
                        lista = "\n".join([f"{letras[i]}. {nombres[i].capitalize()}" for i in range(len(letras))])
                        return responder(f"📋 *{submenu.upper()}*\n{lista}\n\nSelecciona la letra o escribe palabras clave como 'biker', 'nichos', etc.")
                    else:
                        sesiones[telefono] = {}
                        return responder(MENSAJE_BIENVENIDA)

    posible = buscar_plan_por_clave(mensaje)
    if posible:
        return responder(posible + "\n\n✉️ Si deseas volver al menú, escribe *menú* o *volver*.")
    else:
        return responder("📌 Por favor indícanos si deseas información sobre emergencia, servicios o ubicaciones. Puedes escribir palabras como: *emergencia*, *cremación*, *nichos*, *adulto mayor*, *biker*, *ubicación*, etc.")
