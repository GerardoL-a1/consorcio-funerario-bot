
from flask import Blueprint, request
from helpers.respuestas import responder, contiene, parecido
from helpers.mensajes import MENSAJE_BIENVENIDA
from helpers.palabras_clave import claves_planes, claves_emergencia, claves_ubicacion, claves_cierre
from services.twilio_api import reenviar_mensaje, mensaje_inactividad
from planes_info import responder_plan

import threading
import logging

webhook_blueprint = Blueprint("webhook", __name__)

sesiones = {}
temporizadores = {}

@webhook_blueprint.route("/webhook", methods=["POST"])
def webhook():
    mensaje = request.form.get("Body", "").strip()
    telefono = request.form.get("From", "")
    logging.info(f"Mensaje recibido: {mensaje} de {telefono}")

    if not mensaje:
        return responder("❗ No recibimos texto. Por favor escribe tu mensaje.")

    if telefono in temporizadores:
        temporizadores[telefono].cancel()
        del temporizadores[telefono]
    temporizador = threading.Timer(600, mensaje_inactividad, args=(telefono,))
    temporizador.start()
    temporizadores[telefono] = temporizador

    if mensaje.lower() in ["menú", "menu", "inicio"]:
        sesiones[telefono] = {}
        return responder(MENSAJE_BIENVENIDA)

    if contiene(claves_cierre, mensaje):
        return responder("👌 Gracias por confirmar. Si necesitas algo más, escribe *menú* para regresar al inicio.")

    if not sesiones.get(telefono):
        if contiene(claves_emergencia, mensaje):
            sesiones[telefono] = {"menu": "emergencia"}
            return responder("🚨 *ATENCIÓN INMEDIATA*\n\nPor favor proporciona los siguientes datos:\n- Nombre del fallecido\n- Suceso o causa\n- Ubicación\n- ¿Certificado de defunción?\n- Dos números de contacto\n- Tu nombre\n\n📌 Escribe *menú* para regresar al inicio.")
        elif contiene(claves_ubicacion, mensaje):
            sesiones[telefono] = {"menu": "ubicacion"}
            return responder("📍 *Ubicaciones disponibles:*\n- Av. Tláhuac No. 5502\n- Av. Zacatlán No. 60\n- Av. Zacatlán No. 10\n\n¿Deseas agendar cita? (Sí / No)")
        elif contiene(claves_planes, mensaje):
            sesiones[telefono] = {"menu": "planes"}
            return responder("🧾 Has seleccionado *servicios funerarios*.\n1. Planes de necesidad inmediata\n2. Planes a futuro\n3. Servicios individuales\n\nEscribe el número deseado.")
        else:
            return responder(MENSAJE_BIENVENIDA)

    if sesiones[telefono].get("menu") == "emergencia":
        alerta = f"📨 *NUEVA EMERGENCIA*\nDe: {telefono}\nMensaje: {mensaje}"
        reenviar_mensaje("+525523604519", alerta)
        reenviar_mensaje("+525523680734", alerta)
        sesiones[telefono] = {}
        return responder("✅ Gracias. Hemos recibido tu emergencia. Un asesor te contactará pronto.")

    if sesiones[telefono].get("menu") == "ubicacion":
        if mensaje.lower() in ["sí", "si"]:
            sesiones[telefono] = {}
            return responder("✅ Por favor indícanos tu nombre y horario preferido para la cita.")
        elif mensaje.lower() == "no":
            sesiones[telefono] = {}
            return responder("✅ Gracias por consultar. Si necesitas algo más, escribe *menú* para regresar al inicio.")
        else:
            return responder("¿Deseas agendar cita? (Sí / No)")

    if sesiones[telefono].get("menu") == "planes":
        if mensaje == "1":
            return responder("⏱️ *Planes Inmediatos:*\nA. Crédito\nB. Paquete Fetal\nC. Paquete Sencillo\n...\nEscribe la letra correspondiente.")
        elif mensaje == "2":
            return responder("🕰️ *Planes a Futuro:*\nI. Red Biker\nJ. Red Plus\nK. Red Consorcio\n...\nEscribe la letra correspondiente.")
        elif mensaje == "3":
            return responder("⚙️ *Servicios Individuales:*\nN. Traslado\nO. Ataúd\nP. Urna\n...\nEscribe la letra correspondiente.")
        elif len(mensaje) <= 3:
            respuesta = responder_plan(mensaje)
            sesiones[telefono] = {}
            return responder(respuesta + "\n\n📌 Escribe *menú* para regresar al inicio.")
        else:
            return responder("❌ Opción no válida. Escribe 1, 2 o 3, o la letra de un servicio.")

    return responder("🤖 No entendimos tu mensaje. Escribe *menú* para comenzar.")
