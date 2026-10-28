"""
Capa de acceso a datos para PASEC.
Usa SQLite (archivo pasec.db) sin ORM, para mantenerlo simple y fácil de leer.
"""
import sqlite3
import uuid
from datetime import date, datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "pasec.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Crea las tablas si no existen."""
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            rol TEXT NOT NULL CHECK (rol IN ('admin', 'guardia')),
            nombre_completo TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS personas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            cedula TEXT UNIQUE NOT NULL,
            qr_token TEXT UNIQUE NOT NULL,
            fecha_registro TEXT NOT NULL,
            activo INTEGER NOT NULL DEFAULT 1,
            foto_filename TEXT,
            tipo_voluntariado TEXT,
            vigencia_desde TEXT,
            vigencia_hasta TEXT,
            contacto_nombre TEXT,
            contacto_telefono TEXT,
            frase_extra TEXT,
            foto_zoom REAL NOT NULL DEFAULT 1.0,
            foto_x REAL NOT NULL DEFAULT 0.5,
            foto_y REAL NOT NULL DEFAULT 0.3
        );

        CREATE TABLE IF NOT EXISTS registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            persona_id INTEGER NOT NULL,
            tipo TEXT NOT NULL CHECK (tipo IN ('entrada', 'salida')),
            timestamp TEXT NOT NULL,
            FOREIGN KEY (persona_id) REFERENCES personas (id)
        );

        CREATE INDEX IF NOT EXISTS idx_registros_persona ON registros(persona_id);
        """
    )
    conn.commit()
    conn.close()
    _migrar_columnas()


# Columnas que se agregaron después de la primera versión. Si la base de datos
# ya existía (por ejemplo, la de producción), se agregan sin perder datos.
COLUMNAS_NUEVAS_PERSONAS = {
    "foto_filename": "TEXT",
    "tipo_voluntariado": "TEXT",
    "vigencia_desde": "TEXT",
    "vigencia_hasta": "TEXT",
    "contacto_nombre": "TEXT",
    "contacto_telefono": "TEXT",
    "frase_extra": "TEXT",
    "foto_zoom": "REAL NOT NULL DEFAULT 1.0",
    "foto_x": "REAL NOT NULL DEFAULT 0.5",
    "foto_y": "REAL NOT NULL DEFAULT 0.3",
}


def _migrar_columnas():
    """Agrega a 'personas' las columnas que falten. Seguro de correr varias veces."""
    conn = get_conn()
    existentes = {fila["name"] for fila in conn.execute("PRAGMA table_info(personas)")}
    for nombre, definicion in COLUMNAS_NUEVAS_PERSONAS.items():
        if nombre not in existentes:
            conn.execute(f"ALTER TABLE personas ADD COLUMN {nombre} {definicion}")
    conn.commit()
    conn.close()


def crear_usuario(username, password_hash, rol, nombre_completo):
    conn = get_conn()
    conn.execute(
        "INSERT INTO usuarios (username, password_hash, rol, nombre_completo) VALUES (?, ?, ?, ?)",
        (username, password_hash, rol, nombre_completo),
    )
    conn.commit()
    conn.close()


def obtener_usuario_por_username(username):
    conn = get_conn()
    row = conn.execute("SELECT * FROM usuarios WHERE username = ?", (username,)).fetchone()
    conn.close()
    return row


# Campos del carnet que el administrador puede editar (lista blanca: solo
# estos nombres de columna se aceptan al actualizar).
CAMPOS_CARNET = (
    "tipo_voluntariado", "vigencia_desde", "vigencia_hasta",
    "contacto_nombre", "contacto_telefono", "frase_extra",
    "foto_zoom", "foto_x", "foto_y",
)


def crear_persona(nombre, cedula, foto_filename=None, **carnet):
    """Crea una persona nueva con un qr_token único (UUID4).
    El QR no codifica la cédula directamente por seguridad: codifica un token
    aleatorio que el sistema resuelve internamente contra la cédula/nombre.
    `carnet` recibe los campos del carnet (ver CAMPOS_CARNET).
    """
    desconocidos = set(carnet) - set(CAMPOS_CARNET)
    if desconocidos:
        raise ValueError(f"Campos de carnet no válidos: {sorted(desconocidos)}")
    qr_token = uuid.uuid4().hex
    columnas = ["nombre", "cedula", "qr_token", "fecha_registro", "foto_filename"]
    valores = [nombre, cedula, qr_token, datetime.now().isoformat(timespec="seconds"), foto_filename]
    for campo, valor in carnet.items():
        columnas.append(campo)
        valores.append(valor)
    marcas = ", ".join("?" for _ in columnas)
    conn = get_conn()
    cur = conn.execute(
        f"INSERT INTO personas ({', '.join(columnas)}) VALUES ({marcas})", valores
    )
    conn.commit()
    persona_id = cur.lastrowid
    conn.close()
    return persona_id, qr_token


def actualizar_persona(persona_id, nombre=None, activo=None, foto_filename=None, **carnet):
    """Actualiza datos de una persona. Solo toca lo que se pase explícitamente
    (los campos en None no se modifican). Los campos del carnet vacíos se
    guardan como NULL cuando se pasan como cadena vacía."""
    desconocidos = set(carnet) - set(CAMPOS_CARNET)
    if desconocidos:
        raise ValueError(f"Campos de carnet no válidos: {sorted(desconocidos)}")
    cambios = {}
    if nombre is not None:
        cambios["nombre"] = nombre
    if activo is not None:
        cambios["activo"] = 1 if activo else 0
    if foto_filename is not None:
        cambios["foto_filename"] = foto_filename
    for campo, valor in carnet.items():
        cambios[campo] = valor
    if not cambios:
        return
    asignaciones = ", ".join(f"{c} = ?" for c in cambios)
    conn = get_conn()
    conn.execute(
        f"UPDATE personas SET {asignaciones} WHERE id = ?",
        [*cambios.values(), persona_id],
    )
    conn.commit()
    conn.close()


def estado_credencial(persona, hoy=None):
    """Estado que se muestra en el carnet, calculado automáticamente:
    'Inactivo' si la persona fue desactivada; 'Vencido' si la vigencia ya
    terminó; 'Por iniciar' si todavía no empieza; 'Activo' en otro caso."""
    hoy = hoy or date.today().isoformat()
    if not persona["activo"]:
        return "Inactivo"
    desde, hasta = persona["vigencia_desde"], persona["vigencia_hasta"]
    if hasta and hoy > hasta:
        return "Vencido"
    if desde and hoy < desde:
        return "Por iniciar"
    return "Activo"


def actualizar_foto_persona(persona_id, foto_filename):
    conn = get_conn()
    conn.execute(
        "UPDATE personas SET foto_filename = ? WHERE id = ?", (foto_filename, persona_id)
    )
    conn.commit()
    conn.close()


def obtener_persona_por_token(qr_token):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM personas WHERE qr_token = ? AND activo = 1", (qr_token,)
    ).fetchone()
    conn.close()
    return row


def obtener_persona_por_cedula(cedula):
    conn = get_conn()
    row = conn.execute("SELECT * FROM personas WHERE cedula = ?", (cedula,)).fetchone()
    conn.close()
    return row


def obtener_persona_por_id(persona_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM personas WHERE id = ?", (persona_id,)).fetchone()
    conn.close()
    return row


def listar_personas():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM personas WHERE activo = 1 ORDER BY nombre COLLATE NOCASE"
    ).fetchall()
    conn.close()
    return rows


def desactivar_persona(persona_id):
    conn = get_conn()
    conn.execute("UPDATE personas SET activo = 0 WHERE id = ?", (persona_id,))
    conn.commit()
    conn.close()


def ultimo_registro(persona_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM registros WHERE persona_id = ? ORDER BY timestamp DESC, id DESC LIMIT 1",
        (persona_id,),
    ).fetchone()
    conn.close()
    return row


def registrar_movimiento(persona_id):
    """Determina si el siguiente movimiento es entrada o salida (alternando)
    y lo inserta. Devuelve (tipo, timestamp)."""
    ultimo = ultimo_registro(persona_id)
    tipo = "entrada" if (ultimo is None or ultimo["tipo"] == "salida") else "salida"
    ts = datetime.now().isoformat(timespec="seconds")
    conn = get_conn()
    conn.execute(
        "INSERT INTO registros (persona_id, tipo, timestamp) VALUES (?, ?, ?)",
        (persona_id, tipo, ts),
    )
    conn.commit()
    conn.close()
    return tipo, ts


def listar_registros(persona_id=None, desde=None, hasta=None):
    """Lista registros con nombre/cédula de la persona, más recientes primero.
    Filtros opcionales: persona_id, fecha desde/hasta (formato 'YYYY-MM-DD')."""
    conn = get_conn()
    query = """
        SELECT r.id, r.tipo, r.timestamp, p.nombre, p.cedula, p.id as persona_id
        FROM registros r
        JOIN personas p ON p.id = r.persona_id
        WHERE 1=1
    """
    params = []
    if persona_id:
        query += " AND p.id = ?"
        params.append(persona_id)
    if desde:
        query += " AND date(r.timestamp) >= date(?)"
        params.append(desde)
    if hasta:
        query += " AND date(r.timestamp) <= date(?)"
        params.append(hasta)
    query += " ORDER BY r.timestamp DESC, r.id DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def estado_actual_personas():
    """Devuelve, por persona, si está actualmente 'dentro' o 'fuera' del lugar."""
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT p.id, p.nombre, p.cedula, p.foto_filename, p.activo,
               p.tipo_voluntariado, p.vigencia_desde, p.vigencia_hasta,
               (SELECT tipo FROM registros r
                WHERE r.persona_id = p.id
                ORDER BY r.timestamp DESC, r.id DESC LIMIT 1) as ultimo_tipo,
               (SELECT timestamp FROM registros r
                WHERE r.persona_id = p.id
                ORDER BY r.timestamp DESC, r.id DESC LIMIT 1) as ultimo_ts
        FROM personas p
        WHERE p.activo = 1
        ORDER BY p.nombre COLLATE NOCASE
        """
    ).fetchall()
    conn.close()
    return rows
