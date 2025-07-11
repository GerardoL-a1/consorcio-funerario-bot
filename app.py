# -*- coding: utf-8 -*-
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from planes_info import responder_plan
import requests
import os
import threading

app = Flask(__name__)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_MESSAGING_URL = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
TWILIO_AUTH = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
NUMERO_REENVIO = "+525523604519"

sesiones = {}
temporizadores = {}

@app.route("/", methods=["GET"])
def home():
    return "✅ Bot Consorcio Funerario funcionando."

MENSAJE_BIENVENIDA = """👋 *Bienvenido a Consorcio Funerario*

Gracias por escribirnos.

Por favor indíquenos *en qué le gustaría recibir información o en qué podemos apoyarle*:
- Atención inmediata por *emergencia*
- Conocer nuestros *servicios funerarios*
- Consultar nuestras *ubicaciones disponibles*

📌 Puede escribir palabras como: *emergencia*, *planes*, *servicios*, *ubicación*, etc."""

# Diccionario de letras -> servicio
selecciones_letras = {
    **{k: "crédito de necesidad inmediata" for k in ["A", "a"]},
    **{k: "servicio paquete fetal cremación" for k in ["B", "b"]},
    **{k: "servicio paquete sencillo sepultura" for k in ["C", "c"]},
    **{k: "servicio paquete básico sepultura" for k in ["D", "d"]},
    **{k: "servicio cremación directa" for k in ["E", "e"]},
    **{k: "servicio paquete de cremación" for k in ["F", "f"]},
    **{k: "servicio paquete legal" for k in ["G", "g"]},
    **{k: "servicio de refrigeración y conservación" for k in ["H", "h"]},
    **{k: "red biker" for k in ["I", "i"]},
    **{k: "red plus" for k in ["J", "j"]},
    **{k: "red consorcio" for k in ["K", "k"]},
    **{k: "red adulto mayor" for k in ["L", "l"]},
    **{k: "preventa de nichos a temporalidad" for k in ["M", "m"]},
    **{k: "traslado" for k in ["N", "n"]},
    **{k: "ataúd" for k in ["O", "o"]},
    **{k: "urna" for k in ["P", "p"]},
    **{k: "velación" for k in ["Q", "q"]},
    **{k: "boletas" for k in ["R", "r"]},
    **{k: "carroza local" for k in ["S", "s"]},
    **{k: "carroza a panteón u horno crematorio" for k in ["T", "t"]},
    **{k: "carroza legal" for k in ["U", "u"]},
    **{k: "camión local" for k in ["V", "v"]},
    **{k: "embalsamado" for k in ["W", "w"]},
    **{k: "embalsamado legal" for k in ["X", "x"]},
    **{k: "embalsamado infecto-contagiosa" for k in ["Y", "y"]},
    **{k: "trámites de inhumación" for k in ["Z", "z"]},
    **{k: "trámites de cremación" for k in ["AA", "aa", "Aa", "aA"]},
    **{k: "trámites legales" for k in ["AB", "ab", "Ab", "aB"]},
    **{k: "trámites de traslado" for k in ["AC", "ac", "Ac", "aC"]},
    **{k: "trámites de internación nacional" for k in ["AD", "ad", "Ad", "aD"]},
    **{k: "trámites de internación internacional" for k in ["AE", "ae", "Ae", "aE"]},
    **{k: "equipo de velación" for k in ["AF", "af", "Af", "aF"]},
    **{k: "cirios" for k in ["AG", "ag", "Ag", "aG"]},
    **{k: "capilla de gobierno" for k in ["AH", "ah", "Ah", "aH"]},
    **{k: "capilla particular" for k in ["AI", "ai", "Ai", "aI"]},
    **{k: "traslado carretero por km" for k in ["AJ", "aj", "Aj", "aJ"]},
    **{k: "traslado de terracería por km" for k in ["AK", "ak", "Ak", "aK"]},
    **{k: "camión foráneo por km" for k in ["AL", "al", "Al", "aL"]},
}

claves_planes = ["plan", "planes", "servicio", "servicios", "paquete", "información", "informacion"]
claves_emergencia = [
    "emergencia", "urgente", "fallecido", "murió", "murio", "accidente", "suceso",
    "acaba de fallecer", "mi papá falleció", "mi mamá murió", "murió mi", "falleció mi",
    "necesito ayuda con un funeral", "necesito apoyo", "ayúdenos", "urgente apoyo", "acaba de morir"
]
claves_ubicacion = ["ubicación", "ubicaciones", "sucursal", "sucursales", "dirección", "direccion"]
claves_volver = ["volver", "menú", "menu", "inicio", "meno", "menj", "inickp", "ect", "etc"]
claves_cierre = ["gracias", "ok", "vale", "de acuerdo", "listo", "perfecto", "entendido", "muy bien"]

