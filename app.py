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

# --- Variables de Entorno y Constantes ---
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_MESSAGING_URL = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
TWILIO_AUTH = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
NUMERO_REENVIO_PRINCIPAL = os.getenv("NUMERO_REENVIO_PRINCIPAL", "+525523604519")
NUMERO_REENVIO_SECUNDARIO = os.getenv("NUMERO_REENVIO_SECUNDARIO", "+525523680734") # Asegúrate de configurar esta variable en Render

sesiones = {}
temporizadores = {}

# --- Mensajes Centralizados ---
MESSAGES = {
    "welcome": """👋 *Bienvenido a Consorcio Funerario*

Gracias por escribirnos.

Por favor indíquenos *en qué le gustaría recibir información o en qué podemos apoyarle*:
- Atención inmediata por *emergencia*
- Conocer nuestros *servicios funerarios*
- Consultar nuestras *ubicaciones disponibles*

📌 Puede escribir palabras como: *emergencia*, *planes*, *servicios*, *ubicación*, etc.""",

    "emergency_prompt": """🚨 *ATENCIÓN INMEDIATA*

Por favor responde con los siguientes datos:
🔹 Nombre completo del fallecido
🔹 Suceso o causa del fallecimiento
🔹 Ubicación actual del cuerpo
🔹 ¿Ya cuenta con su certificado de defunción?
🔹 Dos números de contacto
🔹 Nombre de la persona que nos está contactando

📌 Si fue un error, escribe la palabra *menú* para regresar al inicio.""",

    "emergency_received": "✅ Gracias. Hemos recibido tu emergencia. Un asesor te contactará de inmediato.\n\n📌 Si deseas más información, escribe la palabra *menú* para regresar al inicio.",

    "location_list": """📍 *Ubicaciones disponibles:*
1. Av. Tláhuac No. 5502, Col. El Rosario, CDMX
2. Av. Zacatlán No. 60, Col. San Lorenzo Tezonco, CDMX
3. Av. Zacatlán No. 10, Col. San Lorenzo Tezonco, CDMX

¿Deseas agendar una cita en alguna de nuestras sucursales? (Sí / No)

📌 Puedes escribir la palabra *menú* para regresar al inicio.""",

    "location_ask_appointment": "No entendí tu respuesta. ¿Te gustaría agendar una cita? Responde 'sí' o 'no'.\n\n📌 Escribe la palabra *menú* para regresar al inicio.",

    "appointment_prompt": "Perfecto. Por favor, indícanos tu nombre y un horario preferido para la cita.\n\n📌 Escribe la palabra *menú* para regresar al inicio.",

    "appointment_received": "✅ Gracias. Hemos registrado tu solicitud de cita. Nuestro equipo te contactará pronto.\n\n📌 Puedes escribir la palabra *menú* para volver al inicio.",

    "plans_menu": (
        "🧾 Has seleccionado *servicios funerarios*. Por favor, elige una opción:\n"
        "1. Planes de necesidad inmediata\n"
        "2. Planes a futuro\n"
        "3. Servicios individuales\n\n"
        "📝 Escribe el número de la opción deseada.\n"
        "📌 Escribe la palabra *menú* para regresar al inicio."
    ),

    "plans_inmediato_menu": (
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
        "🔙 Escribe *regresar* para volver al menú de planes.\n"
        "📌 Escribe *menú* para regresar al inicio."
    ),

    "plans_futuro_menu": (
        "🕰️ *Planes a futuro:*\n"
        "I. Red Biker\n"
        "J. Red Plus\n"
        "K. Red Consorcio\n"
        "L. Red Adulto Mayor\n"
        "M. Preventa de Nichos a Temporalidad\n"
        "N. Cremación Amigo Fiel\n" # Añadido
        "O. Cremación de Restos Áridos\n\n" # Añadido
        "📝 Escribe la letra correspondiente para más información.\n"
        "🔙 Escribe *regresar* para volver al menú de planes.\n"
        "📌 Escribe *menú* para regresar al inicio."
    ),

    # CORRECCIÓN: Renombrado de 'plans_individual_categories' a 'individual_categories'
    "individual_categories": (
        "☝🏻️ *Servicios Individuales* – Elige una categoría:\n\n"
        "A. Trámites y Papelería\n"
        "B. Traslados y Carrozas\n"
        "C. Objetos y Equipamiento\n"
        "D. Procedimientos Especiales\n\n"
        "📝 Escribe la letra correspondiente.\n"
        "🔙 Escribe *regresar* para volver al menú de planes.\n"
        "📌 Escribe *menú* para regresar al inicio."
    ),

    "individual_tramites_menu": (
        "📜 *Trámites y Papelería:*\n"
        "Z. Trámites de inhumación\n"
        "AA. Trámites de cremación\n"
        "AB. Trámites legales\n"
        "AC. Trámites de traslado\n"
        "AD. Trámites de internación nacional\n"
        "AE. Trámites de internación internacional\n\n"
        "📝 Escribe la letra deseada.\n"
        "🔙 Escribe *regresar* para volver a las categorías de servicios individuales.\n"
        "📌 Escribe *menú* para volver al inicio."
    ),

    "individual_traslados_menu": (
        "🚚 *Traslados y Carrozas:*\n"
        "P. Traslado\n" # Letra cambiada para evitar conflicto con planes_futuro_menu
        "Q. Carroza local\n" # Letra cambiada
        "R. Carroza a panteón u horno crematorio\n" # Letra cambiada
        "S. Carroza legal\n" # Letra cambiada
        "T. Camión local\n" # Letra cambiada
        "AJ. Traslado carretero por km\n"
        "AK. Traslado de terracería por km\n"
        "AL. Camión foráneo por km\n\n"
        "📝 Escribe la letra deseada.\n"
        "🔙 Escribe *regresar* para volver a las categorías de servicios individuales.\n"
        "📌 Escribe *menú* para volver al inicio."
    ),

    "individual_equipamiento_menu": (
        "🛄 *Objetos y Equipamiento:*\n"
        "U. Ataúd\n" # Letra cambiada
        "V. Urna\n" # Letra cambiada
        "AF. Equipo de velación\n"
        "AG. Cirios\n"
        "AH. Capilla de gobierno\n"
        "AI. Capilla particular\n\n"
        "📝 Escribe la letra deseada.\n"
        "🔙 Escribe *regresar* para volver a las categorías de servicios individuales.\n"
        "📌 Escribe *menú* para volver al inicio."
    ),

    "individual_procedimientos_menu": (
        "🧪 *Procedimientos Especiales:*\n"
        "W. Velación\n" # Letra cambiada
        "X. Boletas\n" # Letra cambiada
        "Y. Embalsamado\n" # Letra cambiada
        "Z. Embalsamado legal\n" # Letra cambiada
        "AA. Embalsamado infecto-contagiosa\n\n" # Letra cambiada
        "📝 Escribe la letra deseada.\n"
        "🔙 Escribe *regresar* para volver a las categorías de servicios individuales.\n"
        "📌 Escribe *menú* para volver al inicio."
    ),

    "invalid_option": "❌ Opción no válida. Por favor, elige una opción de las mostradas.\n📌 También puedes escribir *menú* para regresar al inicio.",
    "letter_not_recognized": "❌ Letra no reconocida. Intenta otra opción o escribe *regresar* para volver al submenú.\n📌 Puedes escribir la palabra *menú* para volver al inicio.",
    "category_not_recognized": "❌ Categoría no reconocida. Escribe A, B, C o D.\n📌 Puedes escribir *menú* para volver al inicio.",
    "no_text_received": "❗ No recibimos texto. Por favor escribe tu mensaje.",
    "thanks_confirmation": "👌 Gracias por confirmar. Si necesitas algo más, escribe la palabra *menú* para volver al inicio.",
    "inactivity_warning": "⌛ ¿Aún estás ahí? Si necesitas ayuda, escribe la palabra *menú* para volver al inicio.",
    "no_previous_menu": "🔙 No hay menú anterior al cual regresar. Puedes escribir la palabra *menú* para volver al inicio.",
    "general_error": "🤖 Lo siento, algo salió mal. Por favor, intenta de nuevo más tarde o escribe 'menú' para reiniciar.",
    "unrecognized_message": "🤖 No entendimos tu mensaje. Puedes escribir la palabra *menú* para comenzar o intentar con otra opción válida."
}

