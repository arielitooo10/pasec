"""
Pruebas del carnet de voluntariado (campos nuevos, edición, fotos, permisos,
migración de una base de datos antigua).

Usa una base de datos y carpetas TEMPORALES: no toca pasec.db ni tus fotos.
Ejecutar: python test_carnet.py
"""
import io
import sqlite3
import tempfile
from datetime import date, timedelta
from pathlib import Path

from PIL import Image
from werkzeug.security import generate_password_hash

import app as pasec
import config
import models

TMP = Path(tempfile.mkdtemp(prefix="pasec_test_"))
models.DB_PATH = TMP / "test.db"
pasec.FOTOS_DIR = TMP / "fotos"
pasec.QR_DIR = TMP / "qrcodes"
pasec.FOTOS_DIR.mkdir()
pasec.QR_DIR.mkdir()


def verificar(condicion, mensaje):
    assert condicion, mensaje
    print(f"  OK: {mensaje}")


def imagen_bytes(formato="JPEG", tam=(900, 1200), con_exif=False, color=(180, 120, 90)):
    buffer = io.BytesIO()
    img = Image.new("RGB", tam, color)
    if con_exif:
        exif = Image.Exif()
        exif[0x010F] = "CamaraDePrueba"      # fabricante
        exif[0x8825] = {1: "S", 2: (0, 12, 0)}  # bloque GPS
        img.save(buffer, formato, exif=exif)
    else:
        img.save(buffer, formato)
    buffer.seek(0)
    return buffer


def formulario(**cambios):
    datos = {
        "nombre": "María Pérez López", "cedula": "1712345678",
        "tipo_voluntariado": "Prácticas pre-profesionales",
        "vigencia_desde": "2026-09-15", "vigencia_hasta": "2027-03-15",
        "contacto_nombre": "Contacto de Prueba", "contacto_telefono": "0990000000",
        "frase_extra": "El tiempo que se disfruta es el verdadero tiempo vivido",
    }
    datos.update(cambios)
    return {k: v for k, v in datos.items() if v is not None}


print("=== 1. Migración: una base de datos ANTIGUA (sin campos de carnet) se actualiza sin perder datos ===")
conn = sqlite3.connect(models.DB_PATH)
conn.executescript("""
    CREATE TABLE usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL, rol TEXT NOT NULL, nombre_completo TEXT NOT NULL);
    CREATE TABLE personas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL,
        cedula TEXT UNIQUE NOT NULL, qr_token TEXT UNIQUE NOT NULL, fecha_registro TEXT NOT NULL,
        activo INTEGER NOT NULL DEFAULT 1);
    CREATE TABLE registros (id INTEGER PRIMARY KEY AUTOINCREMENT, persona_id INTEGER NOT NULL,
        tipo TEXT NOT NULL, timestamp TEXT NOT NULL);
    INSERT INTO personas (nombre, cedula, qr_token, fecha_registro)
        VALUES ('Persona Antigua', '1700000001', 'token-antiguo', '2026-01-01T10:00:00');
""")
conn.commit()
conn.close()
models.init_db()
models.init_db()  # correrlo dos veces no debe fallar
antigua = models.obtener_persona_por_cedula("1700000001")
verificar(antigua["nombre"] == "Persona Antigua" and antigua["qr_token"] == "token-antiguo", "la persona antigua sigue ahí con su mismo QR")
verificar(antigua["tipo_voluntariado"] is None and antigua["foto_zoom"] == 1.0, "las columnas nuevas existen (vacías) para la persona antigua")
verificar(models.estado_credencial(antigua) == "Activo", "sin vigencia, una persona activa se muestra como 'Activo'")

models.crear_usuario("admin", generate_password_hash("admin123"), "admin", "Administrador")
models.crear_usuario("guardia", generate_password_hash("guardia123"), "guardia", "Guardia")
admin = pasec.app.test_client()
guardia = pasec.app.test_client()
admin.post("/login", data={"username": "admin", "password": "admin123"})
guardia.post("/login", data={"username": "guardia", "password": "guardia123"})