def contiene(palabras, mensaje):
    return any(p in mensaje.lower() for p in palabras)

def responder(texto):
    respuesta = MessagingResponse()
    respuesta.message(texto)
    return str(respuesta)

def mensaje_inactividad(numero):
    if numero in sesiones:
        requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
            "To": numero,
            "From": "whatsapp:+14155238886",
            "Body": "⌛ ¿Aún estás ahí? Si necesitas ayuda, escribe *menú* para volver al inicio."
        })
        temporizadores.pop(numero, None)

@app.route("/webhook", methods=["POST"])
def webhook():
    mensaje = request.form.get("Body", "").strip()
    telefono = request.form.get("From", "")
    estado = sesiones.get(telefono, {})
    msj_lower = mensaje.lower()

    if not mensaje:
        return responder("❗ No recibimos texto. Por favor escribe tu mensaje.")

    if telefono in temporizadores:
        temporizadores[telefono].cancel()
        del temporizadores[telefono]
    temporizador = threading.Timer(600, mensaje_inactividad, args=(telefono,))
    temporizador.start()
    temporizadores[telefono] = temporizador

    if contiene(claves_volver, msj_lower):
        sesiones[telefono] = {}
        return responder(MENSAJE_BIENVENIDA)

    if contiene(claves_cierre, msj_lower):
        return responder("👌 Gracias por confirmar. Si necesitas algo más, puedes escribir *menú* para volver a empezar o seleccionar otra opción.")

    if not estado:
        if contiene(claves_emergencia, msj_lower):
            sesiones[telefono] = {"menu": "emergencia"}
            return responder("""🚨 *ATENCIÓN INMEDIATA*

Por favor responde con los siguientes datos:
🔹 Nombre de la persona que nos está contactando""")

        elif contiene(claves_ubicacion, msj_lower):
            sesiones[telefono] = {"menu": "ubicacion"}
            return responder("""📍 *Ubicaciones disponibles:*
1. Av. Tláhuac No. 5502, Col. El Rosario, CDMX
2. Av. Zacatlán No. 60, Col. San Lorenzo Tezonco, CDMX
3. Av. Zacatlán No. 10, Col. San Lorenzo Tezonco, CDMX

¿Deseas agendar una cita en alguna de nuestras sucursales? (Sí / No)""")

        elif contiene(claves_planes, msj_lower):
            sesiones[telefono] = {"menu": "planes"}
            return responder("""📋 *Selecciona una categoría:*
1. Planes de necesidad inmediata
2. Planes a futuro
3. Servicios individuales""")

        return responder(MENSAJE_BIENVENIDA)

    if estado.get("menu") == "emergencia":
        alerta = f"""📨 *NUEVA EMERGENCIA FUNERARIA*

{mensaje}


"""

        # Enviar a número principal
        requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
            "To": NUMERO_REENVIO,
            "From": "whatsapp:+14155238886",
            "Body": alerta
        })

        # Enviar a número secundario
        requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
            "To": "+525523680734",
            "From": "whatsapp:+14155238886",
            "Body": alerta
        })
        sesiones[telefono] = {}
        return responder("✅ Gracias. Hemos recibido tu emergencia. Un asesor te contactará de inmediato.")

    if estado.get("menu") == "ubicacion":
        if msj_lower in ["sí", "si"]:
            sesiones[telefono] = {"menu": "cita"}
            return responder("""📅 *Agendemos tu cita.*

¿Qué día te gustaría visitarnos?
¿En qué horario podrías acudir?

Tu información será enviada a nuestro equipo.""")
        else:
            sesiones[telefono] = {}
            return responder("✅ Gracias por consultar nuestras ubicaciones. Si necesitas otra información, escribe *menú*.")

    if estado.get("menu") == "cita":
        datos = f"📆 *CITA SOLICITADA*\nCliente: {telefono}\nDatos: {mensaje}"
        requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
            "To": NUMERO_REENVIO,
            "From": "whatsapp:+14155238886",
            "Body": datos
        })
        sesiones[telefono] = {}
        return responder("✅ Gracias. Hemos registrado tu solicitud. Nuestro equipo te contactará pronto.")

    if estado.get("menu") == "planes":
        if mensaje == "1":
            sesiones[telefono] = {"submenu": "inmediato"}
            return responder("""⏱️ *Planes de necesidad inmediata:*
A. Crédito de necesidad inmediata
B. Servicio paquete fetal cremación
C. Servicio paquete sencillo sepultura
D. Servicio paquete básico sepultura
E. Servicio cremación directa
F. Servicio paquete de cremación
G. Servicio paquete legal
H. Servicio de refrigeración y conservación

Escribe la letra correspondiente para más información.""")""")

        elif mensaje == "2":
            sesiones[telefono] = {"submenu": "futuro"}
            return responder("🕰️ *Planes a futuro:*
I. Red Biker
J. Red Plus
K. Red Consorcio
L. Red Adulto Mayor
M. Preventa de Nichos a Temporalidad

Escribe la letra correspondiente para más información.")

        elif mensaje == "3":
            sesiones[telefono] = {"submenu": "servicios", "menu_serv": "categorias"}
            return responder("""🧰 *Servicios Individuales* - Selecciona una categoría:

