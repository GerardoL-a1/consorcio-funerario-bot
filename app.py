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

# Diccionario de letras -> servicio (Aseguramos que las claves sean mayúsculas para una comparación consistente)
# Se mantiene la lógica de que las claves en este diccionario son las que se usan para buscar en planes_info.py
# La conversión a mayúsculas/minúsculas se maneja en la entrada del usuario.
selecciones_letras = {
    "A": "crédito de necesidad inmediata", "B": "servicio paquete fetal cremación",
    "C": "servicio paquete sencillo sepultura", "D": "servicio paquete básico sepultura",
    "E": "servicio cremación directa", "F": "servicio paquete de cremación",
    "G": "servicio paquete legal", "H": "servicio de refrigeración y conservación",
    "I": "red biker", "J": "red plus", "K": "red consorcio", "L": "red adulto mayor",
    "M": "preventa de nichos a temporalidad", "N": "traslado", "O": "ataúd",
    "P": "urna", "Q": "velación", "R": "boletas", "S": "carroza local",
    "T": "carroza a panteón u horno crematorio", "U": "carroza legal",
    "V": "camión local", "W": "embalsamado", "X": "embalsamado legal",
    "Y": "embalsamado infecto-contagiosa", "Z": "trámites de inhumación",
    "AA": "trámites de cremación", "AB": "trámites legales", "AC": "trámites de traslado",
    "AD": "trámites de internación nacional", "AE": "trámites de internación internacional",
    "AF": "equipo de velación", "AG": "cirios", "AH": "capilla de gobierno",
    "AI": "capilla particular", "AJ": "traslado carretero por km",
    "AK": "traslado de terracería por km", "AL": "camión foráneo por km",
}

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
    # Añadimos 'menu' sin acento explícitamente para mayor robustez
    return (
        mensaje.strip().lower() in ["menú", "menu", "menù", "inicio", "menuh", "inicioo", "home"]
        or parecido("menú", mensaje)
        or parecido("menu", mensaje) # Aseguramos que "menu" sin acento sea detectado
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

    # --- Reiniciar temporizador de inactividad por cada mensaje recibido ---
    if telefono in temporizadores:
        temporizadores[telefono].cancel()
        del temporizadores[telefono]
    temporizador = threading.Timer(600, mensaje_inactividad, args=(telefono,))
    temporizador.start()
    temporizadores[telefono] = temporizador

    # --- Volver al menú principal si se detecta 'menú' con tolerancia (PRIORIDAD ALTA) ---
    if es_mensaje_menu(mensaje):
        # Reinicia completamente la sesión para asegurar que el usuario vuelve al inicio
        sesiones[telefono] = {}
        return responder(MENSAJE_BIENVENIDA)

    # --- Regresar a submenús si se detecta 'regresar' ---
    if es_mensaje_regresar(mensaje):
        if "submenu" in sesiones.get(telefono, {}):
            if sesiones[telefono]["menu"] == "planes":
                # Elimina el submenu para volver a la selección 1, 2, 3 de planes
                del sesiones[telefono]["submenu"]
                # Si estaba en servicios individuales, también reinicia menu_serv
                if "menu_serv" in sesiones[telefono]:
                    del sesiones[telefono]["menu_serv"]
                return responder("🔙 Has regresado al submenú de *planes*. Escribe 1, 2 o 3 para seleccionar otra opción.\n📌 Puedes escribir la palabra *menú* para volver al inicio.")
            elif sesiones[telefono]["menu"] == "ubicacion":
                # En ubicación, "regresar" debería llevar a la pregunta de cita si ya se mostró la lista
                # Si ya se preguntó por cita, volver a preguntar
                if sesiones[telefono].get("menu") == "cita": # Si estaba en el flujo de cita, regresa a la pregunta de ubicacion
                    sesiones[telefono]["menu"] = "ubicacion"
                    return responder("🔙 Has regresado al submenú de *ubicaciones*. ¿Deseas agendar una cita? Responde 'sí' o 'no'.\n📌 Puedes escribir la palabra *menú* para volver al inicio.")
                else: # Si no estaba en cita, pero en ubicacion, no hay un "sub-submenú" al que regresar
                    return responder("🔙 No hay menú anterior al cual regresar en *ubicaciones*. ¿Deseas agendar una cita? Responde 'sí' o 'no'.\n📌 Puedes escribir la palabra *menú* para volver al inicio.")
        elif "menu_serv" in sesiones.get(telefono, {}):
            # Si está en un sub-submenú de servicios individuales (trámites, traslados, etc.)
            if sesiones[telefono]["menu_serv"] != "categorias": # Si no está ya en la vista de categorías
                sesiones[telefono]["menu_serv"] = "categorias"
                return responder("🔙 Has regresado a la categoría de *servicios individuales*. Elige A, B, C o D.\n📌 Puedes escribir la palabra *menú* para volver al inicio.")
            else: # Si ya está en categorías, regresar debería llevar al menú principal de planes
                del sesiones[telefono]["submenu"]
                del sesiones[telefono]["menu_serv"]
                return responder("🔙 Has regresado al submenú de *planes*. Escribe 1, 2 o 3 para seleccionar otra opción.\n📌 Puedes escribir la palabra *menú* para volver al inicio.")
        else:
            return responder("🔙 No hay menú anterior al cual regresar. Puedes escribir la palabra *menú* para volver al inicio.")

    # --- Confirmaciones como "gracias", "ok", etc. ---
    if contiene(claves_cierre, mensaje):
        return responder("👌 Gracias por confirmar. Si necesitas algo más, escribe la palabra *menú* para volver al inicio.")
    
    # ----------------------------- #
    # FLUJO: BIENVENIDA Y DETECCIÓN INICIAL
    # ----------------------------- #
    # Si no hay sesión activa, o si la sesión se reinició (por "menú")
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
            # Si el mensaje inicial no coincide con ninguna palabra clave, muestra el menú de bienvenida
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
            "To": "+525523680734", # Número secundario para emergencias
            "From": "whatsapp:+14155238886",
            "Body": alerta
        })

        sesiones[telefono] = {} # Reinicia la sesión después de enviar la alerta
        return responder("✅ Gracias. Hemos recibido tu emergencia. Un asesor te contactará de inmediato.\n\n📌 Si deseas más información, escribe la palabra *menú* para regresar al inicio.")

    # ----------------------------- #
    # FLUJO: UBICACIÓN
    # ----------------------------- #
    if sesiones[telefono].get("menu") == "ubicacion":
        if mensaje.lower() in ["sí", "si", "si me gustaría", "si quiero"]:
            sesiones[telefono]["menu"] = "cita" # Cambia el estado para solicitar datos de cita
            return responder("Perfecto. Por favor, indícanos tu nombre y un horario preferido para la cita.\n\n📌 Escribe la palabra *menú* para regresar al inicio.")
        elif mensaje.lower() in ["no", "no gracias", "no por ahora"]:
            sesiones[telefono] = {} # Reinicia la sesión si no quiere cita
            return responder("✅ Gracias por consultar nuestras ubicaciones. Si necesitas algo más, escribe la palabra *menú* para regresar al inicio.")
        else:
            return responder("No entendí tu respuesta. ¿Te gustaría agendar una cita? Responde 'sí' o 'no'.\n\n📌 Escribe la palabra *menú* para regresar al inicio.")
    
    # ----------------------------- #
    # FLUJO: PLANES
    # ----------------------------- #
    if sesiones[telefono].get("menu") == "planes":
        # Normalizamos el mensaje para la comparación numérica
        mensaje_normalizado = mensaje.strip()

        if "submenu" not in sesiones[telefono]: # Si aún no ha elegido un submenú de planes (1, 2 o 3)
            if mensaje_normalizado == "1":
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

            elif mensaje_normalizado == "2":
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

            elif mensaje_normalizado == "3":
                sesiones[telefono]["submenu"] = "servicios"
                sesiones[telefono]["menu_serv"] = "categorias" # Establece el estado para la selección de categorías de servicios
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
                return responder("❌ Opción no válida. Por favor, escribe *1*, *2* o *3* para seleccionar un tipo de plan.\n📌 También puedes escribir *menú* para regresar al inicio.")

        # Si ya está en un submenú de planes (inmediato, futuro)
        elif sesiones[telefono]["submenu"] in ["inmediato", "futuro"]:
            letra = mensaje.strip().upper() # Convertir a mayúsculas para una comparación consistente
            if letra in selecciones_letras:
                clave = selecciones_letras[letra]
                respuesta = responder_plan(clave)
                sesiones[telefono] = {} # Reinicia la sesión después de dar la información del plan
                return responder(respuesta + "\n\n📌 Si necesitas algo más, escribe la palabra *menú* para regresar al inicio.")
            else:
                return responder("❌ Letra no reconocida. Intenta otra opción o escribe *regresar* para volver al submenú.\n📌 Puedes escribir la palabra *menú* para volver al inicio.")

        # Si está en el submenú de servicios individuales
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

            # Si está en un sub-submenú de servicios individuales (trámites, traslados, etc.)
            elif sesiones[telefono]["menu_serv"] in ["tramites", "traslados", "equipamiento", "procedimientos"]:
                if letra in selecciones_letras:
                    clave = selecciones_letras[letra]
                    respuesta = responder_plan(clave)
                    sesiones[telefono] = {} # Reinicia la sesión después de dar la información del servicio
                    return responder(respuesta + "\n\n📌 Si necesitas algo más, escribe la palabra *menú* para regresar al inicio.")
                else:
                    return responder("❌ Letra no reconocida. Intenta de nuevo o escribe *regresar* para volver.\n📌 Puedes escribir la palabra *menú* para volver al inicio.")
    
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
        sesiones[telefono] = {} # Reinicia la sesión después de registrar la cita
        return responder("✅ Gracias. Hemos registrado tu solicitud de cita. Nuestro equipo te contactará pronto.\n\n📌 Puedes escribir la palabra *menú* para volver al inicio.")

    # ----------------------------- #
    # RESPUESTA GENERAL SI NADA COINCIDE
    # ----------------------------- #
    # Si el mensaje no fue manejado por ningún estado específico, o si el estado es inválido,
    # se devuelve al menú principal. Esto actúa como un "catch-all" para entradas inesperadas.
    return responder("🤖 No entendimos tu mensaje. Puedes escribir la palabra *menú* para comenzar o intentar con otra opción válida.")

# ----------------------------- #
# INICIO DEL SERVIDOR
# ----------------------------- #
if __name__ == "__main__":
    app.run(debug=True)
