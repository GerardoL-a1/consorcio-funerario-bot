# -*- coding: utf-8 -*-
from flask import Flask, request
import sys
import io
import requests
import os
import threading
import logging
from twilio.twiml.messaging_response import MessagingResponse
from planes_info import responder_plan
from difflib import SequenceMatcher  # para comparar palabras similares

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

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
# --------------------------------------------- #
# PALABRAS CLAVE GENERALES
# --------------------------------------------- #

claves_planes = ["plan", "planes", "servicio", "servicios", "paquete", "información", "informacion"]
claves_emergencia = [
    "emergencia", "urgente", "fallecido", "murió", "murio", "accidente", "suceso",
    "acaba de fallecer", "mi papá falleció", "mi mamá murió", "murió mi", "falleció mi",
    "necesito ayuda con un funeral", "necesito apoyo", "ayúdenos", "urgente apoyo", "acaba de morir"
]
claves_ubicacion = ["ubicación", "ubicaciones", "sucursal", "sucursales", "dirección", "direccion"]
claves_cierre = ["gracias", "ok", "vale", "de acuerdo", "listo", "perfecto", "entendido", "muy bien"]

# --------------------------------------------- #
# FUNCIONES AUXILIARES
# --------------------------------------------- #

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
            "Body": "⌛ ¿Aún estás ahí? Si necesitas ayuda, escribe la palabra *menú* para volver al inicio."
        })
        temporizadores.pop(numero, None)

# --------------------------------------------- #
# DETECCIÓN INTELIGENTE DE PALABRAS SIMILARES
# --------------------------------------------- #

def parecido(palabra_objetivo, mensaje, umbral=0.75):
    """Detecta si una palabra es suficientemente parecida al mensaje recibido."""
    return SequenceMatcher(None, palabra_objetivo.lower(), mensaje.lower()).ratio() >= umbral
    
def contiene_flexible(lista_claves, mensaje_usuario, umbral=0.75):
    """Devuelve True si el mensaje es similar a alguna palabra clave."""
    mensaje_usuario = mensaje_usuario.strip().lower()
    for palabra_clave in lista_claves:
        if parecido(palabra_clave, mensaje_usuario, umbral):
            return True
    return False

def es_mensaje_menu(mensaje):
    return (
        mensaje.strip().lower() in ["menú", "menu", "menù", "inicio", "menuh", "inicioo", "home"]
        or parecido("menú", mensaje)
        or parecido("menu", mensaje)
    )

def es_mensaje_regresar(mensaje):
    return (
        mensaje.strip().lower() in ["regresar", "volver", "regresa", "regreso"]
        or parecido("regresar", mensaje)
        or parecido("volver", mensaje)
    )
