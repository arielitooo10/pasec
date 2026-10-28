"""
Copia de seguridad de PASEC: base de datos + fotos.

Crea la carpeta respaldos/AAAA-MM-DD_HH-MM con pasec.db y fotos/, y conserva
solo las últimas 30 copias. La base se copia con la API de SQLite, así que es
segura aunque el sistema esté funcionando.

    python respaldo.py              (guarda en la carpeta respaldos/)
    python respaldo.py D:\\PASEC     (guarda en otra carpeta, p. ej. una USB)
"""
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent
MANTENER = 30


def main():
    origen_db = BASE / "pasec.db"
    if not origen_db.exists():
        print("No hay pasec.db todavía: nada que respaldar.")
        return 0
    raiz = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE / "respaldos"
    destino = raiz / datetime.now().strftime("%Y-%m-%d_%H-%M")
    destino.mkdir(parents=True, exist_ok=True)

    origen = sqlite3.connect(origen_db)
    copia = sqlite3.connect(destino / "pasec.db")
    with copia:
        origen.backup(copia)
    copia.close()
    origen.close()

    fotos = BASE / "fotos"
    if fotos.exists():
        shutil.copytree(fotos, destino / "fotos", dirs_exist_ok=True)

    copias = sorted(p for p in raiz.iterdir() if p.is_dir())
    for vieja in copias[:-MANTENER]:
        shutil.rmtree(vieja, ignore_errors=True)
    print(f"Respaldo guardado en: {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
