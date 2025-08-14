# -*- coding: utf-8 -*-
from flask import Flask, request
import sys
import io
import requests
import os
import threading
import logging
import json  # Importar la librería json
from twilio.twiml.messaging_response import MessagingResponse
from difflib import SequenceMatcher  # para comparar palabras similares
from datetime import datetime  # Importar datetime para fecha y hora

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# --- Variables de Entorno y Constantes ---
# Asegúrate de que estas variables de entorno estén configuradas en tu despliegue.
# Por ejemplo, en Render, Heroku, o tu servidor.
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_MESSAGING_URL = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
TWILIO_AUTH = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Números de reenvío principales y secundarios (usados para asignación de turno)
# Asegúrate de que estos números estén en formato E.164 y puedan recibir WhatsApp.
NUMERO_ASESOR_2 = os.getenv("NUMERO_ASESOR_2", "+525523604519")
NUMERO_ASESOR_3 = os.getenv("NUMERO_ASESOR_3", "+525511230871")

# Mapeo de números de asesor a nombres (para las plantillas)
ASESOR_NAMES = {
    NUMERO_ASESOR_2: "Asesor Juan",
    NUMERO_ASESOR_3: "Asesor María"
}

# Variable para gestionar el turno (simple alternancia para el ejemplo)
turno_actual = 2  # Inicia con el turno 2

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
        "Para brindarle la mejor atención, por favor, envíenos los siguientes datos *uno por uno*:\n"
        "1. Nombre completo del fallecido\n"
        "2. Suceso o causa del fallecimiento\n"
        "3. Ubicación actual del cuerpo\n"
        "4. ¿Ya cuenta con su certificado de defunción? (Sí/No)\n"
        "5. Dos números de contacto\n"
        "6. Nombre de la persona que nos está contactando\n\n"
        "📌 Si fue un error, escribe la palabra *menú* para regresar al inicio."
    ),
    "emergency_ask_name": "Por favor, envíe el *Nombre completo del fallecido*.",
    "emergency_ask_cause": "Ahora, envíe el *Suceso o causa del fallecimiento*.",
    "emergency_ask_location": "Por favor, indique la *Ubicación actual del cuerpo*.",
    "emergency_ask_certificate": "¿Ya cuenta con su *certificado de defunción*? (Responda 'Sí' o 'No')",
    "emergency_ask_contact_numbers": "Ahora, envíe *Dos números de contacto*.",
    "emergency_ask_contact_person": "Finalmente, envíe el *Nombre de la persona que nos está contactando*.",
    "emergency_certificate_invalid": "Respuesta no válida. Por favor, responda 'Sí' o 'No' sobre el certificado de defunción.",

    "emergency_received": "✅ Gracias. Hemos recibido tu emergencia. Un asesor te contactará de inmediato.\n\n📌 Si deseas más información, escribe la palabra *menú* para regresar al inicio.",

    "location_list": """📍 *Ubicaciones disponibles:*
1. Av. Tláhuac No. 5502, Col. El Rosario, CDMX
2. Av. Zacatlán No. 60, Col. San Lorenzo Tezonco, CDMX
3. Av. Zacatlán No. 10, Col. San Lorenzo Tezonco, CDMX

¿Deseas agendar una cita en alguna de nuestras sucursales? (Sí / No)

📌 Puedes escribir la palabra *menú* para regresar al inicio.""",

    "location_ask_appointment": "No entendí tu respuesta. ¿Te gustaría agendar una cita? Responde 'sí' o 'no'.\n\n📌 Escribe la palabra *menú* para regresar al inicio.",
    "appointment_ask_name": "Perfecto. Por favor, indícanos tu *nombre completo*.",
    "appointment_ask_preferred_time": "Gracias, {nombre_cliente}. Ahora, por favor, indícanos tu *horario preferido* para la cita (ej. 'Mañana a las 10 AM' o 'Jueves 15:00').",
    "appointment_ask_location": "Por favor, indícanos la *ubicación elegida* para la cita.",

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
    "ayúdenos", "urgente apoyo", "urgente funeral", "ayuda urgente",
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
    "necesito un servicio funerario urgente", "necesito apoyo urgente", "urgencia funeraria", "urgente fallecimiento", "atención por fallecimiento"
]
claves_ubicacion = ["ubicación", "ubicaciones", "sucursal", "sucursales", "dirección", "direccion"]
claves_cierre = ["gracias", "ok", "vale", "de acuerdo", "listo", "perfecto", "entendido", "muy bien"]
claves_asesor = ["asesor", "especialista", "ayuda", "humano", "agente", "llamar", "marcar", "llamame", "quiero que me llamen", "me pueden marcar"]

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
        logging.info(f"Enviando advertencia de inactividad a {numero}")
        try:
            requests.post(TWILIO_MESSAGING_URL, auth=TWILIO_AUTH, data={
                "To": numero,
                "From": "whatsapp:+525510704725", # Asegúrate que este es tu número de WhatsApp Business de Twilio
                "Body": MESSAGES["inactivity_warning"]
            })
            logging.info(f"Advertencia de inactividad enviada a {numero}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error al enviar advertencia de inactividad a {numero}: {e}")
        finally:
            temporizadores.pop(numero, None)
            sesiones.pop(numero, None)  # Limpiar sesión al expirar inactividad

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
    logging.info(f"Asignando asesor: {numero} (próximo turno: {turno_actual})")
    return numero