print("\n=== 2. Estado del carnet según la vigencia ===")
hoy = date.today()
base = {"activo": 1, "vigencia_desde": None, "vigencia_hasta": None}
verificar(models.estado_credencial({**base, "vigencia_desde": (hoy - timedelta(days=5)).isoformat(),
                                    "vigencia_hasta": (hoy + timedelta(days=5)).isoformat()}) == "Activo", "dentro de la vigencia -> Activo")
verificar(models.estado_credencial({**base, "vigencia_desde": (hoy - timedelta(days=50)).isoformat(),
                                    "vigencia_hasta": (hoy - timedelta(days=1)).isoformat()}) == "Vencido", "vigencia terminada -> Vencido")
verificar(models.estado_credencial({**base, "vigencia_desde": (hoy + timedelta(days=3)).isoformat(),
                                    "vigencia_hasta": (hoy + timedelta(days=30)).isoformat()}) == "Por iniciar", "vigencia futura -> Por iniciar")
verificar(models.estado_credencial({**base, "activo": 0}) == "Inactivo", "persona desactivada -> Inactivo")
verificar(models.estado_credencial({**base, "vigencia_hasta": hoy.isoformat()}) == "Activo", "el último día de vigencia todavía es Activo")

print("\n=== 3. Registrar una persona con todos los datos del carnet y foto ===")
resp = admin.post("/admin/personas/nueva", data={**formulario(), "foto_zoom": "1.5", "foto_x": "0.4", "foto_y": "0.2",
                  "foto": (imagen_bytes("JPEG", con_exif=True), "yo.jpg")}, follow_redirects=False,
                  content_type="multipart/form-data")
verificar(resp.status_code == 302 and "/carnet" in resp.headers["Location"], "tras registrar, va a la página del carnet")
p = models.obtener_persona_por_cedula("1712345678")
verificar((p["tipo_voluntariado"], p["vigencia_desde"], p["vigencia_hasta"]) == ("Prácticas pre-profesionales", "2026-09-15", "2027-03-15"), "tipo y vigencia guardados")
verificar((p["contacto_nombre"], p["contacto_telefono"]) == ("Contacto de Prueba", "0990000000"), "contacto de emergencia guardado")
verificar(p["frase_extra"].startswith("El tiempo que se disfruta"), "frase extra guardada")
verificar((p["foto_zoom"], p["foto_x"], p["foto_y"]) == (1.5, 0.4, 0.2), "encuadre de la foto guardado")
foto = Image.open(pasec.FOTOS_DIR / p["foto_filename"])
verificar(foto.format == "JPEG" and max(foto.size) <= 1200, f"foto re-codificada y reducida ({foto.size})")
verificar(not foto.getexif() and "exif" not in foto.info, "se eliminaron los metadatos (GPS, cámara) de la foto")
verificar(admin.get(f"/foto/{p['id']}").status_code == 200, "la foto se puede ver desde el sistema")
verificar(guardia.get(f"/foto/{p['id']}").status_code == 200, "el guardia también puede ver la foto (la necesita al escanear)")

print("\n=== 4. Validaciones del formulario ===")
casos = {
    "fechas al revés": formulario(cedula="1700000010", vigencia_desde="2027-03-15", vigencia_hasta="2026-09-15"),
    "falta una fecha": formulario(cedula="1700000011", vigencia_hasta=""),
    "teléfono inválido": formulario(cedula="1700000012", contacto_telefono="llamar mañana"),
    "frase muy larga": formulario(cedula="1700000013", frase_extra="x" * 101),
    "cédula con ruta peligrosa": formulario(cedula="../../etc/passwd"),
    "cédula repetida": formulario(cedula="1712345678"),
    "sin nombre": formulario(cedula="1700000014", nombre=""),
}
for nombre, datos in casos.items():
    resp = admin.post("/admin/personas/nueva", data=datos, follow_redirects=False)
    verificar(resp.status_code == 200 and b"flash-error" in resp.data, f"se rechaza: {nombre}")
