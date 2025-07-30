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
from datetime import datetime # Importar datetime para fecha y hora

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# --- Variables de Entorno y Constantes ---
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_MESSAGING_URL = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
TWILIO_AUTH = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
NUMERO_REENVIO_PRINCIPAL = os.getenv("NUMERO_REENVIO_PRINCIPAL", "+525523680734")
NUMERO_REENVIO_SECUNDARIO = os.getenv("NUMERO_REENVIO_SECUNDARIO", "+525511230871") # Asegúrate de configurar esta variable en Render

# Nuevos números de asignación de turno
NUMERO_ASESOR_2 = os.getenv("NUMERO_ASESOR_2", "+525523680734") # Número para mostrar y recibir resumen (Turno 2)
NUMERO_ASESOR_3 = os.getenv("NUMERO_ASESOR_3", "+525511230871") # Número para mostrar y recibir resumen (Turno 3)

# Variable para gestionar el turno (simple alternancia para el ejemplo)
# En un entorno real, esto podría ser una base de datos o un servicio externo
turno_actual = 2 # Inicia con el turno 2

sesiones = {}
temporizadores = {}

# --- Mensajes Centralizados ---
MESSAGES = {
    "welcome": (
        "👋 *Bienvenido a Consorcio Funerario*\n\n"
        "Gracias por escribirnos.\n\n"
        "Por favor indíquenos *en qué le gustaría recibir información o en qué podemos apoyarle*:\n"
        "- Atención inmediata por *emergencia*\n"
        "- Conocer nuestros *servicios funerarios*\n"
        "- Consultar nuestras *ubicaciones disponibles*\n\n"
        "📌 Puede escribir palabras como: *emergencia*, *planes*, *servicios*, *ubicación*, etc."
    ),

    "emergency_prompt": (
        "🚨 *ATENCIÓN INMEDIATA*\n\n"
        "Por favor responde con los siguientes datos:\n"
        "🔹 Nombre completo del fallecido\n"
        "🔹 Suceso o causa del fallecimiento\n"
        "🔹 Ubicación actual del cuerpo\n"
        "🔹 ¿Ya cuenta con su certificado de defunción?\n"
        "🔹 Dos números de contacto\n"
        "🔹 Nombre de la persona que nos está contactando\n\n"
        "📌 Si fue un error, escribe la palabra *menú* para regresar al inicio."
    ),

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
        "📌 Escribe el número de la opción deseada."
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
        "N. Cremación Amigo Fiel\n"
        "O. Cremación de Restos Áridos\n\n"
        "📝 Escribe la letra correspondiente para más información.\n"
        "🔙 Escribe *regresar* para volver al menú de planes.\n"
        "📌 Escribe *menú* para regresar al inicio."
    ),

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
        "AB. Trámites de inhumación\n"
        "AC. Trámites de cremación\n"
        "AD. Trámites legales\n"
        "AE. Trámites de traslado\n"
        "AF. Trámites de internación nacional\n"
        "AG. Trámites de internación internacional\n\n"
        "📝 Escribe la letra deseada.\n"
        "🔙 Escribe *regresar* para volver a las categorías de servicios individuales.\n"
        "📌 Escribe *menú* para volver al inicio."
    ),

    "individual_traslados_menu": (
        "🚚 *Traslados y Carrozas:*\n"
        "P. Traslado\n"
        "Q. Carroza local\n"
        "R. Carroza a panteón u horno crematorio\n"
        "S. Carroza legal\n"
        "T. Camión local\n"
        "AL. Traslado carretero por km\n"
        "AM. Traslado de terracería por km\n"
        "AN. Camión foráneo por km\n\n"
        "📝 Escribe la letra deseada.\n"
        "🔙 Escribe *regresar* para volver a las categorías de servicios individuales.\n"
        "📌 Escribe *menú* para volver al inicio."
    ),

    "individual_equipamiento_menu": (
        "🛄 *Objetos y Equipamiento:*\n"
        "U. Ataúd\n"
        "V. Urna\n"
        "AH. Equipo de velación\n"
        "AI. Cirios\n"
        "AJ. Capilla de gobierno\n"
        "AK. Capilla particular\n\n"
        "📝 Escribe la letra deseada.\n"
        "🔙 Escribe *regresar* para volver a las categorías de servicios individuales.\n"
        "📌 Escribe *menú* para volver al inicio."
    ),

    "individual_procedimientos_menu": (
        "🧪 *Procedimientos Especiales:*\n"
        "W. Velación\n"
        "X. Boletas\n"
        "Y. Embalsamado\n"
        "Z. Embalsamado legal\n"
        "AA. Embalsamado infecto-contagiosa\n\n"
        "📝 Escribe la letra deseada.\n"
        "🔙 Escribe *regresar* para volver a las categorías de servicios individuales.\n"
        "📌 Escribe *menú* para volver al inicio."
    ),

    "invalid_option": "❌ Opción no válida. Por favor, elige una opción de las mostradas.\n📌 También puedes escribir *menú* para regresar al inicio.",
    "letter_not_recognized": "❌ Letra no reconocida. Intenta otra opción o escribe *regresar* para volver al submenú.\n📌 Puedes escribir la palabra *menú* para volver al inicio.",
    "category_not_recognized": "❌ Categoría no reconocida. Escribe A, B, C o D.\n📌 Puedes escribir *menú* para volver al inicio.",
    "no_text_received": (
        "❗ No recibimos ningún mensaje. Por favor escríbanos para poder ayudarle."
    ),
    "thanks_confirmation": "👌 Gracias por confirmar. Si necesitas algo más, escribe la palabra *menú* para volver al inicio.",
    "inactivity_warning": (
        "⌛ *¿Aún necesita ayuda?*\n\n"
        "Hemos notado que no continuó la conversación. "
        "Si desea asistencia personalizada, por favor escriba:\n"
        "- La palabra *menú* para volver a empezar.\n"
        "- O escriba *asesor* para contactar directamente con uno de nuestros especialistas funerarios.\n\n"
        "📌 Nuestro equipo está listo para atenderle cuando lo necesite."
    ),
    "no_previous_menu": "🔙 No hay menú anterior al cual regresar. Puedes escribir la palabra *menú* para volver al inicio.",
    "general_error": (
        "🤖 Lo sentimos, hubo un inconveniente interno.\n\n"
        "Por favor intente nuevamente o escriba *menú* para reiniciar la conversación."
    ),
    "unrecognized_message": (
        "🤖 No entendimos su mensaje.\n\n"
        "Por favor escriba la palabra *menú* para comenzar o elija alguna de las opciones mencionadas."
    ),

    # --- Nuevos mensajes para el flujo de contacto ---
    "contact_clarification": (
        "🔔 *Importante:*\n"
        "Tenga en cuenta que el número de contacto que le compartiremos es únicamente para llamadas normales (no WhatsApp), ya que usamos un sistema empresarial."
    ),
    "ask_contact_interest": (
        "¿Le gustaría contactar con un asesor funerario en este momento para aclarar sus dudas o contratar su servicio?\n"
        "Tenga en cuenta que el número de contacto que le compartiremos es únicamente para llamadas normales, no por WhatsApp, ya que usamos un sistema empresarial."
    ),
    "direct_contact_info": (
        "✅ Perfecto.\n"
        "Aquí tiene el contacto directo de nuestro asesor funerario 📞 {numero_asesor}\n"
        "Puede llamarnos ahora mismo o, si lo prefiere, indicarnos si desea que nosotros le llamemos.\n\n"
        "El número que verá en su pantalla será este mismo, para que pueda identificarlo al recibir nuestra llamada.\n\n"
        "📌 Recuerde: se trata de una llamada convencional, no llamada por WhatsApp."
    ),
    "call_requested_info": (
        "✅ Perfecto.\n"
        "En breve nuestro asesor funerario se pondrá en contacto con usted.\n\n"
        "Le proporcionamos el número desde el cual se realizará la llamada 📞 {numero_asesor} para que lo guarde y pueda identificarlo cuando le llamemos.\n\n"
        "📌 Recuerde: es una llamada normal, no vía WhatsApp."
    ),
    "passive_contact_info": (
        "De cualquier forma, si más adelante desea contactarnos, puede hacerlo al siguiente número directo 📞 {numero_asesor}.\n\n"
        "Tenga en cuenta que es para llamadas normales, no WhatsApp.\n\n"
        "En caso de que prefiera que nosotros le marquemos posteriormente, por favor indíquelo y lo atenderemos con gusto."
    ),
    "whatsapp_call_warning": (
        "Parece que intentó llamarnos por WhatsApp.\n"
        "Le recordamos que nuestro sistema es empresarial y no permite llamadas por WhatsApp. Por favor, realice una llamada normal al número que le proporcionamos."
    ),
    "emergency_contact_direct": (
        "Gracias. Hemos recibido tu emergencia. Nuestro asesor funerario está disponible para atenderte de inmediato. Por favor, llámanos al siguiente número 📞 {numero_asesor}.\n"
        "Recuerda: es una llamada normal (no WhatsApp)."
    ),
    "direct_contact_after_rescue": (
        "✅ Perfecto. Aquí tiene el contacto directo de nuestro asesor funerario:\n"
        "📞 {numero_asesor}\n\n"
        "Puede realizar una llamada normal ahora mismo o indicarnos si prefiere que nuestro asesor le llame.\n\n"
        "Recuerde: es llamada convencional, no por WhatsApp."
    ),
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
claves_asesor = ["asesor", "especialista", "ayuda", "humano", "agente", "llamar", "marcar", "llamame", "quiero que me llamen", "me pueden marcar"] # Añadida "llamar", "marcar", "llamame", "quiero que me llamen", "me pueden marcar"