# --- FUNCIONES PARA ENVIAR PLANTILLAS ---
# Asegúrate de que los ContentSid (HX...) sean los correctos para tus plantillas aprobadas en Twilio.
# Asegúrate de que el número 'From' sea tu número de WhatsApp Business de Twilio.

def enviar_plantilla_emergencia_cliente(telefono_asesor, nombre_asesor, nombre_fallecido, telefono_contacto, causa_fallecimiento, ubicacion_cuerpo, certificado_defuncion):
    """
    Envía la plantilla 'emergencia_cliente_cf' al número del asesor usando ContentSid.
    """
    to_number = f"whatsapp:{telefono_asesor}"
    from_number = "whatsapp:+525510704725"  # Tu número de Twilio/WhatsApp Business

    logging.info(f"Intentando enviar plantilla de emergencia a {to_number} desde {from_number}")
    try:
        response = requests.post(
            TWILIO_MESSAGING_URL,
            auth=TWILIO_AUTH,
            data={
                "To": to_number,
                "From": from_number,
                "ContentSid": "HX45cdcc80ab9e7a45a105f0ee7c1cb19f",  # ID real de la plantilla
                "ContentVariables": json.dumps({
                    "1": nombre_asesor,
                    "2": nombre_fallecido,
                    "3": telefono_contacto,
                    "4": causa_fallecimiento,
                    "5": ubicacion_cuerpo,
                    "6": certificado_defuncion
                })
            }
        )
        response.raise_for_status() # Lanza una excepción para códigos de estado HTTP 4xx/5xx
        logging.info(f"✅ Plantilla 'emergencia_cliente_cf' enviada correctamente a {telefono_asesor}. SID: {response.json().get('sid')}")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Error al enviar plantilla 'emergencia_cliente_cf' a {telefono_asesor}: {type(e).__name__} - {e}")
        if hasattr(e, 'response') and e.response is not None:
            logging.error(f"Respuesta de Twilio (emergencia): {e.response.text}")
        return False
    except Exception as e:
        logging.error(f"❌ Error inesperado al enviar plantilla de emergencia: {type(e).__name__} - {e}")
        return False


def enviar_plantilla_ubicacion_cliente(telefono_asesor, nombre_asesor, nombre_cliente, telefono_contacto, ubicacion_elegida, fecha_hora_cita):
    """
    Envía la plantilla 'ubicacion_cliente_cf' al número del asesor usando ContentSid.
    """
    to_number = f"whatsapp:{telefono_asesor}"
    from_number = "whatsapp:+525510704725"

    logging.info(f"Intentando enviar plantilla de ubicación a {to_number} desde {from_number}")
    try:
        response = requests.post(
            TWILIO_MESSAGING_URL,
            auth=TWILIO_AUTH,
            data={
                "To": to_number,
                "From": from_number,
                "ContentSid": "HXe7d43debe52a0a0e7b4dd19415a5465",  # ID real de la plantilla
                "ContentVariables": json.dumps({
                    "1": nombre_asesor,
                    "2": nombre_cliente,
                    "3": telefono_contacto,
                    "4": ubicacion_elegida,
                    "5": fecha_hora_cita
                })
            }
        )
        response.raise_for_status()
        logging.info(f"✅ Plantilla 'ubicacion_cliente_cf' enviada correctamente a {telefono_asesor}. SID: {response.json().get('sid')}")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Error al enviar plantilla 'ubicacion_cliente_cf' a {telefono_asesor}: {type(e).__name__} - {e}")
        if hasattr(e, 'response') and e.response is not None:
            logging.error(f"Respuesta de Twilio (ubicación): {e.response.text}")
        return False
    except Exception as e:
        logging.error(f"❌ Error inesperado al enviar plantilla de ubicación: {type(e).__name__} - {e}")
        return False


def enviar_plantilla_resumen_general(telefono_asesor, nombre_asesor, nombre_cliente, telefono_cliente, interes_cliente):
    """
    Envía la plantilla 'resumen_general_cf' al número del asesor usando ContentSid.
    """
    to_number = f"whatsapp:{telefono_asesor}"
    from_number = "whatsapp:+525510704725"

    logging.info(f"Intentando enviar plantilla de resumen general a {to_number} desde {from_number}")
    try:
        response = requests.post(
            TWILIO_MESSAGING_URL,
            auth=TWILIO_AUTH,
            data={
                "To": to_number,
                "From": from_number,
                "ContentSid": "HXc050def3724ea3bf540353c5f28886a5",  # ID real de la plantilla
                "ContentVariables": json.dumps({
                    "1": nombre_asesor,
                    "2": nombre_cliente,
                    "3": telefono_cliente,
                    "4": interes_cliente
                })
            }
        )
        response.raise_for_status()
        logging.info(f"✅ Plantilla 'resumen_general_cf' enviada correctamente a {telefono_asesor}. SID: {response.json().get('sid')}")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Error al enviar plantilla 'resumen_general_cf' a {telefono_asesor}: {type(e).__name__} - {e}")
        if hasattr(e, 'response') and e.response is not None:
            logging.error(f"Respuesta de Twilio (resumen general): {e.response.text}")
        return False
    except Exception as e:
        logging.error(f"❌ Error inesperado al enviar plantilla de resumen general: {type(e).__name__} - {e}")
        return False


