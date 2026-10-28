"""
Servidor de producción de PASEC (para la computadora de la organización).

Usa Waitress, un servidor estable que funciona en Windows, Mac y Linux.
Escucha solo en esta computadora (127.0.0.1): el acceso desde internet lo
da el túnel seguro (Cloudflare Tunnel) con el dominio de la organización.

    python servidor.py
"""
import os

from waitress import serve

import models
from app import app

PUERTO = int(os.environ.get("PASEC_PUERTO", "8000"))

if __name__ == "__main__":
    if not models.DB_PATH.exists():
        raise SystemExit("No se encontró pasec.db. Ejecuta primero 1_INSTALAR.bat")
    print(f"PASEC en marcha: http://localhost:{PUERTO}  (no cierres esta ventana)")
    serve(app, host="127.0.0.1", port=PUERTO, threads=6)