# --- Palabras Clave Generales ---
claves_planes = ["plan", "planes", "servicio", "servicios", "paquete", "información", "informacion"]
claves_emergencia = [
   "emergencia", "urgente", "fallecido", "murió", "murio", "accidente", "suceso",
    "acaba de fallecer", "acaba de morir", "necesito ayuda con un funeral", "necesito apoyo",
    "ayúdenos", "urgente apoyo", "urgente funeral", "funeral urgente", "ayuda urgente",
    "se murió", "se nos fue", "ya no está", "ya falleció", "ya murió",

    # Familiares directos
    "murió mi papá", "falleció mi papá", "mi papá murió", "mi papá falleció",
    "murió mi mamá", "falleció mi mamá", "mi mamá murió", "mi mamá falleció",
    "murió mi hijo", "falleció mi hijo", "mi hijo murió", "mi hijo falleció",
    "murió mi hija", "falleció mi hija", "mi hija murió", "mi hija falleció",

    # Familiares indirectos y otras relaciones
    "murió mi abuelo", "falleció mi abuelo", "murió mi abuela", "falleció mi abuela",
    "murió mi tío", "falleció mi tío", "murió mi tía", "falleció mi tía",
    "murió mi primo", "falleció mi primo", "murió mi prima", "falleció mi prima",
    "murió mi suegro", "falleció mi suegro", "murió mi suegra", "falleció mi suegra",
    "murió mi padrastro", "falleció mi padrastro", "murió mi madrastra", "falleció mi madrastra",
    "murió mi cuñado", "falleció mi cuñado", "murió mi cuñada", "falleció mi cuñada",

    # Frases informales y más coloquiales
    "murió alguien", "falleció alguien", "alguien acaba de morir", "se murió un familiar",
    "se nos fue un ser querido", "perdimos a un familiar", "perdí a un ser querido",
    "acaba de fallecer un familiar", "mi familiar murió", "mi ser querido falleció",
    "necesito un servicio funerario urgente", "necesito apoyo urgente", "urgente atención",
    "urgencia funeraria", "urgente fallecimiento", "atención por fallecimiento"
]
claves_ubicacion = ["ubicación", "ubicaciones", "sucursal", "sucursales", "dirección", "direccion"]
claves_cierre = ["gracias", "ok", "vale", "de acuerdo", "listo", "perfecto", "entendido", "muy bien"]