# Diccionario de letras -> servicio (ahora solo en minúsculas, la entrada del usuario se convertirá)
selecciones_letras = {
    "a": "crédito de necesidad inmediata", "b": "servicio paquete fetal cremación",
    "c": "servicio paquete sencillo sepultura", "d": "servicio paquete básico sepultura",
    "e": "servicio cremación directa", "f": "servicio paquete de cremación",
    "g": "servicio paquete legal", "h": "servicio de refrigeración y conservación",
    "i": "red biker", "j": "red plus", "k": "red consorcio", "l": "red adulto mayor",
    "m": "preventa de nichos a temporalidad",
    "n": "cremación amigo fiel",
    "o": "servicio paquete de cremación de restos áridos",

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
    "z": "embalsamado legal",
    "aa": "embalsamado infecto-contagiosa",

    # Servicios Individuales - Trámites y Papelería (AB-AG)
    "ab": "trámites de inhumación",
    "ac": "trámites de cremación",
    "ad": "trámites legales",
    "ae": "trámites de traslado",
    "af": "trámites de internación nacional",
    "ag": "trámites de internación internacional",

    # Servicios Individuales - Equipo de Velación y Capillas (AH-AK)
    "ah": "equipo de velación",
    "ai": "cirios",
    "aj": "capilla de gobierno",
    "ak": "capilla particular",

    # Traslados por Kilómetro (AL-AN)
    "al": "traslado carretero por km",
    "am": "traslado de terracería por km",
    "an": "camión foráneo por km",
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
            "From": "whatsapp:+525510704725",
            "Body": MESSAGES["inactivity_warning"]
        })
        temporizadores.pop(numero, None)
        sesiones.pop(numero, None) # Limpiar sesión al expirar inactividad

