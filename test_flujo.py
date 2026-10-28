"""
Script de prueba end-to-end usando el test client de Flask.
No requiere levantar el servidor ni usar una cámara real: simula
las peticiones HTTP que haría un navegador.

Ejecutar: python test_flujo.py
"""
import models
from app import app

print("=== 1. Login como admin ===")
client = app.test_client()
resp = client.post("/login", data={"username": "admin", "password": "admin123"}, follow_redirects=True)
assert resp.status_code == 200
assert b"Panel de administrador" in resp.data
print("OK: admin inició sesión y ve el panel.\n")

print("=== 2. Registrar una persona nueva ===")
resp = client.post(
    "/admin/personas/nueva",
    data={"nombre": "Juan Pérez (prueba)", "cedula": "1799999999"},
    follow_redirects=True,
)
assert resp.status_code == 200
persona = models.obtener_persona_por_cedula("1799999999")
assert persona is not None, "La persona no quedó guardada en la base de datos"
print(f"OK: persona creada con id={persona['id']}, qr_token={persona['qr_token']}\n")

print("=== 3. No se debe poder registrar la misma cédula dos veces ===")
resp = client.post(
    "/admin/personas/nueva",
    data={"nombre": "Otro Nombre", "cedula": "1799999999"},
    follow_redirects=True,
)
assert "Ya existe una persona registrada".encode("utf-8") in resp.data
print("OK: la validación de cédula duplicada funciona.\n")

print("=== 4. Cerrar sesión de admin y entrar como guardia ===")
client.get("/logout")
resp = client.post("/login", data={"username": "guardia", "password": "guardia123"}, follow_redirects=True)
assert resp.status_code == 200
assert b"Escanear c\xc3\xb3digo QR" in resp.data
print("OK: guardia inició sesión y ve la pantalla de escaneo (no el panel admin).\n")

print("=== 5. El guardia NO debe poder entrar al panel de admin ===")
resp = client.get("/admin")
assert resp.status_code == 403
print("OK: acceso al panel admin bloqueado para el guardia (403).\n")

print("=== 6. Primer escaneo del QR -> debe registrar ENTRADA ===")
resp = client.post("/api/scan", json={"qr_token": persona["qr_token"]})
data = resp.get_json()
assert data["ok"] is True
assert data["tipo"] == "entrada", data
assert data["nombre"] == "Juan Pérez (prueba)"
assert data["cedula"] == "1799999999"
print(f"OK: {data}\n")

print("=== 7. Segundo escaneo del mismo QR -> debe registrar SALIDA (alterna) ===")
resp = client.post("/api/scan", json={"qr_token": persona["qr_token"]})
data = resp.get_json()
assert data["tipo"] == "salida", data
print(f"OK: {data}\n")

print("=== 8. Tercer escaneo -> debe volver a ENTRADA ===")
resp = client.post("/api/scan", json={"qr_token": persona["qr_token"]})
data = resp.get_json()
assert data["tipo"] == "entrada", data
print(f"OK: {data}\n")

print("=== 9. Escanear un QR inexistente -> debe dar error controlado ===")
resp = client.post("/api/scan", json={"qr_token": "token-que-no-existe"})
assert resp.status_code == 404
data = resp.get_json()
assert data["ok"] is False
print(f"OK: {data}\n")

print("=== 10. Verificar historial de registros en la base de datos ===")
registros = models.listar_registros(persona_id=persona["id"])
assert len(registros) == 3
tipos = [r["tipo"] for r in registros]
assert tipos == ["entrada", "salida", "entrada"], tipos
print(f"OK: historial correcto (más reciente primero): {tipos}\n")

print("=== 11. Verificar que se generó la imagen del QR ===")
from pathlib import Path
qr_path = Path("qrcodes") / "1799999999.png"
assert qr_path.exists(), "No se generó el archivo PNG del QR"
print(f"OK: imagen QR generada en {qr_path}\n")

print("TODAS LAS PRUEBAS PASARON CORRECTAMENTE ✔")
