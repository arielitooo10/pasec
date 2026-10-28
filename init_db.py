"""
Script de inicialización: crea las tablas y los usuarios iniciales
(un admin y un guardia) si todavía no existen.

Ejecutar una sola vez (o cada vez que quieras resetear usuarios):
    python init_db.py
"""
from werkzeug.security import generate_password_hash

from models import init_db, obtener_usuario_por_username, crear_usuario

# --- Cambia estas credenciales antes de usar el sistema en producción ---
USUARIOS_INICIALES = [
    {
        "username": "admin",
        "password": "admin123",
        "rol": "admin",
        "nombre_completo": "Administrador",
    },
    {
        "username": "guardia",
        "password": "guardia123",
        "rol": "guardia",
        "nombre_completo": "Guardia de turno",
    },
]


def main():
    init_db()
    for u in USUARIOS_INICIALES:
        if obtener_usuario_por_username(u["username"]) is None:
            crear_usuario(
                u["username"],
                generate_password_hash(u["password"]),
                u["rol"],
                u["nombre_completo"],
            )
            print(f"Usuario creado: {u['username']} (rol: {u['rol']})")
        else:
            print(f"Usuario ya existe, se omite: {u['username']}")
    print("\nBase de datos lista (pasec.db).")
    print("Credenciales iniciales:")
    for u in USUARIOS_INICIALES:
        print(f"  - {u['rol']}: usuario='{u['username']}'  clave='{u['password']}'")
    print("\nIMPORTANTE: cambia estas contraseñas antes de usar el sistema en un caso real.")


if __name__ == "__main__":
    main()
