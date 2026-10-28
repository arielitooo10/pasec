"""
PASEC - Control de acceso por código QR
=========================================
Aplicación Flask para registrar la hora de entrada y salida de personas
mediante escaneo de un código QR, con un panel de administrador y un
acceso restringido para el guardia (solo escaneo).

Ejecutar:
    python init_db.py   # una sola vez, crea la base de datos y usuarios
    python app.py        # levanta el servidor en http://localhost:5000
"""
import calendar
import functools
import io
import csv
import os
import re
from datetime import date, datetime
from pathlib import Path

import qrcode
from PIL import Image, ImageOps
from flask import (
    Flask, render_template, request, redirect, url_for, session,
    flash, send_file, jsonify, abort
)
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

import models
import config

BASE_DIR = Path(__file__).parent
QR_DIR = BASE_DIR / "qrcodes"
QR_DIR.mkdir(exist_ok=True)
FOTOS_DIR = BASE_DIR / "fotos"
FOTOS_DIR.mkdir(exist_ok=True)

EXTENSIONES_FOTO_PERMITIDAS = {"png", "jpg", "jpeg"}

app = Flask(__name__)
# En el servidor (PythonAnywhere), define la variable de entorno SECRET_KEY
# con un valor propio. Localmente, si no existe, usa este valor por defecto.
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "cambia-esta-clave-por-una-propia-antes-de-usar-en-produccion"
)
# Límite de tamaño para las fotos subidas (8 MB).
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

# Cookies de sesión más seguras. SESSION_COOKIE_SECURE solo se activa cuando
# el sistema se sirve por HTTPS (la variable PASEC_HTTPS=1 la define 2_INICIAR.bat).
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("PASEC_HTTPS") == "1"

# Detrás de un túnel o proxy HTTPS (Cloudflare Tunnel, nginx...) Flask debe
# confiar en el esquema/host que le reenvía el proxy.
if os.environ.get("PASEC_PROXY") == "1":
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)


@app.context_processor
def inyectar_config_marca():
    """Hace disponibles NOMBRE_ENTIDAD y SUBTITULO en todas las plantillas."""
    return {
        "NOMBRE_ENTIDAD": config.NOMBRE_ENTIDAD,
        "SUBTITULO": config.SUBTITULO,
        # Textos fijos del carnet; el dibujo del carnet (JavaScript) los lee de aquí.
        "CARNET_CONFIG": {
            "entidad": config.NOMBRE_ENTIDAD,
            "titulo": config.CARNET_TITULO,
            "rol": config.CARNET_ROL,
            "fraseFija": config.CARNET_FRASE_FIJA,
        },
        "TIPOS_VOLUNTARIADO": config.TIPOS_VOLUNTARIADO,
    }


@app.template_filter("fecha_es")
def fecha_es(valor):
    """'2026-09-15' -> '15/09/2026' (vacío si no hay fecha)."""
    if not valor:
        return ""
    try:
        return date.fromisoformat(valor).strftime("%d/%m/%Y")
    except ValueError:
        return valor


@app.template_filter("fecha_hora_es")
def fecha_hora_es(valor):
    """'2026-10-15T17:10:30' -> '15/10/2026 17:10' (vacío si no hay valor)."""
    if not valor:
        return ""
    try:
        return datetime.fromisoformat(valor).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return valor


@app.errorhandler(413)
def archivo_demasiado_grande(_e):
    flash("La foto es demasiado grande (máximo 8 MB).", "error")
    return redirect(request.referrer or url_for("admin_dashboard"))


# ---------------------------------------------------------------------------
# Autenticación y control de acceso
# ---------------------------------------------------------------------------