def enviar_resumen_asesor(telefono_cliente, numero_asesor_destino, tipo_origen, descripcion, nota=""):
    """
    Genera y envía el mensaje resumen al número del asesor usando la plantilla general HSM.
    """
    nombre_cliente = sesiones.get(telefono_cliente, {}).get("nombre_cliente", "Desconocido")
    telefono_cliente_limpio = telefono_cliente.replace("whatsapp:", "")

    # Obtener el nombre del asesor del mapeo, si existe
    nombre_asesor_para_plantilla = ASESOR_NAMES.get(numero_asesor_destino, "Asesor de Consorcio Funerario")

    interes_cliente_para_plantilla = f"Origen: {tipo_origen}. Interés: {descripcion}"
    if nota:
        interes_cliente_para_plantilla += f". Nota: {nota}"

    logging.info(f"Preparando resumen para asesor {numero_asesor_destino}: Cliente={nombre_cliente}, Tel={telefono_cliente_limpio}, Interés={interes_cliente_para_plantilla}")
    return enviar_plantilla_resumen_general(
        telefono_asesor=numero_asesor_destino,
        nombre_asesor=nombre_asesor_para_plantilla,
        nombre_cliente=nombre_cliente,
        telefono_cliente=telefono_cliente_limpio,
        interes_cliente=interes_cliente_para_plantilla
    )

# --- Función placeholder para responder a planes/servicios específicos ---
def responder_plan(clave_plan):
    """
    Esta función debería contener la lógica para devolver la información
    detallada de cada plan o servicio.
    """
    info_planes = {
        "crédito de necesidad inmediata": "Este plan ofrece un crédito rápido para cubrir gastos funerarios urgentes.",
        "servicio paquete fetal cremación": "Servicio especializado para cremación de restos fetales.",
        "servicio paquete sencillo sepultura": "Servicio de sepultura con paquete sencillo.",
        "servicio paquete básico sepultura": "Servicio de sepultura con paquete básico.",
        "servicio cremación directa": "Servicio de cremación sin velación previa.",
        "servicio paquete de cremación": "Paquete completo de servicio de cremación.",
        "servicio paquete legal": "Servicio que incluye trámites legales funerarios.",
        "servicio de refrigeración y conservación": "Servicio para la conservación del cuerpo.",
        "red biker": "Plan exclusivo para la comunidad motociclista, con beneficios especiales.",
        "red plus": "Plan con cobertura amplia y beneficios adicionales.",
        "red consorcio": "Nuestro plan más completo, con todos los servicios incluidos.",
        "red adulto mayor": "Plan diseñado específicamente para adultos mayores, con facilidades de pago.",
        "preventa de nichos a temporalidad": "Adquiere un nicho con anticipación por un periodo determinado.",
        "cremación amigo fiel": "Servicio de cremación para mascotas, tu compañero fiel.",
        "servicio paquete de cremación de restos áridos": "Servicio de cremación para restos óseos.",
        "traslado": "Servicio de traslado del cuerpo a la ubicación deseada.",
        "carroza local": "Servicio de carroza para traslados dentro de la localidad.",
        "carroza a panteón u horno crematorio": "Servicio de carroza para el traslado final al panteón o crematorio.",
        "carroza legal": "Servicio de carroza que cumple con requisitos legales específicos.",
        "camión local": "Servicio de camión para traslados locales de mayor volumen.",
        "ataúd": "Información sobre nuestra variedad de ataúdes disponibles, desde económicos hasta de lujo.",
        "urna": "Detalles sobre los tipos de urnas disponibles para cenizas.",
        "velación": "Detalles sobre el servicio de velación, incluyendo opciones de capilla y duración.",
        "boletas": "Información sobre la emisión y gestión de boletas.",
        "embalsamado": "Servicio de embalsamado para la conservación del cuerpo.",
        "embalsamado legal": "Servicio de embalsamado que cumple con normativas legales.",
        "embalsamado infecto-contagiosa": "Servicio de embalsamado especializado para casos de enfermedades infecto-contagiosas.",
        "trámites de inhumación": "Asesoría y gestión de trámites para inhumación.",
        "trámites de cremación": "Asesoría y gestión de trámites para cremación.",
        "trámites legales": "Asesoría y gestión de trámites legales relacionados con el fallecimiento.",
        "trámites de traslado": "Gestión de la documentación necesaria para el traslado del cuerpo.",
        "trámites de internación nacional": "Trámites para el traslado del cuerpo dentro del territorio nacional.",
        "trámites de internación internacional": "Trámites para el traslado del cuerpo a nivel internacional.",
        "equipo de velación": "Alquiler de equipo necesario para la velación en domicilio.",
        "cirios": "Suministro de cirios para el servicio funerario.",
        "capilla de gobierno": "Uso de capillas proporcionadas por el gobierno.",
        "capilla particular": "Uso de nuestras capillas privadas para la velación.",
        "traslado carretero por km": "Costo de traslado por carretera calculado por kilómetro.",
        "traslado de terracería por km": "Costo de traslado en caminos de terracería calculado por kilómetro.",
        "camión foráneo por km": "Costo de camión para traslados foráneos calculado por kilómetro."
    }
    return info_planes.get(clave_plan, f"No se encontró información para: {clave_plan}. Por favor, intente con otra opción.")