def parecido(palabra_objetivo, mensaje, umbral=0.75):
    """Detecta si una palabra es suficientemente parecida al mensaje recibido."""
    return SequenceMatcher(None, palabra_objetivo.lower(), mensaje.lower()).ratio() >= umbral

def contiene_flexible(lista_claves, mensaje_usuario, umbral=0.75):
    """Devuelve True si el mensaje es similar a alguna palabra clave."""
    mensaje_usuario = mensaje_usuario.strip().lower()
    for palabra_clave in lista_claves:
        if " " in palabra_clave:
            if palabra_clave in mensaje_usuario:
                return True
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

def obtener_numero_asesor():
    """Alterna entre los números de asesor para la asignación de turnos."""
    global turno_actual
    if turno_actual == 2:
        numero = NUMERO_ASESOR_2
        turno_actual = 3
    else:
        numero = NUMERO_ASESOR_3
        turno_actual = 2
    return numero

def enviar_resumen_asesor(telefono_cliente, numero_asesor_destino, tipo_origen, descripcion, nota=""):
    """
    Genera y envía el mensaje resumen al número del asesor.
    """
    now = datetime.now()
    fecha = now.strftime("%d/%m/%Y")
    hora = now.strftime("%H:%M:%S")

    # Eliminar el prefijo "whatsapp:" del número del cliente para el resumen
    nombre_cliente = sesiones.get(telefono_cliente, {}).get("nombre_cliente", "Desconocido")
    telefono_cliente_limpio = telefono_cliente.replace("whatsapp:", "")

    resumen_mensaje = f"""🤖 *MENSAJE DEL ROBOT FUNERARIO* 🤖

🧑 *Nombre*: {nombre_cliente}
📞 *Número*: {telefono_cliente_limpio}
📋 *Plan / Emergencia / Ubicación*: {descripcion}
📍 *Origen*: {tipo_origen}
📆 *Fecha*: {fecha}
⏰ *Hora*: {hora}

🔔 *Nota*: {nota}
"""
    requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
        "To": numero_asesor_destino,
        "From": "whatsapp:+525510704725", # El número del bot que envía el resumen
        "Body": resumen_mensaje
    })
    logging.info(f"Resumen enviado a {numero_asesor_destino} para cliente {telefono_cliente_limpio}")


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
                    sesiones[telefono]["menu_serv"] = "categorias"
                    return responder(MESSAGES["individual_categories"])
                elif current_submenu:
                    del sesiones[telefono]["submenu"]
                    if "menu_serv" in sesiones[telefono]:
                        del sesiones[telefono]["menu_serv"]
                    return responder(MESSAGES["plans_menu"])
                else:
                    return responder(MESSAGES["no_previous_menu"])
            elif current_menu == "ubicacion" or current_menu == "cita":
                if current_menu == "cita":
                    sesiones[telefono]["menu"] = "ubicacion"
                    return responder(MESSAGES["location_list"])
                else:
                    return responder(MESSAGES["no_previous_menu"])
            else:
                return responder(MESSAGES["no_previous_menu"])

        # --- Manejar la palabra clave 'asesor' (prioridad alta) ---
        # Esto permite al usuario pedir un asesor en cualquier momento, incluso si la sesión es nueva.
        if contiene_flexible(claves_asesor, mensaje):
            numero_asesor = obtener_numero_asesor()
            sesiones[telefono] = {} # Limpiar sesión para iniciar un nuevo flujo de contacto directo
            return responder(MESSAGES["direct_contact_after_rescue"].format(numero_asesor=numero_asesor))


        # --- Confirmaciones como "gracias", "ok", etc. ---
        if contiene_flexible(claves_cierre, mensaje):
            sesiones[telefono] = {} # Reinicia la sesión después de una confirmación de cierre
            return responder(MESSAGES["thanks_confirmation"])

        # ----------------------------- #
        # FLUJO: BIENVENIDA Y DETECCIÓN INICIAL
        # ----------------------------- #
        # Esta sección solo se ejecuta si la sesión es nueva y no se detectó "menú", "regresar" o "asesor"
        if not sesiones.get(telefono):
            if contiene_flexible(claves_emergencia, mensaje):
                sesiones[telefono] = {"menu": "emergencia", "nombre_cliente": "Cliente de Emergencia"} # Placeholder para nombre
                # En emergencia, se fuerza el contacto directo
                numero_asesor = obtener_numero_asesor()
                sesiones[telefono]["numero_asesor_asignado"] = numero_asesor
                sesiones[telefono]["estado_contacto"] = "esperando_datos_emergencia" # Nuevo estado para capturar datos
                return responder(MESSAGES["emergency_prompt"])

            elif contiene_flexible(claves_ubicacion, mensaje):
                sesiones[telefono] = {"menu": "ubicacion", "nombre_cliente": "Cliente de Ubicación"} # Placeholder para nombre
                return responder(MESSAGES["location_list"])

            elif contiene_flexible(claves_planes, mensaje):
                sesiones[telefono] = {"menu": "planes", "nombre_cliente": "Cliente de Planes"} # Placeholder para nombre
                return responder(MESSAGES["plans_menu"])
            else:
                # Si no se reconoce ninguna de las intenciones iniciales, se envía el mensaje de bienvenida
                return responder(MESSAGES["welcome"])

        # ----------------------------- #
        # FLUJO: EMERGENCIA
        # ----------------------------- #
        if sesiones[telefono].get("menu") == "emergencia":
            if sesiones[telefono].get("estado_contacto") == "esperando_datos_emergencia":
                # Aquí se asume que el mensaje contiene los datos de la emergencia
                # Se guarda el mensaje completo como descripción para el resumen
                sesiones[telefono]["descripcion_resumen"] = mensaje
                numero_asesor = sesiones[telefono]["numero_asesor_asignado"]

                # Enviar resumen inmediatamente
                enviar_resumen_asesor(
                    telefono,
                    numero_asesor,
                    "Emergencias",
                    mensaje,
                    "El cliente fue dirigido a llamar directamente."
                )
                sesiones[telefono]["estado_contacto"] = "ofreciendo_contacto_emergencia"
                return responder(MESSAGES["emergency_contact_direct"].format(numero_asesor=numero_asesor))
            # Si el cliente responde después de recibir el número de emergencia, se asume que es una confirmación o una solicitud de llamada
            elif sesiones[telefono].get("estado_contacto") == "ofreciendo_contacto_emergencia":
                # Aquí se maneja si el cliente pide que le llamen después de recibir el número de emergencia
                if contiene_flexible(["si", "sí", "llámame", "quiero que me llamen", "me pueden marcar"], mensaje):
                    numero_asesor = sesiones[telefono]["numero_asesor_asignado"]
                    enviar_resumen_asesor(
                        telefono,
                        numero_asesor,
                        "Emergencias",
                        sesiones[telefono].get("descripcion_resumen", "Datos de emergencia no capturados."),
                        "El cliente solicitó ser llamado."
                    )
                    sesiones[telefono] = {} # Reinicia la sesión
                    return responder(MESSAGES["call_requested_info"].format(numero_asesor=numero_asesor))
                else:
                    # Si no es una solicitud de llamada, se asume que ya se le dio el número y se cierra el flujo
                    sesiones[telefono] = {} # Reinicia la sesión
                    return responder(MESSAGES["thanks_confirmation"])


        # ----------------------------- #
        # FLUJO: UBICACIÓN
        # ----------------------------- #
        if sesiones[telefono].get("menu") == "ubicacion":
            if "estado_cita" not in sesiones[telefono]: # Primera pregunta sobre agendar cita
                if mensaje.lower() in ["sí", "si", "si me gustaría", "si quiero"]:
                    sesiones[telefono]["estado_cita"] = "solicitando_datos_cita"
                    return responder(MESSAGES["appointment_prompt"])
                elif mensaje.lower() in ["no", "no gracias", "no por ahora"]:
                    sesiones[telefono] = {} # Reinicia la sesión si no quiere cita
                    numero_asesor = obtener_numero_asesor()
                    return responder(MESSAGES["passive_contact_info"].format(numero_asesor=numero_asesor))
                else:
                    return responder(MESSAGES["location_ask_appointment"])
            elif sesiones[telefono].get("estado_cita") == "solicitando_datos_cita":
                # Aquí se asume que el mensaje contiene el nombre y horario preferido
                sesiones[telefono]["descripcion_resumen"] = f"Cita solicitada: {mensaje}"
                sesiones[telefono]["estado_cita"] = "preguntar_contacto_ubicacion"
                return responder(MESSAGES["ask_contact_interest"])
            elif sesiones[telefono].get("estado_cita") == "preguntar_contacto_ubicacion":
                numero_asesor = obtener_numero_asesor()
                sesiones[telefono]["numero_asesor_asignado"] = numero_asesor
                if contiene_flexible(["sí", "si", "si me gustaría", "si quiero"], mensaje):
                    sesiones[telefono]["estado_contacto"] = "esperando_confirmacion_llamada"
                    enviar_resumen_asesor(
                        telefono,
                        numero_asesor,
                        "Ubicaciones",
                        sesiones[telefono].get("descripcion_resumen", "Cita solicitada."),
                        "El cliente realizará la llamada."
                    )
                    return responder(MESSAGES["direct_contact_info"].format(numero_asesor=numero_asesor))
                elif contiene_flexible(["no", "no gracias", "no por ahora"], mensaje):
                    sesiones[telefono] = {} # Reinicia la sesión
                    return responder(MESSAGES["passive_contact_info"].format(numero_asesor=numero_asesor))
                # AÑADIDO: Manejo explícito de "llámame" en este punto
                elif contiene_flexible(["llámame", "quiero que me llamen", "me pueden marcar"], mensaje):
                    enviar_resumen_asesor(
                        telefono,
                        numero_asesor,
                        "Ubicaciones",
                        sesiones[telefono].get("descripcion_resumen", "Cita solicitada."),
                        "El cliente solicitó ser llamado."
                    )
                    sesiones[telefono] = {} # Reinicia la sesión
                    return responder(MESSAGES["call_requested_info"].format(numero_asesor=numero_asesor))
                else:
                    return responder(MESSAGES["invalid_option"])
            elif sesiones[telefono].get("estado_contacto") == "esperando_confirmacion_llamada":
                # Si el cliente responde después de recibir el número, se asume que es una confirmación o una solicitud de llamada
                # AÑADIDO: Manejo explícito de "llámame" si ya se dio el número
                if contiene_flexible(["llámame", "quiero que me llamen", "me pueden marcar"], mensaje):
                    numero_asesor = sesiones[telefono]["numero_asesor_asignado"]
                    enviar_resumen_asesor(
                        telefono,
                        numero_asesor,
                        "Ubicaciones",
                        sesiones[telefono].get("descripcion_resumen", "Cita solicitada."),
                        "El cliente solicitó ser llamado."
                    )
                    sesiones[telefono] = {} # Reinicia la sesión
                    return responder(MESSAGES["call_requested_info"].format(numero_asesor=numero_asesor))
                else:
                    sesiones[telefono] = {} # Reinicia la sesión
                    return responder(MESSAGES["thanks_confirmation"])


        # ----------------------------- #
        # FLUJO: PLANES
        # ----------------------------- #
        if sesiones[telefono].get("menu") == "planes":
            if "submenu" not in sesiones[telefono]:
                if mensaje == "1":
                    sesiones[telefono]["submenu"] = "inmediato"
                    return responder(MESSAGES["plans_inmediato_menu"])
                elif mensaje == "2":
                    sesiones[telefono]["submenu"] = "futuro"
                    return responder(MESSAGES["plans_futuro_menu"])
                elif mensaje == "3":
                    sesiones[telefono]["submenu"] = "servicios"
                    sesiones[telefono]["menu_serv"] = "categorias"
                    return responder(MESSAGES["individual_categories"])
                else:
                    return responder(MESSAGES["invalid_option"])

            elif sesiones[telefono]["submenu"] in ["inmediato", "futuro"]:
                letra = mensaje.strip().lower()
                if letra in selecciones_letras:
                    clave = selecciones_letras[letra]
                    respuesta_plan = responder_plan(clave)
                    sesiones[telefono]["descripcion_resumen"] = f"Información de plan: {clave}"
                    sesiones[telefono]["estado_contacto"] = "preguntar_contacto_planes"
                    return responder(respuesta_plan + "\n\n" + MESSAGES["ask_contact_interest"])
                else:
                    return responder(MESSAGES["letter_not_recognized"])

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
                elif sesiones[telefono]["menu_serv"] in ["tramites", "traslados", "equipamiento", "procedimientos"]:
                    if letra in selecciones_letras:
                        clave = selecciones_letras[letra]
                        respuesta_plan = responder_plan(clave)
                        sesiones[telefono]["descripcion_resumen"] = f"Información de servicio individual: {clave}"
                        sesiones[telefono]["estado_contacto"] = "preguntar_contacto_planes"
                        return responder(respuesta_plan + "\n\n" + MESSAGES["ask_contact_interest"])
                    else:
                        return responder(MESSAGES["letter_not_recognized"])

            # Lógica para preguntar contacto después de dar información de plan/servicio
            if sesiones[telefono].get("estado_contacto") == "preguntar_contacto_planes":
                numero_asesor = obtener_numero_asesor()
                sesiones[telefono]["numero_asesor_asignado"] = numero_asesor
                if contiene_flexible(["sí", "si", "si me gustaría", "si quiero"], mensaje):
                    sesiones[telefono]["estado_contacto"] = "esperando_confirmacion_llamada"
                    enviar_resumen_asesor(
                        telefono,
                        numero_asesor,
                        "Planes y Servicios",
                        sesiones[telefono].get("descripcion_resumen", "Información de plan/servicio."),
                        "El cliente realizará la llamada."
                    )
                    return responder(MESSAGES["direct_contact_info"].format(numero_asesor=numero_asesor))
                elif contiene_flexible(["no", "no gracias", "no por ahora"], mensaje):
                    sesiones[telefono] = {} # Reinicia la sesión
                    return responder(MESSAGES["passive_contact_info"].format(numero_asesor=numero_asesor))
                # AÑADIDO: Manejo explícito de "llámame" en este punto
                elif contiene_flexible(["llámame", "quiero que me llamen", "me pueden marcar"], mensaje):
                    enviar_resumen_asesor(
                        telefono,
                        numero_asesor,
                        "Planes y Servicios",
                        sesiones[telefono].get("descripcion_resumen", "Información de plan/servicio."),
                        "El cliente solicitó ser llamado."
                    )
                    sesiones[telefono] = {} # Reinicia la sesión
                    return responder(MESSAGES["call_requested_info"].format(numero_asesor=numero_asesor))
                else:
                    return responder(MESSAGES["invalid_option"])
            elif sesiones[telefono].get("estado_contacto") == "esperando_confirmacion_llamada":
                # Si el cliente responde después de recibir el número, se asume que es una confirmación o una solicitud de llamada
                # AÑADIDO: Manejo explícito de "llámame" si ya se dio el número
                if contiene_flexible(["llámame", "quiero que me llamen", "me pueden marcar"], mensaje):
                    numero_asesor = sesiones[telefono]["numero_asesor_asignado"]
                    enviar_resumen_asesor(
                        telefono,
                        numero_asesor,
                        "Planes y Servicios",
                        sesiones[telefono].get("descripcion_resumen", "Información de plan/servicio."),
                        "El cliente solicitó ser llamado."
                    )
                    sesiones[telefono] = {} # Reinicia la sesión
                    return responder(MESSAGES["call_requested_info"].format(numero_asesor=numero_asesor))
                else:
                    sesiones[telefono] = {} # Reinicia la sesión
                    return responder(MESSAGES["thanks_confirmation"])


        # ----------------------------- #
        # RESPUESTA GENERAL SI NADA COINCIDE
        # ----------------------------- #
        return responder(MESSAGES["unrecognized_message"])

    except Exception as e:
        logging.error(f"Error inesperado en webhook: {e}", exc_info=True)
        return responder(MESSAGES["general_error"])

# ----------------------------- #
# INICIO DEL SERVIDOR
# ----------------------------- #
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
