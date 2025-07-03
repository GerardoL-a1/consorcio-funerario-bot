
from flask import Flask, request from twilio.twiml.messaging_response import MessagingResponse from planes_info import responder_plan import requests import os

app = Flask(name)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID") TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN") TWILIO_MESSAGING_URL = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json" TWILIO_AUTH = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

NUMERO_REENVIO = "+525523604519" sesiones = {}

@app.route("/", methods=["GET"]) def home(): return "✅ Bot Consorcio Funerario funcionando."

MENSAJE_BIENVENIDA = ( "👋 Bienvenido a Consorcio Funerario\n\n" "Gracias por escribirnos.\n\n" "Por favor indíquenos en qué le gustaría recibir información o en qué podemos apoyarle:\n" "- Atención inmediata por emergencia\n" "- Conocer nuestros servicios funerarios\n" "- Consultar nuestras ubicaciones disponibles\n\n" "📌 Puede escribir palabras como: emergencia, planes, servicios, ubicación, etc." )

selecciones_letras = { **{k: "crédito de necesidad inmediata" for k in ["A", "a"]}, **{k: "servicio paquete fetal cremación" for k in ["B", "b"]}, **{k: "servicio paquete sencillo sepultura" for k in ["C", "c"]}, **{k: "servicio paquete básico sepultura" for k in ["D", "d"]}, **{k: "servicio cremación directa" for k in ["E", "e"]}, **{k: "servicio paquete de cremación" for k in ["F", "f"]}, **{k: "servicio paquete legal" for k in ["G", "g"]}, **{k: "servicio de refrigeración y conservación" for k in ["H", "h"]}, **{k: "red biker" for k in ["I", "i"]}, **{k: "red plus" for k in ["J", "j"]}, **{k: "red consorcio" for k in ["K", "k"]}, **{k: "red adulto mayor" for k in ["L", "l"]}, **{k: "preventa de nichos a temporalidad" for k in ["M", "m"]}, **{k: "traslado" for k in ["N", "n"]}, **{k: "ataúd" for k in ["O", "o"]}, **{k: "urna" for k in ["P", "p"]}, **{k: "velación" for k in ["Q", "q"]}, **{k: "boletas" for k in ["R", "r"]}, **{k: "carroza local" for k in ["S", "s"]}, **{k: "carroza a panteón u horno crematorio" for k in ["T", "t"]}, **{k: "carroza legal" for k in ["U", "u"]}, **{k: "camión local" for k in ["V", "v"]}, **{k: "embalsamado" for k in ["W", "w"]}, **{k: "embalsamado legal" for k in ["X", "x"]}, **{k: "embalsamado infecto-contagiosa" for k in ["Y", "y"]}, **{k: "trámites de inhumación" for k in ["Z", "z"]}, **{k: "trámites de cremación" for k in ["AA", "aa", "Aa", "aA"]}, **{k: "trámites legales" for k in ["AB", "ab", "Ab", "aB"]}, **{k: "trámites de traslado" for k in ["AC", "ac", "Ac", "aC"]}, **{k: "trámites de internación nacional" for k in ["AD", "ad", "Ad", "aD"]}, **{k: "trámites de internación internacional" for k in ["AE", "ae", "Ae", "aE"]}, **{k: "equipo de velación" for k in ["AF", "af", "Af", "aF"]}, **{k: "cirios" for k in ["AG", "ag", "Ag", "aG"]}, **{k: "capilla de gobierno" for k in ["AH", "ah", "Ah", "aH"]}, **{k: "capilla particular" for k in ["AI", "ai", "Ai", "aI"]}, **{k: "traslado carretero por km" for k in ["AJ", "aj", "Aj", "aJ"]}, **{k: "traslado de terracería por km" for k in ["AK", "ak", "Ak", "aK"]}, **{k: "camión foráneo por km" for k in ["AL", "al", "Al", "aL"]}, }