⚰️ C. Objetos y Equipamiento  

Escribe la letra correspondiente para continuar (A, B, C o D).""")
            return responder("""🧰 *Servicios individuales:*
N. Traslado
O. Ataúd
P. Urna
Q. Velación
R. Boletas
S. Carroza local
T. Carroza a panteón u horno crematorio
U. Carroza legal
V. Camión local
W. Embalsamado
X. Embalsamado legal
Y. Embalsamado infecto-contagiosa
Z. Trámites de inhumación
AA. Trámites de cremación
AB. Trámites legales
AC. Trámites de traslado
AD. Trámites de internación nacional
AE. Trámites de internación internacional
AF. Equipo de velación
AG. Cirios
AH. Capilla de gobierno
AI. Capilla particular
AJ. Traslado carretero por km
AK. Traslado de terracería por km
AL. Camión foráneo por km

Escribe la letra correspondiente para más información.""")

        return responder("✍️ Escribe la letra del plan o servicio que deseas consultar (por ejemplo A, b, AL, etc).")

    if estado.get("submenu"):
        letra = mensaje.strip().replace(" ", "")
        if letra in selecciones_letras:
            clave = selecciones_letras[letra]
            respuesta = responder_plan(clave)
            return responder(respuesta)
        else:
            return responder("❌ No reconocimos tu selección. Intenta con otra letra o palabra clave.")

    return responder(MENSAJE_BIENVENIDA)

    if estado.get("submenu") == "servicios":
        letra = mensaje.strip().upper()

        if estado.get("menu_serv") == "categorias":
            if letra == "A":
                sesiones[telefono]["menu_serv"] = "tramites"
                return responder("""📄 *Trámites y Papelería:*
Z. Trámites de inhumación  
AA. Trámites de cremación  
AB. Trámites legales  
AC. Trámites de traslado  
AD. Trámites de internación nacional  
AE. Trámites de internación internacional

✍️ Escribe la letra correspondiente para más información o *volver* para regresar.""")
            elif letra == "B":
                sesiones[telefono]["menu_serv"] = "traslados"
                return responder("""🚚 *Traslados y Carrozas:*
N. Traslado  
S. Carroza local  
T. Carroza a panteón u horno crematorio  
U. Carroza legal  
V. Camión local  
AJ. Traslado carretero por km  
AK. Traslado de terracería por km  
AL. Camión foráneo por km

✍️ Escribe la letra correspondiente para más información o *volver* para regresar.""")
            elif letra == "C":
                sesiones[telefono]["menu_serv"] = "equipamiento"
                return responder("""⚰️ *Objetos y Equipamiento:*
O. Ataúd  
P. Urna  
AF. Equipo de velación  
AG. Cirios  
AH. Capilla de gobierno  
AI. Capilla particular

✍️ Escribe la letra correspondiente para más información o *volver* para regresar.""")
            elif letra == "D":
                sesiones[telefono]["menu_serv"] = "procedimientos"
                return responder("""🧪 *Procedimientos Especiales:*
Q. Velación  
R. Boletas  
W. Embalsamado  
X. Embalsamado legal  
Y. Embalsamado infecto-contagiosa

✍️ Escribe la letra correspondiente para más información o *volver* para regresar.""")
            else:
                return responder("❌ Opción no válida. Por favor escribe A, B, C o D para seleccionar una categoría.")

        elif estado.get("menu_serv") in ["tramites", "traslados", "equipamiento", "procedimientos"]:
            if letra in selecciones_letras:
                clave = selecciones_letras[letra]
                return responder(responder_plan(clave))
            else:
                return responder("❌ Letra no reconocida. Intenta de nuevo o escribe *volver* para regresar.")

    return responder(MENSAJE_BIENVENIDA)