# Diccionario de letras -> servicio (ahora solo en minúsculas, la entrada del usuario se convertirá)
# CORRECCIÓN: Reorganización y adición de nuevas letras para evitar conflictos y añadir nuevos servicios
selecciones_letras = {
    "a": "crédito de necesidad inmediata", "b": "servicio paquete fetal cremación",
    "c": "servicio paquete sencillo sepultura", "d": "servicio paquete básico sepultura",
    "e": "servicio cremación directa", "f": "servicio paquete de cremación",
    "g": "servicio paquete legal", "h": "servicio de refrigeración y conservación",
    "i": "red biker", "j": "red plus", "k": "red consorcio", "l": "red adulto mayor",
    "m": "preventa de nichos a temporalidad",
    "n": "cremación amigo fiel", # Añadido
    "o": "servicio paquete de cremación de restos áridos", # Añadido

    # Servicios Individuales - Traslados y Carrozas (P-T)
    "p": "traslado",
    "q": "carroza local",
    "r": "carroza a panteón u horno crematorio",
    "s": "carroza legal",
    "t": "camión local",

    # Servicios Individuales - Objetos y Equipamiento (U-V)
    "u": "ataúd",
    "v": "urna",

    # Servicios Individuales - Procedimientos Especiales (W-Y)
    "w": "velación",
    "x": "boletas",
    "y": "embalsamado",
    "z": "embalsamado legal", # Letra cambiada
    "aa": "embalsamado infecto-contagiosa", # Letra cambiada

    # Servicios Individuales - Trámites y Papelería (AB-AE)
    "ab": "trámites de inhumación", # Letra cambiada
    "ac": "trámites de cremación", # Letra cambiada
    "ad": "trámites legales", # Letra cambiada
    "ae": "trámites de traslado", # Letra cambiada
    "af": "trámites de internación nacional", # Letra cambiada
    "ag": "trámites de internación internacional", # Letra cambiada

    # Servicios Individuales - Equipo de Velación y Capillas (AH-AK)
    "ah": "equipo de velación", # Letra cambiada
    "ai": "cirios", # Letra cambiada
    "aj": "capilla de gobierno", # Letra cambiada
    "ak": "capilla particular", # Letra cambiada

    # Traslados por Kilómetro (AL-AN)
    "al": "traslado carretero por km", # Letra cambiada
    "am": "traslado de terracería por km", # Letra cambiada
    "an": "camión foráneo por km", # Letra cambiada
}