verificar(models.obtener_persona_por_cedula("1700000010") is None, "lo rechazado no se guardó")
resp = admin.post("/admin/personas/nueva", data={**formulario(cedula="1700000015"),
                  "foto": (io.BytesIO(b"esto no es una imagen"), "falsa.jpg")}, content_type="multipart/form-data")
verificar(b"no es una imagen" in resp.data and models.obtener_persona_por_cedula("1700000015") is None, "un archivo .jpg falso se rechaza")
resp = admin.post("/admin/personas/nueva", data={**formulario(cedula="1700000016"),
                  "foto": (io.BytesIO(b"hola"), "notas.txt")}, content_type="multipart/form-data")
verificar(b"PNG o JPG" in resp.data, "un archivo que no es PNG/JPG se rechaza")

print("\n=== 5. Registro mínimo (compatibilidad): solo nombre y cédula sigue funcionando ===")
resp = admin.post("/admin/personas/nueva", data={"nombre": "Solo Básico", "cedula": "1700000020"})
verificar(resp.status_code == 302, "se puede registrar con solo nombre y cédula")
basico = models.obtener_persona_por_cedula("1700000020")
verificar(basico["tipo_voluntariado"] is None and basico["foto_filename"] is None, "los campos opcionales quedan vacíos")
verificar(admin.get(f"/admin/personas/{basico['id']}/carnet").status_code == 200, "su página de carnet se abre aunque falten datos")

print("\n=== 6. Editar una persona ===")
verificar(admin.get(f"/admin/personas/{p['id']}/editar").status_code == 200, "el formulario de edición se abre con los datos")
resp = admin.post(f"/admin/personas/{p['id']}/editar", data={**formulario(cedula="9999999999", tipo_voluntariado="Voluntariado general",
                  vigencia_hasta="2027-06-15"), "activo": "on", "foto_zoom": "2", "foto_x": "0.5", "foto_y": "0.5"}, follow_redirects=False)
verificar(resp.status_code == 302, "se guardan los cambios")
p2 = models.obtener_persona_por_id(p["id"])
verificar(p2["tipo_voluntariado"] == "Voluntariado general" and p2["vigencia_hasta"] == "2027-06-15", "tipo y vigencia actualizados")
verificar(p2["cedula"] == "1712345678", "la cédula NO cambia al editar")
verificar(p2["foto_filename"] == p["foto_filename"] and (pasec.FOTOS_DIR / p2["foto_filename"]).exists(), "sin subir foto nueva, se conserva la anterior")
verificar(p2["qr_token"] == p["qr_token"], "el QR (token) sigue siendo el mismo: los carnets ya entregados siguen valiendo")
resp = admin.post(f"/admin/personas/{p['id']}/editar", data={**formulario(), "activo": "on",
                  "foto": (imagen_bytes("PNG", tam=(400, 300)), "nueva.png")}, content_type="multipart/form-data")
verificar(resp.status_code == 302 and Image.open(pasec.FOTOS_DIR / "1712345678.jpg").size[0] <= 400, "se puede reemplazar la foto")

print("\n=== 7. Desactivar / reactivar desde la edición afecta el escaneo ===")
admin.post(f"/admin/personas/{p['id']}/editar", data=formulario())  # sin casilla 'activo' => desactivar
verificar(models.obtener_persona_por_id(p["id"])["activo"] == 0, "sin la casilla 'activa', la persona queda desactivada")
resp = guardia.post("/api/scan", json={"qr_token": p["qr_token"]})
verificar(resp.status_code == 404, "una persona desactivada no puede registrar entrada")
admin.post(f"/admin/personas/{p['id']}/editar", data={**formulario(), "activo": "on"})
resp = guardia.post("/api/scan", json={"qr_token": p["qr_token"]})
verificar(resp.status_code == 200 and resp.get_json()["tipo"] == "entrada", "reactivada, vuelve a registrar normalmente")

