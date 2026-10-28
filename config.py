"""
Configuración de marca de PASEC.
Edita estos valores con los datos de tu organización.
"""

# Nombre que aparece en el encabezado, la pantalla de login y el título de la pestaña.
NOMBRE_ENTIDAD = "Mi Organización"

# Subtítulo que aparece debajo del nombre en la pantalla de login.
SUBTITULO = "Control de acceso por código QR"

# ---------------------------------------------------------------------------
# Textos fijos del carnet de voluntariado
# ---------------------------------------------------------------------------

# Título del encabezado del carnet (se divide en dos líneas automáticamente).
CARNET_TITULO = "Carnet de voluntariado"

# Texto que aparece bajo el nombre de la persona.
CARNET_ROL = "VOLUNTARIO/A"

# Frase fija al pie del carnet, igual para todas las personas.
CARNET_FRASE_FIJA = (
    "Este carnet acredita la participación de la persona identificada en "
    "actividades de voluntariado autorizadas por la organización."
)

# Sugerencias que aparecen al escribir el tipo de voluntariado (se puede
# escribir cualquier otro texto).
TIPOS_VOLUNTARIADO = [
    "Voluntariado comunitario",
    "Voluntariado profesional",
    "Voluntariado coorporativo",
    "Servicio comunitario",
    "Prácticas pre-profesionales",
    "Vinculación comunitaria",
]
