// Lógica de escaneo de QR para la pantalla del guardia.
// Usa la librería html5-qrcode para leer la cámara del dispositivo.

const resultadoDiv = document.getElementById("resultado");
let procesando = false; // evita procesar el mismo QR varias veces seguidas

function mostrarResultado(tipo, texto, esError, fotoUrl) {
    resultadoDiv.classList.remove("resultado-oculto", "resultado-entrada", "resultado-salida", "resultado-error");
    if (esError) {
        resultadoDiv.classList.add("resultado-error");
    } else if (tipo === "entrada") {
        resultadoDiv.classList.add("resultado-entrada");
    } else {
        resultadoDiv.classList.add("resultado-salida");
    }

    let html = "";
    if (fotoUrl) {
        html += `<img class="resultado-foto" src="${fotoUrl}" alt="Foto de la persona">`;
    }
    html += `<div class="resultado-texto">${texto}</div>`;
    resultadoDiv.innerHTML = html;
}

async function procesarCodigo(qrToken) {
    if (procesando) return;
    procesando = true;

    try {
        const resp = await fetch("/api/scan", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ qr_token: qrToken }),
        });
        const data = await resp.json();

        if (!resp.ok || !data.ok) {
            mostrarResultado(null, `⚠️ ${data.error || "No se pudo registrar el escaneo."}`, true, null);
        } else {
            const etiqueta = data.tipo === "entrada" ? "ENTRADA registrada" : "SALIDA registrada";
            mostrarResultado(
                data.tipo,
                `<strong>${etiqueta}</strong><br>${data.nombre}<br>Cédula: ${data.cedula}<br>${data.timestamp}`,
                false,
                data.foto_url
            );
        }
    } catch (err) {
        mostrarResultado(null, "⚠️ Error de conexión con el servidor.", true, null);
    }

    // Pausa breve antes de permitir otro escaneo, para evitar duplicados
    // si la misma persona deja el QR frente a la cámara un momento.
    setTimeout(() => {
        procesando = false;
    }, 3000);
}

const html5QrCode = new Html5Qrcode("reader");
const config = { fps: 10, qrbox: { width: 250, height: 250 } };

Html5Qrcode.getCameras()
    .then((cameras) => {
        if (!cameras || cameras.length === 0) {
            mostrarResultado(null, "⚠️ No se encontró ninguna cámara en este dispositivo.", true);
            return;
        }
        // Preferir la cámara trasera si está disponible (útil en celulares)
        const camaraTrasera = cameras.find((c) => /back|trasera|rear/i.test(c.label));
        const camaraId = camaraTrasera ? camaraTrasera.id : cameras[0].id;

        html5QrCode.start(
            camaraId,
            config,
            (decodedText) => procesarCodigo(decodedText),
            () => {
                /* callback de "no se detectó QR en este frame": se ignora,
                   se llama constantemente mientras la cámara está activa */
            }
        );
    })
    .catch(() => {
        mostrarResultado(
            null,
            "⚠️ No se pudo acceder a la cámara. Revisa los permisos del navegador.",
            true
        );
    });
