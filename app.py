# -*- coding: utf-8 -*-
from flask import Flask, request
import sys
import io
import requests
import os
import threading
import logging
from twilio.twiml.messaging_response import MessagingResponse
from planes_info import responder_plan  # Asegúrate de que este archivo exista y tenga la función responder_plan

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

app = Flask(__name__)

# Configura el logging
logging.basicConfig(level=logging.INFO)

# Variables de entorno para Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_MESSAGING_URL = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
TWILIO_AUTH = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
NUMERO_REENVIO = "+525523604519"  # Cambia este número por el que desees recibir los mensajes

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
    
    # Log para verificar que se recibe el mensaje
    logging.info(f"Mensaje recibido: {mensaje} de {telefono}")

    if not mensaje:
        return responder("❗ No recibimos texto. Por favor escribe tu mensaje.")

    # Reiniciar temporizador de inactividad
    if telefono in temporizadores:
        temporizadores[telefono].cancel()
        del temporizadores[telefono]
    temporizador = threading.Timer(600, mensaje_inactividad, args=(telefono,))
    temporizador.start()
    temporizadores[telefono] = temporizador

    # Lógica para volver al menú principal
    if mensaje.lower() == "*":
        sesiones[telefono] = {}  # Reinicia la sesión
        return responder(MENSAJE_BIENVENIDA)

    # Lógica para regresar al submenú
    if mensaje.lower() == "regresar":
        if "submenu" in sesiones.get(telefono, {}):
            # Regresar al menú del submenú
            if sesiones[telefono]["menu"] == "planes":
                return responder("🔙 Has regresado al submenú de planes. ¿Qué opción deseas seleccionar? Escribe *menú* para volver al menú principal.")
            elif sesiones[telefono]["menu"] == "ubicacion":
                return responder("🔙 Has regresado al submenú de ubicaciones. ¿Qué opción deseas seleccionar? Escribe *menú* para volver al menú principal.")
        else:
            return responder("🔙 Estás en el menú principal. Escribe *menú* para volver a empezar o selecciona otra opción.")

    # Lógica para mensajes de cierre
    if contiene(claves_cierre, mensaje.lower()):
        return responder("👌 Gracias por confirmar. Si necesitas algo más, puedes escribir *menú* para volver a empezar o seleccionar otra opción.")

    # Lógica principal del bot basada en el estado de la sesión
    if not sesiones.get(telefono):  # Si no hay estado, es la primera interacción o la sesión se reinició
        if contiene(claves_emergencia, mensaje.lower()):
            sesiones[telefono] = {"menu": "emergencia"}
            return responder("""🚨 *ATENCIÓN INMEDIATA*

Por favor responde con los siguientes datos:
🔹 Nombre completo del fallecido
🔹 Suceso o causa del fallecimiento
🔹 Ubicación actual del cuerpo
🔹 ¿Ya cuenta con su certificado de defunción?
🔹 Dos números de contacto
🔹 Nombre de la persona que nos está contactando""")
            
        elif contiene(claves_ubicacion, mensaje.lower()):
            sesiones[telefono] = {"menu": "ubicacion"}
            return responder("""📍 *Ubicaciones disponibles:*
1. Av. Tláhuac No. 5502, Col. El Rosario, CDMX
2. Av. Zacatlán No. 60, Col. San Lorenzo Tezonco, CDMX
3. Av. Zacatlán No. 10, Col. San Lorenzo Tezonco, CDMX

¿Deseas agendar una cita en alguna de nuestras sucursales? (Sí / No)""")

        elif contiene(claves_planes, mensaje.lower()):
            sesiones[telefono] = {"menu": "planes"}
            return responder(
                "Has seleccionado *servicios funerarios*. Por favor, elige una opción:\n"
                "1. Planes de necesidad inmediata\n"
                "2. Planes a futuro\n"
                "3. Servicios individuales\n\n"
                "📝 Escribe el número de la opción deseada.\n\n*Escribe '*' para regresar al menú principal."
            )
        else:
            return responder(MENSAJE_BIENVENIDA)

    # Manejo de estados específicos
    if sesiones[telefono].get("menu") == "emergencia":
        alerta = f"""📨 *NUEVA EMERGENCIA FUNERARIA*
De: {telefono}
Mensaje: {mensaje}
"""
        # Enviar a número principal
        requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
            "To": NUMERO_REENVIO,
            "From": "whatsapp:+14155238886",
            "Body": alerta
        })

        # Enviar a número secundario (si aplica)
        requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
            "To": "+525523680734",  # Asegúrate de que este número sea correcto
            "From": "whatsapp:+14155238886",
            "Body": alerta
        })
        sesiones[telefono] = {}  # Reinicia la sesión después de manejar la emergencia
        return responder("✅ Gracias. Hemos recibido tu emergencia. Un asesor te contactará de inmediato.")

    if sesiones[telefono].get("menu") == "ubicacion":
        if mensaje.lower() in ["sí", "si", "si me gustaría", "si quiero"]:
            sesiones[telefono]["menu"] = "cita"  # Cambia el estado a "cita"
            return responder("Perfecto. Por favor, indícanos tu nombre y un horario preferido para la cita.\n\n*Escribe '*' para regresar al menú principal.")
        elif mensaje.lower() in ["no", "no gracias", "no por ahora"]:
            sesiones[telefono] = {}  # Reinicia la sesión si no quiere cita
            return responder("✅ Gracias por consultar nuestras ubicaciones. Si necesitas otra información, escribe *menú*.")
        else:
            return responder("No entendí tu respuesta. ¿Te gustaría agendar una cita para visitarnos? Responde 'sí' o 'no'.\n\n*Escribe '*' para regresar al menú principal.")

    if sesiones[telefono].get("menu") == "cita":
        datos = f"📆 *CITA SOLICITADA*\nCliente: {telefono}\nDatos: {mensaje}"
        requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
            "To": NUMERO_REENVIO,
            "From": "whatsapp:+14155238886",
            "Body": datos
        })
        sesiones[telefono] = {}  # Reinicia la sesión después de registrar la cita
        return responder("✅ Gracias. Hemos registrado tu solicitud de cita. Nuestro equipo te contactará pronto.\n\n*Escribe '*' para regresar al menú principal.")

    if sesiones[telefono].get("menu") == "planes":
        if "submenu" not in sesiones[telefono]:  # Si aún no ha elegido un submenú de planes
            if mensaje == "1":
                sesiones[telefono]["submenu"] = "inmediato"
                return responder(
                    "⏱️ *Planes de necesidad inmediata:*\n"
                    "A. Crédito de necesidad inmediata\n"
                    "B. Servicio paquete fetal cremación\n"
                    "C. Servicio paquete sencillo sepultura\n"
                    "D. Servicio paquete básico sepultura\n"
                    "E. Servicio cremación directa\n"
                    "F. Servicio paquete de cremación\n"
                    "G. Servicio paquete legal\n"
                    "H. Servicio de refrigeración y conservación\n\n"
                    "📝 Escribe la letra correspondiente para más información o *escribe '*' para regresar al menú principal.*\n"
                    "🔙 Escribe 'regresar' para volver al menú de servicios."
                )

            elif mensaje == "2":
                sesiones[telefono]["submenu"] = "futuro"
                return responder(
                    "🕰️ *Planes a futuro:*\n"
                    "I. Red Biker\n"
                    "J. Red Plus\n"
                    "K. Red Consorcio\n"
                    "L. Red Adulto Mayor\n"
                    "M. Preventa de Nichos a Temporalidad\n\n"
                    "📝 Escribe la letra correspondiente para más información o *escribe '*' para regresar al menú principal.*\n"
                    "🔙 Escribe 'regresar' para volver al menú de servicios."
                )

            elif mensaje == "3":
                sesiones[telefono]["submenu"] = "servicios"
                sesiones[telefono]["menu_serv"] = "categorias"  # Establece el estado para la selección de categorías de servicios
                return responder(
                    "☝🏻️ *Servicios Individuales* - Selecciona una categoría:\n\n"
                    "A. Trámites y Papelería\n"
                    "B. Traslados y Carrozas\n"
                    "C. Objetos y Equipamiento\n"
                    "D. Procedimientos Especiales\n\n"
                    "Escribe la letra correspondiente para continuar (A, B, C o D).\n\n*Escribe '*' para regresar al menú principal.*\n"
                    "🔙 Escribe 'regresar' para volver al menú de servicios."
                )
            else:
                return responder("❌ Opción no válida. Por favor, elige 1, 2 o 3 para seleccionar un tipo de plan o escribe *menú* para volver al inicio.")

        # Si ya está en un submenú de planes (inmediato, futuro, servicios)
        elif sesiones[telefono].get("submenu") in ["inmediato", "futuro"]:
            letra = mensaje.strip().replace(" ", "")
            if letra in selecciones_letras:
                clave = selecciones_letras[letra]
                respuesta = responder_plan(clave)  # Asume que responder_plan devuelve el texto del plan
                sesiones[telefono] = {}  # Reinicia la sesión después de dar la información del plan
                return responder(respuesta + "\n\nSi necesitas algo más, escribe *menú* para volver al inicio.")
            else:
                return responder("❌ No reconocimos tu selección. Intenta con otra letra o escribe *volver* para regresar al menú de planes.")

        elif sesiones[telefono].get("submenu") == "servicios":
            letra = mensaje.strip().upper()

            if sesiones[telefono].get("menu_serv") == "categorias":
                if letra == "A":
                    sesiones[telefono]["menu_serv"] = "tramites"
                    return responder(
                        "📜 *Trámites y Papelería:*\n"
                        "Z. Trámites de inhumación\n"
                        "AA. Trámites de cremación\n"
                        "AB. Trámites legales\n"
                        "AC. Trámites de traslado\n"
                        "AD. Trámites de internación nacional\n"
                        "AE. Trámites de internación internacional\n\n"
                        "📝 Escribe la letra correspondiente para más información o *escribe '*' para regresar al menú principal.*\n"
                        "🔙 Escribe 'regresar' para volver al menú de servicios."
                    )
                elif letra == "B":
                    sesiones[telefono]["menu_serv"] = "traslados"
                    return responder(
                        "🚚 *Traslados y Carrozas:*\n"
                        "N. Traslado\n"
                        "S. Carroza local\n"
                        "T. Carroza a panteón"
                        "u horno crematorio\n"
                        "U. Carroza legal\n"
                        "V. Camión local\n"
                        "AJ. Traslado carretero por km\n"
                        "AK. Traslado de terracería por km\n"
                        "AL. Camión foráneo por km\n\n"
                        "📝 Escribe la letra correspondiente para más información o *escribe '*' para regresar al menú principal.*\n"
                        "🔙 Escribe 'regresar' para volver al menú de servicios."
                    )
                elif letra == "C":
                    sesiones[telefono]["menu_serv"] = "equipamiento"
                    return responder(
                        "🛄 *Objetos y Equipamiento:*\n"
                        "O. Ataúd\n"
                        "P. Urna\n"
                        "AF. Equipo de velación\n"
                        "AG. Cirios\n"
                        "AH. Capilla de gobierno\n"
                        "AI. Capilla particular\n\n"
                        "📝 Escribe la letra correspondiente para más información o *escribe '*' para regresar al menú principal.*\n"
                        "🔙 Escribe 'regresar' para volver al menú de servicios."
                    )
                elif letra == "D":
                    sesiones[telefono]["menu_serv"] = "procedimientos"
                    return responder(
                        "🧪 *Procedimientos Especiales:*\n"
                        "Q. Velación\n"
                        "R. Boletas\n"
                        "W. Embalsamado\n"
                        "X. Embalsamado legal\n"
                        "Y. Embalsamado infecto-contagiosa\n\n"
                        "📝 Escribe la letra correspondiente para más información o *escribe '*' para regresar al menú principal.*\n"
                        "🔙 Escribe 'regresar' para volver al menú de servicios."
                    )
                else:
                    return responder("❌ Opción no válida. Por favor escribe A, B, C o D para seleccionar una categoría.")

            elif sesiones[telefono].get("menu_serv") in ["tramites", "traslados", "equipamiento", "procedimientos"]:
                if letra in selecciones_letras:
                    clave = selecciones_letras[letra]
                    respuesta = responder_plan(clave)  # Asume que responder_plan devuelve el texto del servicio
                    sesiones[telefono] = {}  # Reinicia la sesión después de dar la información del servicio
                    return responder(respuesta + "\n\nSi necesitas algo más, escribe *menú* para volver al inicio.")
                else:
                    return responder("❌ Letra no reconocida. Intenta de nuevo o escribe *volver* para regresar.")

    # Si el mensaje no fue manejado por ningún estado específico, o si el estado es inválido,
    # se devuelve al menú principal. Esto actúa como un "catch-all".
    return responder(MENSAJE_BIENVENIDA)

if __name__ == "__main__":
    app.run(debug=True)