# --- Funciones Auxiliares ---
def responder(texto):
    respuesta = MessagingResponse()
    respuesta.message(texto)
    return str(respuesta)

def mensaje_inactividad(numero):
    if numero in sesiones:
        requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
            "To": numero,
            "From": "whatsapp:+14155238886",
            "Body": MESSAGES["inactivity_warning"]
        })
        temporizadores.pop(numero, None)
        sesiones.pop(numero, None) # Limpiar sesión al expirar inactividad

# --- Detección Inteligente de Palabras Similares ---
def parecido(palabra_objetivo, mensaje, umbral=0.75):
    """Detecta si una palabra es suficientemente parecida al mensaje recibido."""
    return SequenceMatcher(None, palabra_objetivo.lower(), mensaje.lower()).ratio() >= umbral

def contiene_flexible(lista_claves, mensaje_usuario, umbral=0.75):
    """Devuelve True si el mensaje es similar a alguna palabra clave."""
    mensaje_usuario = mensaje_usuario.strip().lower()
    for palabra_clave in lista_claves:
        # CORRECCIÓN: Mejorar la detección flexible para frases
        # Si la palabra clave es una frase, buscarla directamente
        if " " in palabra_clave:
            if palabra_clave in mensaje_usuario:
                return True
        # Si es una palabra simple o para comparación de similitud
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

