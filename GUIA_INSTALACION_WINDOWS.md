# Instalar PASEC en una computadora con Windows

Esta guía instala PASEC en una computadora con Windows de la organización, la deja
arrancando sola y la publica con el dominio de la organización (con candado HTTPS)
para que el guardia escanee desde su celular con datos móviles.

**Tiempo aproximado:** 45 minutos, más lo que tarde quien administra el dominio.

> Importante: el sistema solo funciona mientras esta computadora esté
> **prendida, con internet y sin suspenderse**. Debe estar encendida desde
> antes de que llegue el primer voluntario hasta después de que salga el último.

---

## Parte 1. Preparar la computadora

1. Instala **Python 3.12 o más nuevo**: https://www.python.org/downloads/
   En la primera pantalla del instalador **marca la casilla "Add python.exe to PATH"**
   y luego pulsa "Install Now".
2. Copia la carpeta `pasec` (la que viene dentro de `pasec.zip`) al escritorio o a
   `C:\pasec`. Evita carpetas de OneDrive.

## Parte 2. Llevar los datos actuales (solo si ya hay personas registradas)

Hazlo **antes** de instalar, para no empezar de cero.

1. En PythonAnywhere abre la consola Bash y escribe:
   ```
   cd ~/pasec
   zip -r datos.zip pasec.db fotos
   ```
2. En la pestaña **Files** entra a `/home/TU_USUARIO/pasec/`, busca `datos.zip`
   y descárgalo.
3. Descomprime `datos.zip` **dentro de la carpeta `pasec` de la nueva computadora**
   (deben quedar `pasec.db` y la carpeta `fotos` junto a `app.py`).

Cuando el sistema nuevo esté funcionando, **deja de usar el de PythonAnywhere**:
si se usan los dos a la vez, los registros quedan repartidos.

## Parte 3. Instalar

1. Doble clic en **`1_INSTALAR.bat`**. Necesita internet y tarda unos minutos.
   Al final debe decir "Instalacion terminada".
2. Doble clic en **`CAMBIAR_CLAVE.bat`** y cambia la contraseña de `admin`.
   Vuelve a abrirlo y cambia la de `guardia`. Usa al menos 8 caracteres.
3. Doble clic en **`2_INICIAR.bat`**. Se abre una ventana negra: **no la cierres**
   (puede minimizarla). Mientras esté abierta, el sistema funciona.
4. Prueba en esa misma computadora: abre el navegador en http://localhost:8000
   e inicia sesión.

## Parte 4. Que arranque solo

1. Doble clic en **`INICIO_AUTOMATICO.bat`**. Desde ahora, al iniciar sesión en
   Windows el sistema arranca solo (en una ventana minimizada).
2. Evita que Windows se duerma:
   *Configuración → Sistema → Inicio/apagado y suspensión (o Energía)* →
   pon **"Nunca"** en suspender cuando está conectada a la corriente.
3. Si se puede, deja la computadora en un lugar con corriente estable (idealmente
   con un UPS pequeño) y conectada por cable de red.

## Parte 5. Publicarlo con el dominio de la organización (HTTPS)

El guardia usa datos móviles y la cámara del celular solo funciona con HTTPS, así
que el sistema debe tener una dirección segura, por ejemplo
`https://pasec.TU-DOMINIO.org`. Se hace con **Cloudflare Tunnel** (gratis):
la computadora abre una conexión segura hacia Cloudflare y no hace falta abrir
puertos en el router.

**Qué dominio usar.** Hay dos caminos para el paso 1:

- **Dominio nuevo, a nombre de la organización (recomendado si el sistema se maneja por
  separado de la página web).** Se compra un dominio sencillo registrado a nombre
  de la organización (por ejemplo `pasec-tuorganizacion.org`; en Cloudflare o en cualquier
  registrador, normalmente unos 10 a 15 dólares al año). Así no se toca la página
  web ni el correo de la organización. Quedaría `https://pasec.<dominio-nuevo>`.
- **Dominio de la página web que ya tiene la organización.** Quien lo administre
  tendría que pasarlo a Cloudflare, lo que afecta también a la página web: hacerlo
  solo con esa persona presente y revisar después que la página y el correo sigan bien.

1. **Poner el dominio en Cloudflare.** Crear una cuenta gratuita en
   https://dash.cloudflare.com y agregar el dominio elegido ("Add a site",
   plan Free). Si es un dominio que ya existía, Cloudflare copia los registros
   actuales y pide cambiar los *nameservers* en el proveedor donde se compró.
2. En Cloudflare entra a **Zero Trust** (puede pedir crear un equipo gratuito) →
   **Networks → Tunnels → Create a tunnel → Cloudflared**. Ponle de nombre `pasec`.
3. Elige **Windows**. Cloudflare muestra un comando. Cópialo, abre **"Símbolo del
   sistema" como administrador** en la computadora de la organización, pégalo y presiona
   Enter. Eso instala el túnel como servicio: arranca solo con Windows.
4. En **Public hostname** agrega:
   - Subdomain: `pasec`
   - Domain: el dominio de la organización
   - Service: tipo **HTTP**, URL **localhost:8000**
5. Prueba desde un celular con datos móviles: `https://pasec.TU-DOMINIO.org`.
   Debe aparecer el login con candado.

(Los nombres de los menús de Cloudflare pueden cambiar un poco con el tiempo.)

Nota para el tema legal: el sistema y la base de datos quedan **solo en la
computadora de la organización**; Cloudflare únicamente transporta la conexión cifrada.
Conviene confirmarlo con quien revise el requisito de protección de datos.

## Parte 6. Uso diario

- **Al llegar:** prender la computadora. El sistema arranca solo. Para comprobarlo,
  abrir la dirección del sistema en el navegador.
- **Al terminar la jornada:** apagar la computadora solo después de la última salida.
- **Copias de seguridad:** cada vez que arranca el sistema se crea una copia en la
  carpeta `respaldos` (se guardan las últimas 30). Una vez por semana copia esa
  carpeta a una memoria USB o a la nube de la organización. También puedes ejecutar
  `RESPALDO.bat` cuando quieras.
- **Actualizar el sistema:** cuando haya una versión nueva, copia sus archivos sobre
  la carpeta (sin borrar `pasec.db`, `fotos` ni `clave_secreta.txt`) y vuelve a abrir
  `2_INICIAR.bat`.

## Problemas frecuentes

| Qué pasa | Qué hacer |
|---|---|
| `1_INSTALAR.bat` dice que no encuentra Python | Reinstala Python marcando "Add python.exe to PATH". |
| La ventana negra se cierra sola | Abre `2_INICIAR.bat` con doble clic y toma una foto del mensaje que queda en pantalla. |
| En el celular sale error al abrir la dirección | Comprueba que la ventana negra de PASEC esté abierta y que haya internet. |
| La cámara no se activa en el celular | La dirección debe empezar con `https://` y tener candado. |
| Se olvidó la contraseña | Ejecuta `CAMBIAR_CLAVE.bat`. |
| Hay que restaurar una copia | Cierra PASEC, copia `pasec.db` y `fotos` desde una carpeta de `respaldos` sobre las de la carpeta principal, y abre `2_INICIAR.bat`. |
