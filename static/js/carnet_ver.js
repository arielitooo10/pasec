// Página del carnet de una persona: vista, descarga (PNG/JPG), impresión y compartir.
(function () {
    "use strict";

    const info = JSON.parse(document.getElementById("carnet-datos").textContent);
    const canvas = document.getElementById("carnet");
    const aviso = document.getElementById("carnet-aviso");
    const botones = {
        png: document.getElementById("btn-png"),
        jpg: document.getElementById("btn-jpg"),
        imprimir: document.getElementById("btn-imprimir"),
        compartir: document.getElementById("btn-compartir"),
    };

    Carnet.configurar(info.config, info.logo);

    let recursos = null;
    let datos = null;

    function decir(texto) { aviso.textContent = texto || ""; }

    function guardarArchivo(blob, nombre) {
        const enlace = document.createElement("a");
        enlace.href = URL.createObjectURL(blob);
        enlace.download = nombre;
        document.body.appendChild(enlace);
        enlace.click();
        enlace.remove();
        setTimeout(() => URL.revokeObjectURL(enlace.href), 5000);
    }

    async function descargar(formato) {
        decir("Generando imagen…");
        try {
            const blob = await Carnet.exportar(datos, recursos, formato, 2);
            guardarArchivo(blob, Carnet.nombreArchivo(datos.nombre, formato === "jpeg" ? "jpg" : "png"));
            decir("Listo: el carnet se descargó en tu computadora.");
        } catch (err) {
            decir("No se pudo generar la imagen. Intenta de nuevo.");
        }
    }

    async function imprimir() {
        decir("Preparando impresión…");
        try {
            const blob = await Carnet.exportar(datos, recursos, "png", 2);
            const img = document.getElementById("img-impresion");
            img.onload = () => { decir(""); window.print(); };
            img.src = URL.createObjectURL(blob);
        } catch (err) {
            decir("No se pudo preparar la impresión.");
        }
    }

    async function compartir() {
        try {
            const blob = await Carnet.exportar(datos, recursos, "png", 2);
            const archivo = new File([blob], Carnet.nombreArchivo(datos.nombre, "png"), { type: "image/png" });
            await navigator.share({ files: [archivo], title: "Carnet de voluntariado" });
        } catch (err) {
            if (err && err.name !== "AbortError") decir("No se pudo compartir. Descarga la imagen y envíala manualmente.");
        }
    }

    botones.png.addEventListener("click", () => descargar("png"));
    botones.jpg.addEventListener("click", () => descargar("jpeg"));
    botones.imprimir.addEventListener("click", imprimir);
    botones.compartir.addEventListener("click", compartir);

    // El botón "Compartir" solo aparece en dispositivos que permiten compartir archivos
    // (por ejemplo, un celular), donde se puede mandar directo a WhatsApp.
    try {
        const prueba = new File([new Blob(["x"])], "x.png", { type: "image/png" });
        if (navigator.canShare && navigator.canShare({ files: [prueba] })) botones.compartir.hidden = false;
    } catch (err) { /* sin soporte: el botón queda oculto */ }

    Promise.all([
        Carnet.cargarRecursos(),
        Carnet.cargarImagen(info.carnet.fotoUrl),
        Carnet.cargarImagen(info.carnet.qrUrl),
    ]).then(([r, foto, qr]) => {
        recursos = r;
        datos = Object.assign({}, info.carnet, { foto, qr });
        Carnet.dibujar(canvas, datos, recursos, { escala: 2, marcadores: false });
    });
})();
