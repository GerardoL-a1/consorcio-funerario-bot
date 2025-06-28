
planes_info = {
    "crédito de necesidad inmediata": (
        "💳 *Crédito de Necesidad Inmediata*\n"
        "Permite hacer uso inmediato del servicio funerario requerido.\n"
        "✅ Requisitos: Comprobante de domicilio y credencial de elector con el mismo domicilio.\n"
        "💰 Aportaciones:\n"
        "- 50% del valor del servicio como pago inicial.\n"
        "- 50% restante en 20 días.\n"
        "- $60.00 pesos diarios por cada $1,000.00\n"
        "🛡️ Garantías:\n"
        "- Empresa 100% mexicana con 28 años.\n"
        "- Autorizado por PROFECO.\n"
        "- Servicio 24/7 en todo México."
    ),
    "servicio paquete fetal cremación": (
        "⚰️ *Paquete Fetal Cremación*\n"
        "Incluye:\n"
        "- Carroza para recolección del cuerpo desde hospital.\n"
        "- Ataúd fetal especial.\n"
        "- Traslado a crematorio autorizado.\n"
        "- Servicio de cremación.\n"
        "- Urna básica para entrega de cenizas.\n"
        "💰 Costo: $5,800.00 + IVA\n"
        "🛡️ Garantías: Empresa con 28 años, autorizado por PROFECO, cobertura nacional 24/7."
    ),
    "servicio paquete sencillo sepultura": (
        "⚰️ *Paquete Sencillo Sepultura*\n"
        "Incluye:\n"
        "- Carroza desde hospital o domicilio.\n"
        "- Ataúd de madera tapizado.\n"
        "- Vestido con ropa proporcionada por la familia.\n"
        "- Equipo de velación en domicilio (1 cristo, 4 candeleros, pedestal).\n"
        "- Trámite ante registro civil para boleta de inhumación.\n"
        "- Carroza al panteón.\n"
        "💰 Costo: $7,900.00 + IVA"
    ),
    "servicio paquete básico sepultura": (
        "⚰️ *Paquete Básico Sepultura*\n"
        "Incluye lo mismo que el paquete sencillo pero con ataúd metálico, trámites y asesoría legal.\n"
        "💰 Costo: $10,900.00 + IVA"
    ),
    "servicio cremación directa": (
        "🔥 *Cremación Directa*\n"
        "Traslado del cuerpo directo a crematorio autorizado.\n"
        "Incluye urna básica.\n"
        "💰 Costo: $7,000.00 + IVA"
    ),
    "servicio paquete de cremación": (
        "🔥 *Paquete de Cremación Completa*\n"
        "Incluye traslado, ataúd, sala de velación 4 horas y cremación posterior.\n"
        "💰 Costo: $11,900.00 + IVA"
    ),
    "servicio paquete legal": (
        "📑 *Paquete Legal*\n"
        "Asesoría para trámites legales ante MP o fallecimientos por causas violentas.\n"
        "Incluye gestoría legal.\n"
        "💰 Costo: $6,500.00 + IVA"
    ),
    "servicio de refrigeración y conservación": (
        "❄️ *Refrigeración y Conservación*\n"
        "Instalaciones autorizadas por Secretaría de Salud.\n"
        "Preservación del cuerpo mientras se organiza el servicio funerario."
    ),
    "red biker": (
        "🏍️ *Red Biker*\n"
        "Convenio especial para motociclistas.\n"
        "Incluye cobertura a nivel nacional y traslados preferenciales."
    ),
    "red plus": (
        "🔵 *Red Plus*\n"
        "Plan exclusivo con beneficios extendidos en cobertura, plazos y descuentos."
    ),
    "red consorcio": (
        "🏢 *Red Consorcio*\n"
        "Plan empresarial o familiar con múltiples beneficiarios.\n"
        "Asistencia completa 24/7."
    ),
    "red adulto mayor": (
        "👵 *Red Adulto Mayor*\n"
        "Plan diseñado para personas mayores con cobertura completa y beneficios adicionales.\n"
        "💰 Costo: desde $8,000.00 + IVA"
    ),
    "cremación amigo fiel": (
        "🐾 *Cremación Amigo Fiel*\n"
        "Servicio de cremación individual para mascotas.\n"
        "Incluye urna básica y certificado de cremación."
    ),
    "servicio paquete de cremación de restos áridos": (
        "🧱 *Cremación de Restos Áridos*\n"
        "Servicio para restos óseos provenientes de exhumaciones.\n"
        "Incluye urna y trámite ante panteón."
    ),
    "preventa de nichos a temporalidad": (
        "📦 *Preventa de Nichos a Temporalidad*\n"
        "Adquiere un espacio a futuro a precio preferencial.\n"
        "Incluye mantenimiento, uso por 3 años renovables."
    ),
    "traslado": "🚐 *Traslados Individuales* — Local y foráneo. Costo depende del destino.",
    "ataúd": "⚰️ *Ataúdes* — Varios modelos. Pregunta por catálogo.",
    "urna": "⚱️ *Urnas* — Básicas y premium. Consulta disponibilidad.",
    "velación": "🕯️ *Equipo de velación* — Servicio completo en domicilio o funeraria.",
    "boletas": "📝 *Boletas* — Trámite ante registro civil e inhumación."
}

def responder_plan(mensaje):
    for clave, texto in planes_info.items():
        if clave in mensaje:
            return texto
    return "🔍 No encontré información sobre ese plan o servicio. Por favor intenta con otro nombre."