claves_planes = ["plan", "planes", "servicio", "servicios", "paquete", "información", "informacion"] claves_emergencia = ["emergencia", "urgente", "fallecido", "murió", "murio", "accidente", "suceso"] claves_ubicacion = ["ubicación", "ubicaciones", "sucursal", "sucursales", "dirección", "direccion"] claves_volver = ["volver", "menú", "menu", "inicio"]

def contiene(palabras, mensaje): return any(p in mensaje.lower() for p in palabras)

def responder(texto): respuesta = MessagingResponse() respuesta.message(texto) return str(respuesta)

@app.route("/webhook", methods=["POST"]) def webhook(): mensaje = request.form.get("Body", "").strip() telefono = request.form.get("From", "") estado = sesiones.get(telefono, {}) msj_lower = mensaje.lower()

if contiene(claves_volver, msj_lower):
    sesiones[telefono] = {}
    return responder(MENSAJE_BIENVENIDA)

if not estado:
    if contiene(claves_emergencia, msj_lower):
        sesiones[telefono] = {"menu": "emergencia"}
        return responder(
            "🚨 *ATENCIÓN INMEDIATA*\n\n"
            "Por favor responde con los siguientes datos:\n"
            "🔹 Nombre completo del fallecido\n"
            "🔹 Suceso o causa del fallecimiento\n"
            "🔹 Ubicación actual del cuerpo\n"
            "🔹 Dos números de contacto\n"
            "🔹 Nombre de la persona que nos está contactando"
        )
    elif contiene(claves_ubicacion, msj_lower):
        sesiones[telefono] = {"menu": "ubicacion"}
        return responder(
            "📍 *Ubicaciones disponibles:*\n"
            "1. Av. Tláhuac No. 5502, Col. El Rosario, CDMX\n"
            "2. Av. Zacatlán No. 60, Col. San Lorenzo Tezonco, CDMX\n"
            "3. Av. Zacatlán No. 10, Col. San Lorenzo Tezonco, CDMX\n\n"
            "¿Deseas agendar una cita en alguna de nuestras sucursales? (Sí / No)"
        )
    elif contiene(claves_planes, msj_lower):
        sesiones[telefono] = {"menu": "planes"}
        return responder(
            "📋 *Selecciona una categoría:*\n"
            "1. Planes de necesidad inmediata\n"
            "2. Planes a futuro\n"
            "3. Servicios individuales"
        )
    else:
        return responder(MENSAJE_BIENVENIDA)

if estado.get("menu") == "emergencia":
    alerta = f"📨 *EMERGENCIA RECIBIDA*\nMensaje: {mensaje}\nDesde: {telefono}"
    requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
        "To": NUMERO_REENVIO,
        "From": "whatsapp:+14155238886",
        "Body": alerta
    })
    sesiones[telefono] = {}
    return responder("✅ Gracias. Hemos recibido tu emergencia. Un asesor te contactará de inmediato.")

if estado.get("menu") == "ubicacion":
    if msj_lower in ["sí", "si"]:
        sesiones[telefono] = {"menu": "cita"}
        return responder(
            "📅 *Agendemos tu cita.*\n\n"
            "¿Qué día te gustaría visitarnos?\n"
            "¿En qué horario podrías acudir?\n\n"
            "Tu información será enviada a nuestro equipo."
        )
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
    elif mensaje == "2":
        sesiones[telefono] = {"submenu": "futuro"}
    elif mensaje == "3":
        sesiones[telefono] = {"submenu": "servicios"}
    return responder("✍️ Escribe la letra del plan o servicio que deseas consultar (por ejemplo A, b, AL, etc).")

if estado.get("submenu"):
    letra = mensaje.strip().replace(" ", "")
    if letra in selecciones_letras:
        clave = selecciones_letras[letra]
        respuesta = responder_plan(clave)
        return responder(respuesta)
    else:
        return responder("❌ No reconocimos tu selección. Intenta con otra letra o palabra clave, o escribe *menú* para regresar al inicio.")

return responder(MENSAJE_BIENVENIDA)

