
planes_info = {
    "crédito de necesidad inmediata": (
        "💳 *Crédito de Necesidad Inmediata*"

"
        "Permite hacer uso inmediato del servicio funerario requerido.
"
        "✅ Requisitos: Comprobante de domicilio y credencial de elector con el mismo domicilio.
"
        "💰 Aportaciones:
- 50% del valor del servicio como pago inicial.
- 50% restante en 20 días.
"
        "- $60.00 pesos diarios por cada $1,000.00
"
        "🛡️ Garantías:
- Empresa 100% mexicana con 28 años.
- Autorizado por PROFECO.
- Servicio 24/7 en todo México."
    ),
    "servicio paquete fetal cremación": (
        "⚰️ *Paquete Fetal Cremación*

"
        "Incluye:
- Carroza para recolección del cuerpo desde hospital.
- Ataúd fetal especial.
"
        "- Traslado a crematorio autorizado.
- Servicio de cremación.
- Urna básica para entrega de cenizas.
"
        "💰 Costo: $5,800.00 + IVA
🛡️ Garantías: Empresa con 28 años, autorizado por PROFECO, cobertura nacional 24/7."
    ),
    "servicio paquete sencillo sepultura": (
        "⚰️ *Paquete Sencillo Sepultura*

"
        "Incluye:
- Carroza desde hospital o domicilio.
- Ataúd de madera tapizado.
"
        "- Vestido con ropa proporcionada por la familia.
- Equipo de velación en domicilio (1 cristo, 4 candeleros, pedestal).
"
        "- Trámite ante registro civil para boleta de inhumación.
- Carroza al panteón.
"
        "💰 Costo: $7,900.00 + IVA"
    ),
    "servicio paquete básico sepultura": (
        "⚰️ *Paquete Básico Sepultura*

"
        "Incluye lo mismo que el paquete sencillo pero con ataúd metálico, trámites y asesoría legal.
"
        "💰 Costo: $10,900.00 + IVA"
    ),
    "servicio cremación directa": (
        "🔥 *Cremación Directa*

"
        "Traslado del cuerpo directo a crematorio autorizado.
"
        "Incluye urna básica.
"
        "💰 Costo: $7,000.00 + IVA"
    ),
    "servicio paquete de cremación": (
        "🔥 *Paquete de Cremación Completa*

"
        "Incluye traslado, ataúd, sala de velación 4 horas y cremación posterior.
"
        "💰 Costo: $11,900.00 + IVA"
    ),
    "servicio paquete legal": (
        "📑 *Paquete Legal*

"
        "Asesoría para trámites legales ante MP o fallecimientos por causas violentas.
"
        "Incluye gestoría legal.
"
        "💰 Costo: $6,500.00 + IVA"
    ),
    "servicio de refrigeración y conservación": (
        "❄️ *Refrigeración y Conservación*

"
        "Instalaciones autorizadas por Secretaría de Salud.
"
        "Preservación del cuerpo mientras se organiza el servicio funerario."
    ),
    "red biker": (
        "🏍️ *Red Biker*

"
        "Convenio especial para motociclistas.
"
        "Incluye cobertura a nivel nacional y traslados preferenciales."
    ),
    "red plus": (
        "🔵 *Red Plus*

"
        "Plan exclusivo con beneficios extendidos en cobertura, plazos y descuentos."
    ),
    "red consorcio": (
        "🏢 *Red Consorcio*

"
        "Plan empresarial o familiar con múltiples beneficiarios.
"
        "Asistencia completa 24/7."
    ),
    "red adulto mayor": (
        "👵 *Red Adulto Mayor*

"
        "Plan diseñado para personas mayores con cobertura completa y beneficios adicionales.
"
        "💰 Costo: desde $8,000.00 + IVA"
    ),
    "cremación amigo fiel": (
        "🐾 *Cremación Amigo Fiel*

"
        "Servicio de cremación individual para mascotas.
"
        "Incluye urna básica y certificado de cremación."
    ),
    "servicio paquete de cremación de restos áridos": (
        "🧱 *Cremación de Restos Áridos*

"
        "Servicio para restos óseos provenientes de exhumaciones.
"
        "Incluye urna y trámite ante panteón."
    ),
    "preventa de nichos a temporalidad": (
        "📦 *Preventa de Nichos a Temporalidad*

"
        "Adquiere un espacio a futuro a precio preferencial.
"
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