@app.route("/webhook", methods=["POST"])
def webhook():
    mensaje = request.form.get("Body", "").strip()
    telefono = request.form.get("From", "")
    logging.info(f"Mensaje recibido: {mensaje} de {telefono}")

    if not mensaje:
        return responder("❗ No recibimos texto. Por favor escribe tu mensaje.")

    # --- Volver al menú principal si se detecta 'menú' con tolerancia ---
    if es_mensaje_menu(mensaje):
        estado = sesiones.get(telefono, {}).get("menu", "")
        if estado in ["emergencia", "planes", "ubicacion"]:
            sesiones[telefono] = {}
            return responder(MENSAJE_BIENVENIDA)

    # --- Regresar a submenús si se detecta 'regresar' ---
    if es_mensaje_regresar(mensaje):
        if "submenu" in sesiones.get(telefono, {}):
            if sesiones[telefono]["menu"] == "planes":
                return responder("🔙 Has regresado al submenú de *planes*. Escribe 1, 2 o 3 para seleccionar otra opción.")
            elif sesiones[telefono]["menu"] == "ubicacion":
                return responder("🔙 Has regresado al submenú de *ubicaciones*. ¿Deseas agendar una cita? Responde 'sí' o 'no'.")
        elif "menu_serv" in sesiones.get(telefono, {}):
            sesiones[telefono]["menu_serv"] = "categorias"
            return responder("🔙 Has regresado a la categoría de *servicios individuales*. Elige A, B, C o D.")
        else:
            return responder("🔙 No hay menú anterior al cual regresar. Puedes escribir la palabra *menú* para volver al inicio.")

    # --- Reiniciar temporizador de inactividad por cada mensaje recibido ---
    if telefono in temporizadores:
        temporizadores[telefono].cancel()
        del temporizadores[telefono]
    temporizador = threading.Timer(600, mensaje_inactividad, args=(telefono,))
    temporizador.start()
    temporizadores[telefono] = temporizador

    # --- Confirmaciones como "gracias", "ok", etc. ---
    if contiene(claves_cierre, mensaje):
        return responder("👌 Gracias por confirmar. Si necesitas algo más, escribe la palabra *menú* para volver al inicio.")
    # ----------------------------- #
    # FLUJO: BIENVENIDA Y DETECCIÓN INICIAL
    # ----------------------------- #
    if not sesiones.get(telefono):
        if contiene(claves_emergencia, mensaje):
            sesiones[telefono] = {"menu": "emergencia"}
            return responder("""🚨 *ATENCIÓN INMEDIATA*

Por favor responde con los siguientes datos:
🔹 Nombre completo del fallecido
🔹 Suceso o causa del fallecimiento
🔹 Ubicación actual del cuerpo
🔹 ¿Ya cuenta con su certificado de defunción?
🔹 Dos números de contacto
🔹 Nombre de la persona que nos está contactando

📌 Si fue un error, escribe la palabra *menú* para regresar al inicio.""")

        elif contiene(claves_ubicacion, mensaje):
            sesiones[telefono] = {"menu": "ubicacion"}
            return responder("""📍 *Ubicaciones disponibles:*
1. Av. Tláhuac No. 5502, Col. El Rosario, CDMX
2. Av. Zacatlán No. 60, Col. San Lorenzo Tezonco, CDMX
3. Av. Zacatlán No. 10, Col. San Lorenzo Tezonco, CDMX

¿Deseas agendar una cita en alguna de nuestras sucursales? (Sí / No)

📌 Puedes escribir la palabra *menú* para regresar al inicio.""")

        elif contiene(claves_planes, mensaje):
            sesiones[telefono] = {"menu": "planes"}
            return responder(
                "🧾 Has seleccionado *servicios funerarios*. Por favor, elige una opción:\n"
                "1. Planes de necesidad inmediata\n"
                "2. Planes a futuro\n"
                "3. Servicios individuales\n\n"
                "📝 Escribe el número de la opción deseada.\n"
                "📌 Escribe la palabra *menú* para regresar al inicio."
            )
        else:
            return responder(MENSAJE_BIENVENIDA)

    # ----------------------------- #
    # FLUJO: EMERGENCIA
    # ----------------------------- #
    if sesiones[telefono].get("menu") == "emergencia":
        alerta = f"""📨 *NUEVA EMERGENCIA FUNERARIA*
De: {telefono}
Mensaje: {mensaje}
"""
        requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
            "To": NUMERO_REENVIO,
            "From": "whatsapp:+14155238886",
            "Body": alerta
        })
        requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
            "To": "+525523680734",
            "From": "whatsapp:+14155238886",
            "Body": alerta
        })

        sesiones[telefono] = {}
        return responder("✅ Gracias. Hemos recibido tu emergencia. Un asesor te contactará de inmediato.\n\n📌 Si deseas más información, escribe la palabra *menú* para regresar al inicio.")

    # ----------------------------- #
    # FLUJO: UBICACIÓN
    # ----------------------------- #
    if sesiones[telefono].get("menu") == "ubicacion":
        if mensaje.lower() in ["sí", "si", "si me gustaría", "si quiero"]:
            sesiones[telefono]["menu"] = "cita"
            return responder("Perfecto. Por favor, indícanos tu nombre y un horario preferido para la cita.\n\n📌 Escribe la palabra *menú* para regresar al inicio.")
        elif mensaje.lower() in ["no", "no gracias", "no por ahora"]:
            sesiones[telefono] = {}
            return responder("✅ Gracias por consultar nuestras ubicaciones. Si necesitas algo más, escribe la palabra *menú* para regresar al inicio.")
        else:
            return responder("No entendí tu respuesta. ¿Te gustaría agendar una cita? Responde 'sí' o 'no'.\n\n📌 Escribe la palabra *menú* para regresar al inicio.")
    # ----------------------------- #
    # FLUJO: PLANES
    # ----------------------------- #
    if sesiones[telefono].get("menu") == "planes":
        if "submenu" not in sesiones[telefono]:
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
                    "📝 Escribe la letra correspondiente para más información.\n"
                    "🔙 Escribe *regresar* para volver.\n"
                    "📌 Escribe *menú* para regresar al inicio."
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
                    "📝 Escribe la letra correspondiente para más información.\n"
                    "🔙 Escribe *regresar* para volver.\n"
                    "📌 Escribe *menú* para regresar al inicio."
                )

            elif mensaje == "3":
                sesiones[telefono]["submenu"] = "servicios"
                sesiones[telefono]["menu_serv"] = "categorias"
                return responder(
                    "☝🏻️ *Servicios Individuales* – Elige una categoría:\n\n"
                    "A. Trámites y Papelería\n"
                    "B. Traslados y Carrozas\n"
                    "C. Objetos y Equipamiento\n"
                    "D. Procedimientos Especiales\n\n"
                    "📝 Escribe la letra correspondiente.\n"
                    "🔙 Escribe *regresar* para volver.\n"
                    "📌 Escribe *menú* para regresar al inicio."
                )

            else:
                return responder("❌ Opción no válida. Escribe 1, 2 o 3.\n📌 También puedes escribir *menú* para regresar al inicio.")

        elif sesiones[telefono]["submenu"] in ["inmediato", "futuro"]:
            letra = mensaje.strip().replace(" ", "")
            if letra in selecciones_letras:
                clave = selecciones_letras[letra]
                respuesta = responder_plan(clave)
                sesiones[telefono] = {}
                return responder(respuesta + "\n\n📌 Si necesitas algo más, escribe la palabra *menú* para regresar al inicio.")
            else:
                return responder("❌ Letra no reconocida. Intenta otra opción o escribe *regresar* para volver al submenú.")

        elif sesiones[telefono]["submenu"] == "servicios":
            letra = mensaje.strip().upper()

            if sesiones[telefono]["menu_serv"] == "categorias":
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
                        "📝 Escribe la letra deseada.\n"
                        "🔙 Escribe *regresar* para volver a categorías.\n"
                        "📌 Escribe *menú* para volver al inicio."
                    )
                elif letra == "B":
                    sesiones[telefono]["menu_serv"] = "traslados"
                    return responder(
                        "🚚 *Traslados y Carrozas:*\n"
                        "N. Traslado\n"
                        "S. Carroza local\n"
                        "T. Carroza a panteón u horno crematorio\n"
                        "U. Carroza legal\n"
                        "V. Camión local\n"
                        "AJ. Traslado carretero por km\n"
                        "AK. Traslado de terracería por km\n"
                        "AL. Camión foráneo por km\n\n"
                        "📝 Escribe la letra deseada.\n"
                        "🔙 Escribe *regresar* para volver a categorías.\n"
                        "📌 Escribe *menú* para volver al inicio."
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
                        "📝 Escribe la letra deseada.\n"
                        "🔙 Escribe *regresar* para volver a categorías.\n"
                        "📌 Escribe *menú* para volver al inicio."
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
                        "📝 Escribe la letra deseada.\n"
                        "🔙 Escribe *regresar* para volver a categorías.\n"
                        "📌 Escribe *menú* para volver al inicio."
                    )
                else:
                    return responder("❌ Categoría no reconocida. Escribe A, B, C o D.\n📌 Puedes escribir *menú* para volver al inicio.")

            elif sesiones[telefono]["menu_serv"] in ["tramites", "traslados", "equipamiento", "procedimientos"]:
                if letra in selecciones_letras:
                    clave = selecciones_letras[letra]
                    respuesta = responder_plan(clave)
                    sesiones[telefono] = {}
                    return responder(respuesta + "\n\n📌 Si necesitas algo más, escribe la palabra *menú* para regresar al inicio.")
                else:
                    return responder("❌ Letra no reconocida. Intenta de nuevo o escribe *regresar* para volver.")
    # ----------------------------- #
    # FLUJO: CITA DESDE UBICACIÓN
    # ----------------------------- #
    if sesiones[telefono].get("menu") == "cita":
        datos = f"📆 *CITA SOLICITADA*\nCliente: {telefono}\nDatos: {mensaje}"
        requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
            "To": NUMERO_REENVIO,
            "From": "whatsapp:+14155238886",
            "Body": datos
        })
        sesiones[telefono] = {}
        return responder("✅ Gracias. Hemos registrado tu solicitud de cita. Nuestro equipo te contactará pronto.\n\n📌 Puedes escribir la palabra *menú* para volver al inicio.")

    # ----------------------------- #
    # RESPUESTA GENERAL SI NADA COINCIDE
    # ----------------------------- #
    return responder("🤖 No entendimos tu mensaje. Puedes escribir la palabra *menú* para comenzar o intentar con otra opción válida.")

# ----------------------------- #
# INICIO DEL SERVIDOR
# ----------------------------- #
if __name__ == "__main__":
    app.run(debug=True)
