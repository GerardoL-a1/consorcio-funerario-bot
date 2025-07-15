from twilio.twiml.messaging_response import MessagingResponse
from difflib import SequenceMatcher

def responder(texto):
    respuesta = MessagingResponse()
    respuesta.message(texto)
    return str(respuesta)

def contiene(lista_palabras, mensaje):
    return any(palabra in mensaje.lower() for palabra in lista_palabras)

def parecido(palabra_objetivo, mensaje, umbral=0.75):
    return SequenceMatcher(None, palabra_objetivo.lower(), mensaje.lower()).ratio() >= umbral