print("\n=== 8. Permisos: el guardia NO puede entrar al carnet ni a la edición ===")
for ruta in (f"/admin/personas/{p['id']}/carnet", f"/admin/personas/{p['id']}/editar",
             f"/admin/personas/{p['id']}/qr/carnet.png", "/admin/carnet/qr-muestra.png", "/admin/personas/nueva"):
    verificar(guardia.get(ruta).status_code == 403, f"guardia bloqueado en {ruta.replace(str(p['id']), '<id>')}")
verificar(guardia.post(f"/admin/personas/{p['id']}/editar", data=formulario()).status_code == 403, "guardia no puede enviar ediciones")
verificar(pasec.app.test_client().get(f"/admin/personas/{p['id']}/carnet").status_code == 302, "sin sesión se pide iniciar sesión")

print("\n=== 9. Páginas y QR del carnet ===")
resp = admin.get(f"/admin/personas/{p['id']}/carnet")
verificar(resp.status_code == 200 and "María Pérez López".encode() in resp.data, "la página del carnet se muestra")
verificar(admin.get(f"/admin/personas/{p['id']}/qr").status_code == 302, "la ruta antigua /qr redirige al carnet")
qr = admin.get(f"/admin/personas/{p['id']}/qr/carnet.png")
verificar(qr.status_code == 200 and qr.mimetype == "image/png", "el QR del carnet es un PNG")
try:
    import zxingcpp
    leido = zxingcpp.read_barcodes(Image.open(io.BytesIO(qr.data)).convert("RGB"))
    verificar(leido and leido[0].text == p["qr_token"], "el QR del carnet contiene el token correcto de la persona")
except ImportError:
    print("  (se omite leer el QR: instala 'zxing-cpp' para esta comprobación)")
verificar(admin.get("/admin/carnet/qr-muestra.png").mimetype == "image/png", "existe el QR de ejemplo para la vista previa")
verificar(admin.get("/admin/personas/nueva").status_code == 200, "el formulario de registro se abre")

print("\n=== 10. Panel del administrador ===")
resp = admin.get("/admin")
verificar(resp.status_code == 200 and b"Ver carnet" in resp.data and b"Editar" in resp.data, "el panel muestra los enlaces a carnet y edición")
verificar(b"15/03/2027" in resp.data, "la vigencia se muestra en formato dd/mm/aaaa")
verificar("Prácticas pre-profesionales".encode() in resp.data, "se muestra el tipo de voluntariado")
verificar(b"Persona Antigua" in resp.data, "las personas antiguas (sin datos de carnet) también aparecen")

print("\n=== 11. Diseño: marca, tipografía y recursos propios ===")
resp = pasec.app.test_client().get("/login")
verificar(resp.status_code == 200 and config.NOMBRE_ENTIDAD.encode() in resp.data, "el login muestra el nombre de la organización")
verificar(b"emblema_blanco.png" in resp.data and b"favicon.ico" in resp.data, "el login usa el emblema y el favicon de la organización")
for ruta in ("img/emblema_blanco.png", "img/favicon.ico", "img/icono-180.png", "js/html5-qrcode.min.js",
             "fonts/montserrat-latin-400-normal.woff2", "fonts/montserrat-latin-800-normal.woff2", "css/style.css"):
    verificar(pasec.app.test_client().get(f"/static/{ruta}").status_code == 200, f"se sirve static/{ruta}")
resp = guardia.get("/scan")
verificar(b"unpkg.com" not in resp.data and b"js/html5-qrcode.min.js" in resp.data, "la pantalla de escaneo ya no depende de un servidor externo (unpkg)")
resp = admin.get("/admin")
verificar(b"Personas registradas" in resp.data and b"Carnets vencidos" in resp.data, "el panel muestra las tarjetas de resumen")
verificar(resp.data.count(b'class="activo"') == 1, "la navegación marca solo la página actual")

print("\nTODAS LAS PRUEBAS DEL CARNET PASARON CORRECTAMENTE ✔")
