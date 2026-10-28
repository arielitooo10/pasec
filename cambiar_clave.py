"""
Cambia la contraseña de un usuario (admin o guardia) sin borrar nada.

    python cambiar_clave.py            (pregunta el usuario y la clave nueva)
    python cambiar_clave.py admin
"""
import sys
from getpass import getpass

from werkzeug.security import generate_password_hash

import models


def main():
    usuario = sys.argv[1] if len(sys.argv) > 1 else input("Usuario (admin o guardia): ").strip()
    fila = models.obtener_usuario_por_username(usuario)
    if fila is None:
        print(f"No existe el usuario '{usuario}'.")
        return 1
    nueva = getpass("Contraseña nueva (no se ve al escribir): ")
    if len(nueva) < 8:
        print("Usa al menos 8 caracteres.")
        return 1
    if nueva != getpass("Repite la contraseña nueva: "):
        print("Las contraseñas no coinciden. No se cambió nada.")
        return 1
    conn = models.get_conn()
    with conn:
        conn.execute(
            "UPDATE usuarios SET password_hash = ? WHERE username = ?",
            (generate_password_hash(nueva), usuario),
        )
    conn.close()
    print(f"Contraseña de '{usuario}' actualizada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