def login_required(rol=None):
    """Decorador: exige sesión iniciada, y opcionalmente un rol específico
    ('admin' o 'guardia'). Sin rol, acepta cualquier usuario autenticado."""
    def decorador(vista):
        @functools.wraps(vista)
        def envoltura(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login", next=request.path))
            if rol is not None and session.get("rol") != rol:
                abort(403)
            return vista(*args, **kwargs)
        return envoltura
    return decorador


@app.route("/", methods=["GET"])
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("rol") == "admin":
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("scan_page"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        usuario = models.obtener_usuario_por_username(username)
        if usuario is None or not check_password_hash(usuario["password_hash"], password):
            flash("Usuario o contraseña incorrectos.", "error")
            return render_template("login.html")
        session["user_id"] = usuario["id"]
        session["username"] = usuario["username"]
        session["rol"] = usuario["rol"]
        session["nombre_completo"] = usuario["nombre_completo"]
        if usuario["rol"] == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("scan_page"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Panel de administrador
# ---------------------------------------------------------------------------

@app.route("/admin")
@login_required(rol="admin")
def admin_dashboard():
    personas = models.listar_personas()
    estado = []
    for fila in models.estado_actual_personas():
        fila = dict(fila)
        fila["estado_carnet"] = models.estado_credencial(fila)
        estado.append(fila)
    return render_template("admin_dashboard.html", personas=personas, estado=estado)


def _sumar_meses(fecha, meses):
    """Suma meses a una fecha (ajustando el día si el mes destino es más corto)."""
    indice = fecha.month - 1 + meses
    anio, mes = fecha.year + indice // 12, indice % 12 + 1
    dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
    return date(anio, mes, dia)


def _formulario_por_defecto():
    """Valores iniciales del formulario de una persona nueva."""
    hoy = date.today()
    return {
        "nombre": "", "cedula": "", "tipo_voluntariado": "",
        "vigencia_desde": hoy.isoformat(),
        "vigencia_hasta": _sumar_meses(hoy, 6).isoformat(),
        "contacto_nombre": "", "contacto_telefono": "", "frase_extra": "",
        "foto_zoom": 1.0, "foto_x": 0.5, "foto_y": 0.3, "activo": True,
    }


def _formulario_desde_persona(persona):
    """Valores del formulario para editar una persona ya guardada."""
    base = _formulario_por_defecto()
    for campo in ("nombre", "cedula", "tipo_voluntariado", "contacto_nombre",
                  "contacto_telefono", "frase_extra"):
        base[campo] = persona[campo] or ""
    # Personas registradas antes de que existiera el carnet no tienen vigencia:
    # se deja la sugerida (hoy + 6 meses) para que el administrador la confirme.
    for campo in ("vigencia_desde", "vigencia_hasta"):
        base[campo] = persona[campo] or base[campo]
    for campo in ("foto_zoom", "foto_x", "foto_y"):
        base[campo] = persona[campo]
    base["activo"] = bool(persona["activo"])
    return base


def _numero(valor, minimo, maximo, por_defecto):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return por_defecto
    return max(minimo, min(maximo, numero))


def _leer_formulario(form, editando=False):
    """Lee y valida el formulario de registro/edición.
    Devuelve (datos, errores). `datos` incluye los valores tal como se
    mostrarán de nuevo si hay errores."""
    def texto(nombre):
        return re.sub(r"\s+", " ", form.get(nombre, "")).strip()

    datos = {
        "nombre": texto("nombre"),
        "cedula": texto("cedula"),
        "tipo_voluntariado": texto("tipo_voluntariado"),
        "vigencia_desde": form.get("vigencia_desde", "").strip(),
        "vigencia_hasta": form.get("vigencia_hasta", "").strip(),
        "contacto_nombre": texto("contacto_nombre"),
        "contacto_telefono": texto("contacto_telefono"),
        "frase_extra": texto("frase_extra"),
        "foto_zoom": _numero(form.get("foto_zoom"), 1.0, 4.0, 1.0),
        "foto_x": _numero(form.get("foto_x"), 0.0, 1.0, 0.5),
        "foto_y": _numero(form.get("foto_y"), 0.0, 1.0, 0.3),
        "activo": ("activo" in form) if editando else True,
    }
    errores = []

    if not datos["nombre"] or not datos["cedula"]:
        errores.append("Nombre y cédula son obligatorios.")
    elif len(datos["nombre"]) > 80:
        errores.append("El nombre es demasiado largo (máximo 80 caracteres).")
    if datos["cedula"] and not re.fullmatch(r"[A-Za-z0-9-]{5,20}", datos["cedula"]):
        errores.append("La cédula solo puede tener letras, números o guiones (5 a 20 caracteres).")
    if len(datos["tipo_voluntariado"]) > 40:
        errores.append("El tipo de voluntariado es demasiado largo (máximo 40 caracteres).")
    if len(datos["contacto_nombre"]) > 40:
        errores.append("El nombre del contacto de emergencia es demasiado largo (máximo 40 caracteres).")
    if datos["contacto_telefono"] and not re.fullmatch(r"[0-9+()\s-]{6,20}", datos["contacto_telefono"]):
        errores.append("El teléfono de emergencia solo puede tener números, espacios, + ( ) y guiones.")
    if len(datos["frase_extra"]) > 100:
        errores.append("La frase es demasiado larga (máximo 100 caracteres).")

    desde, hasta = datos["vigencia_desde"], datos["vigencia_hasta"]
    if bool(desde) != bool(hasta):
        errores.append("Indica tanto la fecha de inicio como la de fin de la vigencia.")
    elif desde and hasta:
        try:
            if date.fromisoformat(hasta) < date.fromisoformat(desde):
                errores.append("La fecha de fin de la vigencia no puede ser anterior a la de inicio.")
        except ValueError:
            errores.append("Las fechas de vigencia no son válidas.")

    return datos, errores


def _campos_carnet(datos):
    """Del formulario validado, extrae solo los campos del carnet para la BD
    (los textos vacíos se guardan como NULL)."""
    return {
        campo: (datos[campo] if datos[campo] != "" else None)
        for campo in models.CAMPOS_CARNET
    }


def _render_formulario(datos, persona=None, errores=()):
    for error in errores:
        flash(error, "error")
    return render_template(
        "registrar_persona.html", form=datos, persona=persona, editando=persona is not None
    )


@app.route("/admin/personas/nueva", methods=["GET", "POST"])
@login_required(rol="admin")
def registrar_persona():
    if request.method == "POST":
        datos, errores = _leer_formulario(request.form)
        if not errores and models.obtener_persona_por_cedula(datos["cedula"]) is not None:
            errores.append("Ya existe una persona registrada con esa cédula.")

        foto_filename = None
        archivo_foto = request.files.get("foto")
        if not errores and archivo_foto and archivo_foto.filename:
            ok, resultado = _guardar_foto(archivo_foto, datos["cedula"])
            if ok:
                foto_filename = resultado
            else:
                errores.append(resultado)

        if errores:
            return _render_formulario(datos, errores=errores)

        persona_id, qr_token = models.crear_persona(
            datos["nombre"], datos["cedula"], foto_filename, **_campos_carnet(datos)
        )
        _generar_imagen_qr(qr_token, datos["cedula"])
        flash(f"Persona '{datos['nombre']}' registrada correctamente.", "success")
        return redirect(url_for("ver_carnet", persona_id=persona_id))

    return _render_formulario(_formulario_por_defecto())


@app.route("/admin/personas/<int:persona_id>/editar", methods=["GET", "POST"])
@login_required(rol="admin")
def editar_persona(persona_id):
    persona = models.obtener_persona_por_id(persona_id)
    if persona is None:
        abort(404)

    if request.method == "POST":
        datos, errores = _leer_formulario(request.form, editando=True)
        datos["cedula"] = persona["cedula"]  # la cédula no se cambia al editar

        nueva_foto = None
        archivo_foto = request.files.get("foto")
        if not errores and archivo_foto and archivo_foto.filename:
            ok, resultado = _guardar_foto(archivo_foto, persona["cedula"])
            if ok:
                nueva_foto = resultado
            else:
                errores.append(resultado)

        if errores:
            return _render_formulario(datos, persona=persona, errores=errores)

        models.actualizar_persona(
            persona_id,
            nombre=datos["nombre"],
            activo=datos["activo"],
            foto_filename=nueva_foto,
            **_campos_carnet(datos),
        )
        # Si la foto nueva tiene otro nombre de archivo, se borra la anterior.
        if nueva_foto and persona["foto_filename"] and persona["foto_filename"] != nueva_foto:
            (FOTOS_DIR / persona["foto_filename"]).unlink(missing_ok=True)
        flash("Cambios guardados.", "success")
        return redirect(url_for("ver_carnet", persona_id=persona_id))

    return _render_formulario(_formulario_desde_persona(persona), persona=persona)


def _guardar_foto(archivo_foto, cedula):
    """Valida y guarda la foto subida. Devuelve (True, nombre_de_archivo) o
    (False, mensaje_de_error).

    La imagen se vuelve a codificar como JPG (máx. 1200 px de lado): así se
    comprueba que realmente es una imagen, se corrige la rotación de las fotos
    de celular, se achica su tamaño y se descartan los metadatos (por ejemplo
    la ubicación GPS que guardan las cámaras)."""
    extension = Path(secure_filename(archivo_foto.filename)).suffix.lower().lstrip(".")
    if extension not in EXTENSIONES_FOTO_PERMITIDAS:
        return False, "La foto debe ser una imagen PNG o JPG."
    try:
        imagen = Image.open(archivo_foto.stream)
        imagen.load()
    except Exception:
        return False, "No se pudo leer la foto: el archivo no es una imagen válida."
    imagen = ImageOps.exif_transpose(imagen)
    if imagen.mode in ("RGBA", "LA", "P"):
        imagen = imagen.convert("RGBA")
        fondo = Image.new("RGB", imagen.size, "white")
        fondo.paste(imagen, mask=imagen.getchannel("A"))
        imagen = fondo
    else:
        imagen = imagen.convert("RGB")
    imagen.thumbnail((1200, 1200), Image.LANCZOS)
    nombre_archivo = f"{cedula}.jpg"
    imagen.save(FOTOS_DIR / nombre_archivo, "JPEG", quality=90, optimize=True)
    return True, nombre_archivo


def _generar_imagen_qr(qr_token, cedula):
    """Genera y guarda la imagen PNG del QR para un token dado."""
    img = qrcode.make(qr_token)
    ruta = QR_DIR / f"{cedula}.png"
    img.save(ruta)
    return ruta


def _png_qr_sin_borde(texto):
    """QR en PNG sin margen blanco, para dibujarlo dentro del carnet."""
    qr = qrcode.QRCode(box_size=16, border=0, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(texto)
    qr.make(fit=True)
    buffer = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def _datos_carnet(persona):
    """Datos de una persona listos para dibujar su carnet en el navegador."""
    return {
        "nombre": persona["nombre"],
        "tipo": persona["tipo_voluntariado"] or "",
        "desde": persona["vigencia_desde"] or "",
        "hasta": persona["vigencia_hasta"] or "",
        "estado": models.estado_credencial(persona),
        "contactoNombre": persona["contacto_nombre"] or "",
        "contactoTelefono": persona["contacto_telefono"] or "",
        "frase": persona["frase_extra"] or "",
        "fotoUrl": url_for("foto_persona", persona_id=persona["id"]) if persona["foto_filename"] else None,
        "fotoZoom": persona["foto_zoom"],
        "fotoX": persona["foto_x"],
        "fotoY": persona["foto_y"],
        "qrUrl": url_for("qr_carnet", persona_id=persona["id"]),
    }


@app.route("/admin/personas/<int:persona_id>/carnet")
@login_required(rol="admin")
def ver_carnet(persona_id):
    persona = models.obtener_persona_por_id(persona_id)
    if persona is None:
        abort(404)
    return render_template("ver_carnet.html", persona=persona, carnet=_datos_carnet(persona))


@app.route("/admin/personas/<int:persona_id>/qr")
@login_required(rol="admin")
def ver_qr(persona_id):
    """Ruta antigua: ahora el QR forma parte del carnet."""
    return redirect(url_for("ver_carnet", persona_id=persona_id))


@app.route("/admin/personas/<int:persona_id>/qr/carnet.png")
@login_required(rol="admin")
def qr_carnet(persona_id):
    persona = models.obtener_persona_por_id(persona_id)
    if persona is None:
        abort(404)
    return send_file(_png_qr_sin_borde(persona["qr_token"]), mimetype="image/png")


@app.route("/admin/carnet/qr-muestra.png")
@login_required(rol="admin")
def qr_muestra():
    """QR de ejemplo para la vista previa de una persona que aún no se guarda."""
    return send_file(_png_qr_sin_borde("PASEC-VISTA-PREVIA"), mimetype="image/png")


@app.route("/admin/personas/<int:persona_id>/qr/imagen")
@login_required(rol="admin")
def imagen_qr(persona_id):
    persona = models.obtener_persona_por_id(persona_id)
    if persona is None:
        abort(404)
    ruta = QR_DIR / f"{persona['cedula']}.png"
    if not ruta.exists():
        _generar_imagen_qr(persona["qr_token"], persona["cedula"])
    return send_file(ruta, mimetype="image/png")


@app.route("/admin/personas/<int:persona_id>/qr/descargar")
@login_required(rol="admin")
def descargar_qr(persona_id):
    persona = models.obtener_persona_por_id(persona_id)
    if persona is None:
        abort(404)
    ruta = QR_DIR / f"{persona['cedula']}.png"
    if not ruta.exists():
        _generar_imagen_qr(persona["qr_token"], persona["cedula"])
    return send_file(ruta, as_attachment=True, download_name=f"QR_{persona['cedula']}.png")


@app.route("/foto/<int:persona_id>")
@login_required()
def foto_persona(persona_id):
    """Sirve la foto de una persona. Accesible tanto para admin como para
    guardia, ya que el guardia la necesita ver al escanear el QR."""
    persona = models.obtener_persona_por_id(persona_id)
    if persona is None or not persona["foto_filename"]:
        abort(404)
    ruta = FOTOS_DIR / persona["foto_filename"]
    if not ruta.exists():
        abort(404)
    return send_file(ruta)


@app.route("/admin/personas/<int:persona_id>/eliminar", methods=["POST"])
@login_required(rol="admin")
def eliminar_persona(persona_id):
    models.desactivar_persona(persona_id)
    flash("Persona desactivada.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/registros")
@login_required(rol="admin")
def ver_registros():
    persona_id = request.args.get("persona_id", type=int)
    desde = request.args.get("desde") or None
    hasta = request.args.get("hasta") or None
    registros = models.listar_registros(persona_id=persona_id, desde=desde, hasta=hasta)
    personas = models.listar_personas()
    return render_template(
        "registros.html",
        registros=registros,
        personas=personas,
        filtro_persona_id=persona_id,
        filtro_desde=desde or "",
        filtro_hasta=hasta or "",
    )


@app.route("/admin/registros/exportar.csv")
@login_required(rol="admin")
def exportar_registros_csv():
    persona_id = request.args.get("persona_id", type=int)
    desde = request.args.get("desde") or None
    hasta = request.args.get("hasta") or None
    registros = models.listar_registros(persona_id=persona_id, desde=desde, hasta=hasta)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Nombre", "Cédula", "Tipo", "Fecha y hora"])
    for r in registros:
        writer.writerow([r["nombre"], r["cedula"], r["tipo"], r["timestamp"]])

    mem = io.BytesIO(buffer.getvalue().encode("utf-8-sig"))
    return send_file(
        mem, mimetype="text/csv", as_attachment=True, download_name="registros_pasec.csv"
    )


# ---------------------------------------------------------------------------
# Pantalla de escaneo (guardia)
# ---------------------------------------------------------------------------

@app.route("/scan")
@login_required()
def scan_page():
    return render_template("scan.html")


@app.route("/api/scan", methods=["POST"])
@login_required()
def api_scan():
    data = request.get_json(silent=True) or {}
    qr_token = (data.get("qr_token") or "").strip()
    if not qr_token:
        return jsonify({"ok": False, "error": "Código QR vacío."}), 400

    persona = models.obtener_persona_por_token(qr_token)
    if persona is None:
        return jsonify({"ok": False, "error": "Código QR no reconocido."}), 404

    tipo, ts = models.registrar_movimiento(persona["id"])
    foto_url = url_for("foto_persona", persona_id=persona["id"]) if persona["foto_filename"] else None
    return jsonify(
        {
            "ok": True,
            "nombre": persona["nombre"],
            "cedula": persona["cedula"],
            "tipo": tipo,
            "timestamp": ts,
            "foto_url": foto_url,
        }
    )


if __name__ == "__main__":
    if not models.DB_PATH.exists():
        print("No se encontró pasec.db — ejecuta primero: python init_db.py")
    app.run(host="0.0.0.0", port=5000, debug=True)