@app.route("/", methods=["GET"])
def home():
    return "✅ Bot Consorcio Funerario funcionando."

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        mensaje = request.form.get("Body", "").strip()
        telefono = request.form.get("From", "")
        logging.info(f"Mensaje recibido: {mensaje} de {telefono}")

        if not mensaje:
            return responder(MESSAGES["no_text_received"])

        # --- Reiniciar temporizador de inactividad por cada mensaje recibido ---
        if telefono in temporizadores:
            temporizadores[telefono].cancel()
            del temporizadores[telefono]
        temporizador = threading.Timer(600, mensaje_inactividad, args=(telefono,)) # 10 minutos
        temporizador.start()
        temporizadores[telefono] = temporizador

        # --- Volver al menú principal si se detecta 'menú' con tolerancia (PRIORIDAD ALTA) ---
        if es_mensaje_menu(mensaje):
            sesiones[telefono] = {} # Reinicia completamente la sesión
            return responder(MESSAGES["welcome"])

        # --- Regresar a submenús si se detecta 'regresar' ---
        if es_mensaje_regresar(mensaje):
            current_session = sesiones.get(telefono, {})
            current_menu = current_session.get("menu")
            current_submenu = current_session.get("submenu")
            current_menu_serv = current_session.get("menu_serv")

            if current_menu == "planes":
                if current_menu_serv and current_menu_serv != "categorias":
                    # Si está en un sub-submenú de servicios individuales (trámites, traslados, etc.)
                    sesiones[telefono]["menu_serv"] = "categorias"
                    return responder(MESSAGES["individual_categories"]) # CORRECCIÓN: Usar la clave correcta
                elif current_submenu:
                    # Si está en un submenú de planes (inmediato, futuro, servicios)
                    del sesiones[telefono]["submenu"]
                    if "menu_serv" in sesiones[telefono]:
                        del sesiones[telefono]["menu_serv"]
                    return responder(MESSAGES["plans_menu"])
                else:
                    # Si ya está en el menú principal de planes, no hay a dónde regresar
                    return responder(MESSAGES["no_previous_menu"])
            elif current_menu == "ubicacion" or current_menu == "cita":
                # Si estaba en el flujo de cita, regresa a la pregunta de ubicacion
                if current_menu == "cita":
                    sesiones[telefono]["menu"] = "ubicacion"
                    return responder(MESSAGES["location_list"])
                else:
                    # Si ya está en el menú de ubicación y no en cita, no hay a dónde regresar
                    return responder(MESSAGES["no_previous_menu"])
            else:
                return responder(MESSAGES["no_previous_menu"])

        # --- Confirmaciones como "gracias", "ok", etc. ---
        if contiene_flexible(claves_cierre, mensaje):
            sesiones[telefono] = {} # Reinicia la sesión después de una confirmación de cierre
            return responder(MESSAGES["thanks_confirmation"])

        # ----------------------------- #
        # FLUJO: BIENVENIDA Y DETECCIÓN INICIAL
        # ----------------------------- #
        # Si no hay sesión activa, o si la sesión se reinició (por "menú" o inactividad)
        if not sesiones.get(telefono):
            if contiene_flexible(claves_emergencia, mensaje):
                sesiones[telefono] = {"menu": "emergencia"}
                return responder(MESSAGES["emergency_prompt"])

            elif contiene_flexible(claves_ubicacion, mensaje):
                sesiones[telefono] = {"menu": "ubicacion"}
                return responder(MESSAGES["location_list"])

            elif contiene_flexible(claves_planes, mensaje):
                sesiones[telefono] = {"menu": "planes"}
                return responder(MESSAGES["plans_menu"])
            else:
                # Si el mensaje inicial no coincide con ninguna palabra clave, muestra el menú de bienvenida
                return responder(MESSAGES["welcome"])

        # ----------------------------- #
        # FLUJO: EMERGENCIA
        # ----------------------------- #
        if sesiones[telefono].get("menu") == "emergencia":
            alerta = f"""📨 *NUEVA EMERGENCIA FUNERARIA*
De: {telefono}
Mensaje: {mensaje}
"""
            requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
                "To": NUMERO_REENVIO_PRINCIPAL,
                "From": "whatsapp:+14155238886",
                "Body": alerta
            })
            requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
                "To": NUMERO_REENVIO_SECUNDARIO,
                "From": "whatsapp:+14155238886",
                "Body": alerta
            })

            sesiones[telefono] = {} # Reinicia la sesión después de enviar la alerta
            return responder(MESSAGES["emergency_received"])

        # ----------------------------- #
        # FLUJO: UBICACIÓN
        # ----------------------------- #
        if sesiones[telefono].get("menu") == "ubicacion":
            if mensaje.lower() in ["sí", "si", "si me gustaría", "si quiero"]:
                sesiones[telefono]["menu"] = "cita" # Cambia el estado para solicitar datos de cita
                return responder(MESSAGES["appointment_prompt"])
            elif mensaje.lower() in ["no", "no gracias", "no por ahora"]:
                sesiones[telefono] = {} # Reinicia la sesión si no quiere cita
                return responder(MESSAGES["thanks_confirmation"])
            else:
                return responder(MESSAGES["location_ask_appointment"])

        # ----------------------------- #
        # FLUJO: PLANES
        # ----------------------------- #
        if sesiones[telefono].get("menu") == "planes":
            if "submenu" not in sesiones[telefono]: # Si aún no ha elegido un submenú de planes (1, 2 o 3)
                if mensaje == "1":
                    sesiones[telefono]["submenu"] = "inmediato"
                    return responder(MESSAGES["plans_inmediato_menu"])

                elif mensaje == "2":
                    sesiones[telefono]["submenu"] = "futuro"
                    return responder(MESSAGES["plans_futuro_menu"])

                elif mensaje == "3":
                    sesiones[telefono]["submenu"] = "servicios"
                    sesiones[telefono]["menu_serv"] = "categorias" # Establece el estado para la selección de categorías de servicios
                    return responder(MESSAGES["individual_categories"]) # CORRECCIÓN: Usar la clave correcta

                else:
                    return responder(MESSAGES["invalid_option"])

            # Si ya está en un submenú de planes (inmediato, futuro)
            elif sesiones[telefono]["submenu"] in ["inmediato", "futuro"]:
                letra = mensaje.strip().lower() # Convertir a minúsculas para una comparación consistente
                if letra in selecciones_letras:
                    clave = selecciones_letras[letra]
                    respuesta = responder_plan(clave)
                    sesiones[telefono] = {} # Reinicia la sesión después de dar la información del plan
                    return responder(respuesta + "\n\n📌 Si necesitas algo más, escribe la palabra *menú* para regresar al inicio.")
                else:
                    return responder(MESSAGES["letter_not_recognized"])

            # Si está en el submenú de servicios individuales
            elif sesiones[telefono]["submenu"] == "servicios":
                letra = mensaje.strip().lower()

                if sesiones[telefono]["menu_serv"] == "categorias":
                    if letra == "a":
                        sesiones[telefono]["menu_serv"] = "tramites"
                        return responder(MESSAGES["individual_tramites_menu"])
                    elif letra == "b":
                        sesiones[telefono]["menu_serv"] = "traslados"
                        return responder(MESSAGES["individual_traslados_menu"])
                    elif letra == "c":
                        sesiones[telefono]["menu_serv"] = "equipamiento"
                        return responder(MESSAGES["individual_equipamiento_menu"])
                    elif letra == "d":
                        sesiones[telefono]["menu_serv"] = "procedimientos"
                        return responder(MESSAGES["individual_procedimientos_menu"])
                    else:
                        return responder(MESSAGES["category_not_recognized"])

                # Si está en un sub-submenú de servicios individuales (trámites, traslados, etc.)
                elif sesiones[telefono]["menu_serv"] in ["tramites", "traslados", "equipamiento", "procedimientos"]:
                    if letra in selecciones_letras:
                        clave = selecciones_letras[letra]
                        respuesta = responder_plan(clave)
                        sesiones[telefono] = {} # Reinicia la sesión después de dar la información del servicio
                        return responder(respuesta + "\n\n📌 Si necesitas algo más, escribe la palabra *menú* para regresar al inicio.")
                    else:
                        return responder(MESSAGES["letter_not_recognized"])

        # ----------------------------- #
        # FLUJO: CITA DESDE UBICACIÓN
        # ----------------------------- #
        if sesiones[telefono].get("menu") == "cita":
            datos = f"📆 *CITA SOLICITADA*\nCliente: {telefono}\nDatos: {mensaje}"
            requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
                "To": NUMERO_REENVIO_PRINCIPAL,
                "From": "whatsapp:+14155238886",
                "Body": datos
            })
            sesiones[telefono] = {} # Reinicia la sesión después de registrar la cita
            return responder(MESSAGES["appointment_received"])

        # ----------------------------- #
        # RESPUESTA GENERAL SI NADA COINCIDE
        # ----------------------------- #
        # Si el mensaje no fue manejado por ningún estado específico, o si el estado es inválido,
        # se devuelve al menú principal. Esto actúa como un "catch-all" para entradas inesperadas.
        return responder(MESSAGES["unrecognized_message"])

    except Exception as e:
        logging.error(f"Error inesperado en webhook: {e}", exc_info=True)
        return responder(MESSAGES["general_error"])

# ----------------------------- #
# INICIO DEL SERVIDOR
# ----------------------------- #
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))