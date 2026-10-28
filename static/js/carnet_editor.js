// Formulario de registro/edición: vista previa en vivo del carnet.
(function () {
    "use strict";

    const datos = JSON.parse(document.getElementById("carnet-datos").textContent);
    const form = document.getElementById("form-carnet");
    const canvas = document.getElementById("vista-previa");
    const campo = (nombre) => form.elements[nombre];

    const panelAjuste = document.getElementById("ajuste-foto");
    const estadoTexto = document.getElementById("estado-calculado");

    Carnet.configurar(datos.config, datos.logo);

    let recursos = null;
    let foto = null;          // imagen de la persona (existente o recién elegida)
    let qr = null;
    let urlTemporal = null;   // URL de la foto elegida en este formulario
    let pendiente = false;

    function numero(nombre) { return parseFloat(campo(nombre).value); }

    function leer() {
        const activo = campo("activo") ? campo("activo").checked : true;
        const desde = campo("vigencia_desde").value;
        const hasta = campo("vigencia_hasta").value;
        return {
            nombre: campo("nombre").value.trim(),
            tipo: campo("tipo_voluntariado").value.trim(),
            desde, hasta,
            estado: Carnet.estadoCredencial(desde, hasta, activo),
            contactoNombre: campo("contacto_nombre").value.trim(),
            contactoTelefono: campo("contacto_telefono").value.trim(),
            frase: campo("frase_extra").value.trim(),
            foto,
            fotoZoom: numero("foto_zoom") || 1,
            fotoX: numero("foto_x"),
            fotoY: numero("foto_y"),
            qr,
        };
    }

    function redibujar() {
        if (!recursos || pendiente) return;
        pendiente = true;
        requestAnimationFrame(() => {
            pendiente = false;
            const d = leer();
            estadoTexto.textContent = d.estado;
            Carnet.dibujar(canvas, d, recursos, { escala: 2, marcadores: true });
        });
    }

    function mostrarAjuste() {
        panelAjuste.hidden = !foto;
    }

    // --- Elegir una foto nueva ---------------------------------------------
    campo("foto").addEventListener("change", async (e) => {
        const archivo = e.target.files[0];
        if (urlTemporal) { URL.revokeObjectURL(urlTemporal); urlTemporal = null; }
        if (!archivo) { return; }
        urlTemporal = URL.createObjectURL(archivo);
        const img = await Carnet.cargarImagen(urlTemporal);
        if (!img) {
            alert("No se pudo leer esa imagen. Elige un archivo PNG o JPG.");
            e.target.value = "";
            return;
        }
        foto = img;
        campo("foto_zoom").value = 1;
        campo("foto_x").value = 0.5;
        campo("foto_y").value = 0.3;
        mostrarAjuste();
        redibujar();
    });

    document.getElementById("foto-restablecer").addEventListener("click", () => {
        campo("foto_zoom").value = 1;
        campo("foto_x").value = 0.5;
        campo("foto_y").value = 0.3;
        redibujar();
    });

    // --- Arrastrar la foto directamente en la vista previa ------------------
    let arrastre = null;

    function aDiseno(e) {
        const r = canvas.getBoundingClientRect();
        const k = Carnet.ANCHO / r.width;
        return { x: (e.clientX - r.left) * k, y: (e.clientY - r.top) * k, k };
    }

    function dentroDeFoto(p) {
        const f = Carnet.FOTO;
        return p.x >= f.x && p.x <= f.x + f.w && p.y >= f.y && p.y <= f.y + f.h;
    }

    canvas.addEventListener("pointerdown", (e) => {
        if (!foto) return;
        const p = aDiseno(e);
        if (!dentroDeFoto(p)) return;
        arrastre = { cx: e.clientX, cy: e.clientY, k: p.k, x: numero("foto_x"), y: numero("foto_y") };
        canvas.setPointerCapture(e.pointerId);
        canvas.style.cursor = "grabbing";
        e.preventDefault();
    });

    canvas.addEventListener("pointermove", (e) => {
        if (!foto) { canvas.style.cursor = ""; return; }
        if (!arrastre) {
            canvas.style.cursor = dentroDeFoto(aDiseno(e)) ? "grab" : "";
            return;
        }
        const { sobraX, sobraY } = Carnet.sobranteFoto(foto, numero("foto_zoom") || 1);
        const dx = (e.clientX - arrastre.cx) * arrastre.k;
        const dy = (e.clientY - arrastre.cy) * arrastre.k;
        const limitar = (v) => Math.max(0, Math.min(1, v));
        if (sobraX > 0) campo("foto_x").value = limitar(arrastre.x - dx / sobraX).toFixed(3);
        if (sobraY > 0) campo("foto_y").value = limitar(arrastre.y - dy / sobraY).toFixed(3);
        redibujar();
    });

    const soltar = () => { arrastre = null; canvas.style.cursor = ""; };
    canvas.addEventListener("pointerup", soltar);
    canvas.addEventListener("pointercancel", soltar);
    canvas.style.touchAction = "pan-y";

    // --- Cualquier cambio del formulario vuelve a dibujar -------------------
    form.addEventListener("input", redibujar);
    form.addEventListener("change", redibujar);

    // --- Arranque ------------------------------------------------------------
    Promise.all([
        Carnet.cargarRecursos(),
        Carnet.cargarImagen(datos.fotoUrl),
        Carnet.cargarImagen(datos.qrUrl),
    ]).then(([r, fotoExistente, qrImg]) => {
        recursos = r;
        foto = fotoExistente;
        qr = qrImg;
        mostrarAjuste();
        redibujar();
    });
})();