@app.route("/", methods=["GET"])
def home():
    return "✅ Bot Consorcio Funerario funcionando."

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        mensaje = request.form.get("Body", "").strip()
        telefono = request.form.get("From", "")
        print(f"📥 Nuevo mensaje: {mensaje} de {telefono}")  # Log visual
        logging.info(f"Mensaje recibido: {mensaje} de {telefono}")

        if not mensaje:
            logging.warning(f"Mensaje vacío recibido de {telefono}")
            return responder(MESSAGES["no_text_received"])

        # --- Forzar una sesión válida en el primer mensaje ---
        if telefono not in sesiones or not isinstance(sesiones[telefono], dict):
            sesiones[telefono] = {}
            logging.info(f"📌 Nueva sesión creada/inicializada para: {telefono}")

        # --- Reiniciar temporizador de inactividad por cada mensaje recibido ---
        if telefono in temporizadores:
            temporizadores[telefono].cancel()
            del temporizadores[telefono]
        temporizador = threading.Timer(600, mensaje_inactividad, args=(telefono,))  # 10 minutos
        temporizador.start()
        temporizadores[telefono] = temporizador
        logging.debug(f"Temporizador de inactividad reiniciado para {telefono}")

        # --- Volver al menú principal si se detecta 'menú' con tolerancia (PRIORIDAD ALTA) ---
        if es_mensaje_menu(mensaje):
            sesiones[telefono] = {}  # Reinicia completamente la sesión
            logging.info(f"📌 Sesión reiniciada por 'menú' para: {telefono}")
            return responder(MESSAGES["welcome"])

        # --- Regresar a submenús si se detecta 'regresar' ---
        if es_mensaje_regresar(mensaje):
            current_session = sesiones.get(telefono, {})
            current_menu = current_session.get("menu")
            current_submenu = current_session.get("submenu")
            current_menu_serv = current_session.get("menu_serv")
            current_emergency_step = current_session.get("emergency_step")
            current_appointment_step = current_session.get("appointment_step")

            logging.info(f"Usuario {telefono} solicitó 'regresar'. Estado actual: menu={current_menu}, submenu={current_submenu}, menu_serv={current_menu_serv}, emergency_step={current_emergency_step}, appointment_step={current_appointment_step}")

            if current_emergency_step: # Si está en un paso de emergencia, regresa al inicio de emergencia
                sesiones[telefono] = {"menu": "emergencia", "nombre_cliente": "Cliente de Emergencia"}
                logging.info(f"Regresando a emergency_prompt para {telefono}")
                return responder(MESSAGES["emergency_prompt"])
            elif current_appointment_step: # Si está en un paso de cita, regresa al inicio de ubicación
                sesiones[telefono] = {"menu": "ubicacion", "nombre_cliente": "Cliente de Ubicación"}
                logging.info(f"Regresando a location_list para {telefono}")
                return responder(MESSAGES["location_list"])
            elif current_menu == "planes":
                if current_menu_serv and current_menu_serv != "categorias":
                    sesiones[telefono]["menu_serv"] = "categorias"
                    logging.info(f"Regresando a individual_categories para {telefono}")
                    return responder(MESSAGES["individual_categories"])
                elif current_submenu:
                    del sesiones[telefono]["submenu"]
                    if "menu_serv" in sesiones[telefono]:
                        del sesiones[telefono]["menu_serv"]
                    logging.info(f"Regresando a plans_menu para {telefono}")
                    return responder(MESSAGES["plans_menu"])
                else:
                    logging.info(f"No hay menú anterior para regresar para {telefono} en planes.")
                    return responder(MESSAGES["no_previous_menu"])
            elif current_menu == "ubicacion" or current_menu == "cita":
                if current_menu == "cita":
                    sesiones[telefono]["menu"] = "ubicacion"
                    logging.info(f"Regresando a location_list desde cita para {telefono}")
                    return responder(MESSAGES["location_list"])
                else:
                    logging.info(f"No hay menú anterior para regresar para {telefono} en ubicación/cita.")
                    return responder(MESSAGES["no_previous_menu"])
            else:
                logging.info(f"No hay menú anterior para regresar para {telefono}.")
                return responder(MESSAGES["no_previous_menu"])

        # --- Manejar la palabra clave 'asesor' (prioridad alta) ---
        if contiene_flexible(claves_asesor, mensaje):
            numero_asesor = obtener_numero_asesor()
            sesiones[telefono] = {}  # Limpiar sesión para iniciar un nuevo flujo de contacto directo
            logging.info(f"📌 Sesión reiniciada por 'asesor' para: {telefono}. Ofreciendo contacto directo.")
            return responder(MESSAGES["direct_contact_after_rescue"].format(numero_asesor=numero_asesor))

        # --- Confirmaciones como "gracias", "ok", etc. ---
        if contiene_flexible(claves_cierre, mensaje):
            sesiones[telefono] = {}  # Reinicia la sesión después de una confirmación de cierre
            logging.info(f"📌 Sesión reiniciada por 'cierre' para: {telefono}")
            return responder(MESSAGES["thanks_confirmation"])

        # ----------------------------- #
        # FLUJO: BIENVENIDA Y DETECCIÓN INICIAL
        # ----------------------------- #
        if not sesiones.get(telefono) or sesiones[telefono].get("menu") is None:
            logging.info(f"Detectando intención inicial para {telefono} con mensaje: '{mensaje}'")
            if contiene_flexible(claves_emergencia, mensaje):
                sesiones[telefono] = {
                    "menu": "emergencia",
                    "nombre_cliente": "Cliente de Emergencia",
                    "emergency_step": 1,
                    "emergency_data": {}
                }
                logging.info(f"📌 Nueva sesión: Emergencia para {telefono}")
                return responder(MESSAGES["emergency_prompt"])

            elif contiene_flexible(claves_ubicacion, mensaje):
                sesiones[telefono] = {"menu": "ubicacion", "nombre_cliente": "Cliente de Ubicación"}
                logging.info(f"📌 Nueva sesión: Ubicación para {telefono}")
                return responder(MESSAGES["location_list"])

            elif contiene_flexible(claves_planes, mensaje):
                sesiones[telefono] = {"menu": "planes", "nombre_cliente": "Cliente de Planes"}
                logging.info(f"📌 Nueva sesión: Planes para {telefono}")
                return responder(MESSAGES["plans_menu"])
            else:
                logging.info(f"Mensaje inicial no reconocido para {telefono}. Enviando bienvenida.")
                sesiones[telefono] = {"menu": "inicio_fallback", "nombre_cliente": "Cliente nuevo"}
                return responder(MESSAGES["welcome"])

        # ----------------------------- #
        # FLUJO: EMERGENCIA (GUIADO PASO A PASO)
        # ----------------------------- #
        if sesiones[telefono].get("menu") == "emergencia":
            emergency_step = sesiones[telefono].get("emergency_step", 0)
            emergency_data = sesiones[telefono].get("emergency_data", {})
            numero_asesor_asignado = sesiones[telefono].get("numero_asesor_asignado", obtener_numero_asesor())
            sesiones[telefono]["numero_asesor_asignado"] = numero_asesor_asignado

            logging.info(f"Flujo de emergencia para {telefono}. Paso: {emergency_step}")

            if emergency_step == 1:
                emergency_data["nombre_fallecido"] = mensaje
                sesiones[telefono]["emergency_step"] = 2
                sesiones[telefono]["emergency_data"] = emergency_data
                return responder(MESSAGES["emergency_ask_cause"])
            elif emergency_step == 2:
                emergency_data["causa_fallecimiento"] = mensaje
                sesiones[telefono]["emergency_step"] = 3
                sesiones[telefono]["emergency_data"] = emergency_data
                return responder(MESSAGES["emergency_ask_location"])
            elif emergency_step == 3:
                emergency_data["ubicacion_cuerpo"] = mensaje
                sesiones[telefono]["emergency_step"] = 4
                sesiones[telefono]["emergency_data"] = emergency_data
                return responder(MESSAGES["emergency_ask_certificate"])
            elif emergency_step == 4:
                if mensaje.lower() in ["sí", "si"]:
                    emergency_data["certificado_defuncion"] = "Sí"
                elif mensaje.lower() in ["no"]:
                    emergency_data["certificado_defuncion"] = "No"
                else:
                    logging.warning(f"Respuesta inválida para certificado de defunción de {telefono}: '{mensaje}'")
                    return responder(MESSAGES["emergency_certificate_invalid"])
                sesiones[telefono]["emergency_step"] = 5
                sesiones[telefono]["emergency_data"] = emergency_data
                return responder(MESSAGES["emergency_ask_contact_numbers"])
            elif emergency_step == 5:
                emergency_data["numeros_contacto"] = mensaje
                sesiones[telefono]["emergency_step"] = 6
                sesiones[telefono]["emergency_data"] = emergency_data
                return responder(MESSAGES["emergency_ask_contact_person"])
            elif emergency_step == 6:
                emergency_data["nombre_contactante"] = mensaje
                sesiones[telefono]["emergency_step"] = 7 # Finaliza la captura de datos

                logging.info(f"Datos de emergencia completos para {telefono}. Enviando plantilla a asesor {numero_asesor_asignado}.")
                enviar_plantilla_emergencia_cliente(
                    telefono_asesor=numero_asesor_asignado,
                    nombre_asesor=ASESOR_NAMES.get(numero_asesor_asignado, "Asesor"),
                    nombre_fallecido=emergency_data.get("nombre_fallecido", "N/A"),
                    telefono_contacto=emergency_data.get("numeros_contacto", telefono.replace("whatsapp:", "")),
                    causa_fallecimiento=emergency_data.get("causa_fallecimiento", "N/A"),
                    ubicacion_cuerpo=emergency_data.get("ubicacion_cuerpo", "N/A"),
                    certificado_defuncion=emergency_data.get("certificado_defuncion", "N/A")
                )
                sesiones[telefono]["estado_contacto"] = "ofreciendo_contacto_emergencia"
                return responder(MESSAGES["emergency_contact_direct"].format(numero_asesor=numero_asesor_asignado))
            
            elif sesiones[telefono].get("estado_contacto") == "ofreciendo_contacto_emergencia":
                logging.info(f"Usuario {telefono} responde a oferta de contacto de emergencia: '{mensaje}'")
                if contiene_flexible(["si", "sí", "llámame", "quiero que me llamen", "me pueden marcar"], mensaje):
                    logging.info(f"Usuario {telefono} solicitó ser llamado para emergencia.")
                    enviar_resumen_asesor(
                        telefono,
                        numero_asesor_asignado,
                        "Emergencias",
                        "El cliente solicitó ser llamado.",
                        f"Datos previos: {json.dumps(emergency_data, ensure_ascii=False)}" # Incluir datos capturados
                    )
                    sesiones[telefono] = {}
                    return responder(MESSAGES["call_requested_info"].format(numero_asesor=numero_asesor_asignado))
                else:
                    logging.info(f"Usuario {telefono} no solicitó llamada para emergencia. Finalizando flujo.")
                    sesiones[telefono] = {}
                    return responder(MESSAGES["thanks_confirmation"])

        # ----------------------------- #
        # FLUJO: UBICACIÓN (GUIADO PASO A PASO PARA CITA)
        # ----------------------------- #
        if sesiones[telefono].get("menu") == "ubicacion":
            appointment_step = sesiones[telefono].get("appointment_step", 0)
            appointment_data = sesiones[telefono].get("appointment_data", {})
            numero_asesor_asignado = sesiones[telefono].get("numero_asesor_asignado", obtener_numero_asesor())
            sesiones[telefono]["numero_asesor_asignado"] = numero_asesor_asignado

            logging.info(f"Flujo de ubicación para {telefono}. Paso: {appointment_step}")

            if "estado_cita" not in sesiones[telefono]:
                logging.info(f"Usuario {telefono} responde a pregunta de cita: '{mensaje}'")
                if mensaje.lower() in ["sí", "si", "si me gustaría", "si quiero"]:
                    sesiones[telefono]["estado_cita"] = "solicitando_datos_cita"
                    sesiones[telefono]["appointment_step"] = 1
                    sesiones[telefono]["appointment_data"] = {}
                    return responder(MESSAGES["appointment_ask_name"])
                elif mensaje.lower() in ["no", "no gracias", "no por ahora"]:
                    logging.info(f"Usuario {telefono} no desea agendar cita. Ofreciendo contacto pasivo.")
                    sesiones[telefono] = {}
                    return responder(MESSAGES["passive_contact_info"].format(numero_asesor=numero_asesor_asignado))
                else:
                    logging.warning(f"Respuesta inválida para agendar cita de {telefono}: '{mensaje}'")
                    return responder(MESSAGES["location_ask_appointment"])
            
            elif appointment_step == 1:
                appointment_data["nombre_cliente_cita"] = mensaje
                sesiones[telefono]["nombre_cliente"] = mensaje
                sesiones[telefono]["appointment_step"] = 2
                sesiones[telefono]["appointment_data"] = appointment_data
                return responder(MESSAGES["appointment_ask_preferred_time"].format(nombre_cliente=mensaje))
            
            elif appointment_step == 2:
                appointment_data["horario_preferido"] = mensaje
                sesiones[telefono]["appointment_step"] = 3
                sesiones[telefono]["appointment_data"] = appointment_data
                return responder(MESSAGES["appointment_ask_location"])
            
            elif appointment_step == 3:
                appointment_data["ubicacion_elegida"] = mensaje
                sesiones[telefono]["appointment_step"] = 4

                logging.info(f"Datos de cita completos para {telefono}. Enviando plantilla a asesor {numero_asesor_asignado}.")
                enviar_plantilla_ubicacion_cliente(
                    telefono_asesor=numero_asesor_asignado,
                    nombre_asesor=ASESOR_NAMES.get(numero_asesor_asignado, "Asesor"),
                    nombre_cliente=appointment_data.get("nombre_cliente_cita", "N/A"),
                    telefono_contacto=telefono.replace("whatsapp:", ""),
                    ubicacion_elegida=appointment_data.get("ubicacion_elegida", "N/A"),
                    fecha_hora_cita=appointment_data.get("horario_preferido", "N/A")
                )
                del sesiones[telefono]["appointment_data"]
                del sesiones[telefono]["appointment_step"]
                sesiones[telefono]["estado_contacto"] = "preguntar_contacto_ubicacion"
                return responder(MESSAGES["appointment_received"] + "\n\n" + MESSAGES["ask_contact_interest"])

            elif sesiones[telefono].get("estado_contacto") == "preguntar_contacto_ubicacion":
                logging.info(f"Usuario {telefono} responde a oferta de contacto de ubicación: '{mensaje}'")
                if contiene_flexible(["sí", "si", "si me gustaría", "si quiero"], mensaje):
                    sesiones[telefono]["estado_contacto"] = "esperando_confirmacion_llamada"
                    logging.info(f"Usuario {telefono} desea contactar por ubicación. Enviando resumen.")
                    enviar_resumen_asesor(
                        telefono,
                        numero_asesor_asignado,
                        "Ubicaciones",
                        f"Cita agendada: {sesiones[telefono].get('nombre_cliente', 'N/A')} - {appointment_data.get('horario_preferido', 'N/A')}",
                        "El cliente realizará la llamada."
                    )
                    return responder(MESSAGES["direct_contact_info"].format(numero_asesor=numero_asesor_asignado))
                elif contiene_flexible(["no", "no gracias", "no por ahora"], mensaje):
                    logging.info(f"Usuario {telefono} no desea contactar por ubicación. Ofreciendo contacto pasivo.")
                    sesiones[telefono] = {}
                    return responder(MESSAGES["passive_contact_info"].format(numero_asesor=numero_asesor_asignado))
                elif contiene_flexible(["llámame", "quiero que me llamen", "me pueden marcar"], mensaje):
                    logging.info(f"Usuario {telefono} solicitó ser llamado para ubicación.")
                    enviar_resumen_asesor(
                        telefono,
                        numero_asesor_asignado,
                        "Ubicaciones",
                        f"Cita agendada: {sesiones[telefono].get('nombre_cliente', 'N/A')} - {appointment_data.get('horario_preferido', 'N/A')}",
                        "El cliente solicitó ser llamado."
                    )
                    sesiones[telefono] = {}
                    return responder(MESSAGES["call_requested_info"].format(numero_asesor=numero_asesor_asignado))
                else:
                    logging.warning(f"Respuesta inválida para contacto de ubicación de {telefono}: '{mensaje}'")
                    return responder(MESSAGES["invalid_option"])
            elif sesiones[telefono].get("estado_contacto") == "esperando_confirmacion_llamada":
                logging.info(f"Usuario {telefono} responde a confirmación de llamada de ubicación: '{mensaje}'")
                if contiene_flexible(["llámame", "quiero que me llamen", "me pueden marcar"], mensaje):
                    logging.info(f"Usuario {telefono} re-solicitó ser llamado para ubicación.")
                    enviar_resumen_asesor(
                        telefono,
                        numero_asesor_asignado,
                        "Ubicaciones",
                        f"Cita agendada: {sesiones[telefono].get('nombre_cliente', 'N/A')} - {appointment_data.get('horario_preferido', 'N/A')}",
                        "El cliente solicitó ser llamado."
                    )
                    sesiones[telefono] = {}
                    return responder(MESSAGES["call_requested_info"].format(numero_asesor=numero_asesor_asignado))
                else:
                    logging.info(f"Usuario {telefono} no re-solicitó llamada para ubicación. Finalizando flujo.")
                    sesiones[telefono] = {}
                    return responder(MESSAGES["thanks_confirmation"])

        # ----------------------------- #
        # FLUJO: PLANES
        # ----------------------------- #
        if sesiones[telefono].get("menu") == "planes":
            logging.info(f"Flujo de planes para {telefono}. Submenú: {sesiones[telefono].get('submenu')}, Menu_serv: {sesiones[telefono].get('menu_serv')}")
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
                    logging.warning(f"Opción inválida en menú principal de planes para {telefono}: '{mensaje}'")
                    return responder(MESSAGES["invalid_option"])

            elif sesiones[telefono]["submenu"] in ["inmediato", "futuro"]:
                letra = mensaje.strip().lower()
                if letra in selecciones_letras:
                    clave = selecciones_letras[letra]
                    respuesta_plan = responder_plan(clave)
                    sesiones[telefono]["descripcion_resumen"] = f"Información de plan: {clave}"
                    sesiones[telefono]["estado_contacto"] = "preguntar_contacto_planes"
                    logging.info(f"Usuario {telefono} seleccionó plan/servicio: {clave}. Preguntando por contacto.")
                    return responder(respuesta_plan + "\n\n" + MESSAGES["ask_contact_interest"])
                else:
                    logging.warning(f"Letra no reconocida en submenú de planes para {telefono}: '{mensaje}'")
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
                        logging.warning(f"Categoría no reconocida en servicios individuales para {telefono}: '{mensaje}'")
                        return responder(MESSAGES["category_not_recognized"])
                elif sesiones[telefono]["menu_serv"] in ["tramites", "traslados", "equipamiento", "procedimientos"]:
                    if letra in selecciones_letras:
                        clave = selecciones_letras[letra]
                        respuesta_plan = responder_plan(clave)
                        sesiones[telefono]["descripcion_resumen"] = f"Información de servicio individual: {clave}"
                        sesiones[telefono]["estado_contacto"] = "preguntar_contacto_planes"
                        logging.info(f"Usuario {telefono} seleccionó servicio individual: {clave}. Preguntando por contacto.")
                        return responder(respuesta_plan + "\n\n" + MESSAGES["ask_contact_interest"])
                    else:
                        logging.warning(f"Letra no reconocida en submenú de servicios individuales para {telefono}: '{mensaje}'")
                        return responder(MESSAGES["letter_not_recognized"])

            # Lógica para preguntar contacto después de dar información de plan/servicio
            if sesiones[telefono].get("estado_contacto") == "preguntar_contacto_planes":
                numero_asesor = obtener_numero_asesor()
                sesiones[telefono]["numero_asesor_asignado"] = numero_asesor
                logging.info(f"Usuario {telefono} responde a oferta de contacto de planes: '{mensaje}'")
                if contiene_flexible(["sí", "si", "si me gustaría", "si quiero"], mensaje):
                    sesiones[telefono]["estado_contacto"] = "esperando_confirmacion_llamada"
                    logging.info(f"Usuario {telefono} desea contactar por planes. Enviando resumen.")
                    enviar_resumen_asesor(
                        telefono,
                        numero_asesor,
                        "Planes y Servicios",
                        sesiones[telefono].get("descripcion_resumen", "Información de plan/servicio."),
                        "El cliente realizará la llamada."
                    )
                    return responder(MESSAGES["direct_contact_info"].format(numero_asesor=numero_asesor))
                elif contiene_flexible(["no", "no gracias", "no por ahora"], mensaje):
                    logging.info(f"Usuario {telefono} no desea contactar por planes. Ofreciendo contacto pasivo.")
                    sesiones[telefono] = {}
                    return responder(MESSAGES["passive_contact_info"].format(numero_asesor=numero_asesor))
                elif contiene_flexible(["llámame", "quiero que me llamen", "me pueden marcar"], mensaje):
                    logging.info(f"Usuario {telefono} solicitó ser llamado para planes.")
                    enviar_resumen_asesor(
                        telefono,
                        numero_asesor,
                        "Planes y Servicios",
                        sesiones[telefono].get("descripcion_resumen", "Información de plan/servicio."),
                        "El cliente solicitó ser llamado."
                    )
                    sesiones[telefono] = {}
                    return responder(MESSAGES["call_requested_info"].format(numero_asesor=numero_asesor))
                else:
                    logging.warning(f"Respuesta inválida para contacto de planes de {telefono}: '{mensaje}'")
                    return responder(MESSAGES["invalid_option"])
            elif sesiones[telefono].get("estado_contacto") == "esperando_confirmacion_llamada":
                logging.info(f"Usuario {telefono} responde a confirmación de llamada de planes: '{mensaje}'")
                if contiene_flexible(["llámame", "quiero que me llamen", "me pueden marcar"], mensaje):
                    logging.info(f"Usuario {telefono} re-solicitó ser llamado para planes.")
                    enviar_resumen_asesor(
                        telefono,
                        numero_asesor,
                        "Planes y Servicios",
                        sesiones[telefono].get("descripcion_resumen", "Información de plan/servicio."),
                        "El cliente solicitó ser llamado."
                    )
                    sesiones[telefono] = {}
                    return responder(MESSAGES["call_requested_info"].format(numero_asesor=numero_asesor))
                else:
                    logging.info(f"Usuario {telefono} no re-solicitó llamada para planes. Finalizando flujo.")
                    sesiones[telefono] = {}
                    return responder(MESSAGES["thanks_confirmation"])

        # ----------------------------- #
        # RESPUESTA GENERAL SI NADA COINCIDE (FALLBACK)
        # ----------------------------- #
        logging.info(f"Mensaje no reconocido en ningún flujo para {telefono}: '{mensaje}'. Enviando mensaje de no reconocimiento.")
        return responder(MESSAGES["unrecognized_message"])

    except Exception as e:
        logging.error(f"Error inesperado en webhook para {telefono}: {type(e).__name__} - {e}", exc_info=True)
        return responder(MESSAGES["general_error"])

# ----------------------------- #
# INICIO DEL SERVIDOR
# ----------------------------- #
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

